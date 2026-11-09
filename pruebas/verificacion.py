"""Comprobaciones automáticas del cálculo. Ejecutar desde la carpeta raíz:
    python -m pruebas.verificacion
"""
import numpy as np
from configuracion.formato import configurar
from modelo import Modelo
from modelo.analisis import analizar_caso
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


if __name__ == "__main__":
    from pruebas.integridad import revisar
    configurar()
    verificar_portico()
    verificar_voladizo()
    verificar_inestable()
    print("\n===== INTEGRIDAD DEL CÁLCULO (calculo/) =====")
    revisar()