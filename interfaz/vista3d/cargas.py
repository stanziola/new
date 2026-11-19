"""Dibujo de las cargas del caso activo (al editar): bandas, láminas y flechas, en rojo translúcido.

Decisión del usuario (noviembre de 2026): en vez de filas de flechas, que tapan la vista y quedaban mal
repartidas, las cargas distribuidas van como una BANDA roja translúcida con su borde:
- Distribuida en una barra (uniforme, trapezoidal, el peso propio de una viga, la de las losas): la banda
  va en el plano de la barra y de la carga, del lado de donde viene la carga (la carga "empuja" la banda
  contra la barra), desde la cara de la sección hasta la línea de la carga. Su alto es proporcional al
  valor: la mayor del dibujo mide ui.TAMANO_CARGA × el tamaño del modelo y una pequeña, al menos
  ui.MINIMO_BANDA de eso (toda su banda crece igual: no cambia de forma). Una trapezoidal se ve como un
  trapecio; si cambia de signo, se parte en el cero y cada parte va de su lado.
- De área en una losa (la muerta adicional y la viva de cada paño; en el caso de peso propio, el peso
  de la losa): una lámina roja translúcida sobre el paño, de cara a cara de sus vigas, con alto
  proporcional a q, y su valor en kN/m² al centro.
- Puntuales y momentos: flechas (doble flecha el momento), del mismo rojo, translúcidas.
- Distribuida a lo largo de la barra (el peso propio de una columna): no puede tener banda (sería de
  ancho cero): flechas a lo largo del eje, translúcidas. Con la sección real opaca quedan dentro del
  concreto: se ven con las barras como líneas o con transparencia.
- Con la sección real, las bandas y las flechas llegan a la cara de la sección (o del nudo) del lado de
  donde viene la carga, no al eje.
- Peso propio y losas: no son cargas guardadas. El peso propio sale de modelo/analisis.cargas_de_peso_propio;
  la carga de las losas sobre sus vigas y las de área las da la ventana.
El valor de cada carga va en su etiqueta (Etiquetas → Valores de las cargas). flecha, flecha_doble y
flechas_en_nodo las usa también el dibujo de las reacciones (resultados.py).
"""
import numpy as np
import pyvista as pv

from configuracion import colores, formato
from configuracion import interfaz as ui
from interfaz.textos import texto_carga, valor_carga
from interfaz.vista3d.dibujo import media_hacia, seccion_dibujable
from modelo.analisis import cargas_de_peso_propio, geometria
from modelo.estructura import CargaBarra, CargaNodal

GLOBALES = {"X": 0, "Y": 1, "Z": 2}
LOCALES = {"x": 0, "y": 1, "z": 2}
PARALELA = 0.999                       # |coseno| entre la carga y la barra a partir del cual es paralela
DISTRIBUIDAS = ("uniforme", "trapezoidal")


def flecha(punta, u, largo):
    """Flecha de largo `largo` que termina en `punta`, en la dirección u."""
    return pv.Arrow(start=punta - u * largo, direction=u, scale=largo, tip_length=0.28,
                    tip_radius=0.09, shaft_radius=0.025)


def flecha_doble(origen, u, largo):
    """Flecha doble (momento) que sale de `origen` en la dirección u."""
    cuerpo = pv.Arrow(start=origen, direction=u, scale=largo, tip_length=0.25, tip_radius=0.09,
                      shaft_radius=0.025)
    cono = pv.Cone(center=origen + u * largo * 0.74, direction=u, height=largo * 0.25,
                   radius=largo * 0.09, resolution=16)
    return cuerpo.merge(cono)


def flechas_en_nodo(piezas, p, fuerzas, largo, separacion=0.0, minimo_fuerza=0.0, minimo_momento=0.0):
    """Agrega a `piezas` la flecha de la fuerza resultante de [Fx, Fy, Fz, Mx, My, Mz] y la flecha
    doble del momento resultante, en el punto p. Lo que no pase de su mínimo no se dibuja.

    separacion: a qué distancia de p termina la flecha de la fuerza y empieza la del momento
    (0 = en el punto). Es un número o una función de la dirección u (lo que hay del nodo a la cara
    del concreto en esa dirección).
    Devuelve dónde va la etiqueta (junto a la fuerza; si no hay, junto al momento) o None."""
    fuerza, momento = np.asarray(fuerzas[:3], dtype=float), np.asarray(fuerzas[3:], dtype=float)
    nf, nm = np.linalg.norm(fuerza), np.linalg.norm(momento)

    def hasta(u):
        return separacion(u) if callable(separacion) else separacion

    lugar = None
    if nf > minimo_fuerza:
        u = fuerza / nf
        punta = p - u * hasta(-u)
        piezas.append(flecha(punta, u, largo))
        lugar = punta - u * largo * 1.05
    if nm > minimo_momento:
        u = momento / nm
        origen = p + u * hasta(u) if callable(separacion) else p
        piezas.append(flecha_doble(origen, u, largo))
        if lugar is None:
            lugar = origen + u * largo * 1.05
    return lugar


