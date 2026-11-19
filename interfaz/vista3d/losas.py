"""Dibujo de las losas de viguetas en la vista 3D.

- Con la sección real: en cada paño, la losa de arriba (espesor hf) con su cara de arriba al ras de la
  de las vigas de apoyo, de cara a cara de las vigas, y los nervios (bw × (h − hf)) en las posiciones
  de las viguetas (la rejilla común de la losa, modelo/losas.posiciones). Es concreto: va con el gris
  de los elementos, se pinta como seleccionado y toma la transparencia del concreto.
- Sin la sección real: un paño translúcido al nivel de los ejes de las vigas (para saber dónde hay
  losa).
- Acero (se ve con transparencia, como el de vigas y columnas), esquemático:
  - abajo, las barras de cada nervio de eje a eje de los apoyos: siguen de un paño al siguiente,
    continuas (§9.8.1.6);
  - arriba, las barras sobre cada apoyo, hasta ℓn/3 de la cara en un apoyo interior y ℓn/5 en uno
    exterior. Es una práctica usual, no un corte de barras diseñado (el corte y el anclaje son de la
    etapa 5).
- Las losas no se dibujan con resultados a la vista (tampoco en la deformada): solo vigas y columnas
  (decisión del usuario). Las dibuja la ventana solo al editar.

Las coordenadas de la losa son (u, v, z): u a lo largo de las vigas de apoyo (t), v a lo largo de las
viguetas (n). Un punto es u·t + v·n + z·Z.
"""
import numpy as np
import pyvista as pv

from configuracion import colores
from modelo.interaccion import diametro_barra, posiciones_barras

OPACIDAD_SIN_SECCION = 0.25            # el paño translúcido, sin la sección real
FRACCION_INTERIOR = 1 / 3              # barras de arriba: ℓn/3 de la cara en un apoyo interior
FRACCION_EXTERIOR = 1 / 5              # y ℓn/5 en uno exterior


def _punto(t, n, u, v, z):
    return u * t + v * n + np.array([0.0, 0.0, z])


def _caja(t, n, u0, u1, v0, v1, z0, z1):
    """Caja de [u0, u1] × [v0, v1] × [z0, z1] en las coordenadas de la losa."""
    esquinas = [_punto(t, n, u, v, z) for v in (v0, v1) for u, z in ((u0, z0), (u1, z0), (u1, z1), (u0, z1))]
    caras = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
    return pv.PolyData(np.array(esquinas), np.hstack([[4] + c for c in caras]))


