"""Comprobaciones automáticas del cálculo. Ejecutar desde la carpeta raíz:
    python -m pruebas.verificacion
"""
import copy

import numpy as np
from configuracion.formato import configurar
from modelo import Modelo
from modelo import combinaciones as comb
from calculo.rigidez import diagramas
from modelo.analisis import (analizar, analizar_caso, combinar, desplazamientos_globales, envolvente, envolvente_en_x,
                             fuerzas_en, fuerzas_en_x, geometria, peso_propio_total)
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


def verificar_desplazamientos_globales():
    """Desplazamientos a lo largo de una barra en ejes globales (modelo/analisis.desplazamientos_globales):
    los locales (u, v, w) girados con Rᵀ. Es lo que muestran la deformada y el panel Diagrama.

    1. Pórtico (vigas en X y en Y, y columnas): en x = 0 y x = L deben ser los desplazamientos de
       los nodos de la barra, que salen de resolver K·U = F (otro camino). Los dos del análisis con
       la inercia bruta (rc.deformacion), que es de donde sale la deformada.
    2. Voladizo de 3 m en X con P = 10 kN hacia abajo en la punta: a la mitad,
       Dz = −P·x²·(3L − x)/(6EI) = −1.7578 mm, y Dx = Dy = 0.
    3. El mismo voladizo de pie (una columna) con P en +X: a media altura, Dx = +1.7578 mm. Aquí el
       eje local z es −X global: si se confundieran locales y globales, saldría con otro signo."""
    print("\n===== DESPLAZAMIENTOS EN EJES GLOBALES =====")
    m = crear_portico()
    rc = combinar(m, analizar(m), comb.predeterminadas(m.sds, m.rho)[comb.MUERTA])
    peor = 0.0
    for eid, el in m.elementos.items():
        d = desplazamientos_globales(m, rc, eid, x=[0.0, geometria(m, eid)[2]])
        for k, nid in enumerate((el.ni, el.nj)):
            barra = np.array([d["Dx"][k], d["Dy"][k], d["Dz"][k]])
            peor = max(peor, float(np.abs(barra - np.asarray(rc.deformacion.desplazamientos[nid][:3])).max()))
    comprobar(f"Pórtico: en los extremos de cada barra = desplazamientos de los nodos (dif. {peor:.1e})",
              peor < 1e-12)

    teorico = -10 * 1.5 ** 2 * (3 * 3 - 1.5) / (6 * 200e6 * 8e-5)
    for nombre, punta, carga, clave, esperado in (("Voladizo en X", (3, 0, 0), {"fz": -10}, "Dz", teorico),
                                                  ("Columna", (0, 0, 3), {"fx": 10}, "Dx", -teorico)):
        v = Modelo()
        v.agregar_material("Acero", e=200e6, g=77e6)
        v.agregar_seccion("Prueba", a=0.01, iy=8e-5, iz=8e-5, j=1.6e-4)
        v.agregar_nodo(0, 0, 0)
        v.agregar_nodo(*punta)
        v.agregar_elemento(1, 2, 1, 1)
        v.restringir(1)
        v.cargar(2, **carga)
        d = desplazamientos_globales(v, analizar_caso(v, v.caso_inicial()), 1, x=[1.5])
        otros = max(abs(d[k][0]) for k in ("Dx", "Dy", "Dz") if k != clave)
        comprobar(f"{nombre}: {clave} a la mitad = {d[clave][0]:.6e}  (teórico ∓P·x²(3L − x)/6EI = {esperado:.6e})",
                  np.isclose(d[clave][0], esperado) and otros < 1e-12)


def verificar_inercia_agrietada():
    """Dos análisis (modelo/analisis.analizar_caso): el de resistencia con la inercia agrietada de las
    barras de concreto (ACI 318-19 Tabla 6.6.3.1.1(a), PDF p. 78: 0.70·Ig columnas, 0.35·Ig vigas) y
    otro con la bruta Ig, del que sale la deformada.

    1. Los factores: 0.70 y 0.35 (calculo/concreto.factor_inercia).
    2. Columna de concreto en voladizo, 3 m, H = 10 kN en la punta, I = 2.1333e-3 m⁴, E = 25e6 kN/m².
       A mano: con Ig, Δ = H·L³/(3·E·Ig) = 1.6875 mm; con la agrietada, Δ/0.70 = 2.4108 mm. Es
       isostática: el momento en la base es H·L = 30 kN·m en los dos.
    3. Pórtico de concreto (dos columnas de 3 m y una viga de 5 m, empotrado): el de resistencia
       debe ser igual a otro modelo armado a mano con las inercias ya multiplicadas (y sin f'c, para
       que no se vuelvan a reducir), y el de Ig igual al modelo sin reducir. Es hiperestático: los
       momentos cambian con la rigidez de cada barra.
    4. Sin concreto (un material sin f'c, de la familia "Otros") se resuelve una sola vez (bruta = None).
    5. Una combinación lleva también su análisis con Ig, por superposición."""
    from calculo.concreto import factor_inercia

    print("\n===== INERCIA AGRIETADA (ACI 318-19 Tabla 6.6.3.1.1(a)) =====")
    comprobar(f"Factores: columna {factor_inercia(True)}, viga {factor_inercia(False)}",
              factor_inercia(True) == 0.70 and factor_inercia(False) == 0.35)

    e, g, ig = 25e6, 10e6, 2.1333e-3
    v = Modelo()
    v.agregar_material("Concreto", e=e, g=g, fc=27.6e3)
    v.agregar_seccion("Col 40x40", a=0.16, iy=ig, iz=ig, j=3.6e-3)
    v.agregar_nodo(0, 0, 0)
    v.agregar_nodo(0, 0, 3)
    v.agregar_elemento(1, 2, 1, 1)
    v.restringir(1)
    v.cargar(2, fx=10)
    rc = analizar_caso(v, v.caso_inicial())
    bruta, agrietada = rc.deformacion.desplazamientos[2][0], rc.res.desplazamientos[2][0]
    a_mano = 10 * 3 ** 3 / (3 * e * ig)
    comprobar(f"Voladizo: Δ con Ig = {bruta * 1000:.4f} mm (a mano {a_mano * 1000:.4f}); con 0.70·Ig = "
              f"{agrietada * 1000:.4f} mm (a mano {a_mano / 0.70 * 1000:.4f})",
              np.isclose(bruta, a_mano) and np.isclose(agrietada, a_mano / 0.70))
    m_res, m_bruta = rc.res.fuerzas[1][4], rc.bruta.fuerzas[1][4]
    comprobar(f"Voladizo: momento en la base igual en los dos (|My| {abs(m_res):.3f} y {abs(m_bruta):.3f}; "
              f"a mano 30)", np.isclose(abs(m_res), 30) and np.isclose(abs(m_bruta), 30))

    def portico(con_fc, factor_col=1.0, factor_viga=1.0):
        p = Modelo()
        p.agregar_material("Concreto", e=e, g=g, fc=27.6e3 if con_fc else None)
        col = p.agregar_seccion("Col", a=0.16, iy=ig * factor_col, iz=ig * factor_col, j=3.6e-3)
        viga = p.agregar_seccion("Viga", a=0.15, iy=3.125e-3 * factor_viga, iz=1.125e-3 * factor_viga, j=2.8e-3)
        for punto in ((0, 0, 0), (0, 0, 3), (5, 0, 3), (5, 0, 0)):
            p.agregar_nodo(*punto)
        p.agregar_elemento(1, 2, 1, col)
        b = p.agregar_elemento(2, 3, 1, viga)
        p.agregar_elemento(4, 3, 1, col)
        p.restringir(1)
        p.restringir(4)
        p.cargar(2, fx=10)
        p.agregar_carga_barra(b, "uniforme", -20, "Z")
        return p

    real = portico(True)
    rc = analizar_caso(real, real.caso_inicial())
    def caso_inicial(p):
        return analizar_caso(p, p.caso_inicial()).res

    a_mano = caso_inicial(portico(False, 0.70, 0.35))
    sin_reducir = caso_inicial(portico(False))
    iguales = (np.allclose(rc.res.U, a_mano.U, atol=1e-14) and np.allclose(rc.res.R, a_mano.R, atol=1e-9)
               and all(np.allclose(rc.res.fuerzas[k], a_mano.fuerzas[k], atol=1e-9) for k in a_mano.fuerzas))
    comprobar("Pórtico, resistencia = modelo a mano con 0.70·Ig en columnas y 0.35·Ig en la viga (U, R y fuerzas)",
              iguales)
    comprobar("Pórtico, análisis con Ig = modelo sin reducir (U)", np.allclose(rc.bruta.U, sin_reducir.U, atol=1e-14))
    comprobar(f"Pórtico hiperestático: el momento en la base izquierda cambia con la rigidez (|My| con la "
              f"agrietada {abs(rc.res.fuerzas[1][4]):.3f} y con Ig {abs(rc.bruta.fuerzas[1][4]):.3f} kN·m)",
              not np.isclose(rc.res.fuerzas[1][4], rc.bruta.fuerzas[1][4]))

    otro = portico(False)
    comprobar("Sin concreto: un solo análisis (bruta = None)",
              analizar_caso(otro, otro.caso_inicial()).bruta is None)

    resultados = analizar(real)
    rcomb = combinar(real, resultados, comb.predeterminadas(real.sds, real.rho)["C1"])     # 1.4D
    comprobar("Combinación 1.4D: su análisis con Ig = 1.4 × el del caso (U)",
              np.allclose(rcomb.deformacion.U, 1.4 * resultados[real.caso_inicial()].bruta.U, atol=1e-14))


