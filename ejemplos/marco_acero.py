"""Marco de acero de la tarea (los archivos de Ftool ftool/MUERTA 2.ftl, VIVA 2.ftl, VIENTO 2.ftl y SISMO 2.ftl).

Un marco plano de 18.35 m de luz: columnas W18x60 y una cercha curva de tubos de 4 in (cuerda superior
de 7.99 m a 10.20 m en la clave, cuerda inferior y diagonales), todo con nudos rígidos, como en Ftool.
El plano del marco es el XZ (Z vertical); la (x, y) de Ftool pasa a (X, 0, Z).

Datos de Ftool (leídos de los .ftl):
- acero: E = 2.05e8 kN/m², ν = 0.3 (G = E/2.6) y γ = 77 kN/m³;
- tubo de 4 in: D = 114.3 mm, t = 6.02 mm; W18x60: d = 462, bf = 192, tw = 10.5 y tf = 17.7 mm, con el alma
  en el plano del marco (d en X: inercia fuerte para la flexión del marco);
- casos (cargas uniformes en kN/m, por metro de barra):
  - carga muerta (D): 1.56 hacia abajo en la cuerda superior;
  - viva (L): 3.74 hacia abajo en la cuerda superior;
  - viento (W): 4.36 en la columna izquierda y 1.56 en la derecha, las dos hacia +X; en el techo,
    perpendicular a cada barra: presión de 4.36 en la mitad izquierda (barlovento) y succión de 1.56 en
    la derecha. En Ftool son cargas en ejes locales; aquí van con la dirección local z, que en estas
    barras es la normal hacia arriba del techo. SUPUESTO: en Ftool las barras del techo se dibujaron
    de izquierda a derecha (si no, el signo del techo cambia: revisarlo con el dibujo de Ftool);
  - sismo (E): 8.13 kN hacia +X en el nodo de la columna izquierda a 7.00 m.
- Las coordenadas se redondearon a cm (Ftool guardaba, por ejemplo, −0.00027 y 18.3499): así las
  columnas quedan verticales. La diferencia es menor de 0.5 mm.

Lo que se agrega (no está en Ftool):
- PEDESTAL de concreto bajo cada columna: una barra de 0 a HP, empotrada abajo, y la columna de acero
  arranca arriba (todo el acero sube HP). La unión placa base–pedestal queda rígida (el programa aún no
  tiene articulaciones). 60 × 60 cm con 12 #7 (ρ = 1.3 %) y f'c = 4 ksi: más ancho que el W18x60
  (46 cm) para que quepa la placa. Como es una columna de concreto, tiene su pestaña Interacción con
  los puntos Pu–Mu de las combinaciones;
- el PESO PROPIO (caso automático, A·γ de cada barra): Ftool no lo incluye.
Para comparar con Ftool: crear_marco(pedestal=False, peso_propio=False) es el mismo modelo de los .ftl.

Las combinaciones de ASCE 7-05 salen solas de los tipos de los casos (D, L, W y E).
"""
from modelo import Modelo
from modelo import acero as ac
from modelo import concreto as cc
from modelo.estructura import Acero

KSI = 6894.757293168361          # kN/m² por ksi
HP = 0.80                        # altura del pedestal, m
E_FTOOL, NU_FTOOL, GAMMA_FTOOL = 2.05e8, 0.3, 77.0
TUBO_4IN = Acero(forma="tubo", D=0.1143, t=0.00602)
W18X60 = Acero(forma="i", d=0.462, bf=0.192, tw=0.0105, tf=0.0177)
CARGAS = {"D": -1.56, "L": -3.74}                          # cuerda superior, kN/m en Z global
VIENTO = {"col_izq": 4.36, "col_der": 1.56, "techo_izq": -4.36, "techo_der": 1.56}   # kN/m
SISMO = 8.13                                               # kN en +X
APOYOS = (0, 76)                                           # índices en NODOS: las bases
NODO_SISMO = 1                                             # (0, 7.00)

