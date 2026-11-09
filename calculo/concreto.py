"""Fórmulas del concreto: módulos del material y propiedades de la sección rectangular. SAGRADO.

Movidas sin cambios desde modelo/concreto.py (allí quedan los nombres, las familias y las
operaciones sobre el modelo, que no son fórmulas de ingeniería).

- E del concreto: ACI 318-19 §19.2.2.1(b), Ec. 19.2.2.1.b (PDF p. 358), para concreto de peso
  normal: Ec = 57 000·√f'c, con f'c y Ec en psi. Se usa tal cual, convirtiendo unidades: en MPa da
  Ec ≈ 4733·√f'c (el 4700 del ACI 318M es la misma fórmula redondeada).
- ν: el ACI 318-19 no lo da (remite a ensayos ASTM C469). Se usa ν = 0.2, el valor usual, y
  G = E / (2·(1 + ν)), que es mecánica de materiales.
- Sección rectangular con su inercia bruta (sin los modificadores de agrietamiento del ACI).
  Convención: b va en el eje local y de la barra y h en el local z. En una viga con α = 0, z local
  es el vertical global, así que h queda vertical.
    Iy = b·h³/12 (flexión alrededor de y, la que pandea hacia z)
    Iz = h·b³/12
    J  (torsión de Saint-Venant, aproximada; Roark): con a el lado mayor y t el menor,
       J = a·t³·[1/3 − 0.21·(t/a)·(1 − t⁴/(12·a⁴))]
- Peso unitario del concreto reforzado (para el peso propio): ASCE 7-05, Tabla C3-2 (PDF p. 295),
  "Concrete, reinforced — Stone (including gravel)": 150 lb/ft³. Convertido: 23.56 kN/m³.
Todo en unidades internas: m, kN/m² y kN/m³.
"""
import math

PSI = 6.894757293168361      # kN/m² por psi
POISSON = 0.2                # ν del concreto (valor usual; el ACI no lo da)
LB_FT3 = 0.157087463844      # kN/m³ por lb/ft³ (4.4482216152605 N / 0.3048³ m³)
GAMMA_CONCRETO = 150 * LB_FT3    # concreto reforzado, ASCE 7-05 Tabla C3-2: 23.56 kN/m³


def modulos(fc):
    """(E, G) del concreto de peso normal, en kN/m², para f'c en kN/m²."""
    if fc <= 0:
        raise ValueError("f'c debe ser positivo")
    e = 57000.0 * math.sqrt(fc / PSI) * PSI
    return e, e / (2 * (1 + POISSON))


def propiedades_rectangulo(b, h):
    """(A, Iy, Iz, J) de un rectángulo b × h (b en y local, h en z local), en m² y m⁴."""
    if b <= 0 or h <= 0:
        raise ValueError("b y h deben ser positivos")
    a, t = max(b, h), min(b, h)
    j = a * t ** 3 * (1 / 3 - 0.21 * (t / a) * (1 - t ** 4 / (12 * a ** 4)))
    return b * h, b * h ** 3 / 12, h * b ** 3 / 12, j
