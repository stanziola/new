"""Puente entre el modelo y el cálculo: arma las cargas de cada caso, resuelve y prepara resultados.

No tiene fórmulas de ingeniería (están en calculo/): junta datos, cambia de ejes y llama.
Para cada caso de carga:
1. Cargas nodales del caso, en el vector F (orden de K: el de los nodos del modelo).
2. Cargas en barras del caso, más el peso propio (A·γ·factor del caso, global −Z), pasadas a ejes
   locales con R (las filas de R son los ejes locales escritos en globales).
3. FEF de cada barra cargada (calculo/rigidez/empotramiento.py) y su aporte a F: −Tᵀ·FEF.
4. resolver(modelo, F, fef) (calculo/rigidez/solucion.py).
Los diagramas y la deformada de una barra se calculan cuando se piden (calculo/rigidez/diagramas.py).

Combinaciones: no se resuelven otra vez. Como el análisis es lineal (primer orden), el resultado de
1.2D + 1.6L es 1.2 × (resultado de D) + 1.6 × (resultado de L): superposición (combinar).
"""
from dataclasses import dataclass, field

import numpy as np

from calculo.rigidez import diagramas
from calculo.rigidez.barra import angulos, rotacion, transformacion
from calculo.rigidez.empotramiento import empotramiento
from calculo.rigidez.ensamble import gdl_barra, indices_nodos
from calculo.rigidez.resultados import Resultados
from calculo.rigidez.solucion import resolver
from modelo.estructura import CargaBarra, CargaNodal

GLOBALES = {"X": 0, "Y": 1, "Z": 2}
LOCALES = {"x": 0, "y": 1, "z": 2}


@dataclass
class ResultadoCaso:
    """Resultados de un caso o de una combinación (caso = None)."""
    caso: int
    res: object                                   # calculo.rigidez.resultados.Resultados
    cargas_locales: dict = field(default_factory=dict)   # ID de barra -> cargas en ejes locales
    nombre: str = ""                              # el del caso o la combinación (para mostrar)


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
    return ResultadoCaso(caso, resolver(modelo, F, fef), locales, modelo.casos[caso].nombre)


def analizar(modelo):
    """Todos los casos: {ID de caso: ResultadoCaso}."""
    return {caso: analizar_caso(modelo, caso) for caso in modelo.casos}


def combinar(modelo, resultados, coid):
    """Resultados de la combinación coid por superposición: Σ factor × (resultados del caso).

    resultados: {ID de caso: ResultadoCaso} (los de analizar). No se resuelve nada otra vez:
    - U, F, R, desplazamientos, reacciones y fuerzas en los extremos: la suma con los factores
      (K es la misma en todos los casos);
    - cargas en las barras: la lista de las de cada caso, con su vector por el factor. Así
      fuerzas_en y deformada_de dan el diagrama combinado, porque internas() y deformada() suman
      el efecto de cada carga por separado (son lineales)."""
    co = modelo.combinaciones[coid]
    partes = [(f, resultados[cid]) for cid, f in co.factores.items()]
    base = partes[0][1].res

    def suma(nombre):
        return sum(f * np.asarray(getattr(rc.res, nombre), dtype=float) for f, rc in partes)

    def suma_por_id(nombre):
        return {k: sum(f * np.asarray(getattr(rc.res, nombre)[k], dtype=float) for f, rc in partes)
                for k in getattr(base, nombre)}

    res = Resultados(ids=list(base.ids), K=base.K, F=suma("F"), U=suma("U"), R=suma("R"),
                     desplazamientos=suma_por_id("desplazamientos"), reacciones=suma_por_id("reacciones"),
                     fuerzas=suma_por_id("fuerzas"))
    cargas = {}
    for f, rc in partes:
        for eid, lista in rc.cargas_locales.items():
            cargas.setdefault(eid, []).extend((tipo, f * np.asarray(v, dtype=float), a) for tipo, v, a in lista)
    return ResultadoCaso(None, res, cargas, co.nombre)


def fuerzas_en(modelo, rc, eid):
    """Diagramas de la barra: {"x", "N", "Vy", "Vz", "T", "My", "Mz"} (ejes locales)."""
    _r, _t, largo = geometria(modelo, eid)
    return diagramas.internas(largo, rc.res.fuerzas[eid], rc.cargas_locales.get(eid, []))


def fuerzas_en_x(modelo, rc, eid, x):
    """Fuerzas internas en el corte x (m desde el nodo i, ejes locales): {"N", "Vy", "Vz", "T",
    "My", "Mz"}. Si en x hay una carga puntual, da el valor justo después de ella (como en
    diagramas.internas). x fuera de la barra se lleva al extremo más cercano."""
    _r, _t, largo = geometria(modelo, eid)
    x = min(max(float(x), 0.0), largo)
    d = diagramas.internas(largo, rc.res.fuerzas[eid], rc.cargas_locales.get(eid, []), x=[x])
    return {k: float(d[k][0]) for k in diagramas.NOMBRES}


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
