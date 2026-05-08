"""
AGENTE DE CUENTAS A COBRAR (AR) - ISBEROAL
============================================
Lee facturas emitidas desde Holded, las parsea (hito + presupuesto + alerta),
las sincroniza en Google Sheets y permite crear borradores nuevos a partir
de prompts en lenguaje natural. Envia alertas por email cuando hay facturas
proximas a vencer o vencidas.

Modos:
    python agente_cobros.py --init       # Crea Spreadsheet y pestanas
    python agente_cobros.py --sync       # Sincroniza Holded -> Sheets + alertas
    python agente_cobros.py --prompt     # REPL interactivo (crear borradores)
    python agente_cobros.py --verbose    # Logging detallado

Configuracion: ver .env.example
"""

import argparse
import base64
import json
import logging
import os
import re
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import gspread
from gspread.exceptions import APIError, WorksheetNotFound
from gspread_formatting import (
    CellFormat, Color, TextFormat, format_cell_range,
    set_frozen, DataValidationRule, BooleanCondition, set_data_validation_for_cell_range,
)

import anthropic


# ═════════════════════════════════════════════════════════════
# SECCION 1 - CONFIGURACION Y CONSTANTES
# ═════════════════════════════════════════════════════════════

BASE_DIR        = Path(__file__).parent
ENV_PATH        = BASE_DIR / ".env"
LOGS_DIR        = BASE_DIR / "logs"
PROCESADOS_PATH = BASE_DIR / "facturas_procesadas.json"

LOGS_DIR.mkdir(exist_ok=True)

load_dotenv(ENV_PATH, override=True)

HOLDED_API_KEY        = os.getenv("HOLDED_API_KEY", "").strip()
ANTHROPIC_API_KEY     = os.getenv("ANTHROPIC_API_KEY", "").strip()
GOOGLE_CREDENTIALS    = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_TOKEN_PATH     = str(BASE_DIR / "token.json")
SPREADSHEET_ID        = os.getenv("SPREADSHEET_ID", "").strip()
SPREADSHEET_TITLE     = os.getenv("SPREADSHEET_TITLE", "Isberoal AR — Cuentas a cobrar")
ALERT_EMAIL_TO        = os.getenv("ALERT_EMAIL_TO", "contabilidad@isberoal.com").strip()
HITO_VALIDATION_MODE  = os.getenv("HITO_VALIDATION_MODE", "warning").lower()

# Resolver credentials.json relativo a BASE_DIR si es relativo
_creds_path = Path(GOOGLE_CREDENTIALS)
if not _creds_path.is_absolute():
    GOOGLE_CREDENTIALS = str(BASE_DIR / _creds_path)

HOLDED_BASE_URL = "https://api.holded.com/api/invoicing/v1"

# Scopes ampliados respecto al agente hermano: lectura/envio Gmail + Sheets + Drive
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Pestanas y cabeceras
TAB_FACTURAS  = "Facturas_Emitidas"
TAB_PROYECTOS = "Proyectos_Hitos"
TAB_DASHBOARD = "Dashboard_AR"

HEADERS_FACTURAS = [
    "id_holded", "num_factura", "cliente", "id_presupuesto", "hito",
    "fecha_emision", "fecha_vencimiento", "dias_vencimiento",
    "importe_base", "iva", "importe_total", "porcentaje_hito",
    "estado_holded", "estado_cobro", "alerta", "notas",
]

HEADERS_PROYECTOS = [
    "id_presupuesto", "cliente", "valor_total_contrato",
    "hito_1_importe", "hito_1_estado", "hito_1_fecha_venc",
    "hito_2_importe", "hito_2_estado", "hito_2_fecha_venc",
    "hito_3_importe", "hito_3_estado", "hito_3_fecha_venc",
    "total_cobrado", "total_pendiente", "porcentaje_completado",
]

# ─────────────────────────────────────────────────────────────────────────────
# CODIGOS DE ESTADO DE HOLDED (verificado empiricamente con datos reales el
# 2026-05-05 sobre /api/invoicing/v1/documents/invoice de Isberoal):
#
# El campo `status` (int) por SI SOLO no es fiable. Hay que combinar varios:
#
#   - draft (truthy)     ->  es Borrador, sin importar status
#   - approvedAt (set)   ->  factura ya aprobada/emitida
#   - status == 3        ->  Anulada
#   - paymentsPending=0  ->  Cobrada (con paymentsTotal == total)
#   - paymentsTotal>0
#       y < total        ->  Parcial
#   - resto              ->  Pendiente (o Vencida si dueDate < hoy)
#
# Casos de status observados:
#   status = 0  con draft=null y approvedAt set      -> Aprobada/Pendiente (NO borrador!)
#   status = 0  con draft=true                       -> Borrador
#   status = 1  -> Pendiente (aprobada, no cobrada)
#   status = 2  -> Cobrada
#   status = 3  -> Anulada
#
# IMPORTANTE:
#  - "Vencida" NO es un status de Holded; se infiere de dueDate < hoy.
#  - Holded NO siempre actualiza el status al cobrar. Para detectar cobros reales
#    hay que mirar paymentsTotal / paymentsPending del DETALLE
#    (/documents/invoice/{id}); estos campos NO siempre vienen en el listado.
#  - No existen campos cancelled/void/isVoid: la anulacion va por status=3.
#  - Las rectificativas son un docType aparte: /documents/creditnote.
# ─────────────────────────────────────────────────────────────────────────────
ESTADO_MAP = {
    0: "Borrador",     "draft":       "Borrador",
    1: "Pendiente",    "outstanding": "Pendiente",  "pending": "Pendiente",
    2: "Cobrada",      "paid":        "Cobrada",
    3: "Anulada",      "cancelled":   "Anulada",    "voided": "Anulada",
}

ALERTA_ROJA     = "🔴 VENCIDA"
ALERTA_AMARILLA = "🟡 PRÓXIMA"
ALERTA_VERDE    = "🟢 OK"

# Texto "primer/segundo/tercer" para construir descripciones
HITO_TEXTO = {1: "primer", 2: "segundo", 3: "tercer y último"}


# ═════════════════════════════════════════════════════════════
# SECCION 2 - LOGGING Y UTILIDADES
# ═════════════════════════════════════════════════════════════

def configurar_logging(verbose: bool = False) -> logging.Logger:
    """Logger dual: archivo UTF-8 (con emojis) + consola ASCII (sin emojis)."""
    logger = logging.getLogger("agente_cobros")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh = logging.FileHandler(
        LOGS_DIR / f"agente_cobros_{datetime.now().strftime('%Y%m%d')}.log",
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


log = configurar_logging(verbose=False)


def normalizar_texto(s: str) -> str:
    """Quita acentos y pasa a minusculas. Robustez para regex de hitos."""
    if not s:
        return ""
    nfd = unicodedata.normalize("NFD", s)
    sin_acentos = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return sin_acentos.lower().strip()


def formato_eur(n) -> str:
    """Formato europeo: 12.400,50 €. Acepta None/str/float/int."""
    if n is None or n == "":
        return ""
    try:
        v = float(n)
    except (TypeError, ValueError):
        return str(n)
    entero, decimal = f"{v:,.2f}".split(".")
    entero = entero.replace(",", ".")
    return f"{entero},{decimal} €"


def fecha_a_str(d) -> str:
    """Convierte date/datetime/timestamp/string a DD/MM/YYYY."""
    if not d:
        return ""
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(d[:19], fmt).strftime("%d/%m/%Y")
            except ValueError:
                continue
        return d
    if isinstance(d, (int, float)):
        try:
            return datetime.fromtimestamp(int(d)).strftime("%d/%m/%Y")
        except (ValueError, OSError):
            return ""
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    return str(d)


def parsear_fecha(d) -> date | None:
    """Convierte cualquier representacion de fecha de Holded a `date`."""
    if not d:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, (int, float)):
        try:
            return datetime.fromtimestamp(int(d)).date()
        except (ValueError, OSError):
            return None
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(d[:19], fmt).date()
            except ValueError:
                continue
    return None


