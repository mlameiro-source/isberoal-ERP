# ESTADO DEL PROYECTO - ISBEROAL ERP

Última actualización: 13/05/2026

## Repositorio

* GitHub: [https://github.com/mlameiro-source/isberoal-ERP](https://github.com/mlameiro-source/isberoal-ERP)
* Cuenta: mlameiro-source
* Rama principal: main



## Carpetas originales (producción - NO tocar)

* Accounts Payable: G:\\Unidades compartidas\\01\_ISBEROAL Energy\\14\_Agentes\\Accounts-Payable\\files\\
* Accounts Receivable: G:\\Unidades compartidas\\01\_ISBEROAL Energy\\14\_Agentes\\Accounts-Receivable\\files\\



## Carpeta de desarrollo local

* C:\\Users\\Usuario\\proyectos\\isberoal-ERP
* C:\\Users\\Usuario\\test-railway-payable  (entorno aislado para pruebas headless / Railway)



## Stack

* Agentes: Python
* SuperApp: Next.js 15, Supabase, Prisma, Vercel
* Repo SuperApp: [https://github.com/iromay-coder/isberoal-app-interna](https://github.com/iromay-coder/isberoal-app-interna)



## Módulos

### Accounts Payable (facturas de gasto)

* Archivo principal: agente\_facturas.py
* Estado: EN PRODUCCIÓN corriendo en local + LISTO para Railway (modo headless validado)
* Función: lee correo, OCR facturas, imputa a Holded
* Pendiente: deploy en Railway con ISBEROAL\_SHADOW\_MODE=true, luego migrar de Holded a Supabase



### Accounts Receivable (facturas de cobro)

* Archivo principal: agente\_cobros.py
* Estado: EN PRODUCCIÓN corriendo en local
* Pendiente: revisar y conectar a Supabase



## Archivos sensibles (NUNCA subir a GitHub)

* .env
* credentials.json
* token.json
* client\_secret\_\*.json
* mensajes\_procesados.json
* facturas\_procesadas.json



## Decisiones tomadas

1. Agentes en Python separados de la SuperApp Next.js
2. Comunicación via API REST: agente → POST → SuperApp → Supabase
3. Despliegue agentes en Railway (pendiente)
4. Agente local sigue funcionando en producción mientras se desarrolla
5. Estrategia "shadow mode" para validar Railway sin riesgo de duplicados en Holded



## Próximos pasos (por orden)

1. Desplegar agente en Railway con ISBEROAL\_SHADOW\_MODE=true (modo shadow)
2. Validar coincidencia Railway vs producción local durante 5-7 días
3. Quitar shadow mode y coordinar con Ismael apagado del .bat local
4. Conectar agente a Supabase en lugar de Holded
5. Construir módulo ERP en la SuperApp (pantallas Next.js)



## Contexto SuperApp ISBEROAL

* URL: [https://isberoal-isberoal.vercel.app](https://isberoal-isberoal.vercel.app)
* Repo: iromay-coder/isberoal-app-interna
* Supabase proyecto: ISBEROAL-RRHH (sbgqykapjitjcpgmvnih, eu-west-1)
* Responsable ERP: Martín Lameiro ([mlameiro@isberoal.com](mailto:mlameiro@isberoal.com))



## Cómo retomar en una nueva conversación

Pegar este archivo completo al inicio del chat con el mensaje:
'Soy Martín Lameiro, retomo el desarrollo del ERP de ISBEROAL. Este es el estado del proyecto:'

## Sesión 08/05/2026 - Tarde

### Hecho

* Repo subido a GitHub correctamente
* Token Gmail antiguo revocado y regenerado por seguridad
* Agente local verificado funcionando con cuenta [mlameiro@isberoal.com](mailto:mlameiro@isberoal.com)



### Confirmado

* Agente autenticado con: [mlameiro@isberoal.com](mailto:mlameiro@isberoal.com)
* Lee correos enviados a: [contabilidad@isberoal.com](mailto:contabilidad@isberoal.com) (grupo donde está mlameiro)
* Sigue corriendo en local desde G:\\Unidades compartidas...\\Accounts-Payable\\files\\
* Próxima ejecución programada: lunes 9:00 AM



### Pendiente próxima sesión

1. Crear cuenta en Railway
2. Configurar deploy del agente accounts-payable
3. Generar token Gmail compatible con servidor (sin navegador)
4. Configurar variables de entorno en Railway
5. Programar cron a las 2:00 AM
6. Probar en modo --solo-xlsx antes de activar import a Holded
7. Coordinar desactivación del .bat local con Ismael cuando Railway esté operativo



## Sesión 11/05/2026 - Tarde

### Hecho

* Validación completa del modo headless en local antes de Railway:

  * Carpeta aislada `C:\\\\Users\\\\Usuario\\\\test-railway-payable\\\\` con copia de producción (Drive intacto)
  * venv con Python 3.13.7 + dependencias instaladas
  * Test de autenticación headless con GMAIL\_TOKEN\_JSON exitoso (sin abrir navegador)
  * Test de refresh automático de access\_token funcionando con el refresh\_token real
* App OAuth de Google diagnosticada: User type = Internal

  * Refresh tokens NO caducan a los 7 días (limitación de Testing no aplica)
  * Sin necesidad de verificación de scopes sensibles por parte de Google
* Implementado modo SHADOW para Railway:

  * Variable de entorno ISBEROAL\_SHADOW\_MODE=true fuerza solo\_xlsx + no\_holded
  * Permite ejecutar Railway en paralelo al agente local sin riesgo de duplicados
* Implementado logging condicional para Railway:

  * Si RAILWAY\_ENVIRONMENT está definida, logs solo a stdout (no a archivo)
  * En local se mantiene el FileHandler para histórico
* Test E2E con SHADOW\_MODE en correos reales:

  * 16 correos leídos, 13 ya procesados, 3 nuevos procesados
  * OCR de Claude correcto, renombrado de archivos correcto, XLSX generado
  * Holded NUNCA tocado: 0 llamadas a api.holded.com
* Commit subido a GitHub: 1042f06

  * accounts-payable/agente\_facturas.py modificado (+25/-0)
  * accounts-payable/.env.example creado (45 líneas)
  * .gitignore reorganizado por secciones (+47/-13)

### Confirmado

* token.json de producción funcional con refresh\_token vivo
* App OAuth en proyecto Google Cloud "Landing-Isberoal" (project number 765876116624)
* Producción NO ha sido tocada en toda la sesión:

  * Drive sigue intacto en G:...\\Accounts-Payable\\files\\
  * .bat local ejecutándose con su cron habitual
  * mensajes\_procesados.json de producción no modificado

### Pendiente próxima sesión

1. Crear cuenta en Railway (railway.app)
2. Conectar el repo isberoal-ERP a Railway
3. Configurar root directory: accounts-payable/
4. Variables de entorno en Railway:

   * HOLDED\_API\_KEY (copiar de .env de Drive)
   * ANTHROPIC\_API\_KEY (copiar de .env de Drive)
   * GMAIL\_TOKEN\_JSON (copiar contenido completo de token.json de Drive)
   * GOOGLE\_CREDENTIALS\_PATH=credentials.json
   * ISBEROAL\_SHADOW\_MODE=true (CRÍTICO: empezar siempre en shadow)
   * RAILWAY\_ENVIRONMENT: la define Railway automáticamente
5. Subir credentials.json como volume mount o variable (revisar la mejor forma)
6. Configurar cron a las 2:00 AM (Railway CRON\_SCHEDULE)
7. Validar ejecución manual desde dashboard de Railway
8. Comparar XLSX generado por Railway vs facturas importadas por agente local durante 5-7 días
9. Cuando coincida 100%: quitar ISBEROAL\_SHADOW\_MODE de Railway y coordinar con Ismael el apagado del .bat local

### Notas operativas

* El agente local sigue siendo la fuente de verdad hasta que Railway esté validado
* Carpeta C:\\Users\\Usuario\\test-railway-payable\\ se mantiene como entorno de desarrollo local
* Para futuros tests headless desde esa carpeta:

  * $env:GMAIL\_TOKEN\_JSON = Get-Content -Raw -Path token.json
  * $env:ISBEROAL\_SHADOW\_MODE = "true"
  * python agente\_facturas.py --dias 1

## Sesión 12/05/2026 - Tarde

### Hecho

- Deploy del agente accounts-payable en Railway COMPLETADO con éxito.
- Cuenta Railway creada con login GitHub, conectada al repo `mlameiro-source/isberoal-ERP`.
- Configuración del servicio `isberoal-ERP` en Railway:
  - Source: `mlameiro-source/isberoal-ERP`, branch `main`
  - Root Directory: `accounts-payable`
  - Builder: Nixpacks v1.41.0 (Railpack ofrecido pero Nixpacks acabó siendo el efectivo)
  - Custom Start Command: `python agente_facturas.py --dias 1`
  - Region: US West
- Variables de entorno configuradas:
  - `HOLDED_API_KEY` (copiada del .env de Drive)
  - `ANTHROPIC_API_KEY` (copiada del .env de Drive)
  - `GMAIL_TOKEN_JSON` (contenido completo de token.json de Drive, JSON aplanado a una línea)
  - `ISBEROAL_SHADOW_MODE=true`
- Primer deploy falló por "No start command could be found" → resuelto añadiendo el Custom Start Command.
- Segundo deploy: build OK, deploy OK, post-deploy OK, servicio ACTIVE.

### Validado en producción Railway (primer arranque)

- `[OK] Credenciales Gmail cargadas desde variable de entorno` (sin navegador, sin token.json en disco)
- `[OK] Conectado a Gmail correctamente`
- `[WARNING] [SHADOW MODE] Activo. No se importará a Holded. Solo se generará XLSX.`
- `[CORREO] Encontrados 26 correos con facturas`
- `[NUEVOS] 26 mensajes por procesar` (esperado: Railway no comparte mensajes_procesados.json con local)
- `POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"` (OCR funcionando)
- Lógica de discriminación factura/albarán operativa.
- **CERO llamadas a `api.holded.com`** confirmado en los logs.
- Producción local intacta: el .bat local sigue corriendo con su cron habitual, Drive sin modificar.

### Notas técnicas de la sesión

- Anomalía menor con PowerShell + portapapeles: `Set-Clipboard` y `| clip` retornaban 2 caracteres en vez del JSON completo, pero el portapapeles real del sistema funcionaba bien (validado pegando en Notepad vacío). El JSON entró correcto en Railway.
- El archivo temporal `_token_temp.txt` del escritorio se borró al finalizar.
- Warning `file_cache is only supported with oauth2client<4.0.0` es ignorable (de google-api-python-client, sin impacto).

### Pendiente próxima sesión / inminente

1. Configurar Cron Schedule en Railway para validación recurrente:
   - Próxima ejecución programada manualmente para hoy ~16:00 CEST (= 14:00 UTC en cron).
   - Una vez validado el primer cron run, ajustar a `0 0 * * *` (2:00 UTC = 4:00 CEST) o el horario definitivo.
2. Comparar XLSX generado por Railway vs facturas importadas por agente local durante 5-7 días.
3. Cuando coincidan 100%: quitar `ISBEROAL_SHADOW_MODE` de Railway y coordinar con Ismael el apagado del .bat local.
4. Tras validación: migrar de Holded a Supabase como destino final del agente.
5. Decisión pendiente para más adelante: storage persistente para los XLSX generados en Railway (S3, Drive API, o Supabase Storage).

### Pendiente sin urgencia

- Renombrar el proyecto Railway de `empathetic-illumination` a algo descriptivo (ej. `isberoal-erp-agents`).
- Considerar migrar de Nixpacks (deprecated) a Railpack en una sesión futura.

### Sesión 12/05/2026 - Tarde (continuación: cron schedule y validación adicional)
 
#### Hecho
 
- Cron Schedule configurado en Railway → ajustado finalmente a `0 3 * * *` (3:00 UTC = 5:00 CEST).
- Primera configuración fue `30 15 * * *` (15:30 UTC = 17:30 CEST) pero Railway lo saltó a "tomorrow" porque ya eran las 16:30+ cuando se aplicó.
- Reconfigurado a 5:00 CEST para que la primera ejecución automática del cron coincida con la mañana siguiente.
- Botón `Run now` ejecutado manualmente como prueba del cron infrastructure → resultado: 2 entradas en Recent Executions, una de 4m 37s (ejecución completa de los 26 correos) y otra de 7s (probable duplicado de Railway al usar Run now). Ambas en SHADOW MODE confirmado.
- Verificado en la nueva pestaña **Cron Runs** de Railway:
  - Estado del servicio pasa de "Active 24/7" a "Ready" (esperando cron).
  - Tras Run now: tarjeta muestra "Last run succeeded".
  - Próxima ejecución: mañana 5:00 CEST automática.
#### Incidente menor durante la sesión: cambio accidental a Railpack y reversión
 
- Al editar el cron, Railway mostró el Builder actual como **Railpack** marcado como "Default", pero los logs del primer build exitoso confirmaron que el build real se hizo con **Nixpacks v1.41.0**. Hubo confusión en la UI sobre qué builder estaba activo realmente.
- Se cambió accidentalmente el Builder a Railpack a mitad de sesión.
- Decisión: **revertir a Nixpacks** para no introducir variables nuevas la noche previa a la primera ejecución automática del cron, dado que con Nixpacks ya teníamos 3 ejecuciones validadas.
- Builder final: Nixpacks (Deprecated). La migración a Railpack queda formalmente postpuesta a una sesión específica con tiempo de validar.
#### Hallazgo informativo: Serverless no disponible con cron
 
- Captura de Railway: **"Serverless is not available for services that have a cron schedule."**
- No podemos activar Serverless en este servicio. No es problema: el coste de un cron diario es mínimo. Decisión cerrada, no requiere acción.
#### Estado al cerrar la sesión
 
- Servicio Railway `isberoal-ERP`: **Ready**
- Builder: Nixpacks v1.41.0
- Custom Start Command: `python agente_facturas.py --dias 1`
- Cron: `00 03 * * *` (5:00 CEST diario)
- Variables: HOLDED_API_KEY, ANTHROPIC_API_KEY, GMAIL_TOKEN_JSON, ISBEROAL_SHADOW_MODE=true
- Last run: succeeded (Run now manual de las 17:33 CEST, duración 4m 37s)
- Next run: mañana 13/05/2026 a las 5:00 CEST (automático)
- Producción Drive: intacta, sin cambios.
#### Pendiente al llegar a la oficina el 13/05/2026
 
1. Verificar en Railway → Cron Runs → Recent Executions que apareció una nueva entrada con timestamp 5:00 CEST y estado Success.
2. Click en View logs y confirmar:
   - `[OK] Credenciales Gmail cargadas desde variable de entorno`
   - `[WARNING] [SHADOW MODE] Activo`
   - Sin errores ni Tracebacks al final
   - Cero llamadas a `api.holded.com`
3. Si OK: el cron funciona en automático. Empezar oficialmente la ventana de validación shadow de 5-7 días.
4. Si falla: capturar logs y diagnosticar.

## Sesión 13/05/2026 - Mañana (validación cron automático + inicio ventana shadow)
 
### Hecho
 
- Al llegar a la oficina a las 8:00 CEST se comprobó en Railway → Cron Runs que el primer cron automático se había ejecutado correctamente.
- Detalles de la ejecución del 13/05/2026:
  - **Timestamp inicio**: 05:02:07 CEST (cron disparado puntual, 2s de margen sobre las 5:00 UTC = 5:00 CEST con horario CEST→UTC)
  - **Estado final**: Completed (en verde)
  - **Duración**: 1m 36s (mucho más rápido que las ejecuciones de ayer porque procesa solo los correos nuevos del último día, no los 26 acumulados iniciales)
  - **Correos encontrados**: 10 (vs 26 ayer en la primera ejecución)
  - **Próxima ejecución programada**: 14/05/2026 05:00 CEST automática
### Validado en logs del primer cron automático
 
- `[WARNING] [SHADOW MODE] Activo. No se importará a Holded. Solo se generará XLSX.`
- `[OK] Credenciales Gmail cargadas desde variable de entorno` (refresh_token sigue válido tras ~15h)
- `[OK] Conectado a Gmail correctamente`
- `[CORREO] Encontrados 10 correos con facturas`
- `[NUEVOS] 10 mensajes por procesar`
- `[DESCARGA] 3316-INVOICE.pdf` y otros adjuntos procesados correctamente
- `POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"` (OCR Claude funcionando)
- `[OCR] FACTURA DN2026692 - Shenzhen Jiahang Tongda Supply Chain Co., Ltd.` (extracción de proveedor + número correcta)
- `[RENOMBRADO] 20260512_FG_Shenzhen_Jiahang_Tongda_Supply_EXPRESS_CHARGE.pdf` (lógica de renombrado operativa)
- **Cero llamadas a `api.holded.com`** confirmado.
### Hito conseguido
 
Sistema completo funcionando en producción cloud:
- Cron diario automático a las 5:00 CEST.
- Contenedor arranca desde frío, ejecuta, se apaga.
- Autenticación Gmail vía refresh_token sin intervención humana.
- OCR + lógica de discriminación factura/albarán + renombrado funcionando.
- Producción local (Drive) intacta y operando en paralelo como fuente de verdad.
### Plan de validación shadow (en curso, 13-19/05/2026)
 
- **Duración**: 7 días (cubrir ciclo semanal completo, incluido el lunes que suele tener pico de correos atrasados del fin de semana).
- **Método**: cada mañana, Railway → Cron Runs → entrar al run de las 5:00 CEST → contar `[CORREO] Encontrados X correos con facturas` → comparar con número de facturas importadas por agente local en Holded esa misma noche.
- **Apuntar en una hoja simple**: fecha + nº correos Railway + nº facturas Holded.
- **Sin storage persistente**: el XLSX que genera Railway es efímero (se borra al apagarse el contenedor). Validación se hace solo con logs. Decisión consciente: simplicidad > exhaustividad en esta fase.
### Criterios para considerar "OK" durante la ventana
 
- Mismos correos detectados por ambos agentes (o diferencias explicables por `mensajes_procesados.json` separados).
- Cero errores ni Tracebacks en los logs de Railway.
- Mismos proveedores extraídos en logs `[OCR] FACTURA X - PROVEEDOR Y`.
### Banderas rojas que detendrían la validación
 
- Run de Railway no aparece o aparece "Failed" algún día.
- Railway detecta 0 correos cuando el agente local detectó algunos (búsqueda Gmail rota).
- Diferencias grandes y sistemáticas en proveedores o datos extraídos.
### Pendiente al cerrar la ventana shadow (~19-20/05/2026)
 
1. Si todo OK durante 7 días: coordinar con Ismael el momento del switch.
2. Quitar `ISBEROAL_SHADOW_MODE` de Railway (o ponerla a `false`).
3. Apagar el `.bat` local del Drive en la máquina de la oficina.
4. Railway pasa a ser el único agente, importando a Holded en automático.
5. Luego: migración de Holded a Supabase como destino final del agente (sesión aparte). 

## Sesión 13/05/2026 - Tarde (cotejo Railway-vs-local y revisión de código)

### Hecho

Cotejo formal Railway-vs-local del 13/05/2026 con coincidencia 100% en clasificación, número de factura y proveedor.

- Railway (05:02 CEST) y local (10:51 CEST) detectaron los mismos 10 correos en Gmail.
- Los 3 mensajes que el local procesó como nuevos coincidieron al 100% con la clasificación que hizo Railway:
  - `19e1d12fe01a0c54` -> FACTURA DN2026692 - Shenzhen Jiahang Tongda Supply Chain Co., Ltd. (importada a Holded por local, 425.65 EUR)
  - `19e1c8ee950ed374` -> ALBARAN AL/830 - PESADO BARBANZA, S.L.U. (descartado correctamente en ambos)
  - `19e1c070ea0b8b8e` -> ALBARAN 617002554 - SONEPAR BOIRO (descartado correctamente en ambos)
- Los otros 7 correos (que el local tenía como ya procesados en su `mensajes_procesados.json`) Railway los procesó desde cero (porque arranca con registro vacío) y los clasificó coherentemente: 2 facturas adicionales (FURGONET BARBANZA 0000001515, Anthropic Ireland 9BF0758D-1992174), 4 albaranes y 1 recibo, todos correctamente descartados.
- En Railway funcionó la deduplicación intra-lote: dos correos con la misma factura FURGONET se detectaron y el segundo se marcó como `[DUPLICADO] ya procesada en este lote`.
- Cero errores, cero Tracebacks, cero llamadas a `api.holded.com` desde Railway.

Revisión de código - rama "no shadow" de `agente_facturas.py`

- Comprobado el flujo de `ISBEROAL_SHADOW_MODE` (líneas 821-826): si la variable existe y vale exactamente `"true"` (cualquier capitalización), fuerza `solo_xlsx=True` e `importar_holded=False`. En cualquier otro caso (variable ausente, `"false"`, `""`, etc.) la rama no se ejecuta y se queda con los defaults `solo_xlsx=False, importar_holded=True`.
- La condición que dispara la importación real a Holded está en la línea 920: `if importar_holded and not solo_xlsx`.
- Trampa de seguridad detectada: el comportamiento por defecto del agente sin variables de entorno es importar a Holded. Si en el futuro alguien borrase accidentalmente todas las vars en Railway, el agente importaria sin avisar. No es urgente, pero queda anotado para un refactor futuro (invertir el default a "shadow por defecto, hay que poner explicitamente `false` para producción").
- Decisión para el switch: cambiar `ISBEROAL_SHADOW_MODE` de `true` a `false` (Opción B), no eliminar la variable. Razón: deja constancia visual en Railway de que existe el modo y de que está apagado, y permite reactivarlo cambiando un valor en vez de tener que recordar el nombre de la variable.

Revisión de código - manejo de `mensajes_procesados.json`

- Localizada la lógica completa: `cargar_procesados` (líneas 776-781), `guardar_procesados` (784-787), `marcar_procesado` (790-795), `ya_procesado` (798-800). El archivo se carga al inicio (línea 829), se usa para filtrar mensajes duplicados (línea 842) y se escribe a disco tras procesar cada mensaje (líneas 904-905).
- Ruta del archivo (línea 67): `PROCESADOS_PATH = BASE_DIR / "mensajes_procesados.json"`. En local apunta al Drive (persistente). En Railway apuntaria a `/app/accounts-payable/mensajes_procesados.json`, que es sistema de archivos efimero: el archivo se crea durante el run y desaparece al apagarse el contenedor.

### Bloqueo identificado para el switch a producción

No se puede quitar SHADOW MODE en el estado actual sin riesgo real de duplicados en Holded.

- Railway corre con `--dias 1` y arranca cada vez con el registro de mensajes procesados vacío.
- En los datos del 13/05 ya vimos el escenario: Railway detectó como "nuevas" 3 facturas (Shenzhen, FURGONET, Anthropic) de las cuales 2 ya estaban en Holded desde sesiones previas del agente local. Si ayer no hubieramos estado en SHADOW, Railway habria duplicado esas 2 facturas.
- Hay además un riesgo adicional dia-a-dia: si la query Gmail `--dias 1` no aplica un corte estricto a las últimas 24h y un correo puede aparecer en la búsqueda dos dias seguidos, Railway lo reprocesaria sin tener registro de haberlo hecho ya.

### Decisión: Opción A (Volume persistente en Railway) para la próxima sesión

Tras evaluar 3 alternativas:

- **Opción A - Volume en Railway**: montar un volumen persistente en una ruta tipo `/data`, parametrizar `PROCESADOS_PATH` via variable de entorno, y sembrar el volumen con el `mensajes_procesados.json` actual del Drive.
- **Opción B - Labels de Gmail**: marcar correos procesados con un label en Gmail. Solución más limpia pero requiere modificar código, ampliar scope OAuth y regenerar token.
- **Opción C - Consultar Holded antes de importar**: pesado en llamadas, hay que rehacerlo cuando migremos a Supabase.

Elegida Opción A para desbloquear el switch sin entrar en refactor del agente. Opción B queda como tarea futura preferible antes de la migración a Supabase.

Corrección importante: la Opción A no es 100% "infra sin tocar código". Requiere un cambio mínimo en línea 67 de `agente_facturas.py` para parametrizar la ruta del JSON via variable de entorno (con fallback al path actual del Drive, para no romper el agente local).

### Estado al cerrar la sesión

- Railway `isberoal-ERP`: Ready, SHADOW MODE activo, cron 00 03 * * * (5:00 CEST).
- Cotejo Railway vs local del 13/05: 100% coincidencia en clasificación.
- Código del agente: revisado y entendido. Cambio mínimo pendiente para la próxima sesión (parametrizar `PROCESADOS_PATH`).
- Plan de switch: a la espera de implementar Volume persistente en Railway.
- Producción Drive: intacta, agente local sigue siendo la fuente de verdad.

### Pendiente próxima sesión

1. Avisar a Ismael Romay del switch planificado (notificación, no negociación).
2. Implementar Opción A:
   - Crear Volume en Railway y montarlo en `/data`.
   - Modificar línea 67 de `agente_facturas.py` para usar variable de entorno `PROCESADOS_PATH` con fallback al path actual.
   - Añadir variable `PROCESADOS_PATH=/data/mensajes_procesados.json` en Railway.
   - Commit + push + redeploy.
   - Sembrar el Volume con el `mensajes_procesados.json` actual del Drive (método a evaluar: SSH al contenedor, script bootstrap, o subida vía Railway CLI).
3. Validar en SHADOW que el Volume funciona: tras el siguiente cron, el JSON debe persistir y Railway debe saltarse los correos ya marcados.
4. Switch a producción: cambiar `ISBEROAL_SHADOW_MODE=true` -> `false`. Run now. Verificar import a Holded de los nuevos y NO reimport de los antiguos.
5. Desactivar la tarea programada de Windows del `.bat` local (no borrar el archivo, solo desactivar el schedule). Dejarlo unos dias por si toca rollback.
6. Documentar el switch en ESTADO_PROYECTO.md.

### Pendiente sin urgencia (sin cambios respecto a sesiones anteriores)

- Renombrar el proyecto Railway de `empathetic-illumination` a algo descriptivo.
- Migrar Nixpacks -> Railpack en una sesión específica.
- Revisar el agente `accounts-receivable` (`agente_cobros.py`), que también corre en local sin tocar.
- Storage persistente de los XLSX generados en Railway (recomendación: Drive API, antes de Supabase).
- Refactor futuro: invertir el default de SHADOW_MODE para que el comportamiento sin variables de entorno sea seguro (no importar a Holded).

## Sesion 13/05/2026 - Tarde-Noche (Volume Railway persistente + siembra + validacion)

### Hecho

Implementacion completa de Volume persistente en Railway para resolver el bloqueo del switch a produccion identificado en la sesion del 13/05 tarde.

- Codigo del agente parametrizado: linea 67 de `agente_facturas.py` lee ahora `PROCESADOS_PATH` de variable de entorno con fallback al path actual. Cambio compatible hacia atras: el agente local sigue funcionando sin definir la variable.
- Commits aplicados: `a37a30d feat(accounts-payable): parametrizar PROCESADOS_PATH via env var para Volume Railway` y `bfdac51 chore: ignorar mensajes_procesados_seed.json`.
- Volume creado en Railway: `isberoal-erp-volume`, montado en `/data`, 5 GB.
- Variable `PROCESADOS_PATH=/data/mensajes_procesados.json` anadida en Railway.
- Railway CLI instalado en local (v4.58.0), vinculado al servicio. Par de claves SSH ed25519 generado y registrado con nombre `railway-cli-mlameiro-laptop`.
- Seed del Volume: copia limpia (sin BOM, LF) del `mensajes_procesados.json` del Drive subida via SSH+stdin con 22273 bytes y 181 mensajes.

### Validado

Run manual de las 17:43 CEST tras Deploy con Start Command revertido y variable nueva:

- Agente arranca OK, SHADOW MODE activo.
- `[CORREO] Encontrados 17 correos` -> `[DUPLICADOS] 10 mensajes ya procesados (saltados)` (lectura desde `/data` confirmada) -> `[NUEVOS] 7 mensajes por procesar`.
- 2 facturas reales detectadas (Eleven Labs HVX7QBVE-0002, Eminza 7497670-1) + 5 descartes correctos.
- Cero llamadas a `api.holded.com`. Salida limpia. Duracion 1m 14s.

Verificacion de persistencia tras el run (SSH al Volume con Start Command temporal `tail -f /dev/null`):

- Archivo `/data/mensajes_procesados.json` actualizado a las 17:45, 23078 bytes (+805 vs seed).
- 188 mensajes en total (181 iniciales + 7 procesados).
- Los 7 IDs nuevos del run estan todos presentes en el JSON. Persistencia confirmada end-to-end.

### Incidentes

- Manipulacion del BOM en PowerShell rompio dos veces archivos durante la sesion (linea 67 del .py y primer intento de seed). Resuelto en ambos casos restaurando desde git / regenerando, y aplicando los cambios via `System.IO.File::WriteAllText` con `UTF8Encoding(false)` en lugar de `Set-Content -Encoding UTF8`. Lección: en Windows PowerShell 5.1, para escritura UTF-8 sin BOM SIEMPRE usar la API .NET, nunca `Set-Content -Encoding UTF8`.
- `ConvertFrom-Json` de PowerShell dio falso negativo validando un JSON intermedio que Python parseaba bien. Para validar JSONs en adelante usar Python directamente.

### Estado al cerrar la sesion

- Railway `isberoal-ERP`: Custom Start Command revertido a `python agente_facturas.py --dias 1`, deployment en curso al cierre. Variables: 5 (incluida `PROCESADOS_PATH`). SHADOW MODE activo. Cron `00 03 * * *`.
- Volume `isberoal-erp-volume` en `/data` con `mensajes_procesados.json` (188 mensajes).
- Codigo en main: HEAD bfdac51.
- Produccion Drive: intacta. Agente local sigue siendo fuente de verdad.
- Railway CLI y claves SSH operativas en local.

### Pendiente proxima sesion

1. Verificar el cron natural de las 5:00 CEST del 14/05: en logs debe aparecer `[DUPLICADOS] >= 7 mensajes ya procesados` correspondientes a los 7 del run del 13/05. Si OK, persistencia entre runs reales del cron confirmada.
2. Avisar a Ismael Romay del switch planificado.
3. Switch a produccion: `ISBEROAL_SHADOW_MODE=true` -> `false` en Railway. Run now. Verificar import de nuevos a Holded sin reimport de los 188 ya marcados.
4. Desactivar tarea programada del .bat local (no borrar archivo, solo desactivar schedule). Dejar unos dias por si rollback.
5. Documentar el switch.
6. Borrar `mensajes_procesados_seed.json` del directorio local (ya esta en .gitignore).

### Pendiente sin urgencia

- Renombrar proyecto Railway de `empathetic-illumination`.
- Migrar Nixpacks -> Railpack.
- Revisar `agente_cobros.py`.
- Storage persistente de XLSX en Railway.
- Refactor: invertir default de SHADOW_MODE para que el comportamiento sin variables sea seguro.
- Opcion B (labels Gmail) como alternativa mas limpia que el Volume, antes de migracion a Supabase.
