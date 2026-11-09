"""Dibujo del modelo en la vista 3D: barras, nodos, apoyos, números de nodo, rejilla y previsualización.

Las funciones devuelven sus actores, para poder mostrarlos, ocultarlos o borrarlos después. Se
devuelven en vez de buscarlos por nombre porque pyvista cambia algunos nombres: a las etiquetas,
por ejemplo, les agrega "-labels".
Nada de esto mueve la cámara (reset_camera=False): agregar un nodo no debe cambiar la vista.
"""
import numpy as np
import pyvista as pv
from calculo.ensamble import indices_nodos
from configuracion import colores
from configuracion import interfaz as ui


def dibujar_modelo(vista, modelo):
    """Dibuja barras, nodos, apoyos y números de nodo.

    Devuelve {"barras": actor, "barras_sin_asignar": ..., "nodos": ..., "apoyos": ...,
    "etiquetas": ...} con lo que se dibujó.
    """
    actores = {}
    if not modelo.nodos:
        return actores

    idx = indices_nodos(modelo)                       # ID de nodo -> 0, 1, 2...
    ids = list(idx)
    puntos = np.array([modelo.nodos[nid].coords for nid in ids], dtype=float)

    # Barras: cada línea es [2, punto_i, punto_j]. Las que no tienen material o sección van aparte,
    # con otro color, para que se note que les falta algo.
    asignadas, sin_asignar = [], []
    for el in modelo.elementos.values():
        lista = sin_asignar if el.material is None or el.seccion is None else asignadas
        lista += [2, idx[el.ni], idx[el.nj]]
    for nombre, lineas, color in (("barras", asignadas, colores.BARRA),
                                  ("barras_sin_asignar", sin_asignar, colores.BARRA_SIN_ASIGNAR)):
        if lineas:
            actores[nombre] = vista.add_mesh(pv.PolyData(puntos, lines=np.array(lineas)), color=color,
                                             line_width=ui.GROSOR_BARRA, name=nombre,
                                             reset_camera=False)

    # Nodos
    actores["nodos"] = vista.add_points(puntos, color=colores.NODO, point_size=ui.TAMANO_NODO,
                                        render_points_as_spheres=True, name="nodos",
                                        reset_camera=False)

    # Apoyos: nodos con algún GDL restringido
    apoyos = [i for i, nid in enumerate(ids) if any(modelo.nodos[nid].apoyo)]
    if apoyos:
        actores["apoyos"] = vista.add_points(puntos[apoyos], color=colores.APOYO,
                                             point_size=ui.TAMANO_APOYO,
                                             render_points_as_spheres=True, name="apoyos",
                                             reset_camera=False)

    # Número de cada nodo, un poco arriba del punto
    tamano = np.ptp(puntos, axis=0).max() or 1.0      # tamaño del modelo
    arriba = puntos + [0, 0, ui.SEPARACION_ETIQUETA * tamano]
    actores["etiquetas"] = vista.add_point_labels(
        arriba, [str(nid) for nid in ids], font_size=ui.TAMANO_LETRA,
        text_color=colores.ETIQUETA, shape=None, show_points=False, always_visible=True,
        name="etiquetas", reset_camera=False)
    return actores


def dibujar_rejilla(vista, rejilla, cuenta_para_camara=False):
    """Dibuja la rejilla (ver plano_trabajo.geometria_rejilla) y devuelve su actor.

    - Queda un poco detrás del plano (0.1 % del tamaño del modelo), para que no se pise con las
      barras que están justo en el plano.
    - Normalmente no cuenta para el encuadre ni para el zoom (SetUseBounds(False)): la vista se
      ajusta al modelo, no a la rejilla. Con el modelo vacío sí cuenta, para que se vea.
    """
    a, b = rejilla.ejes
    (u0, v0), (u1, v1) = rejilla.minimo, rejilla.maximo
    paso = rejilla.paso
    segmentos = ([((u, v0), (u, v1)) for u in np.arange(u0, u1 + paso / 2, paso)]
                 + [((u0, v), (u1, v)) for v in np.arange(v0, v1 + paso / 2, paso)])
    pts = np.zeros((2 * len(segmentos), 3))
    pts[:, rejilla.normal] = rejilla.posicion - 0.001 * rejilla.escala
    for i, (p, q) in enumerate(segmentos):
        pts[2 * i, [a, b]] = p
        pts[2 * i + 1, [a, b]] = q
    n = len(segmentos)
    lineas = np.column_stack([np.full(n, 2), np.arange(0, 2 * n, 2), np.arange(1, 2 * n, 2)]).ravel()
    actor = vista.add_mesh(pv.PolyData(pts, lines=lineas), color=colores.REJILLA,
                           line_width=ui.GROSOR_REJILLA, lighting=False, pickable=False,
                           reset_camera=False, name="rejilla")
    actor.SetUseBounds(cuenta_para_camara)
    return actor


class Previsualizacion:
    """Puntos y línea grises que muestran dónde va a quedar el nodo o la barra antes de colocarlos.

    Se crean una sola vez y después solo se mueven sus puntos: es mucho más rápido que borrar y
    volver a crear actores en cada movimiento del mouse.
    """

    def __init__(self, vista):
        self.vista = vista
        self._puntos = pv.PolyData(np.zeros((2, 3)))                      # inicio y punto actual
        self._linea = pv.PolyData(np.zeros((2, 3)), lines=np.array([2, 0, 1]))
        self.actor_puntos = vista.add_mesh(self._puntos, style="points", render_points_as_spheres=True,
                                           reset_camera=False, pickable=False,
                                           name="previsualizacion_puntos")
        self.actor_linea = vista.add_mesh(self._linea, reset_camera=False, pickable=False,
                                          name="previsualizacion_linea")
        for actor in (self.actor_puntos, self.actor_linea):
            actor.SetUseBounds(False)
            actor.SetVisibility(False)
        self.visible = False
        self.actualizar_estilo()

    def actualizar_estilo(self):
        """Toma el color y los tamaños vigentes (por ejemplo, después de cambiar Configuración)."""
        color = [c / 255 for c in colores.rgb(colores.PREVISUALIZACION)]
        for actor in (self.actor_puntos, self.actor_linea):
            actor.GetProperty().SetColor(color)
        self.actor_puntos.GetProperty().SetPointSize(ui.TAMANO_PREVISUALIZACION)
        self.actor_linea.GetProperty().SetLineWidth(ui.GROSOR_PREVISUALIZACION)

    def mostrar(self, punto=None, desde=None):
        """Muestra el punto donde quedaría el nodo y, si hay `desde`, la barra desde ahí."""
        if punto is None:
            self.ocultar()
            return
        inicio = punto if desde is None else desde
        self._puntos.points = np.array([inicio, punto], dtype=float)
        self.actor_puntos.SetVisibility(True)
        if desde is not None:
            self._linea.points = np.array([desde, punto], dtype=float)
        self.actor_linea.SetVisibility(desde is not None)
        self.visible = True

    def ocultar(self):
        self.actor_puntos.SetVisibility(False)
        self.actor_linea.SetVisibility(False)
        self.visible = False
