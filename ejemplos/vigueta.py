"""Vigueta T continua de 3 claros sobre apoyos simples (la de "VIGUETAS Y VIGA.sm").

    python -m ejemplos.vigueta      -> guarda los 3 casos de carga viva del profesor, para abrirlos
                                       con Archivo -> Abrir:
        ejemplos/vigueta caso 1.json   viva en los 3 claros
        ejemplos/vigueta caso 2.json   viva solo en el claro del medio
        ejemplos/vigueta caso 3.json   viva solo en los claros de los extremos
    La muerta (peso propio y adicional) va siempre en los 3 claros. Es el patrón de carga viva del
    ACI 318-19 §6.4.2 (PDF p. 75): el M+ máximo de un claro sale con L en ese claro y en los alternos.

Datos (los de la hoja de SMath del usuario):
- concreto f'c = 4000 psi, γ = 2.4 tonf/m³ (23.54 kN/m³);
- sección T: bw 15, h 45, bf 50, hf 10 cm, 1 #6 abajo con d = 45 − 41.19 = 3.81 cm desde abajo, fy 60 ksi;
- claros de 7.65, 7.55 y 7.60 m, en X;
- viguetas a 0.50 m: carga muerta adicional 474.30 kgf/m² × 0.50 m y viva 40 psf × 0.50 m, uniformes
  hacia −Z; el peso propio (A·γ) lo pone el programa en su caso.

Apoyos: "Apoyo fijo" (Δx, Δy, Δz) en los 4 nodos y, solo en el nodo 1, también φx. Sin ese giro la
línea entera podría girar sobre su propio eje (nada lo impide: K sería singular). Como no hay torsión
aplicada, restringirlo no cambia los momentos: siguen siendo los de una viga continua sobre apoyos
simples. Ese nodo sale como apoyo "otro" (no hay un tipo nuevo).
"""
from pathlib import Path

from modelo import Modelo
from modelo import concreto as cc
from modelo.archivo import guardar

PSI = 6.894757293168361        # kN/m² por psi
PSF = 0.04788025898033584      # kN/m² por lb/ft²
KGF = 0.00980665               # kN por kgf

CLAROS = (7.65, 7.55, 7.60)    # m
SEPARACION = 0.50              # m entre viguetas (ancho tributario)
MUERTA_ADICIONAL = 474.3022 * KGF * SEPARACION     # baldosas + topping + paredes, kN/m
VIVA = 40 * PSF * SEPARACION                       # 40 psf, kN/m


# Claros (1, 2, 3) que llevan la carga viva en cada caso del profesor
CASOS_VIVA = {1: (1, 2, 3), 2: (2,), 3: (1, 3)}


def crear_vigueta(viva_en=(1, 2, 3)):
    """La vigueta, con la carga viva solo en los claros de viva_en (numerados 1, 2 y 3 desde x = 0)."""
    m = Modelo()
    concreto = cc.crear_material(m, "", fc=4000 * PSI, gamma=2.4 * 9.80665)
    t = cc.crear_seccion_T(m, concreto, bw=0.15, h=0.45, bf=0.50, hf=0.10, d=0.0381, barra=6, n=1)

    xs = [0.0]
    for largo in CLAROS:
        xs.append(xs[-1] + largo)
    nodos = [m.agregar_nodo(x, 0, 0) for x in xs]
    barras = [m.agregar_elemento(a, b, concreto, t) for a, b in zip(nodos, nodos[1:])]

    for nid in nodos:
        m.restringir(nid, phix=False, phiy=False, phiz=False)       # apoyo fijo
    m.restringir(nodos[0], phix=True, phiy=False, phiz=False)       # y el giro de la línea sobre su eje

    viva = m.agregar_caso("Viva", "L")
    for claro, eid in enumerate(barras, start=1):
        m.agregar_carga_barra(eid, "uniforme", -MUERTA_ADICIONAL, "Z")      # caso inicial: muerta adicional
        if claro in viva_en:
            m.agregar_carga_barra(eid, "uniforme", -VIVA, "Z", caso=viva)
    return m


if __name__ == "__main__":
    for numero, claros in CASOS_VIVA.items():
        ruta = Path(__file__).with_name(f"vigueta caso {numero}.json")
        guardar(crear_vigueta(claros), ruta)
        print(f"Guardado: {ruta}  (viva en los claros {', '.join(map(str, claros))})")