def _eje_carga(modelo, c):
    """El eje de la carga de barra como vector unitario global, sin el signo del valor."""
    v = np.zeros(3)
    if c.direccion in GLOBALES:
        v[GLOBALES[c.direccion]] = 1.0
        return v
    r, _t, _l = geometria(modelo, c.barra)
    return np.array(r[LOCALES[c.direccion]], dtype=float)


def _media_seccion(modelo, eid, u, seccion_real):
    """Lo que hay del eje de la barra a la cara de su sección en la dirección u (m). 0 si las barras
    se dibujan como líneas o la barra no tiene sección que se dibuje (rectangular o T)."""
    c = seccion_dibujable(modelo, modelo.elementos[eid]) if seccion_real else None
    if c is None:
        return 0.0
    r, _t, _l = geometria(modelo, eid)
    return float(media_hacia(c, r, u))


def _tramos(largo_tramo, largo):
    """Cuántas flechas lleva una carga a lo largo de su barra: una cada ui.SEPARACION_CARGA × el largo
    de la flecha, y al menos una."""
    separacion = max(ui.SEPARACION_CARGA * largo, 1e-9)
    return max(1, int(round(float(largo_tramo) / separacion)))


def _extremos(c, largo):
    """(a, b, w1, w2) de una carga distribuida: la uniforme, en toda la barra; la trapezoidal, en su tramo."""
    if c.tipo == "trapezoidal":
        return float(c.a), float(min(c.b, largo)), float(c.valor), float(c.valor2)
    return 0.0, float(largo), float(c.valor), float(c.valor)


class _Piezas:
    """Lo que se junta en una malla: rellenos (triángulos), bordes (líneas), flechas y etiquetas."""

    def __init__(self):
        self.puntos, self.triangulos = [], []
        self.bordes, self.flechas = [], []
        self.etiquetas, self.lugares = [], []

    def cuadrilatero(self, p0, p1, p2, p3):
        n = len(self.puntos)
        self.puntos += [p0, p1, p2, p3]
        self.triangulos += [(n, n + 1, n + 2), (n, n + 2, n + 3)]

    def borde(self, puntos):
        self.bordes.append(pv.lines_from_points(np.array(puntos, dtype=float)))

    def etiqueta(self, texto, lugar):
        if lugar is not None:
            self.etiquetas.append(texto)
            self.lugares.append(lugar)

    def relleno(self):
        if not self.triangulos:
            return None
        caras = np.hstack([[3, *t] for t in self.triangulos])
        return pv.PolyData(np.array(self.puntos, dtype=float), caras)

    def lineas(self):
        return (self.bordes[0].merge(self.bordes[1:]) if len(self.bordes) > 1 else self.bordes[0]) if self.bordes else None


def _banda(p, modelo, c, pi, eje, d, largo, alto_mayor, w_mayor, seccion_real):
    """La banda de una carga distribuida transversal a la barra (d: el eje de la carga). Devuelve dónde
    va su etiqueta, o None."""
    a, b, w1, w2 = _extremos(c, largo)
    pico = max(abs(w1), abs(w2))
    if pico <= 0 or b - a <= 1e-9:
        return None
    k = alto_mayor / w_mayor if w_mayor > 0 else 0.0
    if pico * k < ui.MINIMO_BANDA * alto_mayor:        # una carga pequeña: toda la banda crece igual
        k = ui.MINIMO_BANDA * alto_mayor / pico
    tramos = [(a, b, w1, w2)]
    if w1 * w2 < 0:                                     # cambia de signo: se parte en el cero
        x0 = a + (b - a) * w1 / (w1 - w2)
        tramos = [(a, x0, w1, 0.0), (x0, b, 0.0, w2)]
    lugar, mas_alto = None, -1.0
    for xa, xb, wa, wb in tramos:
        signo = -1.0 if wa + wb < 0 else 1.0           # sentido de la carga en el tramo, sobre d
        hacia = -signo * d                              # la banda, del lado de donde viene la carga
        cara = hacia * _media_seccion(modelo, c.barra, hacia, seccion_real)
        base_a, base_b = pi + eje * xa + cara, pi + eje * xb + cara
        tope_a, tope_b = base_a + hacia * abs(wa) * k, base_b + hacia * abs(wb) * k
        p.cuadrilatero(base_a, base_b, tope_b, tope_a)
        p.borde([base_a, tope_a, tope_b, base_b])
        alto = max(abs(wa), abs(wb)) * k
        if alto > mas_alto:
            mas_alto = alto
            lugar = (tope_a + tope_b) / 2 + hacia * alto_mayor * 0.15
    return lugar