def normalizar_importe(v) -> float:
    """Holded devuelve los importes en euros (float o int). No convertir."""
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ═════════════════════════════════════════════════════════════
# SECCION 3 - CLIENTE HOLDED
# ═════════════════════════════════════════════════════════════

_contactos_cache: dict | None = None


def _holded_request(method: str, url: str, max_retries: int = 3, **kwargs) -> requests.Response:
    """Wrapper con retry exponencial en 429 y 5xx."""
    if not HOLDED_API_KEY:
        raise RuntimeError("HOLDED_API_KEY no configurada en .env")

    headers = kwargs.pop("headers", {})
    headers["key"] = HOLDED_API_KEY
    if method.upper() in ("POST", "PATCH", "PUT"):
        headers.setdefault("Content-Type", "application/json")

    for intento in range(max_retries):
        try:
            resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                espera = 2 ** intento
                log.warning(f"[HOLDED RETRY] {resp.status_code} en {url} - reintento en {espera}s ({intento+1}/{max_retries})")
                time.sleep(espera)
                continue
            return resp
        except requests.RequestException as e:
            espera = 2 ** intento
            log.warning(f"[HOLDED RETRY] Excepcion {e} en {url} - reintento en {espera}s ({intento+1}/{max_retries})")
            time.sleep(espera)
    raise RuntimeError(f"Holded API: agotados {max_retries} reintentos para {method} {url}")


def _holded_listar_documentos(doc_type: str) -> list[dict]:
    """Generico: lista todos los documentos de un docType (paginado)."""
    todas = []
    page = 1
    url_base = f"{HOLDED_BASE_URL}/documents/{doc_type}"
    while True:
        resp = _holded_request("GET", url_base, params={"page": page})
        if resp.status_code != 200:
            log.error(f"[HOLDED] GET /documents/{doc_type} page={page} -> {resp.status_code}: {resp.text[:200]}")
            break
        try:
            batch = resp.json()
        except json.JSONDecodeError:
            break
        if not batch or not isinstance(batch, list):
            break
        todas.extend(batch)
        log.debug(f"[HOLDED] {doc_type} page={page}, recibidos {len(batch)} (acum {len(todas)})")
        if len(batch) < 100:
            break
        page += 1
    return todas


def holded_get_invoices_income() -> list[dict]:
    """Lista todas las facturas emitidas (incluyendo borradores). Paginado."""
    facturas = _holded_listar_documentos("invoice")
    log.info(f"[HOLDED] Total facturas emitidas: {len(facturas)}")
    return facturas


def holded_get_credit_notes() -> list[dict]:
    """Lista todas las facturas rectificativas emitidas (creditnote)."""
    rectificativas = _holded_listar_documentos("creditnote")
    log.info(f"[HOLDED] Total rectificativas emitidas: {len(rectificativas)}")
    return rectificativas


def holded_get_invoice_detail(invoice_id: str) -> dict:
    """GET /documents/invoice/{id} - detalle completo con notes/desc/items."""
    resp = _holded_request("GET", f"{HOLDED_BASE_URL}/documents/invoice/{invoice_id}")
    if resp.status_code != 200:
        log.error(f"[HOLDED] GET detail {invoice_id} -> {resp.status_code}")
        return {}
    try:
        return resp.json()
    except json.JSONDecodeError:
        return {}


def holded_create_draft(payload: dict) -> dict:
    """
    POST /documents/invoice con status=0 (borrador).
    Estructura del payload (ver Accounts-Payable para los campos correctos):
        contactId, invoiceNum (opcional), date (timestamp), dueDate, notes,
        items: [{name, units, subtotal, tax, ...}]
    """
    payload = dict(payload)
    payload["status"] = 0
    resp = _holded_request("POST", f"{HOLDED_BASE_URL}/documents/invoice", json=payload)
    if resp.status_code in (200, 201):
        try:
            return resp.json()
        except json.JSONDecodeError:
            return {}
    log.error(f"[HOLDED] POST draft -> {resp.status_code}: {resp.text[:300]}")
    return {}


def holded_update_invoice(invoice_id: str, payload: dict) -> dict:
    """PATCH /documents/invoice/{id}."""
    resp = _holded_request("PATCH", f"{HOLDED_BASE_URL}/documents/invoice/{invoice_id}", json=payload)
    if resp.status_code in (200, 201, 204):
        try:
            return resp.json()
        except json.JSONDecodeError:
            return {}
    log.error(f"[HOLDED] PATCH {invoice_id} -> {resp.status_code}: {resp.text[:300]}")
    return {}


def cargar_contactos_holded(forzar: bool = False) -> dict:
    """
    Carga TODOS los contactos (paginado) y los indexa por nombre normalizado
    y tambien por id. La API no soporta filtro por nombre (bug conocido).
    """
    global _contactos_cache
    if _contactos_cache is not None and not forzar:
        return _contactos_cache

    todos = []
    page = 1
    while True:
        resp = _holded_request("GET", f"{HOLDED_BASE_URL}/contacts", params={"page": page})
        if resp.status_code != 200:
            log.error(f"[CONTACTOS] page={page} -> {resp.status_code}")
            break
        try:
            batch = resp.json()
        except json.JSONDecodeError:
            break
        if not batch or not isinstance(batch, list):
            break
        todos.extend(batch)
        if len(batch) < 500:
            break
        page += 1

    cache = {"by_name": {}, "by_id": {}}
    for c in todos:
        cid = c.get("id")
        name = (c.get("name") or "").strip()
        if cid:
            cache["by_id"][cid] = c
        if name:
            cache["by_name"][normalizar_texto(name)] = c

    _contactos_cache = cache
    log.info(f"[CONTACTOS] Cargados {len(todos)} contactos en cache")
    return cache


def holded_search_contact(nombre: str) -> dict | None:
    """
    Busca contacto por nombre (match exacto normalizado, luego sustring).
    Devuelve el dict completo del contacto o None.
    """
    if not nombre:
        return None
    cache = cargar_contactos_holded()
    norm = normalizar_texto(nombre)

    if norm in cache["by_name"]:
        return cache["by_name"][norm]

    coincidencias = [c for k, c in cache["by_name"].items() if norm in k or k in norm]
    if len(coincidencias) == 1:
        return coincidencias[0]
    if len(coincidencias) > 1:
        log.warning(f"[CONTACTOS] {len(coincidencias)} coincidencias para '{nombre}'. Uso la primera: {coincidencias[0].get('name')}")
        return coincidencias[0]
    return None


def holded_get_contact_by_id(contact_id: str) -> dict | None:
    """Devuelve datos del contacto desde el cache (lo carga si hace falta)."""
    if not contact_id:
        return None
    cache = cargar_contactos_holded()
    return cache["by_id"].get(contact_id)


# ═════════════════════════════════════════════════════════════
# SECCION 4 - PARSER DE FACTURAS
# ═════════════════════════════════════════════════════════════

RE_PRESUPUESTO     = re.compile(r"PRE\d+", re.IGNORECASE)
RE_PRESUPUESTO_NUM = re.compile(r"presupuesto\s+(\d{5,7})\b", re.IGNORECASE)
RE_PORCENTAJE      = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")


