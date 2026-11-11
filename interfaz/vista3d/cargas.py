"""Dibujo de las cargas del caso activo: flechas para fuerzas y flechas dobles para momentos.

- Carga en nodo: la fuerza (Fx, Fy, Fz) es una flecha que llega al nodo; el momento (Mx, My, Mz) es
  una flecha doble que sale del nodo (regla de la mano derecha).
- Carga en barra: la uniforme es una fila de flechas que llegan a la barra, unidas por una línea;
  la puntual, una flecha en x = a; el momento, una flecha doble en x = a.
- Peso propio: en el caso que lo lleva, cada barra muestra su uniforme A·γ hacia −Z global. No es
  una carga guardada: sale de modelo/analisis.cargas_de_peso_propio y se dibuja como las demás.
- Una uniforme paralela a la barra (el peso propio de una columna) no se puede dibujar con flechas
  que "llegan" a la barra: va sobre el eje de la barra, con las flechas a lo largo. Con la sección
  real opaca queda dentro del concreto: se ve con las barras como líneas o con transparencia.
- Con la sección real a la vista, las flechas de las cargas transversales en barra llegan a la cara
  de la sección y no al eje, y las de las cargas en nodo, a la cara del nudo: si no, quedarían
  metidas dentro del concreto.
Todas del mismo largo (ui.TAMANO_CARGA × tamaño del modelo) y del color colores.CARGA: el valor se
lee en las etiquetas (Etiquetas → Valores de las cargas).
flecha, flecha_doble y flechas_en_nodo las usa también el dibujo de las reacciones (resultados.py).
"""
import numpy as np
import pyvista as pv

from configuracion import colores
from configuracion import interfaz as ui
from interfaz.textos import texto_carga
from interfaz.vista3d.dibujo import seccion_rectangular
from modelo.analisis import cargas_de_peso_propio, geometria
from modelo.estructura import CargaBarra, CargaNodal

GLOBALES = {"X": 0, "Y": 1, "Z": 2}
LOCALES = {"x": 0, "y": 1, "z": 2}
PARALELA = 0.999                       # |coseno| entre la carga y la barra a partir del cual es paralela


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
        punta = p - u * hasta(u)
        piezas.append(flecha(punta, u, largo))
        lugar = punta - u * largo * 1.05
    if nm > minimo_momento:
        u = momento / nm
        origen = p + u * hasta(u) if callable(separacion) else p
        piezas.append(flecha_doble(origen, u, largo))
        if lugar is None:
            lugar = origen + u * largo * 1.05
    return lugar


def _vector_global(modelo, c):
    """La carga de barra como vector global (con su signo)."""
    v = np.zeros(3)
    if c.direccion in GLOBALES:
        v[GLOBALES[c.direccion]] = c.valor
        return v
    r, _t, _l = geometria(modelo, c.barra)
    v[LOCALES[c.direccion]] = c.valor
    return r.T @ v


def _media_seccion(modelo, eid, u, seccion_real):
    """Lo que hay del eje de la barra a la cara de su sección en la dirección u (m). 0 si las barras
    se dibujan como líneas o la barra no tiene sección rectangular."""
    c = seccion_rectangular(modelo, modelo.elementos[eid]) if seccion_real else None
    if c is None:
        return 0.0
    r, _t, _l = geometria(modelo, eid)
    return float(abs(u @ r[1]) * c.b / 2 + abs(u @ r[2]) * c.h / 2)


