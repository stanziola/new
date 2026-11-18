"""Materiales y secciones de concreto en el modelo: nombres, familias y operaciones.

Las fórmulas (Ec, G, A, I y J) están en calculo/concreto.py (sagrado); aquí solo se usan. Este
módulo arma, busca y cambia materiales y secciones del modelo.
Todo en unidades internas: m y kN/m².
"""
from calculo.concreto import (GAMMA_CONCRETO, POISSON, PSI, modulos, propiedades_rectangulo,   # noqa: F401
                              propiedades_T)
from modelo.estructura import FY_DEFECTO, Concreto

TOL = 1e-9


def _cm(x):
    """Medida en cm, sin decimales de más: 0.2 -> "20", 0.255 -> "25.5"."""
    return f"{round(x * 100, 1):g}"


def nombre_seccion(b, h, nx, ny, barra, fy=FY_DEFECTO):
    """Nombre automático, siempre en cm y MPa: "Concreto 20x20 Nx5 Ny6 #6". Si el acero no es el de
    Grado 60, se agrega su fy: "Concreto 20x20 Nx5 Ny6 #6 fy 276 MPa"."""
    nombre = f"Concreto {_cm(b)}x{_cm(h)} Nx{nx} Ny{ny} #{barra}"
    return nombre if abs(fy - FY_DEFECTO) < 1e-6 * FY_DEFECTO else f"{nombre} fy {round(fy / 1000):g} MPa"


def nombre_material(fc):
    """Nombre propuesto para un concreto: "Concreto f'c 28 MPa"."""
    return f"Concreto f'c {round(fc / 1000, 1):g} MPa"


def _igual(c, b, h, d, barra, nx, ny, fy):
    return (c is not None and c.forma == "rectangular" and c.barra == barra and c.nx == nx and c.ny == ny
            and all(abs(x - y) < TOL for x, y in ((c.b, b), (c.h, h), (c.d, d)))
            and abs(c.fy - fy) < 1e-6 * fy)


def buscar_seccion(modelo, material, b, h, d, barra, nx, ny, fy=FY_DEFECTO):
    """ID de una sección rectangular con exactamente esos datos y ese material, o None."""
    for sid, sec in modelo.secciones.items():
        if sec.material == material and _igual(sec.concreto, b, h, d, barra, nx, ny, fy):
            return sid
    return None


def crear_seccion(modelo, material, b, h, d, barra, nx, ny, fy=FY_DEFECTO):
    """Crea la sección rectangular de concreto (con nombre y propiedades) y devuelve su ID."""
    mat = modelo.materiales.get(material)
    if mat is None or mat.fc is None:
        raise ValueError("Elige un material de concreto")
    if not 0 < d < min(b, h) / 2:
        raise ValueError("d debe ser positivo y menor que la mitad de b y de h")
    _positivos(fy=fy)
    concreto = Concreto(forma="rectangular", fc=mat.fc, d=d, barra=barra, b=b, h=h, nx=nx, ny=ny, fy=fy)
    a, iy, iz, j = propiedades_rectangulo(b, h)
    return modelo.agregar_seccion(nombre_seccion(b, h, nx, ny, barra, fy), a, iy, iz, j, concreto, material)


def buscar_o_crear_seccion(modelo, material, b, h, d, barra, nx, ny, fy=FY_DEFECTO):
    """La sección con esos datos: la que ya existe o una nueva. Devuelve (ID, True si es nueva)."""
    sid = buscar_seccion(modelo, material, b, h, d, barra, nx, ny, fy)
    if sid is not None:
        return sid, False
    return crear_seccion(modelo, material, b, h, d, barra, nx, ny, fy), True


# ---------------------------------------------------------------- Sección T (vigas y viguetas)
# Se guarda en un Concreto con forma "T": b es el ancho del alma (bw), h la altura total, bf y hf el
# ala, nx las barras de abajo en el alma (ny = 1) y d, del borde inferior al centro de las barras.
def nombre_seccion_T(bw, h, bf, hf, n, barra, fy=FY_DEFECTO):
    """Nombre automático, siempre en cm y MPa: "Concreto T 15x45 bf50 hf10 1#6"."""
    nombre = f"Concreto T {_cm(bw)}x{_cm(h)} bf{_cm(bf)} hf{_cm(hf)} {n}#{barra}"
    return nombre if abs(fy - FY_DEFECTO) < 1e-6 * FY_DEFECTO else f"{nombre} fy {round(fy / 1000):g} MPa"


def concreto_T(fc, bw, h, bf, hf, d, barra, n, fy=FY_DEFECTO):
    """El Concreto de una T (sin validar)."""
    return Concreto(forma="T", fc=fc, d=d, barra=barra, b=bw, h=h, nx=n, ny=1, fy=fy, bf=bf, hf=hf)