def _extraer_id_presupuesto(texto: str) -> str | None:
    """Detecta `PREXXXXXX` o, en su defecto, `presupuesto NNNNNN` (sin prefijo)."""
    m = RE_PRESUPUESTO.search(texto)
    if m:
        return m.group(0).upper()
    m = RE_PRESUPUESTO_NUM.search(texto)
    if m:
        return f"PRE{m.group(1)}"
    return None


def _extraer_texto_factura(invoice: dict) -> str:
    """Busca el texto descriptivo en notes -> desc -> items[0].desc -> concept."""
    candidatos = [
        invoice.get("notes"),
        invoice.get("desc"),
        invoice.get("description"),
        invoice.get("concept"),
    ]
    items = invoice.get("items") or invoice.get("products") or []
    if items and isinstance(items, list):
        primero = items[0] if isinstance(items[0], dict) else {}
        candidatos.append(primero.get("desc"))
        candidatos.append(primero.get("description"))
        candidatos.append(primero.get("name"))

    for c in candidatos:
        if c and str(c).strip():
            return str(c)
    return ""


def _extraer_hito(texto_norm: str) -> int | None:
    """
    Detecta hito explicito en el texto. Orden de prioridad: mas especifico primero.
    "Ultimo pago" / "tercer y ultimo" -> 3.
    Si no hay marcador explicito, devuelve None (la asignacion por orden
    cronologico se hace despues, en `asignar_hitos_por_orden`).
    """
    if "tercer y ultimo pago" in texto_norm or "tercero y ultimo pago" in texto_norm:
        return 3
    if "tercer pago" in texto_norm or "tercero pago" in texto_norm:
        return 3
    if "ultimo pago" in texto_norm or "pago final" in texto_norm or "pago de fin de obra" in texto_norm:
        return 3
    if "segundo pago" in texto_norm:
        return 2
    if "primer pago" in texto_norm or "primero pago" in texto_norm:
        return 1
    # Fallback: numeros ordinales sueltos en contexto de "pago"/"hito"
    if re.search(r"\bhito\s*1\b", texto_norm):
        return 1
    if re.search(r"\bhito\s*2\b", texto_norm):
        return 2
    if re.search(r"\bhito\s*3\b", texto_norm):
        return 3
    return None


def _calcular_alerta(estado_cobro: str, fecha_venc: date | None) -> str:
    """
    Logica:
        Vencida -> rojo. <=5 dias y Pendiente/Parcial -> amarillo. Resto -> verde.
        Cobrada/Borrador/Anulada/Rectificativa -> siempre verde.
    """
    if estado_cobro in ("Cobrada", "Borrador", "Anulada", "Rectificativa"):
        return ALERTA_VERDE
    if estado_cobro == "Vencida":
        return ALERTA_ROJA
    if fecha_venc is None:
        return ALERTA_VERDE
    dias = (fecha_venc - date.today()).days
    if dias < 0:
        return ALERTA_ROJA
    if dias <= 5:
        return ALERTA_AMARILLA
    return ALERTA_VERDE


def asignar_hitos_por_orden(facturas: list[dict]) -> int:
    """
    Para facturas con id_presupuesto pero sin hito explicito, asigna hito
    por orden cronologico dentro del presupuesto:
        1a factura -> hito 1, 2a -> hito 2, 3a -> hito 3.
    Respeta hitos explicitos (p.ej. detectado por "ultimo pago"): no los
    sobreescribe; los implicitos se asignan a los huecos libres.
    Devuelve el numero de facturas a las que se asigno hito automaticamente.
    """
    por_pre: dict[str, list[dict]] = {}
    for f in facturas:
        pre = f.get("id_presupuesto")
        if pre:
            por_pre.setdefault(pre, []).append(f)

    asignados = 0
    for pre, lista in por_pre.items():
        # Orden cronologico (mas antigua primero)
        lista.sort(key=lambda x: x.get("fecha_emision") or date.min)

        # Posiciones (1,2,3) ya ocupadas por hito explicito
        ocupados = {f["hito"] for f in lista if isinstance(f.get("hito"), int) and f["hito"] in (1, 2, 3)}

        siguiente = 1
        for f in lista:
            if isinstance(f.get("hito"), int) and f["hito"] in (1, 2, 3):
                continue
            while siguiente in ocupados and siguiente <= 3:
                siguiente += 1
            if siguiente <= 3:
                f["hito"] = siguiente
                f["hito_inferido"] = True
                ocupados.add(siguiente)
                asignados += 1
                siguiente += 1
            else:
                # Mas de 3 facturas en este presupuesto, dejar sin hito
                f["hito"] = None
    return asignados


