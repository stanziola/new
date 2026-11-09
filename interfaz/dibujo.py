"""Dibujo del modelo en la vista 3D: barras, nodos, apoyos, números de nodo, rejilla y previsualización.

Colores por elemento: cada barra, nodo y apoyo tiene su color guardado en su malla (un arreglo
RGB). Para resaltar (gris oscuro) o seleccionar (negro) solo se cambia ese color: no se dibuja
nada encima. Así el tamaño es el mismo y no hay parpadeo (dos objetos en el mismo lugar se
"pelean" por verse cuando la tarjeta de video decide cuál está adelante).
Nada de esto mueve la cámara (reset_camera=False): agregar un nodo no debe cambiar la vista.
"""
import numpy as np
import pyvista as pv
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
from calculo.ensamble import indices_nodos
from configuracion import colores
from configuracion import interfaz as ui


class ModeloDibujado:
    """Lo dibujado de un modelo: actores, mallas y de qué ID es cada barra, nodo y apoyo."""

    def __init__(self):
        self.actores = {}          # "barras", "nodos", "apoyos", "etiquetas", "rejilla"
        self.mallas = {}           # "barras", "nodos", "apoyos"
        self.base = {}             # color sin resaltar de cada celda o punto de cada malla
        self.indice_barra = {}     # ID de barra -> celda en la malla "barras"
        self.indice_nodo = {}      # ID de nodo -> punto en la malla "nodos"
        self.indice_apoyo = {}     # ID de nodo -> punto en la malla "apoyos"

    def _lugares(self, item):
        """Dónde está pintado un ("nodo", id) o ("barra", id): lista de (malla, índice)."""
        if item is None:
            return []
        tipo, ident = item
        if tipo == "barra" and ident in self.indice_barra:
            return [("barras", self.indice_barra[ident])]
        if tipo == "nodo" and ident in self.indice_nodo:
            lugares = [("nodos", self.indice_nodo[ident])]
            if ident in self.indice_apoyo:
                lugares.append(("apoyos", self.indice_apoyo[ident]))
            return lugares
        return []

    def pintar(self, resaltado=None, seleccion=None):
        """Colores vigentes: base gris, resaltado en gris oscuro y selección en negro (gana)."""
        nuevos = {nombre: base.copy() for nombre, base in self.base.items()}
        for item, color in ((resaltado, colores.RESALTADO), (seleccion, colores.SELECCIONADO)):
            for malla, i in self._lugares(item):
                nuevos[malla][i] = colores.rgb(color)
        for nombre, malla in self.mallas.items():
            datos = malla.cell_data if nombre == "barras" else malla.point_data
            datos["color"] = nuevos[nombre]


def _rgb(color, n):
    return np.tile(np.array(colores.rgb(color), dtype=np.uint8), (n, 1))


def _agregar(vista, nombre, malla, por_celda, linea=None, punto=None):
    """Actor que toma el color de cada celda o punto del arreglo "color" de ESTA malla.

    Se arma a mano (como el cubo de vistas) porque add_mesh de pyvista le pasa al actor una copia
    de la malla: cambiar los colores de la nuestra no cambiaría lo que se ve.
    """
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(malla)
    if por_celda:
        mapper.SetScalarModeToUseCellFieldData()
    else:
        mapper.SetScalarModeToUsePointFieldData()
    mapper.SelectColorArray("color")
    mapper.SetColorModeToDirectScalars()
    actor = vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    if linea is not None:
        prop.SetLineWidth(linea)
    if punto is not None:
        prop.SetPointSize(punto)
        prop.SetRenderPointsAsSpheres(True)
    vista.add_actor(actor, name=nombre, reset_camera=False, pickable=False, render=False)
    return actor


def dibujar_modelo(vista, modelo):
    """Dibuja barras, nodos, apoyos y números de nodo. Devuelve un ModeloDibujado."""
    d = ModeloDibujado()
    if not modelo.nodos:
        return d

    idx = indices_nodos(modelo)                       # ID de nodo -> 0, 1, 2...
    ids = list(idx)
    puntos = np.array([modelo.nodos[nid].coords for nid in ids], dtype=float)

    # Barras: cada línea es [2, punto_i, punto_j]; las sin material o sección, en un gris más claro
    if modelo.elementos:
        lineas, base = [], []
        for k, (eid, el) in enumerate(modelo.elementos.items()):
            lineas += [2, idx[el.ni], idx[el.nj]]
            sin = el.material is None or el.seccion is None
            base.append(colores.rgb(colores.SIN_ASIGNAR if sin else colores.ELEMENTO))
            d.indice_barra[eid] = k
        malla = pv.PolyData(puntos, lines=np.array(lineas))
        d.base["barras"] = np.array(base, dtype=np.uint8)
        malla.cell_data["color"] = d.base["barras"].copy()
        d.mallas["barras"] = malla
        d.actores["barras"] = _agregar(vista, "barras", malla, por_celda=True, linea=ui.GROSOR_BARRA)

    # Nodos
    malla = pv.PolyData(puntos)
    d.base["nodos"] = _rgb(colores.ELEMENTO, len(ids))
    malla.point_data["color"] = d.base["nodos"].copy()
    d.indice_nodo = {nid: i for i, nid in enumerate(ids)}
    d.mallas["nodos"] = malla
    d.actores["nodos"] = _agregar(vista, "nodos", malla, por_celda=False, punto=ui.TAMANO_NODO)

    # Apoyos: nodos con algún GDL restringido, como esferas más grandes del mismo gris
    apoyos = [nid for nid in ids if any(modelo.nodos[nid].apoyo)]
    if apoyos:
        malla = pv.PolyData(puntos[[idx[nid] for nid in apoyos]])
        d.base["apoyos"] = _rgb(colores.ELEMENTO, len(apoyos))
        malla.point_data["color"] = d.base["apoyos"].copy()
        d.indice_apoyo = {nid: i for i, nid in enumerate(apoyos)}
        d.mallas["apoyos"] = malla
        d.actores["apoyos"] = _agregar(vista, "apoyos", malla, por_celda=False,
                                       punto=ui.FACTOR_APOYO * ui.TAMANO_NODO)

    # Número de cada nodo, un poco arriba del punto
    tamano = np.ptp(puntos, axis=0).max() or 1.0      # tamaño del modelo
    arriba = puntos + [0, 0, ui.SEPARACION_ETIQUETA * tamano]
    d.actores["etiquetas"] = vista.add_point_labels(
        arriba, [str(nid) for nid in ids], font_size=ui.TAMANO_LETRA,
        text_color=colores.ETIQUETA, shape=None, show_points=False, always_visible=True,
        name="etiquetas", reset_camera=False)
    return d


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
    """Punto y línea que muestran dónde va a quedar el nodo o la barra antes de colocarlos.

    Mismo gris y mismo tamaño que un nodo o una barra sin seleccionar, pero transparente. Se crean
    una sola vez y después solo se mueven sus puntos (mucho más rápido que volver a crearlos).
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
        """Toma el color, la transparencia y los tamaños vigentes."""
        color = [c / 255 for c in colores.rgb(colores.ELEMENTO)]
        for actor in (self.actor_puntos, self.actor_linea):
            actor.GetProperty().SetColor(color)
            actor.GetProperty().SetOpacity(ui.OPACIDAD_PREVISUALIZACION)
        self.actor_puntos.GetProperty().SetPointSize(ui.TAMANO_NODO)
        self.actor_linea.GetProperty().SetLineWidth(ui.GROSOR_BARRA)

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