# Nodos (x, y) de Ftool, en m. Barras: (nodo, nodo, sección, grupo de carga); sección "W" (columna) o
# "T" (tubo); grupo: "col_izq", "col_der", "techo_izq", "techo_der" (la cuerda superior) o "-".
NODOS = [
    (0, 0), (0, 7), (0, 7.81), (0.33, 7.99), (0.44, 7.25),
    (0.8, 8.23), (0.89, 7.49), (1.27, 8.46), (1.34, 7.71), (1.75, 8.68),
    (1.8, 7.93), (2.24, 8.88), (2.26, 8.13), (2.73, 9.06), (2.74, 8.31),
    (3.21, 8.49), (3.23, 9.24), (3.69, 8.65), (3.73, 9.4), (4.18, 8.8),
    (4.24, 9.54), (4.67, 8.93), (4.74, 9.67), (5.16, 9.05), (5.26, 9.79),
    (5.65, 9.15), (5.77, 9.89), (6.15, 9.25), (6.29, 9.98), (6.65, 9.32),
    (6.81, 10.06), (7.15, 9.39), (7.34, 10.11), (7.66, 9.44), (7.86, 10.16),
    (8.16, 9.47), (8.39, 10.19), (8.67, 9.49), (8.91, 10.2), (9.18, 9.5),
    (9.44, 10.2), (9.68, 9.49), (9.96, 10.19), (10.19, 9.47), (10.49, 10.16),
    (10.69, 9.44), (11.01, 10.11), (11.2, 9.39), (11.54, 10.06), (11.7, 9.32),
    (12.06, 9.98), (12.2, 9.25), (12.58, 9.89), (12.7, 9.15), (13.09, 9.79),
    (13.19, 9.05), (13.61, 9.67), (13.69, 8.93), (14.11, 9.54), (14.17, 8.8),
    (14.62, 9.4), (14.66, 8.65), (15.12, 9.24), (15.14, 8.49), (15.61, 8.31),
    (15.62, 9.06), (16.09, 8.13), (16.11, 8.88), (16.55, 7.93), (16.6, 8.68),
    (17.01, 7.71), (17.08, 8.46), (17.46, 7.49), (17.55, 8.23), (17.91, 7.25),
    (18.02, 7.99), (18.35, 0), (18.35, 7), (18.35, 7.81),
]
BARRAS = [
    (0, 1, "W", "col_izq"), (1, 2, "W", "col_izq"), (76, 77, "W", "col_der"), (1, 4, "T", "-"),
    (4, 6, "T", "-"), (3, 4, "T", "-"), (74, 77, "T", "-"), (6, 8, "T", "-"),
    (5, 6, "T", "-"), (72, 74, "T", "-"), (72, 75, "T", "-"), (7, 8, "T", "-"),
    (70, 72, "T", "-"), (70, 73, "T", "-"), (2, 4, "T", "-"), (2, 3, "T", "techo_izq"),
    (77, 78, "W", "col_der"), (74, 78, "T", "-"), (8, 10, "T", "-"), (10, 12, "T", "-"),
    (9, 10, "T", "-"), (68, 70, "T", "-"), (68, 71, "T", "-"), (3, 6, "T", "-"),
    (3, 5, "T", "techo_izq"), (74, 75, "T", "-"), (75, 78, "T", "techo_der"), (12, 14, "T", "-"),
    (11, 12, "T", "-"), (66, 68, "T", "-"), (66, 69, "T", "-"), (5, 8, "T", "-"),
    (5, 7, "T", "techo_izq"), (72, 73, "T", "-"), (73, 75, "T", "techo_der"), (14, 15, "T", "-"),
    (13, 14, "T", "-"), (64, 66, "T", "-"), (64, 67, "T", "-"), (7, 10, "T", "-"),
    (7, 9, "T", "techo_izq"), (70, 71, "T", "-"), (71, 73, "T", "techo_der"), (15, 17, "T", "-"),
    (15, 16, "T", "-"), (63, 64, "T", "-"), (63, 65, "T", "-"), (17, 19, "T", "-"),
    (17, 18, "T", "-"), (61, 63, "T", "-"), (61, 62, "T", "-"), (9, 12, "T", "-"),
    (9, 11, "T", "techo_izq"), (68, 69, "T", "-"), (69, 71, "T", "techo_der"), (19, 21, "T", "-"),
    (19, 20, "T", "-"), (59, 61, "T", "-"), (59, 60, "T", "-"), (11, 14, "T", "-"),
    (11, 13, "T", "techo_izq"), (66, 67, "T", "-"), (67, 69, "T", "techo_der"), (21, 23, "T", "-"),
    (21, 22, "T", "-"), (57, 59, "T", "-"), (57, 58, "T", "-"), (23, 25, "T", "-"),
    (23, 24, "T", "-"), (55, 57, "T", "-"), (55, 56, "T", "-"), (13, 15, "T", "-"),
    (13, 16, "T", "techo_izq"), (64, 65, "T", "-"), (65, 67, "T", "techo_der"), (25, 27, "T", "-"),
    (25, 26, "T", "-"), (53, 55, "T", "-"), (53, 54, "T", "-"), (16, 17, "T", "-"),
    (16, 18, "T", "techo_izq"), (62, 63, "T", "-"), (62, 65, "T", "techo_der"), (27, 29, "T", "-"),
    (27, 28, "T", "-"), (51, 53, "T", "-"), (51, 52, "T", "-"), (29, 31, "T", "-"),
    (29, 30, "T", "-"), (49, 51, "T", "-"), (49, 50, "T", "-"), (31, 33, "T", "-"),
    (31, 32, "T", "-"), (47, 49, "T", "-"), (47, 48, "T", "-"), (18, 19, "T", "-"),
    (18, 20, "T", "techo_izq"), (60, 61, "T", "-"), (60, 62, "T", "techo_der"), (33, 35, "T", "-"),
    (33, 34, "T", "-"), (45, 47, "T", "-"), (45, 46, "T", "-"), (35, 37, "T", "-"),
    (35, 36, "T", "-"), (43, 45, "T", "-"), (43, 44, "T", "-"), (37, 39, "T", "-"),
    (37, 38, "T", "-"), (41, 43, "T", "-"), (41, 42, "T", "-"), (39, 41, "T", "-"),
    (39, 40, "T", "-"), (20, 21, "T", "-"), (20, 22, "T", "techo_izq"), (58, 59, "T", "-"),
    (58, 60, "T", "techo_der"), (22, 23, "T", "-"), (22, 24, "T", "techo_izq"), (56, 57, "T", "-"),
    (56, 58, "T", "techo_der"), (24, 25, "T", "-"), (24, 26, "T", "techo_izq"), (54, 55, "T", "-"),
    (54, 56, "T", "techo_der"), (26, 27, "T", "-"), (26, 28, "T", "techo_izq"), (52, 53, "T", "-"),
    (52, 54, "T", "techo_der"), (28, 29, "T", "-"), (28, 30, "T", "techo_izq"), (50, 51, "T", "-"),
    (50, 52, "T", "techo_der"), (30, 31, "T", "-"), (30, 32, "T", "techo_izq"), (48, 49, "T", "-"),
    (48, 50, "T", "techo_der"), (32, 33, "T", "-"), (32, 34, "T", "techo_izq"), (46, 47, "T", "-"),
    (46, 48, "T", "techo_der"), (34, 35, "T", "-"), (34, 36, "T", "techo_izq"), (44, 45, "T", "-"),
    (44, 46, "T", "techo_der"), (36, 37, "T", "-"), (36, 38, "T", "techo_izq"), (42, 43, "T", "-"),
    (42, 44, "T", "techo_der"), (38, 39, "T", "-"), (38, 40, "T", "techo_izq"), (40, 41, "T", "-"),
    (40, 42, "T", "techo_der"),
]