def parse_invoice_metadata(invoice: dict) -> dict:
    """
    Extrae metadatos enriquecidos de una factura de Holded.
    Devuelve un dict listo para upsert en la pestana Facturas_Emitidas.
    """
    texto = _extraer_texto_factura(invoice)
    texto_norm = normalizar_texto(texto)

    hito = _extraer_hito(texto_norm)
    id_presupuesto = _extraer_id_presupuesto(texto)

    m_pct = RE_PORCENTAJE.search(texto)
    porcentaje_hito = None
    if m_pct:
        try:
            porcentaje_hito = float(m_pct.group(1).replace(",", "."))
        except ValueError:
            porcentaje_hito = None

    # Estado de cobro (no fiarse solo del 'status' de Holded - puede no actualizarse al cobrar).
    # Estrategia: combinar status + campos de pago (paid, paymentsTotal, paymentsPending).
    estado_raw = invoice.get("status")
    paid_flag    = invoice.get("paid")  # a veces 0/1
    pagos_total  = invoice.get("paymentsTotal") or invoice.get("paid_total") or 0
    pagos_pdte   = invoice.get("paymentsPending") or invoice.get("paid_pending")
    importe_holded = invoice.get("total") or 0

    try:
        pagos_total = float(pagos_total)
    except (TypeError, ValueError):
        pagos_total = 0.0
    try:
        pagos_pdte_f = float(pagos_pdte) if pagos_pdte is not None else None
    except (TypeError, ValueError):
        pagos_pdte_f = None
    try:
        importe_holded = float(importe_holded)
    except (TypeError, ValueError):
        importe_holded = 0.0

    # Tipo de documento (invoice estandar / creditnote rectificativa)
    doc_type = invoice.get("_doc_type", "invoice")

    # Deteccion de anuladas: prioridad al status=3 (verificado en datos reales).
    # Otros nombres de campo de respaldo por si Holded los usa en otras versiones.
    cancelled_flag = (
        invoice.get("cancelled") or invoice.get("isCancelled")
        or invoice.get("void") or invoice.get("isVoid")
        or invoice.get("voided") or invoice.get("isCancel")
    )
    es_anulada = (estado_raw == 3) or (cancelled_flag in (1, True, "1", "true"))

    # Deteccion de borradores: NO basta con status=0. El indicador real es
    # el campo `draft` o la ausencia de `approvedAt` (timestamp de aprobacion).
    # Verificado con factura 69eb52390813ef414b0e1fdf: status=0, draft=null,
    # approvedAt=valor -> esta APROBADA, no borrador.
    draft_flag   = invoice.get("draft")
    approved_at  = invoice.get("approvedAt")
    es_borrador  = (
        draft_flag in (1, True, "1", "true")
        or (estado_raw == 0 and not approved_at and not invoice.get("docNumber"))
    )

    if doc_type == "creditnote":
        estado_cobro = "Rectificativa"
    elif es_anulada:
        estado_cobro = "Anulada"
    elif es_borrador:
        estado_cobro = "Borrador"
    elif paid_flag in (1, True, "1", "true"):
        estado_cobro = "Cobrada"
    elif pagos_pdte_f is not None and pagos_pdte_f <= 0.01 and importe_holded > 0:
        estado_cobro = "Cobrada"
    elif pagos_total > 0 and importe_holded > 0 and pagos_total >= importe_holded - 0.01:
        estado_cobro = "Cobrada"
    elif pagos_total > 0 and importe_holded > 0 and pagos_total < importe_holded - 0.01:
        estado_cobro = "Parcial"
    else:
        # Aprobada sin pagos registrados -> Pendiente (puede pasar a Vencida segun fecha)
        estado_cobro = "Pendiente"
    estado_mapeado_ok = True

    # Fechas
    fecha_emision = parsear_fecha(invoice.get("date") or invoice.get("issueDate"))
    payment_terms = str(invoice.get("paymentTerms") or invoice.get("payment") or "").lower()
    if invoice.get("dueDate"):
        fecha_venc = parsear_fecha(invoice.get("dueDate"))
    elif fecha_emision:
        if "contado" in payment_terms or payment_terms in ("0", "0d"):
            fecha_venc = fecha_emision
        else:
            # Default B2B Espana: 30 dias desde la emision (no 7).
            # Si Holded devuelve dueDate, ese gana sobre esto.
            fecha_venc = fecha_emision + timedelta(days=30)
    else:
        fecha_venc = None

    # Si esta Pendiente/Parcial y la fecha de vencimiento ha pasado -> Vencida
    if estado_cobro in ("Pendiente", "Parcial") and fecha_venc and fecha_venc < date.today():
        estado_cobro = "Vencida"

    alerta = _calcular_alerta(estado_cobro, fecha_venc)

    # Importes (con normalizacion centimos -> euros)
    importe_base  = normalizar_importe(invoice.get("subtotal") or invoice.get("base"))
    importe_total = normalizar_importe(invoice.get("total"))
    # Las rectificativas se representan con importe NEGATIVO para que cuadren los totales
    if doc_type == "creditnote":
        if importe_base > 0:
            importe_base = -importe_base
        if importe_total > 0:
            importe_total = -importe_total
    iva_pct       = invoice.get("tax") or invoice.get("vat") or invoice.get("ivaPct")
    if iva_pct is None and importe_base and importe_total and importe_base > 0:
        try:
            iva_pct = round(((importe_total - importe_base) / importe_base) * 100, 2)
        except (TypeError, ZeroDivisionError):
            iva_pct = None

    dias_venc = (fecha_venc - date.today()).days if fecha_venc else None

    # Cliente
    cliente = (
        invoice.get("contactName")
        or invoice.get("contact_name")
        or (invoice.get("contact") or {}).get("name")
        or ""
    )
    if not cliente:
        contact_id = invoice.get("contactId") or invoice.get("contact_id")
        if contact_id:
            c = holded_get_contact_by_id(contact_id)
            if c:
                cliente = c.get("name", "")

    if not hito:
        log.debug(f"[PARSE] Sin hito explicito en factura {invoice.get('id')} (texto: {texto[:80]!r})")
    if not id_presupuesto:
        log.debug(f"[PARSE] Sin id_presupuesto en factura {invoice.get('id')}")

    return {
        "id_holded":         invoice.get("id", ""),
        "num_factura":       invoice.get("docNumber") or invoice.get("invoiceNum") or invoice.get("number") or "",
        "cliente":           cliente,
        "id_presupuesto":    id_presupuesto or "",
        "hito":              hito if hito else None,
        "fecha_emision":     fecha_emision,
        "fecha_vencimiento": fecha_venc,
        "dias_vencimiento":  dias_venc if dias_venc is not None else "",
        "importe_base":      importe_base,
        "iva":               iva_pct if iva_pct is not None else "",
        "importe_total":     importe_total,
        "porcentaje_hito":   porcentaje_hito if porcentaje_hito is not None else "",
        "estado_holded":     estado_raw if estado_raw is not None else "",
        "estado_cobro":      estado_cobro,
        "alerta":            alerta,
        "notas":             texto[:500],
    }


# ═════════════════════════════════════════════════════════════
# SECCION 5 - CLIENTES GOOGLE (OAuth + Sheets + Drive + Gmail)
# ═════════════════════════════════════════════════════════════

_google_creds: Credentials | None = None
_gspread_client: gspread.Client | None = None


def get_google_creds() -> Credentials:
    """
    OAuth Desktop flow. Reutiliza token.json. Si los scopes cambian o el
    token no es valido, abre el navegador para reautorizar.
    """
    global _google_creds
    if _google_creds and _google_creds.valid:
        return _google_creds

    creds: Credentials | None = None
    if Path(GOOGLE_TOKEN_PATH).exists():
        try:
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, SCOPES)
        except Exception as e:
            log.warning(f"[OAUTH] token.json invalido: {e}, regenerando")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                log.warning(f"[OAUTH] No se pudo refrescar token: {e}, reautorizando")
                creds = None
        if not creds or not creds.valid:
            if not Path(GOOGLE_CREDENTIALS).exists():
                raise FileNotFoundError(
                    f"No existe {GOOGLE_CREDENTIALS}. Copia el credentials.json de "
                    f"Accounts-Payable/files/ o descarga uno nuevo de Google Cloud."
                )
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GOOGLE_TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    _google_creds = creds
    return creds


def get_gspread_client() -> gspread.Client:
    global _gspread_client
    if _gspread_client is None:
        _gspread_client = gspread.authorize(get_google_creds())
    return _gspread_client


def gsheets_get_or_create_spreadsheet() -> gspread.Spreadsheet:
    """
    Devuelve el Spreadsheet:
    - Si SPREADSHEET_ID en .env esta definido, lo abre.
    - Si no, crea uno nuevo con el titulo configurado y guarda el ID en .env.
    """
    global SPREADSHEET_ID
    gc = get_gspread_client()

    if SPREADSHEET_ID:
        try:
            sh = gc.open_by_key(SPREADSHEET_ID)
            log.info(f"[SHEETS] Abierto Spreadsheet existente: {sh.title}")
            return sh
        except APIError as e:
            log.error(f"[SHEETS] No se pudo abrir SPREADSHEET_ID={SPREADSHEET_ID}: {e}")
            log.info("[SHEETS] Creando nuevo Spreadsheet...")

    # Crear nuevo via Drive API (con drive.file scope) para que aparezca en Drive del usuario
    drive = build("drive", "v3", credentials=get_google_creds())
    file = drive.files().create(
        body={"name": SPREADSHEET_TITLE, "mimeType": "application/vnd.google-apps.spreadsheet"},
        fields="id",
    ).execute()
    new_id = file["id"]
    sh = gc.open_by_key(new_id)
    log.info(f"[SHEETS] Creado Spreadsheet nuevo: {sh.title} (id={new_id})")

    # Persistir el ID en .env
    try:
        if not ENV_PATH.exists():
            ENV_PATH.write_text(f'SPREADSHEET_ID="{new_id}"\n', encoding="utf-8")
        else:
            set_key(str(ENV_PATH), "SPREADSHEET_ID", new_id)
        log.info(f"[SHEETS] SPREADSHEET_ID guardado en {ENV_PATH}")
    except Exception as e:
        log.warning(f"[SHEETS] No se pudo escribir SPREADSHEET_ID en .env: {e}")
        log.warning(f"[SHEETS] Anadelo manualmente: SPREADSHEET_ID={new_id}")

    SPREADSHEET_ID = new_id
    return sh


def _get_or_create_worksheet(sh: gspread.Spreadsheet, title: str, rows: int, cols: int):
    try:
        return sh.worksheet(title)
    except WorksheetNotFound:
        return sh.add_worksheet(title=title, rows=rows, cols=cols)


