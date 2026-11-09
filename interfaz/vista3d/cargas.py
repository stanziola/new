"""Dibujo de las cargas del caso activo: flechas para fuerzas y flechas dobles para momentos.

- Carga en nodo: la fuerza (Fx, Fy, Fz) es una flecha que llega al nodo; el momento (Mx, My, Mz) es
  una flecha doble que sale del nodo (regla de la mano derecha).
- Carga en barra: la uniforme es una fila de flechas que llegan a la barra, unidas por una línea;
  la puntual, una flecha en x = a; el momento, una flecha doble en x = a.
Todas del mismo largo (ui.TAMANO_CARGA × tamaño del modelo) y del color colores.CARGA: el valor se
lee en las etiquetas (Etiquetas → Valores de las cargas).
"""
import numpy as np
import pyvista as pv

from configuracion import colores
from configuracion import interfaz as ui
from interfaz.textos import texto_carga
from modelo.analisis import geometria
from modelo.estructura import CargaBarra, CargaNodal

GLOBALES = {"X": 0, "Y": 1, "Z": 2}
LOCALES = {"x": 0, "y": 1, "z": 2}


def _flecha(punta, u, largo):
    """Flecha de largo `largo` que termina en `punta`, en la dirección u."""
    return pv.Arrow(start=punta - u * largo, direction=u, scale=largo, tip_length=0.28,
                    tip_radius=0.09, shaft_radius=0.025)


def _flecha_doble(origen, u, largo):
    """Flecha doble (momento) que sale de `origen` en la dirección u."""
    flecha = pv.Arrow(start=origen, direction=u, scale=largo, tip_length=0.25, tip_radius=0.09,
                      shaft_radius=0.025)
    cono = pv.Cone(center=origen + u * largo * 0.74, direction=u, height=largo * 0.25,
                   radius=largo * 0.09, resolution=16)
    return flecha.merge(cono)


def _vector_global(modelo, c):
    """La carga de barra como vector global (con su signo)."""
    v = np.zeros(3)
    if c.direccion in GLOBALES:
        v[GLOBALES[c.direccion]] = c.valor
        return v
    r, _t, _l = geometria(modelo, c.barra)
    v[LOCALES[c.direccion]] = c.valor
    return r.T @ v


def dibujar_cargas(vista, modelo, caso, tamano, con_etiquetas=True):
    """Dibuja las cargas del caso. Devuelve {"cargas": actor, "valores_cargas": actor} (si hay)."""
    actores = {}
    piezas, etiquetas, posiciones = [], [], []
    largo = ui.TAMANO_CARGA * tamano
    for c in modelo.cargas.values():
        if c.caso != caso:
            continue
        if isinstance(c, CargaNodal):
            p = np.asarray(modelo.nodos[c.nodo].coords, dtype=float)
            fuerza, momento = np.asarray(c.fuerzas[:3]), np.asarray(c.fuerzas[3:])
            if np.linalg.norm(fuerza) > 0:
                u = fuerza / np.linalg.norm(fuerza)
                piezas.append(_flecha(p, u, largo))
                posiciones.append(p - u * largo * 1.05)
            if np.linalg.norm(momento) > 0:
                u = momento / np.linalg.norm(momento)
                piezas.append(_flecha_doble(p, u, largo))
                posiciones.append(p + u * largo * 1.05)
            if np.linalg.norm(fuerza) == 0 and np.linalg.norm(momento) == 0:
                continue
            etiquetas.append(texto_carga(c))
            if np.linalg.norm(fuerza) > 0 and np.linalg.norm(momento) > 0:
                posiciones.pop()                   # una etiqueta por carga
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
            puntos = [pi + (pj - pi) * t for t in np.linspace(0, 1, 7)]
            for q in puntos:
                piezas.append(_flecha(q, u, largo * 0.8))
            colas = np.array([q - u * largo * 0.8 for q in puntos])
            piezas.append(pv.lines_from_points(colas))
            posiciones.append(colas[len(colas) // 2] - u * largo * 0.15)
        elif c.tipo == "puntual":
            q = pi + eje * c.a
            piezas.append(_flecha(q, u, largo))
            posiciones.append(q - u * largo * 1.05)
        else:
            q = pi + eje * c.a
            piezas.append(_flecha_doble(q, u, largo))
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
