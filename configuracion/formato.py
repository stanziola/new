"""Formato de los números: decimales en pantalla, tablas de consola y nombres de resultados."""
from configuracion import unidades

# ---------- Decimales en pantalla (personalización base) ----------
DECIMALES_LONGITUD = 3
DECIMALES_FUERZA = 2
DECIMALES_MOMENTO = 2
DECIMALES_ESFUERZO = 2
DECIMALES_TABLAS = 3          # tablas de numpy y pandas en la consola

# Qué constante de decimales usa cada magnitud
_DECIMALES_DE = {
    "longitud": "DECIMALES_LONGITUD", "area": "DECIMALES_LONGITUD", "inercia": "DECIMALES_LONGITUD",
    "fuerza": "DECIMALES_FUERZA", "carga_lineal": "DECIMALES_FUERZA",
    "momento": "DECIMALES_MOMENTO", "esfuerzo": "DECIMALES_ESFUERZO",
}

# ---------- Nombres para mostrar resultados ----------
GDL = ["Dx", "Dy", "Dz", "Phix", "Phiy", "Phiz"]       # desplazamientos
FUERZAS = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]         # ejes globales (cargas, reacciones)
FUERZAS_LOCALES = ["N", "Vy", "Vz", "T", "My", "Mz"]   # ejes locales de barra


def decimales(magnitud):
    """Decimales vigentes para esa magnitud (lee el valor actual, por si el usuario lo cambió)."""
    return globals()[_DECIMALES_DE[magnitud]]


def numero(valor_pantalla, magnitud):
    """Número ya convertido, con los decimales de su magnitud. Evita mostrar "-0.000"."""
    d = decimales(magnitud)
    if abs(valor_pantalla) < 0.5 * 10.0 ** -d:
        valor_pantalla = 0.0
    return f"{valor_pantalla:.{d}f}"


def cantidad(valor_interno, magnitud, con_unidad=True):
    """Valor interno convertido a pantalla y con formato: cantidad(2.5, "longitud") -> "2.500 m"."""
    texto = numero(unidades.a_pantalla(valor_interno, magnitud), magnitud)
    return f"{texto} {unidades.simbolo(magnitud)}" if con_unidad else texto


def configurar():
    """Salida de la consola en UTF-8 y formato de las tablas de numpy y pandas."""
    import sys

    import numpy as np
    import pandas as pd

    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 250)
    pd.set_option("display.float_format", f"{{:.{DECIMALES_TABLAS}e}}".format)
    np.set_printoptions(precision=DECIMALES_TABLAS, suppress=True, linewidth=250)
