import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

# graficas

# aspecto de las graficas: fondo negro y sin la barra de botones de arriba
ESTILO = "dark_background"
SIN_BOTONES = {"toolbar": "None"}


def graficar_c(seccion, c, b_cm, h_cm, m_rot):
    with plt.style.context(ESTILO), plt.rc_context(SIN_BOTONES):
        # --- figura y ejes ---
        fig, ax = plt.subplots()
        fig.subplots_adjust(bottom=0.25)                 # espacio para dos deslizadores

        linea, = ax.plot([], [], "w-")                    # la sección, en blanco
        lineas_c = [ax.axvline(0, color="orange", lw=0.8) for i in range(c.shape[1])]   # una por cada c
        linea_i = ax.axvline(0, color="r", lw=1.5)        # la c elegida

        r = np.hypot(b_cm, h_cm) / 2 * 1.1
        ax.set_xlim(c.min() * 1.05, r)                    # desde la c más lejana hasta la sección
        ax.set_ylim(-r, r)
        ax.set_aspect("equal")
        ax.grid(True, color="0.25")                       # rejilla gris oscuro, para que no compita

        # --- deslizadores ---
        n_ang, n_c = c.shape                             # filas = ángulos, columnas = valores de c
        desl_ang = Slider(fig.add_axes([0.15, 0.10, 0.7, 0.04]), "θ (°)", 0, n_ang - 1, valinit=0, valstep=1)
        desl_i   = Slider(fig.add_axes([0.15, 0.04, 0.7, 0.04]), "i", 0, n_c - 1, valinit=0, valstep=1)

    def actualizar(_=None):
        ang = int(desl_ang.val)
        i = int(desl_i.val)

        g = seccion @ m_rot(ang).T
        linea.set_data(g[:, 0], g[:, 1])

        for k, l in enumerate(lineas_c):              # mueve las líneas a los c de este ángulo
            l.set_xdata([c[ang, k], c[ang, k]])
        linea_i.set_xdata([c[ang, i], c[ang, i]])

        ax.set_title(f"θ = {ang}°, i = {i}, c = {c[ang, i]:.2f} cm")
        fig.canvas.draw_idle()

    desl_ang.on_changed(actualizar)
    desl_i.on_changed(actualizar)
    actualizar()
    plt.show()