def verificar_interaccion():
    """Correcciones del diagrama de interacción (noviembre de 2026), contra el ACI 318-19:
    - β1 con f'c = 2.5 ksi es 0.85 (Tabla 22.2.2.4.3, PDF p. 401);
    - diámetros nominales de las barras #14 y #18: 1.693 y 2.257 in (Apéndice B, PDF p. 583);
    - fy es un dato: con 40 ksi, Po = 0.85·f'c·(Ag − Ast) + fy·Ast se calcula a mano igual;
    - columna circular (siempre con aros): techo de diseño 0.65·0.80·Po (Tablas 21.2.2 y 22.4.2.1,
      PDF p. 395 y 402);
    - cuantía: 1–8 % y, en pórtico especial, 1–6 % (§10.6.1.1 y §18.7.4.1);
    - unidades: εy = fy/Es no depende de en qué unidad llegue fy (ksi, MPa o kN/m², que es como lo
      manda la interfaz), y el diagrama armado por el puente del modelo (modelo/interaccion.py) es el
      mismo que el calculado directamente en cm y ksi. Es la prueba que faltaba: en noviembre de 2026
      εy salía 14.27 por el camino de la interfaz y el diagrama quedaba inservible."""
    import math
    from calculo.interaccion import circular, rectangular
    from calculo.interaccion.comun import area_barra, beta1, limites_cuantia, propiedades_seccion, ureg
    from modelo import interaccion as puente

    print("\n===== DIAGRAMA DE INTERACCIÓN =====")
    comprobar(f"β1 con f'c = 2.5 ksi: {beta1(2.5 * ureg.ksi)}  (Tabla 22.2.2.4.3: 0.85)",
              beta1(2.5 * ureg.ksi) == 0.85)
    for n, diametro in ((14, 1.693), (18, 2.257)):
        a = area_barra(n).to("inch**2").magnitude
        comprobar(f"Barra #{n}: área {a:.4f} in²  (π·{diametro}²/4 = {math.pi * diametro ** 2 / 4:.4f})",
                  math.isclose(a, math.pi * diametro ** 2 / 4))

    b = h = 16.0                                                  # in
    ast = 8 * math.pi * 0.75 ** 2 / 4                             # 8 barras #6
    sec = propiedades_seccion(b * ureg.inch, h * ureg.inch, 2.5 * ureg.inch, 3, 3, 4 * ureg.ksi, 6, 40 * ureg.ksi)
    _phi, pn, *_ = rectangular.phipnmn(3 * h * ureg.inch, sec)
    po = (0.85 * 4 * (b * h - ast) + 40 * ast) * 0.45359237      # tonf
    comprobar(f"fy = 40 ksi: Po = {pn.magnitude:.3f} tonf  (a mano {po:.3f})", math.isclose(pn.magnitude, po))

    sc = circular.propiedades_circular(20 * ureg.inch, 2.5 * ureg.inch, 8, 4 * ureg.ksi, 8)
    _phi, p_o, _m, phi_p, _pm = circular.phipnmn_circ(60.0, sc)
    comprobar(f"Circular (aros): φPn,max / Po = {phi_p / p_o:.4f}  (esperado 0.65·0.80 = 0.5200)",
              math.isclose(phi_p / p_o, 0.65 * 0.80))
    comprobar(f"Cuantía: {limites_cuantia(False)} y en pórtico especial {limites_cuantia(True)}  (1–8 % y 1–6 %)",
              limites_cuantia(False) == (1.0, 8.0) and limites_cuantia(True) == (1.0, 6.0))

    # εy no depende de la unidad en que llegue fy: 60 ksi = 413.685 MPa = 413 685 kN/m²
    esperado = 60 / 29000
    kn_m2 = ureg.kilonewton / ureg.meter ** 2
    for unidad, fy in (("ksi", 60 * ureg.ksi), ("MPa", 413.6854375901 * ureg.MPa), ("kN/m²", 413685.4375901 * kn_m2)):
        rect = propiedades_seccion(b * ureg.inch, h * ureg.inch, 2.5 * ureg.inch, 3, 3, 4 * ureg.ksi, 6, fy)
        circ = circular.propiedades_circular(20 * ureg.inch, 2.5 * ureg.inch, 8, 4 * ureg.ksi, 8, fy)
        comprobar(f"εy con fy en {unidad}: {rect['epsilon_y']:.7f} y {circ['epsilon_y']:.7f} (circular)  "
                  f"(fy/Es = {esperado:.7f})",
                  math.isclose(rect["epsilon_y"], esperado, rel_tol=1e-9)
                  and math.isclose(circ["epsilon_y"], esperado, rel_tol=1e-9))

    # El diagrama por el camino de la interfaz (Concreto del modelo -> puente) = el directo en cm y ksi
    concreto = next(s.concreto for s in crear_portico().secciones.values()
                    if s.concreto is not None and abs(s.concreto.b - s.concreto.h) < 1e-9)     # la columna 40x40
    por_puente = rectangular.curva(puente.propiedades(concreto))
    directo = rectangular.curva(propiedades_seccion(
        concreto.b * 100 * ureg.cm, concreto.h * 100 * ureg.cm, concreto.d * 100 * ureg.cm, concreto.nx, concreto.ny,
        4 * ureg.ksi, concreto.barra, 60 * ureg.ksi))
    peor = max(float(np.max(np.abs(a - d_))) for a, d_ in zip(por_puente, directo))
    comprobar(f"Columna del ejemplo por el puente del modelo = cálculo directo: Mn máx {por_puente[1].max():.3f} "
              f"y {directo[1].max():.3f} tonf·m (dif. máx {peor:.1e})", peor < 1e-6)