def _a_lo_largo(p, modelo, c, pi, eje, d, largo, largo_flecha, seccion_real):
    """Una distribuida paralela a la barra (el peso propio de una columna): flechas sobre el eje, una
    en cada tramo de [a, b]. Devuelve dónde va su etiqueta (al costado, en z local)."""
    a, b, w1, w2 = _extremos(c, largo)
    signo = -1.0 if (w1 + w2) < 0 else 1.0
    u = signo * d
    n = _tramos(b - a, largo_flecha)
    cada = min(largo_flecha * 0.8, 0.85 * (b - a) / n)
    for t in (np.arange(n) + 0.5) / n:
        p.flechas.append(flecha(pi + eje * (a + (b - a) * t) + u * cada / 2, u, cada))
    lado = geometria(modelo, c.barra)[0][2]
    return pi + eje * (a + b) / 2 + lado * (_media_seccion(modelo, c.barra, lado, seccion_real) + largo_flecha * 0.2)


ALTO_AREA = 0.6                        # la lámina de q mayor mide esto × el alto de la banda mayor


def _areas(p, areas, alto_mayor):
    """Las cargas de área: una lámina translúcida sobre cada paño, a una altura proporcional a q, con
    sus cuatro aristas verticales hasta la losa (sin paredes: así no tapa las vigas ni sus bandas).
    areas: [(esquinas, q)] con las 4 esquinas de arriba del paño (de cara a cara de sus vigas) y q en
    kN/m², positiva hacia abajo."""
    q_mayor = max((abs(q) for _e, q in areas), default=0.0)
    if q_mayor <= 0:
        return
    for esquinas, q in areas:
        if abs(q) <= 1e-12:
            continue
        alto = ALTO_AREA * alto_mayor * max(ui.MINIMO_BANDA, abs(q) / q_mayor)
        abajo = [np.asarray(e, dtype=float) for e in esquinas]
        arriba = [e + np.array([0.0, 0.0, alto]) for e in abajo]
        p.cuadrilatero(*arriba)
        for i in range(4):
            p.borde([abajo[i], arriba[i]])
        p.borde(arriba + [arriba[0]])
        p.etiqueta(formato.cantidad(q, "carga_area"), sum(arriba) / 4 + np.array([0.0, 0.0, alto_mayor * 0.12]))


