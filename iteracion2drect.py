import math
import pint
import matplotlib.pyplot as plt
import numpy as np
ureg = pint.UnitRegistry()
ureg.define("tonne_force = 1000 * kilogram_force")

DIAM_ESPECIAL = {9: 1.128, 10: 1.270, 11: 1.410}

# VARIABLES
b = 0.65 * ureg.m
h = 0.65 * ureg.m
c = 3.25 * ureg.cm
fc = 4 * ureg.ksi
nob = 8
nx = 5
ny = 5
d = 7.5 * ureg.cm
module_s = 29000 * ureg.ksi

def area_barra(n, cantidad=1):
    d = DIAM_ESPECIAL.get(n, n / 8) * ureg.inch
    return cantidad * math.pi * d**2 / 4

def beta1(fc):
    fc = fc.to("ksi").magnitude
    if fc <= 2.5:
        raise ValueError("fc debe ser mayor a 2.5 ksi")
    elif fc <= 4:
        return 0.85
    elif fc >= 8:
        return 0.65
    else:
        return 1.05 - 0.05 * fc

def fy(n):
    if n >= 4:
        return 60 * ureg.ksi
    else:
        return 40 * ureg.ksi

def nb(nx, ny):
    return 2 * (nx + ny - 2)

def Ast(n, cantidad):
    return area_barra(n, cantidad)

def rho(Ast, b, h):
    return (Ast / (b * h)).to("dimensionless").magnitude * 100

def barras_en_a(a, h, d, nx, ny):
    sep = (h - 2 * d) / (ny - 1)
    total = 0
    for i in range(ny):
        di = d + i * sep
        if di < a:
            total += nx if i in (0, ny - 1) else 2
    return total

def propiedades_seccion(b, h, d, nx, ny, fc, nob):
    nbarras = nb(nx, ny)
    As_total = Ast(nob, nbarras).to("cm^2")
    fy_val = fy(nob)
    return {
        "b": b, "h": h, "d": d, "nx": nx, "ny": ny, "fc": fc, "nob": nob,
        "nbarras": nbarras,
        "As_total": As_total,
        "cuantia": rho(As_total, b, h),
        "beta1": beta1(fc),
        "fy": fy_val,
        "epsilon_y": (fy_val / module_s).magnitude,
    }

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

def mostrar_propiedades(sec):
    print(f"Área de acero = {sec['As_total']:.2f}")
    print(f"Cuantía = {sec['cuantia']:.2f}%")
    print(f"Beta1 = {sec['beta1']:.2f}")
    print(f"Fy = {sec['fy']:.2f}")
    print(f"Epsilon_y = {sec['epsilon_y']:.6f}")
    print(f"Cantidad de barras = {sec['nbarras']}")

    if sec["cuantia"] < 1:
        print("Menor al 1% mínimo: no cumple.")
    elif sec["cuantia"] > 8:
        print("Mayor al 8% máximo: no cumple.")
    else:
        print("Cumple los límites de cuantía")

def mostrar_resultados(phi, pn, mn, phi_pn, phi_mn):
    print(f"φ = {phi:.3f}")
    print(f"Pn = {pn:.1f}")
    print(f"Mn = {mn:.1f}")
    print(f"φPn = {phi_pn:.1f}")
    print(f"φMn = {phi_mn:.1f}")

def graficar_diagrama(sec, n_puntos=100):
    h = sec["h"].to("m").magnitude
    cs = np.geomspace(0.001 * h, 3 * h, n_puntos) * ureg.m

    Pn, Mn, PhiPn, PhiMn = [], [], [], []
    for ci in cs:
        phi, pn, mn, phi_pn, phi_mn = phipnmn(ci, sec)
        Pn.append(pn.magnitude)
        Mn.append(mn.magnitude)
        PhiPn.append(phi_pn.magnitude)
        PhiMn.append(phi_mn.magnitude)

    plt.figure(figsize=(7, 8))
    plt.plot(Mn, Pn, label="Nominal (Mn, Pn)")
    plt.plot(PhiMn, PhiPn, label="Diseño (φMn, φPn)")
    plt.axhline(0, color="k", linewidth=0.8)
    plt.axvline(0, color="k", linewidth=0.8)
    plt.xlabel("M (ton·m)")
    plt.ylabel("P (ton)")
    plt.title("Diagrama de interacción")
    plt.grid(True)
    plt.legend()
    plt.show()

sec = propiedades_seccion(b, h, d, nx, ny, fc, nob)
graficar_diagrama(sec)