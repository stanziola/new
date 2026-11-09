"""Colores, todos en hexadecimal ("#rrggbb"), que entienden Qt y pyvista.

- La interfaz (íconos, barras, botones, menús, paneles) va solo en blanco, negro y grises.
- El dibujo 3D: nodos, barras y apoyos en gris; gris oscuro al pasar el mouse; negro al
  seleccionar. La previsualización usa el mismo gris normal, transparente.
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
ELEMENTO = "#9a9a9a"                  # nodos, barras y apoyos, sin seleccionar
RESALTADO = "#4a4a4a"                 # al pasar el mouse con Seleccionar
SELECCIONADO = "#000000"
SIN_ASIGNAR = "#c8c8c8"               # barras sin material o sección (un gris más claro)
ETIQUETA = "#000000"
REJILLA = "#d4d4d4"
EJE_X = "#ff0000"                     # flecha del eje X (fijo)

# ---------- Cubo de vistas ----------
CUBO_CARA = "#ffffff"
CUBO_RESALTADO = "#bebebe"            # cara, arista o esquina bajo el mouse
CUBO_BORDE = "#787878"


def rgb(color):
    """'#4682b4' -> (70, 130, 180), para VTK."""
    c = color.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