def verificar_combinaciones():
    """Combinaciones por superposición (modelo/analisis.combinar) contra otro método, a mano y
    contra la norma (ASCE 7-05 §2.3.2, PDF p. 34, y §12.4.2.3, PDF p. 156).

    1. Factores de la norma: con SDS = 0.5 y ρ = 1.3, la 5 es 1.3D + 1.3E + L (1.2 + 0.2·SDS = 1.3)
       y la 7 es 0.8D + 1.3E (0.9 − 0.2·SDS = 0.8).
    2. Pórtico con peso propio, carga muerta adicional, viva y viento: 1.2D + 1.6L y 1.2D − 1.6W + L
       sumando resultados deben dar lo mismo que UN análisis con todas las cargas ya multiplicadas
       (y el peso propio × 1.2). Vale porque el análisis es lineal (primer orden). El factor de D
       se aplica a los dos casos tipo D.
    3. Viga simple de 6 m con D = 10, L = 5 y Lr = 4 kN/m y un viento de servicio de 10 kN al centro
       (M = wL²/8 + PL/4 = 4.5w + 1.5P y V = wL/2 + P/2 = 3w + P/2):
       - 1.4D: w = 14 → 63 kN·m y 42 kN;
       - 1.2D + 1.6L + 0.5Lr: w = 12 + 8 + 2 = 22 → 99 kN·m y 66 kN;
       - 1.2D + 1.6Lr + L: w = 12 + 6.4 + 5 = 23.4 → 105.3 kN·m y 70.2 kN;
       - 1.2D + 1.6Lr + 0.8W: w = 18.4 y P = 8 → 94.8 kN·m y 59.2 kN;
       - 1.2D + 1.6W + L + 0.5Lr: w = 19 y P = 16 → 109.5 kN·m y 65 kN (el viento del REP es de
         servicio: va con 1.6, REP 2021 §8.4). L va con 1.0: no se usa la opción de 0.5L.
    4. Las de servicio (ASCE 7-05 Apéndice C, ec. CC-1a, CC-2 y CC-3, PDF p. 413–414), en la misma viga:
       - D + L: w = 15 → 67.5 kN·m y 45 kN;
       - D + 0.5L: w = 12.5 → 56.25 kN·m y 37.5 kN;
       - D + 0.5L + 0.7W: w = 12.5 y P = 7 → 66.75 kN·m y 41 kN.
       No entran en la envolvente ni en los puntos Pu–Mu (comb.aplicables: solo las 13 de resistencia)."""
    print("\n===== COMBINACIONES (SUPERPOSICIÓN) =====")
    pre = comb.predeterminadas(0.5, 1.3)
    norma = comb.resistencia(0.5, 1.3)
    comprobar(f"ASCE 7-05: 13 de resistencia y 4 de servicio, más la carga muerta total: {len(pre) - 1}",
              len(norma) == 13 and len(comb.servicio()) == 4 and len(pre) == 18)
    comprobar(f"3 con L (sin reducir): {pre['C3'].nombre}", pre["C3"].factores == {"D": 1.2, "Lr": 1.6, "L": 1.0})
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
    viva, techo, viento = v.agregar_caso("", "L"), v.agregar_caso("", "Lr"), v.agregar_caso("", "W")
    v.agregar_carga_barra(1, "uniforme", -10.0, "Z")
    v.agregar_carga_barra(1, "uniforme", -5.0, "Z", caso=viva)
    v.agregar_carga_barra(1, "uniforme", -4.0, "Z", caso=techo)
    v.agregar_carga_barra(1, "puntual", -10.0, "Z", a=3.0, caso=viento)
    resultados = analizar(v)
    for clave, w, p in (("C1", 14.0, 0.0), ("C2", 22.0, 0.0), ("C3", 23.4, 0.0), ("C3a", 18.4, 8.0),
                        ("C4a", 19.0, 16.0)):
        r = combinar(v, resultados, pre[clave])
        centro, apoyo = fuerzas_en_x(v, r, 1, 3.0), fuerzas_en_x(v, r, 1, 0.0)
        momento, cortante = w * 6 ** 2 / 8 + p * 6 / 4, w * 6 / 2 + p / 2
        comprobar(f"{pre[clave].nombre}: M centro = {centro['My']:.3f} (a mano {momento:.3f}), "
                  f"V apoyo = {apoyo['Vz']:.3f} (a mano {cortante:.3f})",
                  np.isclose(centro["My"], momento) and np.isclose(apoyo["Vz"], cortante))
    for clave, w, p in (("S1", 15.0, 0.0), ("S2", 12.5, 0.0), ("S3a", 12.5, 7.0)):
        r = combinar(v, resultados, pre[clave])
        centro, apoyo = fuerzas_en_x(v, r, 1, 3.0), fuerzas_en_x(v, r, 1, 0.0)
        momento, cortante = w * 6 ** 2 / 8 + p * 6 / 4, w * 6 / 2 + p / 2
        comprobar(f"{pre[clave].nombre}: M centro = {centro['My']:.3f} (a mano {momento:.3f}), "
                  f"V apoyo = {apoyo['Vz']:.3f} (a mano {cortante:.3f})",
                  np.isclose(centro["My"], momento) and np.isclose(apoyo["Vz"], cortante))
    comprobar("Las de servicio no están entre las aplicables (envolvente y Pu–Mu): solo las 13 de resistencia",
              set(comb.aplicables(v)) == set(norma) and not any(comb.es_servicio(k) for k in comb.aplicables(v)))

    # Envolvente de la misma viga: M al centro = 4.5w + 1.5P en cada combinación de la norma.
    # El mayor es 1.2D + 1.6W + L + 0.5Lr (w = 19, P = 16): 109.5. El menor, 0.9D − 1.6W (w = 9,
    # P = −16, el viento hacia arriba): 40.5 − 24 = 16.5. Y la envolvente no queda por debajo de
    # ninguna combinación en ningún punto, ni por encima en el mínimo.
    env = envolvente(v, resultados, norma)
    vmax, vmin, cmax, cmin = envolvente_en_x(env, 1, "My", 3.0)
    comprobar(f"Envolvente al centro: máx {vmax:.3f} ({cmax}), a mano 109.500 (1.2D + 1.6W + L + 0.5Lr)",
              np.isclose(vmax, 109.5) and cmax == "1.2D + 1.6W + L + 0.5Lr")
    comprobar(f"Envolvente al centro: mín {vmin:.3f} ({cmin}), a mano 16.500 (0.9D - 1.6W)",
              np.isclose(vmin, 16.5) and cmin == "0.9D - 1.6W")
    d = env.barras[1]
    cubre = True
    for co in norma.values():
        rc = combinar(v, resultados, co)
        valores = diagramas.internas(6.0, rc.res.fuerzas[1], rc.cargas_locales.get(1, []), d["x"], d["lado"])
        for k in diagramas.NOMBRES:
            cubre &= bool(np.all(valores[k] <= d[k][0] + 1e-9) and np.all(valores[k] >= d[k][1] - 1e-9))
    comprobar("Envolvente: ninguna combinación se sale del máximo ni del mínimo, en ningún punto", cubre)


