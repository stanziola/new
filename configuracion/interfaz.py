"""Interfaz: tamaños, tiempos, tolerancias del mouse, atajos, rejilla, snap, cubo y etiquetas.

Lo marcado "personalización base" son valores por defecto que el usuario puede cambiar desde
Configuración (ver preferencias.py). Los valores con unidades están en unidades internas (m).
"""
# ---------- Ventana ----------
TITULO_VENTANA = "Análisis estructural 3D"
TAMANO_VENTANA = (1200, 800)          # ancho, alto en píxeles

# ---------- Íconos (personalización base) ----------
TAMANO_ICONO = 24                     # barra de herramientas (izquierda), en píxeles
TAMANO_ICONO_INFERIOR = 20            # barra inferior
ICONO_GROSOR = 1.5                    # grosor de línea, en la cuadrícula de 24 x 24 de los íconos

# ---------- Dibujo del modelo (personalización base) ----------
GROSOR_BARRA = 4
TAMANO_NODO = 8
TAMANO_APOYO = 16
ETIQUETAS_VISIBLES = True             # números de nodo encendidos al abrir
TAMANO_LETRA = 14
SEPARACION_ETIQUETA = 0.04            # fracción del tamaño del modelo, hacia arriba
GROSOR_SELECCION = 10                 # barra seleccionada, en píxeles
TAMANO_SELECCION = 22                 # nodo seleccionado, en píxeles
TAMANO_PREVISUALIZACION = 14          # punto gris donde va a quedar el nodo
GROSOR_PREVISUALIZACION = 2           # línea gris de la barra antes de colocarla

# ---------- Rejilla y plano de trabajo (personalización base) ----------
REJILLA_VISIBLE = True                # encendida al abrir
REJILLA_DIVISIONES = 10               # divisiones aproximadas en el lado mayor (paso automático)
REJILLA_PASO = 0.0                    # 0 = automático; si no, paso fijo en m
REJILLA_MARGEN = 0.25                 # cuánto sobresale del modelo, fracción de su lado mayor
REJILLA_TAMANO_VACIO = 10.0           # lado de la rejilla cuando el modelo está vacío, en m
REJILLA_MAX_LINEAS = 500              # tope de líneas por dirección (si no, el paso se agranda)
GROSOR_REJILLA = 1

# ---------- Snap (personalización base) ----------
SNAP_ACTIVO = True                    # encendido al abrir
TOL_SNAP_PX = 12                      # distancia en pantalla para pegarse a un nodo

# ---------- Mouse ----------
TOL_SELECCION_PX = 8                  # distancia máxima del clic al nodo o barra
TOL_CLIC_PX = 4                       # si el mouse se mueve más que esto, es arrastre (rotar), no clic

# ---------- Atajos de teclado (personalización base, como en Civil 3D) ----------
ATAJO_REJILLA = "F7"
ATAJO_SNAP = "F9"

# ---------- Cubo de vistas (esquina superior derecha) ----------
CUBO_TAMANO = 0.26                    # personalización base: lado, fracción del alto de la vista
CUBO_FRANJA = 0.2                     # ancho de aristas y esquinas clicables, fracción del lado

# ---------- Animación de la cámara (cubo de vistas y Encuadre) ----------
ANIM_CAMARA_DURACION_MS = 350         # personalización base: duración del giro (0 = sin animación)
ANIM_CAMARA_INTERVALO_MS = 15         # tiempo entre cuadros (~60 por segundo)

# ---------- Mensajes ----------
DURACION_MENSAJE_MS = 3000            # cuánto se ve un aviso en la barra de estado
