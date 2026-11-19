"""La planta de la tarea de viguetas (VIGUETAS Y VIGA.sm) como un piso 3D con su losa de viguetas, en L.

    python -m ejemplos.losa_viguetas     -> guarda ejemplos/losa viguetas.json (ábrelo con Archivo -> Abrir)

La planta (memoria de la tarea, imagen del profesor del 2026-11-18):
- ejes B, C, D y E en X, a 0, 7.60, 15.15 y 22.58 m (claros 7.60, 7.55 y 7.43 m entre ejes);
- 3 salones entre B y E, en una franja de 7.70 m en Y (de y = 0 a 7.70);
- 2 pasillos entre C y E, en una franja de 3.00 m (de y = 7.70 a 10.70). El pasillo B–C no entra: la
  losa queda en L;
- viguetas en X (perpendiculares a las vigas de los ejes B, C, D y E, que son sus apoyos). Las vigas en
  X (y = 0, 7.70 y 10.70) son las laterales de los paños.
Piso a 3.00 m, columnas de 40 × 40 en cada cruce y vigas de 40 × 60 (con 40 cm de ancho, el claro libre
del claro de 7.55 m es 7.15 m, el que midió el usuario entre caras de columnas). El refuerzo de vigas y
columnas es de ejemplo.

La vigueta: T de bw 15, h 45 y hf 10 cm, recubrimiento 3/4 in, estribo #3 (el de la hoja; a 20 cm,
de ejemplo), 1 #6 abajo y 2 #5 arriba, f'c 4000 psi, γ 2.4 tonf/m³. Con el estribo, d+ = 41.19 cm y
d− = 41.35 cm, los de la hoja. 15 viguetas en el salón B–C (el paño de referencia):
s = (7.70 − 0.40)/15 = 48.7 cm, y bf = s.
Cargas: muerta adicional 474.30 kgf/m² (baldosas, topping y 300 kgf/m² de paredes, la de la hoja) en
toda la losa; viva de aulas 40 psf en los salones y 100 psf en los pasillos (la del primer piso,
decisión del usuario).
"""
from pathlib import Path

from modelo import Modelo
from modelo import concreto as cc
from modelo.archivo import guardar

PSI = 6.894757293168361          # kN/m² por psi
PSF = 0.04788025898033584        # kN/m² por lb/ft²
KGF = 0.00980665                 # kN por kgf

EJES_X = {"B": 0.0, "C": 7.60, "D": 15.15, "E": 22.58}
Y_SALON, Y_PASILLO = 7.70, 10.70
ALTURA = 3.0
MUERTA = 474.3022 * KGF          # kN/m²
VIVA_SALON = 40 * PSF
VIVA_PASILLO = 100 * PSF
N_VIGUETAS = 15                  # en el salón B–C


def crear_losa_viguetas(n_viguetas=N_VIGUETAS):
    m = Modelo()
    concreto = cc.crear_material(m, "", fc=4000 * PSI, gamma=2.4 * 9.80665)
    columna = cc.crear_seccion(m, concreto, 0.40, 0.40, 0.06, 6, 3, 3)
    viga = cc.crear_seccion(m, concreto, 0.40, 0.60, 0.06, 6, 3, 2)
    vigueta = cc.crear_seccion_T(m, concreto, 0.15, 0.45, 0.50, 0.10, 0.0, 6, 1, barra_sup=5, n_sup=2,
                                 rec=0.75 * 0.0254, estribo=3, s_estribo=0.20)

    # Cruces de la planta: todos en el salón; en el pasillo, solo de C a E
    cruces = [(eje, y) for eje in EJES_X for y in (0.0, Y_SALON)] + \
             [(eje, Y_PASILLO) for eje in ("C", "D", "E")]
    arriba, abajo = {}, {}
    for eje, y in cruces:
        x = EJES_X[eje]
        abajo[(eje, y)] = m.agregar_nodo(x, y, 0.0)
        arriba[(eje, y)] = m.agregar_nodo(x, y, ALTURA)
        m.agregar_elemento(abajo[(eje, y)], arriba[(eje, y)], concreto, columna)
        m.restringir(abajo[(eje, y)])                                   # empotrado
    # Vigas en Y (los apoyos de las viguetas)
    apoyos = {}
    for eje in EJES_X:
        apoyos[(eje, "salon")] = m.agregar_elemento(arriba[(eje, 0.0)], arriba[(eje, Y_SALON)], concreto, viga)
        if (eje, Y_PASILLO) in arriba:
            apoyos[(eje, "pasillo")] = m.agregar_elemento(arriba[(eje, Y_SALON)], arriba[(eje, Y_PASILLO)],
                                                          concreto, viga)
    # Vigas en X (las laterales)
    ejes = list(EJES_X)
    for y in (0.0, Y_SALON, Y_PASILLO):
        for a, b in zip(ejes, ejes[1:]):
            if (a, y) in arriba and (b, y) in arriba:
                m.agregar_elemento(arriba[(a, y)], arriba[(b, y)], concreto, viga)

    # La losa: el salón B–C primero (es el paño de referencia, con las n viguetas)
    losa = m.agregar_losa("Losa 1", vigueta, n_viguetas)
    for a, b in zip(ejes, ejes[1:]):
        m.agregar_pano(losa, apoyos[(a, "salon")], apoyos[(b, "salon")], MUERTA, VIVA_SALON)
    for a, b in (("C", "D"), ("D", "E")):
        m.agregar_pano(losa, apoyos[(a, "pasillo")], apoyos[(b, "pasillo")], MUERTA, VIVA_PASILLO)
    return m


if __name__ == "__main__":
    ruta = Path(__file__).with_name("losa viguetas.json")
    guardar(crear_losa_viguetas(), ruta)
    print(f"Guardado: {ruta}")