def inicializar_pestañas(sh: gspread.Spreadsheet) -> None:
    """Crea las 3 pestanas con cabeceras, formato y validacion."""
    ws_facturas = _get_or_create_worksheet(sh, TAB_FACTURAS, rows=1000, cols=len(HEADERS_FACTURAS))
    ws_proyectos = _get_or_create_worksheet(sh, TAB_PROYECTOS, rows=200, cols=len(HEADERS_PROYECTOS))
    ws_dashboard = _get_or_create_worksheet(sh, TAB_DASHBOARD, rows=20, cols=2)

    # Eliminar la pestana "Sheet1" / "Hoja 1" por defecto si existe
    for ws in sh.worksheets():
        if ws.title.lower() in ("sheet1", "hoja 1", "hoja1"):
            try:
                sh.del_worksheet(ws)
            except APIError:
                pass

    header_fmt = CellFormat(
        backgroundColor=Color(0.85, 0.85, 0.85),
        textFormat=TextFormat(bold=True),
        horizontalAlignment="CENTER",
    )

    # Cabeceras Facturas
    if ws_facturas.row_values(1) != HEADERS_FACTURAS:
        ws_facturas.update(values=[HEADERS_FACTURAS], range_name="A1")
        format_cell_range(ws_facturas, f"A1:{_col_letra(len(HEADERS_FACTURAS))}1", header_fmt)
        set_frozen(ws_facturas, rows=1)

    # Cabeceras Proyectos
    if ws_proyectos.row_values(1) != HEADERS_PROYECTOS:
        ws_proyectos.update(values=[HEADERS_PROYECTOS], range_name="A1")
        format_cell_range(ws_proyectos, f"A1:{_col_letra(len(HEADERS_PROYECTOS))}1", header_fmt)
        set_frozen(ws_proyectos, rows=1)

    # Validacion de la columna "alerta" en Facturas (col O = 15)
    try:
        rule = DataValidationRule(
            BooleanCondition("ONE_OF_LIST", [ALERTA_ROJA, ALERTA_AMARILLA, ALERTA_VERDE]),
            showCustomUi=True,
        )
        set_data_validation_for_cell_range(ws_facturas, "O2:O", rule)
    except Exception as e:
        log.debug(f"[SHEETS] Validacion alerta no aplicada: {e}")

    # Dashboard: KPIs base
    kpis_iniciales = [
        ["Métrica", "Valor"],
        ["Total pendiente cobro", ""],
        ["Nº facturas vencidas", ""],
        ["Importe total vencido", ""],
        ["Nº facturas próximas a vencer", ""],
        ["Importe próximo a vencer", ""],
        ["Proyectos activos", ""],
        ["Fecha última sincronización", ""],
    ]
    if ws_dashboard.row_values(1) != ["Métrica", "Valor"]:
        ws_dashboard.update(values=kpis_iniciales, range_name="A1")
        format_cell_range(ws_dashboard, "A1:B1", header_fmt)
        set_frozen(ws_dashboard, rows=1)

    log.info("[SHEETS] Pestanas inicializadas")


def _col_letra(n: int) -> str:
    """1 -> 'A', 26 -> 'Z', 27 -> 'AA'."""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _factura_a_fila(f: dict) -> list:
    """Ordena los campos del dict parseado en la columna correspondiente."""
    return [
        str(f.get("id_holded", "")),
        str(f.get("num_factura", "")),
        str(f.get("cliente", "")),
        str(f.get("id_presupuesto", "")),
        f.get("hito", ""),
        fecha_a_str(f.get("fecha_emision")),
        fecha_a_str(f.get("fecha_vencimiento")),
        f.get("dias_vencimiento", ""),
        formato_eur(f.get("importe_base")) if f.get("importe_base") not in (None, "") else "",
        f.get("iva", ""),
        formato_eur(f.get("importe_total")) if f.get("importe_total") not in (None, "") else "",
        f.get("porcentaje_hito", ""),
        f.get("estado_holded", ""),
        f.get("estado_cobro", ""),
        f.get("alerta", ""),
        f.get("notas", ""),
    ]


def upsert_facturas(sh: gspread.Spreadsheet, facturas: list[dict]) -> tuple[int, int]:
    """
    Upsert por id_holded (col A). Devuelve (nuevas, actualizadas).
    """
    ws = sh.worksheet(TAB_FACTURAS)
    existentes = ws.col_values(1)  # incluye cabecera en pos 0
    indice = {v: i + 1 for i, v in enumerate(existentes) if v}

    filas_nuevas = []
    actualizaciones = []  # [(rango, fila), ...]

    for f in facturas:
        fila = _factura_a_fila(f)
        idh = str(f.get("id_holded", ""))
        if idh in indice and indice[idh] > 1:
            row_num = indice[idh]
            rango = f"A{row_num}:{_col_letra(len(HEADERS_FACTURAS))}{row_num}"
            actualizaciones.append({"range": rango, "values": [fila]})
        else:
            filas_nuevas.append(fila)

    if actualizaciones:
        ws.batch_update(actualizaciones, value_input_option="USER_ENTERED")
    if filas_nuevas:
        ws.append_rows(filas_nuevas, value_input_option="USER_ENTERED")

    return len(filas_nuevas), len(actualizaciones)


def recalcular_proyectos(sh: gspread.Spreadsheet, facturas: list[dict]) -> int:
    """
    Agrupa facturas por id_presupuesto y vuelca a la pestana Proyectos_Hitos.
    Sobreescribe completa la pestana (excepto cabecera).
    """
    proyectos: dict[str, dict] = {}
    for f in facturas:
        pre = f.get("id_presupuesto")
        if not pre:
            continue
        # Las anuladas no cuentan ni como hito ni en totales del proyecto
        if f.get("estado_cobro") == "Anulada":
            continue
        p = proyectos.setdefault(pre, {
            "id_presupuesto": pre,
            "cliente": f.get("cliente", ""),
            "hitos": {},
            "total_cobrado": 0.0,
            "total_pendiente": 0.0,
            "valor_total": 0.0,
        })
        if not p["cliente"] and f.get("cliente"):
            p["cliente"] = f["cliente"]

        h = f.get("hito") or 0
        if h in (1, 2, 3) and f.get("estado_cobro") != "Rectificativa":
            p["hitos"][h] = {
                "importe": f.get("importe_total") or 0,
                "estado":  f.get("estado_cobro", ""),
                "fvenc":   fecha_a_str(f.get("fecha_vencimiento")),
            }

        total = f.get("importe_total") or 0
        try:
            total = float(total)
        except (TypeError, ValueError):
            total = 0.0
        # Las rectificativas (importe negativo) restan del valor del proyecto
        p["valor_total"] += total
        estado = f.get("estado_cobro")
        if estado == "Cobrada":
            p["total_cobrado"] += total
        elif estado == "Rectificativa":
            # La rectificativa no se suma al pendiente; solo afecta al valor_total
            pass
        else:
            p["total_pendiente"] += total

    filas = []
    for pre, p in sorted(proyectos.items()):
        h1 = p["hitos"].get(1, {})
        h2 = p["hitos"].get(2, {})
        h3 = p["hitos"].get(3, {})
        pct = (p["total_cobrado"] / p["valor_total"] * 100) if p["valor_total"] > 0 else 0
        filas.append([
            pre,
            p["cliente"],
            formato_eur(p["valor_total"]),
            formato_eur(h1.get("importe")), h1.get("estado", ""), h1.get("fvenc", ""),
            formato_eur(h2.get("importe")), h2.get("estado", ""), h2.get("fvenc", ""),
            formato_eur(h3.get("importe")), h3.get("estado", ""), h3.get("fvenc", ""),
            formato_eur(p["total_cobrado"]),
            formato_eur(p["total_pendiente"]),
            f"{pct:.1f}%",
        ])

    ws = sh.worksheet(TAB_PROYECTOS)
    # Limpiar todo excepto cabecera
    if ws.row_count > 1:
        ws.batch_clear([f"A2:{_col_letra(len(HEADERS_PROYECTOS))}{ws.row_count}"])
    if filas:
        ws.append_rows(filas, value_input_option="USER_ENTERED")

    return len(filas)


