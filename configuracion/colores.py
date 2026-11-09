"""Colores, todos en hexadecimal ("#rrggbb"), que entienden Qt y pyvista.

- La interfaz (íconos, barras, botones, menús) va solo en blanco, negro y grises.
- El dibujo 3D puede tener color.
Para VTK, rgb() los pasa a (r, g, b).
"""
# ---------- Interfaz (solo grises) ----------
INTERFAZ_FONDO = "#ffffff"            # fondo de barras, menús y paneles
INTERFAZ_TEXTO = "#000000"
INTERFAZ_BORDE = "#dcdcdc"            # líneas divisorias
INTERFAZ_HOVER = "#efefef"            # botón bajo el mouse
INTERFAZ_ACTIVO = "#d9d9d9"           # botón activo (sombreado)
INTERFAZ_ACTIVO_BORDE = "#b3b3b3"
INTERFAZ_PRESIONADO = "#c8c8c8"
INTERFAZ_DESHABILITADO = "#a6a6a6"    # texto deshabilitado
ICONO = "#000000"
ICONO_DESHABILITADO = "#b0b0b0"

# ---------- Dibujo 3D (personalización base) ----------
FONDO_VISTA = "#ffffff"
BARRA = "#4682b4"                     # azul acero
BARRA_SIN_ASIGNAR = "#9e9e9e"         # barra sin material o sin sección
NODO = "#000000"
APOYO = "#ff0000"
SELECCION = "#ffa500"
ETIQUETA = "#000000"
REJILLA = "#d4d4d4"
PREVISUALIZACION = "#8c8c8c"          # dónde va a quedar el nodo o la barra antes de colocarlos

# ---------- Cubo de vistas ----------
CUBO_CARA = "#ffffff"
CUBO_RESALTADO = "#bebebe"            # cara, arista o esquina bajo el mouse
CUBO_BORDE = "#787878"


def rgb(color):
    """'#4682b4' -> (70, 130, 180), para VTK."""
    c = color.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