def _uniforme(piezas, modelo, eid, pi, pj, eje, u, largo, seccion_real):
    """Agrega a `piezas` la fila de flechas de una carga uniforme. Devuelve dónde va su etiqueta."""
    tramos = np.linspace(0, 1, 7)
    if abs(u @ eje) < PARALELA:                    # lo normal: flechas que llegan a la barra
        cara = u * _media_seccion(modelo, eid, u, seccion_real)
        puntos = [pi + (pj - pi) * t - cara for t in tramos]
        for q in puntos:
            piezas.append(flecha(q, u, largo * 0.8))
        colas = np.array([q - u * largo * 0.8 for q in puntos])
        piezas.append(pv.lines_from_points(colas))
        return colas[len(colas) // 2] - u * largo * 0.15
    # Paralela a la barra (el peso propio de una columna): sobre el eje, con las flechas a lo largo.
    # La propia barra hace de línea que las une. Con la sección real opaca quedan dentro del
    # concreto: se ven con las barras como líneas o con transparencia.
    puntos = [pi + (pj - pi) * t for t in tramos]
    cada = min(largo * 0.8, 0.85 * float(np.linalg.norm(puntos[1] - puntos[0])))
    for q in (puntos[1:] if u @ eje > 0 else puntos[:-1]):     # cada flecha queda dentro de su tramo
        piezas.append(flecha(q, u, cada))
    lado = geometria(modelo, eid)[0][2]                        # la etiqueta, al costado (z local)
    return puntos[len(puntos) // 2] + lado * (_media_seccion(modelo, eid, lado, seccion_real) + largo * 0.2)


def dibujar_cargas(vista, modelo, caso, tamano, con_etiquetas=True, seccion_real=False):
    """Dibuja las cargas del caso (las puestas a mano y, si el caso lo lleva, el peso propio de
    cada barra). seccion_real: las barras se ven con su sección (las flechas llegan a la cara).
    Devuelve {"cargas": actor, "valores_cargas": actor} (si hay)."""
    actores = {}
    piezas, etiquetas, posiciones = [], [], []
    largo = ui.TAMANO_CARGA * tamano
    cargas = [c for c in modelo.cargas.values() if c.caso == caso]
    cargas += list(cargas_de_peso_propio(modelo, caso).values())
    for c in cargas:
        if isinstance(c, CargaNodal):
            p = np.asarray(modelo.nodos[c.nodo].coords, dtype=float)
            barras = modelo.elementos_conectados(c.nodo) if seccion_real else []

            def cara(u, barras=barras):
                """Del nodo a la cara del concreto (el nudo o la sección de sus barras) hacia u."""
                return max((_media_seccion(modelo, eid, u, True) for eid in barras), default=0.0)

            lugar = flechas_en_nodo(piezas, p, c.fuerzas, largo, cara)
            if lugar is not None:
                etiquetas.append(texto_carga(c))
                posiciones.append(lugar)
            continue
        if not isinstance(c, CargaBarra) or c.valor == 0:
            continue
        el = modelo.elementos[c.barra]
        pi = np.asarray(modelo.nodos[el.ni].coords, dtype=float)
        pj = np.asarray(modelo.nodos[el.nj].coords, dtype=float)
        eje = (pj - pi) / np.linalg.norm(pj - pi)
        v = _vector_global(modelo, c)
        u = v / np.linalg.norm(v)
        if c.tipo == "uniforme":
            posiciones.append(_uniforme(piezas, modelo, c.barra, pi, pj, eje, u, largo, seccion_real))
        elif c.tipo == "puntual":
            q = pi + eje * c.a - u * _media_seccion(modelo, c.barra, u, seccion_real)
            piezas.append(flecha(q, u, largo))
            posiciones.append(q - u * largo * 1.05)
        else:
            q = pi + eje * c.a
            piezas.append(flecha_doble(q, u, largo))
            posiciones.append(q + u * largo * 1.05)
        etiquetas.append(texto_carga(c))
    if not piezas:
        return actores
    malla = piezas[0].merge(piezas[1:]) if len(piezas) > 1 else piezas[0]
    actores["cargas"] = vista.add_mesh(malla, color=colores.CARGA, pickable=False, reset_camera=False,
                                       name="cargas", render=False)
    actores["cargas"].SetUseBounds(False)
    if con_etiquetas and etiquetas:
        actores["valores_cargas"] = vista.add_point_labels(
            np.array(posiciones), etiquetas, font_size=ui.TAMANO_LETRA - 3, text_color=colores.CARGA,
            shape=None, show_points=False, always_visible=True, name="valores_cargas", reset_camera=False)
    return actores
