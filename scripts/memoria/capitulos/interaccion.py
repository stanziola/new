"""Capítulo 3: Diagrama de interacción de columnas (calculo/interaccion/).

Fórmulas y código. Las citas del ACI 318-19 se confirmaron en el PDF de docs/codigos/. Los números
de la figura del punto balanceado se calculan aquí (in, ksi, kip) solo para dibujarla.
"""
import math

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from calculo.interaccion import biaxial, circular, comun, rectangular
from calculo.interaccion.comun import ureg
from ejemplos.portico import crear_portico
from modelo import interaccion as puente

# Conversiones y constantes para los cálculos a mano
CM_IN = 1 / 2.54                     # pulgadas por centímetro
KSI_KN_M2 = 4.4482216152605 / 0.0254 ** 2    # kN/m² por ksi (1 kip = 4.4482216152605 kN; 1 in = 0.0254 m)
KIP_TONF = 0.45359237                # tonf (métrica) por kip
KIPIN_TONFM = 0.45359237 * 0.0254    # tonf·m por kip·in
ES = 29000.0                         # ksi (ACI 318-19 §20.2.2.2)
DIAMETROS = {3: 0.375, 4: 0.500, 5: 0.625, 6: 0.750, 7: 0.875, 8: 1.000, 9: 1.128, 10: 1.270, 11: 1.410}
GRIS, NEGRO = "#8c8c8c", "#000000"


def _area(n):
    """Área de una barra (in²) con su diámetro nominal (ACI 318-19, Apéndice B)."""
    return math.pi * DIAMETROS[n] ** 2 / 4


def _beta1(fc):
    """β1 de la Tabla 22.2.2.4.3, con f'c en ksi."""
    return 0.85 if fc <= 4 else 0.65 if fc >= 8 else 0.85 - 0.05 * (fc - 4)


def _phi(et, ey, espiral=False):
    """φ de la Tabla 21.2.2."""
    base, pendiente = (0.75, 0.15) if espiral else (0.65, 0.25)
    if et <= ey:
        return base
    return 0.90 if et >= ey + 0.003 else base + pendiente * (et - ey) / 0.003


def rectangular_a_mano(b, h, d, nx, ny, fc, fy, barra, c):
    """Columna rectangular con el eje neutro a c de la fibra comprimida, fila por fila (in, ksi, kip).
    Devuelve los totales y las filas, para mostrarlas en una tabla."""
    ey, ab = fy / ES, _area(barra)
    a = min(_beta1(fc) * c, h)
    cc = 0.85 * fc * b * a
    pn, mn, filas = cc, cc * (h / 2 - a / 2), []
    for i in range(ny):
        y = d + i * (h - 2 * d) / (ny - 1)
        n = nx if i in (0, ny - 1) else 2
        e = max(-ey, min(ey, 0.003 * (c - y) / c))
        f = e * ES - (0.85 * fc if y < a else 0.0)
        fuerza = f * n * ab
        pn += fuerza
        mn += fuerza * (h / 2 - y)
        filas.append((i + 1, y, n, e, f, fuerza, h / 2 - y, fuerza * (h / 2 - y)))
    et = 0.003 * (h - d - c) / c
    return {"a": a, "cc": cc, "brazo_cc": h / 2 - a / 2, "pn": pn, "mn": mn, "et": et, "phi": _phi(et, ey),
            "filas": filas}


def _columna_del_ejemplo():
    """La columna del pórtico de ejemplo (40×40 con 8 barras #6): su Concreto y el diccionario de
    propiedades que usa el cálculo, armado por el mismo puente que usa la interfaz."""
    modelo = crear_portico()
    concreto = next(s.concreto for s in modelo.secciones.values()
                    if s.concreto is not None and abs(s.concreto.b - s.concreto.h) < 1e-9)
    return concreto, puente.propiedades(concreto)


