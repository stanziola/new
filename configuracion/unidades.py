"""Unidades: el modelo guarda todo en unidades internas (kN y m); la pantalla convierte.

Por qué: si el modelo guardara los números en las unidades de la pantalla, al cambiarlas habría
que convertir todos los datos, y un error a mitad de camino lo dañaría. Así, cambiar de unidades
solo cambia cómo se muestran y se escriben los números: los datos no se tocan.

Cada magnitud se describe con sus exponentes de fuerza y de longitud (análisis dimensional).
Ejemplo: el momento es fuerza·longitud = F¹·L¹ y el esfuerzo es fuerza/longitud² = F¹·L⁻².
El factor de conversión sale solo:
    factor = (kN por unidad de fuerza)^a · (m por unidad de longitud)^b
Ejemplo: 1 kip/in² = 4.4482216152605 kN / 0.0254² m² = 6894.757 kN/m².
"""
# Cuántas unidades internas vale una unidad de pantalla
UNIDADES_LONGITUD = {"m": 1.0, "cm": 0.01, "mm": 0.001, "ft": 0.3048, "in": 0.0254}   # en m
UNIDADES_FUERZA = {"kN": 1.0, "N": 0.001, "tonf": 9.80665, "kgf": 0.00980665,
                   "kip": 4.4482216152605, "lbf": 0.0044482216152605}                # en kN
# tonf es la tonelada fuerza MÉTRICA (1000 kgf = 9.80665 kN), la misma que usan los diagramas de
# interacción. Ojo: en pint, "ton_force" es la tonelada CORTA de EE. UU. (2000 lbf = 8.896 kN).

INTERNA_LONGITUD = "m"
INTERNA_FUERZA = "kN"

# Personalización base: unidades de pantalla al abrir el programa
LONGITUD = "m"
FUERZA = "kN"

# Exponentes (fuerza, longitud) de cada magnitud
MAGNITUDES = {
    "longitud": (0, 1),
    "area": (0, 2),
    "inercia": (0, 4),
    "fuerza": (1, 0),
    "carga_lineal": (1, -1),
    "momento": (1, 1),
    "esfuerzo": (1, -2),
}

_SUPERINDICES = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def factor(magnitud):
    """Cuántas unidades internas vale 1 unidad de pantalla de esa magnitud."""
    a, b = MAGNITUDES[magnitud]
    return UNIDADES_FUERZA[FUERZA] ** a * UNIDADES_LONGITUD[LONGITUD] ** b


def a_interna(valor, magnitud):
    """De unidades de pantalla a internas (para guardar en el modelo)."""
    return valor * factor(magnitud)


def a_pantalla(valor, magnitud):
    """De unidades internas a las de pantalla (para mostrar)."""
    return valor / factor(magnitud)


def simbolo(magnitud):
    """Símbolo de la unidad de pantalla: "m", "kN·m", "kN/m²", "m⁴"..."""
    a, b = MAGNITUDES[magnitud]

    def potencia(unidad, n):
        return unidad if n == 1 else unidad + str(n).translate(_SUPERINDICES)

    arriba = ([potencia(FUERZA, a)] if a > 0 else []) + ([potencia(LONGITUD, b)] if b > 0 else [])
    abajo = [potencia(LONGITUD, -b)] if b < 0 else []
    return "·".join(arriba) + ("/" + "·".join(abajo) if abajo else "")
