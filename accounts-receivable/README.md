# AGENTE AR ISBEROAL

## ROL Y CONTEXTO
Eres un ingeniero de software especializado en automatización financiera. 
Vas a construir un agente de gestión de cuentas a cobrar (AR) para 
Isberoal, una startup fotovoltaica española. El agente se conecta a 
Holded (ERP SaaS español) vía API REST y sincroniza las facturas 
emitidas a clientes en Google Sheets.

La empresa ya tiene un agente operativo que lee facturas de proveedores 
desde contabilidad@isberoal.com y las sube a Holded. Este nuevo agente 
es el flujo inverso: leer lo que Isberoal emite a sus clientes.

---

## OBJETIVO PRINCIPAL
Construir un agente Python que:
1. Lea facturas emitidas (estado: outstanding, paid, overdue) y borradores 
   (estado: draft) desde Holded API
2. Extraiga el número de hito (1, 2 o 3) y el ID de presupuesto 
   (formato PREXXXXXX) del texto de cada factura mediante regex + NLP
3. Sincronice toda la información en Google Sheets (upsert diario)
4. Permita crear borradores nuevos en Holded mediante un prompt 
   conversacional en lenguaje natural
5. Genere alertas de vencimiento automáticas

---

## STACK TECNOLÓGICO
- Lenguaje: Python 3.11+
- API principal: Holded API REST v1
  - Base URL: https://api.holded.com/api/invoicing/v1
  - Autenticación: header "key: 024fb7231d7dfb79eb04dfacc9cfcc9c"
  - Endpoints a usar:
    - GET  /invoices?type=income          → facturas emitidas
    - GET  /invoices/{id}                 → detalle de una factura
    - POST /invoices                      → crear borrador
    - PATCH /invoices/{id}               → actualizar borrador
- Google Sheets: biblioteca gspread + oauth2client
- Variables de entorno: python-dotenv
- Scheduling: APScheduler (sincronización diaria a las 08:00)
- Opcional para alertas: smtplib o requests (Telegram Bot API)

---

## ESTRUCTURA DE ARCHIVOS DEL PROYECTO

ar_agent/
├── main.py                  # Entrypoint: sincronización + CLI prompt
├── holded_client.py         # Clase HoldedClient con todos los métodos API
├── sheets_client.py         # Clase SheetsClient con métodos de lectura/escritura
├── invoice_parser.py        # Parser de hito, presupuesto y condiciones de pago
├── draft_creator.py         # Módulo de creación de borradores por prompt
├── alert_manager.py         # Lógica de alertas por vencimiento
├── config.py                # Configuración central (constantes, rutas)
├── .env                     # Variables de entorno (no subir a git)
├── .env.example             # Plantilla de variables de entorno
├── requirements.txt         # Dependencias
└── README.md                # Instrucciones de instalación y uso

---

## VARIABLES DE ENTORNO (.env)

HOLDED_API_KEY=tu_api_key_aqui
GOOGLE_SHEETS_CREDENTIALS_JSON=ruta/a/credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=id_del_spreadsheet
ALERT_EMAIL_FROM=contabilidad@isberoal.com
ALERT_EMAIL_TO=contabilidad@isberoal.com
ALERT_EMAIL_PASSWORD=password_smtp
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

---

## MÓDULO 1: holded_client.py

Implementa la clase HoldedClient con estos métodos:

```python
class HoldedClient:
    def get_all_issued_invoices(self) -> list[dict]
    # GET /invoices?type=income
    # Devuelve lista de todas las facturas emitidas incluyendo borradores
    # Paginar si hay más de 100 resultados

    def get_invoice_detail(self, invoice_id: str) -> dict
    # GET /invoices/{id}
    # Devuelve detalle completo incluyendo el campo 'notes' o 'desc'
    # donde está el texto del hito

    def create_draft_invoice(self, payload: dict) -> dict
    # POST /invoices
    # Crea un borrador. El payload debe incluir:
    # - contactId, date, notes, items (lista con desc, units, price, tax)
    # - status: 0 (draft en Holded)

    def update_invoice(self, invoice_id: str, payload: dict) -> dict
    # PATCH /invoices/{id}
    # Actualiza campos de una factura existente
```

Manejo de errores: reintentar 3 veces con backoff exponencial en 
errores 429 (rate limit) y 5xx. Loggear todos los errores.

---

## MÓDULO 2: invoice_parser.py

Función principal: parse_invoice_metadata(invoice: dict) -> dict

El campo a analizar es el texto de descripción/notas de la factura.
Formato típico del texto en las facturas de Isberoal:

  "Factura correspondiente al [primer/segundo/tercer y último] pago 
   del [X]% del Presupuesto [PREXXXXXX] consistente en: [detalle]"

