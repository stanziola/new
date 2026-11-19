"""Puente entre el modelo y el cálculo: arma las cargas de cada caso, resuelve y prepara resultados.

No tiene fórmulas de ingeniería (están en calculo/): junta datos, cambia de ejes y llama.
Para cada caso de carga:
1. Cargas nodales del caso, en el vector F (orden de K: el de los nodos del modelo).
2. Cargas en barras del caso, más el peso propio (A·γ·factor del caso, global −Z), pasadas a ejes
   locales con R (las filas de R son los ejes locales escritos en globales).
3. FEF de cada barra cargada (calculo/rigidez/empotramiento.py) y su aporte a F: −Tᵀ·FEF.
4. resolver(modelo, F, fef) (calculo/rigidez/solucion.py).
Los diagramas y la deformada de una barra se calculan cuando se piden (calculo/rigidez/diagramas.py).

Peso propio: no es una carga guardada. En los casos con factor de peso propio (el caso "Peso
propio"), cada barra con material y sección recibe una uniforme de A·γ·factor hacia −Z global
(peso_propio_de). La interfaz la dibuja y la lista con esa misma función.

Losas: la carga de las losas de viguetas sobre sus vigas (modelo/losas.cargas_a_vigas: la reacción de
cada vigueta entre s) tampoco se guarda. Entra como una uniforme más hacia −Z global en el peso
propio, la carga muerta adicional y el caso "Viva de losas" (cargas_de_losas la da para dibujarla).

Combinaciones: no se resuelven otra vez. Como el análisis es lineal (primer orden), el resultado de
1.2D + 1.6L es 1.2 × (resultados de los casos tipo D) + 1.6 × (resultados de los tipo L):
superposición (combinar). Los factores van por tipo de caso. Con `casos`, solo entran esos casos: así
se arma una combinación con un caso de viva (patrón) de una vigueta (las vivas de sus claros).

Dos análisis por caso (decisión del usuario):
- de RESISTENCIA: las barras de concreto (material con f'c) con su inercia agrietada, 0.70·Ig en
  columnas y 0.35·Ig en vigas (calculo/concreto.factor_inercia, ACI 318-19 Tabla 6.6.3.1.1(a)). De
  él salen las fuerzas internas, las reacciones y los puntos Pu–Mu (ResultadoCaso.res);
- con la inercia BRUTA Ig: de él salen los desplazamientos y la deformada (ResultadoCaso.bruta, que
  da ResultadoCaso.deformacion). Es una simplificación: para servicio el ACI pide 1.4 × la inercia
  agrietada en los desplazamientos laterales (§6.6.3.2.2) e Ie en las flechas de vigas (§24.2).
Si ninguna barra es de concreto, los dos coinciden y se resuelve una sola vez (bruta = None).
"""
from dataclasses import dataclass, field, replace

import numpy as np

from calculo.concreto import factor_inercia
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
    res: object                                   # Resultados del análisis de resistencia (inercia agrietada)
    cargas_locales: dict = field(default_factory=dict)   # ID de barra -> cargas en ejes locales
    nombre: str = ""                              # el del caso o la combinación (para mostrar)
    bruta: object = None                          # Resultados con la inercia bruta Ig (None: igual a res)

    @property
    def deformacion(self):
        """Los Resultados de los que salen los desplazamientos y la deformada: los del análisis con
        la inercia bruta (o res, si no hay barras de concreto y los dos son el mismo)."""
        return self.bruta if self.bruta is not None else self.res


