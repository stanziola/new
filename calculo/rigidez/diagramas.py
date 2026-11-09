"""Fuerzas internas y deformada a lo largo de una barra. SAGRADO.

Datos: el largo L, las 12 fuerzas de los extremos (las que los nodos ejercen sobre la barra, en ejes
locales, [N, Vy, Vz, T, My, Mz] de i y de j; con cargas en la barra ya incluyen las FEF) y las
cargas de la barra en ejes locales (como en empotramiento.py).

Fuerzas internas en una sección x: equilibrio del tramo de 0 a x. La parte derecha ejerce sobre
la cara positiva (la que mira hacia +x) de la parte izquierda:
    S = −(F_i + cargas entre 0 y x)                       fuerza
    Mc = −(M_i + r_i × F_i + Σ r × cargas)                momento respecto de la sección
con r medido desde la sección. Los diagramas usan la convención clásica de vigas:
    N = Sx       > 0 es tracción
    Vy = −Sy,  Vz = −Sz
    T = Mcx
    Mz = Mcz     > 0 tracciona la fibra −y
    My = −Mcy    > 0 tracciona la fibra −z
Así, en una viga con z hacia arriba (α = 0), My > 0 es el momento positivo: la viga simple con
carga hacia abajo da My = wL²/8 al centro y Vz = wL/2 en el apoyo izquierdo. Y se cumple, en los
dos planos, dM/dx = V (dMz/dx = Vy, dMy/dx = Vz) y dV/dx = q (la carga en el sentido +y o +z).
En una carga puntual hay salto: la sección x = a se evalúa dos veces, justo antes y justo después.

Deformada (Euler-Bernoulli), en ejes locales, integrando:
    u' = N/EA,  φ' = T/GJ,  v'' = Mz/(E·Iz),  w'' = My/(E·Iy)
u y φ parten del extremo i; v y w usan los desplazamientos de los dos extremos (v(0) = vi y
v(L) = vj), así la curva es la exacta para estas fuerzas y coincide con los nodos.
"""
import numpy as np

NOMBRES = ("N", "Vy", "Vz", "T", "My", "Mz")


def secciones(L, cargas, n=41):
    """Puntos x donde evaluar: n puntos parejos y, en cada carga puntual, dos (antes y después).

    Devuelve (x, lado): lado = −1 si la sección queda justo antes de una carga en ese x, +1 si no."""
    xs = [(float(x), 1) for x in np.linspace(0.0, L, n)]
    for tipo, _vector, a in cargas:
        if tipo != "uniforme" and 0.0 < a < L:
            xs += [(float(a), -1), (float(a), 1)]
    xs = sorted(set(xs))
    return np.array([x for x, _ in xs]), np.array([lado for _, lado in xs])


def internas(L, fuerzas, cargas, x=None, lado=None):
    """Fuerzas internas en cada sección: diccionario {"N", "Vy", "Vz", "T", "My", "Mz", "x"}."""
    if x is None:
        x, lado = secciones(L, cargas)
    x = np.asarray(x, dtype=float)
    lado = np.ones_like(x) if lado is None else np.asarray(lado)
    f = np.asarray(fuerzas, dtype=float)
    fi, mi = f[0:3], f[3:6]
    e1 = np.array([1.0, 0.0, 0.0])
    S = np.zeros((len(x), 3))
    M = np.zeros((len(x), 3))
    for k, xk in enumerate(x):
        fuerza = fi.copy()
        momento = mi + np.cross(-xk * e1, fi)          # r_i = (−x, 0, 0)
        for tipo, vector, a in cargas:
            v = np.asarray(vector, dtype=float)
            if tipo == "uniforme":                     # resultante q·x en el centro del tramo, x/2
                fuerza += v * xk
                momento += np.cross(-xk / 2 * e1, v * xk)
                continue
            antes = a < xk or (a == xk and lado[k] > 0)
            if not antes:
                continue
            if tipo == "puntual":
                fuerza += v
                momento += np.cross((a - xk) * e1, v)
            else:                                      # momento concentrado
                momento += v
        S[k] = -fuerza
        M[k] = -momento
    return {"x": x, "N": S[:, 0], "Vy": -S[:, 1], "Vz": -S[:, 2],
            "T": M[:, 0], "My": -M[:, 1], "Mz": M[:, 2]}


def _integral(x, y):
    """Integral acumulada por trapecios, desde 0 (vale 0 en x[0])."""
    pasos = np.diff(x) * (y[1:] + y[:-1]) / 2
    return np.concatenate([[0.0], np.cumsum(pasos)])


def deformada(L, fuerzas, cargas, u_local, e, g, a, iy, iz, j, x=None, n_fino=801):
    """Desplazamientos locales a lo largo de la barra: {"x", "u", "v", "w", "phi"}.

    u_local: los 12 desplazamientos locales de los extremos [ui, vi, wi, φxi, φyi, φzi, uj, ...].
    Se integra en una malla fina (n_fino puntos, con las cargas puntuales) para que el error de la
    integración numérica sea despreciable, y se devuelve en los puntos x pedidos."""
    xf, lado = secciones(L, cargas, n_fino)
    d = internas(L, fuerzas, cargas, xf, lado)
    ul = np.asarray(u_local, dtype=float)
    u = ul[0] + _integral(xf, d["N"] / (e * a))
    phi = ul[3] + _integral(xf, d["T"] / (g * j))

    def flecha(curvatura, inicio, fin):
        gx = _integral(xf, _integral(xf, curvatura))
        c = (fin - inicio - gx[-1]) / L
        return inicio + c * xf + gx

    v = flecha(d["Mz"] / (e * iz), ul[1], ul[7])
    w = flecha(d["My"] / (e * iy), ul[2], ul[8])
    x = secciones(L, cargas)[0] if x is None else np.asarray(x, dtype=float)
    return {"x": x, **{k: np.interp(x, xf, y) for k, y in (("u", u), ("v", v), ("w", w), ("phi", phi))}}
