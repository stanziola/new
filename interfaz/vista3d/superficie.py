"""Superficie de interacción en 3D, dibujada con VTK (la misma librería de la vista del modelo).

Antes se dibujaba con matplotlib, que pinta por software: al girarla iba a pocos cuadros por
segundo y sus ejes saltaban de un lado al otro de la caja según el ángulo. Aquí:
- la superficie la dibuja la tarjeta de video;
- los ejes son tres rectas fijas que pasan por el origen: Mz (flexión hacia b), My (flexión hacia h)
  y P (compresión hacia arriba), con sus marcas y valores en unidades de pantalla. Giran con la
  superficie, pero nunca cambian de lado;
- lleva el mismo cubo de vistas de la ventana principal (con su anillo y sus flechas).

Escala: momentos y cargas no comparten unidad (kN·m y kN), así que no hay una proporción "real"
entre los ejes. El momento mayor mide 1 y la carga mayor, ALTO: un diagrama un poco más alto que
ancho, como el 2D.

Los puntos Pu–Mu (uno por combinación y por extremo de la columna) van en su lugar, (Mz, My, P): los
que quedan dentro de la superficie cumplen. El elegido se resalta y lleva una línea desde el eje P,
que muestra la dirección de su momento.
"""
import math

import numpy as np
import pyvista as pv
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from configuracion import colores, unidades
from configuracion import interfaz as ui
from interfaz.vista3d.camara import AnimadorCamara
from interfaz.vista3d.cubo import CuboVistas

ALTO = 1.3                 # largo del eje P cuando el momento mayor mide 1
SOBRANTE = 1.14            # cuánto pasan los ejes de la superficie
MARCAS = 4                 # marcas por semieje, más o menos
MEDIA_MARCA = 0.018        # medio largo de cada marca
OPACIDAD = 0.45            # de la superficie: deja ver los puntos que quedan dentro
VISTA_INICIAL = (1.0, -1.25, 0.75)     # desde dónde se mira al abrir: Mz a la derecha, My al fondo


def _paso(maximo, marcas=MARCAS):
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


