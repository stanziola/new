from modelo import Modelo
from modelo import concreto as cc

KSI = 6894.757293168361        # kN/m² por ksi (1 kip/in² = 4.4482216152605 kN / 0.0254² m²)


def crear_portico():
    """Pórtico 3D de prueba: 5 nodos, 4 barras de concreto, un empotramiento y una articulación."""
    m = Modelo()

    # Concreto de f'c = 4 ksi (27.6 MPa): E y G se calculan con el ACI 318-19 (19.2.2.1b) y ν = 0.2
    concreto = cc.crear_material(m, "", fc=4 * KSI)
    # Secciones con refuerzo DE EJEMPLO (para ver el dibujo y el diagrama de interacción), d = 6 cm:
    # viga 30x50 con 6 barras #6 y columna 40x40 con 8 barras #6. Nombre automático.
    viga = cc.crear_seccion(m, concreto, b=0.30, h=0.50, d=0.06, barra=6, nx=3, ny=2)
    columna = cc.crear_seccion(m, concreto, b=0.40, h=0.40, d=0.06, barra=6, nx=3, ny=3)

    # Nodos 1 a 5
    m.agregar_nodo(0, 0, 0)
    m.agregar_nodo(0, 0, 3)
    m.agregar_nodo(5, 0, 3)
    m.agregar_nodo(5, 0, 0)
    m.agregar_nodo(5, 4, 3)

    # Barras (nodo_i, nodo_j, material, sección), algunas dibujadas al revés
    m.agregar_elemento(2, 1, concreto, columna)            # columna, de arriba a abajo
    m.agregar_elemento(3, 2, concreto, viga)               # viga, de derecha a izquierda
    m.agregar_elemento(4, 3, concreto, columna, alfa=90)   # columna girada 90°
    m.agregar_elemento(5, 3, concreto, viga)               # viga en Y, hacia -y

    # Apoyos y cargas
    m.restringir(1)                                       # empotrado
    m.restringir(4, phix=False, phiy=False, phiz=False)   # articulado
    m.cargar(3, fx=10, fz=-20)

    return m