def _figura_seccion(dim, mano):
    """Esquema del cálculo: la sección, las deformaciones y las fuerzas, para el punto balanceado."""
    b, h, d, c = dim["b"], dim["h"], dim["d"], dim["c"]
    fig = Figure(figsize=(8.6, 3.4))
    FigureCanvasAgg(fig)
    seccion, deformacion, fuerzas = fig.subplots(1, 3, sharey=True, gridspec_kw={"width_ratios": [1.0, 1.15, 1.25]})
    # Sección (la fibra comprimida, arriba): el bloque de compresión sombreado y el eje neutro punteado
    seccion.plot([0, b, b, 0, 0], [0, 0, h, h, 0], color=NEGRO, linewidth=1.2)
    seccion.fill_between([0, b], h - mano["a"], h, color="#d9d9d9")
    xs = np.linspace(d, b - d, dim["nx"])
    for _i, y, n, *_resto in mano["filas"]:
        for x in (xs if n == dim["nx"] else (xs[0], xs[-1])):
            seccion.plot(x, h - y, "o", color=NEGRO, markersize=5)
    seccion.axhline(h - c, color=GRIS, linestyle="--", linewidth=0.9)
    # Los rótulos van donde no hay barras: el del bloque, en su parte baja; el del eje neutro, más abajo
    seccion.text(b / 2, h - mano["a"] + 1.1, f"bloque: a = {mano['a']:.2f} in", ha="center", va="center", fontsize=7)
    seccion.text(b / 2, h - c - 1.5, f"eje neutro: c = {c:.2f} in", ha="center", va="top", fontsize=7)
    seccion.set_title("Sección", fontsize=9)
    seccion.set_aspect("equal")
    seccion.set_ylabel("in", fontsize=8)
    # Deformaciones: 0.003 en la fibra comprimida y cero en el eje neutro; el valor de cada fila, al lado
    abajo = -0.003 * (h - c) / c
    deformacion.plot([0.003, abajo], [h, 0], color=NEGRO, linewidth=1.2)
    deformacion.plot([0, 0], [0, h], color=GRIS, linewidth=0.8)
    deformacion.plot([0, 0.003], [h, h], color=GRIS, linewidth=0.8)
    deformacion.axhline(h - c, color=GRIS, linestyle="--", linewidth=0.9)
    deformacion.text(0.003, h + 0.35, "0.003", ha="center", va="bottom", fontsize=7)
    for i, y, _n, e, *_resto in mano["filas"]:
        deformacion.plot([0, 0.003 * (c - y) / c], [h - y, h - y], color=GRIS, linewidth=0.8)
        deformacion.text(0.0036, h - y + 0.2, f"fila {i}: {e:+.6f}".replace("-", "−"), ha="left", va="bottom",
                         fontsize=7)
    deformacion.set_xlim(-0.0034, 0.0105)
    deformacion.set_title("Deformaciones (+ compresión)", fontsize=9)
    deformacion.set_xticks([])
    # Fuerzas: una flecha por fuerza, desde el eje; compresión (+) hacia la derecha y tracción hacia la izquierda
    escala = max(abs(mano["cc"]), *(abs(f[5]) for f in mano["filas"]))
    fuerzas.plot([0, 0], [0, h], color=GRIS, linewidth=0.8)
    for valor, y, texto in [(mano["cc"], mano["a"] / 2, "$C_c$")] + [(f[5], f[1], f"$F_{f[0]}$") for f in mano["filas"]]:
        sentido = 1 if valor >= 0 else -1
        punta = sentido * max(abs(valor) / escala, 0.06)        # una fuerza muy chica igual se ve
        fuerzas.annotate("", xy=(punta, h - y), xytext=(0, h - y),
                         arrowprops={"arrowstyle": "->", "color": NEGRO, "linewidth": 1.1})
        fuerzas.text(punta + 0.06 * sentido, h - y, f"{texto} = {valor:+.1f} kip".replace("-", "−"),
                     ha="left" if sentido > 0 else "right", va="center", fontsize=7)
    fuerzas.set_xlim(-2.3, 2.5)
    fuerzas.set_title("Fuerzas (+ compresión)", fontsize=9)
    fuerzas.set_xticks([])
    for eje in (seccion, deformacion, fuerzas):
        eje.tick_params(labelsize=7)
        for lado in ("top", "right", "bottom"):
            eje.spines[lado].set_visible(False)
    seccion.set_xticks([])
    fig.tight_layout()
    return fig