def dibujar_cargas(vista, modelo, caso, tamano, con_etiquetas=True, seccion_real=False, extra=None, areas=None,
                   con_barras=True):
    """Dibuja las cargas del caso. seccion_real: las barras se ven con su sección (las bandas y flechas
    llegan a la cara).
    con_barras: las cargas en nodos y barras (las puestas a mano y el peso propio de las barras);
    extra: otras cargas de barra del caso (la de las losas sobre sus vigas, modelo/analisis.cargas_de_losas);
    areas: [(esquinas, q)] las cargas de área de los paños de las losas (None o vacío: ninguna).
    Devuelve {"cargas": flechas, "cargas_relleno", "cargas_bordes", "cargas_areas", "valores_cargas"}
    (los que haya)."""
    actores = {}
    largo = ui.TAMANO_CARGA * tamano
    cargas = []
    if con_barras:
        cargas = [c for c in modelo.cargas.values() if c.caso == caso]
        cargas += list(cargas_de_peso_propio(modelo, caso).values())
    cargas += list(extra or [])

    # La mayor distribuida transversal (las bandas se escalan con ella)
    w_mayor = 0.0
    for c in cargas:
        if isinstance(c, CargaBarra) and c.tipo in DISTRIBUIDAS:
            el = modelo.elementos[c.barra]
            pi, pj = (np.asarray(modelo.nodos[n].coords, dtype=float) for n in (el.ni, el.nj))
            eje = (pj - pi) / np.linalg.norm(pj - pi)
            if abs(_eje_carga(modelo, c) @ eje) < PARALELA:
                w_mayor = max(w_mayor, max(abs(x) for x in _extremos(c, np.linalg.norm(pj - pi))[2:]))

    p = _Piezas()
    areas_piezas = _Piezas()
    for c in cargas:
        if isinstance(c, CargaNodal):
            q = np.asarray(modelo.nodos[c.nodo].coords, dtype=float)
            barras = modelo.elementos_conectados(c.nodo) if seccion_real else []

            def cara(u, barras=barras):
                """Del nodo a la cara del concreto (el nudo o la sección de sus barras) hacia u."""
                return max((_media_seccion(modelo, eid, u, True) for eid in barras), default=0.0)

            lugar = flechas_en_nodo(p.flechas, q, c.fuerzas, largo, cara)
            p.etiqueta(texto_carga(c), lugar)
            continue
        if not isinstance(c, CargaBarra) or (c.valor == 0 and (c.tipo != "trapezoidal" or c.valor2 == 0)):
            continue
        el = modelo.elementos[c.barra]
        pi = np.asarray(modelo.nodos[el.ni].coords, dtype=float)
        pj = np.asarray(modelo.nodos[el.nj].coords, dtype=float)
        largo_barra = float(np.linalg.norm(pj - pi))
        eje = (pj - pi) / largo_barra
        d = _eje_carga(modelo, c)
        if c.tipo in DISTRIBUIDAS:
            if abs(d @ eje) < PARALELA:
                lugar = _banda(p, modelo, c, pi, eje, d, largo_barra, largo, w_mayor, seccion_real)
                p.etiqueta(valor_carga(c), lugar)
            else:
                p.etiqueta(valor_carga(c), _a_lo_largo(p, modelo, c, pi, eje, d, largo_barra, largo, seccion_real))
            continue
        u = d * np.sign(c.valor)
        if c.tipo == "puntual":
            q = pi + eje * c.a - u * _media_seccion(modelo, c.barra, -u, seccion_real)
            p.flechas.append(flecha(q, u, largo))
            p.etiqueta(texto_carga(c), q - u * largo * 1.05)
        else:
            q = pi + eje * c.a
            p.flechas.append(flecha_doble(q, u, largo))
            p.etiqueta(texto_carga(c), q + u * largo * 1.05)
    if areas:
        _areas(areas_piezas, areas, largo)

    comunes = dict(pickable=False, reset_camera=False, render=False)
    relleno = p.relleno()
    if relleno is not None:
        actores["cargas_relleno"] = vista.add_mesh(relleno, color=colores.CARGA, opacity=ui.OPACIDAD_CARGA,
                                                   lighting=False, name="cargas_relleno", **comunes)
    relleno_areas = areas_piezas.relleno()
    if relleno_areas is not None:
        actores["cargas_areas"] = vista.add_mesh(relleno_areas, color=colores.CARGA,
                                                 opacity=ui.OPACIDAD_CARGA * 0.6, lighting=False,
                                                 name="cargas_areas", **comunes)
    lineas = [x for x in (p.lineas(), areas_piezas.lineas()) if x is not None]
    if lineas:
        malla = lineas[0].merge(lineas[1:]) if len(lineas) > 1 else lineas[0]
        actores["cargas_bordes"] = vista.add_mesh(malla, color=colores.CARGA, opacity=ui.OPACIDAD_FLECHA_CARGA,
                                                  line_width=1.5, name="cargas_bordes", **comunes)
    if p.flechas:
        malla = p.flechas[0].merge(p.flechas[1:]) if len(p.flechas) > 1 else p.flechas[0]
        actores["cargas"] = vista.add_mesh(malla, color=colores.CARGA, opacity=ui.OPACIDAD_FLECHA_CARGA,
                                           name="cargas", **comunes)
    for actor in actores.values():
        actor.SetUseBounds(False)
    etiquetas = p.etiquetas + areas_piezas.etiquetas
    if con_etiquetas and etiquetas:
        actores["valores_cargas"] = vista.add_point_labels(
            np.array(p.lugares + areas_piezas.lugares), etiquetas, font_size=ui.TAMANO_LETRA - 3,
            text_color=colores.CARGA, shape=None, show_points=False, always_visible=True, name="valores_cargas",
            reset_camera=False)
    return actores