def verificar_demandas():
    """Puntos Pu–Mu de una columna para el diagrama de interacción (modelo/analisis.demandas_columna,
    modelo/combinaciones.aplicables y calculo/interaccion/biaxial.curva_direccion).

    1. Columna en voladizo de 3 m (empotrada abajo), sin peso propio. Arriba, D: 100 kN hacia abajo y
       10 kN en +X; L: 50 kN hacia abajo y 5 kN en +X. A mano:
       - 1.4D: Pu = 140 kN en los dos extremos; M abajo = 1.4·10·3 = 42 kN·m y arriba 0;
       - 1.2D + 1.6L: Pu = 120 + 80 = 200 kN; M abajo = (12 + 8)·3 = 60 kN·m;
       - en general, con los factores fD y fL de cada combinación: Pu = 100·fD + 50·fL y
         M abajo = 30·fD + 15·fL (arriba 0).
       Se grafican las 13, aunque Lr, W y E no tengan cargas (valen cero): 0.9D ± 1.6W da Pu = 90 kN
       y M = 27 kN·m, dos veces.
       La fuerza va en X global y el eje local z de una columna es −X: flexiona hacia h, o sea My.
    2. El corte de la superficie en la dirección del momento: en 0° y 90° es la curva de un eje; en
       una sección cuadrada, a 45°, es la curva con θ = 45° (por simetría); y en cualquier dirección
       llega al mismo Po y al mismo techo 0.52·Po (ACI 318-19 Tabla 22.4.2.1, PDF p. 402)."""
    import math
    from calculo.interaccion import biaxial
    from calculo.interaccion.comun import KIP_TF, propiedades_seccion, ureg
    from modelo.analisis import demandas_columna

    print("\n===== PUNTOS Pu–Mu DE UNA COLUMNA =====")
    m = Modelo()
    m.agregar_material("C", e=25e6, g=10e6)
    m.agregar_seccion("S", a=0.16, iy=2.133e-3, iz=2.133e-3, j=3.6e-3)
    m.agregar_nodo(0, 0, 0)
    m.agregar_nodo(0, 0, 3)
    m.agregar_elemento(1, 2, 1, 1)
    m.restringir(1)
    m.cargar(2, fx=10, fz=-100)
    viva = m.agregar_caso("Viva", "L")
    m.cargar(2, fx=5, fz=-50, caso=viva)
    aplican = comb.aplicables(m)
    comprobar(f"Se grafican las 13 combinaciones de la norma, aunque falten Lr, W y E: {len(aplican)}",
              len(aplican) == 13 and comb.MUERTA not in aplican)
    resultados = analizar(m)
    puntos = demandas_columna(m, {k: combinar(m, resultados, c) for k, c in aplican.items()}, 1)
    comprobar(f"Dos puntos por combinación (inferior y superior): {len(puntos)}", len(puntos) == 26)

    def a_mano(p):
        """(Pu, |My|) a mano con los factores de la combinación del punto (lo que no está vale cero)."""
        f = aplican[p.clave].factores
        fd, fl = f.get("D", 0.0), f.get("L", 0.0)
        return 100 * fd + 50 * fl, (30 * fd + 15 * fl) if p.lugar == "inferior" else 0.0

    def igual(p):
        pu, mu = a_mano(p)
        return bool(np.isclose(p.p, pu) and np.isclose(abs(p.my), mu, atol=1e-9) and abs(p.mz) < 1e-9)

    for p in puntos:
        if p.clave in ("C1", "C2", "C6a"):              # a la vista: la 1, la 2 y una sin su carga (W)
            pu, mu = a_mano(p)
            comprobar(f"{p.combinacion}, {p.lugar}: Pu = {p.p:.3f} (a mano {pu:g}), |My| = {abs(p.my):.3f} "
                      f"(a mano {mu:g}), Mz = {p.mz:.1e}", igual(p))
    comprobar("Los 26 puntos: Pu = 100·fD + 50·fL y M abajo = 30·fD + 15·fL (arriba 0), con los factores de "
              "cada combinación", all(igual(p) for p in puntos))

    for nombre, (b, h) in (("40x40", (0.40, 0.40)), ("30x60", (0.30, 0.60))):
        sec = propiedades_seccion(b * ureg.m, h * ureg.m, 0.06 * ureg.m, 3, 4 if h > b else 3, 4 * ureg.ksi, 8)
        for grados in (0, 90) + ((45,) if b == h else ()):
            corte = biaxial.curva_direccion(sec, math.radians(grados))
            curva = biaxial.curva(sec, math.radians(grados), 60)
            dif = max(float(np.abs(np.array(a) - (np.abs(np.array(c)) if i in (1, 3) else np.array(c))).max())
                      for i, (a, c) in enumerate(zip(corte, curva)))      # los momentos, en valor absoluto
            comprobar(f"{nombre}: corte en la dirección {grados}° = curva con θ = {grados}° (dif. máx {dif:.1e})", dif < 1e-6)
        pn, _mn, ppn, _pmn = (np.array(v) for v in biaxial.curva_direccion(sec, math.radians(35)))
        ast = sec["As_total"].to("inch**2").magnitude
        ag = (sec["b"] * sec["h"]).to("inch**2").magnitude
        po = (0.85 * 4 * (ag - ast) + 60 * ast) * KIP_TF
        comprobar(f"{nombre}: corte a 35°, Pn máx = {pn.max():.2f} tonf (Po a mano {po:.2f}) y techo {ppn.max():.2f} "
                  f"(0.52·Po = {0.52 * po:.2f})", np.isclose(pn.max(), po, rtol=0.02) and np.isclose(ppn.max(), 0.52 * po))

    # 3. Por qué el 2D ya no usa la curva con θ: en la 30×60 a 45°, con el mismo φPn, la curva con la
    #    fibra más comprimida hacia θ da más momento que el corte real en esa dirección del momento.
    #    φMn a φPn = 100 tonf, interpolado (φPn crece a lo largo de la curva). sec es la 30×60, la última
    #    del ciclo de arriba.
    _, _, ppn_d, pmn_d = (np.array(v) for v in biaxial.curva_direccion(sec, math.radians(45), 200))
    _, _, ppn_t, pmn_t = (np.array(v) for v in biaxial.curva(sec, math.radians(45), 200))
    m_corte, m_theta = np.interp(100, ppn_d, pmn_d), np.interp(100, ppn_t, np.abs(pmn_t))
    comprobar(f"30x60 a 45°, φPn = 100 tonf: corte real φMn = {m_corte:.2f} y curva con θ = 45° {m_theta:.2f} tonf·m "
              f"(+{(m_theta / m_corte - 1) * 100:.0f} %: la de θ da de más)", m_theta > 1.2 * m_corte)

    # 4. El aviso de puntos fuera (modelo/interaccion.dentro_del_diagrama), contra el corte a 90° de la
    #    30×60: φMn a una altura, interpolado aparte, y puntos a cada lado del borde.
    from modelo.interaccion import dentro_del_diagrama
    _, _, ppn, pmn = (np.array(v) for v in biaxial.curva_direccion(sec, math.radians(90)))
    techo, traccion = ppn.max(), ppn.min()
    m100 = np.interp(100, ppn, pmn)
    casos = (("Pu = 0.1·techo, M = 0", 0.1 * techo, 0.0, True),
             ("Pu = 100 tonf, M = 0.99·φMn", 100, 0.99 * m100, True),
             ("Pu = 100 tonf, M = 1.01·φMn", 100, 1.01 * m100, False),
             ("Pu = 100 tonf, M = 2·φMn", 100, 2 * m100, False),
             ("en el techo, M = 0", techo, 0.0, True),
             ("1 % sobre el techo, M = 0", 1.01 * techo, 0.0, False),
             ("1 % más tracción que la del acero, M = 0", 1.01 * traccion, 0.0, False))
    for texto, pu, mu, esperado in casos:
        dentro = dentro_del_diagrama(ppn, pmn, pu, mu)
        comprobar(f"Aviso, {texto}: {'dentro' if dentro else 'fuera'} (debe quedar {'dentro' if esperado else 'fuera'})",
                  dentro == esperado)


