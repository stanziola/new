"""Capítulo: Cargas en barras (calculo/rigidez/empotramiento.py y diagramas.py).

Cómo llegan a los nodos las cargas a lo largo de una barra (fuerzas de empotramiento) y cómo se
calculan N, V, M y T a lo largo de ella. Análisis matricial: no vienen de una norma.
"""
from calculo.rigidez import diagramas, empotramiento


def capitulo(m):
    m.titulo("Cargas en barras")
    m.parrafo("Las cargas sobre una barra se llevan a sus nodos con las fuerzas de empotramiento (FEF): el "
              "trabajo de la carga sobre las funciones de forma de la barra. Código: "
              "`calculo/rigidez/empotramiento.py` y `calculo/rigidez/diagramas.py`.")

    m.titulo("Hipótesis", 2)
    m.lista([
        "Las de la matriz de rigidez (Euler-Bernoulli, primer orden); las cargas, en ejes locales.",
        "Uniforme en toda la barra; puntual y momento en $x = a$; trapezoidal: lineal de $q_1$ en $a$ a $q_2$ "
        "en $b$ ($q_1 = q_2$ es una uniforme parcial).",
    ])

    m.titulo("Funciones de forma", 2)
    m.ecuacion(r"\xi = \frac{x}{L}")
    m.ecuacion(r"N_1 = 1 - 3\xi^2 + 2\xi^3 \qquad N_2 = L \left( \xi - 2\xi^2 + \xi^3 \right)")
    m.ecuacion(r"N_3 = 3\xi^2 - 2\xi^3 \qquad N_4 = L \left( -\xi^2 + \xi^3 \right)", cita="`_forma`")
    m.parrafo("Axial y torsión con las lineales $1 - \\xi$ y $\\xi$.")

    m.titulo("Cargas equivalentes", 2)
    m.ecuacion(r"p = N(a) \, P", cita="`equivalentes_puntual`")
    m.codigo(empotramiento.equivalentes_puntual)
    m.ecuacion(r"q(x) = q_1 + \left( q_2 - q_1 \right) \frac{x - a}{b - a}")
    m.ecuacion(r"p = \int_a^b N(x) \, q(x) \, dx = \frac{b - a}{2} \sum_{g=1}^{3} w_g \, N(x_g) \, q(x_g)",
               cita="`equivalentes_lineal`")
    m.ecuacion(r"t_g = 0, \; \pm \sqrt{3/5} \qquad w_g = 8/9, \; 5/9 \qquad x_g = \frac{a + b}{2} + \frac{b - a}{2} t_g")
    m.parrafo("Exacta: $N(x)\\,q(x)$ es de grado 4 y Gauss de 3 puntos integra sin error hasta grado 5.")
    m.codigo(empotramiento.equivalentes_lineal)
    m.ecuacion(r"FEF = -p \qquad F_{nodos} = -T^{\mathsf{T}} \, FEF \qquad f = k \, u + FEF",
               cita="`empotramiento`")

    m.titulo("Fuerzas internas", 2)
    m.parrafo("Equilibrio del tramo de 0 a $x$, con las fuerzas del nodo $i$ sobre la barra ($F_i$, $M_i$):")
    m.ecuacion(r"S = -\left( F_i + \sum F_{0 \to x} \right) \qquad "
               r"M_c = -\left( M_i + r_i \times F_i + \sum r \times F_{0 \to x} \right)", cita="`internas`")
    m.ecuacion(r"N = S_x \quad V_y = -S_y \quad V_z = -S_z \quad T = M_{cx} \quad M_y = -M_{cy} \quad M_z = M_{cz}")
    m.parrafo("La trapezoidal aporta su parte entre $a$ y $\\min(x, b)$: $\\int q$ y $\\int (s - x)\\,e_1 \\times q$, "
              "con Gauss de 2 puntos (exacto hasta grado 3).")
    m.codigo(diagramas.internas)

    m.titulo("Limitaciones", 2)
    m.lista([
        "Sin cargas de temperatura ni asentamientos.",
        "La carga de una losa de viguetas sobre su viga es la reacción de cada vigueta entre su separación: "
        "continua, aunque en la realidad son puntuales cada $s$.",
    ])
