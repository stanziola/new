"""Materiales y secciones de acero en el modelo: nombres y operaciones (crear, buscar y cambiar).

Las fórmulas (G, A, I y J) están en calculo/acero.py (sagrado); aquí solo se usan. Es el par de
modelo/concreto.py para el acero. Dos formas de sección:
- tubo circular: D (diámetro exterior) y t (espesor);
- perfil I (W): d (peralte, en el eje local z), bf (ancho de alas, en el local y), tw y tf.
Nombre automático en mm (no depende de las unidades de pantalla): "Tubo 114.3x6.02",
"I 462x192x10.5x17.7". Si el usuario da un nombre (por ejemplo "W18x60"), se usa ese.
Todo en unidades internas: m y kN/m².
"""
from calculo.acero import GAMMA_ACERO, POISSON_ACERO, modulo_cortante, propiedades_perfil_i, propiedades_tubo  # noqa: F401
from modelo.concreto import _positivos, uso_material, uso_seccion
from modelo.estructura import Acero

FAMILIA = "acero"
E_ACERO = 200e6                  # kN/m² (200 000 MPa ≈ 29 000 ksi), valor usual por defecto
FORMAS = {"tubo": "Tubo circular", "i": "Perfil I"}
MEDIDAS = {"tubo": ("D", "t"), "i": ("d", "bf", "tw", "tf")}
TOL = 1e-9


def _mm(x):
    """Medida en mm, sin decimales de más: 0.1143 -> "114.3", 0.00602 -> "6.02"."""
    return f"{round(x * 1000, 2):g}"


def nombre_material(e):
    return f"Acero E {round(e / 1000):g} MPa"


def nombre_seccion(acero):
    """Nombre automático, en mm: "Tubo 114.3x6.02" o "I 462x192x10.5x17.7"."""
    medidas = "x".join(_mm(getattr(acero, m)) for m in MEDIDAS[acero.forma])
    return f"{'Tubo' if acero.forma == 'tubo' else 'I'} {medidas}"


def geometria(forma, **medidas):
    """El Acero con esas medidas (en m), revisado: ValueError si no sirve."""
    if forma not in FORMAS:
        raise ValueError("La forma debe ser tubo o perfil I")
    acero = Acero(forma=forma, **{m: float(medidas[m]) for m in MEDIDAS[forma]})
    propiedades(acero)                      # las fórmulas revisan las medidas
    return acero


def propiedades(acero):
    """(A, Iy, Iz, J) de la sección de acero, de calculo/acero.py."""
    if acero.forma == "tubo":
        return propiedades_tubo(acero.D, acero.t)
    return propiedades_perfil_i(acero.d, acero.bf, acero.tw, acero.tf)


def _igual(a, b):
    return (a is not None and b is not None and a.forma == b.forma
            and all(abs(getattr(a, m) - getattr(b, m)) < TOL for m in MEDIDAS[a.forma]))


def es_de_acero(modelo, mid):
    mat = modelo.materiales.get(mid)
    return mat is not None and getattr(mat, "familia", None) == FAMILIA


# ---------------------------------------------------------------- Materiales
def crear_material(modelo, nombre, e=E_ACERO, nu=POISSON_ACERO, gamma=GAMMA_ACERO):
    """Material de acero: E y ν (G = E/(2(1 + ν))) y su peso unitario. Devuelve el ID."""
    _positivos(E=e)
    g = modulo_cortante(e, nu)
    gamma = 0.0 if gamma is None else gamma
    return modelo.agregar_material(nombre.strip() or nombre_material(e), e, g, gamma=gamma, familia=FAMILIA)


def poisson(mat):
    """ν del material, desde E y G."""
    return mat.e / (2 * mat.g) - 1


def cambiar_material(modelo, mid, nombre, e, nu, gamma=None):
    """Cambia el material de acero en su lugar (todo el modelo lo toma). Devuelve (barras, secciones)."""
    _positivos(E=e)
    mat = modelo.materiales[mid]
    mat.e, mat.g = e, modulo_cortante(e, nu)
    mat.nombre = nombre.strip() or nombre_material(e)
    if gamma is not None:
        mat.gamma = gamma
    return uso_material(modelo, mid)


# ---------------------------------------------------------------- Secciones
def buscar_seccion(modelo, material, acero):
    """ID de una sección de acero con esa geometría y ese material, o None."""
    for sid, sec in modelo.secciones.items():
        if sec.material == material and _igual(getattr(sec, "acero", None), acero):
            return sid
    return None


def crear_seccion(modelo, material, acero, nombre=""):
    """Crea la sección de acero (tubo o perfil I) con sus propiedades y devuelve su ID."""
    if not es_de_acero(modelo, material):
        raise ValueError("Elige un material de acero")
    acero = geometria(acero.forma, **{m: getattr(acero, m) for m in MEDIDAS[acero.forma]})
    a, iy, iz, j = propiedades(acero)
    return modelo.agregar_seccion(nombre.strip() or nombre_seccion(acero), a, iy, iz, j, None, material, acero)


def cambiar_seccion(modelo, sid, material, acero, nombre=""):
    """Cambia una sección de acero en su lugar (todas sus barras la toman, con su material). No puede
    quedar igual a otra. Devuelve las barras que la usan."""
    if not es_de_acero(modelo, material):
        raise ValueError("Elige un material de acero")
    acero = geometria(acero.forma, **{m: getattr(acero, m) for m in MEDIDAS[acero.forma]})
    otra = buscar_seccion(modelo, material, acero)
    if otra is not None and otra != sid:
        raise ValueError(f"Ya existe una sección igual: {modelo.secciones[otra].nombre}")
    sec = modelo.secciones[sid]
    sec.acero, sec.material = acero, material
    sec.nombre = nombre.strip() or nombre_seccion(acero)
    sec.a, sec.iy, sec.iz, sec.j = propiedades(acero)
    barras = uso_seccion(modelo, sid)
    for eid in barras:
        modelo.elementos[eid].material = material
    return barras
