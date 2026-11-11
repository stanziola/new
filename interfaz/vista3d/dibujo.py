"""Dibujo del modelo en la vista 3D: barras, nodos, apoyos, números de nodo, rejilla y previsualización.

Apoyos: el apoyo fijo es un cono con la punta en el nodo; el empotrado, una placa bajo el nodo.
Su tamaño es una fracción del modelo (ui.TAMANO_APOYO), porque son objetos 3D, no píxeles.

Sección real: una barra con sección rectangular se puede dibujar como una caja de b × h a lo largo
de su eje. Sus esquinas son los nodos ± b/2 en el eje local y y ± h/2 en el local z (las filas de
calculo.rigidez.barra.rotacion son los ejes locales escritos en globales). Las barras sin sección siguen
como línea.

Nudos: donde se encuentran dos o más barras con sección, sus cajas (que van de nodo a nodo) dejarían
un hueco o se encimarían. Por eso en cada nudo va un bloque de concreto y las barras se recortan en
sus caras (nudos). El bloque usa los ejes de la columna que llega al nudo (o, si no hay, los de la
barra de mayor sección) y, en cada uno de esos tres ejes, mide lo que la mayor de las secciones de
las barras que NO van a lo largo de ese eje: en un nudo viga–columna queda la sección de la columna
por el peralte de la viga, ensanchado si la viga es más ancha. Es parte del nodo: se pinta y se
selecciona con él. Es solo dibujo: el análisis sigue de nodo a nodo (sin brazos rígidos).

Transparencia y acero: las cajas de la sección real pueden dibujarse transparentes (opacidad < 1).
Entonces se dibuja también el acero longitudinal de las barras con sección rectangular y refuerzo,
columnas y vigas: un tubo por barra de refuerzo, con su diámetro real, de nodo a nodo, en las
posiciones del arreglo Nx × Ny de la sección. Es un dibujo esquemático: sin estribos, traslapes ni
ganchos, y en los nudos las barras de unas y otras se cruzan sin anclarse. En una viga es el arreglo
de su sección (Nx arriba y abajo), no un armado diseñado: ese llega con el diseño de vigas.

Ejes locales: los x, y, z de la barra seleccionada, como tres flechas con los colores de los ejes
globales de la esquina (dibujar_ejes_locales). Los diagramas N, V, M y T están en esos ejes.

Colores por elemento: cada barra, nodo y apoyo tiene su color guardado en su malla (un arreglo
RGB). Para marcar lo seleccionado (gris oscuro) o lo relacionado y lo que está bajo el mouse (un
gris intermedio) solo se cambia ese color: no se dibuja nada encima. Así el tamaño es el mismo y no hay parpadeo (dos objetos en el mismo lugar se
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
from modelo.interaccion import diametro_barra, posiciones_barras

PARALELA = 0.999                   # |coseno| desde el cual una barra va "a lo largo" de un eje del nudo
RECORTE_MAXIMO = 0.45              # el nudo no le quita a una barra más que esta fracción de su largo
POSICION_EJES_LOCALES = 0.15       # dónde van los ejes locales: fracción del largo, desde el nodo i


class ModeloDibujado:
    """Lo dibujado de un modelo: actores, mallas y de qué ID es cada barra, nodo y apoyo."""

    def __init__(self):
        self.actores = {}          # "barras", "nodos", "apoyos", "etiquetas", "rejilla"
        self.mallas = {}           # "barras", "nodos", "apoyos"
        self.base = {}             # color sin resaltar de cada celda o punto de cada malla
        self.indice_barra = {}     # ID de barra -> celda en la malla "barras"
        self.indice_nodo = {}      # ID de nodo -> punto en la malla "nodos"
        self.indice_apoyo = {}     # ID de nodo -> celdas (inicio, fin) en la malla "apoyos"
        self.cajas_apoyo = {}      # ID de nodo -> caja 3D de su cono o placa (para seleccionarlo)
        self.indice_solido = {}    # ID de barra -> celdas (inicio, fin) en la malla "solidos"
        self.indice_nudo = {}      # ID de nodo -> celdas (inicio, fin) de su bloque en la malla "solidos"
        self.cajas_nudo = {}       # ID de nodo -> caja 3D de su bloque (un clic sobre él elige el nodo)

    def _lugares(self, item):
        """Dónde está pintado un ("nodo", id), ("apoyo", id) o ("barra", id): lista de (malla, índice).

        Un nodo es su punto y, con la sección real, el bloque de su nudo. Un apoyo es solo su cono o
        su placa: el apoyo de un nodo seleccionado se pinta aparte, como relacionado (lo decide la
        ventana)."""
        if item is None:
            return []
        tipo, ident = item
        if tipo == "apoyo":
            return [("apoyos", slice(*self.indice_apoyo[ident]))] if ident in self.indice_apoyo else []
        if tipo == "barra":
            lugares = []
            if ident in self.indice_barra:
                lugares.append(("barras", self.indice_barra[ident]))
            if ident in self.indice_solido:
                lugares.append(("solidos", slice(*self.indice_solido[ident])))
            return lugares
        if tipo == "nodo":
            lugares = []
            if ident in self.indice_nodo:
                lugares.append(("nodos", self.indice_nodo[ident]))
            if ident in self.indice_nudo:
                lugares.append(("solidos", slice(*self.indice_nudo[ident])))
            return lugares
        return []

    def pintar(self, resaltado=None, seleccion=None, enlazados=()):
        """Colores vigentes, en este orden (el último gana): base gris; lo relacionado con la
        selección (los nodos y apoyos de una barra, el apoyo y las barras de un nodo) y lo que está
        bajo el mouse, en un gris intermedio (RESALTADO); y lo seleccionado, en gris oscuro."""
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


def _caja(pi, pj, ey, ez):
    """Caja entre los puntos pi y pj. ey y ez son vectores: la media dimensión en cada lado."""
    esquinas = [p + sy * ey + sz * ez for p in (pi, pj) for sy, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    caras = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
    return pv.PolyData(np.array(esquinas), np.hstack([[4] + c for c in caras]))


def _ejes_barra(modelo, el):
    """(pi, pj, R, largo) de una barra: sus extremos y sus ejes locales (las filas de R)."""
    pi = np.asarray(modelo.nodos[el.ni].coords, dtype=float)
    pj = np.asarray(modelo.nodos[el.nj].coords, dtype=float)
    beta, gamma, largo = angulos(pi, pj)
    return pi, pj, rotacion(np.radians(el.alfa), beta, gamma), largo


def caja_barra(pi, pj, alfa_grados, b, h, recorte_i=0.0, recorte_j=0.0):
    """Caja de b × h entre los puntos pi y pj (b en el eje local y, h en el local z). Los recortes
    la acortan en cada extremo: es lo que ocupa el bloque del nudo."""
    pi, pj = np.asarray(pi, float), np.asarray(pj, float)
    beta, gamma, _ = angulos(pi, pj)
    r = rotacion(np.radians(alfa_grados), beta, gamma)
    return _caja(pi + r[0] * recorte_i, pj - r[0] * recorte_j, r[1] * b / 2, r[2] * h / 2)


def nudos(modelo, con_caja):
    """Bloque de concreto de cada nudo y lo que se recorta cada barra que llega a él.

    con_caja: {ID de barra: Concreto} de las barras que se dibujan con su sección. Devuelve
    (bloques, recortes):
    - bloques: {ID de nodo: (centro, ejes, medias)}. Una caja centrada en el nodo; `ejes` son los
      tres ejes del nudo (filas) y `medias`, su media dimensión en cada uno;
    - recortes: {(ID de barra, ID de nodo): distancia} que se acorta la caja de la barra en ese
      extremo, para terminar en la cara del bloque.

    Ejes del nudo: los locales de la columna que llega (si hay) o de la barra de mayor sección.
    Media dimensión en un eje `a`: la mayor, entre las barras que no van a lo largo de `a`, de lo
    que mide su sección en esa dirección, |a·y|·b/2 + |a·z|·h/2 (y, z: sus ejes locales). Ejemplo:
    columna de 40×40 y vigas de 30×50 en X y en Y → bloque de 40×40×50.
    Si alguna media da 0 (dos barras en línea, sin nada que las cruce) no hay bloque. Solo se
    recortan las barras que van a lo largo de un eje del nudo; una inclinada llega hasta el nodo."""
    datos = {eid: _ejes_barra(modelo, modelo.elementos[eid]) for eid in con_caja}
    llegan = {}                                        # ID de nodo -> barras con caja que llegan a él
    for eid in con_caja:
        el = modelo.elementos[eid]
        for nid in (el.ni, el.nj):
            llegan.setdefault(nid, []).append(eid)
    bloques, recortes = {}, {}
    for nid, barras in llegan.items():
        if len(barras) < 2:
            continue
        principal = max(barras, key=lambda e: (modelo.es_columna(e), con_caja[e].b * con_caja[e].h))
        ejes = datos[principal][2]
        medias = np.zeros(3)
        for k, a in enumerate(ejes):
            for eid in barras:
                r, c = datos[eid][2], con_caja[eid]
                if abs(a @ r[0]) < PARALELA:           # esta barra cruza el eje: su sección cuenta
                    medias[k] = max(medias[k], abs(a @ r[1]) * c.b / 2 + abs(a @ r[2]) * c.h / 2)
        if medias.min() <= 1e-9:
            continue
        bloques[nid] = (np.asarray(modelo.nodos[nid].coords, dtype=float), ejes, medias)
        for eid in barras:
            r, largo = datos[eid][2], datos[eid][3]
            for k, a in enumerate(ejes):
                if abs(a @ r[0]) >= PARALELA:
                    recortes[(eid, nid)] = min(medias[k], RECORTE_MAXIMO * largo)
    return bloques, recortes


def _unir(mallas):
    """Une mallas en una sola, conservando el orden de sus celdas (para saber cuál es cuál)."""
    union = vtkAppendPolyData()
    for m in mallas:
        union.AddInputData(m)
    union.Update()
    return pv.wrap(union.GetOutput())


def seccion_rectangular(modelo, el):
    """El Concreto rectangular de la sección de la barra, o None."""
    sec = modelo.secciones.get(el.seccion) if el.seccion is not None else None
    c = sec.concreto if sec is not None else None
    return c if c is not None and c.forma == "rectangular" and c.b > 0 and c.h > 0 else None


def acero_longitudinal(modelo, barras):
    """Malla con el acero longitudinal de las barras (columnas y vigas), o None si ninguna tiene
    refuerzo.

    barras: {ID de barra: Concreto} de las barras que se dibujan con su sección. Cada barra de
    refuerzo es un tubo de su diámetro real, de nodo a nodo, a (y − b/2) en el eje local y y
    (z − h/2) en el local z del centro, como las cajas de caja_barra. Es el arreglo Nx × Ny de la
    sección: en los nudos, el acero de unas barras y otras se cruza sin anclarse."""
    por_radio = {}                                   # radio -> (puntos, líneas): un filtro tube por diámetro
    for eid, c in barras.items():
        if c.nx < 2 or c.ny < 2 or not 0 < c.d < min(c.b, c.h) / 2:
            continue
        pi, pj, r, _largo = _ejes_barra(modelo, modelo.elementos[eid])
        puntos, lineas = por_radio.setdefault(diametro_barra(c.barra) / 2, ([], []))
        for y, z in posiciones_barras(c):
            desplazado = r[1] * (y - c.b / 2) + r[2] * (z - c.h / 2)
            n = len(puntos)
            puntos += [pi + desplazado, pj + desplazado]
            lineas += [2, n, n + 1]
    tubos = [pv.PolyData(np.array(puntos), lines=np.array(lineas)).tube(radius=radio, n_sides=10, capping=True)
             for radio, (puntos, lineas) in por_radio.items()]
    if not tubos:
        return None
    return tubos[0].merge(tubos[1:]) if len(tubos) > 1 else tubos[0]


def dibujar_modelo(vista, modelo, seccion_real=True, opacidad=1.0):
    """Dibuja barras, nodos, apoyos y números de nodo. Devuelve un ModeloDibujado.

    Con seccion_real, las barras con sección rectangular se dibujan como cajas de b × h, con un
    bloque en cada nudo, y con la opacidad dada (1 = opaco). Con opacidad < 1 se dibuja también el
    acero longitudinal."""
    d = ModeloDibujado()
    if not modelo.nodos:
        return d

    idx = indices_nodos(modelo)                       # ID de nodo -> 0, 1, 2...
    ids = list(idx)
    puntos = np.array([modelo.nodos[nid].coords for nid in ids], dtype=float)

    # Barras con sección real: una caja por barra (recortada en sus nudos) y un bloque por nudo,
    # todo en una malla
    con_caja = {eid: c for eid, el in modelo.elementos.items()
                if seccion_real and (c := seccion_rectangular(modelo, el)) is not None}
    if con_caja:
        bloques, recortes = nudos(modelo, con_caja)
        cajas, inicio = [], 0
        for eid, c in con_caja.items():
            el = modelo.elementos[eid]
            caja = caja_barra(modelo.nodos[el.ni].coords, modelo.nodos[el.nj].coords, el.alfa, c.b, c.h,
                              recortes.get((eid, el.ni), 0.0), recortes.get((eid, el.nj), 0.0))
            d.indice_solido[eid] = (inicio, inicio + caja.n_cells)
            inicio += caja.n_cells
            cajas.append(caja)
        for nid, (centro, ejes, medias) in bloques.items():
            bloque = _caja(centro - ejes[0] * medias[0], centro + ejes[0] * medias[0],
                           ejes[1] * medias[1], ejes[2] * medias[2])
            d.indice_nudo[nid] = (inicio, inicio + bloque.n_cells)
            d.cajas_nudo[nid] = tuple(float(v) for v in bloque.bounds)
            inicio += bloque.n_cells
            cajas.append(bloque)
        malla = _unir(cajas)
        d.base["solidos"] = _rgb(colores.ELEMENTO, malla.n_cells)
        malla.cell_data["color"] = d.base["solidos"].copy()
        d.mallas["solidos"] = malla
        d.actores["solidos"] = _agregar(vista, "solidos", malla, por_celda=True)
        d.actores["solidos"].GetProperty().SetOpacity(opacidad)
        acero = acero_longitudinal(modelo, con_caja) if opacidad < 1 else None
        if acero is not None:                         # se ve a través del concreto transparente
            d.actores["acero"] = vista.add_mesh(acero, color=colores.ACERO, pickable=False,
                                                reset_camera=False, name="acero", render=False)

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
            d.cajas_apoyo[nid] = tuple(float(v) for v in forma.bounds)
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


def dibujar_ejes_locales(vista, modelo, eid, tamano, seccion_real=False):
    """Ejes locales x, y, z de la barra eid: tres flechas con los colores de los ejes globales de la
    esquina (x rojo, y verde, z azul) y su letra. Devuelve {"ejes_locales": actor,
    "letras_ejes_locales": actor}.

    Van cerca del nodo i (el origen de x), a POSICION_EJES_LOCALES del largo. Con la sección real,
    salen de la arista +y, +z de la caja y no del eje: si no, el concreto taparía la flecha de x.
    Las fuerzas internas N, V, M y T de la barra están en estos ejes: N a lo largo de x; My, Vz, N y
    T se dibujan en el plano x–z y Mz y Vy en el x–y."""
    el = modelo.elementos[eid]
    pi, _pj, r, largo = _ejes_barra(modelo, el)
    origen = pi + r[0] * POSICION_EJES_LOCALES * largo
    c = seccion_rectangular(modelo, el) if seccion_real else None
    if c is not None:
        origen = origen + r[1] * c.b / 2 + r[2] * c.h / 2
    lado = min(ui.TAMANO_CARGA * tamano, 0.5 * largo)
    flechas = []
    for eje, color in zip(r, (colores.EJE_X, colores.EJE_Y, colores.EJE_Z)):
        flecha = pv.Arrow(start=origen, direction=eje, scale=lado, tip_length=0.28, tip_radius=0.09,
                          shaft_radius=0.03)
        flecha.cell_data["color"] = _rgb(color, flecha.n_cells)
        flechas.append(flecha)
    actores = {"ejes_locales": _agregar(vista, "ejes_locales", _unir(flechas), por_celda=True)}
    actores["ejes_locales"].SetUseBounds(False)
    actores["letras_ejes_locales"] = vista.add_point_labels(
        np.array([origen + eje * lado * 1.12 for eje in r]), ["x", "y", "z"], font_size=ui.TAMANO_LETRA,
        text_color=colores.ETIQUETA, shape=None, show_points=False, always_visible=True,
        name="letras_ejes_locales", reset_camera=False)
    return actores


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
