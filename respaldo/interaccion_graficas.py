import math
import sys
from pathlib import Path

import numpy as np

# el cubo de vistas y los colores son los del programa, que está en la carpeta de arriba
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# PySide6 antes que matplotlib: así matplotlib usa el mismo Qt para su lienzo
import pyvista as pv
from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter
from pyvistaqt import QtInteractor

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Polygon
from matplotlib.widgets import Slider

from configuracion import colores
from configuracion import interfaz as ui
from interfaz.vista3d.camara import AnimadorCamara
from interfaz.vista3d.cubo import CuboVistas, viewport_esquina

# graficas

# aspecto de la grafica 2D: fondo negro y sin la barra de botones de arriba
ESTILO = "dark_background"
SIN_BOTONES = {"toolbar": "None"}

# ventana: el 3D a la izquierda y la columna (2D) a la derecha, en pantalla completa
PROPORCION_3D = 0.55       # parte del ancho para el 3D; el resto, para la columna

# bloque del 2D (en píxeles): la sección, su título y los deslizadores van juntos, centrados en la altura
MARGEN_IZQ_PX = 55         # para los números del eje y
MARGEN_DER_PX = 25
TITULO_PX = 60             # el título, de dos líneas
NUMEROS_X_PX = 35          # los números del eje x, debajo de la sección
DESLIZADOR_PX = 34         # alto de cada deslizador
SEPARACION_PX = 18

# superficie 3D (como la del programa, interfaz/vista3d/superficie.py)
ALTO = 1.3                 # largo del eje P cuando el momento mayor mide 1 (momento y carga no comparten unidad)
SOBRANTE = 1.14            # cuánto pasan los ejes de la superficie
MEDIA_MARCA = 0.018        # medio largo de cada marca de los ejes
OPACIDAD = 0.45            # de la superficie: deja ver las c del ángulo elegido
VISTA_INICIAL = (1.0, -1.25, 0.75)     # desde dónde se mira al abrir
TAMANO_CUBO = 0.12         # lado del cubo, fracción del alto de la vista (en el programa, 0.20)
AMARILLO = "#e6b800"       # las c del ángulo elegido (amarillo oscuro: se ve sobre el fondo blanco)
ROJO = "#d62728"           # la c elegida


def _deslizador(fig, abajo, nombre, maximo):
    """Deslizador en grises, con su zona de clic alta (todo el rectángulo responde, no solo la perilla)."""
    zona = fig.add_axes([0.15, abajo, 0.7, 0.07])     # 0.07 de alto: más fácil de agarrar
    desl = Slider(zona, nombre, 0, maximo, valinit=0, valstep=1,
                  color="0.75",                        # parte recorrida
                  track_color="0.25",                  # parte por recorrer
                  initcolor="none",                    # sin la línea roja en el valor inicial
                  handle_style={"facecolor": "white", "edgecolor": "0.5", "size": 16})
    desl.label.set_x(-0.04)                            # el nombre, a la izquierda de la perilla en 0
    desl.valtext.set_x(1.04)                           # el valor, a la derecha de la perilla al final
    return desl


def _paso(maximo, marcas=4):
    """Separación "redonda" entre marcas (1, 2, 2.5 o 5 por una potencia de 10) para llegar a maximo."""
    if maximo <= 0:
        return 1.0
    bruto = maximo / marcas
    potencia = 10.0 ** math.floor(math.log10(bruto))
    for multiplo in (1.0, 2.0, 2.5, 5.0, 10.0):
        if bruto <= multiplo * potencia * (1 + 1e-9):
            return multiplo * potencia
    return 10.0 * potencia


def _segmentos(pares):
    """PolyData con un segmento por cada par de puntos."""
    puntos = np.array([p for par in pares for p in par], dtype=float)
    n = len(pares)
    lineas = np.column_stack([np.full(n, 2), np.arange(0, 2 * n, 2), np.arange(1, 2 * n, 2)]).ravel()
    return pv.PolyData(puntos, lines=lineas)