def _rectangulo(t, n, u0, u1, v0, v1, z):
    esquinas = [_punto(t, n, u, v, z) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
    return pv.PolyData(np.array(esquinas), np.array([4, 0, 1, 2, 3]))


def _interiores(geos):
    """{(ID de paño, "a" o "b"): True} si ese apoyo del paño es interior: otro paño de la losa sigue del
    otro lado de la misma viga (con tramo en común)."""
    salida = {}
    for pid, g in geos.items():
        for lado, v in (("a", g.va), ("b", g.vb)):
            salida[(pid, lado)] = any(
                otro != pid and abs((h.vb if lado == "a" else h.va) - v) < 1e-3
                and min(g.u1, h.u1) - max(g.u0, h.u0) > 1e-3 for otro, h in geos.items())
    return salida


def mallas_losas(modelo, resumenes, seccion_real):
    """(concreto, acero, indices, esquinas):
    - concreto: lista de (ID de paño, malla) con la losa y los nervios de cada paño (o el paño
      translúcido sin la sección real);
    - acero: lista de (radio, puntos, líneas) de las barras de las viguetas (vacía sin sección real);
    - esquinas: {ID de paño: (4 esquinas de arriba)} para elegir un paño con un clic.
    resumenes: {ID de losa: modelo.losas.resumen(...)}."""
    concreto, acero, esquinas = [], {}, {}
    for lid, r in resumenes.items():
        if "error" in r:
            continue
        losa = modelo.losas[lid]
        c = modelo.secciones[losa.seccion].concreto
        t, n = r["ejes"]
        interiores = _interiores(r["geos"])
        for pid, datos in r["panos"].items():
            g = datos["geo"]
            v0, v1 = g.va + g.ancho_a / 2, g.vb - g.ancho_b / 2       # de cara a cara de los apoyos
            arriba = g.tope
            esquinas[pid] = [_punto(t, n, u, v, arriba) for u, v in ((g.u0, g.va), (g.u1, g.va), (g.u1, g.vb),
                                                                      (g.u0, g.vb))]
            if not seccion_real:
                concreto.append((pid, _rectangulo(t, n, g.u0, g.u1, g.va, g.vb, g.z)))
                continue
            partes = [_caja(t, n, g.libre_0, g.libre_1, v0, v1, arriba - c.hf, arriba)]
            for u in datos["viguetas"]:
                partes.append(_caja(t, n, u - c.b / 2, u + c.b / 2, v0, v1, arriba - c.h, arriba - c.hf))
            malla = partes[0]
            for p in partes[1:]:
                malla = malla.merge(p, merge_points=False)
            concreto.append((pid, malla))
            # Acero: abajo, de eje a eje (sigue al paño de al lado); arriba, sobre cada apoyo
            ln = g.claro_libre
            for u in datos["viguetas"]:
                for x, y, numero in posiciones_barras(c, con_numero=True):
                    radio = diametro_barra(numero) / 2
                    du = x - c.b / 2
                    z = arriba - c.h + y
                    if y < c.h / 2:                                    # abajo
                        tramos = [(g.va, g.vb)]
                    else:                                              # arriba: sobre los apoyos
                        tramos = []
                        for lado, v, cara, signo in (("a", g.va, v0, 1), ("b", g.vb, v1, -1)):
                            largo = ln * (FRACCION_INTERIOR if interiores[(pid, lado)] else FRACCION_EXTERIOR)
                            extremo = cara + signo * largo
                            tramos.append(tuple(sorted((v, extremo))))
                    puntos, lineas = acero.setdefault(radio, ([], []))
                    for a, b in tramos:
                        k = len(puntos)
                        puntos += [_punto(t, n, u + du, a, z), _punto(t, n, u + du, b, z)]
                        lineas += [2, k, k + 1]
    return concreto, [(radio, p, l) for radio, (p, l) in acero.items()], esquinas


def malla_acero(acero):
    """Une los tubos del acero en una malla (o None)."""
    tubos = [pv.PolyData(np.array(p), lines=np.array(l)).tube(radius=radio, n_sides=10, capping=True)
             for radio, p, l in acero if p]
    if not tubos:
        return None
    return tubos[0].merge(tubos[1:]) if len(tubos) > 1 else tubos[0]


def cortes_superiores(franja, modelo_franja):
    """En la vista de un sistema de vigueta: {ID de barra: [(x0, x1)]} por dónde van las barras de
    arriba de cada claro (ℓn/3 de la cara en los apoyos interiores, ℓn/5 en los exteriores), en la
    misma regla que el dibujo de la losa."""
    barras = sorted(modelo_franja.elementos)
    n = len(barras)
    salida = {}
    for k, eid in enumerate(barras):
        largo, ln = franja.claros[k], franja.libre(k)
        cara_i, cara_j = franja.anchos[k] / 2, largo - franja.anchos[k + 1] / 2
        fi = FRACCION_INTERIOR if k > 0 else FRACCION_EXTERIOR
        fj = FRACCION_INTERIOR if k < n - 1 else FRACCION_EXTERIOR
        salida[eid] = [(0.0, min(largo, cara_i + fi * ln)), (max(0.0, cara_j - fj * ln), largo)]
    return salida


def colores_base(cantidad):
    """Colores (RGB por celda) de las losas sin seleccionar: el gris de los elementos."""
    return np.tile(np.array(colores.rgb(colores.ELEMENTO), dtype=np.uint8), (cantidad, 1))


def resumenes(modelo):
    """{ID de losa: resumen} de todas las losas (modelo/losas.resumen)."""
    from modelo.losas import resumen
    return {lid: resumen(modelo, lid) for lid in getattr(modelo, "losas", {})}
