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
