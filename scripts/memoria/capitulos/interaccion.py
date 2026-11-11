"""Capítulo 3: Diagrama de interacción de columnas (calculo/interaccion/).

Las citas del ACI 318-19 se confirmaron en el PDF de docs/codigos/ (páginas 160, 308, 375, 376, 394,
395, 399 a 402 y 583). Las verificaciones "a mano" se calculan aquí con números sueltos, en pulgadas,
ksi y kip, sin usar calculo/ ni pint: son otro camino para llegar al mismo resultado.
"""
import math

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from calculo.interaccion import biaxial, circular, comun, rectangular
from calculo.interaccion.comun import ureg
from ejemplos.portico import crear_portico
from modelo import interaccion as puente
from scripts.memoria.documento import numero

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


def circular_a_mano(diametro, d, nbarras, fc, fy, barra):
    """Columna circular con el bloque de compresión hasta el centro (a = R): el concreto comprimido es
    medio círculo, de área πR²/2 y centroide a 4R/3π del centro (in, ksi, kip)."""
    radio, ey, ab = diametro / 2, fy / ES, _area(barra)
    rs = radio - d
    c = radio / _beta1(fc)
    cc = 0.85 * fc * math.pi * radio ** 2 / 2
    pn, mn, mayor = cc, cc * 4 * radio / (3 * math.pi), 0.0
    for k in range(nbarras):
        brazo = rs * math.cos(2 * math.pi * k / nbarras)
        t = radio - brazo
        e = max(-ey, min(ey, 0.003 * (c - t) / c))
        f = e * ES - (0.85 * fc if t < radio else 0.0)
        pn += f * ab
        mn += f * ab * brazo
        mayor = max(mayor, t)
    et = 0.003 * (mayor - c) / c
    ast = nbarras * ab
    po = 0.85 * fc * (math.pi * radio ** 2 - ast) + fy * ast
    return {"c": c, "pn": pn, "mn": mn, "phi": _phi(et, ey, espiral=True), "po": po}


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
    """El diagrama de la columna del ejemplo: curva nominal, curva de diseño y los puntos comprobados."""
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
    m.parrafo("Una columna resiste a la vez carga axial y momento. El **diagrama de interacción** es la curva "
              "de todas las parejas (momento, carga axial) que agotan la sección: un punto dentro de la curva "
              "resiste; uno fuera, no. El programa calcula la curva **nominal** ($M_n$, $P_n$) y la de "
              "**diseño** ($\\phi M_n$, $\\phi P_n$) de tres secciones: rectangular con flexión en un eje, "
              "rectangular con flexión biaxial y circular. Todo está en `calculo/interaccion/` y sigue el "
              "ACI 318-19.")
    m.parrafo("Las fórmulas trabajan en **pulgadas, ksi y kip**. Los resultados salen en tonf y tonf·m, y el "
              "programa los pasa a kN y kN·m para mostrarlos.")

    # ------------------------------------------------------------------ Hipótesis
    m.titulo("Hipótesis", 2)
    m.tabla(["Hipótesis", "ACI 318-19"], [
        ["Hay equilibrio en la sección, y las deformaciones del concreto y del acero son proporcionales a la "
         "distancia al eje neutro (las secciones siguen planas).", "§22.2.1.1 y §22.2.1.2 (PDF p. 399)"],
        ["La deformación máxima del concreto en la fibra más comprimida es 0.003.", "§22.2.2.1 (PDF p. 400)"],
        ["La resistencia del concreto a tracción se desprecia.", "§22.2.2.2 (PDF p. 400)"],
        [r"El concreto comprimido se reemplaza por un bloque rectangular de esfuerzo $0.85 f'_c$ y "
         r"profundidad $a = \beta_1 c$, medida desde la fibra más comprimida.", "§22.2.2.4.1 (PDF p. 400)"],
        [r"$\beta_1$ depende de $f'_c$.", "Tabla 22.2.2.4.3 (PDF p. 401)"],
        [r"El acero es elastoplástico: $f_s = E_s \varepsilon_s$ hasta $f_y$ y, después, $f_s = f_y$.",
         "§20.2.2.1 (PDF p. 375)"],
        [r"$E_s$ = 29 000 000 psi (29 000 ksi).", "§20.2.2.2 (PDF p. 376)"],
    ], anchos_cm=[11.2, 4.7])
    m.parrafo("En todo el capítulo, $c$ es la profundidad del eje neutro, medida desde la fibra más comprimida, "
              "y las deformaciones y fuerzas de **compresión son positivas**.")

    # ------------------------------------------------------------------ Propiedades
    m.titulo("Datos de la sección y propiedades", 2)
    m.parrafo("La sección rectangular se define con su ancho $b$ y su alto $h$, la distancia $d$ del borde al "
              "centro de las barras, el número de barra, $n_x$ (barras en cada una de las dos caras extremas) y "
              "$n_y$ (filas de barras). Las filas intermedias llevan dos barras, una en cada costado. De ahí "
              "salen:")
    m.ecuacion(r"A_b = \frac{\pi \, d_b^2}{4}", cita="Área de una barra, con su diámetro nominal $d_b$: `area_barra`")
    m.parrafo("El diámetro nominal es el número de la barra en octavos de pulgada, salvo en las barras #9, #10 "
              "y #11, que miden 1.128, 1.270 y 1.410 in (ACI 318-19, Apéndice B, PDF p. 583).")
    m.ecuacion(r"n_b = 2 \left( n_x + n_y - 2 \right)", cita="Cantidad de barras de la sección rectangular: `nb`")
    m.ecuacion(r"A_{st} = n_b \, A_b, \quad \rho = \frac{A_{st}}{b \, h}", cita="Acero total y cuantía: `Ast` y `rho`")
    m.ecuacion(r"\beta_1 = \begin{cases} 0.85 & 2.5 < f'_c \le 4 \text{ ksi} \\ "
               r"1.05 - 0.05 \, f'_c & 4 < f'_c < 8 \text{ ksi} \\ 0.65 & f'_c \ge 8 \text{ ksi} \end{cases}",
               cita="ACI 318-19, Tabla 22.2.2.4.3 (PDF p. 401), con $f'_c$ en ksi: `beta1`")
    m.parrafo("La tabla del ACI da el tramo del medio como $0.85 - 0.05 (f'_c - 4000) / 1000$, con $f'_c$ en "
              "psi; es la misma recta.")
    m.ecuacion(r"\varepsilon_y = \frac{f_y}{E_s}", cita="Deformación de fluencia (la $\\varepsilon_{ty}$ del "
               "ACI 318-19 §21.2.2.1, PDF p. 394)")
    m.parrafo("El programa toma $f_y$ = 60 ksi para las barras #4 y mayores y 40 ksi para la #3. Es un supuesto "
              "del programa, no una regla de la norma (ver las limitaciones al final del capítulo).")
    m.codigo(comun)

    # ------------------------------------------------------------------ Rectangular
    m.titulo("Columna rectangular con flexión en un eje", 2)
    m.parrafo("Para una profundidad $c$ del eje neutro, la resistencia sale de sumar la fuerza del concreto y "
              "la de cada fila de barras. La flexión es en la dirección de $h$: la fibra comprimida es una cara "
              "de ancho $b$.")
    m.titulo("Concreto", 3)
    m.ecuacion(r"a = \text{mín} \left( \beta_1 c, \; h \right)")
    m.ecuacion(r"C_c = 0.85 \, f'_c \, b \, a", cita="ACI 318-19 §22.2.2.4.1 (PDF p. 400)")
    m.parrafo("$C_c$ actúa en el centro del bloque, a $a/2$ de la fibra comprimida. El bloque no puede ser más "
              "alto que la sección: por eso $a$ se limita a $h$.")
    m.titulo("Acero, fila por fila", 3)
    m.parrafo("La fila $i$ está a $y_i$ de la fibra comprimida y tiene $n_i$ barras:")
    m.ecuacion(r"y_i = d + i \, \frac{h - 2d}{n_y - 1}, \quad i = 0, 1, \ldots, n_y - 1")
    m.ecuacion(r"\varepsilon_{si} = 0.003 \, \frac{c - y_i}{c}, \quad -\varepsilon_y \le \varepsilon_{si} \le \varepsilon_y",
               cita="Deformación lineal (§22.2.1.2), limitada a la fluencia (§20.2.2.1)")
    m.ecuacion(r"f_{si} = E_s \, \varepsilon_{si} - 0.85 \, f'_c \;\; \text{(si } y_i < a \text{)}")
    m.ecuacion(r"F_i = f_{si} \, n_i \, A_b")
    m.parrafo("Limitar la deformación a $\\pm \\varepsilon_y$ equivale a limitar el esfuerzo a $\\pm f_y$. A las "
              "barras que quedan dentro del bloque de compresión se les resta $0.85 f'_c$, porque ocupan un "
              "lugar donde $C_c$ ya contó concreto.")
    m.titulo("Resistencia nominal", 3)
    m.ecuacion(r"P_n = C_c + \sum_i F_i")
    m.ecuacion(r"M_n = C_c \left( \frac{h}{2} - \frac{a}{2} \right) + \sum_i F_i \left( \frac{h}{2} - y_i \right)",
               cita="Momentos respecto del centro de la sección: `rectangular.phipnmn`")

    # ------------------------------------------------------------------ φ y Pn,max
    m.titulo("Factor de reducción de resistencia", 2)
    m.parrafo("El factor $\\phi$ depende de cuánto se estira el acero más traccionado cuando el concreto llega "
              "a 0.003. Esa deformación es $\\varepsilon_t$, con $d_t$ la distancia de la fibra comprimida a la "
              "fila más traccionada ($d_t = h - d$ en la rectangular):")
    m.ecuacion(r"\varepsilon_t = 0.003 \, \frac{d_t - c}{c}")
    m.tabla([r"Deformación $\varepsilon_t$", "Clasificación", r"$\phi$ con estribos", r"$\phi$ con espiral"], [
        [r"$\varepsilon_t \le \varepsilon_{ty}$", "Controlada por compresión", "0.65", "0.75"],
        [r"$\varepsilon_{ty} < \varepsilon_t < \varepsilon_{ty} + 0.003$", "Transición",
         r"$0.65 + 0.25 \, \frac{\varepsilon_t - \varepsilon_{ty}}{0.003}$",
         r"$0.75 + 0.15 \, \frac{\varepsilon_t - \varepsilon_{ty}}{0.003}$"],
        [r"$\varepsilon_t \ge \varepsilon_{ty} + 0.003$", "Controlada por tracción", "0.90", "0.90"],
    ], anchos_cm=[4.2, 4.3, 3.7, 3.7], centrar=(0, 2, 3))
    m.parrafo("ACI 318-19, Tabla 21.2.2 (PDF p. 395), con $\\varepsilon_{ty} = f_y / E_s$ (§21.2.2.1, PDF p. "
              "394).").style = "Cita"
    m.parrafo("Las columnas rectangulares usan la columna «con estribos»; la circular, la de «con espiral».")

    m.titulo("Resistencia axial máxima", 2)
    m.parrafo("La resistencia a compresión se recorta, para cubrir la excentricidad accidental:")
    m.ecuacion(r"P_o = 0.85 \, f'_c \left( A_g - A_{st} \right) + f_y \, A_{st}",
               cita="ACI 318-19 §22.4.2.2, Ec. 22.4.2.2 (PDF p. 402)")
    m.ecuacion(r"P_{n,max} = 0.80 \, P_o \;\; \text{(estribos)}, \quad P_{n,max} = 0.85 \, P_o \;\; \text{(espiral)}",
               cita="ACI 318-19 §22.4.2.1, Tabla 22.4.2.1 (PDF p. 402)")
    m.parrafo("En el diagrama de diseño, eso es un techo horizontal:")
    m.ecuacion(r"\phi P_n = \text{mín} \left( \phi \, P_n, \;\; 0.65 \cdot 0.80 \, P_o \right) \;\; \text{(estribos)}")
    m.ecuacion(r"\phi P_n = \text{mín} \left( \phi \, P_n, \;\; 0.75 \cdot 0.85 \, P_o \right) \;\; \text{(espiral)}")
    m.codigo(rectangular)

    # ------------------------------------------------------------------ Curva
    m.titulo("Cómo se arma la curva", 2)
    m.parrafo("Cada valor de $c$ da un punto ($M_n$, $P_n$). El programa recorre 100 valores de $c$, de "
              "$0.001 h$ a $3 h$, repartidos en progresión geométrica (más juntos donde $c$ es chico, que es "
              "donde la curva cambia más rápido). Con $c$ muy chico casi toda la sección está en tracción; con "
              "$c = 3h$ todo el concreto está comprimido y todo el acero fluye en compresión: $P_n = P_o$.")
    m.parrafo("Conversiones de salida: 1 kip = 0.45359237 tonf y 1 kip·in = 0.45359237 × 0.0254 tonf·m "
              "(1 lb = 0.45359237 kg y 1 in = 0.0254 m, exactos).")

    # ------------------------------------------------------------------ Biaxial
    m.titulo("Columna rectangular con flexión biaxial", 2)
    m.parrafo("Cuando el momento no va en la dirección de un lado, el eje neutro queda inclinado. El programa "
              "lo maneja con un ángulo $\\theta$: la **dirección hacia la fibra más comprimida**, en el plano de "
              "la sección. Los ejes de la sección tienen el origen en su centro, con $x$ a lo largo de $b$ e "
              "$y$ a lo largo de $h$.")
    m.ecuacion(r"u = \left( \cos\theta, \; \text{sen}\,\theta \right)")
    m.lista([
        "$\\theta$ = 0°: la compresión va hacia $+x$. La flexión es en la dirección de $b$.",
        "$\\theta$ = 90°: la compresión va hacia $+y$. Es la flexión en un eje de la sección anterior.",
        "Cualquier otro ángulo: flexión biaxial.",
    ])
    m.parrafo("La distancia de un punto $p = (x, y)$ a la fibra más comprimida, medida a lo largo de $u$, es:")
    m.ecuacion(r"t(p) = t_{max} - p \cdot u, \quad t_{max} = \frac{b}{2} \left| \cos\theta \right| + "
               r"\frac{h}{2} \left| \text{sen}\,\theta \right|")
    m.parrafo("$2 t_{max}$ es el alto de la sección en la dirección $u$. El bloque de compresión llega hasta "
              "$a = \\text{mín}(\\beta_1 c, 2 t_{max})$ y es la parte del rectángulo con $t \\le a$: un "
              "**polígono** (triángulo, trapecio o pentágono) que el programa obtiene recortando el rectángulo "
              "con la recta $p \\cdot u = t_{max} - a$ (`_recortar`). Su área y su centroide salen de sus "
              "vértices ($x_i$, $y_i$), recorridos en orden:")
    m.ecuacion(r"A = \frac{1}{2} \sum_i \left( x_i \, y_{i+1} - x_{i+1} \, y_i \right)")
    m.ecuacion(r"\bar{x} = \frac{1}{6A} \sum_i \left( x_i + x_{i+1} \right) \left( x_i \, y_{i+1} - x_{i+1} \, y_i \right), "
               r"\quad \bar{y} = \frac{1}{6A} \sum_i \left( y_i + y_{i+1} \right) \left( x_i \, y_{i+1} - x_{i+1} \, y_i \right)",
               cita="Área y centroide de un polígono: `_area_centroide`")
    m.parrafo("Con eso, el concreto y cada barra $k$, que está en ($x_k$, $y_k$), dan:")
    m.ecuacion(r"C_c = 0.85 \, f'_c \, A")
    m.ecuacion(r"t_k = t_{max} - \left( x_k \cos\theta + y_k \, \text{sen}\,\theta \right), \quad "
               r"\varepsilon_k = 0.003 \, \frac{c - t_k}{c}, \quad F_k = f_k \, A_b")
    m.ecuacion(r"P_n = C_c + \sum_k F_k, \quad M_x = C_c \, \bar{y} + \sum_k F_k \, y_k, \quad "
               r"M_y = C_c \, \bar{x} + \sum_k F_k \, x_k", cita="`biaxial.phipnmn_biaxial`")
    m.parrafo("El esfuerzo $f_k$ sale de $\\varepsilon_k$ igual que en la sección anterior (límite de fluencia y "
              "descuento de $0.85 f'_c$ si $t_k < a$). $M_x$ es el momento de las fuerzas por su distancia "
              "$y$, y $M_y$ por su distancia $x$. $\\phi$ sale de la barra más alejada de la fibra comprimida, "
              "con la columna «con estribos» de la tabla, y $\\phi P_n$ lleva el mismo techo.")
    m.parrafo("El diagrama en la dirección $\\theta$ usa el momento en esa dirección, y la **superficie** de "
              "interacción se arma repitiendo la curva cada 10°, de 0° a 360°, con 60 valores de $c$ en cada "
              "una:")
    m.ecuacion(r"M_n = M_y \cos\theta + M_x \, \text{sen}\,\theta", cita="`biaxial.curva` y `biaxial.superficie`")
    m.codigo(biaxial)

    # ------------------------------------------------------------------ Circular
    m.titulo("Columna circular", 2)
    m.parrafo("La columna circular tiene diámetro $D$ (radio $R$) y $n$ barras repartidas por igual en un "
              "círculo de radio $R_s = R - d$, con la primera en la fibra más comprimida. Como es simétrica, "
              "da lo mismo en cualquier dirección.")
    m.titulo("Concreto: un segmento circular", 3)
    m.parrafo("El bloque de compresión, de profundidad $a = \\text{mín}(\\beta_1 c, D)$, es un segmento "
              "circular. Con $\\alpha$ el medio ángulo que abarca desde el centro:")
    m.ecuacion(r"\alpha = \arccos \left( \frac{R - a}{R} \right)")
    m.ecuacion(r"A = R^2 \left( \alpha - \text{sen}\,\alpha \, \cos\alpha \right)")
    m.ecuacion(r"\bar{y} = \frac{4 R \, \text{sen}^3 \alpha}{3 \left( 2\alpha - \text{sen}\,2\alpha \right)}",
               cita="Área del segmento y distancia de su centroide al centro: `circular.phipnmn_circ`")
    m.ecuacion(r"C_c = 0.85 \, f'_c \, A")
    m.parrafo("Cuando el bloque llega justo al centro ($a = R$, $\\alpha$ = 90°), estas fórmulas dan el medio "
              "círculo: $A = \\pi R^2 / 2$ e $\\bar{y} = 4R / 3\\pi$.")
    m.titulo("Acero", 3)
    m.ecuacion(r"\text{brazo}_k = R_s \cos \left( \frac{2 \pi k}{n} \right), \quad t_k = R - \text{brazo}_k, "
               r"\quad k = 0, 1, \ldots, n - 1")
    m.ecuacion(r"P_n = C_c + \sum_k F_k, \quad M_n = C_c \, \bar{y} + \sum_k F_k \, \text{brazo}_k")
    m.parrafo("$\\varepsilon_k$, $f_k$ y $F_k$ salen de $t_k$ como antes. El programa trata toda columna "
              "circular como **con espiral**: $\\phi$ de la columna «con espiral» de la tabla y "
              "$P_{n,max} = 0.85 P_o$, con $A_g = \\pi R^2$.")
    m.codigo(circular)

    # ------------------------------------------------------------------ Verificación
    m.titulo("Verificación", 2)
    concreto, sec = _columna_del_ejemplo()
    b, h, d = concreto.b * 100 * CM_IN, concreto.h * 100 * CM_IN, concreto.d * 100 * CM_IN
    nx, ny, barra = concreto.nx, concreto.ny, concreto.barra
    fc, fy = concreto.fc / KSI_KN_M2, 60.0           # f'c del material del ejemplo; fy de la barra #6
    ab, nb = _area(barra), 2 * (nx + ny - 2)
    ast, ey = nb * ab, fy / ES

    m.parrafo("Los valores «a mano» están calculados aparte, con números sueltos en pulgadas, ksi y kip y las "
              "fórmulas de este capítulo; los del «programa» salen de `calculo/interaccion/`, por el mismo "
              "camino que usa la interfaz.")
    m.titulo("La columna del ejemplo", 3)
    m.tabla(["Dato", "Valor"], [
        ["Sección $b$ × $h$", f"{concreto.b * 100:.0f} × {concreto.h * 100:.0f} cm = {b:.3f} × {h:.3f} in"],
        ["$d$, del borde al centro de las barras", f"{concreto.d * 100:.0f} cm = {d:.3f} in"],
        ["Concreto", f"$f'_c$ = {fc:.0f} ksi"],
        ["Barras", f"#{barra}, con $n_x$ = {nx} y $n_y$ = {ny}; $f_y$ = {fy:.0f} ksi"],
    ], anchos_cm=[6.5, 9.4])
    m.comprobacion([
        ("Cantidad de barras, $n_b = 2 (n_x + n_y - 2)$", str(nb), str(sec["nbarras"]), nb == sec["nbarras"]),
        ("Acero total $A_{st}$ (cm²)", numero(ast * 2.54 ** 2, 6), numero(sec["As_total"].to("cm^2").magnitude, 6),
         bool(np.isclose(ast * 2.54 ** 2, sec["As_total"].to("cm^2").magnitude))),
        (r"Cuantía $\rho$ (%)", numero(100 * ast / (b * h), 6), numero(sec["cuantia"], 6),
         bool(np.isclose(100 * ast / (b * h), sec["cuantia"]))),
        (r"$\beta_1$", numero(_beta1(fc), 4), numero(sec["beta1"], 4), bool(np.isclose(_beta1(fc), sec["beta1"]))),
        (r"$\varepsilon_y = f_y / E_s$", numero(ey, 6), numero(sec["epsilon_y"], 6), bool(np.isclose(ey, sec["epsilon_y"]))),
    ])

    m.titulo("Compresión pura", 3)
    po = 0.85 * fc * (b * h - ast) + fy * ast
    m.parrafo(f"$A_g$ = {b:.3f} × {h:.3f} = {b * h:.2f} in² y $A_{{st}}$ = {nb} × {ab:.4f} = {ast:.3f} in². "
              f"Entonces $P_o$ = 0.85 × {fc:.0f} × ({b * h:.2f} − {ast:.3f}) + {fy:.0f} × {ast:.3f} = "
              f"{po:.1f} kip = {po * KIP_TONF:.2f} tonf, y el techo de diseño es 0.65 × 0.80 × $P_o$. El "
              "programa debe dar $P_n = P_o$ en el último punto de la curva ($c = 3h$).")
    _phi_fin, pn_fin, _mn_fin, phi_pn_fin, _ = rectangular.phipnmn(3 * h * ureg.inch, sec)
    m.comprobacion([
        ("$P_o$ (tonf)", numero(po * KIP_TONF, 6), numero(pn_fin.magnitude, 6),
         bool(np.isclose(po * KIP_TONF, pn_fin.magnitude))),
        (r"Techo de diseño, $0.65 \cdot 0.80 \, P_o$ (tonf)", numero(0.52 * po * KIP_TONF, 6),
         numero(phi_pn_fin.magnitude, 6), bool(np.isclose(0.52 * po * KIP_TONF, phi_pn_fin.magnitude))),
    ])

    m.titulo("Punto balanceado, fila por fila", 3)
    dt = h - d
    cb = 0.003 * dt / (0.003 + ey)
    mano = rectangular_a_mano(b, h, d, nx, ny, fc, fy, barra, cb)
    m.parrafo("En el punto balanceado el concreto llega a 0.003 justo cuando la fila más traccionada llega a "
              "la fluencia. Por triángulos semejantes en el diagrama de deformaciones:")
    m.ecuacion(r"c_b = \frac{0.003}{0.003 + \varepsilon_y} \, d_t")
    m.parrafo(f"Con $d_t = h - d$ = {dt:.3f} in y $\\varepsilon_y$ = {ey:.6f}: $c_b$ = {cb:.3f} in, "
              f"$a = \\beta_1 c_b$ = {mano['a']:.3f} in y $C_c$ = 0.85 × {fc:.0f} × {b:.3f} × {mano['a']:.3f} = "
              f"{mano['cc']:.2f} kip, con brazo $h/2 - a/2$ = {mano['brazo_cc']:.3f} in. Las filas de acero:")
    m.tabla(["Fila", "$y_i$ (in)", "Barras", r"$\varepsilon_{si}$", "$f_{si}$ (ksi)", "$F_i$ (kip)", "Brazo (in)",
             "$F_i$ × brazo (kip·in)"],
            [[texto.replace("-", "−") for texto in
              (str(i), f"{y:.3f}", str(n), f"{e:+.6f}", f"{f:+.2f}", f"{fuerza:+.2f}", f"{brazo:+.3f}", f"{momento:+.1f}")]
             for i, y, n, e, f, fuerza, brazo, momento in mano["filas"]],
            anchos_cm=[1.2, 1.9, 1.5, 2.3, 2.1, 2.1, 2.1, 2.7], centrar=range(8))
    suma_f, suma_m = sum(f[5] for f in mano["filas"]), sum(f[7] for f in mano["filas"])
    m.parrafo((f"Sumando: $P_n$ = {mano['cc']:.2f} + ({suma_f:+.2f}) = {mano['pn']:.2f} kip = "
               f"{mano['pn'] * KIP_TONF:.2f} tonf, y $M_n$ = {mano['cc']:.2f} × {mano['brazo_cc']:.3f} + "
               f"({suma_m:+.1f}) = {mano['mn']:.1f} kip·in = {mano['mn'] * KIPIN_TONFM:.2f} tonf·m. ").replace("-", "−")
              + "Como $\\varepsilon_t = \\varepsilon_y$, la sección está en el límite de «controlada por "
                "compresión»: $\\phi$ = 0.65.")
    dimensiones = {"b": b, "h": h, "d": d, "c": cb, "nx": nx}
    m.figura(_figura_seccion(dimensiones, mano),
             "Punto balanceado de la columna del ejemplo: la sección, con el bloque de compresión sombreado; las "
             "deformaciones, de 0.003 en la fibra comprimida a la fluencia en la última fila; y las fuerzas.",
             ancho_cm=15.5)
    phi_b, pn_b, mn_b, phi_pn_b, phi_mn_b = rectangular.phipnmn(cb * ureg.inch, sec)
    m.comprobacion([
        ("$P_n$ en el punto balanceado (tonf)", numero(mano["pn"] * KIP_TONF, 6), numero(pn_b.magnitude, 6),
         bool(np.isclose(mano["pn"] * KIP_TONF, pn_b.magnitude))),
        ("$M_n$ en el punto balanceado (tonf·m)", numero(mano["mn"] * KIPIN_TONFM, 6), numero(mn_b.magnitude, 6),
         bool(np.isclose(mano["mn"] * KIPIN_TONFM, mn_b.magnitude))),
        (r"$\phi$ en el punto balanceado", numero(mano["phi"], 6), numero(phi_b, 6),
         bool(np.isclose(mano["phi"], phi_b, atol=1e-9))),
    ])

    m.titulo("Otros puntos del diagrama", 3)
    c_traccion = 0.003 * dt / (0.003 + ey + 0.003)
    traccion = rectangular_a_mano(b, h, d, nx, ny, fc, fy, barra, c_traccion)
    phi_t, pn_t, mn_t, _phi_pn_t, _phi_mn_t = rectangular.phipnmn(c_traccion * ureg.inch, sec)
    m.parrafo("La sección pasa a «controlada por tracción» ($\\phi$ = 0.90) cuando "
              "$\\varepsilon_t = \\varepsilon_y + 0.003$, es decir, con "
              f"$c = 0.003 \\, d_t / (0.006 + \\varepsilon_y)$ = {c_traccion:.3f} in. Y con $\\theta$ = 90°, la "
              "flexión biaxial debe dar lo mismo que la de un eje.")
    _phi_x, p_x, mx_x, my_x, _pp, _pmx, _pmy = biaxial.phipnmn_biaxial(cb, math.pi / 2, sec)
    m.comprobacion([
        (r"$\phi$ con $\varepsilon_t = \varepsilon_y + 0.003$", "0.9", numero(phi_t, 6),
         bool(np.isclose(phi_t, 0.90, atol=1e-9))),
        ("$P_n$ en ese punto (tonf)", numero(traccion["pn"] * KIP_TONF, 6), numero(pn_t.magnitude, 6),
         bool(np.isclose(traccion["pn"] * KIP_TONF, pn_t.magnitude))),
        ("$M_n$ en ese punto (tonf·m)", numero(traccion["mn"] * KIPIN_TONFM, 6), numero(mn_t.magnitude, 6),
         bool(np.isclose(traccion["mn"] * KIPIN_TONFM, mn_t.magnitude))),
        (r"Biaxial con $\theta$ = 90° y $c = c_b$: $P_n$ (tonf)", numero(mano["pn"] * KIP_TONF, 6),
         numero(p_x * KIP_TONF, 6), bool(np.isclose(mano["pn"] * KIP_TONF, p_x * KIP_TONF))),
        (r"Biaxial con $\theta$ = 90° y $c = c_b$: $M_x$ (tonf·m)", numero(mano["mn"] * KIPIN_TONFM, 6),
         numero(mx_x * KIPIN_TONFM, 6), bool(np.isclose(mano["mn"] * KIPIN_TONFM, mx_x * KIPIN_TONFM))),
        (r"Biaxial con $\theta$ = 90°: $M_y$ (tonf·m), por simetría", "0", numero(my_x * KIPIN_TONFM, 2),
         abs(my_x * KIPIN_TONFM) < 1e-9),
    ], encabezados=("Comprobación", "A mano", "Programa", ""))

    m.figura(_figura_diagrama(sec, [
        ("Po", (0.0, po * KIP_TONF), (8, -1), "left"),
        ("Techo de diseño: 0.65 · 0.80 · Po", (0.0, 0.52 * po * KIP_TONF), (8, 5), "left"),
        ("Balanceado (nominal)", (mn_b.magnitude, pn_b.magnitude), (8, -3), "left"),
        ("Balanceado (diseño)", (phi_mn_b.magnitude, phi_pn_b.magnitude), (-8, -12), "right"),
        ("Desde aquí hacia abajo, φ = 0.90", (0.90 * mn_t.magnitude, 0.90 * pn_t.magnitude), (9, -4), "left"),
    ]), "Diagrama de interacción de la columna del ejemplo, con flexión en un eje, calculado por el programa. "
        "Los puntos son los que se comprobaron a mano.")

    m.titulo("Columna circular", 3)
    diametro_cm, d_cm, nbarras, barra_c = 50.0, 6.0, 8, 8
    diametro, dc = diametro_cm * CM_IN, d_cm * CM_IN
    mano_c = circular_a_mano(diametro, dc, nbarras, fc, fy, barra_c)
    sec_c = circular.propiedades_circular(diametro_cm * ureg.cm, d_cm * ureg.cm, nbarras, fc * ureg.ksi, barra_c)
    phi_c, pn_c, mn_c, _phi_pn_c, _phi_mn_c = circular.phipnmn_circ(mano_c["c"], sec_c)
    _phi_fin, pn_cfin, _m, phi_pn_cfin, _pm = circular.phipnmn_circ(3 * diametro, sec_c)
    m.parrafo(f"Columna de $D$ = {diametro_cm:.0f} cm con {nbarras} barras #{barra_c}, $d$ = {d_cm:.0f} cm y "
              f"$f'_c$ = {fc:.0f} ksi. Se comprueba el punto en que el bloque llega al centro ($a = R$, o sea "
              f"$c = R / \\beta_1$ = {mano_c['c']:.3f} in): ahí el concreto comprimido es medio círculo, de "
              "área $\\pi R^2 / 2$ y centroide a $4R / 3\\pi$ del centro, y las barras se suman una por una.")
    m.comprobacion([
        ("$P_n$ con $a = R$ (tonf)", numero(mano_c["pn"] * KIP_TONF, 6), numero(pn_c, 6),
         bool(np.isclose(mano_c["pn"] * KIP_TONF, pn_c))),
        ("$M_n$ con $a = R$ (tonf·m)", numero(mano_c["mn"] * KIPIN_TONFM, 6), numero(mn_c, 6),
         bool(np.isclose(mano_c["mn"] * KIPIN_TONFM, mn_c))),
        (r"$\phi$ con $a = R$ (espiral)", numero(mano_c["phi"], 6), numero(phi_c, 6),
         bool(np.isclose(mano_c["phi"], phi_c, atol=1e-9))),
        ("$P_o$ (tonf)", numero(mano_c["po"] * KIP_TONF, 6), numero(pn_cfin, 6),
         bool(np.isclose(mano_c["po"] * KIP_TONF, pn_cfin))),
        (r"Techo de diseño, $0.75 \cdot 0.85 \, P_o$ (tonf)", numero(0.75 * 0.85 * mano_c["po"] * KIP_TONF, 6),
         numero(phi_pn_cfin, 6), bool(np.isclose(0.75 * 0.85 * mano_c["po"] * KIP_TONF, phi_pn_cfin))),
    ])

    # ------------------------------------------------------------------ Limitaciones
    m.titulo("Limitaciones y hallazgos pendientes", 2)
    m.parrafo("Este capítulo describe lo que el programa hace **hoy**. Lo que sigue está identificado y "
              "pendiente de decidir; corregirlo cambia el cálculo, así que se hará en un cambio aparte, con su "
              "propia verificación.")
    m.lista([
        "**$\\beta_1$ con $f'_c$ = 2.5 ksi:** el programa lo rechaza (exige $f'_c$ > 2.5 ksi), pero la Tabla "
        "22.2.2.4.3 del ACI 318-19 incluye $f'_c$ = 2500 psi (PDF p. 401).",
        "**Barras #14 y #18:** el programa les da 14/8 y 18/8 de pulgada; sus diámetros nominales son 1.693 y "
        "2.257 in (ACI 318-19, Apéndice B, PDF p. 583). La interfaz solo ofrece de la #3 a la #11, que están "
        "bien.",
        "**Área de la barra:** se calcula como $\\pi d_b^2 / 4$ y no con el área nominal de la tabla del "
        "Apéndice B. La diferencia es menor de 1 % (en la #6, 0.4418 contra 0.44 in²).",
        "**$f_y$ según la barra:** 40 ksi para la #3 y 60 ksi para las demás es un supuesto del programa. El "
        "grado del acero debería ser un dato de la sección.",
        "**Cuantía:** el programa la calcula pero no la limita. El ACI 318-19 pide "
        "$0.01 A_g \\le A_{st} \\le 0.08 A_g$ (§10.6.1.1, PDF p. 160) y, en columnas de pórticos especiales, "
        "un máximo de $0.06 A_g$ (§18.7.4.1, PDF p. 308).",
        "**Columna circular:** siempre se calcula como con espiral. Con aros circulares corresponden la "
        "columna «con estribos» de la Tabla 21.2.2 y $P_{n,max} = 0.80 P_o$, que dan menos resistencia de "
        "diseño.",
        "**$\\varepsilon_{ty}$:** se usa $f_y / E_s$. El ACI 318-19 permite tomar 0.002 con acero Grado 60 "
        "(§21.2.2.1, PDF p. 394); la diferencia solo mueve un poco la zona de transición de $\\phi$.",
        "**Alcance:** el diagrama es el de la sección. Todavía no se comparan contra él las fuerzas de la "
        "columna ($P_u$, $M_u$), ni se considera la esbeltez. Eso es la etapa de diseño de columnas.",
        "**Unidades:** estas fórmulas trabajan en pulgadas y ksi, y el resto del programa en kN y m. La "
        "conversión se hace en un solo lugar (`modelo/interaccion.py`).",
    ])
