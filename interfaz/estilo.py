# ---------- Ventana ----------
TITULO_VENTANA = "Análisis estructural 3D"
TAMANO_VENTANA = (1200, 800)          # ancho, alto en píxeles

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

# ---------- Etiquetas ----------
COLOR_ETIQUETA = "black"
TAMANO_LETRA = 14
SEPARACION_ETIQUETA = 0.04            # fracción del tamaño del modelo, hacia arriba

# ---------- Cubo de vistas (esquina superior derecha) ----------
CUBO_VIEWPORT = (0.82, 0.74, 1.0, 1.0)  # xmin, ymin, xmax, ymax como fracción de la vista
CUBO_FRANJA = 0.2                     # ancho de aristas y esquinas clicables, fracción del lado
CUBO_COLOR_CARA = (255, 255, 255)     # RGB 0-255, blanco como en Civil 3D
CUBO_COLOR_RESALTADO = (190, 190, 190)  # cara, arista o esquina bajo el mouse
CUBO_COLOR_BORDE = (120, 120, 120)
CUBO_ANIM_DURACION_MS = 350           # duración del giro al hacer clic en el cubo
CUBO_ANIM_INTERVALO_MS = 15           # tiempo entre cuadros de la animación (~60 por segundo)

# ---------- Selección ----------
COLOR_SELECCION = "orange"
GROSOR_SELECCION = 10                 # barra seleccionada, en píxeles
TAMANO_SELECCION = 22                 # nodo seleccionado, en píxeles
TOL_SELECCION_PX = 8                  # distancia máxima del clic al nodo o barra
TOL_CLIC_PX = 4                       # si el mouse se mueve más que esto, es arrastre (rotar), no clic

# ---------- Panel de herramientas (derecha) ----------
TAMANO_ICONO = 32