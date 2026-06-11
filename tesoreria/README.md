# Tesorería - ISBEROAL

Sistema de proyección de tesorería. Objetivo: ejecutar un script y obtener
la posición de caja prevista a una fecha futura indicada.

## Componentes previstos

- proyeccion.py - calcula la posición futura: saldo bancario actual + cobros
  previstos (Holded ventas) - pagos a proveedores (Holded compras) - nóminas
  y cargas sociales - impuestos.
- conciliacion.py - re-anclaje semanal del saldo con el export CSV del banco.
- nominas.py - módulo de datos: calendario de pagos de personal (neto,
  Seguros Sociales, IRPF).

## Estado

En diseño. Sin código todavía. Read-only contra Holded: este sistema
solo lee, nunca escribe.

## Convenciones

- Secretos en .env (nunca en el código ni en Git).
- Salidas XLSX excluidas de Git.
- Reutiliza el patrón de lectura de holded_ventas.py (accounts-receivable-v2).