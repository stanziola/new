"""Colores, todos en hexadecimal ("#rrggbb"), que entienden Qt y pyvista.

- La interfaz (íconos, barras, botones, menús, paneles) va solo en blanco, negro y grises.
- El dibujo 3D: nodos, barras y apoyos en gris; lo seleccionado, en gris oscuro; lo relacionado
  con lo seleccionado (y lo que está bajo el mouse), en un gris intermedio, más tenue. La
  previsualización usa el mismo gris normal, transparente. Las cargas, las reacciones, la
  deformada, los diagramas y el acero de refuerzo sí llevan color.
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
INTERFAZ_PESTANA_INACTIVA = "#d2d2d2" # pestaña que no está elegida (más oscura: la elegida va en blanco)
INTERFAZ_SELECCION = "#b5b5b5"        # fila elegida en los árboles (explorador, Definir)
INTERFAZ_ENLAZADO = "#e3e3e3"         # filas relacionadas con lo elegido (más claras)
ICONO = "#000000"
ICONO_DESHABILITADO = "#b0b0b0"

# ---------- Dibujo 3D (personalización base) ----------
FONDO_VISTA = "#ffffff"
ELEMENTO = "#9a9a9a"                  # nodos, barras y apoyos, sin seleccionar
RESALTADO = "#707070"                 # lo relacionado con lo seleccionado y lo que está bajo el mouse
SELECCIONADO = "#333333"              # lo seleccionado: gris oscuro
SIN_ASIGNAR = "#c8c8c8"               # barras sin material o sección (un gris más claro)
ETIQUETA = "#000000"
REJILLA = "#d4d4d4"
EJE_X = "#ff0000"                     # ejes X, Y y Z (fijos): los globales de la esquina y los locales
EJE_Y = "#2e8b57"                     # (x, y, z) de la barra seleccionada usan los mismos tres colores
EJE_Z = "#0000cd"
CARGA = "#c0392b"                     # flechas de las cargas
REACCION = "#2e7d32"                  # flechas de las reacciones en los apoyos
ACERO = "#7a4a2a"                     # barras de refuerzo de columnas y vigas (se ven con el concreto transparente)
DEFORMADA = "#1f4e9c"                 # barras deformadas
DIAGRAMA_POSITIVO = "#5b9bd5"         # relleno de los diagramas: valores positivos (azul suave)
DIAGRAMA_NEGATIVO = "#e07b7b"         # y negativos (rojo suave)
DIAGRAMA_BORDE = "#303030"

# ---------- Cubo de vistas ----------
CUBO_CARA = "#ffffff"
CUBO_RESALTADO = "#bebebe"            # cara, arista o esquina bajo el mouse
CUBO_BORDE = "#787878"


def rgb(color):
    """'#4682b4' -> (70, 130, 180), para VTK."""
    c = color.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
