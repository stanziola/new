"""Diagrama de interacción de columna rectangular biaxial: ventana tkinter con la sección y el diagrama.

El cálculo está en calculo/interaccion (cálculo sagrado). Aquí solo la ventana y los gráficos.
"""
import math
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from calculo.interaccion.biaxial import _barras, curva, superficie
from calculo.interaccion.comun import propiedades_seccion, ureg


# ---------- Interfaz ----------
class App:
    CAMPOS = [("b (cm)", "65"), ("h (cm)", "65"), ("d (cm)", "7.5"),
              ("f'c (ksi)", "4"), ("Barra # (nob)", "8"),
              ("nx (barras arriba/abajo)", "5"), ("ny (filas)", "5")]

    def __init__(self, root):
        self.root = root
        root.title("Diagrama de interacción - columna rectangular")
        self.sec = None
        self.cache = {}

        panel = ttk.Frame(root, padding=8)
        panel.pack(side="left", fill="y")

        self.vars = []
        for i, (nombre, val) in enumerate(self.CAMPOS):
            ttk.Label(panel, text=nombre).grid(row=i, column=0, sticky="w", pady=2)
            v = tk.StringVar(value=val)
            e = ttk.Entry(panel, textvariable=v, width=8)
            e.grid(row=i, column=1, pady=2)
            e.bind("<Return>", lambda ev: self.actualizar())
            self.vars.append(v)

        ttk.Button(panel, text="Actualizar sección", command=self.actualizar)\
            .grid(row=len(self.CAMPOS), column=0, columnspan=2, pady=8, sticky="ew")

        ttk.Button(panel, text="Ver 3D", command=self.ver_3d)\
            .grid(row=len(self.CAMPOS) + 1, column=0, columnspan=2, pady=4, sticky="ew")

        # Ángulo: casilla + slider sincronizados
        self.ang_txt = tk.StringVar(value="0")
        ttk.Label(panel, text="Ángulo θ (°)").grid(row=20, column=0, sticky="w")
        e_ang = ttk.Entry(panel, textvariable=self.ang_txt, width=8)
        e_ang.grid(row=20, column=1, pady=2)
        e_ang.bind("<Return>", lambda ev: self.desde_casilla())
        e_ang.bind("<FocusOut>", lambda ev: self.desde_casilla())

        self.ang_scale = tk.Scale(panel, from_=0, to=360, resolution=1, orient="horizontal",
                                  length=220, command=self.desde_slider)
        self.ang_scale.grid(row=21, column=0, columnspan=2)

        self.info = tk.StringVar()
        ttk.Label(panel, textvariable=self.info, justify="left",
                  font=("Consolas", 9)).grid(row=22, column=0, columnspan=2, pady=10, sticky="w")

        self.fig = Figure(figsize=(12, 6))
        self.ax1 = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(side="right", fill="both", expand=True)

        self.actualizar()

    def angulo(self):
        try:
            return float(self.ang_txt.get()) % 360
        except ValueError:
            return None

    def desde_slider(self, v):
        self.ang_txt.set(f"{float(v):g}")
        self.dibujar()

    def desde_casilla(self):
        a = self.angulo()
        if a is None:
            messagebox.showerror("Ángulo inválido", "Escribe un número en grados.")
            return
        self.ang_scale.set(a)
        self.ang_txt.set(f"{a:g}")
        self.dibujar()

    def actualizar(self):
        try:
            b, h, d, fc, nob, nx, ny = [float(v.get()) for v in self.vars]
            self.sec = propiedades_seccion(
                b * ureg.cm, h * ureg.cm, d * ureg.cm, int(nx), int(ny),
                fc * ureg.ksi, int(nob))
        except Exception as e:
            messagebox.showerror("Datos inválidos", str(e))
            return
        self.cache.clear()
        self.dibujar()

    def curva(self, th):
        key = round(th, 6)
        if key not in self.cache:
            self.cache[key] = curva(self.sec, th)
        return self.cache[key]

    def dibujar(self):
        ang = self.angulo()
        if self.sec is None or ang is None:
            return
        sec = self.sec
        th = math.radians(ang)
        u = np.array([math.cos(th), math.sin(th)])

        b = sec["b"].to("inch").magnitude
        h = sec["h"].to("inch").magnitude
        d = sec["d"].to("inch").magnitude
        tmax = (b / 2) * abs(u[0]) + (h / 2) * abs(u[1])
        k = 2.54                                          # in -> cm

        # --- Sección ---
        ax = self.ax1
        ax.clear()
        rect = np.array([[-b/2, -h/2], [b/2, -h/2], [b/2, h/2], [-b/2, h/2]])
        ax.add_patch(Polygon(rect * k, fill=False, edgecolor="k", linewidth=2))
        bars = _barras(b, h, d, sec["nx"], sec["ny"])
        ax.scatter(bars[:, 0] * k, bars[:, 1] * k, c="tab:blue", s=70,
                   zorder=3, edgecolors="k")
        ax.annotate("", xy=u * tmax * k * 1.25, xytext=u * tmax * k * 0.6,
                    arrowprops=dict(arrowstyle="->", color="green", lw=2))
        ax.text(*(u * tmax * k * 1.3), "compresión", color="green", ha="center")

        lim = 0.8 * max(b, h) * k
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal")
        ax.set_title(f"Sección (θ = {ang:g}°)")
        ax.set_xlabel("x (cm)")
        ax.set_ylabel("y (cm)")
        ax.grid(True, alpha=0.3)

        # --- Diagrama 2D ---
        Pn, Mn, PPn, PMn = self.curva(th)
        ax = self.ax2
        ax.clear()
        ax.plot(Mn, Pn, color="lightskyblue", label="Nominal (Mn, Pn)")
        ax.plot(PMn, PPn, color="gray", label="Diseño (φMn, φPn)")
        ax.axhline(0, color="k", linewidth=0.8)
        ax.axvline(0, color="k", linewidth=0.8)
        ax.set_xlabel("M (ton·m)")
        ax.set_ylabel("P (ton)")
        ax.set_title(f"Diagrama de interacción - θ = {ang:g}°")
        ax.grid(True)
        ax.legend()

        self.info.set(
            f"Cuantía = {sec['cuantia']:.2f}%\n"
            f"Barras  = {sec['nbarras']}\n"
            f"As      = {sec['As_total'].magnitude:.1f} cm²")
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def ver_3d(self):
        if self.sec is None:
            return
        X, Y, Z = superficie(self.sec)

        win = tk.Toplevel(self.root)
        win.title("Superficie de interacción 3D")
        fig = Figure(figsize=(8, 7))
        ax = fig.add_subplot(111, projection="3d")
        ax.plot_surface(np.array(X), np.array(Y), np.array(Z),
                        cmap="viridis", alpha=0.85, linewidth=0)
        ax.set_xlabel("φMy (ton·m)")
        ax.set_ylabel("φMx (ton·m)")
        ax.set_zlabel("φPn (ton)")
        ax.set_title("Superficie de interacción de diseño")
        canvas = FigureCanvasTkAgg(fig, master=win)
        NavigationToolbar2Tk(canvas, win)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
