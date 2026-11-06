import numpy as np
import pyvista as pv
from calculo.ensamble import indices_nodos
from interfaz import estilo as es

def dibujar_modelo(vista, modelo):
    """Dibuja barras, nodos, apoyos y números de nodo en la vista 3D."""
    if not modelo.nodos:
        return

    idx = indices_nodos(modelo)                       # ID de nodo -> 0, 1, 2...
    ids = list(idx)
    puntos = np.array([modelo.nodos[nid].coords for nid in ids], dtype=float)

    # Barras: cada línea es [2, punto_i, punto_j]
    if modelo.elementos:
        lineas = []
        for el in modelo.elementos.values():
            lineas += [2, idx[el.ni], idx[el.nj]]
        barras = pv.PolyData(puntos, lines=np.array(lineas))
        vista.add_mesh(barras, color=es.COLOR_BARRA, line_width=es.GROSOR_BARRA)

    # Nodos
    vista.add_points(puntos, color=es.COLOR_NODO, point_size=es.TAMANO_NODO,
                     render_points_as_spheres=True)

    # Apoyos: nodos con algún GDL restringido
    apoyos = [i for i, nid in enumerate(ids) if any(modelo.nodos[nid].apoyo)]
    if apoyos:
        vista.add_points(puntos[apoyos], color=es.COLOR_APOYO, point_size=es.TAMANO_APOYO,
                         render_points_as_spheres=True)

    # Número de cada nodo, un poco arriba del punto
    tamano = np.ptp(puntos, axis=0).max() or 1.0      # tamaño del modelo
    arriba = puntos + [0, 0, es.SEPARACION_ETIQUETA * tamano]
    vista.add_point_labels(arriba, [str(nid) for nid in ids],
                           font_size=es.TAMANO_LETRA, text_color=es.COLOR_ETIQUETA,
                           shape=None, show_points=False, always_visible=True)