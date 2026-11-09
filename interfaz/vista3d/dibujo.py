"""Dibujo del modelo en la vista 3D: barras, nodos, apoyos, números de nodo, rejilla y previsualización.

Apoyos: el apoyo fijo es un cono con la punta en el nodo; el empotrado, una placa bajo el nodo.
Su tamaño es una fracción del modelo (ui.TAMANO_APOYO), porque son objetos 3D, no píxeles.

Sección real: una barra con sección rectangular se puede dibujar como una caja de b × h a lo largo
de su eje. Sus esquinas son los nodos ± b/2 en el eje local y y ± h/2 en el local z (las filas de
calculo.rigidez.barra.rotacion son los ejes locales escritos en globales). Las barras sin sección siguen
como línea.

Colores por elemento: cada barra, nodo y apoyo tiene su color guardado en su malla (un arreglo
RGB). Para resaltar (gris oscuro) o seleccionar (negro) solo se cambia ese color: no se dibuja
nada encima. Así el tamaño es el mismo y no hay parpadeo (dos objetos en el mismo lugar se
"pelean" por verse cuando la tarjeta de video decide cuál está adelante).
Nada de esto mueve la cámara (reset_camera=False): agregar un nodo no debe cambiar la vista.
"""
import numpy as np
import pyvista as pv
from vtkmodules.vtkFiltersCore import vtkAppendPolyData
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
from calculo.rigidez.barra import angulos, rotacion
from calculo.rigidez.ensamble import indices_nodos
from configuracion import colores
from configuracion import interfaz as ui
from modelo.apoyos import tipo_de


class ModeloDibujado:
    """Lo dibujado de un modelo: actores, mallas y de qué ID es cada barra, nodo y apoyo."""

    def __init__(self):
        self.actores = {}          # "barras", "nodos", "apoyos", "etiquetas", "rejilla"
        self.mallas = {}           # "barras", "nodos", "apoyos"
        self.base = {}             # color sin resaltar de cada celda o punto de cada malla
        self.indice_barra = {}     # ID de barra -> celda en la malla "barras"
        self.indice_nodo = {}      # ID de nodo -> punto en la malla "nodos"
        self.indice_apoyo = {}     # ID de nodo -> celdas (inicio, fin) en la malla "apoyos"
        self.indice_solido = {}    # ID de barra -> celdas (inicio, fin) en la malla "solidos"

    def _lugares(self, item):
        """Dónde está pintado un ("nodo", id) o ("barra", id): lista de (malla, índice)."""
        if item is None:
            return []
        tipo, ident = item
        if tipo == "barra":
            lugares = []
            if ident in self.indice_barra:
                lugares.append(("barras", self.indice_barra[ident]))
            if ident in self.indice_solido:
                lugares.append(("solidos", slice(*self.indice_solido[ident])))
            return lugares
        if tipo == "nodo" and ident in self.indice_nodo:
            lugares = [("nodos", self.indice_nodo[ident])]
            if ident in self.indice_apoyo:
                lugares.append(("apoyos", slice(*self.indice_apoyo[ident])))
            return lugares
        return []

    def pintar(self, resaltado=None, seleccion=None, enlazados=()):
        """Colores vigentes, en este orden (el último gana): base gris; lo enlazado a la selección
        (los nodos y apoyos de una barra) y lo que está bajo el mouse, en gris oscuro; y lo
        seleccionado, en negro."""
        nuevos = {nombre: base.copy() for nombre, base in self.base.items()}
        capas = [(item, colores.RESALTADO) for item in enlazados]
        capas += [(resaltado, colores.RESALTADO), (seleccion, colores.SELECCIONADO)]
        for item, color in capas:
            for malla, i in self._lugares(item):
                nuevos[malla][i] = colores.rgb(color)
        for nombre, malla in self.mallas.items():
            datos = malla.point_data if nombre == "nodos" else malla.cell_data
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


def _forma_apoyo(punto, apoyo, tamano):
    """Cono (apoyo fijo) o placa (empotrado u otra combinación) bajo el nodo, con el eje Z hacia arriba."""
    x, y, z = punto
    if tipo_de(apoyo) == "fijo":
        alto = tamano
        return pv.Cone(center=(x, y, z - alto / 2), direction=(0, 0, 1), height=alto,
                       radius=0.55 * tamano, resolution=24)
    lado, grueso = 0.75 * tamano, 0.22 * tamano
    return pv.Box(bounds=(x - lado, x + lado, y - lado, y + lado, z - grueso, z))


