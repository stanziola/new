"""Puente entre las secciones del modelo (unidades internas) y el cálculo de interacción (pint).

No es cálculo: solo convierte unidades y llama a calculo/interaccion, donde están las fórmulas.
El cálculo devuelve tonne_force (tonelada métrica) y tonne_force·m; aquí se pasan a kN y kN·m
(× 9.80665), que son las unidades internas del programa.
"""
import math
from functools import lru_cache

import numpy as np

from calculo.interaccion import biaxial, circular
from calculo.interaccion.comun import area_barra, limites_cuantia, propiedades_seccion, ureg

TONF_KN = 9.80665                       # kN por tonelada fuerza métrica (1000 kgf)
KN_M2 = ureg.kilonewton / ureg.meter ** 2


def propiedades(concreto):
    """Propiedades de la sección (el diccionario de calculo.interaccion) desde un Concreto."""
    fc, fy = concreto.fc * KN_M2, concreto.fy * KN_M2
    if concreto.forma == "circular":
        return circular.propiedades_circular(concreto.D * ureg.m, concreto.d * ureg.m,
                                             concreto.nbarras, fc, concreto.barra, fy)
    return propiedades_seccion(concreto.b * ureg.m, concreto.h * ureg.m, concreto.d * ureg.m,
                               concreto.nx, concreto.ny, fc, concreto.barra, fy)


def usada_en_columna(modelo, sid):
    """True si alguna columna (barra vertical) usa la sección sid. El aviso de cuantía es la regla de
    columnas (ACI 318-19 §10.6.1.1 y §18.7.4.1): en vigas no aplica (sus límites, de la etapa 5, son
    otros: §9.6.1.2, §9.3.3.1 y §18.6.3.1)."""
    return any(el.seccion == sid and modelo.es_columna(eid) for eid, el in modelo.elementos.items())


def aviso_cuantia(cuantia, especial):
    """Texto de aviso si la cuantía (%) de una columna se sale de sus límites, o "" si cumple."""
    minima, maxima = limites_cuantia(especial)
    if minima <= cuantia <= maxima:
        return ""
    regla = "pórtico especial, ACI 318-19 §18.7.4.1" if especial else "ACI 318-19 §10.6.1.1"
    return f"fuera de {minima:g} %–{maxima:g} % ({regla})"


@lru_cache(maxsize=None)
def diametro_barra(numero):
    """Diámetro de la barra de refuerzo en m (del área que usa el cálculo de interacción)."""
    return math.sqrt(4 * area_barra(numero).to("m^2").magnitude / math.pi)


def _a_lo_ancho(n, borde, ancho):
    """n posiciones repartidas en el ancho, a `borde` de cada cara (una sola: al centro)."""
    return [borde + i * (ancho - 2 * borde) / (n - 1) for i in range(n)] if n > 1 else [ancho / 2]


def posiciones_barras(c, con_numero=False):
    """Centros de las barras de una sección rectangular, en m, desde la esquina inferior izquierda:
    (a lo ancho b, a lo alto h). Nx barras en las caras de arriba y abajo y dos por cada fila
    intermedia: el mismo arreglo que usa el cálculo (calculo/interaccion/biaxial.py, _barras).
    En una T (con "b" el alma): nx barras abajo, repartidas en el alma, a d del borde inferior, y
    n_sup arriba, a d_superior del borde de arriba, también en el ancho del alma.
    con_numero: cada posición lleva también el número de su barra, (x, y, #)."""
    if c.forma == "T":
        from modelo.concreto import d_superior
        abajo = [(x, c.d, c.barra) for x in _a_lo_ancho(c.nx, min(c.d, c.b / 2), c.b)]
        arriba = []
        if c.n_sup:
            borde = min(d_superior(c), c.b / 2)
            arriba = [(x, c.h - d_superior(c), c.barra_sup) for x in _a_lo_ancho(c.n_sup, borde, c.b)]
        puntos = abajo + arriba
    else:
        xs = _a_lo_ancho(c.nx, c.d, c.b)
        ys = [c.d + j * (c.h - 2 * c.d) / (c.ny - 1) for j in range(c.ny)] if c.ny > 1 else [c.h / 2]
        puntos = [(x, ys[0]) for x in xs] + [(x, ys[-1]) for x in xs]
        puntos += [(x, y) for y in ys[1:-1] for x in (xs[0], xs[-1])]
        puntos = [(x, y, c.barra) for x, y in puntos]
    return puntos if con_numero else [(x, y) for x, y, _n in puntos]


