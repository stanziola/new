"""Puente entre el modelo y el cálculo: arma las cargas de cada caso, resuelve y prepara resultados.

No tiene fórmulas de ingeniería (están en calculo/): junta datos, cambia de ejes y llama.
Para cada caso de carga:
1. Cargas nodales del caso, en el vector F (orden de K: el de los nodos del modelo).
2. Cargas en barras del caso, más el peso propio (A·γ·factor del caso, global −Z), pasadas a ejes
   locales con R (las filas de R son los ejes locales escritos en globales).
3. FEF de cada barra cargada (calculo/rigidez/empotramiento.py) y su aporte a F: −Tᵀ·FEF.
4. resolver(modelo, F, fef) (calculo/rigidez/solucion.py).
Los diagramas y la deformada de una barra se calculan cuando se piden (calculo/rigidez/diagramas.py).
"""
from dataclasses import dataclass, field

import numpy as np

from calculo.rigidez import diagramas
from calculo.rigidez.barra import angulos, rotacion, transformacion
from calculo.rigidez.empotramiento import empotramiento
from calculo.rigidez.ensamble import gdl_barra, indices_nodos
from calculo.rigidez.solucion import resolver
from modelo.estructura import CargaBarra, CargaNodal

GLOBALES = {"X": 0, "Y": 1, "Z": 2}
LOCALES = {"x": 0, "y": 1, "z": 2}


@dataclass
class ResultadoCaso:
    caso: int
    res: object                                   # calculo.rigidez.resultados.Resultados
    cargas_locales: dict = field(default_factory=dict)   # ID de barra -> cargas en ejes locales


def geometria(modelo, eid):
    """(R, T, L) de una barra: rotación 3x3, transformación 12x12 y largo."""
    el = modelo.elementos[eid]
    pi, pj = modelo.nodos[el.ni].coords, modelo.nodos[el.nj].coords
    beta, gamma, largo = angulos(pi, pj)
    r = rotacion(np.radians(el.alfa), beta, gamma)
    return r, transformacion(r), largo


def _vector(r, direccion, valor):
    """La carga como vector en ejes locales: si la dirección es global, se pasa con R."""
    if direccion in LOCALES:
        v = np.zeros(3)
        v[LOCALES[direccion]] = valor
        return v
    g = np.zeros(3)
    g[GLOBALES[direccion]] = valor
    return r @ g


def cargas_locales(modelo, eid, caso):
    """Cargas de la barra en el caso, en ejes locales, más su peso propio."""
    r, _t, _l = geometria(modelo, eid)
    lista = []
    for c in modelo.cargas.values():
        if isinstance(c, CargaBarra) and c.barra == eid and c.caso == caso:
            lista.append((c.tipo, _vector(r, c.direccion, c.valor), None if c.tipo == "uniforme" else c.a))
    el = modelo.elementos[eid]
    factor = modelo.casos[caso].peso_propio
    mat, sec = modelo.materiales.get(el.material), modelo.secciones.get(el.seccion)
    if factor and mat is not None and sec is not None and mat.gamma:
        lista.append(("uniforme", r @ np.array([0.0, 0.0, -sec.a * mat.gamma * factor]), None))
    return lista


def peso_propio_total(modelo, caso):
    """Peso propio de todas las barras en el caso (kN), para comprobar el equilibrio."""
    total = 0.0
    factor = modelo.casos[caso].peso_propio
    for el in modelo.elementos.values():
        mat, sec = modelo.materiales.get(el.material), modelo.secciones.get(el.seccion)
        if factor and mat is not None and sec is not None and mat.gamma:
            total += sec.a * mat.gamma * factor * modelo.nodos[el.ni].distancia(modelo.nodos[el.nj])
    return total


def analizar_caso(modelo, caso):
    """Resuelve un caso de carga. ValueError si falta algo (sección, apoyos) o es inestable."""
    if caso not in modelo.casos:
        raise KeyError(f"El caso {caso} no existe")
    faltan = modelo.sin_asignar()
    if faltan:
        raise ValueError(f"Las barras {', '.join(map(str, faltan))} no tienen material o sección asignados")
    idx = indices_nodos(modelo)
    F = np.zeros(6 * len(idx))
    for c in modelo.cargas.values():
        if isinstance(c, CargaNodal) and c.caso == caso:
            F[6 * idx[c.nodo]:6 * idx[c.nodo] + 6] += c.fuerzas
    fef, locales = {}, {}
    for eid, el in modelo.elementos.items():
        lista = cargas_locales(modelo, eid, caso)
        if not lista:
            continue
        _r, t, largo = geometria(modelo, eid)
        fef[eid] = empotramiento(largo, lista)
        F[gdl_barra(idx[el.ni], idx[el.nj])] += t.T @ (-fef[eid])
        locales[eid] = lista
    return ResultadoCaso(caso, resolver(modelo, F, fef), locales)


def analizar(modelo):
    """Todos los casos: {ID de caso: ResultadoCaso}."""
    return {caso: analizar_caso(modelo, caso) for caso in modelo.casos}


def fuerzas_en(modelo, rc, eid):
    """Diagramas de la barra: {"x", "N", "Vy", "Vz", "T", "My", "Mz"} (ejes locales)."""
    _r, _t, largo = geometria(modelo, eid)
    return diagramas.internas(largo, rc.res.fuerzas[eid], rc.cargas_locales.get(eid, []))


def deformada_de(modelo, rc, eid):
    """Deformada de la barra: (puntos originales, desplazamientos globales) a lo largo de x."""
    el = modelo.elementos[eid]
    r, t, largo = geometria(modelo, eid)
    mat, sec = modelo.materiales[el.material], modelo.secciones[el.seccion]
    idx = indices_nodos(modelo)
    u_local = t @ rc.res.U[gdl_barra(idx[el.ni], idx[el.nj])]
    d = diagramas.deformada(largo, rc.res.fuerzas[eid], rc.cargas_locales.get(eid, []), u_local,
                            mat.e, mat.g, sec.a, sec.iy, sec.iz, sec.j)
    pi = np.asarray(modelo.nodos[el.ni].coords, dtype=float)
    puntos = pi + np.outer(d["x"], r[0])
    desplazamientos = np.column_stack([d["u"], d["v"], d["w"]]) @ r      # locales -> globales (Rᵀ)
    return puntos, desplazamientos