Extraer:
- hito: int (1, 2 o 3)
  Mapeo:
    "primer pago"           → 1
    "segundo pago"          → 2  
    "tercer y último pago"  → 3
    "tercer pago"           → 3
  Normalizar texto: quitar acentos, pasar a minúsculas antes del match

- id_presupuesto: str (formato PRE + dígitos, ej: PRE002341)
  Regex: r'PRE\d+'

- porcentaje_hito: float (el % que aparece en el texto, ej: 30.0)
  Regex: r'(\d+(?:\.\d+)?)\s*%'

- fecha_vencimiento: date
  Lógica:
    Si paymentTerms de Holded = "contado" → fecha_emision
    En cualquier otro caso               → fecha_emision + 7 días
  
- estado_cobro: str
  Mapeo desde status de Holded:
    0 → "Borrador"
    1 → "Pendiente"
    2 → "Cobrada"  
    3 → "Vencida"

- alerta: str
  Lógica:
    Si estado = "Vencida"                    → "🔴 VENCIDA"
    Si dias_vencimiento <= 5 y no cobrada    → "🟡 PRÓXIMA"
    En cualquier otro caso                   → "🟢 OK"

Devolver dict con todos estos campos más los originales de Holded 
que se necesiten para Google Sheets.

---

## MÓDULO 3: sheets_client.py

El Google Sheets tendrá 3 pestañas. Implementar upsert por 
columna id_holded (si existe, actualizar; si no, insertar fila nueva).

### Pestaña 1: "Facturas_Emitidas"
Columnas en este orden exacto:
id_holded | num_factura | cliente | id_presupuesto | hito | 
fecha_emision | fecha_vencimiento | dias_vencimiento | 
importe_base | iva | importe_total | porcentaje_hito |
estado_holded | estado_cobro | alerta | notas

Nota: dias_vencimiento se recalcula en cada sync como 
(fecha_vencimiento - fecha_hoy).days

### Pestaña 2: "Proyectos_Hitos"
Columnas:
id_presupuesto | cliente | valor_total_contrato |
hito_1_importe | hito_1_estado | hito_1_fecha_venc |
hito_2_importe | hito_2_estado | hito_2_fecha_venc |
hito_3_importe | hito_3_estado | hito_3_fecha_venc |
total_cobrado | total_pendiente | porcentaje_completado

Esta pestaña se construye agrupando la pestaña Facturas_Emitidas 
por id_presupuesto. Un proyecto aparece aquí cuando tiene al menos 
una factura registrada.

### Pestaña 3: "Dashboard_AR"
Celdas clave (no tabla, sino KPIs en celdas nombradas):
- Total pendiente cobro (suma importe_total donde estado != Cobrada)
- Nº facturas vencidas
- Importe total vencido
- Nº facturas próximas a vencer (≤ 5 días)
- Importe próximo a vencer
- Proyectos activos (con hitos pendientes)
- Fecha última sincronización

Actualizar esta pestaña al final de cada sync.

---

## MÓDULO 4: draft_creator.py

Función: create_draft_from_prompt(prompt_text: str) -> dict

El agente recibe texto en lenguaje natural (puede venir de voz 
transcrita) y crea un borrador en Holded.

Ejemplos de prompts que debe entender:

  "Crea borrador del segundo hito del proyecto PRE002341 
   para cliente Ayuntamiento de Ribeira por 12.400€"

  "Nuevo borrador, tercer y último pago del PRE001892, 
   8.200€, cliente Endesa Renovables"

  "Primer hito PRE003012, Iberdrola, 45.000 euros"

Pasos internos:
1. Parsear el prompt con regex + lógica para extraer:
   - id_presupuesto (PRE + dígitos)
   - numero_hito (1, 2 o 3) desde "primer", "segundo", "tercer"
   - nombre_cliente (texto tras "cliente" o "para")
   - importe (número con punto o coma decimal, con o sin €)

2. Validar en Google Sheets (pestaña Proyectos_Hitos):
   - Si es hito 2: verificar que hito 1 esté en estado "Cobrada" 
     (si no, mostrar WARNING pero permitir continuar)
   - Si es hito 3: verificar que hito 2 esté en estado "Cobrada"
     (mismo comportamiento)

3. Construir el texto estándar de la factura:
   hito_texto = {1: "primer", 2: "segundo", 3: "tercer y último"}
   
   "Factura correspondiente al {hito_texto[hito]} pago del {pct}% 
    del Presupuesto {id_presupuesto} consistente en: 
    [Instalación sistema fotovoltaico según presupuesto]"

   Nota: el porcentaje se obtiene de la pestaña Proyectos_Hitos 
   si existe; si no, dejarlo como placeholder "[X]%"

