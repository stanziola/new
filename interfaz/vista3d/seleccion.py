"""Selección de nodos, apoyos y barras con un clic en la vista 3D.

Se trabaja en coordenadas de pantalla (píxeles): cada nodo se proyecta a la pantalla y se busca
el más cercano al clic; si no hay ninguno lo bastante cerca, se mira si el clic cae sobre el bloque
de un nudo (con la sección real, el bloque tapa el punto del nodo y vale como nodo) o sobre el
dibujo de un apoyo (el cono o la placa, debajo del nodo); y si tampoco, se busca la barra más
cercana (distancia del clic al segmento proyectado). Así la tolerancia es la misma sin importar el
zoom. nodo_cercano también lo usa el snap para pegarse a nodos existentes.
"""
import numpy as np


def a_pantalla(renderer, punto):
    """Coordenadas en píxeles (origen abajo a la izquierda) de un punto 3D."""
    renderer.SetWorldPoint(*punto, 1.0)
    renderer.WorldToDisplay()
    x, y, _ = renderer.GetDisplayPoint()
    return np.array([x, y])


def proyectar(renderer, puntos):
    """Muchos puntos 3D a la pantalla de una vez (para el snap a la rejilla 3D).

    Usa la matriz de la cámara (mundo -> coordenadas normalizadas de -1 a 1) y la pasa a píxeles
    como hace VTK. Da lo mismo que a_pantalla punto por punto, pero en una sola operación de numpy.
    Devuelve (xy en píxeles, profundidad de -1 a 1, cuáles están delante de la cámara)."""
    puntos = np.asarray(puntos, dtype=float)
    camara = renderer.GetActiveCamera()
    m = camara.GetCompositeProjectionTransformMatrix(renderer.GetTiledAspectRatio(), -1, 1)
    matriz = np.array([[m.GetElement(i, j) for j in range(4)] for i in range(4)])
    h = np.column_stack([puntos, np.ones(len(puntos))]) @ matriz.T
    w = h[:, 3]
    delante = w > 1e-12
    w = np.where(delante, w, 1.0)
    ndc = h[:, :3] / w[:, None]
    ancho, alto = renderer.GetSize()
    x0, y0 = renderer.GetOrigin()
    xy = np.column_stack([(ndc[:, 0] + 1) * ancho / 2 + x0, (ndc[:, 1] + 1) * alto / 2 + y0])
    return xy, ndc[:, 2], delante


def distancia_a_segmento(p, a, b):
    """Distancia del punto p al segmento ab (en 2D)."""
    ab = b - a
    largo2 = ab @ ab
    t = 0.0 if largo2 == 0 else np.clip((p - a) @ ab / largo2, 0.0, 1.0)
    return float(np.linalg.norm(p - (a + t * ab)))


def nodo_cercano(renderer, modelo, x, y, tol_px):
    """ID del nodo más cercano al punto (x, y) de la pantalla, si está a menos de tol_px; o None."""
    clic = np.array([x, y], dtype=float)
    cercanos = [(float(np.linalg.norm(a_pantalla(renderer, n.coords) - clic)), nid)
                for nid, n in modelo.nodos.items()]
    if cercanos:
        d, nid = min(cercanos)
        if d <= tol_px:
            return nid
    return None


def barra_cercana(renderer, modelo, x, y, tol_px):
    """ID de la barra más cercana al punto (x, y) de la pantalla, si está a menos de tol_px; o None."""
    clic = np.array([x, y], dtype=float)
    pantalla = {nid: a_pantalla(renderer, n.coords) for nid, n in modelo.nodos.items()}
    cercanas = [(distancia_a_segmento(clic, pantalla[el.ni], pantalla[el.nj]), eid)
                for eid, el in modelo.elementos.items()]
    if cercanas:
        d, eid = min(cercanas)
        if d <= tol_px:
            return eid
    return None


