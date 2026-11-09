"""Dibujo del modelo en la vista 3D: barras, nodos, apoyos, números de nodo y rejilla de piso.

Las funciones devuelven sus actores, para poder mostrarlos u ocultarlos después. Se devuelven en
vez de buscarlos por nombre porque pyvista cambia algunos nombres: a las etiquetas, por ejemplo,
les agrega "-labels".
"""
import numpy as np
import pyvista as pv
from calculo.ensamble import indices_nodos
from interfaz import estilo as es


def dibujar_modelo(vista, modelo):
    """Dibuja barras, nodos, apoyos y números de nodo en la vista 3D.

    Devuelve {"barras": actor, "nodos": ..., "apoyos": ..., "etiquetas": ...} con lo que se dibujó.
    """
    actores = {}
    if not modelo.nodos:
        return actores

    idx = indices_nodos(modelo)                       # ID de nodo -> 0, 1, 2...
    ids = list(idx)
    puntos = np.array([modelo.nodos[nid].coords for nid in ids], dtype=float)

    # Barras: cada línea es [2, punto_i, punto_j]
    if modelo.elementos:
        lineas = []
        for el in modelo.elementos.values():
            lineas += [2, idx[el.ni], idx[el.nj]]
        barras = pv.PolyData(puntos, lines=np.array(lineas))
        actores["barras"] = vista.add_mesh(barras, color=es.COLOR_BARRA,
                                           line_width=es.GROSOR_BARRA, name="barras")

    # Nodos
    actores["nodos"] = vista.add_points(puntos, color=es.COLOR_NODO, point_size=es.TAMANO_NODO,
                                        render_points_as_spheres=True, name="nodos")

    # Apoyos: nodos con algún GDL restringido
    apoyos = [i for i, nid in enumerate(ids) if any(modelo.nodos[nid].apoyo)]
    if apoyos:
        actores["apoyos"] = vista.add_points(puntos[apoyos], color=es.COLOR_APOYO,
                                             point_size=es.TAMANO_APOYO,
                                             render_points_as_spheres=True, name="apoyos")

    # Número de cada nodo, un poco arriba del punto
    tamano = np.ptp(puntos, axis=0).max() or 1.0      # tamaño del modelo
    arriba = puntos + [0, 0, es.SEPARACION_ETIQUETA * tamano]
    actores["etiquetas"] = vista.add_point_labels(
        arriba, [str(nid) for nid in ids], font_size=es.TAMANO_LETRA,
        text_color=es.COLOR_ETIQUETA, shape=None, show_points=False, always_visible=True,
        name="etiquetas")
    return actores


def paso_rejilla(largo, divisiones):
    """Paso "redondo" (1, 2 o 5 x 10^k) que da cerca de `divisiones` divisiones en `largo`.

    Ejemplo: largo 5 con 10 divisiones da 0.5; largo 20 da 2. Como solo depende del tamaño del
    modelo, sirve en cualquier unidad (m, cm, ft).
    """
    bruto = largo / divisiones
    potencia = 10.0 ** np.floor(np.log10(bruto))
    m = bruto / potencia                    # entre 1 y 10
    # Se corta en la media geométrica entre redondos vecinos: √2, √10 y √50
    redondo = 1 if m < np.sqrt(2) else 2 if m < np.sqrt(10) else 5 if m < np.sqrt(50) else 10
    return float(f"{redondo * potencia:.12g}")   # quita restos como 0.5000000000000001


def dibujar_rejilla(vista, modelo):
    """Rejilla de piso en la base del modelo. Devuelve su actor, o None si no hay nodos.

    - Está en el plano z = z mínimo del modelo, un poco más abajo (0.1 % del tamaño) para que no
      se pise con las barras que están a nivel de suelo.
    - Su borde cae en múltiplos del paso y sobresale de la planta del modelo.
    - No cuenta para el encuadre ni para el zoom (SetUseBounds(False)): la vista se ajusta al
      modelo, no a la rejilla.
    """
    if not modelo.nodos:
        return None
    puntos = np.array([n.coords for n in modelo.nodos.values()], dtype=float)
    minimo, maximo = puntos.min(axis=0), puntos.max(axis=0)
    tamano = np.ptp(puntos, axis=0).max() or 1.0                          # tamaño en 3D
    largo = max(maximo[0] - minimo[0], maximo[1] - minimo[1]) or tamano   # lado mayor en planta
    paso = paso_rejilla(largo, es.REJILLA_DIVISIONES)
    margen = es.REJILLA_MARGEN * largo
    x0, y0 = np.floor((minimo[:2] - margen) / paso) * paso
    x1, y1 = np.ceil((maximo[:2] + margen) / paso) * paso
    z = minimo[2] - 0.001 * tamano

    extremos = ([((x, y0, z), (x, y1, z)) for x in np.arange(x0, x1 + paso / 2, paso)]
                + [((x0, y, z), (x1, y, z)) for y in np.arange(y0, y1 + paso / 2, paso)])
    pts = np.array([p for par in extremos for p in par], dtype=float)
    n = len(extremos)
    lineas = np.column_stack([np.full(n, 2), np.arange(0, 2 * n, 2), np.arange(1, 2 * n, 2)]).ravel()
    actor = vista.add_mesh(pv.PolyData(pts, lines=lineas), color=es.COLOR_REJILLA,
                           line_width=es.GROSOR_REJILLA, lighting=False, pickable=False,
                           reset_camera=False, name="rejilla")
    actor.SetUseBounds(False)
    return actor
