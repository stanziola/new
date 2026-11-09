"""Estilo de la interfaz: colores, tamaños, tolerancias y valores por defecto.

- La interfaz (íconos, barras, botones) usa solo blanco, negro y grises. El dibujo 3D puede tener
  color.
- Lo marcado como "personalización base" son valores por defecto que más adelante podrá cambiar
  el usuario desde un botón de Configuración.
"""
# ---------- Ventana ----------
TITULO_VENTANA = "Análisis estructural 3D"
TAMANO_VENTANA = (1200, 800)          # ancho, alto en píxeles

# ---------- Tema de la interfaz (solo blanco, negro y grises) ----------
INTERFAZ_FONDO = "#ffffff"            # fondo de barras y paneles
INTERFAZ_TEXTO = "#000000"
INTERFAZ_BORDE = "#dcdcdc"            # líneas divisorias
INTERFAZ_HOVER = "#efefef"            # botón bajo el mouse
INTERFAZ_ACTIVO = "#d9d9d9"           # botón activo (sombreado)
INTERFAZ_ACTIVO_BORDE = "#b3b3b3"
INTERFAZ_PRESIONADO = "#c8c8c8"
INTERFAZ_DESHABILITADO = "#a6a6a6"    # texto deshabilitado
ICONO_COLOR = "#000000"
ICONO_DESHABILITADO = "#b0b0b0"
ICONO_GROSOR = 1.5                    # grosor de línea, en la cuadrícula de 24 x 24 de los íconos

# ---------- Íconos (personalización base) ----------
TAMANO_ICONO = 24                     # barra de herramientas (izquierda), en píxeles
TAMANO_ICONO_INFERIOR = 20            # barra inferior

# ---------- Vista 3D ----------
COLOR_FONDO = "white"

# ---------- Barras ----------
COLOR_BARRA = "steelblue"
GROSOR_BARRA = 4

# ---------- Nodos ----------
COLOR_NODO = "black"
TAMANO_NODO = 8

# ---------- Apoyos ----------
COLOR_APOYO = "red"
TAMANO_APOYO = 16

# ---------- Etiquetas (números de nodo) ----------
ETIQUETAS_VISIBLES = True             # personalización base: encendidas al abrir
COLOR_ETIQUETA = "black"
TAMANO_LETRA = 14
SEPARACION_ETIQUETA = 0.04            # fracción del tamaño del modelo, hacia arriba

# ---------- Rejilla de piso (personalización base) ----------
REJILLA_VISIBLE = True                # encendida al abrir
REJILLA_DIVISIONES = 10               # divisiones aproximadas en el lado mayor del modelo en planta
REJILLA_MARGEN = 0.25                 # cuánto sobresale de la planta, fracción de ese lado
COLOR_REJILLA = "#d4d4d4"
GROSOR_REJILLA = 1

# ---------- Atajos de teclado (personalización base, como en Civil 3D) ----------
ATAJO_REJILLA = "F7"
ATAJO_SNAP = "F9"

# ---------- Cubo de vistas (esquina superior derecha) ----------
CUBO_VIEWPORT = (0.82, 0.74, 1.0, 1.0)  # personalización base (tamaño): xmin, ymin, xmax, ymax
CUBO_FRANJA = 0.2                     # ancho de aristas y esquinas clicables, fracción del lado
CUBO_COLOR_CARA = (255, 255, 255)     # RGB 0-255, blanco como en Civil 3D
CUBO_COLOR_RESALTADO = (190, 190, 190)  # cara, arista o esquina bajo el mouse
CUBO_COLOR_BORDE = (120, 120, 120)

# ---------- Animación de la cámara (cubo de vistas y Encuadre) ----------
ANIM_CAMARA_DURACION_MS = 350         # personalización base: duración del giro
ANIM_CAMARA_INTERVALO_MS = 15         # tiempo entre cuadros (~60 por segundo)

# ---------- Selección ----------
COLOR_SELECCION = "orange"
GROSOR_SELECCION = 10                 # barra seleccionada, en píxeles
TAMANO_SELECCION = 22                 # nodo seleccionado, en píxeles
TOL_SELECCION_PX = 8                  # distancia máxima del clic al nodo o barra
TOL_CLIC_PX = 4                       # si el mouse se mueve más que esto, es arrastre (rotar), no clic
