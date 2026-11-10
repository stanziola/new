"""Comprobaciones automáticas del cálculo. Ejecutar desde la carpeta raíz:
    python -m pruebas.verificacion
"""
import copy

import numpy as np
from configuracion.formato import configurar
from modelo import Modelo
from modelo import combinaciones as comb
from modelo.analisis import analizar, analizar_caso, combinar, fuerzas_en, fuerzas_en_x, peso_propio_total
from modelo.estructura import CargaNodal
from ejemplos.portico import crear_portico
from salida.consola import mostrar, mostrar_resultados


def comprobar(descripcion, condicion):
    print(f"  {'✓' if condicion else '✗'} {descripcion}")


def verificar_portico():
    m = crear_portico()
    mostrar(m, "PÓRTICO DE PRUEBA")
    # La carga muerta total: peso propio (automático) + carga muerta adicional (la carga del nodo 3)
    res = combinar(m, analizar(m), comb.predeterminadas(m.sds, m.rho)[comb.MUERTA]).res

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


def verificar_peso_propio():
    """El peso propio va en su propio caso, automático: A·γ de cada barra, hacia abajo.

    Equilibrio: la suma de las reacciones verticales debe ser el peso de todas las barras, Σ A·γ·L.
    Y la carga muerta total (D) debe ser peso propio + carga muerta adicional."""
    print("\n===== PESO PROPIO Y CARGA MUERTA =====")
    m = crear_portico()
    propio, adicional = [c for c in m.casos if m.es_automatico(c)][0], m.caso_inicial()
    resultados = analizar(m)
    rz = sum(r[2] for r in resultados[propio].res.reacciones.values())
    peso = peso_propio_total(m, propio)
    comprobar(f"Peso propio: ΣRz = {rz:.4f} kN  (Σ A·γ·L = {peso:.4f} kN)", np.isclose(rz, peso))
    muerta = combinar(m, resultados, comb.predeterminadas(m.sds, m.rho)[comb.MUERTA])
    suma = resultados[propio].res.U + resultados[adicional].res.U
    comprobar("Carga muerta (D) = peso propio + carga muerta adicional", np.allclose(muerta.res.U, suma))


