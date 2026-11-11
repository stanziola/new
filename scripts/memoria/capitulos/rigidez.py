"""Capítulo 2: Matriz de rigidez de la barra y su transformación (calculo/rigidez/barra.py).

Las fórmulas de este capítulo son de análisis matricial (no vienen de una norma). Las verificaciones
se calculan aquí por otro camino, sin usar el programa, y se comparan con lo que da el programa.
"""
import numpy as np

from calculo.rigidez import barra
from modelo import Modelo
from modelo.analisis import analizar_caso
from scripts.memoria.documento import numero

# Grados de libertad de la barra en ejes locales, en el orden del programa
GDL = [r"u_i", r"v_i", r"w_i", r"\phi_{xi}", r"\phi_{yi}", r"\phi_{zi}",
       r"u_j", r"v_j", r"w_j", r"\phi_{xj}", r"\phi_{yj}", r"\phi_{zj}"]

# La matriz como la escribe el programa: k = (E / L³) · [tabla]. Cada término: su fórmula y su valor
TERMINOS = {
    "a": (r"A L^2", lambda p: p["a"] * p["l"] ** 2),
    "12z": (r"12 I_z", lambda p: 12 * p["iz"]),
    "6z": (r"6 L I_z", lambda p: 6 * p["l"] * p["iz"]),
    "4z": (r"4 L^2 I_z", lambda p: 4 * p["l"] ** 2 * p["iz"]),
    "2z": (r"2 L^2 I_z", lambda p: 2 * p["l"] ** 2 * p["iz"]),
    "12y": (r"12 I_y", lambda p: 12 * p["iy"]),
    "6y": (r"6 L I_y", lambda p: 6 * p["l"] * p["iy"]),
    "4y": (r"4 L^2 I_y", lambda p: 4 * p["l"] ** 2 * p["iy"]),
    "2y": (r"2 L^2 I_y", lambda p: 2 * p["l"] ** 2 * p["iy"]),
    "t": (r"\frac{G J L^2}{E}", lambda p: p["g"] * p["j"] * p["l"] ** 2 / p["e"]),
}
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

# Barra de prueba para las verificaciones (números cualesquiera, en kN y m)
PRUEBA = {"e": 25.0e6, "g": 10.4e6, "a": 0.12, "l": 4.0, "iy": 1.6e-3, "iz": 0.9e-3, "j": 2.0e-3}


def _latex(clave):
    """La celda de la tabla: vacía si es cero; si no, la fórmula del término con su signo."""
    if clave == "0":
        return ""
    return ("-" if clave.startswith("-") else "") + TERMINOS[clave.lstrip("-")][0]


def _valor(clave, p):
    if clave == "0":
        return 0.0
    return (-1.0 if clave.startswith("-") else 1.0) * TERMINOS[clave.lstrip("-")][1](p)


def _vector(v):
    """(0, −1, 0): un vector para una tabla, sin el −0 que deja el redondeo."""
    partes = (f"{x + 0.0:.0f}" if abs(x - round(x)) < 1e-9 else f"{x:.4f}" for x in np.round(v, 9))
    return "(" + ", ".join(partes).replace("-", "−") + ")"


def _voladizo(punta, carga):
    """Un voladizo de 3 m empotrado en el origen, resuelto con el programa completo. Devuelve los
    desplazamientos de la punta [Δx, Δy, Δz, φx, φy, φz]."""
    v = Modelo()
    v.agregar_material("Prueba", e=200e6, g=77e6)
    v.agregar_seccion("Prueba", a=0.01, iy=8e-5, iz=8e-5, j=1.6e-4)
    v.agregar_nodo(0, 0, 0)
    v.agregar_nodo(*punta)
    v.agregar_elemento(1, 2, 1, 1)
    v.restringir(1)
    v.cargar(2, **carga)
    return analizar_caso(v, v.caso_inicial()).res.desplazamientos[2]