class ModeloAgrietado:
    """El modelo visto con la inercia del análisis con cargas mayoradas: cada barra de concreto
    (material con f'c) lleva su propia copia de la sección, con Iy e Iz por factor_inercia (0.70 si
    es columna, 0.35 si no). A y J no cambian. El cálculo lo lee como a un modelo cualquiera (nodos,
    elementos, materiales, secciones); todo lo demás se toma del modelo original, que no se toca.

    Que una barra sea columna lo decide Modelo.es_columna (vertical); las demás, también las
    inclinadas, van como vigas.

    factores: {ID de barra: factor} para usar otros (por ejemplo Ie/Ig de cada claro de una vigueta,
    en las deflexiones); las barras que no están ahí no cambian."""

    def __init__(self, modelo, factores=None):
        self._modelo = modelo
        self.elementos, self.secciones = dict(modelo.elementos), dict(modelo.secciones)
        self.cambia = False                       # True si alguna barra cambió (hay concreto)
        for eid, el in modelo.elementos.items():
            mat, sec = modelo.materiales.get(el.material), modelo.secciones.get(el.seccion)
            if mat is None or sec is None or mat.fc is None:
                continue
            if factores is not None and eid not in factores:
                continue
            f = factor_inercia(modelo.es_columna(eid)) if factores is None else factores[eid]
            clave = ("agrietada", eid)            # una sección por barra: la misma puede ser viga y columna
            self.secciones[clave] = replace(sec, iy=sec.iy * f, iz=sec.iz * f)
            self.elementos[eid] = replace(el, seccion=clave)
            self.cambia = True

    def __getattr__(self, nombre):
        return getattr(self._modelo, nombre)


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


def peso_propio_de(modelo, eid, caso):
    """Peso propio de la barra en el caso, como carga uniforme (kN/m, positiva): A·γ·factor del caso.
    0 si el caso no lleva peso propio o a la barra le falta el material o la sección. Va hacia −Z
    global, con la longitud entre nodos."""
    el = modelo.elementos[eid]
    factor = modelo.casos[caso].peso_propio
    mat, sec = modelo.materiales.get(el.material), modelo.secciones.get(el.seccion)
    if not factor or mat is None or sec is None or not mat.gamma:
        return 0.0
    return sec.a * mat.gamma * factor


def carga_de_peso_propio(modelo, eid, caso):
    """El peso propio de la barra en el caso como una CargaBarra (uniforme, hacia −Z global), para
    dibujarlo y listarlo igual que las cargas puestas a mano. No se guarda en el modelo. None si la
    barra no tiene peso propio en ese caso."""
    peso = peso_propio_de(modelo, eid, caso)
    return CargaBarra(caso, eid, "uniforme", -peso, "Z") if peso else None


def cargas_de_peso_propio(modelo, caso):
    """{ID de barra: CargaBarra} con el peso propio de cada barra en el caso (vacío si no lo lleva)."""
    if caso not in modelo.casos or not modelo.casos[caso].peso_propio:
        return {}
    cargas = {eid: carga_de_peso_propio(modelo, eid, caso) for eid in modelo.elementos}
    return {eid: c for eid, c in cargas.items() if c is not None}


def cargas_locales(modelo, eid, caso, losas=None):
    """Cargas de la barra en el caso, en ejes locales, más su peso propio y la carga de las losas
    (losas: {ID de barra: w} de este caso, kN/m hacia abajo; None = sin losas)."""
    r, _t, _l = geometria(modelo, eid)
    lista = []
    for c in modelo.cargas.values():
        if isinstance(c, CargaBarra) and c.barra == eid and c.caso == caso:
            lista.append((c.tipo, _vector(r, c.direccion, c.valor), None if c.tipo == "uniforme" else c.a))
    peso = peso_propio_de(modelo, eid, caso)
    if peso:
        lista.append(("uniforme", r @ np.array([0.0, 0.0, -peso]), None))
    w = (losas or {}).get(eid, 0.0)
    if w:
        lista.append(("uniforme", r @ np.array([0.0, 0.0, -w]), None))
    return lista


def cargas_de_losas(modelo, caso, por_caso=None):
    """{ID de barra: CargaBarra} con la carga de las losas sobre cada viga en el caso (uniforme, −Z
    global), para dibujarla y listarla. No se guarda en el modelo. por_caso: el resultado de
    losas.cargas_a_vigas, si ya se calculó (es lo que tarda)."""
    if por_caso is None:
        from modelo.losas import cargas_a_vigas
        por_caso = cargas_a_vigas(modelo)
    return {eid: CargaBarra(caso, eid, "uniforme", -w, "Z") for eid, w in por_caso.get(caso, {}).items()
            if abs(w) > 1e-12 and eid in modelo.elementos}