def direccion_momento(my, mz):
    """Dirección (rad) del momento resultante de una barra en el plano de su sección, con los
    momentos My y Mz de la barra (ejes locales): 0 = flexión hacia b (solo Mz) y 90° = flexión hacia h
    (solo My). Es el ángulo que usa curva_direccion.

    Nombres: la sección tiene b en el eje local y, y h en el local z. El cálculo de interacción llama
    x al eje de b e y al de h, y nombra el momento por el eje HACIA el que flexiona: su "My" (Σ F·x,
    hacia b) es el Mz de la barra, y su "Mx" (Σ F·y, hacia h) es el My de la barra. Los signos
    coinciden: Mz > 0 comprime la cara +y local y My > 0, la cara +z local."""
    return math.atan2(my, mz)


def curva_direccion(concreto, sec, direccion):
    """Diagrama para un momento resultante con esa dirección (rad; direccion_momento): arreglos
    (Pn, Mn, φPn, φMn) en kN y kN·m, con Mn = √(My² + Mz²). Es el corte de la superficie contra el
    que se compara un punto Pu–Mu con momento en los dos ejes. En la circular, por simetría, la
    dirección no importa: es su curva de siempre."""
    if concreto.forma == "circular":
        datos = circular.curva_circ(sec, 100)
    else:
        datos = biaxial.curva_direccion(sec, direccion)
    return [np.asarray(d, dtype=float) * TONF_KN for d in datos]


def dentro_del_diagrama(phi_pn, phi_mn, pu, mu, tol=1e-6):
    """True si el punto (Pu, Mu) queda dentro del diagrama de diseño (o en su borde): la curva
    (φPn, φMn) de SU dirección (curva_direccion), cerrada por el eje P. Pu en kN (compresión
    positiva) y Mu, el momento resultante, en kN·m.

    A lo largo de la curva, de la tracción a la compresión, φPn nunca baja (comprobado en
    rectangulares de varias proporciones, en todas las direcciones, y en la circular). Así, la recta
    P = Pu corta la curva una sola vez, y el punto está dentro si Pu está entre el φPn menor (la
    tracción) y el mayor (el techo) y si Mu no pasa del φMn de la curva a esa altura. En el techo,
    que es plano, se toma el mayor φMn. tol es una holgura relativa para los puntos en el borde.

    Es una comparación para el aviso de la pantalla, no la relación demanda/capacidad del diseño
    (etapa 4)."""
    pn = np.asarray(phi_pn, dtype=float)
    mn = np.abs(np.asarray(phi_mn, dtype=float))
    holgura_p, holgura_m = tol * float(np.abs(pn).max()), tol * float(mn.max())
    if not pn.min() - holgura_p <= pu <= pn.max() + holgura_p:
        return False
    pu = min(max(pu, pn.min()), pn.max())               # si se pasó solo por la holgura, al borde
    a, b = pn[:-1], pn[1:]
    corta = (a <= pu) & (pu <= b) & (b > a)              # los tramos que cruzan P = Pu
    cortes = mn[:-1][corta] + (mn[1:][corta] - mn[:-1][corta]) * (pu - a[corta]) / (b[corta] - a[corta])
    en_altura = mn[np.abs(pn - pu) <= holgura_p]         # puntos justo a esa altura (el techo plano)
    capacidad = max(cortes.max(initial=0.0), en_altura.max(initial=0.0))
    return abs(mu) <= capacidad + holgura_m


def superficie_3d(concreto, sec):
    """Superficie de diseño: arreglos X = φMz, Y = φMy (kN·m) y Z = φPn (kN), con los nombres de los
    momentos de la barra (X: flexión hacia b; Y: flexión hacia h; ver direccion_momento). En el
    cálculo, X es su "φMy" e Y su "φMx".

    Rectangular: la superficie biaxial del cálculo. Circular: como es simétrica, la curva de diseño
    girada alrededor del eje P.
    """
    if concreto.forma == "circular":
        _, _, phi_pn, phi_mn = circular.curva_circ(sec, 100)
        giro = np.linspace(0, 2 * np.pi, 73)[:, None]
        X, Y, Z = phi_mn[None, :] * np.cos(giro), phi_mn[None, :] * np.sin(giro), np.tile(phi_pn, (73, 1))
    else:
        X, Y, Z = biaxial.superficie(sec)
    return [np.asarray(d, dtype=float) * TONF_KN for d in (X, Y, Z)]
