from dataclasses import dataclass
import numpy as np
from .tolerancias import COND_MAXIMA
from .ensamble import ensamblar_k, ensamblar_f, indices_nodos, gdl_barra
from .elemento import angulos, rotacion, transformacion, k_local

@dataclass
class Resultados:
    ids: list                # IDs de nodo en el orden de K
    K: np.ndarray            # matriz de rigidez global
    F: np.ndarray            # vector de cargas
    U: np.ndarray            # vector de desplazamientos
    R: np.ndarray            # vector de reacciones (0 en GDL libres)
    desplazamientos: dict    # id nodo -> [Dx, Dy, Dz, Phix, Phiy, Phiz]
    reacciones: dict         # id nodo con apoyo -> [Fx, Fy, Fz, Mx, My, Mz]
    fuerzas: dict            # id elemento -> 12 fuerzas en ejes locales

def vector_apoyos(modelo):
    """True en cada GDL restringido, en el orden de K."""
    return np.array([a for n in modelo.nodos.values() for a in n.apoyo], dtype=bool)

def resolver(modelo):
    """Resuelve K·U = F y calcula reacciones y fuerzas internas."""
    faltan = modelo.sin_asignar()
    if faltan:
        raise ValueError(f"Las barras {', '.join(map(str, faltan))} no tienen material o "
                         "sección asignados")
    K, ids = ensamblar_k(modelo)
    F = ensamblar_f(modelo)

    restringidos = vector_apoyos(modelo)
    libres = ~restringidos
    if not restringidos.any():
        raise ValueError("La estructura no tiene apoyos")
    if not libres.any():
        raise ValueError("Todos los GDL están restringidos: no hay nada que resolver")

    Kll = K[np.ix_(libres, libres)]
    if np.linalg.cond(Kll) > COND_MAXIMA:
        raise ValueError("La estructura es inestable (mecanismo): revisa apoyos y conexiones")

    U = np.zeros_like(F)
    U[libres] = np.linalg.solve(Kll, F[libres])

    R = K @ U - F
    R[libres] = 0.0

    desplazamientos = {nid: U[6*i:6*i+6] for i, nid in enumerate(ids)}
    reacciones = {nid: R[6*i:6*i+6] for i, nid in enumerate(ids)
                  if any(modelo.nodos[nid].apoyo)}
    fuerzas = fuerzas_internas(modelo, U)

    return Resultados(ids, K, F, U, R, desplazamientos, reacciones, fuerzas)

def fuerzas_internas(modelo, U):
    """Fuerzas en los extremos de cada barra, en ejes locales.

    Orden: [N, Vy, Vz, T, My, Mz] del nodo i, luego lo mismo del nodo j.
    Convención: fuerzas que los nodos ejercen sobre la barra.
    """
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
    return fuerzas