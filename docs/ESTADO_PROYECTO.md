# ESTADO DEL PROYECTO - ISBEROAL ERP

Última actualización: 11/05/2026

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