4. Buscar contactId en Holded por nombre de cliente:
   GET /contacts?name={nombre_cliente}
   Usar el primer resultado. Si no encuentra, devolver error claro.

5. Crear el borrador en Holded via HoldedClient.create_draft_invoice()

6. Confirmar al usuario con resumen:
   "✅ Borrador creado en Holded
    Proyecto: PRE002341
    Hito: 2 (segundo pago)
    Cliente: Ayuntamiento de Ribeira  
    Importe: 12.400,00 €
    Nº Factura: [asignado por Holded]
    Estado: Borrador"

7. Sincronizar inmediatamente con Google Sheets

---

## MÓDULO 5: alert_manager.py

Función: check_and_send_alerts(invoices: list[dict]) -> None

Revisar diariamente tras la sincronización:
- Facturas con alerta 🔴 (vencidas y no cobradas)
- Facturas con alerta 🟡 (vencen en ≤ 5 días)

Si hay alguna, enviar email a ALERT_EMAIL_TO con:
- Asunto: "⚠️ Isberoal AR — X facturas requieren atención [fecha]"
- Cuerpo HTML con tabla de facturas afectadas
- Incluir: num_factura, cliente, importe_total, dias_vencimiento, alerta

No enviar email si no hay alertas activas.

---

## MÓDULO 6: main.py

Dos modos de ejecución:

### Modo sincronización (automático):
```bash
python main.py --sync
```
1. Llama a HoldedClient.get_all_issued_invoices()
2. Para cada factura, llama a invoice_parser.parse_invoice_metadata()
3. Llama a SheetsClient para upsert en las 3 pestañas
4. Llama a alert_manager.check_and_send_alerts()
5. Log resumen: "Sync completada: X facturas procesadas, Y alertas enviadas"

### Modo prompt interactivo (manual):
```bash
python main.py --prompt
```
Loop interactivo:

Comandos que debe reconocer:
- "crear borrador [texto]" → draft_creator.create_draft_from_prompt()
- "sync" → ejecutar sincronización manual
- "estado [PRE002341]" → mostrar resumen del proyecto en consola
- "alertas" → listar facturas con alerta activa
- "salir" → terminar

### Scheduling automático:
Configurar APScheduler para ejecutar --sync cada día a las 08:00 
hora de Madrid (Europe/Madrid).

---

## GOOGLE SHEETS — CONFIGURACIÓN INICIAL

Al ejecutar por primera vez, si el Spreadsheet está vacío, 
el agente debe:
1. Crear las 3 pestañas con sus cabeceras
2. Aplicar formato a la fila de cabecera (negrita, fondo gris)
3. Congelar la primera fila en cada pestaña
4. Configurar validación de datos en columna "alerta" 
   (valores: 🔴 VENCIDA / 🟡 PRÓXIMA / 🟢 OK)

Implementar función: sheets_client.initialize_spreadsheet()

---

## REQUISITOS DE CALIDAD

- Logging estructurado en todos los módulos (usar módulo logging 
  de Python, nivel INFO por defecto, DEBUG con flag --verbose)
- Manejo explícito de excepciones en todas las llamadas API
- El agente nunca debe crashear silenciosamente: capturar excepciones, 
  loggear y continuar con la siguiente factura
- Todas las fechas en formato DD/MM/YYYY en Google Sheets
- Todos los importes en formato europeo: 12.400,50 € en Sheets, 
  float internamente
- El archivo .env nunca debe subirse a git (.gitignore incluido)
- Incluir README.md con:
  - Instrucciones de instalación
  - Cómo obtener credenciales de Holded y Google
  - Cómo ejecutar en modo sync y modo prompt
  - Ejemplo de uso del modo interactivo

---

## ENTREGABLES ESPERADOS

1. Todos los archivos Python del proyecto completos y funcionales
2. requirements.txt con versiones fijadas
3. .env.example completo
4. README.md con instrucciones paso a paso
5. Script de inicialización del Sheets (puede ir en main.py --init)

---

## NOTAS ADICIONALES

- La API de Holded puede devolver el campo de descripción en 
  distintos campos según el tipo de factura: revisar 'desc', 
  'notes', 'items[0].desc' y 'concept' en el detalle de factura
- Los importes en Holded vienen en céntimos (int) o en euros (float): 
  verificar y normalizar
- El IVA estándar en España para instalaciones fotovoltaicas es 10% 
  (uso doméstico) o 21% (uso empresarial): no asumir, leer de Holded
- Holded identifica borradores con status=0; no confundir con 
  facturas rectificativas
- Si un proyecto tiene solo 1 o 2 hitos (contrato simplificado), 
  el sistema debe manejarlo sin errores