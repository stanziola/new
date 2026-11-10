"""Formato de los números: decimales de cada magnitud (como en Ftool), tablas de consola y nombres."""
from configuracion import unidades

# ---------- Decimales en pantalla, uno por magnitud (personalización base) ----------
DECIMALES_LONGITUD = 3
DECIMALES_SECCION = 1
DECIMALES_DESPLAZAMIENTO = 3
DECIMALES_AREA = 2
DECIMALES_INERCIA = 1
DECIMALES_FUERZA = 2
DECIMALES_MOMENTO = 2
DECIMALES_CARGA_LINEAL = 2
DECIMALES_ESFUERZO = 2
DECIMALES_PESO_UNITARIO = 2   # magnitud derivada (F/L³): no tiene fila en Configuración
DECIMALES_TABLAS = 3          # tablas de numpy y pandas en la consola (no se configura)

# ---------- Nombres para mostrar resultados ----------
GDL = ["Dx", "Dy", "Dz", "Phix", "Phiy", "Phiz"]       # desplazamientos (consola y CSV)
GDL_PANTALLA = ["Δx", "Δy", "Δz", "φx", "φy", "φz"]    # los mismos, con Δ y φ (interfaz)
FUERZAS = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]         # ejes globales (cargas, reacciones)
FUERZAS_LOCALES = ["N", "Vy", "Vz", "T", "My", "Mz"]   # ejes locales de barra


def decimales(magnitud):
    """Decimales vigentes de esa magnitud (lee el valor actual, por si el usuario lo cambió)."""
    return globals()[f"DECIMALES_{magnitud.upper()}"]


def numero(valor, d):
    """Número con d decimales. Evita mostrar "-0.000"."""
    if abs(valor) < 0.5 * 10.0 ** -d:
        valor = 0.0
    return f"{valor:.{d}f}"


def cantidad(valor_interno, magnitud, con_unidad=True):
    """Valor interno convertido a pantalla y con formato: cantidad(2.5, "longitud") -> "2.500 m"."""
    texto = numero(unidades.a_pantalla(valor_interno, magnitud), decimales(magnitud))
    return f"{texto} {unidades.simbolo(magnitud)}" if con_unidad else texto


def compacto(valor_interno, magnitud):
    """Como cantidad(), sin unidad y sin ceros de más (para nombres): 0.30 m en cm -> "30";
    0.255 m -> "25.5"."""
    texto = numero(unidades.a_pantalla(valor_interno, magnitud), decimales(magnitud))
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return "0" if texto in ("-0", "") else texto


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
