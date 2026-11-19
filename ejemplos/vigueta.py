"""Viguetas T continuas sobre apoyos simples (las de "VIGUETAS Y VIGA.sm"): la del salón y la del pasillo.

    python -m ejemplos.vigueta      -> guarda un archivo por cada patrón de carga viva, para abrirlos
                                       con Archivo -> Abrir:
        ejemplos/vigueta salon caso 1.json     viva en los 3 claros            (caso del profesor)
        ejemplos/vigueta salon caso 2.json     viva solo en el claro del medio (caso del profesor)
        ejemplos/vigueta salon caso 3.json     viva en los dos extremos        (caso del profesor)
        ejemplos/vigueta salon caso 4.json     viva en los claros 1 y 2
        ejemplos/vigueta salon caso 5.json     viva en los claros 2 y 3
        ejemplos/vigueta pasillo caso 1.json   viva en los 2 claros
        ejemplos/vigueta pasillo caso 2.json   viva solo en el claro 1
        ejemplos/vigueta pasillo caso 3.json   viva solo en el claro 2
    La muerta (peso propio y adicional) va siempre en todos los claros. Es el patrón de carga viva del
    ACI 318-19 §6.4.2 (PDF p. 75): el M+ máximo de un claro sale con L en ese claro y en los alternos
    (salón 2 y 3; pasillo 2 y 3), y el M− máximo de un apoyo, con L solo en los dos claros vecinos
    (salón 4 y 5; pasillo 1). La flecha máxima de un claro sale con el mismo patrón que su M+ máximo:
    cargar el claro vecino aumenta el negativo del apoyo común y le quita flecha.

Datos (los de la hoja de SMath del usuario y la planta de la tarea):
- concreto f'c = 4000 psi, γ = 2.4 tonf/m³ (23.54 kN/m³);
- sección T: bw 15, h 45, bf 50, hf 10 cm, 1 #6 abajo con d = 45 − 41.19 = 3.81 cm desde abajo, fy 60 ksi;
- viguetas a 0.50 m, en X, con la carga muerta adicional de la hoja (474.30 kgf/m²: baldosas,
  topping y 300 kgf/m² de paredes) × 0.50 m, uniforme hacia −Z; el peso propio (A·γ) lo pone el
  programa en su caso;
- salón: 3 claros entre los ejes B, C, D y E de la planta: 7.60, 7.55 y 7.43 m; viva de aulas,
  40 psf (ASCE 7-05 Tabla 4-1, PDF p. 42);
- pasillo: 2 claros entre los ejes C, D y E: 7.55 y 7.43 m; viva de 100 psf, la de los pasillos del
  primer piso (decisión del usuario, del lado seguro: sobre el primer piso la tabla da 80 psf).

Apoyos: "Apoyo fijo" (Δx, Δy, Δz) en todos los nodos y, solo en el nodo 1, también φx. Sin ese giro
la línea entera podría girar sobre su propio eje (nada lo impide: K sería singular). Como no hay
torsión aplicada, restringirlo no cambia los momentos: siguen siendo los de una viga continua sobre
apoyos simples. Ese nodo sale como apoyo "otro" (no hay un tipo nuevo).
"""
from pathlib import Path

from modelo import Modelo
from modelo import concreto as cc
from modelo.archivo import guardar

PSI = 6.894757293168361        # kN/m² por psi
PSF = 0.04788025898033584      # kN/m² por lb/ft²
KGF = 0.00980665               # kN por kgf

SEPARACION = 0.50              # m entre viguetas (ancho tributario)
MUERTA_ADICIONAL = 474.3022 * KGF * SEPARACION     # baldosas + topping + paredes, kN/m

CLAROS_SALON = (7.60, 7.55, 7.43)                  # m, entre ejes (B–C, C–D y D–E)
VIVA_SALON = 40 * PSF * SEPARACION                 # aulas, 40 psf, kN/m
CLAROS_PASILLO = (7.55, 7.43)                      # m, entre ejes (C–D y D–E)
VIVA_PASILLO = 100 * PSF * SEPARACION              # pasillo, 100 psf, kN/m

# Cada vigueta: sus claros, su viva y, por caso, los claros (1, 2, 3 desde x = 0) que llevan la viva
VIGUETAS = {
    "salon": (CLAROS_SALON, VIVA_SALON, {1: (1, 2, 3), 2: (2,), 3: (1, 3), 4: (1, 2), 5: (2, 3)}),
    "pasillo": (CLAROS_PASILLO, VIVA_PASILLO, {1: (1, 2), 2: (1,), 3: (2,)}),
}


def crear_vigueta(claros=CLAROS_SALON, viva=VIVA_SALON, viva_en=None):
    """Una vigueta continua con esos claros (m) y esa viva (kN/m), puesta solo en los claros de
    viva_en (numerados desde 1 en x = 0; None = en todos)."""
    if viva_en is None:
        viva_en = tuple(range(1, len(claros) + 1))
    m = Modelo()
    concreto = cc.crear_material(m, "", fc=4000 * PSI, gamma=2.4 * 9.80665)
    t = cc.crear_seccion_T(m, concreto, bw=0.15, h=0.45, bf=0.50, hf=0.10, d=0.0381, barra=6, n=1)

    xs = [0.0]
    for largo in claros:
        xs.append(xs[-1] + largo)
    nodos = [m.agregar_nodo(x, 0, 0) for x in xs]
    barras = [m.agregar_elemento(a, b, concreto, t) for a, b in zip(nodos, nodos[1:])]

    for nid in nodos:
        m.restringir(nid, phix=False, phiy=False, phiz=False)       # apoyo fijo
    m.restringir(nodos[0], phix=True, phiy=False, phiz=False)       # y el giro de la línea sobre su eje

    caso_viva = m.caso_viva()                                        # el caso fijo "Carga viva"
    for claro, eid in enumerate(barras, start=1):
        m.agregar_carga_barra(eid, "uniforme", -MUERTA_ADICIONAL, "Z")      # caso inicial: muerta adicional
        if claro in viva_en:
            m.agregar_carga_barra(eid, "uniforme", -viva, "Z", caso=caso_viva)
    return m


if __name__ == "__main__":
    for nombre, (claros, viva, casos) in VIGUETAS.items():
        for numero, viva_en in casos.items():
            ruta = Path(__file__).with_name(f"vigueta {nombre} caso {numero}.json")
            guardar(crear_vigueta(claros, viva, viva_en), ruta)
            print(f"Guardado: {ruta}  (viva en los claros {', '.join(map(str, viva_en))})")
