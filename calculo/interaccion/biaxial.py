"""Diagrama de interacción de columna rectangular con flexión biaxial (ACI 318-19).

Movido sin cambios desde iteracion3drect.py; sin la ventana tkinter.
curva() y superficie() son los cálculos que hacían App.curva y App.ver_3d, separados del dibujo.
"""
import math

import numpy as np

from .comun import KIP_TF, KIPIN_TFM, area_barra, module_s


def _recortar(poly, u, t0):
    """Recorta el polígono y conserva los puntos con p·u >= t0."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = p @ u - t0, q @ u - t0
        if fp >= 0:
            out.append(p)
        if fp * fq < 0:
            out.append(p + (q - p) * fp / (fp - fq))
    return np.array(out)


def _area_centroide(poly):
    if len(poly) < 3:
        return 0.0, 0.0, 0.0
    x, y = poly[:, 0], poly[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cr = x * y1 - x1 * y
    A = cr.sum() / 2
    if abs(A) < 1e-12:
        return 0.0, 0.0, 0.0
    cx = ((x + x1) * cr).sum() / (6 * A)
    cy = ((y + y1) * cr).sum() / (6 * A)
    return abs(A), cx, cy


def _barras(b, h, d, nx, ny):
    xs = np.linspace(-b/2 + d, b/2 - d, nx)
    ys = np.linspace(-h/2 + d, h/2 - d, ny)
    bars = []
    for j, y in enumerate(ys):
        for x in (xs if j in (0, ny - 1) else (xs[0], xs[-1])):
            bars.append((x, y))
    return np.array(bars)


def phipnmn_biaxial(c, theta, sec):
    """Unidades internas: in, ksi, kip. theta = dirección de la fibra comprimida (rad)."""
    b = sec["b"].to("inch").magnitude
    h = sec["h"].to("inch").magnitude
    d = sec["d"].to("inch").magnitude
    fc = sec["fc"].to("ksi").magnitude
    fy_val = sec["fy"].to("ksi").magnitude
    Es = module_s.to("ksi").magnitude
    ey = sec["epsilon_y"]
    As1 = area_barra(sec["nob"]).to("inch**2").magnitude
    As_total = sec["As_total"].to("inch**2").magnitude
    nx, ny = sec["nx"], sec["ny"]

    u = np.array([np.cos(theta), np.sin(theta)])
    tmax = (b / 2) * abs(u[0]) + (h / 2) * abs(u[1])
    a = min(sec["beta1"] * c, 2 * tmax)

    rect = np.array([[-b/2, -h/2], [b/2, -h/2], [b/2, h/2], [-b/2, h/2]])
    A, cx, cy = _area_centroide(_recortar(rect, u, tmax - a))
    Cc = 0.85 * fc * A
    P = Cc
    Mx = Cc * cy
    My = Cc * cx

    bars = _barras(b, h, d, nx, ny)
    t = tmax - bars @ u
    es = np.clip(0.003 * (c - t) / c, -ey, ey)
    fs = es * Es
    fs = np.where(t < a, fs - 0.85 * fc, fs)
    F = fs * As1
    P += F.sum()
    Mx += (F * bars[:, 1]).sum()
    My += (F * bars[:, 0]).sum()

    et = 0.003 * (t.max() - c) / c
    if et <= ey:
        phi = 0.65
    elif et >= ey + 0.003:
        phi = 0.90
    else:
        phi = 0.65 + 0.25 * (et - ey) / 0.003

    P0 = 0.85 * fc * (b * h - As_total) + fy_val * As_total
    phi_P = min(phi * P, 0.80 * 0.65 * P0)

    return phi, P, Mx, My, phi_P, phi * Mx, phi * My


def curva(sec, th, n_puntos=100):
    """Diagrama en la dirección th (rad): listas (Pn, Mn, φPn, φMn) en tonne_force y tonne_force·m.

    Es el cálculo de App.curva de iteracion3drect.py.
    """
    b = sec["b"].to("inch").magnitude
    h = sec["h"].to("inch").magnitude
    cth, sth = math.cos(th), math.sin(th)
    D = b * abs(cth) + h * abs(sth)
    cs = np.geomspace(0.001 * D, 3 * D, n_puntos)
    Pn, Mn, PPn, PMn = [], [], [], []
    for ci in cs:
        _, P, Mx, My, phi_P, phi_Mx, phi_My = phipnmn_biaxial(ci, th, sec)
        Pn.append(P * KIP_TF)
        Mn.append((My * cth + Mx * sth) * KIPIN_TFM)
        PPn.append(phi_P * KIP_TF)
        PMn.append((phi_My * cth + phi_Mx * sth) * KIPIN_TFM)
    return Pn, Mn, PPn, PMn


def curva_direccion(sec, lam, n_puntos=60, tol=1e-6):
    """Diagrama para un momento resultante de dirección lam (rad): listas (Pn, Mn, φPn, φMn) en
    tonne_force y tonne_force·m, con Mn = √(Mx² + My²).

    lam = atan2(Mx, My): 0 es flexión hacia +x (a lo largo de b) y 90°, hacia +y (a lo largo de h).
    Es el corte de la superficie de interacción por el semiplano vertical que contiene al eje P y a
    esa dirección: el diagrama contra el que se compara un punto (Pu, Mux, Muy) con ese momento.

    No es curva(sec, lam). Allí el ángulo es θ, la dirección de la fibra más comprimida, y el momento
    resultante de ese eje neutro apunta, en general, hacia otro lado: solo coinciden en 0°, 90°, 180°
    y 270° (y en 45° si la sección es cuadrada con el mismo acero en las cuatro caras).

    Para cada profundidad relativa del eje neutro (c = f·D(θ), con D la altura de la sección en la
    dirección θ, como en curva) se busca el θ cuyo momento resultante nominal tiene la dirección
    pedida. La sección es doblemente simétrica, así que se trabaja en el primer cuadrante, donde esa
    dirección vale 0 con θ = 0 y 90° con θ = 90°: siempre hay una raíz entre los dos. Se busca con
    falsa posición (variante Illinois), que encierra la raíz como la bisección pero llega en pocas
    evaluaciones.
    """
    b = sec["b"].to("inch").magnitude
    h = sec["h"].to("inch").magnitude
    lam = math.atan2(abs(math.sin(lam)), abs(math.cos(lam)))      # al primer cuadrante, por simetría

    def punto(f, th):
        D = b * abs(math.cos(th)) + h * abs(math.sin(th))
        return phipnmn_biaxial(f * D, th, sec)

    def desvio(r):
        return math.atan2(r[2], r[3]) - lam                       # dirección del momento − la pedida

    Pn, Mn, PPn, PMn = [], [], [], []
    for f in np.geomspace(0.001, 3, n_puntos):
        if lam < tol or lam > math.pi / 2 - tol:                  # un eje principal: θ = lam, sin buscar
            r = punto(f, 0.0 if lam < tol else math.pi / 2)
        else:
            lo, hi = 0.0, math.pi / 2
            r, g_lo, g_hi = None, -lam, math.pi / 2 - lam         # en los extremos, θ = dirección
            lado = 0
            for _ in range(60):
                th = (lo * g_hi - hi * g_lo) / (g_hi - g_lo)      # donde la recta entre los extremos da 0
                r = punto(f, th)
                g = desvio(r)
                if abs(g) < tol or hi - lo < 1e-12:
                    break
                if g < 0:
                    lo, g_lo = th, g
                    if lado < 0:
                        g_hi /= 2                                 # dos veces del mismo lado: se acerca el otro
                    lado = -1
                else:
                    hi, g_hi = th, g
                    if lado > 0:
                        g_lo /= 2
                    lado = 1
        Pn.append(r[1] * KIP_TF)
        Mn.append(math.hypot(r[2], r[3]) * KIPIN_TFM)
        PPn.append(r[4] * KIP_TF)
        PMn.append(math.hypot(r[5], r[6]) * KIPIN_TFM)
    return Pn, Mn, PPn, PMn


def superficie(sec, paso_grados=10, n_puntos=60):
    """Superficie de diseño: listas X = φMy, Y = φMx (tonne_force·m) y Z = φPn (tonne_force).

    Es el cálculo de App.ver_3d de iteracion3drect.py.
    """
    b = sec["b"].to("inch").magnitude
    h = sec["h"].to("inch").magnitude
    X, Y, Z = [], [], []
    for deg in range(0, 361, paso_grados):
        th = math.radians(deg)
        D = b * abs(math.cos(th)) + h * abs(math.sin(th))
        cs = np.geomspace(0.001 * D, 3 * D, n_puntos)
        r = [phipnmn_biaxial(c, th, sec) for c in cs]
        X.append([x[6] * KIPIN_TFM for x in r])   # φMy
        Y.append([x[5] * KIPIN_TFM for x in r])   # φMx
        Z.append([x[4] * KIP_TF for x in r])      # φPn
    return X, Y, Z