def actualizar_dashboard(sh: gspread.Spreadsheet, facturas: list[dict], n_proyectos: int) -> None:
    # "Pendiente de cobro" excluye explicitamente: cobradas, borradores, anuladas y rectificativas
    pendientes = [
        f for f in facturas
        if f.get("estado_cobro") in ("Pendiente", "Parcial", "Vencida")
    ]
    vencidas   = [f for f in pendientes if f.get("alerta") == ALERTA_ROJA]
    proximas   = [f for f in pendientes if f.get("alerta") == ALERTA_AMARILLA]

    total_pendiente = sum(float(f.get("importe_total") or 0) for f in pendientes)
    total_vencido   = sum(float(f.get("importe_total") or 0) for f in vencidas)
    total_proximo   = sum(float(f.get("importe_total") or 0) for f in proximas)

    ws = sh.worksheet(TAB_DASHBOARD)
    valores = [
        [formato_eur(total_pendiente)],
        [str(len(vencidas))],
        [formato_eur(total_vencido)],
        [str(len(proximas))],
        [formato_eur(total_proximo)],
        [str(n_proyectos)],
        [datetime.now().strftime("%d/%m/%Y %H:%M:%S")],
    ]
    ws.update(values=valores, range_name="B2:B8")
    log.info(f"[DASHBOARD] Pendiente={formato_eur(total_pendiente)} | Vencidas={len(vencidas)} | Proximas={len(proximas)} | Proyectos={n_proyectos}")


# ═════════════════════════════════════════════════════════════
# SECCION 6 - CREADOR DE BORRADORES (Claude + Holded)
# ═════════════════════════════════════════════════════════════

_anthropic_client: anthropic.Anthropic | None = None


def get_anthropic_client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY no configurada en .env")
        _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client


SYSTEM_PROMPT_DRAFT = """Eres un parser que extrae campos de instrucciones en español
para crear borradores de facturas. Devuelve EXCLUSIVAMENTE un JSON valido con esta forma:
{
  "id_presupuesto": "PRE002341",
  "numero_hito": 2,
  "nombre_cliente": "Ayuntamiento de Ribeira",
  "importe": 12400.0
}
Reglas:
- id_presupuesto: formato PRE seguido de digitos (PRE001234). Si falta, usa null.
- numero_hito: 1, 2 o 3. "primer pago"/"primero"=1, "segundo pago"/"segundo"=2, "tercer y ultimo"/"tercer"=3.
- nombre_cliente: nombre tal cual (no inventes nada). Si falta, null.
- importe: numero (admite "12.400" formato europeo o "12400" o "12,4k"). Devuelve float. Si falta, null.
NO incluyas explicaciones. NO uses bloques markdown. SOLO el JSON.
"""


def extract_draft_fields_with_claude(prompt_text: str) -> dict:
    """Llama a Claude Sonnet 4-6 para extraer los campos del prompt."""
    client = get_anthropic_client()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        temperature=0,
        system=SYSTEM_PROMPT_DRAFT,
        messages=[{"role": "user", "content": prompt_text}],
    )
    texto = resp.content[0].text.strip()
    texto = re.sub(r"^```(?:json)?\s*", "", texto)
    texto = re.sub(r"```\s*$", "", texto)
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        log.error(f"[CLAUDE] JSON invalido: {e} | respuesta: {texto[:200]}")
        raise ValueError(f"Claude devolvio JSON invalido: {texto[:200]}") from e


def _validar_secuencia_hitos(sh: gspread.Spreadsheet, id_presupuesto: str, numero_hito: int) -> str | None:
    """
    Devuelve mensaje de warning/error si el hito anterior no esta cobrado.
    Si todo OK, devuelve None.
    """
    if numero_hito == 1:
        return None
    try:
        ws = sh.worksheet(TAB_PROYECTOS)
        valores = ws.get_all_records()
    except WorksheetNotFound:
        return None

    proyecto = next((p for p in valores if p.get("id_presupuesto") == id_presupuesto), None)
    if not proyecto:
        return f"Proyecto {id_presupuesto} no esta registrado todavia (sin hitos previos)"

    estado_anterior = proyecto.get(f"hito_{numero_hito - 1}_estado", "")
    if estado_anterior != "Cobrada":
        return f"El hito {numero_hito - 1} de {id_presupuesto} no esta cobrado (estado: '{estado_anterior or 'sin registrar'}')"
    return None


def create_draft_from_prompt(prompt_text: str, sh: gspread.Spreadsheet) -> dict:
    """
    Pipeline completo:
    1. Claude extrae campos
    2. Validacion de secuencia de hitos (warning o bloqueante segun config)
    3. Construye texto estandar de la factura
    4. Busca contactId
    5. POST borrador en Holded
    Devuelve dict con resultado y resumen.
    """
    log.info(f"[BORRADOR] Prompt: {prompt_text}")
    campos = extract_draft_fields_with_claude(prompt_text)
    pre = campos.get("id_presupuesto")
    hito = campos.get("numero_hito")
    cliente = campos.get("nombre_cliente")
    importe = campos.get("importe")

    faltan = [k for k, v in [("id_presupuesto", pre), ("numero_hito", hito), ("nombre_cliente", cliente), ("importe", importe)] if not v]
    if faltan:
        return {"ok": False, "error": f"Faltan campos: {', '.join(faltan)}", "campos": campos}

    if hito not in (1, 2, 3):
        return {"ok": False, "error": f"numero_hito debe ser 1, 2 o 3 (recibido: {hito})", "campos": campos}

    aviso = _validar_secuencia_hitos(sh, pre, hito)
    if aviso:
        if HITO_VALIDATION_MODE == "strict":
            return {"ok": False, "error": f"Validacion de hitos: {aviso}", "campos": campos}
        log.warning(f"[BORRADOR WARNING] {aviso}")

    # Buscar el porcentaje desde la pestana Proyectos_Hitos si existe
    pct_str = "[X]"
    try:
        ws = sh.worksheet(TAB_FACTURAS)
        registros = ws.get_all_records()
        previas = [r for r in registros if r.get("id_presupuesto") == pre and r.get("hito") == hito]
        if previas and previas[0].get("porcentaje_hito"):
            pct_str = str(previas[0]["porcentaje_hito"])
    except Exception:
        pass

    texto_factura = (
        f"Factura correspondiente al {HITO_TEXTO[hito]} pago del {pct_str}% "
        f"del Presupuesto {pre} consistente en: "
        f"[Instalación sistema fotovoltaico según presupuesto]"
    )

    # Buscar contactId
    contacto = holded_search_contact(cliente)
    if not contacto:
        return {"ok": False, "error": f"Cliente '{cliente}' no encontrado en Holded. Crealo manualmente o revisa el nombre.", "campos": campos}

    # Construir payload de borrador
    importe_float = float(importe)
    payload = {
        "contactId":  contacto["id"],
        "date":       int(datetime.now().timestamp()),
        "notes":      texto_factura,
        "items": [{
            "name":     texto_factura[:200],
            "units":    1,
            "subtotal": importe_float,
            # IVA: dejar a Holded por defecto si no se sabe; si quieres forzar usa "tax": 21
        }],
        "currency":   "eur",
    }

    resultado = holded_create_draft(payload)
    if not resultado or not resultado.get("id"):
        return {"ok": False, "error": "Holded no devolvio ID al crear el borrador", "campos": campos, "payload": payload}

    resumen = {
        "id_holded":   resultado.get("id"),
        "num_factura": resultado.get("docNumber") or resultado.get("invoiceNum") or "(asignado por Holded)",
        "cliente":     contacto.get("name", cliente),
        "id_presupuesto": pre,
        "hito":        hito,
        "importe":     importe_float,
    }
    log.info(f"[BORRADOR OK] Creado en Holded: {resumen}")
    return {"ok": True, "resumen": resumen, "aviso": aviso}


