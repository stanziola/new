"""Diagrama de interacción de columna rectangular con flexión en un eje (ACI 318-19).

Movido sin cambios desde iteracion2drect.py; sin el gráfico ni los datos de ejemplo.
curva() es el cálculo que hacía graficar_diagrama, separado del dibujo.
"""
import numpy as np

from .comun import area_barra, module_s, propiedades_seccion, ureg  # noqa: F401 (propiedades_seccion se usa desde aquí)


def barras_en_a(a, h, d, nx, ny):
    sep = (h - 2 * d) / (ny - 1)
    total = 0
    for i in range(ny):
        di = d + i * sep
        if di < a:
            total += nx if i in (0, ny - 1) else 2
    return total


def phipnmn(c, sec):
    b, h, d, fc = sec["b"], sec["h"], sec["d"], sec["fc"]
    nx, ny = sec["nx"], sec["ny"]
    fy_val, ey = sec["fy"], sec["epsilon_y"]
    As1 = area_barra(sec["nob"])

    a = min(sec["beta1"] * c, h)
    Cc = 0.85 * fc * b * a
    pn = Cc
    mn = Cc * (h / 2 - a / 2)

    sep = (h - 2 * d) / (ny - 1)
    for i in range(ny):
        yi = d + i * sep                      # desde la fibra comprimida
        n = nx if i in (0, ny - 1) else 2     # barras en esa fila
        esi = (0.003 * (c - yi) / c).to("dimensionless").magnitude
        esi = max(-ey, min(ey, esi))          # limita a ±εy (cedencia)
        fsi = esi * module_s
        if yi < a:
            fsi = fsi - 0.85 * fc
        Fi = fsi * n * As1
        pn += Fi
        mn += Fi * (h / 2 - yi)               # brazo respecto al centroide

    # phi según la deformación de la última fila
    et = (0.003 * (h - d - c) / c).to("dimensionless").magnitude
    if et <= ey:
        phi = 0.65
    elif et >= ey + 0.003:
        phi = 0.90
    else:
        phi = 0.65 + 0.25 * (et - ey) / 0.003

    # límite de carga axial
    P0 = 0.85 * fc * (b * h - sec["As_total"]) + fy_val * sec["As_total"]
    phi_pn = min(phi * pn, 0.80 * 0.65 * P0)
    phi_mn = phi * mn

    pn = pn.to("tonne_force")
    mn = mn.to("tonne_force*m")
    phi_pn = phi_pn.to("tonne_force")
    phi_mn = phi_mn.to("tonne_force*m")

    return phi, pn, mn, phi_pn, phi_mn


def curva(sec, n_puntos=100):
    """Puntos del diagrama: arreglos (Pn, Mn, φPn, φMn) en tonne_force y tonne_force·m."""
    h = sec["h"].to("m").magnitude
    cs = np.geomspace(0.001 * h, 3 * h, n_puntos) * ureg.m

    Pn, Mn, PhiPn, PhiMn = [], [], [], []
    for ci in cs:
        phi, pn, mn, phi_pn, phi_mn = phipnmn(ci, sec)
        Pn.append(pn.magnitude)
        Mn.append(mn.magnitude)
        PhiPn.append(phi_pn.magnitude)
        PhiMn.append(phi_mn.magnitude)
    return np.array(Pn), np.array(Mn), np.array(PhiPn), np.array(PhiMn)
