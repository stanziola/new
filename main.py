import numpy as np
import pandas as pd
from configuracion import configurar, GDL, FUERZAS, FUERZAS_LOCALES
from calculo.modelo import Modelo
from calculo.analisis import resolver
from herramientas import ver

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

def mostrar_resultados(m, res):
    print("\n===== DESPLAZAMIENTOS =====")
    print(pd.DataFrame(res.desplazamientos, index=GDL).T)

    print("\n===== REACCIONES =====")
    print(pd.DataFrame(res.reacciones, index=FUERZAS).T)

    print("\n===== FUERZAS EN EXTREMOS DE BARRAS (ejes locales) =====")
    filas, etiquetas = [], []
    for eid, f in res.fuerzas.items():
        el = m.elementos[eid]
        filas += [f[:6], f[6:]]
        etiquetas += [f"Barra {eid} nodo {el.ni}", f"Barra {eid} nodo {el.nj}"]
    print(pd.DataFrame(filas, index=etiquetas, columns=FUERZAS_LOCALES))

def comprobar(descripcion, condicion):
    print(f"  {'✓' if condicion else '✗'} {descripcion}")

configurar()
m = Modelo()

# ---------- 1. Materiales y secciones ----------
m.agregar_material("Acero", e=200e6, g=77e6)
m.agregar_material("Concreto", e=25e6, g=10e6)
m.agregar_seccion("Viga 30x50", a=0.15, iy=3.125e-3, iz=1.125e-3, j=2.8e-3)
m.agregar_seccion("Col 40x40", a=0.16, iy=2.133e-3, iz=2.133e-3, j=3.6e-3)

# ---------- 2. Nodos ----------
m.agregar_nodo(0, 0, 0)
m.agregar_nodo(0, 0, 3)
m.agregar_nodo(5, 0, 3)
m.agregar_nodo(5, 0, 0)
m.agregar_nodo(5, 4, 3)

# ---------- 3. Barras dibujadas en sentidos "incorrectos" ----------
m.agregar_elemento(2, 1, 2, 2)            # de arriba a abajo
m.agregar_elemento(3, 2, 2, 1)               # de derecha a izquierda
m.agregar_elemento(4, 3, 2, 2, alfa=90)   # correcta, girada 90°
m.agregar_elemento(5, 3, 1, 1)                  # hacia -y

# ---------- 4. Apoyos y cargas ----------
m.restringir(1)                                          # empotrado
m.restringir(4, phix=False, phiy=False, phiz=False)      # articulado
m.cargar(3, fx=10, fz=-20)

mostrar(m, "Modelo de prueba")

# ---------- 5. Resolver ----------
res = resolver(m)

print("\n===== MATRIZ K GLOBAL =====")
print("Nodos en orden:", res.ids, "  Tamaño:", res.K.shape)
ver(res.K, nodos=res.ids)

mostrar_resultados(m, res)

# ---------- 6. Comprobaciones automáticas ----------
print("\n===== COMPROBACIONES =====")
K, F, R = res.K, res.F, res.R

# K simétrica
comprobar("K es simétrica", np.allclose(K, K.T))

# Traslación rígida: mover todo en bloque no genera fuerzas
for nombre, d in [("X", 0), ("Y", 1), ("Z", 2)]:
    u_rigido = np.zeros(K.shape[0])
    u_rigido[d::6] = 1.0
    comprobar(f"Traslación rígida en {nombre} no genera fuerzas",
              np.allclose(K @ u_rigido, 0, atol=1e-6 * np.abs(K).max()))

# Equilibrio global de fuerzas y de momentos (respecto al origen)
total = (F + R).reshape(-1, 6)
coords = np.array([m.nodos[nid].coords for nid in res.ids], dtype=float)
suma_f = total[:, :3].sum(axis=0)
suma_m = total[:, 3:].sum(axis=0) + np.cross(coords, total[:, :3]).sum(axis=0)
comprobar(f"Equilibrio de fuerzas  ΣF = {np.round(suma_f, 8)}", np.allclose(suma_f, 0, atol=1e-8))
comprobar(f"Equilibrio de momentos ΣM = {np.round(suma_m, 8)}", np.allclose(suma_m, 0, atol=1e-8))

# ---------- 7. Voladizo: comparar con fórmulas de libro ----------
v = Modelo()
v.agregar_material("Acero", e=200e6, g=77e6)
v.agregar_seccion("Prueba", a=0.01, iy=8e-5, iz=4e-5, j=1.6e-4)
v.agregar_nodo(0, 0, 0)
v.agregar_nodo(3, 0, 0)
v.agregar_elemento(1, 2, 1, 1)
v.restringir(1)
v.cargar(2, fz=-10)

rv = resolver(v)
dz = rv.desplazamientos[2][2]
teorico = -10 * 3**3 / (3 * 200e6 * 8e-5)
comprobar(f"Voladizo: Dz = {dz:.6e}  (teórico P·L³/3EI = {teorico:.6e})", np.isclose(dz, teorico))
comprobar(f"Voladizo: reacción Fz = {rv.reacciones[1][2]:.3f}  (teórico 10)",
          np.isclose(rv.reacciones[1][2], 10))
comprobar(f"Voladizo: momento en el empotramiento = {abs(rv.fuerzas[1][4]):.3f}  (teórico P·L = 30)",
          np.isclose(abs(rv.fuerzas[1][4]), 30))

# ---------- 8. Estructura inestable: debe dar un error claro ----------
print("\n===== ERRORES ESPERADOS =====")
inestable = Modelo()
inestable.agregar_material("A", 200e6, 77e6)
inestable.agregar_seccion("S", 0.01, 8e-5, 4e-5, 1.6e-4)
inestable.agregar_nodo(0, 0, 0)
inestable.agregar_nodo(3, 0, 0)
inestable.agregar_elemento(1, 2, 1, 1)
inestable.restringir(1, phix=False, phiy=False, phiz=False)   # solo una articulación
inestable.cargar(2, fz=-10)
try:
    resolver(inestable)
    comprobar("Estructura inestable detectada", False)
except ValueError as e:
    comprobar(f"Estructura inestable detectada: {e}", True)