def verificar_seccion_T():
    """Propiedades de la sección T (calculo/concreto.propiedades_T) contra otra forma de calcularlas:
    el rectángulo lleno bf × h menos los dos huecos bajo el ala, (bf − bw) × (h − hf), con las
    inercias tomadas respecto al borde inferior (b·h³/3) y pasadas al centroide (Steiner al revés).
    Vigueta de la hoja del usuario: bw 15, h 45, bf 50, hf 10 cm."""
    from calculo.concreto import propiedades_T
    print("\n===== SECCIÓN T =====")
    bw, h, bf, hf = 0.15, 0.45, 0.50, 0.10
    hueco_b, hueco_h = bf - bw, h - hf
    area = bf * h - hueco_b * hueco_h
    yb = (bf * h ** 2 / 2 - hueco_b * hueco_h ** 2 / 2) / area
    iy = bf * h ** 3 / 3 - hueco_b * hueco_h ** 3 / 3 - area * yb ** 2
    iz = (h * bf ** 3 - hueco_h * (bf ** 3 - bw ** 3)) / 12
    a_t, iy_t, iz_t, j_t, yb_t = propiedades_T(bw, h, bf, hf)
    comprobar(f"A = {a_t * 1e4:.1f} cm² (lleno − huecos: {area * 1e4:.1f})", np.isclose(a_t, area))
    comprobar(f"yb = {yb_t * 100:.3f} cm desde abajo ({yb * 100:.3f})", np.isclose(yb_t, yb))
    comprobar(f"Iy = {iy_t * 1e8:.0f} cm⁴ ({iy * 1e8:.0f}; la hoja de SMath: 187 410)", np.isclose(iy_t, iy))
    comprobar(f"Iz = {iz_t * 1e8:.0f} cm⁴ ({iz * 1e8:.0f})", np.isclose(iz_t, iz))
    comprobar(f"J = {j_t * 1e8:.0f} cm⁴ (suma de ala y alma, positiva)", j_t > 0)
    # Con bf = bw la T es un rectángulo bw × h
    from calculo.concreto import propiedades_rectangulo
    comprobar("T con bf = bw = rectángulo (A, Iy, Iz)",
              np.allclose(propiedades_T(0.3, 0.5, 0.3, 0.1)[:3], propiedades_rectangulo(0.3, 0.5)[:3]))