def peso_propio_total(modelo, caso):
    """Peso propio de todas las barras en el caso (kN), para comprobar el equilibrio."""
    return sum(peso_propio_de(modelo, eid, caso) * modelo.nodos[el.ni].distancia(modelo.nodos[el.nj])
               for eid, el in modelo.elementos.items())


def _cargas_del_caso(modelo, caso, losas=None):
    """(F, fef, locales) del caso: el vector de cargas, las FEF de cada barra cargada y sus cargas en
    ejes locales. losas: {ID de barra: w} de este caso (None: se calculan con cargas_a_vigas)."""
    if caso not in modelo.casos:
        raise KeyError(f"El caso {caso} no existe")
    faltan = modelo.sin_asignar()
    if faltan:
        raise ValueError(f"Las barras {', '.join(map(str, faltan))} no tienen material o sección asignados")
    if losas is None:
        losas = {}
        if getattr(modelo, "losas", None):
            from modelo.losas import cargas_a_vigas
            losas = cargas_a_vigas(modelo).get(caso, {})
    idx = indices_nodos(modelo)
    F = np.zeros(6 * len(idx))
    for c in modelo.cargas.values():
        if isinstance(c, CargaNodal) and c.caso == caso:
            F[6 * idx[c.nodo]:6 * idx[c.nodo] + 6] += c.fuerzas
    fef, locales = {}, {}
    for eid, el in modelo.elementos.items():
        lista = cargas_locales(modelo, eid, caso, losas)
        if not lista:
            continue
        _r, t, largo = geometria(modelo, eid)
        fef[eid] = empotramiento(largo, lista)
        F[gdl_barra(idx[el.ni], idx[el.nj])] += t.T @ (-fef[eid])
        locales[eid] = lista
    return F, fef, locales


def analizar_caso(modelo, caso, losas=None):
    """Resuelve un caso de carga dos veces, con las mismas cargas: con la inercia agrietada de las
    barras de concreto (res: fuerzas y reacciones) y con la bruta (bruta: desplazamientos). Sin
    concreto se resuelve una vez. ValueError si falta algo (sección, apoyos) o es inestable.
    losas: la carga de las losas de este caso ({ID de barra: w}), si ya se calculó."""
    F, fef, locales = _cargas_del_caso(modelo, caso, losas)
    agrietado = ModeloAgrietado(modelo)
    if not agrietado.cambia:
        return ResultadoCaso(caso, resolver(modelo, F, fef), locales, modelo.casos[caso].nombre)
    return ResultadoCaso(caso, resolver(agrietado, F, fef), locales, modelo.casos[caso].nombre,
                         bruta=resolver(modelo, F, fef))


def analizar(modelo):
    """Todos los casos: {ID de caso: ResultadoCaso}. La carga de las losas se calcula una vez."""
    por_caso = {}
    if getattr(modelo, "losas", None):
        from modelo.losas import cargas_a_vigas
        por_caso = cargas_a_vigas(modelo)
    return {caso: analizar_caso(modelo, caso, por_caso.get(caso, {})) for caso in modelo.casos}


def analizar_con_inercias(modelo, factores):
    """Todos los casos con Iy e Iz de cada barra por su factor ({ID de barra: factor}; las demás, con
    Ig): {ID de caso: ResultadoCaso}, con fuerzas y desplazamientos de ese mismo análisis (sin bruta).
    Sirve para las deflexiones con Ie (ACI 318-19 §24.2.3): factor = Ie/Ig de cada claro."""
    vista = ModeloAgrietado(modelo, factores)
    salida = {}
    for caso in modelo.casos:
        F, fef, locales = _cargas_del_caso(modelo, caso, {})
        salida[caso] = ResultadoCaso(caso, resolver(vista, F, fef), locales, modelo.casos[caso].nombre)
    return salida