def caja_barra(pi, pj, alfa_grados, b, h):
    """Caja de b × h entre los puntos pi y pj (b en el eje local y, h en el local z)."""
    pi, pj = np.asarray(pi, float), np.asarray(pj, float)
    beta, gamma, _ = angulos(pi, pj)
    r = rotacion(np.radians(alfa_grados), beta, gamma)
    ey, ez = r[1] * b / 2, r[2] * h / 2
    esquinas = [p + sy * ey + sz * ez for p in (pi, pj) for sy, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    caras = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
    return pv.PolyData(np.array(esquinas), np.hstack([[4] + c for c in caras]))


def _unir(mallas):
    """Une mallas en una sola, conservando el orden de sus celdas (para saber cuál es cuál)."""
    union = vtkAppendPolyData()
    for m in mallas:
        union.AddInputData(m)
    union.Update()
    return pv.wrap(union.GetOutput())


def _rectangular(modelo, el):
    """El Concreto rectangular de la sección de la barra, o None."""
    sec = modelo.secciones.get(el.seccion) if el.seccion is not None else None
    c = sec.concreto if sec is not None else None
    return c if c is not None and c.forma == "rectangular" and c.b > 0 and c.h > 0 else None


def dibujar_modelo(vista, modelo, seccion_real=True):
    """Dibuja barras, nodos, apoyos y números de nodo. Devuelve un ModeloDibujado.

    Con seccion_real, las barras con sección rectangular se dibujan como cajas de b × h."""
    d = ModeloDibujado()
    if not modelo.nodos:
        return d

    idx = indices_nodos(modelo)                       # ID de nodo -> 0, 1, 2...
    ids = list(idx)
    puntos = np.array([modelo.nodos[nid].coords for nid in ids], dtype=float)

    # Barras con sección real: una caja por barra, todas en una malla
    con_caja = {eid: c for eid, el in modelo.elementos.items()
                if seccion_real and (c := _rectangular(modelo, el)) is not None}
    if con_caja:
        cajas, inicio = [], 0
        for eid, c in con_caja.items():
            el = modelo.elementos[eid]
            caja = caja_barra(modelo.nodos[el.ni].coords, modelo.nodos[el.nj].coords, el.alfa, c.b, c.h)
            d.indice_solido[eid] = (inicio, inicio + caja.n_cells)
            inicio += caja.n_cells
            cajas.append(caja)
        malla = _unir(cajas)
        d.base["solidos"] = _rgb(colores.ELEMENTO, malla.n_cells)
        malla.cell_data["color"] = d.base["solidos"].copy()
        d.mallas["solidos"] = malla
        d.actores["solidos"] = _agregar(vista, "solidos", malla, por_celda=True)

    # Barras como línea (las que no tienen caja); las sin material o sección, en un gris más claro
    lineales = [(eid, el) for eid, el in modelo.elementos.items() if eid not in con_caja]
    if lineales:
        lineas, base = [], []
        for k, (eid, el) in enumerate(lineales):
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

    tamano = np.ptp(puntos, axis=0).max() or 1.0      # tamaño del modelo

    # Apoyos: un cono o una placa por nodo con algún GDL restringido, del mismo gris
    apoyos = [nid for nid in ids if any(modelo.nodos[nid].apoyo)]
    if apoyos:
        formas, inicio = [], 0
        for nid in apoyos:
            forma = _forma_apoyo(puntos[idx[nid]], modelo.nodos[nid].apoyo, ui.TAMANO_APOYO * tamano)
            d.indice_apoyo[nid] = (inicio, inicio + forma.n_cells)
            inicio += forma.n_cells
            formas.append(forma)
        malla = _unir(formas)
        d.base["apoyos"] = _rgb(colores.ELEMENTO, malla.n_cells)
        malla.cell_data["color"] = d.base["apoyos"].copy()
        d.mallas["apoyos"] = malla
        d.actores["apoyos"] = _agregar(vista, "apoyos", malla, por_celda=True)

    # Número de cada nodo, un poco arriba del punto
    arriba = puntos + [0, 0, ui.SEPARACION_ETIQUETA * tamano]
    d.actores["etiquetas"] = vista.add_point_labels(
        arriba, [str(nid) for nid in ids], font_size=ui.TAMANO_LETRA,
        text_color=colores.ETIQUETA, shape=None, show_points=False, always_visible=True,
        name="etiquetas", reset_camera=False)
    # Número de cada barra, en su punto medio (Etiquetas → Números de barra)
    if modelo.elementos:
        medios = np.array([(np.asarray(modelo.nodos[el.ni].coords) + np.asarray(modelo.nodos[el.nj].coords)) / 2
                           for el in modelo.elementos.values()], dtype=float)
        d.actores["numeros_barras"] = vista.add_point_labels(
            medios, [f"[{eid}]" for eid in modelo.elementos], font_size=ui.TAMANO_LETRA - 2,
            text_color=colores.ETIQUETA, shape=None, show_points=False, always_visible=True,
            name="numeros_barras", reset_camera=False)
    return d


def dibujar_rejilla(vista, rejilla, cuenta_para_camara=False):
    """Dibuja la rejilla 3D (ver rejilla.geometria_rejilla) y devuelve su actor.

    - En cada nivel z, la planta: líneas paralelas a X (una por cada y) y a Y (una por cada x).
    - Cada planta queda un poco debajo de su nivel (0.1 % del tamaño del modelo), para que no se
      pise con las vigas que están justo en ese nivel.
    - Normalmente no cuenta para el encuadre ni para el zoom (SetUseBounds(False)): la vista se
      ajusta al modelo, no a la rejilla. Con el modelo vacío sí cuenta, para que se vea.
    """
    xs, ys = rejilla.xs, rejilla.ys
    segmentos = []
    for z in rejilla.zs - 0.001 * rejilla.escala:
        segmentos += [((xs[0], y, z), (xs[-1], y, z)) for y in ys]     # paralelas a X
        segmentos += [((x, ys[0], z), (x, ys[-1], z)) for x in xs]     # paralelas a Y
    pts = np.array([p for segmento in segmentos for p in segmento], dtype=float)
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
