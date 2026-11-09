"""Interfaz: tamaños, tiempos, rejilla, cubo y ejes.

Lo marcado "personalización base" lo puede cambiar el usuario en Configuración (preferencias.py).
Lo demás son constantes internas. Los valores con unidades están en unidades internas (m).
"""
# ---------- Ventana ----------
TITULO_VENTANA = "Análisis estructural 3D"
TAMANO_VENTANA = (1400, 860)          # ancho, alto en píxeles

# ---------- Íconos (personalización base) ----------
TAMANO_ICONO = 24                     # barra de herramientas (izquierda) y barra Definir, en píxeles
TAMANO_ICONO_INFERIOR = 20            # barra inferior
ICONO_GROSOR = 1.5                    # grosor de línea, en la cuadrícula de 24 x 24 de los íconos

# ---------- Vista (personalización base: solo estos dos) ----------
GROSOR_BARRA = 4                      # en píxeles; la barra seleccionada usa el mismo
TAMANO_NODO = 9                       # en píxeles; el nodo seleccionado usa el mismo

TAMANO_APOYO = 0.06                   # cono y placa de los apoyos: fracción del tamaño del modelo

# Derivados y fijos
ANCHO_SEPARADOR = 4                   # línea entre la vista y los paneles, en píxeles
OPACIDAD_PREVISUALIZACION = 0.35      # el gris normal, transparente, antes de colocar
ETIQUETAS_VISIBLES = True
TAMANO_LETRA = 14
SEPARACION_ETIQUETA = 0.04            # fracción del tamaño del modelo, hacia arriba

# ---------- Rejilla (personalización base) ----------
REJILLA_DISTANCIA = 1.0               # distancia entre líneas, en m
REJILLA_LINEAS_X = 11                 # líneas en cada eje: de 0 a (n - 1) · distancia
REJILLA_LINEAS_Y = 11
REJILLA_LINEAS_Z = 11
REJILLA_VISIBLE = True                # encendida al abrir
GROSOR_REJILLA = 1

# ---------- Mouse y snap (fijos) ----------
SNAP_ACTIVO = True
TOL_SNAP_PX = 12                      # distancia en pantalla para pegarse a un nodo
TOL_SELECCION_PX = 8                  # distancia para resaltar y seleccionar
TOL_CLIC_PX = 4                       # si el mouse se mueve más que esto, es arrastre (rotar), no clic

# ---------- Atajos (fijos, como en Civil 3D) ----------
ATAJO_REJILLA = "F7"
ATAJO_SNAP = "F9"

# ---------- Cubo de vistas y ejes (personalización base) ----------
CUBO_TAMANO = 0.20                    # lado del cubo, fracción del alto de la vista
EJES_TAMANO = 0.16                    # lado de los ejes X, Y, Z, fracción del alto de la vista
MARGEN_ESQUINA_PX = 8                 # separación del cubo y los ejes a sus esquinas
CUBO_FRANJA = 0.2                     # ancho de aristas y esquinas clicables, fracción del lado

# ---------- Animación de la cámara (cubo de vistas y Encuadre) ----------
ANIM_CAMARA_DURACION_MS = 350         # personalización base: duración del giro (0 = sin animación)
ANIM_CAMARA_INTERVALO_MS = 15         # tiempo entre cuadros (~60 por segundo)

# ---------- Deshacer y dibujo de secciones ----------
HISTORIAL_MAXIMO = 50                 # personalización base: pasos que se pueden deshacer
SECCION_REAL_VISIBLE = True           # barras dibujadas con su sección (cajas b × h) al abrir

# ---------- Mensajes y configuración ----------
DURACION_MENSAJE_MS = 3000            # cuánto se ve un aviso en la barra de comandos
RETARDO_CONFIGURACION_MS = 150        # espera antes de aplicar un cambio de Configuración
