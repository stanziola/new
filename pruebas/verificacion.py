"""Comprobaciones automáticas del cálculo. Ejecutar desde la carpeta raíz:
    python -m pruebas.verificacion
"""
import copy

import numpy as np
from configuracion.formato import configurar
from modelo import Modelo
from modelo.analisis import analizar, analizar_caso, combinar, fuerzas_en, fuerzas_en_x
from modelo.estructura import CargaNodal
from ejemplos.portico import crear_portico
from salida.consola import mostrar, mostrar_resultados


def comprobar(descripcion, condicion):
    print(f"  {'✓' if condicion else '✗'} {descripcion}")


def verificar_portico():
    m = crear_portico()
    mostrar(m, "PÓRTICO DE PRUEBA")
    res = analizar_caso(m, m.caso_inicial()).res

    print("\n===== MATRIZ K GLOBAL =====")
    print("Nodos en orden:", res.ids, "  Tamaño:", res.K.shape)
    mostrar_resultados(m, res)

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


def verificar_voladizo():
    v = Modelo()
    v.agregar_material("Acero", e=200e6, g=77e6)
    v.agregar_seccion("Prueba", a=0.01, iy=8e-5, iz=4e-5, j=1.6e-4)
    v.agregar_nodo(0, 0, 0)
    v.agregar_nodo(3, 0, 0)
    v.agregar_elemento(1, 2, 1, 1)
    v.restringir(1)
    v.cargar(2, fz=-10)

    rv = analizar_caso(v, v.caso_inicial()).res
    dz = rv.desplazamientos[2][2]
    teorico = -10 * 3**3 / (3 * 200e6 * 8e-5)
    comprobar(f"Voladizo: Dz = {dz:.6e}  (teórico P·L³/3EI = {teorico:.6e})", np.isclose(dz, teorico))
    comprobar(f"Voladizo: reacción Fz = {rv.reacciones[1][2]:.3f}  (teórico 10)",
              np.isclose(rv.reacciones[1][2], 10))
    comprobar(f"Voladizo: momento en el empotramiento = {abs(rv.fuerzas[1][4]):.3f}  (teórico P·L = 30)",
              np.isclose(abs(rv.fuerzas[1][4]), 30))


def verificar_inestable():
    print("\n===== ERRORES ESPERADOS =====")
    m = Modelo()
    m.agregar_material("A", 200e6, 77e6)
    m.agregar_seccion("S", 0.01, 8e-5, 4e-5, 1.6e-4)
    m.agregar_nodo(0, 0, 0)
    m.agregar_nodo(3, 0, 0)
    m.agregar_elemento(1, 2, 1, 1)
    m.restringir(1, phix=False, phiy=False, phiz=False)   # solo una articulación
    m.cargar(2, fz=-10)
    try:
        analizar_caso(m, m.caso_inicial())
        comprobar("Estructura inestable detectada", False)
    except ValueError as e:
        comprobar(f"Estructura inestable detectada: {e}", True)


def verificar_combinaciones():
    """Combinaciones por superposición (modelo/analisis.combinar) contra otro método y a mano.

    1. Pórtico con D (peso propio y cargas) y L: 1.2D + 1.6L sumando resultados debe dar lo mismo
       que UN análisis con las cargas ya multiplicadas (y el peso propio × 1.2). Vale porque el
       análisis es lineal (primer orden).
    2. Viga simple de 6 m con D = 10 y L = 5 kN/m (ASCE 7-05 §2.3.2, combinaciones 1 y 2):
       1.2D + 1.6L da w = 20 kN/m → M = wL²/8 = 90 kN·m y V = wL/2 = 60 kN; 1.4D da w = 14."""
    print("\n===== COMBINACIONES (SUPERPOSICIÓN) =====")
    m = crear_portico()
    D = m.caso_inicial()
    L = m.agregar_caso("Viva", "L")
    m.agregar_carga_barra(2, "uniforme", -15.0, "Z", caso=D)
    m.agregar_carga_barra(4, "uniforme", -8.0, "z", caso=L)
    m.agregar_carga_barra(2, "puntual", -12.0, "Z", a=1.5, caso=L)
    m.cargar(5, fy=3.0, mz=2.0, caso=L)
    combo = m.agregar_combinacion("", {D: 1.2, L: 1.6})
    rc = combinar(m, analizar(m), combo)

    directo = copy.deepcopy(m)                 # un solo caso con las cargas ya multiplicadas
    directo.casos[D].peso_propio = 1.2
    for c in directo.cargas.values():
        f = 1.2 if c.caso == D else 1.6
        if isinstance(c, CargaNodal):
            c.fuerzas = [f * v for v in c.fuerzas]
        else:
            c.valor *= f
        c.caso = D
    directo.combinaciones.clear()
    del directo.casos[L]
    rd = analizar_caso(directo, D)
    comprobar(f"{m.combinaciones[combo].nombre}: desplazamientos = análisis directo", np.allclose(rc.res.U, rd.res.U))
    comprobar(f"{m.combinaciones[combo].nombre}: reacciones = análisis directo",
              np.allclose(rc.res.R, rd.res.R, atol=1e-9))
    iguales = all(np.allclose(fuerzas_en(m, rc, e)[k], fuerzas_en(directo, rd, e)[k], atol=1e-9)
                  for e in m.elementos for k in ("N", "Vy", "Vz", "T", "My", "Mz"))
    comprobar(f"{m.combinaciones[combo].nombre}: diagramas de todas las barras = análisis directo", iguales)

    v = Modelo()
    v.agregar_material("A", 200e6, 77e6)                      # γ = 0: sin peso propio
    v.agregar_seccion("S", 0.01, 8e-5, 4e-5, 1.6e-4)
    v.agregar_nodo(0, 0, 0)
    v.agregar_nodo(6, 0, 0)
    v.agregar_elemento(1, 2, 1, 1)
    v.restringir(1, phiy=False, phiz=False)                   # apoyo fijo (con torsión)
    v.restringir(2, dx=False, phix=False, phiy=False, phiz=False)
    Dv, Lv = v.caso_inicial(), v.agregar_caso("Viva", "L")
    v.agregar_carga_barra(1, "uniforme", -10.0, "Z", caso=Dv)
    v.agregar_carga_barra(1, "uniforme", -5.0, "Z", caso=Lv)
    resultados = analizar(v)
    for factores, w in (({Dv: 1.2, Lv: 1.6}, 20.0), ({Dv: 1.4}, 14.0)):
        co = v.agregar_combinacion("", factores)
        r = combinar(v, resultados, co)
        centro, apoyo = fuerzas_en_x(v, r, 1, 3.0), fuerzas_en_x(v, r, 1, 0.0)
        comprobar(f"{v.combinaciones[co].nombre} (w = {w:g} kN/m): M centro = {centro['My']:.3f} (wL²/8 = {w * 4.5:.3f}), "
                  f"V apoyo = {apoyo['Vz']:.3f} (wL/2 = {w * 3:.3f})",
                  np.isclose(centro["My"], w * 4.5) and np.isclose(apoyo["Vz"], w * 3))


if __name__ == "__main__":
    from pruebas.integridad import revisar
    configurar()
    verificar_portico()
    verificar_voladizo()
    verificar_inestable()
    verificar_combinaciones()
    print("\n===== INTEGRIDAD DEL CÁLCULO (calculo/) =====")
    revisar()