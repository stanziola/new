from modelo import Concreto, Modelo

KSI = 6894.757293168361        # kN/m² por ksi (1 kip/in² = 4.4482216152605 kN / 0.0254² m²)


def crear_portico():
    """Pórtico 3D de prueba: 5 nodos, 4 barras, un empotramiento y una articulación."""
    m = Modelo()

    # Materiales (1, 2) y secciones (1, 2)
    m.agregar_material("Acero", e=200e6, g=77e6)
    m.agregar_material("Concreto", e=25e6, g=10e6)
    m.agregar_seccion("Viga 30x50", a=0.15, iy=3.125e-3, iz=1.125e-3, j=2.8e-3)
    # Refuerzo DE EJEMPLO (para ver el diagrama de interacción): 8 barras #6, f'c = 4 ksi
    m.agregar_seccion("Col 40x40", a=0.16, iy=2.133e-3, iz=2.133e-3, j=3.6e-3,
                      concreto=Concreto(forma="rectangular", fc=4 * KSI, d=0.06, barra=6,
                                        b=0.40, h=0.40, nx=3, ny=3))

    # Nodos 1 a 5
    m.agregar_nodo(0, 0, 0)
    m.agregar_nodo(0, 0, 3)
    m.agregar_nodo(5, 0, 3)
    m.agregar_nodo(5, 0, 0)
    m.agregar_nodo(5, 4, 3)

    # Barras (nodo_i, nodo_j, material, sección), algunas dibujadas al revés
    m.agregar_elemento(2, 1, 2, 2)            # columna, de arriba a abajo
    m.agregar_elemento(3, 2, 2, 1)            # viga, de derecha a izquierda
    m.agregar_elemento(4, 3, 2, 2, alfa=90)   # columna girada 90°
    m.agregar_elemento(5, 3, 1, 1)            # viga en Y, hacia -y

    # Apoyos y cargas
    m.restringir(1)                                       # empotrado
    m.restringir(4, phix=False, phiy=False, phiz=False)   # articulado
    m.cargar(3, fx=10, fz=-20)

    return m
