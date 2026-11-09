"""Fuerzas de empotramiento de las cargas en barras (FEF). SAGRADO.

Una barra recta de largo L, con sus dos extremos empotrados, recibe cargas en ejes LOCALES
(x a lo largo de la barra, de i a j; y, z los de la sección). Las FEF son las fuerzas que los
nodos (los empotramientos) ejercen sobre la barra, en el orden del programa:
    [N, Vy, Vz, T, My, Mz] del nodo i y luego del nodo j.

Cómo se usan en el método de rigidez (Kassimali, cap. de cargas en barras):
1. cargas nodales equivalentes = −FEF (lo que la barra empotrada le hace a los nodos), pasadas a
   globales con Tᵀ;
2. después de resolver: fuerzas en los extremos = k·u + FEF.

De dónde salen: las cargas equivalentes son el trabajo de la carga sobre las funciones de forma de
la barra (lineales para N y T, cúbicas de Hermite para la flexión). Con ξ = a/L:
    N1 = 1 − 3ξ² + 2ξ³,  N2 = L(ξ − 2ξ² + ξ³),  N3 = 3ξ² − 2ξ³,  N4 = L(−ξ² + ξ³)
En el plano x–y, θz = dv/dx; en el plano x–z, θy = −dw/dx (por eso cambian los signos de My).
Resultados conocidos que salen de aquí (b = L − a):
    uniforme q:  qL/2 en cada extremo y qL²/12 de momento
    puntual P:   P·b²(3a + b)/L³ y P·a²(a + 3b)/L³;  momentos P·a·b²/L² y P·a²·b/L²
    momento M:   6·M·a·b/L³;  momentos M·b(b − 2a)/L² y M·a(a − 2b)/L²
Unidades: las que se usen (kN, kN/m, kN·m y m en el programa).
"""
import numpy as np


def _forma(L, a):
    """Funciones de forma y sus derivadas en x = a: lineales (Li, Lj) y de Hermite (N1..N4)."""
    xi = a / L
    lineal = (1 - xi, xi)
    hermite = (1 - 3 * xi ** 2 + 2 * xi ** 3, L * (xi - 2 * xi ** 2 + xi ** 3),
               3 * xi ** 2 - 2 * xi ** 3, L * (-xi ** 2 + xi ** 3))
    derivadas = ((-6 * xi + 6 * xi ** 2) / L, 1 - 4 * xi + 3 * xi ** 2,
                 (6 * xi - 6 * xi ** 2) / L, -2 * xi + 3 * xi ** 2)
    return lineal, hermite, derivadas


def equivalentes_puntual(L, a, fuerza, momento):
    """Cargas nodales equivalentes (12, locales) de una fuerza [Px, Py, Pz] y un momento
    [Mx, My, Mz] concentrados en x = a."""
    (li, lj), (n1, n2, n3, n4), (d1, d2, d3, d4) = _forma(L, a)
    px, py, pz = fuerza
    mx, my, mz = momento
    p = np.zeros(12)
    # Axial y torsión: reparto lineal
    p[0] += px * li
    p[6] += px * lj
    p[3] += mx * li
    p[9] += mx * lj
    # Plano x–y (v, θz = dv/dx): fuerza Py y momento Mz
    p[1] += py * n1 + mz * d1
    p[5] += py * n2 + mz * d2
    p[7] += py * n3 + mz * d3
    p[11] += py * n4 + mz * d4
    # Plano x–z (w, θy = −dw/dx): fuerza Pz y momento My
    p[2] += pz * n1 - my * d1
    p[4] += -pz * n2 + my * d2
    p[8] += pz * n3 - my * d3
    p[10] += -pz * n4 + my * d4
    return p


def equivalentes_uniforme(L, q):
    """Cargas nodales equivalentes (12, locales) de una carga uniforme q = [qx, qy, qz] (por unidad de
    largo) en toda la barra."""
    qx, qy, qz = q
    p = np.zeros(12)
    p[0] = p[6] = qx * L / 2
    p[1] = p[7] = qy * L / 2
    p[5], p[11] = qy * L ** 2 / 12, -qy * L ** 2 / 12
    p[2] = p[8] = qz * L / 2
    p[4], p[10] = -qz * L ** 2 / 12, qz * L ** 2 / 12
    return p


def empotramiento(L, cargas):
    """FEF (12, locales) de una lista de cargas locales: ("uniforme", [qx, qy, qz], None),
    ("puntual", [Px, Py, Pz], a) o ("momento", [Mx, My, Mz], a). FEF = −(cargas equivalentes)."""
    total = np.zeros(12)
    for tipo, vector, a in cargas:
        vector = np.asarray(vector, dtype=float)
        if tipo == "uniforme":
            total += equivalentes_uniforme(L, vector)
        elif tipo == "puntual":
            total += equivalentes_puntual(L, a, vector, np.zeros(3))
        elif tipo == "momento":
            total += equivalentes_puntual(L, a, np.zeros(3), vector)
        else:
            raise ValueError(f"Tipo de carga desconocido: {tipo}")
    return -total
