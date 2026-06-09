"""
Lectura read-only de facturas de venta en Holded (API v1).

Modulo reutilizable: SOLO lee y normaliza. No contiene logica de cobros ni de
tesoreria, para que ambos consumidores lo reutilicen sin reescribir nada.
SOLO hace peticiones GET. No escribe absolutamente nada en Holded.
"""

import os
from datetime import datetime

import requests

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Europe/Madrid")
except Exception:
    # En Windows zoneinfo necesita el paquete 'tzdata'. Sin el, se usa la hora
    # local del sistema (correcta en una maquina en Espana, pero no en la nube).
    _TZ = None

_BASE = "https://api.holded.com/api/invoicing/v1/documents/invoice"
_MAX_PAGINAS = 1000  # tope de seguridad anti-bucle


def _a_fecha(ts):
    """Convierte timestamp Unix de Holded a date. Devuelve None si no hay fecha."""
    if not ts:
        return None
    if _TZ is not None:
        return datetime.fromtimestamp(ts, _TZ).date()
    return datetime.fromtimestamp(ts).date()


def _norm(doc):
    """Normaliza un documento de Holded a una factura a nivel de cabecera."""
    return {
        "id": doc.get("id"),
        "es_borrador": bool(doc.get("draft")),
        "num_factura": doc.get("docNumber"),
        "cliente": doc.get("contactName") or "",
        "fecha_emision": _a_fecha(doc.get("date")),
        "fecha_vencimiento": _a_fecha(doc.get("dueDate")),
        "descripcion": doc.get("desc") or "",
        "base": round(float(doc.get("subtotal") or 0), 2),
        "iva": round(float(doc.get("tax") or 0), 2),
        "descuento": round(float(doc.get("discount") or 0), 2),
        "total": round(float(doc.get("total") or 0), 2),
        "cobrado": round(float(doc.get("paymentsTotal") or 0), 2),
        "pendiente": round(float(doc.get("paymentsPending") or 0), 2),
        "moneda": (doc.get("currency") or "eur").upper(),
        "tags": doc.get("tags") if isinstance(doc.get("tags"), list) else [],
        "status": doc.get("status"),
    }


def leer_facturas_venta(api_key=None, incluir_emitidas=True, incluir_borradores=True):
    """
    Lee todas las facturas de venta (docType 'invoice') paginando hasta el final.
    Devuelve una lista de dicts normalizados, uno por factura.
    """
    api_key = api_key or os.environ.get("HOLDED_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta HOLDED_API_KEY (variable de entorno o .env). "
            "Nunca la escribas en el codigo."
        )

    headers = {"key": api_key, "Accept": "application/json"}
    facturas = []
    vistos = set()

    for page in range(1, _MAX_PAGINAS + 1):
        r = requests.get(_BASE, headers=headers, params={"page": page}, timeout=30)
        r.raise_for_status()
        data = r.json()
        docs = data.get("documents") if isinstance(data, dict) else data
        if not docs:
            break

        nuevos = 0
        for d in docs:
            doc_id = d.get("id")
            if doc_id in vistos:
                continue  # algunas APIs repiten la ultima pagina; evitamos duplicar
            vistos.add(doc_id)
            nuevos += 1

            f = _norm(d)
            if f["es_borrador"] and not incluir_borradores:
                continue
            if not f["es_borrador"] and not incluir_emitidas:
                continue
            facturas.append(f)

        if nuevos == 0:
            break  # pagina sin documentos nuevos -> hemos llegado al final

    return facturas