def combinar(modelo, resultados, combinacion, casos=None):
    """Resultados de una combinación por superposición: Σ factor × (resultados del caso).

    combinacion: una Combinacion, con un factor por tipo de caso ({"D": 1.2, "L": 1.6}). Cada caso
    entra con el factor de su tipo (los dos casos tipo D, peso propio y carga muerta adicional, con
    el de D); un tipo sin casos no aporta nada.
    casos: si se da, solo entran esos casos (un caso de viva de una vigueta: los casos D y las vivas
    de los claros cargados).
    resultados: {ID de caso: ResultadoCaso} (los de analizar). No se resuelve nada otra vez:
    - U, F, R, desplazamientos, reacciones y fuerzas en los extremos: la suma con los factores
      (K es la misma en todos los casos);
    - cargas en las barras: la lista de las de cada caso, con su vector por el factor. Así
      fuerzas_en y deformada_de dan el diagrama combinado, porque internas() y deformada() suman
      el efecto de cada carga por separado (son lineales)."""
    partes = [(combinacion.factores[modelo.casos[cid].tipo], rc) for cid, rc in resultados.items()
              if modelo.casos[cid].tipo in combinacion.factores and (casos is None or cid in casos)]
    primero = next(iter(resultados.values()))     # K y las formas de los arreglos: iguales en todos
    res = _superponer([(f, rc.res) for f, rc in partes], primero.res)
    bruta = None
    if primero.bruta is not None:                 # el análisis con la inercia bruta, igual
        bruta = _superponer([(f, rc.bruta) for f, rc in partes], primero.bruta)
    cargas = {}
    for f, rc in partes:
        for eid, lista in rc.cargas_locales.items():
            cargas.setdefault(eid, []).extend((tipo, f * np.asarray(v, dtype=float), a) for tipo, v, a in lista)
    return ResultadoCaso(None, res, cargas, combinacion.nombre, bruta)


def _superponer(partes, base):
    """Σ factor × Resultados: partes [(factor, Resultados)]; base da K y la forma de cada arreglo."""

    def cero(valor):
        return np.zeros_like(np.asarray(valor, dtype=float))

    def suma(nombre):
        return sum((f * np.asarray(getattr(r, nombre), dtype=float) for f, r in partes), cero(getattr(base, nombre)))

    def suma_por_id(nombre):
        return {k: sum((f * np.asarray(getattr(r, nombre)[k], dtype=float) for f, r in partes), cero(v))
                for k, v in getattr(base, nombre).items()}

    return Resultados(ids=list(base.ids), K=base.K, F=suma("F"), U=suma("U"), R=suma("R"),
                      desplazamientos=suma_por_id("desplazamientos"), reacciones=suma_por_id("reacciones"),
                      fuerzas=suma_por_id("fuerzas"))


@dataclass
class Envolvente:
    """Máximos y mínimos de las fuerzas internas entre varias combinaciones.

    barras: {ID de barra: {"x": arreglo, "lado": arreglo, "N": (max, min, i_max, i_min), ...}}; i_max e
    i_min dicen, punto por punto, qué combinación (su posición en `nombres`) da cada valor."""
    nombres: list
    barras: dict
    nombre: str = "Envolvente"


def envolvente(modelo, resultados, combinaciones):
    """Envolvente de las fuerzas internas (N, Vy, Vz, T, My, Mz) de las combinaciones dadas.

    combinaciones: {clave: Combinacion}, o {clave: (nombre, Combinacion, casos)} para combinar solo
    esos casos (los casos de viva de una vigueta). No se vuelve a resolver: cada combinación sale por
    superposición (combinar) y sus diagramas se evalúan en los MISMOS puntos x de cada barra (los de
    todas las cargas de todos los casos juntas, con los dos lados de cada carga puntual). Luego, en
    cada punto, el mayor y el menor valor y de qué combinación salen."""
    entradas = [co if isinstance(co, tuple) else (co.nombre, co, None) for co in combinaciones.values()]
    combinados = [combinar(modelo, resultados, co, casos) for _n, co, casos in entradas]
    barras = {}
    for eid in modelo.elementos:
        _r, _t, largo = geometria(modelo, eid)
        todas = [c for rc in resultados.values() for c in rc.cargas_locales.get(eid, [])]
        x, lado = diagramas.secciones(largo, todas)
        valores = [diagramas.internas(largo, rc.res.fuerzas[eid], rc.cargas_locales.get(eid, []), x, lado)
                   for rc in combinados]
        datos = {"x": x, "lado": lado}
        for k in diagramas.NOMBRES:
            tabla = np.array([v[k] for v in valores])           # combinación × punto
            imax, imin = tabla.argmax(axis=0), tabla.argmin(axis=0)
            columnas = np.arange(len(x))
            datos[k] = (tabla[imax, columnas], tabla[imin, columnas], imax, imin)
        barras[eid] = datos
    return Envolvente([nombre for nombre, _co, _c in entradas], barras)


