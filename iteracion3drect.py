import math
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
import numpy as np
import pint
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

ureg = pint.UnitRegistry()
ureg.define("tonne_force = 1000 * kilogram_force")

DIAM_ESPECIAL = {9: 1.128, 10: 1.270, 11: 1.410}
module_s = 29000 * ureg.ksi
KIP_TF = 0.45359237                  # kip -> tonne_force
KIPIN_TFM = 0.45359237 * 0.0254      # kip*in -> tonne_force*m

# ---------- Funciones base ----------
def area_barra(n, cantidad=1):
    diam = DIAM_ESPECIAL.get(n, n / 8) * ureg.inch
    return cantidad * math.pi * diam**2 / 4

def nb(nx, ny):
    return 2 * (nx + ny - 2)

def Ast(n, cantidad):
    return area_barra(n, cantidad)

def fy(n):
    return 60 * ureg.ksi if n >= 4 else 40 * ureg.ksi

def rho(Ast, b, h):
    return (Ast / (b * h)).to("dimensionless").magnitude * 100

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

def propiedades_seccion(b, h, d, nx, ny, fc, nob):
    if nx < 2 or ny < 2:
        raise ValueError("nx y ny deben ser al menos 2")
    if min(b, h) <= 2 * d:
        raise ValueError("b y h deben ser mayores que 2·d")
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
        if key in self.cache:
            return self.cache[key]
        sec = self.sec
        b = sec["b"].to("inch").magnitude
        h = sec["h"].to("inch").magnitude
        cth, sth = math.cos(th), math.sin(th)
        D = b * abs(cth) + h * abs(sth)
        cs = np.geomspace(0.001 * D, 3 * D, 100)
        Pn, Mn, PPn, PMn = [], [], [], []
        for ci in cs:
            _, P, Mx, My, phi_P, phi_Mx, phi_My = phipnmn_biaxial(ci, th, sec)
            Pn.append(P * KIP_TF)
            Mn.append((My * cth + Mx * sth) * KIPIN_TFM)
            PPn.append(phi_P * KIP_TF)
            PMn.append((phi_My * cth + phi_Mx * sth) * KIPIN_TFM)
        self.cache[key] = (Pn, Mn, PPn, PMn)
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
        sec = self.sec
        b = sec["b"].to("inch").magnitude
        h = sec["h"].to("inch").magnitude
        X, Y, Z = [], [], []
        for deg in range(0, 361, 10):
            th = math.radians(deg)
            D = b * abs(math.cos(th)) + h * abs(math.sin(th))
            cs = np.geomspace(0.001 * D, 3 * D, 60)
            r = [phipnmn_biaxial(c, th, sec) for c in cs]
            X.append([x[6] * KIPIN_TFM for x in r])   # φMy
            Y.append([x[5] * KIPIN_TFM for x in r])   # φMx
            Z.append([x[4] * KIP_TF for x in r])      # φPn

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