def verificar_vigueta_continua():
    """Vigueta T del salón, de 3 claros (7.60, 7.55 y 7.43 m), sobre apoyos simples (ejemplos/vigueta.py)
    con 1.2D + 1.6L, contra la ecuación de los tres momentos resuelta aquí:
        M_(i−1)·L_i + 2·M_i·(L_i + L_(i+1)) + M_(i+1)·L_(i+1) = −w·(L_i³ + L_(i+1)³)/4
    con M = 0 en los extremos. Momento positivo de cada claro: con su reacción izquierda
    R = w·L/2 + (M_der − M_izq)/L, M+ = M_izq + R²/(2w). Además, ΣRz = w·ΣL, y la restricción de φx
    del nodo 1 (que evita el giro de la línea sobre su eje) no cambia los momentos. La del pasillo, de
    2 claros (7.55 y 7.43 m, 100 psf): con M = 0 en los extremos la misma ecuación da
    M = −w·(L1³ + L2³) / (8·(L1 + L2)) en el apoyo del medio."""
    from ejemplos.vigueta import (CLAROS_PASILLO, CLAROS_SALON, MUERTA_ADICIONAL, VIVA_PASILLO, VIVA_SALON,
                                  crear_vigueta)
    print("\n===== VIGUETA T CONTINUA, 3 CLAROS =====")
    m = crear_vigueta()
    resultados = analizar(m)
    c2 = comb.todas(m)["C2"]                                   # 1.2D + 1.6L (+ 0.5Lr, que no hay)
    rc = combinar(m, resultados, c2)
    sec, mat = m.secciones[1], m.materiales[1]
    w = 1.2 * (sec.a * mat.gamma + MUERTA_ADICIONAL) + 1.6 * VIVA_SALON
    L = CLAROS_SALON
    a = np.array([[2 * (L[0] + L[1]), L[1]], [L[1], 2 * (L[1] + L[2])]])
    b = -w * np.array([(L[0] ** 3 + L[1] ** 3) / 4, (L[1] ** 3 + L[2] ** 3) / 4])
    mb, mc = np.linalg.solve(a, b)
    apoyos = (0.0, mb, mc, 0.0)
    comprobar(f"wu = 1.2D + 1.6L = {w:.3f} kN/m", w > 0)
    barras = sorted(m.elementos)
    for k, eid in enumerate(barras):
        my = np.asarray(fuerzas_en(m, rc, eid)["My"])
        izq, der = apoyos[k], apoyos[k + 1]
        r = w * L[k] / 2 + (der - izq) / L[k]
        positivo = izq + r ** 2 / (2 * w)
        comprobar(f"Claro {k + 1} ({L[k]} m): M i = {my[0]:.2f}, M j = {my[-1]:.2f}, M+ = {my.max():.2f} kN·m "
                  f"(a mano: {izq:.2f}, {der:.2f}, {positivo:.2f})",
                  np.isclose(my[0], izq, atol=1e-6) and np.isclose(my[-1], der, atol=1e-6)
                  and np.isclose(my.max(), positivo, rtol=1e-3))
    rz = sum(v[2] for v in rc.res.reacciones.values())
    comprobar(f"ΣRz = {rz:.3f} kN (w·ΣL = {w * sum(L):.3f})", np.isclose(rz, w * sum(L)))
    # Con φx restringido en los 4 nodos (en vez de solo el 1) los momentos no cambian
    m2 = crear_vigueta()
    for nid in m2.nodos:
        m2.nodos[nid].apoyo[3] = True
    rc2 = combinar(m2, analizar(m2), comb.todas(m2)["C2"])
    iguales = all(np.allclose(fuerzas_en(m, rc, e)["My"], fuerzas_en(m2, rc2, e)["My"]) for e in barras)
    comprobar("φx en un solo nodo o en los 4: los mismos momentos (no hay torsión aplicada)", iguales)

    p = crear_vigueta(CLAROS_PASILLO, VIVA_PASILLO)
    rp = combinar(p, analizar(p), comb.todas(p)["C2"])
    wp = 1.2 * (sec.a * mat.gamma + MUERTA_ADICIONAL) + 1.6 * VIVA_PASILLO
    l1, l2 = CLAROS_PASILLO
    medio = -wp * (l1 ** 3 + l2 ** 3) / (8 * (l1 + l2))
    mp = np.asarray(fuerzas_en(p, rp, min(p.elementos))["My"])
    comprobar(f"Pasillo, 2 claros, wu = {wp:.3f} kN/m: M en el apoyo del medio = {mp[-1]:.2f} kN·m "
              f"(a mano {medio:.2f})", np.isclose(mp[-1], medio, atol=1e-6))


