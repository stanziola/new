"""Capítulo 4: Vigueta T de una losa nervada (calculo/diseno/viga.py y modelo/diseno_vigueta.py).

Fórmulas y código. Las citas del ACI 318-19 se confirmaron en el PDF de docs/codigos/ (páginas del PDF).
"""
from calculo.diseno import viga
from modelo import diseno_vigueta, losas


def capitulo(m):
    m.titulo("Vigueta T de una losa nervada")
    m.parrafo("Diseño de la vigueta de una losa de viguetas en una dirección (ACI 318-19 §9.8): flexión, "
              "cortante y deflexiones, con las fuerzas de todos sus sistemas (franjas) y casos de viva. "
              "Fórmulas: `calculo/diseno/viga.py`; cómo se juntan: `modelo/diseno_vigueta.py` y "
              "`modelo/losas.py`.")

    m.titulo("Hipótesis", 2)
    m.lista([
        "Cada franja de la losa es una vigueta continua con apoyos simples en los ejes de las vigas; los claros "
        "van de eje a eje y la carga ocupa todo el claro.",
        "Una sola vigueta (sección T) para toda la losa; la separación $s$ sale de las viguetas del paño de "
        "referencia y vale en toda la losa.",
        "Carga viva por patrones (§6.4.2, p. 75): todos los claros, los impares, los pares, cada par de vecinos "
        "y los que agregue el usuario.",
        "$M_u$ y $V_u$ en la cara de las vigas (§9.4.2.1 y §9.4.3.1, p. 132; figura R9.4.3.2(e), p. 134).",
        "Bloque rectangular equivalente con $\\varepsilon_{cu} = 0.003$ (§22.2.2.1 y §22.2.2.4.1, p. 400) y "
        "$E_s = 29\\,000$ ksi (§20.2.2.2, p. 376); el acero en tracción fluye.",
    ])

    m.titulo("Ancho efectivo y peso propio", 2)
    m.ecuacion(r"b_f = \min\left( s, \; b_w + 2\min\left(8 h_f, \frac{s_w}{2}, \frac{\ell_n}{8}\right) \right)",
               cita="ACI 318-19 Tabla 6.3.2.1 (p. 75) · `ancho_efectivo`")
    m.ecuacion(r"w_{pp} = \left( A_T + (s - b_f)\,h_f \right) \gamma",
               cita="por vigueta: si $b_f < s$, la losa entre alas también pesa · `losas.sistema`")
    m.codigo(viga.ancho_efectivo)

    m.titulo("Flexión", 2)
    m.ecuacion(r"a = \frac{A_s f_y}{0.85 f'_c \, b}", cita="ACI 318-19 §22.2.2.4.1 (p. 400)")
    m.ecuacion(r"M_n = A_s f_y \left( d - \frac{a}{2} \right) \quad (a \le h_f)")
    m.ecuacion(r"M_n = C_f \left( d - \frac{h_f}{2} \right) + 0.85 f'_c b_w a \left( d - \frac{a}{2} \right), "
               r"\quad C_f = 0.85 f'_c (b - b_w) h_f \quad (a > h_f)", cita="la T con el bloque en el alma")
    m.ecuacion(r"c = \frac{a}{\beta_1}, \qquad \varepsilon_t = 0.003 \, \frac{d - c}{c}",
               cita="Tabla 22.2.2.4.3 (p. 401) para $\\beta_1$")
    m.ecuacion(r"\phi = 0.65 + 0.25 \, \frac{\varepsilon_t - \varepsilon_{ty}}{0.003}, \quad "
               r"0.65 \le \phi \le 0.90", cita="ACI 318-19 Tabla 21.2.2 (p. 395); $\\varepsilon_{ty} = f_y/E_s$ "
                                               "(§21.2.2.1, p. 394)")
    m.parrafo("Momento positivo: el ala comprimida ($b = b_f$). Negativo: el alma comprimida abajo ($b = b_w$). "
              "Las vigas deben quedar controladas por tracción: $\\varepsilon_t \\ge \\varepsilon_{ty} + 0.003$ "
              "(§9.3.3.1, p. 132).")
    m.codigo(viga.flexion)
    m.ecuacion(r"A_{s,min} = \max\left( \frac{3\sqrt{f'_c}}{f_y}, \frac{200}{f_y} \right) b_w d",
               cita="ACI 318-19 §9.6.1.2 (p. 137); no hace falta si $A_s \\ge \\frac{4}{3} A_{s,req}$ "
                    "(§9.6.1.3, p. 138)")
    m.codigo(viga.as_minimo)

    m.titulo("Cortante", 2)
    m.ecuacion(r"V_c = 2 \lambda \sqrt{f'_c} \, b_w d \quad (A_v \ge A_{v,min})",
               cita="ACI 318-19 Tabla 22.5.5.1(a) (p. 406); con $N_u = 0$")
    m.ecuacion(r"V_c = 8 \lambda_s \lambda \, \rho_w^{1/3} \sqrt{f'_c} \, b_w d \quad (A_v < A_{v,min}), \qquad "
               r"\lambda_s = \sqrt{\frac{2}{1 + d/10}} \le 1",
               cita="Tabla 22.5.5.1(c) (p. 406) y Ec. 22.5.5.1.3 (p. 407), $d$ en in; $\\rho_w = A_s/(b_w d)$")
    m.ecuacion(r"\frac{A_{v,min}}{s} = \max\left( 0.75\sqrt{f'_c}, \; 50 \right) \frac{b_w}{f_{yt}}, \qquad "
               r"V_s = \frac{A_v f_{yt} d}{s}", cita="Tabla 9.6.3.4 (p. 140) y Ec. 22.5.8.5.3 (p. 412)")
    m.ecuacion(r"\phi \left( 1.1 V_c + V_s \right) \ge V_u, \quad \phi = 0.75, \quad "
               r"V_c \le 5\lambda\sqrt{f'_c}\,b_w d",
               cita="§9.8.1.5 (p. 153), Tabla 21.2.1(b) (p. 393) y §22.5.5.1.1 (p. 407)")
    m.codigo(viga.vc)

    m.titulo("Deflexiones", 2)
    m.ecuacion(r"f_r = 7.5\lambda\sqrt{f'_c}, \qquad M_{cr} = \frac{f_r I_g}{y_t}",
               cita="ACI 318-19 §19.2.3.1 (p. 358) y Ec. 24.2.3.5 (p. 459)")
    m.ecuacion(r"I_e = \frac{I_{cr}}{1 - \left( \frac{(2/3) M_{cr}}{M_a} \right)^2 \left( 1 - \frac{I_{cr}}{I_g} "
               r"\right)} \le I_g \quad \left( M_a > \tfrac{2}{3} M_{cr} \right)",
               cita="ACI 318-19 Tabla 24.2.3.5 (p. 459); a media luz de cada claro (§24.2.3.7)")
    m.parrafo("$M_a$ por nivel de carga (D, D + L y la sostenida D + $\\psi$L), el mayor entre los casos de viva. "
              "Cada nivel se vuelve a resolver con $I = I_e$ claro por claro.")
    m.ecuacion(r"\Delta_L = \Delta_{D+L} - \Delta_D \le \frac{\ell}{360}", cita="Tabla 24.2.2 (p. 458), pisos")
    m.ecuacion(r"\lambda_\Delta \Delta_{sost} + \Delta_L \le \frac{\ell}{480} \;\; \left(\text{o } "
               r"\frac{\ell}{240}\right), \qquad \lambda_\Delta = \frac{\xi}{1 + 50\rho'}",
               cita="Tabla 24.2.2 (p. 458) y Ec. 24.2.4.1.1 (p. 460); con $\\Delta_L$ completa, del lado seguro")
    m.codigo(viga.inercia_agrietada)
    m.codigo(viga.inercia_efectiva)

    m.titulo("Viguetas (§9.8)", 2)
    m.tabla(["Requisito", "Límite", "Cláusula"], [
        ["Ancho del nervio", "$b_w \\ge 4$ in", "§9.8.1.2 (p. 153)"],
        ["Altura del nervio", "$h - h_f \\le 3.5 \\, b_w$", "§9.8.1.3 (p. 153)"],
        ["Separación libre", "$\\le 30$ in", "§9.8.1.4 (p. 153)"],
        ["Losa", "$h_f \\ge \\max(\\text{libre}/12, \\, 2 \\text{ in})$", "§9.8.3.1 (p. 154)"],
        ["Apoyo exterior (recomendada)", "$\\phi M_n^- \\ge w_u \\ell_n^2 / 24$", "Tabla 6.5.2 (p. 76)"],
    ], anchos_cm=[4.5, 5.5, 4.0])
    m.codigo(diseno_vigueta.combinaciones_efectivas)
    m.codigo(losas.patrones_automaticos)

    m.titulo("Limitaciones", 2)
    m.lista([
        "La vigueta de borde sin viga lateral (ala de un solo lado) se avisa, pero se diseña con la misma T.",
        "El refuerzo de temperatura de la losa (§9.8.1.7 y 24.4) todavía no se revisa.",
        "Sin redistribución de momentos (§6.6.5) ni corte de barras diseñado (etapa 5): el acero de arriba "
        "se dibuja hasta ℓn/3 (o ℓn/5 en un apoyo exterior).",
        "$\\rho' = 0$ en $\\lambda_\\Delta$: el acero de arriba es de los apoyos, no llega a media luz.",
    ])
