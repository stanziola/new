"""Materiales y secciones de concreto: lo que se calcula al definirlos (no es el cálculo sagrado).

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
Todo en unidades internas: m y kN/m².
"""
import math

from modelo.estructura import Concreto

PSI = 6.894757293168361      # kN/m² por psi
POISSON = 0.2                # ν del concreto (valor usual; el ACI no lo da)
TOL = 1e-9


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


def _cm(x):
    """Medida en cm, sin decimales de más: 0.2 -> "20", 0.255 -> "25.5"."""
    return f"{round(x * 100, 1):g}"


def nombre_seccion(b, h, nx, ny, barra):
    """Nombre automático, siempre en cm: "Concreto 20x20 Nx5 Ny6 #6"."""
    return f"Concreto {_cm(b)}x{_cm(h)} Nx{nx} Ny{ny} #{barra}"


def nombre_material(fc):
    """Nombre propuesto para un concreto: "Concreto f'c 28 MPa"."""
    return f"Concreto f'c {round(fc / 1000, 1):g} MPa"


def _igual(c, b, h, d, barra, nx, ny):
    return (c is not None and c.forma == "rectangular" and c.barra == barra and c.nx == nx and c.ny == ny
            and all(abs(x - y) < TOL for x, y in ((c.b, b), (c.h, h), (c.d, d))))


def buscar_seccion(modelo, material, b, h, d, barra, nx, ny):
    """ID de una sección rectangular con exactamente esos datos y ese material, o None."""
    for sid, sec in modelo.secciones.items():
        if sec.material == material and _igual(sec.concreto, b, h, d, barra, nx, ny):
            return sid
    return None


def crear_seccion(modelo, material, b, h, d, barra, nx, ny):
    """Crea la sección rectangular de concreto (con nombre y propiedades) y devuelve su ID."""
    mat = modelo.materiales.get(material)
    if mat is None or mat.fc is None:
        raise ValueError("Elige un material de concreto")
    if not 0 < d < min(b, h) / 2:
        raise ValueError("d debe ser positivo y menor que la mitad de b y de h")
    concreto = Concreto(forma="rectangular", fc=mat.fc, d=d, barra=barra, b=b, h=h, nx=nx, ny=ny)
    a, iy, iz, j = propiedades_rectangulo(b, h)
    return modelo.agregar_seccion(nombre_seccion(b, h, nx, ny, barra), a, iy, iz, j, concreto, material)


def buscar_o_crear_seccion(modelo, material, b, h, d, barra, nx, ny):
    """La sección con esos datos: la que ya existe o una nueva. Devuelve (ID, True si es nueva)."""
    sid = buscar_seccion(modelo, material, b, h, d, barra, nx, ny)
    if sid is not None:
        return sid, False
    return crear_seccion(modelo, material, b, h, d, barra, nx, ny), True
