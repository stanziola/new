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
                                             concreto.nbarras, fc, concreto.barra, fy, concreto.confinamiento)
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


def posiciones_barras(c):
    """Centros de las barras de una sección rectangular, en m, desde la esquina inferior izquierda:
    (a lo ancho b, a lo alto h). Nx barras en las caras de arriba y abajo y dos por cada fila
    intermedia: el mismo arreglo que usa el cálculo (calculo/interaccion/biaxial.py, _barras)."""
    xs = [c.d + i * (c.b - 2 * c.d) / (c.nx - 1) for i in range(c.nx)] if c.nx > 1 else [c.b / 2]
    ys = [c.d + j * (c.h - 2 * c.d) / (c.ny - 1) for j in range(c.ny)] if c.ny > 1 else [c.h / 2]
    puntos = [(x, ys[0]) for x in xs] + [(x, ys[-1]) for x in xs]
    puntos += [(x, y) for y in ys[1:-1] for x in (xs[0], xs[-1])]
    return puntos


def curva_2d(concreto, sec, theta=0.0):
    """Diagrama 2D: arreglos (Pn, Mn, φPn, φMn) en kN y kN·m. theta (rad) solo en la rectangular."""
    if concreto.forma == "circular":
        datos = circular.curva_circ(sec, 100)
    else:
        datos = biaxial.curva(sec, theta, 100)
    return [np.asarray(d, dtype=float) * TONF_KN for d in datos]


def superficie_3d(concreto, sec):
    """Superficie de diseño: arreglos X = φMy, Y = φMx (kN·m) y Z = φPn (kN).

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
