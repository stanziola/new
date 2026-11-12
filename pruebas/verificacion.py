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
       los nodos de la barra, que salen de resolver K·U = F (otro camino).
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
            peor = max(peor, float(np.abs(barra - np.asarray(rc.res.desplazamientos[nid][:3])).max()))
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
         servicio: va con 1.6, REP 2021 §8.4). L va con 1.0: no se usa la opción de 0.5L."""
    print("\n===== COMBINACIONES (SUPERPOSICIÓN) =====")
    pre = comb.predeterminadas(0.5, 1.3)
    comprobar(f"ASCE 7-05: 13 combinaciones, más la carga muerta total: {len(pre) - 1}", len(pre) == 14)
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

    # Envolvente de la misma viga: M al centro = 4.5w + 1.5P en cada combinación de la norma.
    # El mayor es 1.2D + 1.6W + L + 0.5Lr (w = 19, P = 16): 109.5. El menor, 0.9D − 1.6W (w = 9,
    # P = −16, el viento hacia arriba): 40.5 − 24 = 16.5. Y la envolvente no queda por debajo de
    # ninguna combinación en ningún punto, ni por encima en el mínimo.
    norma = {k: c for k, c in pre.items() if k != comb.MUERTA}
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
       - 1.2D + 1.6L: Pu = 120 + 80 = 200 kN; M abajo = (12 + 8)·3 = 60 kN·m.
       Solo esas dos se grafican: las demás necesitan Lr, W o E, que no tienen cargas.
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
    comprobar(f"Con D y L se revisan: {', '.join(c.nombre for c in aplican.values())}  (la 1 y la 2)",
              list(aplican) == ["C1", "C2"])
    resultados = analizar(m)
    puntos = demandas_columna(m, {k: combinar(m, resultados, c) for k, c in aplican.items()}, 1)
    esperado = {("C1", "inferior"): (140, 42), ("C1", "superior"): (140, 0),
                ("C2", "inferior"): (200, 60), ("C2", "superior"): (200, 0)}
    comprobar(f"Dos puntos por combinación (inferior y superior): {len(puntos)}", len(puntos) == 4)
    for p in puntos:
        pu, mu = esperado[(p.clave, p.lugar)]
        comprobar(f"{p.combinacion}, {p.lugar}: Pu = {p.p:.3f} (a mano {pu}), |My| = {abs(p.my):.3f} (a mano {mu}), "
                  f"Mz = {p.mz:.1e}", np.isclose(p.p, pu) and np.isclose(abs(p.my), mu, atol=1e-9) and abs(p.mz) < 1e-9)

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


if __name__ == "__main__":
    from pruebas.integridad import revisar
    configurar()
    verificar_portico()
    verificar_voladizo()
    verificar_inestable()
    verificar_peso_propio()
    verificar_desplazamientos_globales()
    verificar_interaccion()
    verificar_combinaciones()
    verificar_demandas()
    print("\n===== INTEGRIDAD DEL CÁLCULO (calculo/) =====")
    revisar()