def verificar_combinaciones():
    """Combinaciones por superposición (modelo/analisis.combinar) contra otro método, a mano y
    contra la norma (ASCE 7-05 §2.3.2, PDF p. 34, y §12.4.2.3, PDF p. 156).

    1. Factores de la norma: con SDS = 0.5 y ρ = 1.3, la 5 es 1.3D + 1.3E + L (1.2 + 0.2·SDS = 1.3)
       y la 7 es 0.8D + 1.3E (0.9 − 0.2·SDS = 0.8).
    2. Pórtico con peso propio, carga muerta adicional, viva y viento: 1.2D + 1.6L y 1.2D − 1.6W + L
       sumando resultados deben dar lo mismo que UN análisis con todas las cargas ya multiplicadas
       (y el peso propio × 1.2). Vale porque el análisis es lineal (primer orden). El factor de D
       se aplica a los dos casos tipo D.
    3. Viga simple de 6 m con D = 10 y L = 5 kN/m y un viento de servicio de 10 kN al centro:
       - 1.2D + 1.6L: w = 20 kN/m → M = wL²/8 = 90 kN·m y V = wL/2 = 60 kN;
       - 1.4D: w = 14 kN/m → 63 kN·m y 42 kN;
       - 1.2D + 1.6W + L: w = 17 kN/m y P = 1.6·10 = 16 kN → M = 76.5 + PL/4 = 100.5 kN·m y
         V = 51 + P/2 = 59 kN (el viento del REP es de servicio: va con 1.6, REP 2021 §8.4)."""
    print("\n===== COMBINACIONES (SUPERPOSICIÓN) =====")
    pre = comb.predeterminadas(0.5, 1.3)
    comprobar(f"ASCE 7-05: 12 combinaciones, más la carga muerta total: {len(pre) - 1}", len(pre) == 13)
    comprobar(f"5 con SDS = 0.5 y ρ = 1.3: {pre['C5a'].nombre}  (1.2 + 0.2·SDS = 1.3)",
              pre["C5a"].factores == {"D": 1.3, "E": 1.3, "L": 1.0})
    comprobar(f"7 con SDS = 0.5 y ρ = 1.3: {pre['C7a'].nombre}  (0.9 − 0.2·SDS = 0.8)",
              pre["C7a"].factores == {"D": 0.8, "E": 1.3})

    m = crear_portico()
    adicional = m.caso_inicial()
    viva, viento = m.agregar_caso("", "L"), m.agregar_caso("", "W")
    m.agregar_carga_barra(2, "uniforme", -15.0, "Z")
    m.agregar_carga_barra(4, "uniforme", -8.0, "z", caso=viva)
    m.agregar_carga_barra(2, "puntual", -12.0, "Z", a=1.5, caso=viva)
    m.cargar(5, fy=3.0, mz=2.0, caso=viva)
    m.cargar(3, fx=6.0, caso=viento)
    resultados = analizar(m)
    for clave in ("C2", "C4b"):
        co = pre[clave]
        rc = combinar(m, resultados, co)
        directo = copy.deepcopy(m)             # un solo caso con todas las cargas ya multiplicadas
        directo.casos[adicional].peso_propio = co.factores["D"]
        for c in directo.cargas.values():
            f = co.factores.get(m.casos[c.caso].tipo, 0.0)
            if isinstance(c, CargaNodal):
                c.fuerzas = [f * v for v in c.fuerzas]
            else:
                c.valor *= f
            c.caso = adicional
        for cid in [c for c in directo.casos if c != adicional]:
            del directo.casos[cid]
        rd = analizar_caso(directo, adicional)
        iguales = (np.allclose(rc.res.U, rd.res.U) and np.allclose(rc.res.R, rd.res.R, atol=1e-9)
                   and all(np.allclose(fuerzas_en(m, rc, e)[k], fuerzas_en(directo, rd, e)[k], atol=1e-9)
                           for e in m.elementos for k in ("N", "Vy", "Vz", "T", "My", "Mz")))
        comprobar(f"{co.nombre}: desplazamientos, reacciones y diagramas = análisis directo", iguales)

    v = Modelo()
    v.agregar_material("A", 200e6, 77e6)                      # γ = 0: sin peso propio
    v.agregar_seccion("S", 0.01, 8e-5, 4e-5, 1.6e-4)
    v.agregar_nodo(0, 0, 0)
    v.agregar_nodo(6, 0, 0)
    v.agregar_elemento(1, 2, 1, 1)
    v.restringir(1, phiy=False, phiz=False)                   # apoyo fijo (con torsión)
    v.restringir(2, dx=False, phix=False, phiy=False, phiz=False)
    viva, viento = v.agregar_caso("", "L"), v.agregar_caso("", "W")
    v.agregar_carga_barra(1, "uniforme", -10.0, "Z")
    v.agregar_carga_barra(1, "uniforme", -5.0, "Z", caso=viva)
    v.agregar_carga_barra(1, "puntual", -10.0, "Z", a=3.0, caso=viento)
    resultados = analizar(v)
    for clave, w, p in (("C2", 20.0, 0.0), ("C1", 14.0, 0.0), ("C4a", 17.0, 16.0)):
        r = combinar(v, resultados, pre[clave])
        centro, apoyo = fuerzas_en_x(v, r, 1, 3.0), fuerzas_en_x(v, r, 1, 0.0)
        momento, cortante = w * 6 ** 2 / 8 + p * 6 / 4, w * 6 / 2 + p / 2
        comprobar(f"{pre[clave].nombre}: M centro = {centro['My']:.3f} (a mano {momento:.3f}), "
                  f"V apoyo = {apoyo['Vz']:.3f} (a mano {cortante:.3f})",
                  np.isclose(centro["My"], momento) and np.isclose(apoyo["Vz"], cortante))


if __name__ == "__main__":
    from pruebas.integridad import revisar
    configurar()
    verificar_portico()
    verificar_voladizo()
    verificar_inestable()
    verificar_peso_propio()
    verificar_combinaciones()
    print("\n===== INTEGRIDAD DEL CÁLCULO (calculo/) =====")
    revisar()
