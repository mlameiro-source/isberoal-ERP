# Diagnostico read-only: relacion entre fecha de emision y fecha de vencimiento
# en las facturas de venta de Holded. No escribe nada en Holded.
# Solo imprime agregados (conteos e importes), sin datos de clientes.

from collections import Counter
from datetime import date

from holded_ventas import leer_facturas_venta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def eur(x):
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


hoy = date.today()
facturas = leer_facturas_venta()
emitidas = [f for f in facturas if not f["es_borrador"]]
con_pendiente = [f for f in emitidas if f["pendiente"] > 0.005]

print(f"Hoy: {hoy}")
print(f"Facturas emitidas: {len(emitidas)}")
print(f"Emitidas con pendiente > 0: {len(con_pendiente)} "
      f"(pendiente total {eur(sum(f['pendiente'] for f in con_pendiente))})")
print()

sin_venc = [f for f in con_pendiente if f["fecha_vencimiento"] is None]
venc_igual = [f for f in con_pendiente
              if f["fecha_vencimiento"] and f["fecha_vencimiento"] == f["fecha_emision"]]
venc_distinto = [f for f in con_pendiente
                 if f["fecha_vencimiento"] and f["fecha_vencimiento"] != f["fecha_emision"]]

print("--- Relacion vencimiento vs emision (solo facturas con pendiente) ---")
print(f"Sin fecha de vencimiento:        {len(sin_venc):4d}  "
      f"pendiente {eur(sum(f['pendiente'] for f in sin_venc))}")
print(f"Vencimiento IGUAL a emision:     {len(venc_igual):4d}  "
      f"pendiente {eur(sum(f['pendiente'] for f in venc_igual))}")
print(f"Vencimiento DISTINTO de emision: {len(venc_distinto):4d}  "
      f"pendiente {eur(sum(f['pendiente'] for f in venc_distinto))}")
print()

if venc_distinto:
    plazos = Counter((f["fecha_vencimiento"] - f["fecha_emision"]).days
                     for f in venc_distinto)
    print("--- Plazos reales encontrados (dias emision->vencimiento : n facturas) ---")
    for dias, n in sorted(plazos.items()):
        print(f"  {dias:4d} dias : {n} facturas")
    print()

vencidas = [f for f in con_pendiente
            if f["fecha_vencimiento"] and f["fecha_vencimiento"] < hoy]
no_vencidas = [f for f in con_pendiente if f not in vencidas]
print("--- Situacion a dia de hoy ---")
print(f"Vencidas:    {len(vencidas):4d}  importe {eur(sum(f['pendiente'] for f in vencidas))}")
print(f"No vencidas: {len(no_vencidas):4d}  importe {eur(sum(f['pendiente'] for f in no_vencidas))}")
print()

if vencidas:
    tramos = {"1-30": 0.0, "31-60": 0.0, "61-90": 0.0, "+90": 0.0}
    n_tramos = {"1-30": 0, "31-60": 0, "61-90": 0, "+90": 0}
    for f in vencidas:
        d = (hoy - f["fecha_vencimiento"]).days
        k = "1-30" if d <= 30 else "31-60" if d <= 60 else "61-90" if d <= 90 else "+90"
        tramos[k] += f["pendiente"]
        n_tramos[k] += 1
    print("--- Antiguedad del vencido (sobre fecha de vencimiento actual) ---")
    for k in ("1-30", "31-60", "61-90", "+90"):
        print(f"  {k:>5} dias : {n_tramos[k]:3d} facturas, {eur(tramos[k])}")