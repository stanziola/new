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
TAMANO_CARGA = 0.08                   # largo de las flechas de carga: fracción del tamaño del modelo

# ---------- Escala de los resultados ----------
# Deformada: el factor multiplica los desplazamientos REALES (1 = tamaño real, que casi no se ve).
# Con la escala automática, el factor se elige para que el desplazamiento mayor ocupe
# FRACCION_DEFORMADA del tamaño del modelo (el aviso dice qué factor salió).
# Diagramas: una fuerza no se mide en metros, así que no hay escala "real". Su 1 es la escala
# automática: el valor mayor del modelo ocupa FRACCION_DIAGRAMA del tamaño del modelo.
DEFORMADA_AUTOMATICA = True           # personalización base
FACTOR_DEFORMADA = 100.0              # personalización base: × desplazamiento real (si no es automática)
FACTOR_DIAGRAMA = 1.0                 # personalización base: × la escala automática de los diagramas
FRACCION_DEFORMADA = 0.05             # fija
FRACCION_DIAGRAMA = 0.12              # fija

# Derivados y fijos
ANCHO_SEPARADOR = 4                   # línea entre la vista y los paneles, en píxeles
OPACIDAD_PREVISUALIZACION = 0.35      # el gris normal, transparente, antes de colocar
ETIQUETAS_VISIBLES = True             # números de nodo al abrir
TAMANO_LETRA = 14
SEPARACION_ETIQUETA = 0.04            # fracción del tamaño del modelo, hacia arriba

# ---------- Rejilla (personalización base) ----------
REJILLA_DISTANCIA_X = 1.0             # distancia entre líneas de cada eje, en m
REJILLA_DISTANCIA_Y = 1.0
REJILLA_DISTANCIA_Z = 3.0             # entre niveles (pisos)
REJILLA_LINEAS_X = 11                 # líneas en cada eje: de 0 a (n - 1) · distancia
REJILLA_LINEAS_Y = 11
REJILLA_LINEAS_Z = 4                  # niveles: 0, 3, 6 y 9 m
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

# ---------- Deshacer y lo que se ve al abrir ----------
HISTORIAL_MAXIMO = 50                 # personalización base: pasos que se pueden deshacer
SECCION_REAL_VISIBLE = True           # barras dibujadas con su sección (cajas b × h) al abrir
CARGAS_VISIBLES = True                # cargas del caso activo dibujadas al abrir (botón Cargas)
REACCIONES_VISIBLES = False           # reacciones en los apoyos, con resultados a la vista (botón Reacciones)
OPACIDAD_MINIMA = 0.1                 # concreto con la transparencia al máximo: no llega a desaparecer
ANCHO_DESLIZADOR_PX = 90              # deslizador de transparencia de la barra inferior
ANCHO_MAXIMO_LISTA_PX = 240           # tope del ancho de las listas desplegables (paneles/comunes.Lista)
ANCHO_PANEL_INTERACCION = 560         # personalización base: ancho de Propiedades con la pestaña Interacción
EJES_LOCALES_VISIBLES = True          # ejes x, y, z locales de la barra seleccionada (menú Etiquetas)

# ---------- Panel Diagrama ----------
PASOS_DESLIZADOR = 400                # posiciones del deslizador a lo largo de la barra
ALTO_PANEL_DIAGRAMA = 240             # alto inicial del panel, en píxeles

# ---------- Mensajes y configuración ----------
DURACION_MENSAJE_MS = 3000            # cuánto se ve un aviso en la barra de comandos
RETARDO_CONFIGURACION_MS = 150        # espera antes de aplicar un cambio de Configuración