class Superficie3D(QObject):
    """La superficie de interacción en 3D, con el cubo de vistas del programa (arriba a la derecha) y
    los ejes Mx, My, P (abajo a la izquierda). Solo dibuja: los números le llegan ya calculados.

    phi_M_x, phi_M_y (tonf·m) y phi_P_n (tonf): (ángulos, n_c), en los ejes de la sección.
    Cada fila (un ángulo) es un "meridiano" de la superficie; seleccionar(ang, i) lo pinta en amarillo
    y su c número i en rojo.
    """

    def __init__(self, parent, phi_M_x, phi_M_y, phi_P_n):
        super().__init__(parent)
        self.mx, self.my, self.p = (np.asarray(a, dtype=float) for a in (phi_M_x, phi_M_y, phi_P_n))
        self.vista = QtInteractor(parent, lighting="three lights")
        try:
            self.vista.enable_depth_peeling(number_of_peels=6, occlusion_ratio=0.0)   # transparencia ordenada
        except Exception:
            pass
        self.vista.set_background(colores.FONDO_VISTA)
        self.vista.add_axes(xlabel="Mx", ylabel="My", zlabel="P",
                            x_color=colores.EJE_X, y_color=colores.EJE_Y, z_color=colores.EJE_Z)
        self.animador = AnimadorCamara(self.vista)
        ui.CUBO_TAMANO = TAMANO_CUBO                   # solo mientras corre este script: no toca las preferencias del programa
        self.cubo = CuboVistas(self.vista, self.animador)
        # si se gira o hace zoom a mitad de un giro del cubo, manda el usuario
        for evento in ("LeftButtonPressEvent", "MiddleButtonPressEvent", "RightButtonPressEvent",
                       "MouseWheelForwardEvent", "MouseWheelBackwardEvent"):
            self.vista.iren.add_observer(evento, lambda *_: self.animador.detener())
        self.vista.installEventFilter(self)            # al cambiar de tamaño, los ejes vuelven a su esquina

        # escala del dibujo: el momento mayor mide 1 y la carga mayor (en valor absoluto), ALTO
        self.m_max = float(np.hypot(self.mx, self.my).max()) or 1.0
        self.p_sup = max(float(self.p.max()), 0.0)
        self.p_inf = min(float(self.p.min()), 0.0)
        self.em = 1.0 / self.m_max
        self.ep = ALTO / (max(self.p_sup, -self.p_inf) or 1.0)
        self._dibujar_superficie()
        self._dibujar_ejes()
        self.vista.view_vector(VISTA_INICIAL, viewup=(0, 0, 1))
        self.vista.reset_camera()

    def escena(self, mx, my, p):
        """De tonf·m y tonf a coordenadas del dibujo."""
        return np.column_stack([np.ravel(mx) * self.em, np.ravel(my) * self.em, np.ravel(p) * self.ep])

    def _dibujar_superficie(self):
        # cerrada arriba y abajo: una columna más en cada extremo, sobre el eje P (momento 0) y a la misma P
        def cerrada(a, es_p):
            primera, ultima = a[:, :1], a[:, -1:]
            return np.hstack([primera if es_p else 0 * primera, a, ultima if es_p else 0 * ultima])

        malla = pv.StructuredGrid(cerrada(self.mx, False) * self.em, cerrada(self.my, False) * self.em,
                                  cerrada(self.p, True) * self.ep)
        self.vista.add_mesh(malla, color=colores.INTERACCION_SUPERFICIE, opacity=OPACIDAD, smooth_shading=True,
                            pickable=False, reset_camera=False, name="superficie", render=False)

    def _dibujar_ejes(self):
        """Los tres ejes por el origen, con flecha, marcas, valores y nombre (como en el programa)."""
        vista = self.vista
        m_max, p_sup, p_inf, em, ep = self.m_max, self.p_sup, self.p_inf, self.em, self.ep
        largo = SOBRANTE
        arriba, abajo = p_sup * ep * SOBRANTE, min(p_inf * ep * SOBRANTE, -0.08)
        ejes = [((-largo, 0, 0), (largo, 0, 0)), ((0, -largo, 0), (0, largo, 0)), ((0, 0, abajo), (0, 0, arriba))]
        marcas, lugares, textos = [], [], []
        paso = _paso(m_max)
        k = 1
        while k * paso <= m_max * SOBRANTE * 0.98:
            v = k * paso * em
            for s in (-1, 1):
                marcas += [((s * v, -MEDIA_MARCA, 0), (s * v, MEDIA_MARCA, 0)),
                           ((-MEDIA_MARCA, s * v, 0), (MEDIA_MARCA, s * v, 0))]
            lugares += [(v, -3.2 * MEDIA_MARCA, 0), (-3.2 * MEDIA_MARCA, v, 0)]
            textos += [f"{k * paso:g}"] * 2
            k += 1
        paso = _paso(max(p_sup, -p_inf))
        k = math.ceil(p_inf / paso)
        while k * paso <= p_sup * SOBRANTE * 0.98:
            if k != 0:
                z = k * paso * ep
                marcas += [((-MEDIA_MARCA, 0, z), (MEDIA_MARCA, 0, z)), ((0, -MEDIA_MARCA, z), (0, MEDIA_MARCA, z))]
                lugares.append((-3.2 * MEDIA_MARCA, -3.2 * MEDIA_MARCA, z))
                textos.append(f"{k * paso:g}")
            k += 1
        color = colores.SELECCIONADO
        vista.add_mesh(_segmentos(ejes + marcas), color=color, line_width=1.5, lighting=False, pickable=False,
                       reset_camera=False, name="ejes", render=False)
        puntas = [pv.Cone(center=np.array(fin) - 0.03 * np.array(d), direction=d, height=0.06, radius=0.018,
                          resolution=16)
                  for (_ini, fin), d in zip(ejes, ((1, 0, 0), (0, 1, 0), (0, 0, 1)))]
        vista.add_mesh(pv.merge(puntas), color=color, lighting=False, pickable=False, reset_camera=False,
                       name="puntas", render=False)
        vista.add_point_labels(np.array(lugares, dtype=float), textos, font_size=max(ui.TAMANO_LETRA - 3, 8),
                               text_color=colores.ETIQUETA, shape=None, show_points=False, always_visible=True,
                               name="valores", reset_camera=False, render=False)
        vista.add_point_labels(
            np.array([(largo * 1.07, 0, 0), (0, largo * 1.07, 0), (0, 0, arriba + 0.09)], dtype=float),
            ["Mx (tonf·m)", "My (tonf·m)", "P (tonf)"], font_size=ui.TAMANO_LETRA, bold=True,   # VTK no dibuja la φ
            text_color=colores.ETIQUETA, shape=None, show_points=False, always_visible=True, name="nombres",
            reset_camera=False, render=False)

    def seleccionar(self, ang, i):
        """Todas las c del ángulo ang en amarillo (línea y puntos) y la c número i en rojo."""
        vista = self.vista
        meridiano = self.escena(self.mx[ang], self.my[ang], self.p[ang])
        vista.add_mesh(_segmentos(list(zip(meridiano[:-1], meridiano[1:]))), color=AMARILLO, line_width=3,
                       lighting=False, pickable=False, reset_camera=False, name="meridiano", render=False)
        vista.add_mesh(pv.PolyData(meridiano), color=AMARILLO, point_size=8, render_points_as_spheres=True,
                       lighting=False, pickable=False, reset_camera=False, name="cs", render=False)
        vista.add_mesh(pv.PolyData(meridiano[i].reshape(1, 3)), color=ROJO, point_size=16,
                       render_points_as_spheres=True, lighting=False, pickable=False, reset_camera=False,
                       name="c_elegida", render=False)
        vista.renderer.ResetCameraClippingRange()
        vista.render()

    def ajustar_esquinas(self):
        """Cubo arriba a la derecha y ejes abajo a la izquierda: cuadrados y con el mismo margen."""
        ancho, alto = self.vista.ren_win.GetSize()
        if ancho <= 0 or alto <= 0:
            return
        self.cubo.ajustar_tamano()
        ejes = self.vista.renderer.axes_widget
        if ejes is not None:
            ejes.SetViewport(*viewport_esquina(ancho, alto, ui.EJES_TAMANO, "abajo_izquierda"))
        self.vista.render()

    def eventFilter(self, objeto, evento):
        if objeto is self.vista and evento.type() == QEvent.Resize:
            QTimer.singleShot(0, self.ajustar_esquinas)   # después de que la vista tome su tamaño
        return False

    def cerrar(self):
        self.animador.detener()
        self.vista.removeEventFilter(self)
        self.cubo.apagar()
        self.vista.close()