# ═════════════════════════════════════════════════════════════
# SECCION 7 - ALERTAS POR EMAIL (Gmail API)
# ═════════════════════════════════════════════════════════════

def _construir_html_alertas(facturas_alerta: list[dict]) -> str:
    rojas = [f for f in facturas_alerta if f.get("alerta") == ALERTA_ROJA]
    amarillas = [f for f in facturas_alerta if f.get("alerta") == ALERTA_AMARILLA]

    def _fila(f, color):
        return f"""<tr style="background:{color}">
            <td>{f.get('num_factura','')}</td>
            <td>{f.get('cliente','')}</td>
            <td>{f.get('id_presupuesto','')}</td>
            <td>{f.get('hito','')}</td>
            <td style="text-align:right">{formato_eur(f.get('importe_total'))}</td>
            <td style="text-align:right">{f.get('dias_vencimiento','')}</td>
            <td>{f.get('alerta','')}</td>
        </tr>"""

    filas_html = "".join(_fila(f, "#ffd6d6") for f in rojas) + "".join(_fila(f, "#fff4cc") for f in amarillas)
    n_total = len(rojas) + len(amarillas)
    fecha = date.today().strftime("%d/%m/%Y")

    return f"""<html><body style="font-family:Arial,sans-serif">
    <h2>Isberoal AR — Resumen de alertas {fecha}</h2>
    <p>Hay <b>{n_total}</b> facturas que requieren atencion: {len(rojas)} vencidas y {len(amarillas)} proximas a vencer.</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
        <thead style="background:#444;color:white">
            <tr>
                <th>Nº Factura</th><th>Cliente</th><th>Presupuesto</th><th>Hito</th>
                <th>Importe</th><th>Días</th><th>Alerta</th>
            </tr>
        </thead>
        <tbody>{filas_html}</tbody>
    </table>
    <p style="color:#666;font-size:11px;margin-top:18px">
        Generado automaticamente por agente_cobros.py el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    </p>
    </body></html>"""


def send_email_via_gmail(to: str, subject: str, html_body: str) -> bool:
    """Envia un email HTML usando Gmail API. Devuelve True si OK."""
    try:
        service = build("gmail", "v1", credentials=get_google_creds())
        msg = MIMEMultipart("alternative")
        msg["to"] = to
        msg["subject"] = subject
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except HttpError as e:
        log.error(f"[EMAIL] Error Gmail API: {e}")
        return False
    except Exception as e:
        log.error(f"[EMAIL] Error inesperado: {e}")
        return False


def check_and_send_alerts(facturas: list[dict]) -> int:
    """Filtra facturas con alerta y manda email. Devuelve numero de alertas enviadas (0 o 1)."""
    activas = [f for f in facturas if f.get("alerta") in (ALERTA_ROJA, ALERTA_AMARILLA) and f.get("estado_cobro") not in ("Cobrada", "Borrador")]
    if not activas:
        log.info("[ALERTAS] Sin facturas en alerta. Email no enviado.")
        return 0

    fecha = date.today().strftime("%d/%m/%Y")
    subject = f"⚠️ Isberoal AR — {len(activas)} facturas requieren atención [{fecha}]"
    html = _construir_html_alertas(activas)

    destinatarios = [d.strip() for d in ALERT_EMAIL_TO.split(",") if d.strip()]
    enviados = 0
    for d in destinatarios:
        if send_email_via_gmail(d, subject, html):
            log.info(f"[EMAIL] Alerta enviada a {d} ({len(activas)} facturas)")
            enviados += 1
    return enviados


# ═════════════════════════════════════════════════════════════
# SECCION 8 - ORQUESTADOR (sync, prompt REPL, init)
# ═════════════════════════════════════════════════════════════