def capitulo(m):
    m.titulo("Matriz de rigidez y transformación")
    m.parrafo("El programa analiza la estructura por el **método de rigidez**: cada barra aporta una matriz que "
              "relaciona las fuerzas en sus extremos con los desplazamientos de sus dos nodos. Este capítulo "
              "documenta esa matriz en los ejes de la barra (locales) y cómo se pasa a los ejes del modelo "
              "(globales). Todo está en `calculo/rigidez/barra.py`.")

    # ------------------------------------------------------------------ Hipótesis
    m.titulo("Hipótesis", 2)
    m.lista([
        "Barra **recta y prismática** (sección constante), de material **elástico lineal**.",
        "**Desplazamientos pequeños**: el equilibrio se plantea sobre la geometría sin deformar (análisis de "
        "primer orden, sin efecto P-Δ).",
        "Flexión de **Euler-Bernoulli**: las secciones siguen planas y perpendiculares al eje. No se incluye la "
        "deformación por cortante.",
        "El axial, la torsión y la flexión en los dos planos principales de la sección **no se acoplan** entre "
        "sí. La torsión es la de Saint-Venant, con la constante $J$.",
        "Los nodos son rígidos: la barra transmite fuerzas y momentos en sus dos extremos (sin articulaciones "
        "ni brazos rígidos).",
    ])
    m.parrafo("La deducción de la matriz está en los textos de análisis matricial, por ejemplo Kassimali, "
              "*Matrix Analysis of Structures*, y McGuire, Gallagher y Ziemian, *Matrix Structural Analysis*.")

    # ------------------------------------------------------------------ k local
    m.titulo("Matriz de rigidez local", 2)
    m.parrafo("En ejes locales, la barra tiene 12 grados de libertad: en cada extremo, los desplazamientos $u$, "
              "$v$, $w$ a lo largo de $x$, $y$, $z$ y los giros $\\phi_x$, $\\phi_y$, $\\phi_z$ alrededor de "
              "esos ejes. La matriz $k$ da las fuerzas de extremo $f$ que corresponden a los desplazamientos $u$:")
    m.ecuacion(r"f = k \, u")
    m.parrafo("La columna $j$ de $k$ son las doce fuerzas de extremo que aparecen cuando el grado de libertad "
              "$j$ vale 1 y los otros once valen 0. De ahí salen sus coeficientes, que son los de la barra "
              "biempotrada:")
    m.tabla(["Efecto", "Rigidez", "Qué significa"], [
        ["Axial", r"$\frac{E A}{L}$", "Fuerza para alargar la barra una unidad."],
        ["Torsión", r"$\frac{G J}{L}$", "Momento para torcer un extremo una unidad de giro."],
        ["Flexión", r"$\frac{12 E I}{L^3}$", "Cortante por un desplazamiento transversal unitario de un extremo."],
        ["Flexión", r"$\frac{6 E I}{L^2}$", "Momento por ese desplazamiento; y cortante por un giro unitario."],
        ["Flexión", r"$\frac{4 E I}{L}$", "Momento en el extremo que gira una unidad."],
        ["Flexión", r"$\frac{2 E I}{L}$", "Momento que ese giro transmite al otro extremo."],
    ], anchos_cm=[2.4, 2.6, 10.9], centrar=(1,))
    m.parrafo("La flexión en el plano $x$–$y$ (desplazamiento $v$ y giro $\\phi_z$) usa $I_z$; la del plano "
              "$x$–$z$ (desplazamiento $w$ y giro $\\phi_y$) usa $I_y$. En una sección rectangular con $b$ en "
              "$y$ y $h$ en $z$, $I_y = b h^3 / 12$ e $I_z = h b^3 / 12$.")
    m.parrafo("El programa escribe la matriz sacando el factor común $E / L^3$:")
    m.ecuacion(r"k = \frac{E}{L^3} \, \left[ \; \text{tabla siguiente} \; \right]",
               cita="`calculo/rigidez/barra.py`, función `k_local`")
    m.matriz(GDL, [[_latex(clave) for clave in fila] for fila in TABLA])
    m.parrafo("Las celdas vacías son ceros. Cada fila y cada columna corresponde al grado de libertad de su "
              "encabezado; por ejemplo, la celda ($v_i$, $\\phi_{zi}$) multiplicada por $E / L^3$ es "
              "$6 E I_z / L^2$.")
    m.parrafo("Los términos que acoplan $w$ con $\\phi_y$ llevan el signo contrario a los que acoplan $v$ con "
              "$\\phi_z$. No es un error: con la regla de la mano derecha, un giro positivo alrededor de $z$ "
              "levanta la barra hacia $+y$ (la pendiente es $dv/dx = +\\phi_z$), mientras que uno positivo "
              "alrededor de $y$ la baja hacia $-z$ ($dw/dx = -\\phi_y$).")
    m.codigo(barra.k_local)

    # ------------------------------------------------------------------ Ángulos
    m.titulo("Orientación de la barra: largo y ángulos", 2)
    m.parrafo("La barra va del nodo $i$ al nodo $j$. Con las diferencias de coordenadas $dx$, $dy$, $dz$ entre "
              "los dos nodos, su largo y sus dos ángulos de dirección son:")
    m.ecuacion(r"L = \sqrt{dx^2 + dy^2 + dz^2}")
    m.ecuacion(r"\gamma = \text{atan2} \left( dy, \, dx \right)")
    m.ecuacion(r"\beta = - \text{atan2} \left( dz, \, \sqrt{dx^2 + dy^2} \right)",
               cita="`calculo/rigidez/barra.py`, función `angulos`")
    m.parrafo("$\\gamma$ es el ángulo de la barra en planta, medido desde el eje $X$, y $\\beta$ su inclinación "
              "respecto de la horizontal. $\\beta$ lleva el signo menos por cómo está escrita la matriz $B$ que "
              "sigue: así, una barra que sube ($dz > 0$) queda con su eje $x$ hacia $+Z$. El tercer ángulo, "
              "$\\alpha$, es el **giro de la sección** alrededor del eje de la barra; lo da el usuario, en "
              "grados, y el programa lo pasa a radianes.")
    m.codigo(barra.angulos)

    # ------------------------------------------------------------------ Rotación
    m.titulo("Matriz de rotación", 2)
    m.parrafo("La orientación de la barra se arma con tres giros sucesivos, uno por cada ángulo:")
    m.ecuacion(r"A(\alpha) = \begin{bmatrix} 1 & 0 & 0 \\ 0 & \cos\alpha & \text{sen}\,\alpha \\ "
               r"0 & -\text{sen}\,\alpha & \cos\alpha \end{bmatrix}")
    m.ecuacion(r"B(\beta) = \begin{bmatrix} \cos\beta & 0 & -\text{sen}\,\beta \\ 0 & 1 & 0 \\ "
               r"\text{sen}\,\beta & 0 & \cos\beta \end{bmatrix}")
    m.ecuacion(r"C(\gamma) = \begin{bmatrix} \cos\gamma & \text{sen}\,\gamma & 0 \\ "
               r"-\text{sen}\,\gamma & \cos\gamma & 0 \\ 0 & 0 & 1 \end{bmatrix}")
    m.ecuacion(r"R = A(\alpha) \, B(\beta) \, C(\gamma)", cita="`calculo/rigidez/barra.py`, función `rotacion`")
    m.parrafo("$R$ es una matriz de 3 × 3. Sus **filas son los ejes locales** $x$, $y$, $z$ de la barra escritos "
              "en ejes globales: la primera fila es la dirección de la barra. Por eso $R$ pasa cualquier vector "
              "de globales a locales:")
    m.ecuacion(r"v_{local} = R \, v_{global} \quad \text{y} \quad v_{global} = R^{\mathsf{T}} \, v_{local}")
    m.parrafo("$R$ es ortogonal ($R R^{\\mathsf{T}} = I$): su inversa es su traspuesta, y por eso la vuelta a "
              "globales se hace con $R^{\\mathsf{T}}$.")
    m.codigo(barra.rotacion)

    # ------------------------------------------------------------------ Transformación
    m.titulo("Matriz de transformación y rigidez en ejes globales", 2)
    m.parrafo("Los 12 grados de libertad de la barra son cuatro vectores de tres componentes: el desplazamiento "
              "y el giro del nodo $i$, y los del nodo $j$. Cada uno se gira con la misma $R$, así que la "
              "transformación completa es una matriz de 12 × 12 con cuatro bloques $R$ en la diagonal:")
    m.ecuacion(r"T = \begin{bmatrix} R & 0 & 0 & 0 \\ 0 & R & 0 & 0 \\ 0 & 0 & R & 0 \\ 0 & 0 & 0 & R "
               r"\end{bmatrix}", cita="`calculo/rigidez/barra.py`, función `transformacion`")
    m.parrafo("Con $u_{local} = T \\, u_{global}$ y $f_{global} = T^{\\mathsf{T}} f_{local}$, la relación "
              "$f = k \\, u$ escrita en ejes globales queda:")
    m.ecuacion(r"K = T^{\mathsf{T}} \, k \, T", cita="`calculo/rigidez/barra.py`, función `k_global_barra`")
    m.parrafo("$K$ es la matriz de 12 × 12 de la barra en ejes globales. El programa suma las de todas las "
              "barras en la matriz de la estructura (ensamble) y resuelve $K U = F$. La ventana "
              "**Matriz de rigidez** de la interfaz muestra esta $K$ para cada barra.")
    m.codigo(barra.transformacion)
    m.codigo(barra.k_global_barra)

    # ------------------------------------------------------------------ Verificación
    m.titulo("Verificación", 2)
    p = PRUEBA
    k = barra.k_local(p["e"], p["g"], p["a"], p["l"], p["iy"], p["iz"], p["j"])
    tabla = p["e"] / p["l"] ** 3 * np.array([[_valor(clave, p) for clave in fila] for fila in TABLA])
    mayor = np.abs(k).max()

    m.titulo("La matriz local", 3)
    m.parrafo(f"Barra de prueba, en kN y m: $E$ = {numero(p['e'])}, $G$ = {numero(p['g'])}, $A$ = {p['a']}, "
              f"$L$ = {p['l']}, $I_y$ = {numero(p['iy'])}, $I_z$ = {numero(p['iz'])} y $J$ = {numero(p['j'])}. "
              "Los valores a mano salen de las fórmulas de la tabla de coeficientes.")
    a_mano = [
        (r"Axial, $E A / L$", p["e"] * p["a"] / p["l"], k[0, 0]),
        (r"Torsión, $G J / L$", p["g"] * p["j"] / p["l"], k[3, 3]),
        (r"Cortante por desplazamiento, $12 E I_z / L^3$", 12 * p["e"] * p["iz"] / p["l"] ** 3, k[1, 1]),
        (r"Momento por desplazamiento, $6 E I_z / L^2$", 6 * p["e"] * p["iz"] / p["l"] ** 2, k[5, 1]),
        (r"Momento por giro propio, $4 E I_z / L$", 4 * p["e"] * p["iz"] / p["l"], k[5, 5]),
        (r"Momento transmitido, $2 E I_z / L$", 2 * p["e"] * p["iz"] / p["l"], k[11, 5]),
        (r"Plano $x$–$z$, $-6 E I_y / L^2$", -6 * p["e"] * p["iy"] / p["l"] ** 2, k[4, 2]),
    ]
    filas = [(que, numero(mano, 6), numero(prog, 6), bool(np.isclose(mano, prog, rtol=1e-12)))
             for que, mano, prog in a_mano]
    filas.append(("Los 144 términos de la tabla de este capítulo contra `k_local` (diferencia mayor, relativa)",
                  "0", numero(float(np.abs(tabla - k).max() / mayor), 2),
                  bool(np.allclose(tabla, k, rtol=1e-12, atol=1e-12 * mayor))))
    filas.append((r"Simetría: $k = k^{\mathsf{T}}$ (diferencia mayor, relativa)", "0",
                  numero(float(np.abs(k - k.T).max() / mayor), 2), bool(np.allclose(k, k.T, rtol=0, atol=1e-12 * mayor))))
    m.comprobacion(filas)

    m.titulo("Los ángulos y la rotación", 3)
    pi, pj, alfa = (0.0, 0.0, 0.0), (3.0, 4.0, 12.0), np.radians(30.0)
    beta, gamma, largo = barra.angulos(pi, pj)
    r = barra.rotacion(alfa, beta, gamma)
    m.parrafo("Barra del origen al punto (3, 4, 12) m, con la sección girada $\\alpha$ = 30°. A mano: "
              "$L = \\sqrt{9 + 16 + 144} = 13$ m; $\\gamma = \\text{atan2}(4, 3)$; "
              "$\\beta = -\\text{atan2}(12, 5)$; y el eje $x$ local es la dirección de la barra, (3, 4, 12)/13.")
    direccion = np.array(pj) / 13.0
    m.comprobacion([
        ("Largo $L$ (m)", "13", numero(largo, 8), bool(np.isclose(largo, 13.0))),
        (r"$\gamma$ (grados)", numero(np.degrees(np.arctan2(4.0, 3.0)), 6), numero(np.degrees(gamma), 6),
         bool(np.isclose(gamma, np.arctan2(4.0, 3.0)))),
        (r"$\beta$ (grados)", numero(-np.degrees(np.arctan2(12.0, 5.0)), 6), numero(np.degrees(beta), 6),
         bool(np.isclose(beta, -np.arctan2(12.0, 5.0)))),
        ("Eje $x$ local (primera fila de $R$)", _vector(direccion), _vector(r[0]), bool(np.allclose(r[0], direccion))),
        (r"Ortogonal: $R R^{\mathsf{T}} = I$ (diferencia mayor)", "0",
         numero(float(np.abs(r @ r.T - np.eye(3)).max()), 2), bool(np.allclose(r @ r.T, np.eye(3), atol=1e-12))),
        ("Sin reflejar: determinante de $R$", "1", numero(float(np.linalg.det(r)), 8),
         bool(np.isclose(np.linalg.det(r), 1.0))),
    ])

    m.parrafo("Ejes locales de las tres barras típicas, con $\\alpha$ = 0. Son las filas de $R$ que da el "
              "programa, y coinciden con lo esperado: en una viga, $z$ local es la vertical; en una columna, "
              "$x$ local es la vertical y $z$ local queda hacia $-X$.")
    tipicas = [("Viga hacia $+X$", (5.0, 0.0, 0.0), ((1, 0, 0), (0, 1, 0), (0, 0, 1))),
               ("Viga hacia $+Y$", (0.0, 4.0, 0.0), ((0, 1, 0), (-1, 0, 0), (0, 0, 1))),
               ("Columna hacia $+Z$", (0.0, 0.0, 3.0), ((0, 0, 1), (0, 1, 0), (-1, 0, 0)))]
    filas = []
    for nombre, punta, esperado in tipicas:
        b_, g_, _l = barra.angulos((0.0, 0.0, 0.0), punta)
        ejes = barra.rotacion(0.0, b_, g_)
        coincide = bool(np.allclose(ejes, np.array(esperado, dtype=float), atol=1e-12))
        if not coincide:
            m.fallas.append(f"Ejes locales: {nombre}")
        filas.append([nombre, _vector(ejes[0]), _vector(ejes[1]), _vector(ejes[2]), "✓" if coincide else "✗"])
    m.tabla(["Barra", "$x$ local", "$y$ local", "$z$ local", ""], filas, anchos_cm=[4.6, 3.5, 3.5, 3.5, 0.8],
            centrar=(1, 2, 3, 4))

    m.titulo("La matriz global: movimiento de cuerpo rígido", 3)
    kg = barra.k_global_barra(p["e"], p["g"], p["a"], p["iy"], p["iz"], p["j"], pi, pj, alfa)
    m.parrafo("Si la barra se mueve entera, sin deformarse, no debe aparecer ninguna fuerza: $K u = 0$. Se "
              "prueba con la barra inclinada anterior y seis movimientos: tres traslaciones y tres giros "
              "alrededor de los ejes globales. En un giro $\\theta$ alrededor del origen, cada nodo se "
              "desplaza $\\theta \\times r$ y gira $\\theta$.")
    filas = []
    for k_eje, eje in enumerate("XYZ"):
        direccion = np.eye(3)[k_eje]
        traslacion = np.concatenate([direccion, np.zeros(3), direccion, np.zeros(3)])
        giro = np.concatenate([np.cross(direccion, pi), direccion, np.cross(direccion, pj), direccion])
        for nombre, u in ((f"Traslación en ${eje}$", traslacion), (f"Giro alrededor de ${eje}$", giro)):
            residuo = float(np.abs(kg @ u).max() / np.abs(kg).max())
            filas.append((f"{nombre}: fuerza mayor / rigidez mayor", "0", numero(residuo, 2), residuo < 1e-12))
    filas.append((r"Simetría: $K = K^{\mathsf{T}}$ (diferencia mayor, relativa)", "0",
                  numero(float(np.abs(kg - kg.T).max() / np.abs(kg).max()), 2),
                  bool(np.allclose(kg, kg.T, rtol=0, atol=1e-12 * np.abs(kg).max()))))
    m.comprobacion(filas)

    m.titulo("Un voladizo, con el programa completo", 3)
    m.parrafo("Voladizo de $L$ = 3 m con $E$ = 200 000 MPa e $I$ = 8·10⁻⁵ m⁴, empotrado en un extremo y con "
              "$P$ = 10 kN en la punta. La solución cerrada es:")
    m.ecuacion(r"\delta = \frac{P L^3}{3 E I} = \frac{10 \cdot 3^3}{3 \cdot 200 \cdot 10^6 \cdot 8 \cdot 10^{-5}} "
               r"= 5.625 \cdot 10^{-3} \text{ m}")
    m.ecuacion(r"\theta = \frac{P L^2}{2 E I} = \frac{10 \cdot 3^2}{2 \cdot 200 \cdot 10^6 \cdot 8 \cdot 10^{-5}} "
               r"= 2.8125 \cdot 10^{-3} \text{ rad}")
    m.parrafo("Se resuelve dos veces con el programa (matriz local, transformación, ensamble y solución): "
              "acostado, como viga en $X$ con la carga hacia $-Z$, y de pie, como columna en $Z$ con la carga "
              "hacia $+X$. La segunda pasa por la transformación: debe dar lo mismo.")
    delta, theta = 10 * 3 ** 3 / (3 * 200e6 * 8e-5), 10 * 3 ** 2 / (2 * 200e6 * 8e-5)
    viga, columna = _voladizo((3, 0, 0), {"fz": -10}), _voladizo((0, 0, 3), {"fx": 10})
    m.comprobacion([
        (r"Viga: $\Delta_z$ de la punta (m)", numero(-delta, 6), numero(viga[2], 6), bool(np.isclose(viga[2], -delta))),
        (r"Viga: giro $\phi_y$ de la punta (rad)", numero(theta, 6), numero(viga[4], 6), bool(np.isclose(viga[4], theta))),
        (r"Columna: $\Delta_x$ de la punta (m)", numero(delta, 6), numero(columna[0], 6),
         bool(np.isclose(columna[0], delta))),
        (r"Columna: giro $\phi_y$ de la punta (rad)", numero(theta, 6), numero(columna[4], 6),
         bool(np.isclose(columna[4], theta))),
    ])

    # ------------------------------------------------------------------ Limitaciones
    m.titulo("Limitaciones", 2)
    m.lista([
        "Análisis elástico lineal de **primer orden**: sin efecto P-Δ ni pandeo.",
        "Sin **deformación por cortante** (importa en vigas cortas y de gran peralte).",
        "Sin **liberaciones** (articulaciones en los extremos de la barra) ni **brazos rígidos**: la barra va de "
        "nodo a nodo y transmite momento en los dos extremos.",
        "Inercia **bruta** de la sección: todavía sin los factores de agrietamiento del ACI 318-19.",
    ])