def apoyo_en(renderer, cajas, x, y):
    """ID del nodo cuyo apoyo está bajo el punto (x, y) de la pantalla, o None.

    cajas: {ID de nodo: (xmin, xmax, ymin, ymax, zmin, zmax)}, la caja 3D del cono o la placa de cada
    apoyo (la guarda dibujo.ModeloDibujado). Se proyectan sus 8 esquinas y se mira si el clic cae en
    el rectángulo que ocupan en la pantalla; si cae en varios, gana el de centro más cercano."""
    clic = np.array([x, y], dtype=float)
    mejor = None
    for nid, (x0, x1, y0, y1, z0, z1) in cajas.items():
        esquinas = [(a, b, c) for a in (x0, x1) for b in (y0, y1) for c in (z0, z1)]
        xy, _profundidad, delante = proyectar(renderer, esquinas)
        if not delante.all():
            continue
        bajo, alto = xy.min(axis=0), xy.max(axis=0)
        if np.all(clic >= bajo) and np.all(clic <= alto):
            distancia = float(np.linalg.norm((bajo + alto) / 2 - clic))
            if mejor is None or distancia < mejor[0]:
                mejor = (distancia, nid)
    return mejor[1] if mejor else None


def nodo_en(renderer, modelo, x, y, tol_px, cajas_nudo=None):
    """ID del nodo bajo el clic (x, y), o None: el que está a menos de tol_px o, con la sección real
    a la vista, aquel sobre cuyo bloque de nudo cae el clic (cajas_nudo: las cajas 3D de los
    bloques, como en apoyo_en). El bloque tapa el punto del nodo: por eso también vale como nodo."""
    nid = nodo_cercano(renderer, modelo, x, y, tol_px)
    if nid is None and cajas_nudo:
        nid = apoyo_en(renderer, cajas_nudo, x, y)
    return nid


def _dentro(p, poligono):
    """True si el punto p (2D) está dentro del polígono convexo (en cualquier sentido de giro)."""
    signos = []
    for a, b in zip(poligono, np.roll(poligono, -1, axis=0)):
        cruz = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        if abs(cruz) > 1e-9:
            signos.append(cruz > 0)
    return bool(signos) and (all(signos) or not any(signos))


def pano_en(renderer, esquinas, x, y, con_profundidad=False):
    """ID del paño de losa bajo el clic (x, y), o None. esquinas: {ID de paño: sus 4 esquinas 3D}
    (las guarda dibujo.ModeloDibujado). Si el clic cae en varios, gana el más cercano a la cámara.
    con_profundidad: devuelve (ID, profundidad de -1 a 1) o None."""
    clic = np.array([x, y], dtype=float)
    mejor = None
    for pid, puntos in esquinas.items():
        xy, profundidad, delante = proyectar(renderer, puntos)
        if not delante.all() or not _dentro(clic, xy):
            continue
        if mejor is None or profundidad.mean() < mejor[0]:
            mejor = (float(profundidad.mean()), pid)
    if mejor is None:
        return None
    return (mejor[1], mejor[0]) if con_profundidad else mejor[1]


def elemento_en(renderer, modelo, x, y, tol_px, cajas_apoyo=None, cajas_nudo=None, esquinas_pano=None):
    """Nodo, apoyo, barra o paño de losa bajo el clic (x, y): ("nodo", id), ("apoyo", id del nodo),
    ("barra", id), ("pano", id) o None.

    Prioridad: el nodo (si hay uno a menos de tol_px, o si el clic cae sobre el bloque de su nudo),
    después el apoyo (si el clic cae sobre su dibujo; cajas_apoyo como en apoyo_en), la barra y por
    último el paño de losa (si el clic cae dentro de él; esquinas_pano como en pano_en). Un paño que
    tapa a un apoyo (está más cerca de la cámara) gana: la losa está delante del apoyo de abajo.
    """
    nid = nodo_en(renderer, modelo, x, y, tol_px, cajas_nudo)
    if nid is not None:
        return ("nodo", nid)
    pano = pano_en(renderer, esquinas_pano, x, y, con_profundidad=True) if esquinas_pano else None
    if cajas_apoyo:
        aid = apoyo_en(renderer, cajas_apoyo, x, y)
        if aid is not None:
            x0, x1, y0, y1, z0, z1 = cajas_apoyo[aid]
            _xy, profundidad, _d = proyectar(renderer, [((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)])
            if pano is None or float(profundidad[0]) < pano[1]:
                return ("apoyo", aid)
    eid = barra_cercana(renderer, modelo, x, y, tol_px)
    if eid is not None:
        return ("barra", eid)
    if pano is not None:
        return ("pano", pano[0])
    return None
