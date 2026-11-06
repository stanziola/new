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
ver(res.K, nodos=res.ids, archivo="K_global.csv")

mostrar_resultados(m, res)