def crear_marco(pedestal=True, peso_propio=True):
    """El marco de la tarea. pedestal: con los pedestales de concreto (si no, empotrado en la base,
    como en Ftool). peso_propio: γ de los materiales (si no, γ = 0: sin peso propio, como en Ftool)."""
    m = Modelo()
    acero = ac.crear_material(m, "Acero (Ftool)", E_FTOOL, NU_FTOOL, GAMMA_FTOOL if peso_propio else 0.0)
    tubo = ac.crear_seccion(m, acero, TUBO_4IN, "Tubo 4 in")
    columna = ac.crear_seccion(m, acero, W18X60, "W18x60")
    z0 = HP if pedestal else 0.0
    ids = [m.agregar_nodo(x, 0.0, y + z0) for x, y in NODOS]

    casos = {"D": m.caso_inicial(), "L": m.agregar_caso("Viva", "L"), "W": m.agregar_caso("Viento", "W"),
             "E": m.agregar_caso("Sismo", "E")}
    for a, b, seccion, grupo in BARRAS:
        eid = m.agregar_elemento(ids[a], ids[b], acero, columna if seccion == "W" else tubo)
        if grupo.startswith("techo"):
            for tipo, valor in CARGAS.items():
                m.agregar_carga_barra(eid, "uniforme", valor, "Z", caso=casos[tipo])
            m.agregar_carga_barra(eid, "uniforme", VIENTO[grupo], "z", caso=casos["W"])
        elif grupo.startswith("col"):
            m.agregar_carga_barra(eid, "uniforme", VIENTO[grupo], "X", caso=casos["W"])
    m.cargar(ids[NODO_SISMO], fx=SISMO, caso=casos["E"])

    if pedestal:
        concreto = cc.crear_material(m, "", fc=4 * KSI, gamma=None if peso_propio else 0.0)
        ped = cc.crear_seccion(m, concreto, b=0.60, h=0.60, d=0.06, barra=7, nx=4, ny=4)
        for k in APOYOS:
            x, _y, _z = m.nodos[ids[k]].coords
            base = m.agregar_nodo(x, 0.0, 0.0)
            m.agregar_elemento(base, ids[k], concreto, ped)
            m.restringir(base)
    else:
        for k in APOYOS:
            m.restringir(ids[k])
    return m