class _Ventana(QMainWindow):
    """La ventana: el 3D a la izquierda y la columna (2D) a la derecha, en pantalla completa.
    F11 entra y sale de la pantalla completa; Esc sale (queda maximizada). Al cerrarla se apaga el 3D."""

    def __init__(self, lienzo, superficie):
        super().__init__()
        self.superficie = superficie
        self.setWindowTitle("Diagrama de interacción biaxial")
        self.division = QSplitter(Qt.Horizontal)
        if superficie is not None:
            superficie.setParent(self)
            self.division.addWidget(superficie.vista)
        self.division.addWidget(lienzo)
        self.setCentralWidget(self.division)
        QShortcut(QKeySequence(Qt.Key_F11), self, self._alternar_pantalla)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.showMaximized)

    def repartir(self):
        """PROPORCION_3D del ancho para el 3D y el resto para la columna."""
        if self.superficie is not None:
            ancho = self.division.width()
            self.division.setSizes([round(ancho * PROPORCION_3D), round(ancho * (1 - PROPORCION_3D))])

    def showEvent(self, evento):
        super().showEvent(evento)
        QTimer.singleShot(0, self.repartir)     # cuando la ventana ya tiene su tamaño

    def _alternar_pantalla(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def closeEvent(self, evento):
        if self.superficie is not None:
            self.superficie.cerrar()
        super().closeEvent(evento)


def graficar_c(seccion_girada, barras_giradas, r_barra_cm, c, b_cm, h_cm,
               coord_comp_todas=None, n_comp=None, centroide_comp=None,
               phi_P_n=None, phi_M_x=None, phi_M_y=None):
    """Dibuja lo ya calculado: no gira ni calcula nada, solo toma la fila del ángulo elegido.

    seccion_girada: (ángulos, 5, 2), barras_giradas: (ángulos, n_barras, 2), c: (ángulos, n_c); todo en cm.
    coord_comp_todas: (ángulos, n_c, 6, 2) y n_comp: (ángulos, n_c), la zona comprimida (bloque de Whitney)
    de cada c y cuántos puntos tiene; si no se dan, no se dibuja.
    centroide_comp: (ángulos, n_c, 2), el centroide del bloque comprimido de cada c; si no se da, no se dibuja.
    phi_P_n (tonf), phi_M_x y phi_M_y (tonf·m): (ángulos, n_c), ya en los ejes de la sección. Si se dan, a la
    derecha va la superficie 3D, con las c del ángulo elegido en amarillo y la c elegida en rojo.
    """
    app = QApplication.instance() or QApplication(sys.argv)

    with matplotlib.style.context(ESTILO), matplotlib.rc_context(SIN_BOTONES):
        # --- figura y ejes ---
        fig = Figure()
        lienzo = FigureCanvasQTAgg(fig)
        ax = fig.add_subplot()                           # su lugar lo pone acomodar(), con los deslizadores

        r = np.hypot(b_cm, h_cm) / 2 * 1.1

        # animated=True: no entran al dibujo completo (el fondo); se pintan aparte en cada cuadro
        lineas_c = LineCollection([], colors="0.35", lw=0.8, animated=True)   # todas las c en un solo objeto
        ax.add_collection(lineas_c)
        zona = ax.add_patch(Polygon(np.zeros((1, 2)), closed=True,             # zona comprimida, rellena
                                    facecolor="tab:blue", edgecolor="none", alpha=0.6, animated=True))
        linea_i = ax.axvline(0, color="r", lw=1.5, animated=True)            # la c elegida, en rojo
        linea, = ax.plot([], [], "w-", animated=True)                        # la sección, en blanco
        barras = [ax.add_patch(Circle((0, 0), r_barra_cm, color="0.7", animated=True))   # una por barra
                  for k in range(barras_giradas.shape[1])]
        punto_comp, = ax.plot([], [], "x", ms=10, color="yellow", mew=2, animated=True)   # centroide del bloque
        titulo = ax.set_title("", animated=True)

        x_izq = c.min() * 1.05                            # desde la c más lejana hasta la sección
        ax.set_xlim(x_izq, r)
        ax.set_ylim(-r, r)
        ax.set_aspect("equal")
        ax.grid(False)                                    # sin rejilla: solo las líneas de c

        # --- deslizadores ---
        n_ang, n_c = c.shape                             # filas = ángulos, columnas = valores de c
        desl_ang = _deslizador(fig, 0.12, "θ (°)", n_ang - 1)
        desl_i   = _deslizador(fig, 0.03, "i", n_c - 1)

    # --- superficie 3D, a la derecha ---
    superficie = None
    if phi_P_n is not None and phi_M_x is not None and phi_M_y is not None:
        superficie = Superficie3D(None, phi_M_x, phi_M_y, phi_P_n)

    # lo que cambia, en el orden en que se pinta (lo último queda encima)
    moviles = [lineas_c, zona, linea_i, linea, *barras, punto_comp, titulo]
    for d in (desl_ang, desl_i):
        d.drawon = False                                  # el deslizador ya no pide redibujar toda la ventana
        for a in (d.poly, d._handle, d.valtext):          # su parte que se mueve
            a.set_animated(True)
            moviles.append(a)

    fondo = None                                          # imagen de lo fijo: ejes, números, rieles

    def pintar():
        """Pega el fondo guardado y dibuja encima solo lo que cambia: el blitting."""
        if fondo is None:
            return
        lienzo.restore_region(fondo)
        for a in moviles:
            fig.draw_artist(a)
        lienzo.blit(fig.bbox)

    def guardar_fondo(_):
        """Después de un dibujo completo (al abrir o cambiar el tamaño), guarda el fondo."""
        nonlocal fondo
        fondo = lienzo.copy_from_bbox(fig.bbox)
        pintar()

    def actualizar(_=None):
        ang = int(desl_ang.val)
        i = int(desl_i.val)

        g = seccion_girada[ang]
        linea.set_data(g[:, 0], g[:, 1])
        for barra, centro in zip(barras, barras_giradas[ang]):   # cada círculo a su posición girada
            barra.center = centro

        lineas_c.set_segments([[(x, -r), (x, r)] for x in c[ang]])   # las c de este ángulo
        linea_i.set_xdata([c[ang, i], c[ang, i]])

        if coord_comp_todas is not None:                  # solo los puntos reales (sin los NaN de relleno)
            zona.set_xy(coord_comp_todas[ang, i, :n_comp[ang, i]])
        zona.set_visible(coord_comp_todas is not None)

        if centroide_comp is not None:
            punto_comp.set_data([centroide_comp[ang, i, 0]], [centroide_comp[ang, i, 1]])
        punto_comp.set_visible(centroide_comp is not None)

        texto = f"θ = {ang}°, i = {i}, c = {c[ang, i]:.2f} cm"
        if phi_P_n is not None:
            texto += f"\nφPn = {phi_P_n[ang, i]:.1f} tonf"
            if phi_M_x is not None and phi_M_y is not None:
                texto += f", φMx = {phi_M_x[ang, i]:.1f}, φMy = {phi_M_y[ang, i]:.1f} tonf·m"
        titulo.set_text(texto)
        pintar()
        if superficie is not None:
            superficie.seleccionar(ang, i)

    def acomodar(_=None):
        """La sección (con sus c), el título y los deslizadores, como un bloque centrado en la altura:
        la sección ocupa todo el ancho del panel y los deslizadores van justo debajo."""
        ancho, alto = fig.get_size_inches() * fig.dpi
        if ancho < 100 or alto < 100:
            return
        resto = TITULO_PX + NUMEROS_X_PX + 3 * SEPARACION_PX + 2 * DESLIZADOR_PX   # lo que no es la sección
        proporcion = 2 * r / (r - x_izq)                  # alto / ancho de la sección con sus c (aspecto 1:1)
        w = ancho - MARGEN_IZQ_PX - MARGEN_DER_PX
        h = w * proporcion
        if h > alto - resto - 2 * SEPARACION_PX:          # panel bajo: manda la altura
            h = max(alto - resto - 2 * SEPARACION_PX, 40)
            w = h / proporcion
        bloque = h + resto
        y_ax = (alto + bloque) / 2 - TITULO_PX - h        # borde de abajo de la sección
        x_ax = MARGEN_IZQ_PX + (ancho - MARGEN_IZQ_PX - MARGEN_DER_PX - w) / 2
        ax.set_position([x_ax / ancho, y_ax / alto, w / ancho, h / alto])
        y = y_ax - NUMEROS_X_PX - SEPARACION_PX
        for d in (desl_ang, desl_i):
            y -= DESLIZADOR_PX
            d.ax.set_position([0.15, y / alto, 0.70, DESLIZADOR_PX / alto])
            y -= SEPARACION_PX

    lienzo.mpl_connect("resize_event", acomodar)      # antes de cada dibujo completo por cambio de tamaño
    lienzo.mpl_connect("draw_event", guardar_fondo)
    desl_ang.on_changed(actualizar)
    desl_i.on_changed(actualizar)

    ventana = _Ventana(lienzo, superficie)
    actualizar()
    ventana.showFullScreen()
    app.exec()
