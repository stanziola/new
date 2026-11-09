"""Puente entre las secciones del modelo (unidades internas) y el cálculo de interacción (pint).

No es cálculo: solo convierte unidades y llama a calculo/interaccion, donde están las fórmulas.
El cálculo devuelve tonne_force (tonelada métrica) y tonne_force·m; aquí se pasan a kN y kN·m
(× 9.80665), que son las unidades internas del programa.
"""
import numpy as np

from calculo.interaccion import biaxial, circular
from calculo.interaccion.comun import propiedades_seccion, ureg

TONF_KN = 9.80665                       # kN por tonelada fuerza métrica (1000 kgf)
KN_M2 = ureg.kilonewton / ureg.meter ** 2


def propiedades(concreto):
    """Propiedades de la sección (el diccionario de calculo.interaccion) desde un Concreto."""
    fc = concreto.fc * KN_M2
    if concreto.forma == "circular":
        return circular.propiedades_circular(concreto.D * ureg.m, concreto.d * ureg.m,
                                             concreto.nbarras, fc, concreto.barra)
    return propiedades_seccion(concreto.b * ureg.m, concreto.h * ureg.m, concreto.d * ureg.m,
                               concreto.nx, concreto.ny, fc, concreto.barra)


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
