from configuracion import configurar
from calculo.modelo import Modelo

def mostrar(m, titulo):
    print(f"\n===== {titulo} =====")
    print("Materiales:")
    for mid, mat in m.materiales.items():
        print(f"  {mid}: {mat.nombre}  E={mat.e:.3e}  G={mat.g:.3e}")
    print("Secciones:")
    for sid, s in m.secciones.items():
        print(f"  {sid}: {s.nombre}  A={s.a}  Iy={s.iy}  Iz={s.iz}  J={s.j}")
    print("Nodos:")
    for nid, n in m.nodos.items():
        extra = ""
        if any(n.apoyo):
            extra += f"  apoyo={n.apoyo}"
        if any(n.carga):
            extra += f"  carga={n.carga}"
        print(f"  {nid}: {n.coords}{extra}")
    print("Elementos:")
    for eid, el in m.elementos.items():
        print(f"  {eid}: {el.ni} -> {el.nj}  mat={el.material}  sec={el.seccion}  alfa={el.alfa}°")

def probar_error(descripcion, funcion, *args):
    try:
        funcion(*args)
        print(f"  ✗ {descripcion}: NO dio error (debería)")
    except (KeyError, ValueError) as e:
        print(f"  ✓ {descripcion}: {e}")

configurar()
m = Modelo()

# ---------- 1. Materiales y secciones ----------
acero    = m.agregar_material("Acero", e=200e6, g=77e6)
concreto = m.agregar_material("Concreto", e=25e6, g=10e6)
viga     = m.agregar_seccion("Viga 30x50", a=0.15, iy=3.125e-3, iz=1.125e-3, j=2.8e-3)
columna  = m.agregar_seccion("Col 40x40", a=0.16, iy=2.133e-3, iz=2.133e-3, j=3.6e-3)

# ---------- 2. Nodos ----------
n1 = m.agregar_nodo(0, 0, 0)
n2 = m.agregar_nodo(0, 0, 3)
n3 = m.agregar_nodo(5, 0, 3)
n4 = m.agregar_nodo(5, 0, 0)
n5 = m.agregar_nodo(5, 4, 3)

# ---------- 3. Barras dibujadas en sentidos "incorrectos" ----------
c1 = m.agregar_elemento(n2, n1, concreto, columna)            # de arriba a abajo
v1 = m.agregar_elemento(n3, n2, concreto, viga)               # de derecha a izquierda
c2 = m.agregar_elemento(n4, n3, concreto, columna, alfa=90)   # correcta, girada 90°
v2 = m.agregar_elemento(n5, n3, acero, viga)                  # hacia -y

# ---------- 4. Apoyos y cargas ----------
m.restringir(n1)                                          # empotrado
m.restringir(n4, phix=False, phiy=False, phiz=False)      # articulado
m.cargar(n3, fx=10, fz=-20)

mostrar(m, "Modelo de prueba")