def envolvente_en_x(env, eid, componente, x):
    """(máximo, mínimo, combinación del máximo, combinación del mínimo) de la envolvente en el corte x,
    interpolando entre los puntos guardados (en un salto, el valor de después, como en los diagramas)."""
    d = env.barras[eid]
    xs = d["x"]
    k = int(np.searchsorted(xs, x, side="right") - 1)
    k = min(max(k, 0), len(xs) - 1)
    maximo, minimo, imax, imin = d[componente]
    if k + 1 < len(xs) and xs[k + 1] > xs[k]:
        f = (x - xs[k]) / (xs[k + 1] - xs[k])
        vmax, vmin = maximo[k] + f * (maximo[k + 1] - maximo[k]), minimo[k] + f * (minimo[k + 1] - minimo[k])
        cerca = k if f < 0.5 else k + 1
    else:
        vmax, vmin, cerca = maximo[k], minimo[k], k
    return float(vmax), float(vmin), env.nombres[imax[cerca]], env.nombres[imin[cerca]]


def fuerzas_en(modelo, rc, eid):
    """Diagramas de la barra: {"x", "N", "Vy", "Vz", "T", "My", "Mz"} (ejes locales)."""
    _r, _t, largo = geometria(modelo, eid)
    return diagramas.internas(largo, rc.res.fuerzas[eid], rc.cargas_locales.get(eid, []))


@dataclass
class Demanda:
    """Fuerzas de una sección de una columna para una combinación: el punto (Pu, Muy, Muz) que se
    compara con el diagrama de interacción. Son simultáneas: las tres salen del mismo corte de la
    misma combinación (ACI 318-19 §10.4.2.1, PDF p. 158)."""
    clave: object          # clave de la combinación ("C1", "C3a"…)
    combinacion: str       # su nombre ("1.2D + 1.6L + 0.5Lr")
    lugar: str             # "inferior" (nodo i), "superior" (nodo j) o "tramo" (el mayor momento, entre los dos)
    x: float               # distancia desde el nodo i, en m
    p: float               # carga axial en kN, positiva en COMPRESIÓN (es −N: N > 0 es tracción)
    my: float              # momento My en kN·m (ejes locales): flexión hacia h
    mz: float              # momento Mz en kN·m: flexión hacia b

    @property
    def m(self):
        """Momento resultante, √(My² + Mz²)."""
        return float(np.hypot(self.my, self.mz))


def demandas_columna(modelo, combinados, eid):
    """Puntos (Pu, My, Mz) de la barra eid, uno por combinación y por extremo: lista de Demanda.

    combinados: {clave: ResultadoCaso}, los resultados de cada combinación (combinar). De cada una se
    toman los dos extremos de la barra: el inferior (x = 0: el nodo i es el de abajo, por el orden de
    los nodos de una barra) y el superior (x = L). Sin cargas a lo largo de la columna el momento es
    lineal y el mayor siempre está en un extremo; si las hay y el momento resultante es mayor dentro
    del tramo, se agrega ese punto ("tramo"). Cada extremo va con su propia Pu (con el peso propio, la
    de abajo es mayor) y son los M1 y M2 de la esbeltez (ACI 318-19 §6.6.4.5.3, PDF p. 82).

    Son fuerzas de primer orden: sin magnificar por esbeltez y sin el momento mínimo (§6.6.4.5.4)."""
    puntos = []
    for clave, rc in combinados.items():
        d = fuerzas_en(modelo, rc, eid)
        resultante = np.hypot(d["My"], d["Mz"])
        lugares = [("inferior", 0), ("superior", len(d["x"]) - 1)]
        k = int(np.argmax(resultante))
        if resultante[k] > max(resultante[0], resultante[-1]) * (1 + 1e-6) + 1e-9:
            lugares.insert(1, ("tramo", k))
        for lugar, i in lugares:
            puntos.append(Demanda(clave, rc.nombre, lugar, float(d["x"][i]), -float(d["N"][i]),
                                  float(d["My"][i]), float(d["Mz"][i])))
    return puntos