def verificar_diseno_vigueta():
    """calculo/diseno/viga.py contra la hoja de SMath del usuario (VIGUETAS Y VIGA.sm): vigueta T de
    bw 15, h 45, bf 50, hf 10 cm, f'c 4000 psi, γ 2.4 tonf/m³, recubrimiento 3/4 in, estribo #3, 1 #6
    abajo y 2 #5 arriba. Y el cortante y una T con el bloque en el alma, a mano."""
    from calculo.concreto import PSI, modulos, propiedades_T
    from calculo.diseno import viga as v
    print("\n===== DISEÑO DE LA VIGUETA T (contra el SMath) =====")
    tf, in4 = 9.80665, 0.0254 ** 4                    # kN por tonf; m⁴ por in⁴
    fc, fy = 4000 * PSI, 60000 * PSI
    bw, h, bf, hf = 0.15, 0.45, 0.50, 0.10
    rec, est = 0.75 * 0.0254, v.diametro_barra(3)
    _a, ig, _iz, _j, yb = propiedades_T(bw, h, bf, hf)
    ec = modulos(fc, 2.4 * tf)[0]

    def cerca(valor, smath, tol=5e-5):
        return abs(valor / smath - 1) < tol

    fr, mcr = v.momento_agrietamiento(fc, ig, yb)
    comprobar(f"fr = {fr / PSI:.2f} psi y Mcr+ = {mcr / tf:.4f} tonf·m (SMath 474.34 y 2.1949)",
              cerca(fr / PSI, 474.3416) and cerca(mcr / tf, 2.1949, 1e-4))
    dpos = h - rec - est - v.diametro_barra(6) / 2
    fp = v.flexion(v.area_barra(6), dpos, fc, fy, bf, bw, hf)
    comprobar(f"Positivo: d = {dpos * 100:.2f} cm, c = {fp.c * 100:.4f} cm, εt = {fp.et:.4f}, "
              f"φMn = {fp.phi_mn / tf:.4f} tonf·m (SMath 41.19, 1.1835, 0.1014 y 4.4028)",
              cerca(dpos * 100, 41.19, 1e-4) and cerca(fp.c * 100, 1.1835, 1e-4) and cerca(fp.et, 0.1014, 1e-3)
              and cerca(fp.phi_mn / tf, 4.4028, 1e-4) and fp.phi == 0.9 and not fp.como_t)
    dneg = h - rec - est - v.diametro_barra(5) / 2
    fn = v.flexion(v.area_barra(5, 2), dneg, fc, fy, bw)
    comprobar(f"Negativo: d = {dneg * 100:.4f} cm, c = {fn.c * 100:.4f} cm, εt = {fn.et:.4f}, "
              f"φMn = {fn.phi_mn / tf:.4f} tonf·m (SMath 41.3488, 5.4791, 0.0196 y 5.8645)",
              cerca(dneg * 100, 41.3488) and cerca(fn.c * 100, 5.4791, 1e-4) and cerca(fn.et, 0.0196, 5e-3)
              and cerca(fn.phi_mn / tf, 5.8645, 1e-4))
    comprobar("Las dos controladas por tracción (εt ≥ εty + 0.003, §9.3.3.1)",
              fp.controlada_traccion and fn.controlada_traccion)
    kd, icr = v.inercia_agrietada(v.area_barra(6), dpos, v.ES / ec, bf, bw, hf)
    ie = v.inercia_efectiva(19.19, mcr, ig, icr)
    comprobar(f"Ig = {ig / in4:.2f}, Icr = {icr / in4:.3f} e Ie = {ie / in4:.2f} in⁴ con Ma = 19.19 kN·m "
              f"(SMath 4502.54, 727.458 y 1369.48)",
              cerca(ig / in4, 4502.5386) and cerca(icr / in4, 727.4582) and cerca(ie / in4, 1369.4836))
    comprobar("Ie = Ig si Ma ≤ (2/3)Mcr", v.inercia_efectiva(0.6 * mcr, mcr, ig, icr) == ig)
    comprobar("λΔ = 2 con ξ = 2 (60 meses) y ρ' = 0", v.lambda_delta(v.XI[60]) == 2.0)
    # As,min = 200/fy·bw·d (con 4000 psi manda 200/fy: 3√4000 = 189.7 < 200)
    asmin = v.as_minimo(fc, fy, bw, dpos)
    comprobar(f"As,min = {asmin * 1e4:.3f} cm² (a mano 200/60000·15·41.19 = 2.060)",
              np.isclose(asmin * 1e4, 200 / 60000 * 15 * dpos * 100))
    # Cortante, a mano en lb e in: bw = 5.906 in, d = 16.217 in, As = 0.4418 in², √f'c = 63.246 psi
    bw_in, d_in, as_in = 15 / 2.54, dpos / 0.0254, v.area_barra(6) / 0.0254 ** 2
    va_mano = 2 * 63.2456 * bw_in * d_in * 4.448222e-3                     # kN
    rho_w = as_in / (bw_in * d_in)
    ls = (2 / (1 + d_in / 10)) ** 0.5
    vc_mano = 8 * ls * rho_w ** (1 / 3) * 63.2456 * bw_in * d_in * 4.448222e-3
    va, ea = v.vc(fc, bw, dpos, v.area_barra(6), True)
    vcc, ecc = v.vc(fc, bw, dpos, v.area_barra(6), False)
    comprobar(f"Vc con estribos (a) = {va:.2f} kN y sin estribos (c) = {vcc:.2f} kN, λs = {ls:.4f} "
              f"(a mano {va_mano:.2f} y {vc_mano:.2f})",
              ea == "a" and ecc == "c" and np.isclose(va, va_mano, rtol=1e-4) and np.isclose(vcc, vc_mano, rtol=1e-4))
    # T con el bloque en el alma (losa de 3 cm), a mano: Cf = 0.85f'c(b − bw)hf
    k = 0.85 * fc
    asT, d = v.area_barra(8, 3), 0.40
    cf = k * 0.35 * 0.03
    a = (asT * fy - cf) / (k * 0.15)
    mn = cf * (d - 0.015) + k * 0.15 * a * (d - a / 2)
    ft = v.flexion(asT, d, fc, fy, 0.50, 0.15, 0.03)
    comprobar(f"T con a > hf: a = {ft.a * 100:.3f} cm y Mn = {ft.mn:.2f} kN·m (a mano {a * 100:.3f} y {mn:.2f})",
              ft.como_t and np.isclose(ft.a, a) and np.isclose(ft.mn, mn))
    asr = v.as_requerido(43.64, dpos, fc, fy, bf, bw, hf)
    comprobar(f"As requerido para Mu = 43.64 kN·m: {asr * 1e4:.3f} cm², con φMn = Mu",
              np.isclose(v.flexion(asr, dpos, fc, fy, bf, bw, hf).phi_mn, 43.64, rtol=1e-6))
    # Icr de la T con el eje neutro en el alma, contra la suma de partes hecha aparte
    kdt, icrt = v.inercia_agrietada(asT, d, 8.0, 0.50, 0.15, 0.03)
    resto = 0.50 * 0.03 * (kdt - 0.015) + 0.15 * (kdt - 0.03) ** 2 / 2 - 8.0 * asT * (d - kdt)
    comprobar(f"Icr de la T con kd = {kdt * 100:.2f} cm > hf: momentos estáticos en equilibrio",
              kdt > 0.03 and abs(resto) < 1e-12)
    lim = v.limites_vigueta(bw, h, hf, bf - bw)
    comprobar("Límites de §9.8: 4 in, 3.5·bw, 30 in y max(libre/12, 2 in)",
              np.isclose(lim["ancho_minimo"], 0.1016) and np.isclose(lim["altura_maxima"], 0.525)
              and np.isclose(lim["separacion_maxima"], 0.762) and np.isclose(lim["losa_minima"], 0.0508))
    comprobar("bf efectivo = 50 cm con sw = 35 cm (manda sw/2) y ℓ/18.5 de 7.60 m = 41.08 cm",
              np.isclose(v.ancho_efectivo(bw, hf, 0.35, 7.15), 0.50)
              and np.isclose(v.h_minima(7.60, "un_extremo", fy), 7.60 / 18.5))