def cargar_procesados() -> dict:
    if PROCESADOS_PATH.exists():
        try:
            return json.loads(PROCESADOS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def guardar_procesados(d: dict) -> None:
    PROCESADOS_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def ejecutar_sync() -> dict:
    """Pipeline completo de sincronizacion."""
    log.info("=" * 60)
    log.info("INICIO SYNC AR ISBEROAL")
    log.info("=" * 60)

    sh = gsheets_get_or_create_spreadsheet()
    inicializar_pestañas(sh)

    # Precargar contactos para enriquecer cliente cuando solo viene contactId
    cargar_contactos_holded()

    crudas_inv = holded_get_invoices_income()
    crudas_rec = holded_get_credit_notes()
    if not crudas_inv and not crudas_rec:
        log.warning("[SYNC] No se han recibido facturas ni rectificativas. Sin cambios en Sheets.")
        return {"facturas": 0, "alertas": 0}

    # Marcar tipo y unir
    for inv in crudas_inv:
        inv["_doc_type"] = "invoice"
    for rec in crudas_rec:
        rec["_doc_type"] = "creditnote"

    # Identificar facturas originales canceladas por una rectificativa.
    # Holded puede usar varios nombres de campo: probamos en orden.
    facturas_anuladas_por_rec: set[str] = set()
    for rec in crudas_rec:
        original = (
            rec.get("rectifiedDocId")
            or rec.get("rectifyInvoiceId")
            or rec.get("relatedDocId")
            or rec.get("originalInvoiceId")
            or rec.get("invoiceId")
            or rec.get("parentId")
        )
        if original:
            facturas_anuladas_por_rec.add(str(original))
        else:
            # Algunos Holded tienen array `relatedDocuments`
            for r in rec.get("relatedDocuments") or []:
                rid = r.get("id") if isinstance(r, dict) else None
                if rid:
                    facturas_anuladas_por_rec.add(str(rid))

    if facturas_anuladas_por_rec:
        log.info(f"[SYNC] {len(facturas_anuladas_por_rec)} facturas serán marcadas Anuladas (tienen rectificativa)")

    crudas = crudas_inv + crudas_rec

    parseadas = []
    fallos = 0
    for inv in crudas:
        try:
            f = parse_invoice_metadata(inv)
            # Marcar como Anulada si tiene una rectificativa que la cancela
            if str(inv.get("id", "")) in facturas_anuladas_por_rec and f.get("estado_cobro") not in ("Borrador", "Rectificativa"):
                f["estado_cobro"] = "Anulada"
            parseadas.append(f)
        except Exception as e:
            fallos += 1
            log.error(f"[SYNC] Error parseando factura {inv.get('id', '?')}: {e}")

    log.info(f"[SYNC] Parseadas {len(parseadas)} facturas (fallos: {fallos})")

    # Resumen de estados crudos para diagnostico
    from collections import Counter
    estados_crudos = Counter(inv.get("status") for inv in crudas)
    log.info(f"[SYNC] Estados crudos de Holded: {dict(estados_crudos)}")
    estados_mapeados = Counter(f.get("estado_cobro") for f in parseadas)
    log.info(f"[SYNC] Estados mapeados: {dict(estados_mapeados)}")
    con_duedate = sum(1 for inv in crudas if inv.get("dueDate"))
    log.info(f"[SYNC] Facturas con dueDate de Holded: {con_duedate}/{len(crudas)}")

    # Diagnostico de campos de pago disponibles
    campos_pago = ("paid", "paymentsTotal", "paid_total", "paymentsPending", "paid_pending", "paid_at")
    presencia = {c: sum(1 for inv in crudas if inv.get(c) is not None) for c in campos_pago}
    log.info(f"[SYNC] Campos de pago presentes en respuesta: {presencia}")

    n_inferidos = asignar_hitos_por_orden(parseadas)
    if n_inferidos:
        log.info(f"[SYNC] Hitos asignados por orden cronologico: {n_inferidos}")

    # Normalizar: hito None -> "" para volcado en Sheets
    for f in parseadas:
        if f.get("hito") is None:
            f["hito"] = ""

    nuevas, actualizadas = upsert_facturas(sh, parseadas)
    log.info(f"[SYNC] Sheets: {nuevas} nuevas, {actualizadas} actualizadas")

    n_proyectos = recalcular_proyectos(sh, parseadas)
    log.info(f"[SYNC] Proyectos: {n_proyectos} agrupaciones")

    actualizar_dashboard(sh, parseadas, n_proyectos)

    n_alertas = check_and_send_alerts(parseadas)

    procesados = cargar_procesados()
    procesados[datetime.now().isoformat()] = {
        "facturas": len(parseadas),
        "nuevas": nuevas,
        "actualizadas": actualizadas,
        "alertas_email": n_alertas,
    }
    # Mantener solo las ultimas 30 entradas
    if len(procesados) > 30:
        keys_ord = sorted(procesados.keys())
        procesados = {k: procesados[k] for k in keys_ord[-30:]}
    guardar_procesados(procesados)

    log.info(f"[SYNC] Completado: {len(parseadas)} facturas procesadas, {n_alertas} alertas enviadas")
    log.info("=" * 60)
    return {"facturas": len(parseadas), "alertas": n_alertas, "nuevas": nuevas, "actualizadas": actualizadas}


def comando_estado(sh: gspread.Spreadsheet, id_presupuesto: str) -> str:
    try:
        ws = sh.worksheet(TAB_PROYECTOS)
        registros = ws.get_all_records()
    except WorksheetNotFound:
        return "Pestana Proyectos_Hitos no inicializada. Ejecuta primero un --sync."
    p = next((r for r in registros if r.get("id_presupuesto") == id_presupuesto), None)
    if not p:
        return f"No hay datos del proyecto {id_presupuesto} en Sheets."
    return (
        f"Proyecto: {p.get('id_presupuesto')}\n"
        f"Cliente: {p.get('cliente')}\n"
        f"Valor total: {p.get('valor_total_contrato')}\n"
        f"Hito 1: {p.get('hito_1_importe')} - {p.get('hito_1_estado')} (vence {p.get('hito_1_fecha_venc')})\n"
        f"Hito 2: {p.get('hito_2_importe')} - {p.get('hito_2_estado')} (vence {p.get('hito_2_fecha_venc')})\n"
        f"Hito 3: {p.get('hito_3_importe')} - {p.get('hito_3_estado')} (vence {p.get('hito_3_fecha_venc')})\n"
        f"Cobrado: {p.get('total_cobrado')} | Pendiente: {p.get('total_pendiente')} | Completado: {p.get('porcentaje_completado')}"
    )


def comando_alertas(sh: gspread.Spreadsheet) -> str:
    try:
        ws = sh.worksheet(TAB_FACTURAS)
        registros = ws.get_all_records()
    except WorksheetNotFound:
        return "Pestana Facturas_Emitidas no inicializada."
    activas = [r for r in registros if r.get("alerta") in (ALERTA_ROJA, ALERTA_AMARILLA)]
    if not activas:
        return "Sin alertas activas."
    lineas = [f"{r['alerta']} | {r['num_factura']} | {r['cliente']} | {r['importe_total']} | vence {r['fecha_vencimiento']}" for r in activas]
    return "\n".join(lineas)


def ejecutar_prompt_repl():
    """REPL interactivo para crear borradores y consultar estado."""
    sh = gsheets_get_or_create_spreadsheet()
    inicializar_pestañas(sh)
    cargar_contactos_holded()

    print("\n" + "=" * 60)
    print("AGENTE AR ISBEROAL - Modo interactivo")
    print("=" * 60)
    print("Comandos:")
    print("  crear borrador <texto>     Crea borrador en Holded a partir de prompt")
    print("  sync                       Ejecuta sincronizacion completa")
    print("  estado PRE002341           Muestra resumen del proyecto")
    print("  alertas                    Lista facturas con alerta activa")
    print("  salir                      Termina la sesion")
    print()

    while True:
        try:
            entrada = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not entrada:
            continue
        low = entrada.lower()

        if low in ("salir", "exit", "quit"):
            break

        if low == "sync":
            ejecutar_sync()
            continue

        if low == "alertas":
            print(comando_alertas(sh))
            continue

        if low.startswith("estado "):
            pre = entrada[7:].strip().upper()
            print(comando_estado(sh, pre))
            continue

        if low.startswith("crear borrador "):
            prompt_text = entrada[len("crear borrador "):].strip()
            try:
                resultado = create_draft_from_prompt(prompt_text, sh)
            except Exception as e:
                print(f"[ERROR] {e}")
                continue
            if not resultado.get("ok"):
                print(f"[ERROR] {resultado.get('error')}")
                if resultado.get("campos"):
                    print(f"        Campos extraidos: {resultado['campos']}")
                continue
            r = resultado["resumen"]
            print(f"[OK] Borrador creado en Holded")
            print(f"    Proyecto:   {r['id_presupuesto']}")
            print(f"    Hito:       {r['hito']} ({HITO_TEXTO.get(r['hito'], '?')} pago)")
            print(f"    Cliente:    {r['cliente']}")
            print(f"    Importe:    {formato_eur(r['importe'])}")
            print(f"    Nº Factura: {r['num_factura']}")
            print(f"    Estado:     Borrador")
            if resultado.get("aviso"):
                print(f"    [AVISO]    {resultado['aviso']}")
            # Resync inmediato para reflejar el borrador en Sheets
            try:
                ejecutar_sync()
            except Exception as e:
                print(f"[WARN] Sync post-creacion fallo: {e}")
            continue

        print("Comando no reconocido. Escribe 'salir' para terminar.")


def main():
    parser = argparse.ArgumentParser(description="Agente AR Isberoal (cuentas a cobrar)")
    parser.add_argument("--init",    action="store_true", help="Crea/inicializa el Spreadsheet y las 3 pestanas")
    parser.add_argument("--sync",    action="store_true", help="Sincroniza Holded -> Google Sheets + alertas")
    parser.add_argument("--prompt",  action="store_true", help="Modo REPL interactivo (crear borradores, etc.)")
    parser.add_argument("--verbose", action="store_true", help="Logging DEBUG")
    args = parser.parse_args()

    if args.verbose:
        global log
        log = configurar_logging(verbose=True)

    if not (args.init or args.sync or args.prompt):
        parser.print_help()
        return 0

    try:
        if args.init:
            sh = gsheets_get_or_create_spreadsheet()
            inicializar_pestañas(sh)
            print(f"[OK] Spreadsheet listo: https://docs.google.com/spreadsheets/d/{sh.id}")
        if args.sync:
            ejecutar_sync()
        if args.prompt:
            ejecutar_prompt_repl()
    except FileNotFoundError as e:
        log.error(f"[FATAL] {e}")
        return 2
    except RuntimeError as e:
        log.error(f"[FATAL] {e}")
        return 3
    except Exception as e:
        log.exception(f"[FATAL] Error inesperado: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
