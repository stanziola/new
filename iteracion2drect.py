"""Diagrama de interacción de columna rectangular (flexión en un eje): datos de ejemplo y gráfico.

El cálculo está en calculo/interaccion (cálculo sagrado). Aquí solo se imprime y se dibuja.
"""
import matplotlib.pyplot as plt

from calculo.interaccion.comun import propiedades_seccion, ureg
from calculo.interaccion.rectangular import curva

# VARIABLES
b = 0.65 * ureg.m
h = 0.65 * ureg.m
c = 3.25 * ureg.cm
fc = 4 * ureg.ksi
nob = 8
nx = 5
ny = 5
d = 7.5 * ureg.cm


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
    Pn, Mn, PhiPn, PhiMn = curva(sec, n_puntos)

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


if __name__ == "__main__":
    sec = propiedades_seccion(b, h, d, nx, ny, fc, nob)
    graficar_diagrama(sec)
