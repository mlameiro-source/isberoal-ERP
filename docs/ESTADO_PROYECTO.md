# ESTADO DEL PROYECTO - ISBEROAL ERP
Última actualización: 08/05/2026

## Repositorio
- GitHub: https://github.com/mlameiro-source/isberoal-ERP
- Cuenta: mlameiro-source
- Rama principal: main

## Carpetas originales (producción - NO tocar)
- Accounts Payable: G:\Unidades compartidas\01_ISBEROAL Energy\14_Agentes\Accounts-Payable\files\
- Accounts Receivable: G:\Unidades compartidas\01_ISBEROAL Energy\14_Agentes\Accounts-Receivable\files\

## Carpeta de desarrollo local
- C:\Users\Usuario\proyectos\isberoal-ERP

## Stack
- Agentes: Python
- SuperApp: Next.js 15, Supabase, Prisma, Vercel
- Repo SuperApp: https://github.com/iromay-coder/isberoal-app-interna

## Módulos
### Accounts Payable (facturas de gasto)
- Archivo principal: agente_facturas.py
- Estado: EN PRODUCCIÓN corriendo en local
- Función: lee correo, OCR facturas, imputa a Holded
- Pendiente: migrar de Holded a Supabase + desplegar en Railway

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

## Próximos pasos (por orden)
1. Desplegar agente en Railway
2. Conectar agente a Supabase en lugar de Holded
3. Construir módulo ERP en la SuperApp (pantallas Next.js)

## Contexto SuperApp ISBEROAL
- URL: https://isberoal-isberoal.vercel.app
- Repo: iromay-coder/isberoal-app-interna
- Supabase proyecto: ISBEROAL-RRHH (sbgqykapjitjcpgmvnih, eu-west-1)
- Responsable ERP: Martín Lameiro (mlameiro@isberoal.com)

## Cómo retomar en una nueva conversación
Pegar este archivo completo al inicio del chat con el mensaje:
'Soy Martín Lameiro, retomo el desarrollo del ERP de ISBEROAL. Este es el estado del proyecto:'

## Sesión 08/05/2026 - Tarde

### Hecho
- Repo subido a GitHub correctamente
- Token Gmail antiguo revocado y regenerado por seguridad
- Agente local verificado funcionando con cuenta mlameiro@isberoal.com

### Confirmado
- Agente autenticado con: mlameiro@isberoal.com
- Lee correos enviados a: contabilidad@isberoal.com (grupo donde está mlameiro)
- Sigue corriendo en local desde G:\Unidades compartidas\...\Accounts-Payable\files\
- Próxima ejecución programada: lunes 9:00 AM

### Pendiente próxima sesión
1. Crear cuenta en Railway
2. Configurar deploy del agente accounts-payable
3. Generar token Gmail compatible con servidor (sin navegador)
4. Configurar variables de entorno en Railway
5. Programar cron a las 2:00 AM
6. Probar en modo --solo-xlsx antes de activar import a Holded
7. Coordinar desactivación del .bat local con Ismael cuando Railway esté operativo

## Sesión 08/05/2026 - Noche

### Hecho

- Repo conectado a Railway (proyecto `empathetic-illumination`, región US West)
- Root Directory configurado a `accounts-payable`
- Commit `e3d9c85` mergeado a main:
  - Creado `accounts-payable/requirements.txt` con dependencias mínimas
  - `conectar_gmail()` adaptado para Railway: lee credenciales desde variable de entorno `GMAIL_TOKEN_JSON` con fallback a `token.json` local
  - Compatibilidad total con flujo local actual mantenida

### Pendiente próxima sesión

1. Relanzar deploy en Railway (build debería pasar ahora)
2. Configurar variables de entorno en Railway:
   - `GMAIL_TOKEN_JSON` (contenido del token.json local)
   - `ANTHROPIC_API_KEY`
   - Revisar `.env` local por si hay más variables a portar
3. Probar ejecución manual del agente desde Railway
4. Configurar cron `0 2 * * *` en Railway
5. Coordinar con Ismael la desactivación del .bat local

### Pendiente menor

- Borrar carpeta huérfana `.claude/worktrees/determined-gauss-b7368c` después del próximo reinicio