class VistaSuperficie(QWidget):
    """La superficie de interacción de diseño con sus ejes, sus puntos y un cubo de vistas."""

    punto_elegido = Signal(int)                 # clic sobre el punto de ese índice

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vista = QtInteractor(self, lighting="three lights")
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        diseno.addWidget(self.vista)
        try:
            self.vista.enable_depth_peeling(number_of_peels=6, occlusion_ratio=0.0)   # transparencia bien ordenada
        except Exception:                       # tarjetas que no lo soportan: se ve igual, con menos precisión
            pass
        self.animador = AnimadorCamara(self.vista)
        self.cubo = CuboVistas(self.vista, self.animador)
        self._datos = None                      # (X, Y, Z, puntos, elegido), en unidades internas
        self._en_escena = np.zeros((0, 3))      # los puntos, en coordenadas del dibujo (para elegirlos)
        self._encuadrada = False
        self._presion = None
        self._cerrada = False
        iren = self.vista.iren
        iren.add_observer("LeftButtonPressEvent", self._al_presionar)
        iren.add_observer("LeftButtonReleaseEvent", self._al_soltar)
        # Si el usuario desplaza o hace zoom a mitad de un giro, manda el usuario
        for evento in ("MiddleButtonPressEvent", "RightButtonPressEvent",
                       "MouseWheelForwardEvent", "MouseWheelBackwardEvent"):
            iren.add_observer(evento, lambda *_: self.animador.detener())

    # ---------- Qué se muestra ----------
    def mostrar(self, X, Y, Z, puntos=(), elegido=None):
        """La superficie: X = φMz, Y = φMy (kN·m) y Z = φPn (kN), arreglos de (ángulos × puntos).
        puntos: [(Mz, My, P), …] en kN·m y kN; elegido: el índice del que se resalta, o None."""
        self._datos = (np.asarray(X, dtype=float), np.asarray(Y, dtype=float), np.asarray(Z, dtype=float),
                       [tuple(float(v) for v in p) for p in puntos], elegido)
        self.refrescar()

    def refrescar(self):
        """Vuelve a dibujar con las unidades y los colores vigentes. No mueve la cámara (salvo la
        primera vez, que encuadra)."""
        if self._datos is None or self._cerrada:
            return
        X, Y, Z, puntos, elegido = self._datos
        fm, fp = unidades.factor("momento"), unidades.factor("fuerza")
        nube = np.array(puntos, dtype=float).reshape(-1, 3)
        # En unidades de pantalla: el momento mayor y los extremos de P (de la superficie y de los puntos)
        m_max = max(float(np.hypot(X, Y).max()), float(np.hypot(nube[:, 0], nube[:, 1]).max()) if len(nube) else 0.0) / fm
        p_sup = max(float(Z.max()), float(nube[:, 2].max()) if len(nube) else 0.0, 0.0) / fp
        p_inf = min(float(Z.min()), float(nube[:, 2].min()) if len(nube) else 0.0, 0.0) / fp
        m_max = m_max or 1.0
        em = 1.0 / m_max                                       # escena por unidad de momento de pantalla
        ep = ALTO / (max(p_sup, -p_inf) or 1.0)                # y por unidad de fuerza de pantalla

        def escena(mz, my, p):
            return np.column_stack([np.ravel(mz) / fm * em, np.ravel(my) / fm * em, np.ravel(p) / fp * ep])

        vista = self.vista
        vista.set_background(colores.FONDO_VISTA)
        # La superficie, cerrada arriba y abajo: en sus dos extremos el momento es casi cero, no cero
        def cerrada(a, es_p):
            """Una columna más al principio y al final: sobre el eje P (momento 0) y a la misma P."""
            primera, ultima = a[:, :1], a[:, -1:]
            return np.hstack([primera if es_p else 0 * primera, a, ultima if es_p else 0 * ultima])

        malla = pv.StructuredGrid(cerrada(X, False) / fm * em, cerrada(Y, False) / fm * em,
                                  cerrada(Z, True) / fp * ep)
        vista.add_mesh(malla, color=colores.INTERACCION_SUPERFICIE, opacity=OPACIDAD, smooth_shading=True,
                       show_edges=False, pickable=False, reset_camera=False, name="superficie", render=False)
        # Los cuatro meridianos de los ejes principales: son los diagramas de un solo eje (P–Mz y P–My)
        filas = [round(k * (X.shape[0] - 1) / 4) for k in range(4)]
        lineas = []
        for i in filas:
            p = escena(X[i], Y[i], Z[i])
            lineas += list(zip(p[:-1], p[1:]))
        vista.add_mesh(_segmentos(lineas), color=colores.RESALTADO, line_width=1.5, lighting=False, pickable=False,
                       reset_camera=False, name="meridianos", render=False)
        self._dibujar_ejes(m_max, p_inf, p_sup, em, ep)
        # Los puntos Pu–Mu
        self._en_escena = escena(nube[:, 0], nube[:, 1], nube[:, 2]) if len(nube) else np.zeros((0, 3))
        for nombre in ("puntos", "elegido", "radio"):
            vista.remove_actor(nombre, render=False)
        otros = [i for i in range(len(nube)) if i != elegido]
        if otros:
            vista.add_mesh(pv.PolyData(self._en_escena[otros]), color=colores.INTERACCION_PUNTO, point_size=9,
                           render_points_as_spheres=True, lighting=False, pickable=False, reset_camera=False,
                           name="puntos", render=False)
        if elegido is not None and 0 <= elegido < len(nube):
            p = self._en_escena[elegido]
            vista.add_mesh(pv.PolyData(p.reshape(1, 3)), color=colores.INTERACCION_ELEGIDO, point_size=14,
                           render_points_as_spheres=True, lighting=False, pickable=False, reset_camera=False,
                           name="elegido", render=False)
            vista.add_mesh(_segmentos([((0.0, 0.0, p[2]), p)]), color=colores.INTERACCION_ELEGIDO, line_width=2,
                           lighting=False, pickable=False, reset_camera=False, name="radio", render=False)
        if not self._encuadrada:
            self.encuadrar()
        vista.renderer.ResetCameraClippingRange()
        self.cubo.actualizar_colores()
        vista.render()

    def _dibujar_ejes(self, m_max, p_inf, p_sup, em, ep):
        """Los tres ejes por el origen, con flecha, marcas, valores y nombre. Fijos: giran con la
        superficie pero no saltan de un lado a otro."""
        vista = self.vista
        largo = SOBRANTE                                        # el momento mayor mide 1
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
            lugares += [(v, -3.2 * MEDIA_MARCA, 0), (-3.2 * MEDIA_MARCA, v, 0)]        # valores, del lado positivo
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
        puntas = [pv.Cone(center=np.array(fin) - 0.03 * np.array(d), direction=d, height=0.06, radius=0.018, resolution=16)
                  for (_ini, fin), d in zip(ejes, ((1, 0, 0), (0, 1, 0), (0, 0, 1)))]
        vista.add_mesh(pv.merge(puntas), color=color, lighting=False, pickable=False, reset_camera=False,
                       name="puntas", render=False)
        vista.add_point_labels(np.array(lugares, dtype=float), textos, font_size=max(ui.TAMANO_LETRA - 3, 8),
                               text_color=colores.ETIQUETA, shape=None, show_points=False, always_visible=True,
                               name="valores", reset_camera=False, render=False)
        sm, sf = unidades.simbolo("momento"), unidades.simbolo("fuerza")
        vista.add_point_labels(
            np.array([(largo * 1.07, 0, 0), (0, largo * 1.07, 0), (0, 0, arriba + 0.09)], dtype=float),
            [f"Mz ({sm})", f"My ({sm})", f"P ({sf})"], font_size=ui.TAMANO_LETRA, bold=True,
            text_color=colores.ETIQUETA, shape=None, show_points=False, always_visible=True, name="nombres",
            reset_camera=False, render=False)

    def encuadrar(self):
        """Vista inicial: en perspectiva, con Mz hacia la derecha, y todo el diagrama a la vista."""
        self.vista.view_vector(VISTA_INICIAL, viewup=(0, 0, 1))
        self.vista.reset_camera()
        self._encuadrada = True

    # ---------- Clic sobre un punto ----------
    def _al_presionar(self, *_):
        self.animador.detener()                    # si la cámara estaba girando, manda el usuario
        self._presion = self.vista.iren.get_event_position()

    def _al_soltar(self, *_):
        if self._presion is None:
            return
        x, y = self.vista.iren.get_event_position()
        x0, y0 = self._presion
        self._presion = None
        if abs(x - x0) > ui.TOL_CLIC_PX or abs(y - y0) > ui.TOL_CLIC_PX or self.cubo.contiene(x, y):
            return                                 # fue un arrastre para girar, o un clic del cubo
        indice = self.punto_en(x, y)
        if indice is not None:
            self.punto_elegido.emit(indice)

    def en_pantalla(self, indice):
        """Posición en píxeles de la vista del punto de ese índice."""
        renderer = self.vista.renderer
        renderer.SetWorldPoint(*self._en_escena[indice], 1.0)
        renderer.WorldToDisplay()
        return renderer.GetDisplayPoint()[:2]

    def punto_en(self, x, y):
        """Índice del punto Pu–Mu más cercano a (x, y), en píxeles de la vista, o None si ninguno está
        a menos de TOL_SELECCION_PX."""
        mejor, distancia = None, float(ui.TOL_SELECCION_PX)
        for i in range(len(self._en_escena)):
            px, py = self.en_pantalla(i)
            d = math.hypot(px - x, py - y)
            if d <= distancia:
                mejor, distancia = i, d
        return mejor

    def cerrar(self):
        """Apaga el cubo y libera la ventana 3D (se llama antes de cerrar la ventana que la contiene)."""
        if self._cerrada:
            return
        self._cerrada = True
        self.animador.detener()
        self.cubo.apagar()
        self.vista.close()
