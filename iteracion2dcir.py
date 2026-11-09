"""Diagrama de interacción de columna circular: datos de ejemplo y gráficos.

El cálculo está en calculo/interaccion (cálculo sagrado). Aquí solo se imprime y se dibuja.
"""
import matplotlib.pyplot as plt
import numpy as np

from calculo.interaccion.circular import curva_circ, propiedades_circular
from calculo.interaccion.comun import ureg

# ---------- Datos de ejemplo ----------
D = 0.7335 * ureg.m
d = 7.5 * ureg.cm
nbarras = 16
nob = 8
fc = 4 * ureg.ksi


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
if __name__ == "__main__":
    sec = propiedades_circular(D, d, nbarras, fc, nob)
    mostrar_propiedades_circ(sec)
    graficar_diagrama_circ(sec)
