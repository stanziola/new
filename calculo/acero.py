"""Fórmulas del acero estructural: módulo de cortante y propiedades de las secciones. SAGRADO.

- G = E / (2·(1 + ν)): mecánica de materiales. E y ν son datos del usuario (AISC 360 no está en
  docs/codigos/; los valores usuales son E = 29 000 ksi ≈ 200 000 MPa y ν = 0.3).
- Peso unitario por defecto: ASCE 7-05, Tabla C3-2 (PDF p. 295), "Steel, cold-drawn": 492 lb/ft³.
  Convertido: 77.29 kN/m³.
- Tubo circular de diámetro exterior D y espesor t (d = D − 2t, el diámetro interior):
    A = π·(D² − d²)/4,  I = π·(D⁴ − d⁴)/64 (igual en los dos ejes),  J = 2·I (sección cerrada circular).
- Perfil I (W) de peralte d, ancho de alas bf, espesor del alma tw y de las alas tf, sin los filetes
  (como Ftool: con los filetes, las tablas del AISC dan un poco más; en la W18x60, A 17.6 contra 17.5 in²
  e I 984 contra 969 in⁴). Convención, la misma del concreto: el peralte d va en el eje local z y las
  alas en el local y. Así, en una viga con α = 0 o en una columna, la inercia fuerte es Iy (flexión en el
  plano x–z):
    A  = 2·bf·tf + (d − 2·tf)·tw
    Iy = [bf·d³ − (bf − tw)·(d − 2·tf)³] / 12                 (eje fuerte)
    Iz = 2·tf·bf³/12 + (d − 2·tf)·tw³/12                       (eje débil)
    J  ≈ [2·bf·tf³ + (d − tf)·tw³] / 3                          (rectángulos delgados, alas y alma
                                                                 entre los centros de las alas)
Todo en unidades internas: m, kN/m² y kN/m³.
"""
import math

LB_FT3 = 0.157087463844          # kN/m³ por lb/ft³ (4.4482216152605 N / 0.3048³ m³)
GAMMA_ACERO = 492 * LB_FT3       # ASCE 7-05 Tabla C3-2, "Steel, cold-drawn": 77.29 kN/m³
POISSON_ACERO = 0.3


def modulo_cortante(e, nu):
    """G = E / (2·(1 + ν)), en las unidades de E."""
    if e <= 0:
        raise ValueError("E debe ser positivo")
    if not 0 <= nu < 0.5:
        raise ValueError("ν debe estar entre 0 y 0.5")
    return e / (2 * (1 + nu))


def propiedades_tubo(D, t):
    """(A, Iy, Iz, J) de un tubo circular de diámetro exterior D y espesor t, en m² y m⁴."""
    if D <= 0 or t <= 0 or 2 * t > D:
        raise ValueError("el tubo necesita D > 0 y 0 < t ≤ D/2")
    d = D - 2 * t
    a = math.pi * (D ** 2 - d ** 2) / 4
    i = math.pi * (D ** 4 - d ** 4) / 64
    return a, i, i, 2 * i


def propiedades_perfil_i(d, bf, tw, tf):
    """(A, Iy, Iz, J) de un perfil I sin filetes (d en z local, alas en y local), en m² y m⁴."""
    if min(d, bf, tw, tf) <= 0 or 2 * tf >= d or tw >= bf:
        raise ValueError("el perfil I necesita medidas positivas, 2·tf < d y tw < bf")
    alma = d - 2 * tf
    a = 2 * bf * tf + alma * tw
    iy = (bf * d ** 3 - (bf - tw) * alma ** 3) / 12
    iz = 2 * tf * bf ** 3 / 12 + alma * tw ** 3 / 12
    j = (2 * bf * tf ** 3 + (d - tf) * tw ** 3) / 3
    return a, iy, iz, j
