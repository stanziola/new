"""Diagrama de interacción de columna circular (ACI 318-19).

Movido desde iteracion2dcir.py; sin los gráficos ni los datos de ejemplo.

El refuerzo transversal son aros (estribos circulares cerrados), como en la rectangular: φ de la
Tabla 21.2.2 (b), (d) y (f) y Pn,max = 0.80·Po (Tabla 22.4.2.1 (a)). ACI 318-19, PDF p. 395 y 402.
La espiral (φ = 0.75 y 0.85·Po) no se usa: se quitó a pedido del usuario (noviembre de 2026). Con una
columna con espiral, estos valores quedan del lado seguro.
"""
import math

import numpy as np

from .comun import FY, Ast, area_barra, beta1, module_s


def propiedades_circular(D, d, nbarras, fc, nob, fy=FY):
    Ag = math.pi * D**2 / 4
    As_total = Ast(nob, nbarras).to("cm^2")
    fy_val = fy
    return {
        "D": D, "d": d, "nbarras": nbarras, "fc": fc, "nob": nob,
        "As_total": As_total,
        "cuantia": (As_total / Ag).to("dimensionless").magnitude * 100,
        "beta1": beta1(fc),
        "fy": fy_val,
        "epsilon_y": (fy_val / module_s).to("dimensionless").magnitude,
    }


def phipnmn_circ(c, sec):
    """c en pulgadas. Devuelve phi, Pn, Mn, phiPn, phiMn en tonne_force y tonne_force*m."""
    D = sec["D"].to("inch").magnitude
    R = D / 2
    Rs = R - sec["d"].to("inch").magnitude          # radio de la circunferencia de barras
    fc = sec["fc"].to("ksi").magnitude
    fy_val = sec["fy"].to("ksi").magnitude
    Es = module_s.to("ksi").magnitude
    ey = sec["epsilon_y"]
    As1 = area_barra(sec["nob"]).to("inch**2").magnitude
    As_total = sec["As_total"].to("inch**2").magnitude
    nbar = sec["nbarras"]

    # concreto: segmento circular de profundidad a
    a = min(sec["beta1"] * c, D)
    alpha = math.acos(max(-1.0, min(1.0, (R - a) / R)))
    A = R**2 * (alpha - math.sin(alpha) * math.cos(alpha))
    if alpha < 1e-6:
        ybar = R
    else:
        ybar = 4 * R * math.sin(alpha)**3 / (3 * (2 * alpha - math.sin(2 * alpha)))
    Cc = 0.85 * fc * A
    P = Cc
    M = Cc * ybar                                   # respecto al centro

    # barras igualmente espaciadas; la primera en la fibra comprimida
    ang = 2 * np.pi * np.arange(nbar) / nbar
    arm = Rs * np.cos(ang)                          # brazo respecto al centro (+ hacia compresión)
    t = R - arm                                     # distancia a la fibra extrema
    es = np.clip(0.003 * (c - t) / c, -ey, ey)
    fs = es * Es
    fs = np.where(t < a, fs - 0.85 * fc, fs)
    F = fs * As1
    P += F.sum()
    M += (F * arm).sum()

    # phi con la barra más lejana de la fibra comprimida (columna con aros)
    et = 0.003 * (t.max() - c) / c
    if et <= ey:
        phi = 0.65
    elif et >= ey + 0.003:
        phi = 0.90
    else:
        phi = 0.65 + 0.25 * (et - ey) / 0.003

    P0 = 0.85 * fc * (math.pi * R**2 - As_total) + fy_val * As_total
    phi_P = min(phi * P, 0.80 * 0.65 * P0)

    kip_tf = 0.45359237                 # kip -> tonne_force
    kipin_tfm = 0.45359237 * 0.0254     # kip*in -> tonne_force*m
    return phi, P * kip_tf, M * kipin_tfm, phi_P * kip_tf, phi * M * kipin_tfm


def curva_circ(sec, n_puntos=100):
    D = sec["D"].to("inch").magnitude
    cs = np.geomspace(0.001 * D, 3 * D, n_puntos)
    Pn, Mn, PhiPn, PhiMn = [], [], [], []
    for ci in cs:
        _, pn, mn, phi_pn, phi_mn = phipnmn_circ(ci, sec)
        Pn.append(pn); Mn.append(mn)
        PhiPn.append(phi_pn); PhiMn.append(phi_mn)
    return np.array(Pn), np.array(Mn), np.array(PhiPn), np.array(PhiMn)
