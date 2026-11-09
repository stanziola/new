import numpy as np
from ..tolerancias import COND_MAXIMA
from .ensamble import ensamblar_k, indices_nodos, gdl_barra
from .barra import angulos, rotacion, transformacion, k_local
from .resultados import Resultados

def vector_apoyos(modelo):
    """True en cada GDL restringido, en el orden de K."""
    return np.array([a for n in modelo.nodos.values() for a in n.apoyo], dtype=bool)

def resolver(modelo, F, fef=None):
    """Resuelve K·U = F y calcula reacciones y fuerzas en los extremos de las barras.

    F: vector global de cargas nodales del caso, en el orden de K. Incluye las cargas nodales
       equivalentes de las cargas en barras (−Tᵀ·FEF); lo arma modelo/analisis.py.
    fef: {ID de barra: 12 FEF locales} de las barras con cargas (ver empotramiento.py). Se suman a
       k·u para tener las fuerzas finales en los extremos."""
    faltan = modelo.sin_asignar()
    if faltan:
        raise ValueError(f"Las barras {', '.join(map(str, faltan))} no tienen material o "
                         "sección asignados")
    K, ids = ensamblar_k(modelo)
    F = np.asarray(F, dtype=float)
    if F.shape != (6 * len(ids),):
        raise ValueError(f"F debe tener {6 * len(ids)} valores (6 por nodo)")

    restringidos = vector_apoyos(modelo)
    libres = ~restringidos
    if not restringidos.any():
        raise ValueError("La estructura no tiene apoyos")

    U = np.zeros_like(F)
    if libres.any():          # si todo está restringido (una viga biempotrada sola), U = 0
        Kll = K[np.ix_(libres, libres)]
        if np.linalg.cond(Kll) > COND_MAXIMA:
            raise ValueError("La estructura es inestable (mecanismo): revisa apoyos y conexiones")
        U[libres] = np.linalg.solve(Kll, F[libres])

    R = K @ U - F
    R[libres] = 0.0

    desplazamientos = {nid: U[6*i:6*i+6] for i, nid in enumerate(ids)}
    reacciones = {nid: R[6*i:6*i+6] for i, nid in enumerate(ids)
                  if any(modelo.nodos[nid].apoyo)}
    fuerzas = fuerzas_internas(modelo, U, fef)

    return Resultados(ids, K, F, U, R, desplazamientos, reacciones, fuerzas)

def fuerzas_internas(modelo, U, fef=None):
    """Fuerzas en los extremos de cada barra, en ejes locales: k·u (+ FEF si la barra tiene cargas).

    Orden: [N, Vy, Vz, T, My, Mz] del nodo i, luego lo mismo del nodo j.
    Convención: fuerzas que los nodos ejercen sobre la barra.
    """
    fef = fef or {}
    idx = indices_nodos(modelo)
    fuerzas = {}
    for eid, el in modelo.elementos.items():
        ni = modelo.nodos[el.ni]
        nj = modelo.nodos[el.nj]
        mat = modelo.materiales[el.material]
        sec = modelo.secciones[el.seccion]

        beta, gamma, l = angulos(ni.coords, nj.coords)
        t = transformacion(rotacion(np.radians(el.alfa), beta, gamma))

        u_global = U[gdl_barra(idx[el.ni], idx[el.nj])]
        u_local = t @ u_global
        fuerzas[eid] = k_local(mat.e, mat.g, sec.a, l, sec.iy, sec.iz, sec.j) @ u_local
        if eid in fef:
            fuerzas[eid] = fuerzas[eid] + fef[eid]
    return fuerzas