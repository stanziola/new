"""Selección de nodos y barras con un clic en la vista 3D.

Se trabaja en coordenadas de pantalla (píxeles): cada nodo se proyecta a la pantalla y se busca
el más cercano al clic; si no hay ninguno lo bastante cerca, se busca la barra más cercana
(distancia del clic al segmento proyectado). Así la tolerancia es la misma sin importar el zoom.
nodo_cercano también lo usa el snap para pegarse a nodos existentes.
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


def elemento_en(renderer, modelo, x, y, tol_px):
    """Nodo o barra bajo el clic (x, y): ("nodo", id), ("barra", id) o None.

    Los nodos tienen prioridad: si hay un nodo a menos de tol_px, gana el nodo.
    """
    nid = nodo_cercano(renderer, modelo, x, y, tol_px)
    if nid is not None:
        return ("nodo", nid)
    eid = barra_cercana(renderer, modelo, x, y, tol_px)
    return ("barra", eid) if eid is not None else None
