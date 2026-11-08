import math
import pint
import numpy as np
import matplotlib.pyplot as plt

ureg = pint.UnitRegistry()
ureg.define("tonne_force = 1000 * kilogram_force")

DIAM_ESPECIAL = {9: 1.128, 10: 1.270, 11: 1.410}

# VARIABLES
D = 0.7335 * ureg.m
d = 7.5 * ureg.cm
nbarras = 16
nob = 8
fc = 4 * ureg.ksi
module_s = 29000 * ureg.ksi

# ---------- Funciones base ----------
def area_barra(n, cantidad=1):
    diam = DIAM_ESPECIAL.get(n, n / 8) * ureg.inch
    return cantidad * math.pi * diam**2 / 4

def Ast(n, cantidad):
    return area_barra(n, cantidad)

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

# ---------- Sección circular ----------
def propiedades_circular(D, d, nbarras, fc, nob):
    Ag = math.pi * D**2 / 4
    As_total = Ast(nob, nbarras).to("cm^2")
    fy_val = fy(nob)
    return {
        "D": D, "d": d, "nbarras": nbarras, "fc": fc, "nob": nob,
        "As_total": As_total,
        "cuantia": (As_total / Ag).to("dimensionless").magnitude * 100,
        "beta1": beta1(fc),
        "fy": fy_val,
        "epsilon_y": (fy_val / module_s).magnitude,
    }

def mostrar_propiedades_circ(sec):
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

    # phi con la barra más lejana de la fibra comprimida
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

# ---------- Gráficos ----------
def graficar_diagrama_circ(sec, n_puntos=100):
    Pn, Mn, PhiPn, PhiMn = curva_circ(sec, n_puntos)

    plt.figure(figsize=(7, 8))
    plt.plot(Mn, Pn, label="Nominal (Mn, Pn)")
    plt.plot(PhiMn, PhiPn, label="Diseño (φMn, φPn)")
    plt.axhline(0, color="k", linewidth=0.8)
    plt.axvline(0, color="k", linewidth=0.8)
    plt.xlabel("M (ton·m)")
    plt.ylabel("P (ton)")
    plt.title("Diagrama de interacción - columna circular")
    plt.grid(True)
    plt.legend()
    plt.show()

def graficar_circ_3d(sec, n_puntos=100, n_theta=72):
    Pn, Mn, PhiPn, PhiMn = curva_circ(sec, n_puntos)
    th = np.linspace(0, 2 * np.pi, n_theta + 1)[:, None]

    def revolucion(M, P):
        return M[None, :] * np.cos(th), M[None, :] * np.sin(th), np.tile(P, (len(th), 1))

    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(*revolucion(Mn, Pn),
                    color="lightskyblue", alpha=0.35, linewidth=0, shade=False)
    ax.plot_surface(*revolucion(PhiMn, PhiPn),
                    color="gray", alpha=0.5, linewidth=0, shade=False)
    ax.set_xlabel("M x (ton·m)")
    ax.set_ylabel("M y (ton·m)")
    ax.set_zlabel("P (ton)")
    ax.set_title("Superficie de interacción - columna circular")
    plt.show()

# ---------- Ejecución ----------
sec = propiedades_circular(D, d, nbarras, fc, nob)
mostrar_propiedades_circ(sec)
graficar_diagrama_circ(sec)