"""Fórmulas del concreto: módulos del material y propiedades de la sección rectangular. SAGRADO.

Movidas sin cambios desde modelo/concreto.py (allí quedan los nombres, las familias y las
operaciones sobre el modelo, que no son fórmulas de ingeniería).

- E del concreto: ACI 318-19 §19.2.2.1(a), Ec. 19.2.2.1.a (PDF p. 358): Ec = wc^1.5·33·√f'c, con
  wc en lb/ft³ (entre 90 y 160), f'c y Ec en psi. wc es el peso unitario γ del material (el mismo
  del peso propio; el de por defecto, 150 lb/ft³, incluye el acero, así que da un Ec ~3 % mayor que
  con el concreto simple de 145). Con wc ≈ 144 da lo mismo que la (b), 57 000·√f'c. Si γ queda fuera
  de 90–160 lb/ft³ (por ejemplo γ = 0, sin peso propio), se usa la (b), la de concreto de peso
  normal. Se usan tal cual, convirtiendo unidades (en MPa la (b) da Ec ≈ 4733·√f'c).
- ν: el ACI 318-19 no lo da (remite a ensayos ASTM C469). Se usa ν = 0.2, el valor usual, y
  G = E / (2·(1 + ν)), que es mecánica de materiales.
- Sección rectangular con su inercia bruta Ig. Los factores de agrietamiento no se aplican aquí sino
  en el análisis (modelo/analisis.py), con factor_inercia. Convención: b va en el eje local y de la barra y h en el local z. En una viga con α = 0, z local
  es el vertical global, así que h queda vertical.
    Iy = b·h³/12 (flexión alrededor de y, la que pandea hacia z)
    Iz = h·b³/12
    J  (torsión de Saint-Venant, aproximada; Roark): con a el lado mayor y t el menor,
       J = a·t³·[1/3 − 0.21·(t/a)·(1 − t⁴/(12·a⁴))]
- Sección T (vigas y viguetas con su losa): alma bw × (h − hf) y ala bf × hf arriba. A, centroide yb
  e Iy con Steiner respecto al centroide real; Iz de las dos partes; J como suma de las J de Roark
  del ala y del alma (aproximada). El ancho bf lo da el usuario (ACI 318-19 Tabla 6.3.2.1, PDF p. 74).
- Peso unitario del concreto reforzado (para el peso propio): ASCE 7-05, Tabla C3-2 (PDF p. 295),
  "Concrete, reinforced — Stone (including gravel)": 150 lb/ft³. Convertido: 23.56 kN/m³.
- Inercia para el análisis elástico con cargas mayoradas: ACI 318-19 §6.6.3.1.1, Tabla 6.6.3.1.1(a)
  (PDF p. 78): columnas 0.70·Ig y vigas 0.35·Ig. El área queda 1.0·Ag (misma tabla). J no está en la
  tabla y no se cambia. Si hay cargas laterales sostenidas, la I de las columnas se divide además
  entre (1 + βds): no se aplica (el programa no tiene cargas laterales sostenidas). Son valores
  fijos de la norma, no de presentación.
Todo en unidades internas: m, kN/m² y kN/m³.
"""
import math

PSI = 6.894757293168361      # kN/m² por psi
POISSON = 0.2                # ν del concreto (valor usual; el ACI no lo da)
LB_FT3 = 0.157087463844      # kN/m³ por lb/ft³ (4.4482216152605 N / 0.3048³ m³)
GAMMA_CONCRETO = 150 * LB_FT3    # concreto reforzado, ASCE 7-05 Tabla C3-2: 23.56 kN/m³
INERCIA_COLUMNA = 0.70       # I = 0.70·Ig en columnas, ACI 318-19 Tabla 6.6.3.1.1(a)
INERCIA_VIGA = 0.35          # I = 0.35·Ig en vigas, misma tabla


WC_MIN, WC_MAX = 90.0, 160.0    # lb/ft³: rango de la Ec. 19.2.2.1.a


def modulos(fc, gamma=GAMMA_CONCRETO):
    """(E, G) del concreto, en kN/m², para f'c en kN/m² y su peso unitario γ en kN/m³: E con la
    Ec. 19.2.2.1.a (wc = γ en lb/ft³) o, si wc queda fuera de 90–160 lb/ft³, con la 19.2.2.1.b."""
    if fc <= 0:
        raise ValueError("f'c debe ser positivo")
    wc = gamma / LB_FT3
    if WC_MIN <= wc <= WC_MAX:
        e = wc ** 1.5 * 33.0 * math.sqrt(fc / PSI) * PSI
    else:
        e = 57000.0 * math.sqrt(fc / PSI) * PSI
    return e, e / (2 * (1 + POISSON))


def propiedades_rectangulo(b, h):
    """(A, Iy, Iz, J) de un rectángulo b × h (b en y local, h en z local), en m² y m⁴."""
    if b <= 0 or h <= 0:
        raise ValueError("b y h deben ser positivos")
    a, t = max(b, h), min(b, h)
    j = a * t ** 3 * (1 / 3 - 0.21 * (t / a) * (1 - t ** 4 / (12 * a ** 4)))
    return b * h, b * h ** 3 / 12, h * b ** 3 / 12, j


def propiedades_T(bw, h, bf, hf):
    """(A, Iy, Iz, J, yb) de una sección T: alma bw × (h − hf) y ala bf × hf arriba (bw y bf en y
    local, h en z local, el ala hacia +z). En m² y m⁴; yb es la altura del centroide desde abajo.

    Iy (flexión en el plano x-z, la vertical de una viga con α = 0) se toma respecto al centroide
    real (Steiner con las dos partes). Iz: las dos partes comparten el eje vertical de simetría.
    J: suma de la J de Roark de cada rectángulo (ala bf × hf y alma bw × (h − hf)), la aproximación
    usual de una sección abierta formada por rectángulos; no cuenta el refuerzo de la unión."""
    if bw <= 0 or h <= 0 or bf <= 0 or hf <= 0:
        raise ValueError("bw, h, bf y hf deben ser positivos")
    if bf < bw:
        raise ValueError("bf debe ser mayor o igual que bw")
    if hf >= h:
        raise ValueError("hf debe ser menor que h")
    hw = h - hf
    a_alma, a_ala = bw * hw, bf * hf
    area = a_alma + a_ala
    yb = (a_alma * hw / 2 + a_ala * (hw + hf / 2)) / area
    iy = (bw * hw ** 3 / 12 + a_alma * (yb - hw / 2) ** 2
          + bf * hf ** 3 / 12 + a_ala * (hw + hf / 2 - yb) ** 2)
    iz = hf * bf ** 3 / 12 + hw * bw ** 3 / 12
    j = propiedades_rectangulo(bf, hf)[3] + propiedades_rectangulo(bw, hw)[3]
    return area, iy, iz, j, yb


def factor_inercia(es_columna):
    """Factor que multiplica Iy e Iz brutas de una barra de concreto en el análisis con cargas
    mayoradas (ACI 318-19 Tabla 6.6.3.1.1(a), PDF p. 78): 0.70 en columnas y 0.35 en vigas."""
    return INERCIA_COLUMNA if es_columna else INERCIA_VIGA