def verificar_losa_viguetas():
    """La losa de viguetas de la planta de la tarea (ejemplos/losa_viguetas.py): franjas, casos de viva,
    carga a las vigas (equilibrio), momentos contra la ecuación de los tres momentos, deflexión de un
    claro simple con Ie contra 5wL⁴/384EIe y el archivo (versión 7)."""
    import tempfile
    from pathlib import Path
    from ejemplos.losa_viguetas import MUERTA, VIVA_PASILLO, VIVA_SALON, crear_losa_viguetas
    from calculo.diseno import viga as v
    from modelo import losas as ml
    from modelo.archivo import abrir, guardar
    from modelo.diseno_vigueta import disenar_losa
    print("\n===== LOSA DE VIGUETAS (planta de la tarea, en L) =====")
    m = crear_losa_viguetas()
    r = ml.resumen(m, 1)
    fr = r["franjas"]
    comprobar(f"Dos franjas: {fr[0].nombre} {fr[0].claros} y {fr[1].nombre} {fr[1].claros}",
              len(fr) == 2 and fr[0].claros == [7.60, 7.55, 7.43] and fr[1].claros == [7.55, 7.43])
    comprobar(f"s = 7.30/15 = {r['s'] * 100:.3f} cm y bf = s", np.isclose(r["s"], 7.30 / 15) and np.isclose(r["bf"], r["s"]))
    comprobar("Casos de viva automáticos (§6.4.2): 5 con 3 claros y 3 con 2",
              [c for _n, c in ml.patrones_automaticos(3)] == [(1, 2, 3), (1, 3), (2,), (1, 2), (2, 3)]
              and [c for _n, c in ml.patrones_automaticos(2)] == [(1, 2), (1,), (2,)])
    # Carga a las vigas: lo que llega a las vigas es q × área en cada caso
    cargas = ml.cargas_a_vigas(m)
    area = {pid: (g.u1 - g.u0) * g.claro for pid, g in r["geos"].items()}
    esperado = {2: ml.peso_por_area(m, m.losas[1]) * sum(area.values()), 1: MUERTA * sum(area.values()),
                m.caso_viva_losas(): sum(a * (VIVA_SALON if pid <= 3 else VIVA_PASILLO) for pid, a in area.items())}
    for cid, total in esperado.items():
        llega = sum(w * m.nodos[m.elementos[e].ni].distancia(m.nodos[m.elementos[e].nj]) for e, w in cargas[cid].items())
        comprobar(f"{m.casos[cid].nombre}: a las vigas llegan {llega:.2f} kN = q·área {total:.2f}", np.isclose(llega, total))
    res = analizar(m)
    rz = sum(x[2] for x in res[m.caso_viva_losas()].res.reacciones.values())
    comprobar(f"Viva de losas en el 3D: ΣRz = {rz:.2f} kN = {esperado[m.caso_viva_losas()]:.2f}",
              np.isclose(rz, esperado[m.caso_viva_losas()]))
    # La franja del pasillo con 1.2D + 1.6L: el M del apoyo del medio, con la ecuación de los tres momentos
    sv = ml.sistemas(m, 1)[1]
    sec = next(iter(sv.modelo.secciones.values()))
    mat = next(iter(sv.modelo.materiales.values()))
    wu = 1.2 * (sec.a * mat.gamma + MUERTA * sv.s) + 1.6 * VIVA_PASILLO * sv.s
    l1, l2 = sv.franja.claros
    rs = analizar(sv.modelo)
    rc = combinar(sv.modelo, rs, comb.todas(sv.modelo)["C2"], sv.casos_de((1, 2)))
    medio = fuerzas_en(sv.modelo, rc, 1)["My"][-1]
    comprobar(f"Pasillo, 1.2D + 1.6L: M del apoyo del medio = {medio:.2f} kN·m (a mano "
              f"{-wu * (l1 ** 3 + l2 ** 3) / (8 * (l1 + l2)):.2f})", np.isclose(medio, -wu * (l1 ** 3 + l2 ** 3) / (8 * (l1 + l2))))
    d = disenar_losa(m, 1)
    comprobar(f"Mu+ = {d.mu_pos.valor:.2f}, Mu− = {d.mu_neg.valor:.2f} kN·m y Vu = {d.vu.valor:.2f} kN: mandan en el "
              f"pasillo ({d.mu_pos.franja}, {d.mu_neg.franja})", d.mu_pos.franja.startswith("Franja B")
              and d.mu_neg.franja.startswith("Franja B") and not d.error)

    # Un solo claro (paño de salón B–C solo): Δ(D) con Ie contra 5wL⁴/384EIe
    m1 = crear_losa_viguetas()
    for pid in list(m1.losas[1].panos)[1:]:
        m1.eliminar_pano(pid)
    m1.losas[1].sostenida = 0.0
    d1 = disenar_losa(m1, 1)
    f1 = d1.franjas[0]
    sv1 = f1.sistema
    w = sec.a * mat.gamma + MUERTA * sv1.s
    largo = sv1.franja.claros[0]
    ma = w * largo ** 2 / 8
    ie = v.inercia_efectiva(ma, d1.mcr_pos, d1.ig, d1.icr_pos)
    mano = 5 * w * largo ** 4 / (384 * mat.e * ie)
    from modelo.diseno_vigueta import _deflexiones, niveles
    calc = float(_deflexiones(sv1, f1.ie, d1.ig, niveles(m1.losas[1]))["D"][("", ())][0].max())
    comprobar(f"Claro simple: Ma = wL²/8 = {f1.ma['D'][0]:.2f} kN·m (a mano {ma:.2f}); Δ(D) con Ie = {calc * 1000:.3f} mm "
              f"(5wL⁴/384EIe = {mano * 1000:.3f})", np.isclose(f1.ma["D"][0], ma) and np.isclose(calc, mano, rtol=1e-4))
    # En un claro simple todo es máximo al centro: Δ largo = λΔ·Δ(D) + ΔL, con λΔ = 2 (ξ = 2, ρ' = 0)
    comprobar(f"Con la viva sostenida en 0: Δ largo = 2·Δ(D) + ΔL = {f1.delta_largo[0].valor * 1000:.3f} mm",
              np.isclose(f1.delta_largo[0].valor, 2.0 * calc + f1.delta_l[0].valor, rtol=1e-3))
    # Archivo, versión 7: se guarda y se abre igual
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "losa.json"
        guardar(m, ruta)
        m2, _ = abrir(ruta)
    comprobar("Archivo v7: la losa, sus paños y el caso Viva de losas vuelven iguales",
              m2.losas == m.losas and m2.caso_viva_losas() == m.caso_viva_losas()
              and ml.resumen(m2, 1)["s"] == r["s"])
    # Borrar una viga de apoyo borra sus paños
    m3 = crear_losa_viguetas()
    apoyo = m3.losas[1].panos[4].apoyo_a[0]
    m3.eliminar_elemento(apoyo)
    comprobar(f"Borrar la viga {apoyo} borra los paños que se apoyan en ella (quedan {sorted(m3.losas[1].panos)})",
              all(apoyo not in p.apoyo_a + p.apoyo_b for p in m3.losas[1].panos.values()))


if __name__ == "__main__":
    from pruebas.integridad import revisar
    configurar()
    verificar_portico()
    verificar_voladizo()
    verificar_inestable()
    verificar_peso_propio()
    verificar_desplazamientos_globales()
    verificar_inercia_agrietada()
    verificar_interaccion()
    verificar_combinaciones()
    verificar_demandas()
    verificar_seccion_T()
    verificar_vigueta_continua()
    verificar_diseno_vigueta()
    verificar_losa_viguetas()
    print("\n===== INTEGRIDAD DEL CÁLCULO (calculo/) =====")
    revisar()
