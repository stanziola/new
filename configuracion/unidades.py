"""Unidades: el modelo guarda todo en unidades internas (kN y m); la pantalla convierte.

Como en Ftool: cada magnitud (longitud, área, fuerza, momento...) tiene su propia unidad de
pantalla, y sus decimales están en formato.py. Cambiar una unidad solo cambia cómo se muestran y
se escriben los números: los datos del modelo no se tocan.

Cada tabla dice cuántas unidades internas vale una unidad de pantalla. Ejemplos:
- 1 cm = 0.01 m;
- 1 kgf/cm² = 0.00980665 kN / 0.0001 m² = 98.0665 kN/m²;
- 1 kip·ft = 4.4482216152605 kN × 0.3048 m = 1.3558 kN·m.
tonf es la tonelada fuerza MÉTRICA (1000 kgf = 9.80665 kN), la misma de los diagramas de
interacción. Ojo: en pint, "ton_force" es la tonelada CORTA de EE. UU. (2000 lbf = 8.896 kN).

"seccion" (dimensiones de sección: b, h, d) y "desplazamiento" (los resultados: desplazamientos de
nodos y barras) son longitudes con unidad propia: la geometría del modelo suele ir en m, las
secciones en cm o mm y los desplazamientos en mm.
Magnitudes derivadas (DERIVADAS): no tienen unidad propia; se arman con las de fuerza y longitud,
como el peso unitario γ en F/L³ (kN/m³, tonf/m³, lbf/ft³...).
"""
KGF = 0.00980665                  # kN
TONF = 9.80665                    # kN (tonelada métrica)
KIP = 4.4482216152605             # kN
LBF = 0.0044482216152605          # kN
FT, PULG = 0.3048, 0.0254         # m

UNIDADES = {
    "longitud": {"m": 1.0, "cm": 0.01, "mm": 0.001, "ft": FT, "in": PULG},
    "seccion": {"cm": 0.01, "mm": 0.001, "m": 1.0, "in": PULG},
    "desplazamiento": {"mm": 0.001, "cm": 0.01, "m": 1.0, "in": PULG},
    "area": {"m²": 1.0, "cm²": 1e-4, "mm²": 1e-6, "in²": PULG ** 2, "ft²": FT ** 2},
    "inercia": {"m⁴": 1.0, "cm⁴": 1e-8, "mm⁴": 1e-12, "in⁴": PULG ** 4, "ft⁴": FT ** 4},
    "fuerza": {"kN": 1.0, "N": 0.001, "tonf": TONF, "kgf": KGF, "kip": KIP, "lbf": LBF},
    "momento": {"kN·m": 1.0, "N·m": 0.001, "tonf·m": TONF, "kgf·m": KGF, "kgf·cm": KGF * 0.01,
                "kip·ft": KIP * FT, "kip·in": KIP * PULG, "lbf·ft": LBF * FT},
    "carga_lineal": {"kN/m": 1.0, "N/m": 0.001, "tonf/m": TONF, "kgf/m": KGF, "kip/ft": KIP / FT,
                     "lbf/ft": LBF / FT},
    "esfuerzo": {"MPa": 1000.0, "GPa": 1e6, "kPa": 1.0, "kgf/cm²": KGF / 1e-4, "tonf/m²": TONF,
                 "ksi": KIP / PULG ** 2, "psi": LBF / PULG ** 2},
}

NOMBRES = {"longitud": "Longitud", "seccion": "Dimensiones de sección", "desplazamiento": "Desplazamientos",
           "area": "Área", "inercia": "Inercia",
           "fuerza": "Fuerza", "momento": "Momento", "carga_lineal": "Carga distribuida",
           "esfuerzo": "Esfuerzo y módulos"}

DERIVADAS = {"peso_unitario": (1, -3)}     # magnitud -> (a, b) de F^a·L^b (ver compuesta)

# ---------- Personalización base: unidad de pantalla de cada magnitud ----------
LONGITUD = "m"
SECCION = "cm"
DESPLAZAMIENTO = "mm"
AREA = "cm²"
INERCIA = "cm⁴"
FUERZA = "kN"
MOMENTO = "kN·m"
CARGA_LINEAL = "kN/m"
ESFUERZO = "MPa"

_SUPERINDICES = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def elegida(magnitud):
    """Unidad de pantalla vigente de esa magnitud (lee el valor actual, por si el usuario la cambió)."""
    return globals()[magnitud.upper()]


def factor(magnitud):
    """Cuántas unidades internas vale 1 unidad de pantalla de esa magnitud."""
    if magnitud in DERIVADAS:
        return compuesta(*DERIVADAS[magnitud])[0]
    return UNIDADES[magnitud][elegida(magnitud)]


def a_interna(valor, magnitud):
    """De unidades de pantalla a internas (para guardar en el modelo)."""
    return valor * factor(magnitud)


def a_pantalla(valor, magnitud):
    """De unidades internas a las de pantalla (para mostrar)."""
    return valor / factor(magnitud)


def simbolo(magnitud):
    if magnitud in DERIVADAS:
        return compuesta(*DERIVADAS[magnitud])[1]
    return elegida(magnitud)


def compuesta(a, b):
    """Unidad F^a·L^b con las unidades elegidas de fuerza y longitud: (factor, símbolo).

    Para lo que no tiene fila propia. Ejemplo: los términos de una matriz de rigidez están en
    F/L (a = 1, b = -1), en F (1, 0) o en F·L (1, 1): con kip y ft dan kip/ft, kip y kip·ft.
    """
    f = UNIDADES["fuerza"][FUERZA] ** a * UNIDADES["longitud"][LONGITUD] ** b

    def potencia(unidad, n):
        return unidad if n == 1 else unidad + str(n).translate(_SUPERINDICES)

    arriba = ([potencia(FUERZA, a)] if a > 0 else []) + ([potencia(LONGITUD, b)] if b > 0 else [])
    abajo = [potencia(LONGITUD, -b)] if b < 0 else []
    return f, "·".join(arriba) + ("/" + "·".join(abajo) if abajo else "")