def _validar_T(modelo, material, bw, h, bf, hf, d, n, fy):
    mat = modelo.materiales.get(material)
    if mat is None or mat.fc is None:
        raise ValueError("Elige un material de concreto")
    propiedades_T(bw, h, bf, hf)                     # revisa las medidas (bf ≥ bw, hf < h)
    if not 0 < d < min(bw / 2, h - hf):
        raise ValueError("d debe ser positivo y menor que bw/2 y que la altura del alma (h − hf)")
    if n < 1:
        raise ValueError("Pon al menos una barra abajo")
    _positivos(fy=fy)
    return mat


def _igual_T(c, bw, h, bf, hf, d, barra, n, fy):
    return (c is not None and c.forma == "T" and c.barra == barra and c.nx == n
            and all(abs(x - y) < TOL for x, y in ((c.b, bw), (c.h, h), (c.bf, bf), (c.hf, hf), (c.d, d)))
            and abs(c.fy - fy) < 1e-6 * fy)


def buscar_seccion_T(modelo, material, bw, h, bf, hf, d, barra, n, fy=FY_DEFECTO):
    """ID de una sección T con exactamente esos datos y ese material, o None."""
    for sid, sec in modelo.secciones.items():
        if sec.material == material and _igual_T(sec.concreto, bw, h, bf, hf, d, barra, n, fy):
            return sid
    return None


def crear_seccion_T(modelo, material, bw, h, bf, hf, d, barra, n, fy=FY_DEFECTO):
    """Crea la sección T de concreto (con nombre y propiedades) y devuelve su ID."""
    mat = _validar_T(modelo, material, bw, h, bf, hf, d, n, fy)
    a, iy, iz, j, _ = propiedades_T(bw, h, bf, hf)
    return modelo.agregar_seccion(nombre_seccion_T(bw, h, bf, hf, n, barra, fy), a, iy, iz, j,
                                  concreto_T(mat.fc, bw, h, bf, hf, d, barra, n, fy), material)


def cambiar_seccion_T(modelo, sid, material, bw, h, bf, hf, d, barra, n, fy=FY_DEFECTO):
    """Cambia una sección en su lugar por una T (todas sus barras la toman, con su material).
    Devuelve las barras que la usan."""
    mat = _validar_T(modelo, material, bw, h, bf, hf, d, n, fy)
    otra = buscar_seccion_T(modelo, material, bw, h, bf, hf, d, barra, n, fy)
    if otra is not None and otra != sid:
        raise ValueError(f"Ya existe una sección igual: {modelo.secciones[otra].nombre}")
    sec = modelo.secciones[sid]
    sec.concreto = concreto_T(mat.fc, bw, h, bf, hf, d, barra, n, fy)
    sec.material = material
    sec.nombre = nombre_seccion_T(bw, h, bf, hf, n, barra, fy)
    sec.a, sec.iy, sec.iz, sec.j, _ = propiedades_T(bw, h, bf, hf)
    barras = uso_seccion(modelo, sid)
    for eid in barras:
        modelo.elementos[eid].material = material
    return barras


def centroide(c):
    """Altura del centroide desde el borde inferior de la sección (m): h/2, o el yb de la T."""
    return propiedades_T(c.b, c.h, c.bf, c.hf)[4] if c.forma == "T" else c.h / 2


def contorno(c):
    """Contorno de la sección en ejes locales (y, z), en m, con el centroide en el origen y el ala de
    la T hacia +z: lista de vértices en orden antihorario. Rectángulo de b × h o T."""
    if c.forma == "T":
        yb = centroide(c)
        abajo, alma, arriba = -yb, c.h - c.hf - yb, c.h - yb
        w, f = c.b / 2, c.bf / 2
        return [(-w, abajo), (w, abajo), (w, alma), (f, alma), (f, arriba), (-f, arriba), (-f, alma), (-w, alma)]
    return [(-c.b / 2, -c.h / 2), (c.b / 2, -c.h / 2), (c.b / 2, c.h / 2), (-c.b / 2, c.h / 2)]


# ---------------------------------------------------------------- Familias, uso y cambios
# Las carpetas de Definir: solo concreto (el programa es de concreto armado; el acero estructural quedó
# en la copia "utp"). Los materiales sin f'c y las secciones sin refuerzo (de archivos viejos, también
# los de acero, o del código) van a "Otros", que solo aparece si hay alguno.
FAMILIAS = {"concreto": "Concreto"}
NOMBRE_OTROS = "Otros"


def nombre_familia(familia):
    return FAMILIAS.get(familia, NOMBRE_OTROS)


def familia_material(mat):
    """"concreto" si se definió por f'c; "otros" si se dieron E y G directamente (viejos)."""
    return "concreto" if mat.fc is not None else "otros"


def familia_seccion(sec):
    """"concreto" si tiene geometría y refuerzo; "otros" si se dieron A, I y J directamente (viejas)."""
    return "concreto" if sec.concreto is not None else "otros"


