"""Selección de nodos y barras con un clic en la vista 3D.

Se trabaja en coordenadas de pantalla (píxeles): cada nodo se proyecta a la pantalla y se busca
el más cercano al clic; si no hay ninguno lo bastante cerca, se busca la barra más cercana
(distancia del clic al segmento proyectado). Así la tolerancia es la misma sin importar el zoom.
"""
import numpy as np
from configuracion import FUERZAS, GDL


def a_pantalla(renderer, punto):
    """Coordenadas en píxeles (origen abajo a la izquierda) de un punto 3D."""
    renderer.SetWorldPoint(*punto, 1.0)
    renderer.WorldToDisplay()
    x, y, _ = renderer.GetDisplayPoint()
    return np.array([x, y])


def distancia_a_segmento(p, a, b):
    """Distancia del punto p al segmento ab (en 2D)."""
    ab = b - a
    largo2 = ab @ ab
    t = 0.0 if largo2 == 0 else np.clip((p - a) @ ab / largo2, 0.0, 1.0)
    return float(np.linalg.norm(p - (a + t * ab)))


def elemento_en(renderer, modelo, x, y, tol_px):
    """Nodo o barra bajo el clic (x, y): ("nodo", id), ("barra", id) o None.

    Los nodos tienen prioridad: si hay un nodo a menos de tol_px, gana el nodo.
    """
    clic = np.array([x, y], dtype=float)
    pantalla = {nid: a_pantalla(renderer, n.coords) for nid, n in modelo.nodos.items()}

    cercanos = [(float(np.linalg.norm(q - clic)), nid) for nid, q in pantalla.items()]
    if cercanos:
        d, nid = min(cercanos)
        if d <= tol_px:
            return ("nodo", nid)

    cercanas = [(distancia_a_segmento(clic, pantalla[el.ni], pantalla[el.nj]), eid)
                for eid, el in modelo.elementos.items()]
    if cercanas:
        d, eid = min(cercanas)
        if d <= tol_px:
            return ("barra", eid)
    return None


def texto_seleccion(modelo, seleccion):
    """Descripción corta del nodo o barra seleccionado, para la barra de estado."""
    tipo, ident = seleccion
    if tipo == "nodo":
        n = modelo.nodos[ident]
        x, y, z = n.coords
        texto = f"Nodo {ident}:  ({x:g}, {y:g}, {z:g})"
        if any(n.apoyo):
            texto += "  |  apoyo: " + ", ".join(g for g, r in zip(GDL, n.apoyo) if r)
        if any(n.carga):
            texto += "  |  carga: " + ", ".join(f"{f}={c:g}" for f, c in zip(FUERZAS, n.carga) if c)
        return texto
    el = modelo.elementos[ident]
    largo = modelo.nodos[el.ni].distancia(modelo.nodos[el.nj])
    material = modelo.materiales[el.material].nombre
    seccion = modelo.secciones[el.seccion].nombre
    return (f"Barra {ident}:  nodos {el.ni} → {el.nj}  |  {material}  |  {seccion}  |  "
            f"L = {largo:.3f}  |  α = {el.alfa:g}°")