def _figura_diagrama(sec, puntos):
    """El diagrama de la columna del ejemplo: curva nominal, curva de diseño y los puntos marcados."""
    pn, mn, phi_pn, phi_mn = rectangular.curva(sec)
    fig = Figure(figsize=(6.4, 5.0))
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.plot(mn, pn, color=GRIS, linewidth=1.4, label="Nominal (Mn, Pn)")
    ax.plot(phi_mn, phi_pn, color=NEGRO, linewidth=1.6, label="Diseño (φMn, φPn)")
    for nombre, (x, y), desplazamiento, lado in puntos:
        ax.plot(x, y, "o", color=NEGRO, markersize=5)
        ax.annotate(nombre, (x, y), textcoords="offset points", xytext=desplazamiento, fontsize=7.5, ha=lado)
    ax.set_xlim(right=1.32 * float(np.max(mn)))            # lugar para los rótulos de la derecha
    ax.axhline(0, color=NEGRO, linewidth=0.7)
    ax.axvline(0, color=NEGRO, linewidth=0.7)
    ax.set_xlabel("M (tonf·m)", fontsize=9)
    ax.set_ylabel("P (tonf)", fontsize=9)
    ax.grid(True, alpha=0.35)
    ax.legend(fontsize=8)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    return fig


def capitulo(m):
    m.titulo("Diagrama de interacción")
    m.parrafo("Curva de las parejas (momento, carga axial) que agotan la sección: nominal ($M_n$, $P_n$) y de "
              "diseño ($\\phi M_n$, $\\phi P_n$), para columnas rectangulares (un eje y biaxial) y circulares. "
              "ACI 318-19. Código: `calculo/interaccion/`, en pulgadas, ksi y kip; los resultados salen en tonf "
              "y tonf·m.")

    # ------------------------------------------------------------------ Hipótesis
    m.titulo("Hipótesis", 2)
    m.tabla(["Hipótesis", "ACI 318-19"], [
        ["Equilibrio; deformaciones proporcionales a la distancia al eje neutro.", "§22.2.1.1 y §22.2.1.2 (PDF p. 399)"],
        ["Deformación máxima del concreto: 0.003.", "§22.2.2.1 (PDF p. 400)"],
        ["Se desprecia la tracción del concreto.", "§22.2.2.2 (PDF p. 400)"],
        [r"Bloque rectangular $0.85 f'_c$ de profundidad $a = \beta_1 c$.", "§22.2.2.4.1 (PDF p. 400)"],
        [r"Acero elastoplástico, $E_s$ = 29 000 ksi.", "§20.2.2.1 y §20.2.2.2 (PDF p. 375–376)"],
    ], anchos_cm=[10.2, 5.7])
    m.parrafo("$c$: profundidad del eje neutro desde la fibra más comprimida. Compresión positiva.")

    # ------------------------------------------------------------------ Propiedades
    m.titulo("Propiedades de la sección", 2)
    m.ecuacion(r"A_b = \frac{\pi \, d_b^2}{4}, \quad n_b = 2 \left( n_x + n_y - 2 \right), \quad A_{st} = n_b \, A_b, "
               r"\quad \rho = \frac{A_{st}}{b \, h}",
               cita="$d_b$: diámetro nominal (ACI 318-19, Apéndice B, PDF p. 583)")
    m.ecuacion(r"\beta_1 = \begin{cases} 0.85 & 2.5 < f'_c \le 4 \text{ ksi} \\ "
               r"1.05 - 0.05 \, f'_c & 4 < f'_c < 8 \text{ ksi} \\ 0.65 & f'_c \ge 8 \text{ ksi} \end{cases}",
               cita="ACI 318-19, Tabla 22.2.2.4.3 (PDF p. 401)")
    m.ecuacion(r"\varepsilon_y = \frac{f_y}{E_s}", cita="ACI 318-19 §21.2.2.1 (PDF p. 394)")
    m.codigo(comun.beta1)
    m.codigo(comun.fy)
    m.codigo(comun.propiedades_seccion)

    # ------------------------------------------------------------------ Rectangular
    m.titulo("Columna rectangular con flexión en un eje", 2)
    m.ecuacion(r"a = \text{mín} \left( \beta_1 c, \; h \right), \quad C_c = 0.85 \, f'_c \, b \, a",
               cita="ACI 318-19 §22.2.2.4.1 (PDF p. 400)")
    m.ecuacion(r"y_i = d + i \, \frac{h - 2d}{n_y - 1}, \quad "
               r"\varepsilon_{si} = 0.003 \, \frac{c - y_i}{c}, \quad -\varepsilon_y \le \varepsilon_{si} \le \varepsilon_y")
    m.ecuacion(r"f_{si} = E_s \, \varepsilon_{si} - 0.85 \, f'_c \;\; \text{(si } y_i < a \text{)}, \quad "
               r"F_i = f_{si} \, n_i \, A_b")
    m.ecuacion(r"P_n = C_c + \sum_i F_i, \quad "
               r"M_n = C_c \left( \frac{h}{2} - \frac{a}{2} \right) + \sum_i F_i \left( \frac{h}{2} - y_i \right)")
    m.parrafo("$n_i$: barras de la fila $i$ ($n_x$ en las extremas, 2 en las intermedias). La curva recorre 100 "
              "valores de $c$, de $0.001 h$ a $3 h$, en progresión geométrica.")

    concreto, sec = _columna_del_ejemplo()
    b, h, d = concreto.b * 100 * CM_IN, concreto.h * 100 * CM_IN, concreto.d * 100 * CM_IN
    fc, fy = concreto.fc / KSI_KN_M2, 60.0
    cb = 0.003 * (h - d) / (0.003 + fy / ES)
    mano = rectangular_a_mano(b, h, d, concreto.nx, concreto.ny, fc, fy, concreto.barra, cb)
    m.figura(_figura_seccion({"b": b, "h": h, "d": d, "c": cb, "nx": concreto.nx}, mano),
             "Cómo se calcula un punto: sección, deformaciones y fuerzas (columna del ejemplo, 40 × 40 cm, "
             "8 #6, punto balanceado).", ancho_cm=15.5)
    m.codigo(rectangular.phipnmn)
    m.codigo(rectangular.curva)

    # ------------------------------------------------------------------ φ y Pn,max
    m.titulo("Factor φ y resistencia axial máxima", 2)
    m.ecuacion(r"\varepsilon_t = 0.003 \, \frac{d_t - c}{c}")
    m.tabla([r"$\varepsilon_t$", r"$\phi$ con estribos", r"$\phi$ con espiral"], [
        [r"$\varepsilon_t \le \varepsilon_{ty}$", "0.65", "0.75"],
        [r"$\varepsilon_{ty} < \varepsilon_t < \varepsilon_{ty} + 0.003$",
         r"$0.65 + 0.25 \, \frac{\varepsilon_t - \varepsilon_{ty}}{0.003}$",
         r"$0.75 + 0.15 \, \frac{\varepsilon_t - \varepsilon_{ty}}{0.003}$"],
        [r"$\varepsilon_t \ge \varepsilon_{ty} + 0.003$", "0.90", "0.90"],
    ], anchos_cm=[5.3, 5.3, 5.3], centrar=(0, 1, 2))
    m.parrafo("ACI 318-19, Tabla 21.2.2 (PDF p. 395).").style = "Cita"
    m.ecuacion(r"P_o = 0.85 \, f'_c \left( A_g - A_{st} \right) + f_y \, A_{st}",
               cita="ACI 318-19 Ec. 22.4.2.2 (PDF p. 402)")
    m.ecuacion(r"\phi P_n \le 0.65 \cdot 0.80 \, P_o \;\; \text{(estribos)}, \quad "
               r"\phi P_n \le 0.75 \cdot 0.85 \, P_o \;\; \text{(espiral)}",
               cita="ACI 318-19 Tabla 22.4.2.1 (PDF p. 402)")
    _phi, pn_fin, _mn, _ppn, _pmn = rectangular.phipnmn(3 * h * ureg.inch, sec)
    po = pn_fin.magnitude
    m.figura(_figura_diagrama(sec, [
        ("Po", (0.0, po), (8, -1), "left"),
        ("Techo de diseño: 0.65 · 0.80 · Po", (0.0, 0.52 * po), (8, 5), "left"),
    ]), "Diagrama de interacción de la columna del ejemplo (flexión en un eje).")

    # ------------------------------------------------------------------ Biaxial
    m.titulo("Columna rectangular con flexión biaxial", 2)
    m.parrafo("$\\theta$: dirección hacia la fibra más comprimida (0° = compresión hacia $+x$, a lo largo de "
              "$b$; 90° = hacia $+y$, a lo largo de $h$). Origen en el centro de la sección.")
    m.ecuacion(r"t_{max} = \frac{b}{2} \left| \cos\theta \right| + \frac{h}{2} \left| \text{sen}\,\theta \right|, "
               r"\quad a = \text{mín} \left( \beta_1 c, \; 2 t_{max} \right)")
    m.parrafo("El bloque comprimido es el polígono del rectángulo con $t \\le a$; su área y su centroide:")
    m.ecuacion(r"A = \frac{1}{2} \sum_i \left( x_i \, y_{i+1} - x_{i+1} \, y_i \right), \quad "
               r"\bar{x} = \frac{1}{6A} \sum_i \left( x_i + x_{i+1} \right) \left( x_i \, y_{i+1} - x_{i+1} \, y_i \right)")
    m.ecuacion(r"t_k = t_{max} - \left( x_k \cos\theta + y_k \, \text{sen}\,\theta \right), \quad "
               r"\varepsilon_k = 0.003 \, \frac{c - t_k}{c}")
    m.ecuacion(r"C_c = 0.85 f'_c A, \quad P_n = C_c + \sum_k F_k, \quad M_x = C_c \, \bar{y} + \sum_k F_k \, y_k, \quad "
               r"M_y = C_c \, \bar{x} + \sum_k F_k \, x_k")
    m.ecuacion(r"M_n = M_y \cos\theta + M_x \, \text{sen}\,\theta",
               cita="Superficie: la curva cada 10°, con 60 valores de $c$")
    m.codigo(biaxial.phipnmn_biaxial)
    m.codigo(biaxial.curva)

    # ------------------------------------------------------------------ Circular
    m.titulo("Columna circular", 2)
    m.parrafo("Diámetro $D$ (radio $R$), $n$ barras en un círculo de radio $R_s = R - d$. Siempre con espiral.")
    m.ecuacion(r"a = \text{mín} \left( \beta_1 c, \; D \right), \quad \alpha = \arccos \left( \frac{R - a}{R} \right)")
    m.ecuacion(r"A = R^2 \left( \alpha - \text{sen}\,\alpha \, \cos\alpha \right), \quad "
               r"\bar{y} = \frac{4 R \, \text{sen}^3 \alpha}{3 \left( 2\alpha - \text{sen}\,2\alpha \right)}")
    m.ecuacion(r"\text{brazo}_k = R_s \cos \left( \frac{2 \pi k}{n} \right), \quad t_k = R - \text{brazo}_k")
    m.ecuacion(r"P_n = C_c + \sum_k F_k, \quad M_n = C_c \, \bar{y} + \sum_k F_k \, \text{brazo}_k")
    m.codigo(circular.phipnmn_circ)

    # ------------------------------------------------------------------ Limitaciones
    m.titulo("Limitaciones y hallazgos pendientes", 2)
    m.lista([
        "$\\beta_1$: rechaza $f'_c$ = 2.5 ksi, que la Tabla 22.2.2.4.3 sí incluye.",
        "Barras #14 y #18: diámetro como $n/8$ in; los nominales son 1.693 y 2.257 in.",
        "Área de barra $\\pi d_b^2/4$, no la nominal del Apéndice B (diferencia < 1 %).",
        "$f_y$: 40 ksi en la #3 y 60 ksi en las demás (supuesto del programa).",
        "Cuantía sin límite: $0.01 A_g \\le A_{st} \\le 0.08 A_g$ (§10.6.1.1) y $0.06 A_g$ en pórticos "
        "especiales (§18.7.4.1).",
        "Circular siempre con espiral; con aros correspondería 0.65 y $0.80 P_o$.",
        "Todavía sin los puntos $P_u$–$M_u$ ni esbeltez (etapa 4).",
    ])
