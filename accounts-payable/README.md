# Agente de Facturas de Compra - ISBEROAL

Automatiza la lectura de facturas de proveedores desde Gmail, extrae los datos
con inteligencia artificial y los importa en Holded.

---

## Requisitos previos

- Python 3.10 o superior
- Cuenta en Google Cloud Console (gratis)
- API Key de Holded
- API Key de Anthropic (Claude)

---

## Instalación

### 1. Instalar dependencias

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 \
            google-api-python-client anthropic python-dotenv \
            pymupdf pillow requests pandas
```

### 2. Configurar credenciales de Google (Gmail)

1. Ve a https://console.cloud.google.com
2. Crea un proyecto nuevo (ej: "Agente Facturas Isberoal")
3. Activa la **Gmail API**: APIs y servicios > Biblioteca > Gmail API > Activar
4. Crea credenciales OAuth 2.0:
   - APIs y servicios > Credenciales > Crear credenciales > ID de cliente OAuth
   - Tipo: **Aplicación de escritorio**
   - Descarga el JSON y guárdalo como `credentials.json` en la carpeta del agente
5. En "Pantalla de consentimiento OAuth" añade tu email como usuario de prueba

### 3. Configurar el archivo .env

```bash
cp .env.ejemplo .env
```

Edita `.env` y rellena:
- `HOLDED_API_KEY`: Ve a Holded > Configuración > API
- `ANTHROPIC_API_KEY`: Ve a https://console.anthropic.com

### 4. Primera ejecución (autenticación Gmail)

La primera vez que ejecutes el agente se abrirá el navegador para que
autorices el acceso a Gmail. Solo ocurre una vez.

```bash
python agente_facturas.py
```

---

## Uso

### Ejecución básica (últimos 7 días)
```bash
python agente_facturas.py
```

### Buscar en los últimos 30 días
```bash
python agente_facturas.py --dias 30
```

### Solo generar el CSV (sin importar en Holded)
```bash
python agente_facturas.py --solo-csv
```

### Sin importar en Holded (solo descarga y renombra facturas)
```bash
python agente_facturas.py --no-holded
```

---

## Estructura de carpetas

```
agente_facturas/
├── agente_facturas.py     ← Script principal
├── .env                   ← Tus credenciales (NO compartir)
├── credentials.json       ← Credenciales Google (NO compartir)
├── token.json             ← Token Gmail (se genera automáticamente)
├── Facturas_de_gasto/     ← PDFs descargados y renombrados
├── csv_output/            ← CSVs generados para Holded
└── logs/                  ← Registro de ejecuciones
```

---

## Automatización (ejecución diaria)

### En Windows (Programador de tareas)
1. Abre "Programador de tareas"
2. Crear tarea básica > Diariamente a las 8:00
3. Acción: Iniciar programa
   - Programa: `python`
   - Argumentos: `C:\ruta\al\agente_facturas.py`

### En Mac/Linux (cron)
```bash
# Ejecutar cada día a las 8:00
crontab -e
0 8 * * * /usr/bin/python3 /ruta/al/agente_facturas.py
```

---

## Formato de nombre de archivos

Las facturas se renombran automáticamente con el formato:

```
AAAAMMDD_FG_Proveedor_descripcion.pdf
```

Ejemplo: `20260413_FG_Alro_Maquinaria_reparacion_obra.pdf`

---

## Solución de problemas

**Error de autenticación Gmail**: Borra `token.json` y vuelve a ejecutar.

**Factura no reconocida**: El archivo se guarda como `ERROR_nombrearchivo.pdf`
en la carpeta `Facturas_de_gasto/` para revisión manual.

**Error en Holded**: Revisa los logs en `logs/agente_YYYYMMDD.log`
y el CSV en `csv_output/` para importar manualmente.
