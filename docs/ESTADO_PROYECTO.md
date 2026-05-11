# ESTADO DEL PROYECTO - ISBEROAL ERP

Última actualización: 11/05/2026

## Repositorio

- GitHub: <https://github.com/mlameiro-source/isberoal-ERP>
- Cuenta: mlameiro-source
- Rama principal: main


## Carpetas originales (producción - NO tocar)

- Accounts Payable: G:\Unidades compartidas\01_ISBEROAL Energy\14_Agentes\Accounts-Payable\files\
- Accounts Receivable: G:\Unidades compartidas\01_ISBEROAL Energy\14_Agentes\Accounts-Receivable\files\


## Carpeta de desarrollo local

- C:\Users\Usuario\proyectos\isberoal-ERP
- C:\Users\Usuario\test-railway-payable  (entorno aislado para pruebas headless / Railway)


## Stack

- Agentes: Python
- SuperApp: Next.js 15, Supabase, Prisma, Vercel
- Repo SuperApp: <https://github.com/iromay-coder/isberoal-app-interna>


## Módulos

### Accounts Payable (facturas de gasto)

- Archivo principal: agente_facturas.py
- Estado: EN PRODUCCIÓN corriendo en local + LISTO para Railway (modo headless validado)
- Función: lee correo, OCR facturas, imputa a Holded
- Pendiente: deploy en Railway con ISBEROAL_SHADOW_MODE=true, luego migrar de Holded a Supabase


### Accounts Receivable (facturas de cobro)

- Archivo principal: agente_cobros.py
- Estado: EN PRODUCCIÓN corriendo en local
- Pendiente: revisar y conectar a Supabase


## Archivos sensibles (NUNCA subir a GitHub)

- .env
- credentials.json
- token.json
- client_secret_*.json
- mensajes_procesados.json
- facturas_procesadas.json


## Decisiones tomadas

1. Agentes en Python separados de la SuperApp Next.js
2. Comunicación via API REST: agente → POST → SuperApp → Supabase
3. Despliegue agentes en Railway (pendiente)
4. Agente local sigue funcionando en producción mientras se desarrolla
5. Estrategia "shadow mode" para validar Railway sin riesgo de duplicados en Holded


## Próximos pasos (por orden)

1. Desplegar agente en Railway con ISBEROAL_SHADOW_MODE=true (modo shadow)
2. Validar coincidencia Railway vs producción local durante 5-7 días
3. Quitar shadow mode y coordinar con Ismael apagado del .bat local
4. Conectar agente a Supabase en lugar de Holded
5. Construir módulo ERP en la SuperApp (pantallas Next.js)


## Contexto SuperApp ISBEROAL

- URL: <https://isberoal-isberoal.vercel.app>
- Repo: iromay-coder/isberoal-app-interna
- Supabase proyecto: ISBEROAL-RRHH (sbgqykapjitjcpgmvnih, eu-west-1)
- Responsable ERP: Martín Lameiro (<mlameiro@isberoal.com>)


## Cómo retomar en una nueva conversación

Pegar este archivo completo al inicio del chat con el mensaje:
'Soy Martín Lameiro, retomo el desarrollo del ERP de ISBEROAL. Este es el estado del proyecto:'

## Sesión 08/05/2026 - Tarde

### Hecho

- Repo subido a GitHub correctamente
- Token Gmail antiguo revocado y regenerado por seguridad
- Agente local verificado funcionando con cuenta <mlameiro@isberoal.com>


### Confirmado

- Agente autenticado con: <mlameiro@isberoal.com>
- Lee correos enviados a: <contabilidad@isberoal.com> (grupo donde está mlameiro)
- Sigue corriendo en local desde G:\Unidades compartidas...\Accounts-Payable\files\
- Próxima ejecución programada: lunes 9:00 AM


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

- Validación completa del modo headless en local antes de Railway:
  - Carpeta aislada `C:\Users\Usuario\test-railway-payable\` con copia de producción (Drive intacto)
  - venv con Python 3.13.7 + dependencias instaladas
  - Test de autenticación headless con GMAIL_TOKEN_JSON exitoso (sin abrir navegador)
  - Test de refresh automático de access_token funcionando con el refresh_token real
- App OAuth de Google diagnosticada: User type = Internal
  - Refresh tokens NO caducan a los 7 días (limitación de Testing no aplica)
  - Sin necesidad de verificación de scopes sensibles por parte de Google
- Implementado modo SHADOW para Railway:
  - Variable de entorno ISBEROAL_SHADOW_MODE=true fuerza solo_xlsx + no_holded
  - Permite ejecutar Railway en paralelo al agente local sin riesgo de duplicados
- Implementado logging condicional para Railway:
  - Si RAILWAY_ENVIRONMENT está definida, logs solo a stdout (no a archivo)
  - En local se mantiene el FileHandler para histórico
- Test E2E con SHADOW_MODE en correos reales:
  - 16 correos leídos, 13 ya procesados, 3 nuevos procesados
  - OCR de Claude correcto, renombrado de archivos correcto, XLSX generado
  - Holded NUNCA tocado: 0 llamadas a api.holded.com
- Commit subido a GitHub: 1042f06
  - accounts-payable/agente_facturas.py modificado (+25/-0)
  - accounts-payable/.env.example creado (45 líneas)
  - .gitignore reorganizado por secciones (+47/-13)

### Confirmado

- token.json de producción funcional con refresh_token vivo
- App OAuth en proyecto Google Cloud "Landing-Isberoal" (project number 765876116624)
- Producción NO ha sido tocada en toda la sesión:
  - Drive sigue intacto en G:\...\Accounts-Payable\files\
  - .bat local ejecutándose con su cron habitual
  - mensajes_procesados.json de producción no modificado

### Pendiente próxima sesión

1. Crear cuenta en Railway (railway.app)
2. Conectar el repo isberoal-ERP a Railway
3. Configurar root directory: accounts-payable/
4. Variables de entorno en Railway:
   - HOLDED_API_KEY (copiar de .env de Drive)
   - ANTHROPIC_API_KEY (copiar de .env de Drive)
   - GMAIL_TOKEN_JSON (copiar contenido completo de token.json de Drive)
   - GOOGLE_CREDENTIALS_PATH=credentials.json
   - ISBEROAL_SHADOW_MODE=true (CRÍTICO: empezar siempre en shadow)
   - RAILWAY_ENVIRONMENT: la define Railway automáticamente
5. Subir credentials.json como volume mount o variable (revisar la mejor forma)
6. Configurar cron a las 2:00 AM (Railway CRON_SCHEDULE)
7. Validar ejecución manual desde dashboard de Railway
8. Comparar XLSX generado por Railway vs facturas importadas por agente local durante 5-7 días
9. Cuando coincida 100%: quitar ISBEROAL_SHADOW_MODE de Railway y coordinar con Ismael el apagado del .bat local

### Notas operativas

- El agente local sigue siendo la fuente de verdad hasta que Railway esté validado
- Carpeta C:\Users\Usuario\test-railway-payable\ se mantiene como entorno de desarrollo local
- Para futuros tests headless desde esa carpeta:
  - $env:GMAIL_TOKEN_JSON = Get-Content -Raw -Path token.json
  - $env:ISBEROAL_SHADOW_MODE = "true"
  - python agente_facturas.py --dias 1