def fuerzas_en_x(modelo, rc, eid, x):
    """Fuerzas internas en el corte x (m desde el nodo i, ejes locales): {"N", "Vy", "Vz", "T",
    "My", "Mz"}. Si en x hay una carga puntual, da el valor justo después de ella (como en
    diagramas.internas). x fuera de la barra se lleva al extremo más cercano."""
    _r, _t, largo = geometria(modelo, eid)
    x = min(max(float(x), 0.0), largo)
    d = diagramas.internas(largo, rc.res.fuerzas[eid], rc.cargas_locales.get(eid, []), x=[x])
    return {k: float(d[k][0]) for k in diagramas.NOMBRES}


def desplazamientos_locales(modelo, rc, eid, x=None, n_fino=801):
    """Desplazamientos de la barra en sus ejes locales: {"x", "u", "v", "w", "phi"} (u a lo largo
    del eje, v en y local, w en z local y phi el giro alrededor de x). x: los puntos donde se piden
    (m desde el nodo i); sin x, los mismos de los diagramas. n_fino: puntos de la integración
    (diagramas.deformada); menos es más rápido (las deflexiones de las viguetas usan 101).

    Salen del análisis con la inercia bruta (rc.deformacion): sus desplazamientos de los nodos, sus
    fuerzas y la sección del modelo (Ig), todo del mismo análisis para que la curva sea coherente."""
    el = modelo.elementos[eid]
    _r, t, largo = geometria(modelo, eid)
    mat, sec = modelo.materiales[el.material], modelo.secciones[el.seccion]
    idx = indices_nodos(modelo)
    d = rc.deformacion
    u_local = t @ d.U[gdl_barra(idx[el.ni], idx[el.nj])]
    return diagramas.deformada(largo, d.fuerzas[eid], rc.cargas_locales.get(eid, []), u_local,
                               mat.e, mat.g, sec.a, sec.iy, sec.iz, sec.j, x=x, n_fino=n_fino)


def desplazamientos_globales(modelo, rc, eid, x=None, n_fino=801):
    """Desplazamientos de la barra en ejes GLOBALES: {"x", "Dx", "Dy", "Dz"} (x sigue siendo la
    distancia desde el nodo i, a lo largo de la barra). Son los locales (u, v, w) girados: las
    filas de R son los ejes locales escritos en globales, así que global = Rᵀ · local."""
    r, _t, _largo = geometria(modelo, eid)
    d = desplazamientos_locales(modelo, rc, eid, x, n_fino)
    g = np.column_stack([d["u"], d["v"], d["w"]]) @ r                    # cada fila: Rᵀ · (u, v, w)
    return {"x": d["x"], "Dx": g[:, 0], "Dy": g[:, 1], "Dz": g[:, 2]}


def deformada_de(modelo, rc, eid):
    """Deformada de la barra: (puntos originales, desplazamientos globales) a lo largo de x."""
    el = modelo.elementos[eid]
    r, _t, _largo = geometria(modelo, eid)
    d = desplazamientos_globales(modelo, rc, eid)
    pi = np.asarray(modelo.nodos[el.ni].coords, dtype=float)
    puntos = pi + np.outer(d["x"], r[0])
    return puntos, np.column_stack([d["Dx"], d["Dy"], d["Dz"]])
