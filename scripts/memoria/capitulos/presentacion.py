"""Capítulo 1: Presentación. Para qué es la memoria, qué normas rigen, unidades y convenciones.

Las citas se confirmaron en los PDF de docs/codigos/ (REP 2021, páginas 16, 20, 21 y 100).
"""


def capitulo(m):
    m.titulo("Presentación")
    m.parrafo("Esta memoria reúne las **fórmulas** que usa el programa de análisis y diseño estructural 3D, la "
              "**programación** que las calcula y las **verificaciones** que respaldan sus resultados. Crece con "
              "el programa: cada etapa que se termina agrega aquí sus fórmulas, su código y sus comprobaciones.")

    m.titulo("Para qué sirve", 2)
    m.parrafo("El Reglamento Estructural Panameño (REP 2021) pone condiciones al uso de programas de computadora "
              "en el diseño. Su sección 1.8.2 hace responsable al ingeniero estructural de, entre otras cosas:")
    m.lista([
        "emplear solo programas cuyo funcionamiento y limitaciones son conocidos;",
        "basar sus decisiones solo en programas y datos numéricos cuya validez haya sido verificada;",
        "contar con documentación que describa los métodos analíticos empleados y las limitaciones del programa;",
        "verificar los resultados, analizando el mismo problema con uno o más programas independientes o "
        "mediante métodos aproximados que ofrezcan un orden de magnitud realista.",
    ])
    m.parrafo("Y la sección 1.8.3 pide que la memoria de cálculos estructurales conste de cálculos manuales, datos "
              "de entrada y salida de los programas, dibujos y esquemas. Este documento es la parte que le toca "
              "al programa: dice qué fórmula usa, de dónde sale, cómo está programada y cómo se comprobó.")
    m.parrafo("REP 2021 §1.8.2 y §1.8.3 (PDF p. 20–21).").style = "Cita"

    m.titulo("Normas que aplican", 2)
    m.tabla(["Tema", "Norma", "Dónde lo dice el REP 2021"], [
        ["Todo el diseño estructural", "REP 2021 (manda donde modifica a las demás)", "—"],
        ["Combinaciones de carga", "ASCE/SEI 7-05, capítulo 2", "§1.4.1 (PDF p. 16)"],
        ["Concreto estructural", "ACI 318-19", "§8.1 (PDF p. 100)"],
    ], anchos_cm=[5.0, 6.4, 4.5])
    m.parrafo("Las páginas que se citan en todo el documento son las **del PDF** de cada norma (las que muestra "
              "el visor), que están en `docs/codigos/`; no las impresas en el papel.")

    m.titulo("Unidades", 2)
    m.lista([
        "**Análisis matricial** (capítulo 2): el programa guarda y calcula todo en **kN y m** (E y G en kN/m², "
        "A en m², I y J en m⁴). La interfaz muestra cada magnitud en la unidad que se elija; eso no cambia los "
        "datos.",
        "**Diagramas de interacción** (capítulo 3): las fórmulas trabajan en **pulgadas, ksi y kip**, las "
        "unidades del ACI 318-19, y entregan los resultados en **tonf y tonf·m**. Aquí tonf es la tonelada "
        "métrica de fuerza: 1 tonf = 1000 kgf = 9.80665 kN. El programa las pasa a kN y kN·m antes de "
        "mostrarlas (`modelo/interaccion.py`).",
    ])

    m.titulo("Convenciones", 2)
    m.lista([
        "**Grados de libertad** de cada nodo, en este orden: los desplazamientos $\\Delta_x$, $\\Delta_y$, "
        "$\\Delta_z$ y los giros $\\phi_x$, $\\phi_y$, $\\phi_z$. Una barra tiene dos nodos: 12 grados de "
        "libertad.",
        "**Ejes globales** $X$, $Y$, $Z$: los del modelo; $Z$ es la vertical.",
        "**Ejes locales** $x$, $y$, $z$: los de cada barra. $x$ va a lo largo de la barra, del nodo inicial $i$ "
        "al final $j$; el ancho $b$ de la sección va en $y$ y el alto $h$ en $z$. En una viga horizontal sin "
        "giro de sección, $z$ local es la vertical.",
        "**Signos**: las fuerzas de extremo son las que los nodos ejercen sobre la barra.",
    ])

    m.titulo("Cómo leer este documento", 2)
    m.parrafo("Cada tema sigue el mismo orden: las **hipótesis**; las **fórmulas**, cada una con su cita (norma, "
              "cláusula y página) o con la línea del programa que la calcula; la **programación**, que es el "
              "código vigente del programa, copiado al generar este documento; la **verificación**, donde un "
              "cálculo a mano, hecho por otro camino, se compara con lo que da el programa; y las "
              "**limitaciones**.")
    m.parrafo("El documento **no se edita a mano**: lo genera el propio programa con `python -m scripts.memoria`. "
              "Así el código que muestra es siempre el que corre y los números de las verificaciones se "
              "recalculan cada vez. Si una verificación deja de coincidir, sale marcada con ✗ y el generador "
              "avisa.")

    m.titulo("Alcance de esta versión", 2)
    m.parrafo("Esta versión documenta la matriz de rigidez de la barra y su transformación (capítulo 2) y los "
              "diagramas de interacción de columnas (capítulo 3). Quedan por documentar, aunque el programa ya "
              "las calcula: el ensamble y la solución del sistema, las fuerzas de empotramiento de las cargas en "
              "barras, los diagramas N, V, M y T, las propiedades del concreto y de la sección, el peso propio y "
              "las combinaciones de carga.")