def uso_material(modelo, mid):
    """(barras, secciones) que usan el material mid."""
    barras = [eid for eid, el in modelo.elementos.items() if el.material == mid]
    secciones = [sid for sid, sec in modelo.secciones.items() if sec.material == mid]
    return barras, secciones


def uso_seccion(modelo, sid):
    """Barras que usan la sección sid."""
    return [eid for eid, el in modelo.elementos.items() if el.seccion == sid]


def _positivos(**valores):
    for nombre, v in valores.items():
        if v is None or v <= 0:
            raise ValueError(f"{nombre} debe ser positivo")


def crear_material(modelo, nombre, fc=None, e=None, g=None, gamma=None):
    """Concreto (con fc: E y G se calculan; γ por defecto el del concreto reforzado) u otro material
    (con E y G). Devuelve el ID."""
    if fc is not None:
        _positivos(**{"f'c": fc})
        e, g = modulos(fc)
        gamma = GAMMA_CONCRETO if gamma is None else gamma
        return modelo.agregar_material(nombre.strip() or nombre_material(fc), e, g, fc=fc, gamma=gamma)
    _positivos(E=e, G=g)
    return modelo.agregar_material(nombre.strip() or "Material", e, g)


def cambiar_material(modelo, mid, nombre, fc=None, e=None, g=None, gamma=None):
    """Cambia el material en su lugar: todo el modelo lo toma.

    - Concreto: con el f'c nuevo se recalculan E y G, y las secciones que lo usan copian el f'c
      (para sus diagramas de interacción).
    - Otros: E y G nuevos.
    Las barras guardan el ID del material, así que usan los valores nuevos sin hacer nada más.
    Devuelve (barras, secciones) que lo usan.
    """
    mat = modelo.materiales[mid]
    if familia_material(mat) == "concreto":
        _positivos(**{"f'c": fc})
        mat.fc = fc
        mat.e, mat.g = modulos(fc)
        mat.nombre = nombre.strip() or nombre_material(fc)
        if gamma is not None:
            mat.gamma = gamma
        for sec in modelo.secciones.values():
            if sec.material == mid and sec.concreto is not None:
                sec.concreto.fc = fc
    else:
        _positivos(E=e, G=g)
        mat.e, mat.g = e, g
        mat.nombre = nombre.strip() or mat.nombre
    return uso_material(modelo, mid)


def cambiar_seccion(modelo, sid, material, b, h, d, barra, nx, ny, fy=FY_DEFECTO):
    """Cambia una sección de concreto en su lugar (todas sus barras la toman, con su material).

    No se permite que quede igual a otra sección: habría dos con el mismo nombre y los mismos datos.
    Devuelve las barras que la usan.
    """
    mat = modelo.materiales.get(material)
    if mat is None or mat.fc is None:
        raise ValueError("Elige un material de concreto")
    if not 0 < d < min(b, h) / 2:
        raise ValueError("d debe ser positivo y menor que la mitad de b y de h")
    _positivos(fy=fy)
    otra = buscar_seccion(modelo, material, b, h, d, barra, nx, ny, fy)
    if otra is not None and otra != sid:
        raise ValueError(f"Ya existe una sección igual: {modelo.secciones[otra].nombre}")
    sec = modelo.secciones[sid]
    sec.concreto = Concreto(forma="rectangular", fc=mat.fc, d=d, barra=barra, b=b, h=h, nx=nx, ny=ny, fy=fy)
    sec.material = material
    sec.nombre = nombre_seccion(b, h, nx, ny, barra, fy)
    sec.a, sec.iy, sec.iz, sec.j = propiedades_rectangulo(b, h)
    barras = uso_seccion(modelo, sid)
    for eid in barras:
        modelo.elementos[eid].material = material
    return barras


def crear_seccion_general(modelo, nombre, a, iy, iz, j, material=None):
    """Sección dada por A, Iy, Iz y J (familia "otros", ya no se ofrece en Definir). Devuelve el ID."""
    _positivos(A=a, Iy=iy, Iz=iz, J=j)
    return modelo.agregar_seccion(nombre.strip() or "Sección", a, iy, iz, j, None, material)


def cambiar_seccion_general(modelo, sid, nombre, a, iy, iz, j, material=None):
    """Cambia en su lugar una sección de la familia "otros". Devuelve las barras que la usan."""
    _positivos(A=a, Iy=iy, Iz=iz, J=j)
    if material is not None and material not in modelo.materiales:
        raise KeyError(f"El material {material} no existe")
    sec = modelo.secciones[sid]
    sec.nombre = nombre.strip() or sec.nombre
    sec.a, sec.iy, sec.iz, sec.j = a, iy, iz, j
    sec.material = material
    barras = uso_seccion(modelo, sid)
    if material is not None:
        for eid in barras:
            modelo.elementos[eid].material = material
    return barras
