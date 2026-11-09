"""Funciones comunes de los diagramas de interacción: barras, β1, fy, cuantía y sección rectangular.

Movidas sin cambios desde iteracion2drect.py, iteracion2dcir.py e iteracion3drect.py, que las
tenían repetidas. Un solo registro de unidades (ureg) para todo el paquete: las cantidades de
registros distintos de pint no se pueden mezclar.

Hallazgos pendientes de revisión (docs/plan_de_estudio.md): β1 con f'c ≤ 2.5 ksi, diámetros de las
barras #14 y #18, fy según el número de barra. NO se corrigen aquí: es cálculo sagrado y cualquier
corrección se aprueba aparte.
"""
import math

import pint

ureg = pint.UnitRegistry()
ureg.define("tonne_force = 1000 * kilogram_force")

DIAM_ESPECIAL = {9: 1.128, 10: 1.270, 11: 1.410}
module_s = 29000 * ureg.ksi
KIP_TF = 0.45359237                  # kip -> tonne_force
KIPIN_TFM = 0.45359237 * 0.0254      # kip*in -> tonne_force*m


def area_barra(n, cantidad=1):
    diam = DIAM_ESPECIAL.get(n, n / 8) * ureg.inch
    return cantidad * math.pi * diam**2 / 4


def nb(nx, ny):
    return 2 * (nx + ny - 2)


def Ast(n, cantidad):
    return area_barra(n, cantidad)


def fy(n):
    return 60 * ureg.ksi if n >= 4 else 40 * ureg.ksi


def rho(Ast, b, h):
    return (Ast / (b * h)).to("dimensionless").magnitude * 100


def beta1(fc):
    fc = fc.to("ksi").magnitude
    if fc <= 2.5:
        raise ValueError("fc debe ser mayor a 2.5 ksi")
    elif fc <= 4:
        return 0.85
    elif fc >= 8:
        return 0.65
    else:
        return 1.05 - 0.05 * fc


def propiedades_seccion(b, h, d, nx, ny, fc, nob):
    """Sección rectangular (la versión con validaciones de iteracion3drect.py)."""
    if nx < 2 or ny < 2:
        raise ValueError("nx y ny deben ser al menos 2")
    if min(b, h) <= 2 * d:
        raise ValueError("b y h deben ser mayores que 2·d")
    nbarras = nb(nx, ny)
    As_total = Ast(nob, nbarras).to("cm^2")
    fy_val = fy(nob)
    return {
        "b": b, "h": h, "d": d, "nx": nx, "ny": ny, "fc": fc, "nob": nob,
        "nbarras": nbarras,
        "As_total": As_total,
        "cuantia": rho(As_total, b, h),
        "beta1": beta1(fc),
        "fy": fy_val,
        "epsilon_y": (fy_val / module_s).magnitude,
    }
