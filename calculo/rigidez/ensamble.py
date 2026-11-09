import numpy as np
from .barra import k_global_barra

def indices_nodos(modelo):
    """ID de nodo -> posición 0, 1, 2... en la matriz global."""
    return {nid: i for i, nid in enumerate(modelo.nodos)}

def gdl_barra(i, j):
    """Los 12 GDL globales de una barra entre las posiciones i y j."""
    return np.r_[6*i:6*i+6, 6*j:6*j+6]

def ensamblar_k(modelo):
    """Matriz de rigidez global. Devuelve K y la lista de IDs de nodo en el orden de K."""
    idx = indices_nodos(modelo)
    n_gdl = 6 * len(idx)
    K = np.zeros((n_gdl, n_gdl))

    for el in modelo.elementos.values():
        ni = modelo.nodos[el.ni]
        nj = modelo.nodos[el.nj]
        mat = modelo.materiales[el.material]
        sec = modelo.secciones[el.seccion]

        kb = k_global_barra(mat.e, mat.g, sec.a, sec.iy, sec.iz, sec.j,
                            ni.coords, nj.coords, np.radians(el.alfa))

        gdl = gdl_barra(idx[el.ni], idx[el.nj])
        K[np.ix_(gdl, gdl)] += kb

    return K, list(idx)
