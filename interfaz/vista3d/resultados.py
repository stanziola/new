"""Dibujo de los resultados del análisis: la deformada y los diagramas N, V, M y T sobre las barras.

- Deformada: cada barra deformada (curva) y los nodos desplazados, en colores.DEFORMADA. El factor
  multiplica los desplazamientos reales (1 = tamaño real): ui.FACTOR_DEFORMADA o, con la escala
  automática, el que hace que el desplazamiento mayor mida ui.FRACCION_DEFORMADA × tamaño del modelo.
- Diagramas: el valor a lo largo de cada barra, dibujado en un plano local. Con escala 1
  (ui.FACTOR_DIAGRAMA), el valor mayor de todo el modelo mide ui.FRACCION_DIAGRAMA × tamaño del
  modelo; con 2, el doble:
      My: hacia −z local y Mz: hacia −y local (del lado traccionado; con z hacia arriba, el momento
          positivo de una viga queda abajo);
      Vy: hacia +y; Vz: hacia +z; N y T: hacia +z.
  Relleno en colores.DIAGRAMA_POSITIVO o DIAGRAMA_NEGATIVO según el signo, con borde. Si el signo
  cambia dentro de un tramo, se parte en el cruce por cero.
Los valores vienen de modelo/analisis.py (que usa las fórmulas de calculo/rigidez/diagramas.py).
"""
import numpy as np
import pyvista as pv

from configuracion import colores
from configuracion import interfaz as ui
from interfaz.textos import valor_corto
from modelo.analisis import deformada_de, fuerzas_en, geometria

DIRECCION = {"My": (2, -1.0), "Mz": (1, -1.0), "Vy": (1, 1.0), "Vz": (2, 1.0), "N": (2, 1.0), "T": (2, 1.0)}


def _malla(puntos, triangulos):
    caras = np.hstack([[3, *t] for t in triangulos]) if triangulos else np.array([], dtype=int)
    return pv.PolyData(np.asarray(puntos, dtype=float), caras)


def factor_deformada(mayor, tamano):
    """Cuántas veces se amplifican los desplazamientos reales al dibujarlos.

    mayor: el desplazamiento mayor del modelo (m); tamano: el tamaño del modelo (m)."""
    if ui.DEFORMADA_AUTOMATICA:
        return ui.FRACCION_DEFORMADA * tamano / mayor if mayor > 0 else 1.0
    return ui.FACTOR_DEFORMADA


def dibujar_deformada(vista, modelo, rc, tamano):
    """Barras deformadas y nodos desplazados. Devuelve ({"deformada": actor}, factor usado);
    sin desplazamientos, ({}, None)."""
    curvas = [deformada_de(modelo, rc, eid) for eid in modelo.elementos]
    mayor = max((np.abs(u).max() for _p, u in curvas), default=0.0)
    if mayor <= 0:
        return {}, None
    escala = factor_deformada(mayor, tamano)
    lineas = [pv.lines_from_points(p + u * escala) for p, u in curvas]
    malla = lineas[0].merge(lineas[1:]) if len(lineas) > 1 else lineas[0]
    actor = vista.add_mesh(malla, color=colores.DEFORMADA, line_width=ui.GROSOR_BARRA, pickable=False,
                           reset_camera=False, name="deformada", render=False)
    actor.SetUseBounds(False)
    return {"deformada": actor}, escala


def dibujar_diagrama(vista, modelo, rc, componente, tamano, con_valores=True):
    """Diagrama de `componente` ("N", "Vy", "Vz", "T", "My" o "Mz") en todas las barras."""
    datos = {eid: fuerzas_en(modelo, rc, eid) for eid in modelo.elementos}
    mayor = max((np.abs(d[componente]).max() for d in datos.values()), default=0.0)
    if mayor <= 1e-12:
        return {}
    escala = ui.FACTOR_DIAGRAMA * ui.FRACCION_DIAGRAMA * tamano / mayor
    eje, signo = DIRECCION[componente]
    pos = {"puntos": [], "tri": []}
    neg = {"puntos": [], "tri": []}
    bordes, etiquetas, lugares = [], [], []

    def triangulo(destino, a, b, c):
        n = len(destino["puntos"])
        destino["puntos"] += [a, b, c]
        destino["tri"].append((n, n + 1, n + 2))

    for eid, d in datos.items():
        el = modelo.elementos[eid]
        r, _t, _l = geometria(modelo, eid)
        pi = np.asarray(modelo.nodos[el.ni].coords, dtype=float)
        x, val = d["x"], d[componente]
        base = pi + np.outer(x, r[0])
        tope = base + np.outer(val * escala * signo, r[eje])
        for k in range(len(x) - 1):
            v0, v1 = val[k], val[k + 1]
            b0, b1, t0, t1 = base[k], base[k + 1], tope[k], tope[k + 1]
            if v0 * v1 < 0:                                  # cambia de signo: se parte en el cero
                f = v0 / (v0 - v1)
                bc = b0 + (b1 - b0) * f
                triangulo(pos if v0 > 0 else neg, b0, t0, bc)
                triangulo(pos if v1 > 0 else neg, bc, t1, b1)
            else:
                destino = pos if (v0 + v1) >= 0 else neg
                triangulo(destino, b0, t0, t1)
                triangulo(destino, b0, t1, b1)
        bordes.append(pv.lines_from_points(np.vstack([base[0], tope, base[-1]])))
        k = int(np.argmax(np.abs(val)))
        if abs(val[k]) > 1e-9 * mayor:
            etiquetas.append(valor_corto(val[k], componente))
            lugares.append(tope[k])
    actores = {}
    for nombre, grupo, color in (("diagrama_pos", pos, colores.DIAGRAMA_POSITIVO),
                                 ("diagrama_neg", neg, colores.DIAGRAMA_NEGATIVO)):
        if grupo["tri"]:
            actores[nombre] = vista.add_mesh(_malla(grupo["puntos"], grupo["tri"]), color=color, opacity=0.85,
                                             lighting=False, pickable=False, reset_camera=False,
                                             name=nombre, render=False)
    borde = bordes[0].merge(bordes[1:]) if len(bordes) > 1 else bordes[0]
    actores["diagrama_borde"] = vista.add_mesh(borde, color=colores.DIAGRAMA_BORDE, line_width=1,
                                               pickable=False, reset_camera=False, name="diagrama_borde",
                                               render=False)
    for actor in actores.values():
        actor.SetUseBounds(False)
    if con_valores and etiquetas:
        actores["valores_resultados"] = vista.add_point_labels(
            np.array(lugares), etiquetas, font_size=ui.TAMANO_LETRA - 3, text_color=colores.DIAGRAMA_BORDE,
            shape=None, show_points=False, always_visible=True, name="valores_resultados", reset_camera=False)
    return actores
