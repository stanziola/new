"""Funciones comunes de los diagramas de interacción: barras, β1, fy, cuantía y sección rectangular.

Movidas sin cambios desde iteracion2drect.py, iteracion2dcir.py e iteracion3drect.py, que las
tenían repetidas. Un solo registro de unidades (ureg) para todo el paquete: las cantidades de
registros distintos de pint no se pueden mezclar.

Corregido en noviembre de 2026 (antes eran hallazgos pendientes):
- β1 acepta f'c = 2.5 ksi (ACI 318-19 Tabla 22.2.2.4.3, PDF p. 401);
- diámetros nominales de las barras #9 a #18 (ACI 318-19 Apéndice B, PDF p. 583); hasta la #8 es n/8 in;
- fy es un dato de la sección (por defecto FY = 60 ksi, Grado 60), no se deduce del número de barra;
- límites de cuantía de columnas: 1 %–8 % (§10.6.1.1, PDF p. 160) y 6 % en pórticos especiales
  (§18.7.4.1, PDF p. 308).

εy = fy/Es se reduce a un número sin unidades con .to("dimensionless"): fy puede llegar en ksi, en MPa
o en kN/m² (así lo manda la interfaz) y Es está en ksi. Con .magnitude a secas, pint devuelve el número
en las unidades mezcladas (413 685 kN/m² / 29 000 ksi = 14.27 en vez de 0.00207) y el acero nunca cede.
"""
import math

import pint

ureg = pint.UnitRegistry()
ureg.define("tonne_force = 1000 * kilogram_force")

DIAM_ESPECIAL = {9: 1.128, 10: 1.270, 11: 1.410, 14: 1.693, 18: 2.257}
module_s = 29000 * ureg.ksi
FY = 60 * ureg.ksi                   # fy por defecto: Grado 60
KIP_TF = 0.45359237                  # kip -> tonne_force
KIPIN_TFM = 0.45359237 * 0.0254      # kip*in -> tonne_force*m


def area_barra(n, cantidad=1):
    diam = DIAM_ESPECIAL.get(n, n / 8) * ureg.inch
    return cantidad * math.pi * diam**2 / 4


def nb(nx, ny):
    return 2 * (nx + ny - 2)


def Ast(n, cantidad):
    return area_barra(n, cantidad)


def rho(Ast, b, h):
    return (Ast / (b * h)).to("dimensionless").magnitude * 100


def limites_cuantia(especial):
    """(mínima, máxima) de la cuantía de una columna, en %: 1–8 %, o 1–6 % en pórtico especial."""
    return 1.0, 6.0 if especial else 8.0


def beta1(fc):
    fc = fc.to("ksi").magnitude
    if fc < 2.5:
        raise ValueError("fc debe ser al menos 2.5 ksi")
    elif fc <= 4:
        return 0.85
    elif fc >= 8:
        return 0.65
    else:
        return 1.05 - 0.05 * fc


def propiedades_seccion(b, h, d, nx, ny, fc, nob, fy=FY):
    """Sección rectangular (la versión con validaciones de iteracion3drect.py)."""
    if nx < 2 or ny < 2:
        raise ValueError("nx y ny deben ser al menos 2")
    if min(b, h) <= 2 * d:
        raise ValueError("b y h deben ser mayores que 2·d")
    nbarras = nb(nx, ny)
    As_total = Ast(nob, nbarras).to("cm^2")
    fy_val = fy
    return {
        "b": b, "h": h, "d": d, "nx": nx, "ny": ny, "fc": fc, "nob": nob,
        "nbarras": nbarras,
        "As_total": As_total,
        "cuantia": rho(As_total, b, h),
        "beta1": beta1(fc),
        "fy": fy_val,
        "epsilon_y": (fy_val / module_s).to("dimensionless").magnitude,
    }
