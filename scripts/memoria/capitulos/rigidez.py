"""Capítulo 2: Matriz de rigidez de la barra y su transformación (calculo/rigidez/barra.py).

Fórmulas de análisis matricial (no vienen de una norma) y el código que las calcula.
"""
from calculo.rigidez import barra

# Grados de libertad de la barra en ejes locales, en el orden del programa
GDL = [r"u_i", r"v_i", r"w_i", r"\phi_{xi}", r"\phi_{yi}", r"\phi_{zi}",
       r"u_j", r"v_j", r"w_j", r"\phi_{xj}", r"\phi_{yj}", r"\phi_{zj}"]

# La matriz como la escribe el programa: k = (E / L³) · [tabla]
TERMINOS = {"a": r"A L^2", "12z": r"12 I_z", "6z": r"6 L I_z", "4z": r"4 L^2 I_z", "2z": r"2 L^2 I_z",
            "12y": r"12 I_y", "6y": r"6 L I_y", "4y": r"4 L^2 I_y", "2y": r"2 L^2 I_y",
            "t": r"\frac{G J L^2}{E}"}
TABLA = [fila.split() for fila in (
    "a    0    0    0    0    0   -a    0    0    0    0    0",
    "0  12z    0    0    0   6z    0 -12z    0    0    0   6z",
    "0    0  12y    0  -6y    0    0    0 -12y    0  -6y    0",
    "0    0    0    t    0    0    0    0    0   -t    0    0",
    "0    0  -6y    0   4y    0    0    0   6y    0   2y    0",
    "0   6z    0    0    0   4z    0  -6z    0    0    0   2z",
    "-a   0    0    0    0    0    a    0    0    0    0    0",
    "0 -12z    0    0    0  -6z    0  12z    0    0    0  -6z",
    "0    0 -12y    0   6y    0    0    0  12y    0   6y    0",
    "0    0    0   -t    0    0    0    0    0    t    0    0",
    "0    0  -6y    0   2y    0    0    0   6y    0   4y    0",
    "0   6z    0    0    0   2z    0  -6z    0    0    0   4z",
)]


def _latex(clave):
    """La celda de la tabla: vacía si es cero; si no, la fórmula del término con su signo."""
    if clave == "0":
        return ""
    return ("-" if clave.startswith("-") else "") + TERMINOS[clave.lstrip("-")]


def capitulo(m):
    m.titulo("Matriz de rigidez y transformación")
    m.parrafo("Método de rigidez: cada barra aporta una matriz que relaciona las fuerzas en sus extremos con los "
              "desplazamientos de sus nodos. Código: `calculo/rigidez/barra.py`.")

    m.titulo("Hipótesis", 2)
    m.lista([
        "Barra recta y prismática, material elástico lineal, desplazamientos pequeños (primer orden).",
        "Flexión de Euler-Bernoulli, sin deformación por cortante; torsión de Saint-Venant ($J$).",
        "Axial, torsión y flexión en los dos planos, sin acoplar. Nodos rígidos en los dos extremos.",
    ])

    m.titulo("Matriz de rigidez local", 2)
    m.parrafo("12 grados de libertad: en cada extremo, $u$, $v$, $w$ a lo largo de $x$, $y$, $z$ locales y los "
              "giros $\\phi_x$, $\\phi_y$, $\\phi_z$.")
    m.ecuacion(r"f = k \, u")
    m.tabla(["Efecto", "Rigidez"], [
        ["Axial", r"$\frac{E A}{L}$"], ["Torsión", r"$\frac{G J}{L}$"],
        ["Flexión", r"$\frac{12 E I}{L^3}, \; \frac{6 E I}{L^2}, \; \frac{4 E I}{L}, \; \frac{2 E I}{L}$"],
    ], anchos_cm=[3.0, 6.0], centrar=(1,))
    m.parrafo("$I_z$ para la flexión en el plano $x$–$y$ ($v$, $\\phi_z$) e $I_y$ para la del plano $x$–$z$ "
              "($w$, $\\phi_y$).")
    m.ecuacion(r"k = \frac{E}{L^3} \, \left[ \; \text{tabla siguiente} \; \right]",
               cita="`k_local`; las celdas vacías son ceros")
    m.matriz(GDL, [[_latex(clave) for clave in fila] for fila in TABLA])
    m.codigo(barra.k_local)

    m.titulo("Largo y ángulos", 2)
    m.ecuacion(r"L = \sqrt{dx^2 + dy^2 + dz^2}")
    m.ecuacion(r"\gamma = \text{atan2} \left( dy, \, dx \right)")
    m.ecuacion(r"\beta = - \text{atan2} \left( dz, \, \sqrt{dx^2 + dy^2} \right)", cita="`angulos`")
    m.parrafo("$\\gamma$: ángulo en planta; $\\beta$: inclinación (negativa por la convención de $B$); "
              "$\\alpha$: giro de la sección, dado por el usuario en grados.")
    m.codigo(barra.angulos)

    m.titulo("Matriz de rotación", 2)
    m.ecuacion(r"A(\alpha) = \begin{bmatrix} 1 & 0 & 0 \\ 0 & \cos\alpha & \text{sen}\,\alpha \\ "
               r"0 & -\text{sen}\,\alpha & \cos\alpha \end{bmatrix}")
    m.ecuacion(r"B(\beta) = \begin{bmatrix} \cos\beta & 0 & -\text{sen}\,\beta \\ 0 & 1 & 0 \\ "
               r"\text{sen}\,\beta & 0 & \cos\beta \end{bmatrix}")
    m.ecuacion(r"C(\gamma) = \begin{bmatrix} \cos\gamma & \text{sen}\,\gamma & 0 \\ "
               r"-\text{sen}\,\gamma & \cos\gamma & 0 \\ 0 & 0 & 1 \end{bmatrix}")
    m.ecuacion(r"R = A(\alpha) \, B(\beta) \, C(\gamma)", cita="`rotacion`")
    m.parrafo("Las filas de $R$ son los ejes locales escritos en globales: $v_{local} = R \\, v_{global}$.")
    m.codigo(barra.rotacion)

    m.titulo("Transformación y rigidez en ejes globales", 2)
    m.ecuacion(r"T = \begin{bmatrix} R & 0 & 0 & 0 \\ 0 & R & 0 & 0 \\ 0 & 0 & R & 0 \\ 0 & 0 & 0 & R "
               r"\end{bmatrix}", cita="`transformacion`")
    m.ecuacion(r"K = T^{\mathsf{T}} \, k \, T", cita="`k_global_barra`")
    m.codigo(barra.k_global_barra)

    m.titulo("Limitaciones", 2)
    m.lista([
        "Primer orden: sin P-Δ ni pandeo.",
        "Sin deformación por cortante, liberaciones ni brazos rígidos.",
        "Inercia bruta, sin los factores de agrietamiento del ACI 318-19.",
    ])
