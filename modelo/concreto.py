"""Materiales y secciones de concreto en el modelo: nombres, familias y operaciones.

Las fórmulas (Ec, G, A, I y J) están en calculo/concreto.py (sagrado); aquí solo se usan. Este
módulo arma, busca y cambia materiales y secciones del modelo.
Todo en unidades internas: m y kN/m².

Acero de refuerzo (noviembre de 2026, pedido del usuario): es un material más, con fy y su norma
(ASTM A615 o A706, ACI 318-19 §20.2.1.3) y Es = 29 000 ksi fijo (§20.2.2.2, PDF p. 376). No se asigna
a barras: cada sección de concreto dice qué acero llevan sus barras (Concreto.acero, que da su fy) y
sus estribos (Concreto.acero_estribo, que da su fyt). Cambiar el fy de un acero cambia todas las
secciones que lo usan. El modelo trae "Acero Grado 60" (60 ksi, A615) por defecto: lo crea
acero_por_defecto al hacer Nuevo y al crear la primera sección de concreto, y el archivo al abrir uno
viejo. Las funciones que reciben fy (sin acero) toman el acero del modelo con ese fy, o lo crean.
"""
from calculo.concreto import (GAMMA_CONCRETO, POISSON, PSI, modulos, propiedades_rectangulo,   # noqa: F401
                              propiedades_T)
from calculo.diseno.viga import ES, area_barra, diametro_barra
from modelo.estructura import FY_DEFECTO, Concreto

TOL = 1e-9
KSI = 1000 * PSI                     # kN/m² por ksi
GRADOS_ACERO = (40, 60, 80, 100)     # ksi: los grados de ASTM A615 y A706 (A706 solo 60 y 80)
NORMAS_ACERO = ("A615", "A706")
POISSON_ACERO = 0.3


# ---------------------------------------------------------------- Acero de refuerzo
def es_acero(mat):
    """True si el material es acero de refuerzo (tiene fy)."""
    return mat is not None and getattr(mat, "fy", None) is not None


def grado_de(fy):
    """El grado (40, 60, 80 o 100, en ksi) si fy es el de uno de ellos; si no, None."""
    return next((g for g in GRADOS_ACERO if abs(fy - g * KSI) < 1e-6 * g * KSI), None)


def nombre_acero(fy):
    """Nombre automático de un acero de refuerzo: "Acero Grado 60" si fy es el de un grado; si no,
    "Acero fy 300 MPa" (en MPa, como los demás nombres guardados)."""
    grado = grado_de(fy)
    return f"Acero Grado {grado}" if grado else f"Acero fy {round(fy / 1000):g} MPa"


def crear_acero(modelo, nombre, fy, norma="A615"):
    """Crea un acero de refuerzo (fy en kN/m²; Es = 29 000 ksi, §20.2.2.2) y devuelve su ID."""
    _positivos(fy=fy)
    if norma not in NORMAS_ACERO:
        raise ValueError(f"La norma del acero debe ser una de {', '.join(NORMAS_ACERO)}")
    return modelo.agregar_material(nombre.strip() or nombre_acero(fy), ES, ES / (2 * (1 + POISSON_ACERO)),
                                   fy=fy, norma=norma)


def buscar_acero(modelo, fy, norma=None):
    """ID del primer acero de refuerzo del modelo con ese fy (y esa norma, si se da), o None."""
    for mid, mat in modelo.materiales.items():
        if es_acero(mat) and abs(mat.fy - fy) < 1e-6 * fy and (norma is None or mat.norma == norma):
            return mid
    return None


def acero_para(modelo, fy, norma=None):
    """ID del acero de refuerzo con ese fy: el que ya está en el modelo o uno nuevo."""
    mid = buscar_acero(modelo, fy, norma)
    return mid if mid is not None else crear_acero(modelo, "", fy, norma or "A615")


def acero_por_defecto(modelo):
    """El acero que el modelo trae por defecto, Grado 60 (60 ksi, A615): el que ya está o uno nuevo."""
    return acero_para(modelo, FY_DEFECTO)


def _acero(modelo, acero, fy):
    """(ID del acero, su fy): el acero dado o, sin él, el del modelo con ese fy (o uno nuevo)."""
    if acero is None:
        acero = acero_para(modelo, fy)
    mat = modelo.materiales.get(acero)
    if not es_acero(mat):
        raise ValueError("Elige un acero de refuerzo para las barras")
    return acero, mat.fy


def _mismo_acero(c, acero):
    """True si la sección usa ese acero (o si alguno de los dos no lo dice: secciones de antes)."""
    return acero is None or c.acero is None or c.acero == acero


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


def _igual(c, b, h, d, barra, nx, ny, fy, acero=None):
    return (c is not None and c.forma == "rectangular" and c.barra == barra and c.nx == nx and c.ny == ny
            and all(abs(x - y) < TOL for x, y in ((c.b, b), (c.h, h), (c.d, d)))
            and abs(c.fy - fy) < 1e-6 * fy and _mismo_acero(c, acero))


def buscar_seccion(modelo, material, b, h, d, barra, nx, ny, fy=FY_DEFECTO, acero=None):
    """ID de una sección rectangular con exactamente esos datos, ese material y ese acero (sin acero:
    el del modelo con ese fy), o None. No crea nada."""
    if acero is not None and es_acero(modelo.materiales.get(acero)):
        fy = modelo.materiales[acero].fy
    else:
        acero = buscar_acero(modelo, fy)
    for sid, sec in modelo.secciones.items():
        if sec.material == material and _igual(sec.concreto, b, h, d, barra, nx, ny, fy, acero):
            return sid
    return None


def crear_seccion(modelo, material, b, h, d, barra, nx, ny, fy=FY_DEFECTO, acero=None):
    """Crea la sección rectangular de concreto (con nombre y propiedades) y devuelve su ID. acero: el ID
    del acero de sus barras (sin él, el del modelo con ese fy, que se crea si falta)."""
    mat = modelo.materiales.get(material)
    if mat is None or mat.fc is None:
        raise ValueError("Elige un material de concreto")
    if not 0 < d < min(b, h) / 2:
        raise ValueError("d debe ser positivo y menor que la mitad de b y de h")
    _positivos(fy=fy)
    acero, fy = _acero(modelo, acero, fy)
    concreto = Concreto(forma="rectangular", fc=mat.fc, d=d, barra=barra, b=b, h=h, nx=nx, ny=ny, fy=fy,
                        acero=acero, acero_estribo=acero, fyt=fy)
    a, iy, iz, j = propiedades_rectangulo(b, h)
    return modelo.agregar_seccion(nombre_seccion(b, h, nx, ny, barra, fy), a, iy, iz, j, concreto, material)


def buscar_o_crear_seccion(modelo, material, b, h, d, barra, nx, ny, fy=FY_DEFECTO, acero=None):
    """La sección con esos datos: la que ya existe o una nueva. Devuelve (ID, True si es nueva)."""
    sid = buscar_seccion(modelo, material, b, h, d, barra, nx, ny, fy, acero)
    if sid is not None:
        return sid, False
    return crear_seccion(modelo, material, b, h, d, barra, nx, ny, fy, acero), True


# ---------------------------------------------------------------- Sección T (vigas y viguetas)
# Se guarda en un Concreto con forma "T": b es el ancho del alma (bw), h la altura total, bf y hf el
# ala, nx barras #barra abajo y n_sup barras #barra_sup arriba (en el ancho del alma), con su
# recubrimiento libre y su estribo (#estribo a s_estribo; 0 = sin estribos). d, del borde inferior
# al centro de las barras de abajo, sale del recubrimiento: d = rec + d_estribo + db/2 (como en el
# SMath del usuario). Los datos extra van por nombre (refuerzo_T): barra_sup, n_sup, rec, estribo y
# s_estribo.
def nombre_seccion_T(bw, h, bf, hf, n, barra, fy=FY_DEFECTO, barra_sup=0, n_sup=0, estribo=0, s_estribo=0.0):
    """Nombre automático, siempre en cm y MPa: "Concreto T 15x45 bf50 hf10 1#6", y con acero arriba y
    estribos, "Concreto T 15x45 bf50 hf10 1#6 sup 2#5 E#3@20"."""
    nombre = f"Concreto T {_cm(bw)}x{_cm(h)} bf{_cm(bf)} hf{_cm(hf)} {n}#{barra}"
    if n_sup:
        nombre += f" sup {n_sup}#{barra_sup}"
    if estribo:
        nombre += f" E#{estribo}@{_cm(s_estribo)}"
    return nombre if abs(fy - FY_DEFECTO) < 1e-6 * FY_DEFECTO else f"{nombre} fy {round(fy / 1000):g} MPa"


def _d_estribo(estribo):
    return diametro_barra(estribo) if estribo else 0.0


def concreto_T(fc, bw, h, bf, hf, d, barra, n, fy=FY_DEFECTO, barra_sup=0, n_sup=0, rec=None, estribo=0,
               s_estribo=0.0, acero=None, acero_estribo=None, fyt=None):
    """El Concreto de una T (sin validar). Con rec (recubrimiento libre), d se calcula; sin rec (las T
    de antes, que daban d), el recubrimiento sale de d. Sin fyt, el de los estribos es fy."""
    if not estribo:
        estribo, s_estribo = 0, 0.0
    if not n_sup:
        barra_sup, n_sup = 0, 0
    if rec is None:
        rec = d - _d_estribo(estribo) - diametro_barra(barra) / 2
    else:
        d = rec + _d_estribo(estribo) + diametro_barra(barra) / 2
    return Concreto(forma="T", fc=fc, d=d, barra=barra, b=bw, h=h, nx=n, ny=1, fy=fy, bf=bf, hf=hf,
                    barra_sup=barra_sup, n_sup=n_sup, recubrimiento=rec, estribo=estribo, s_estribo=s_estribo,
                    acero=acero, acero_estribo=acero_estribo, fyt=fy if fyt is None else fyt)


def _aceros_T(modelo, fy, acero, acero_estribo):
    """(acero, fy, acero de estribos, fyt) de una T: los dados o, sin ellos, el del modelo con ese fy
    (los estribos, sin el suyo, con el mismo de las barras)."""
    acero, fy = _acero(modelo, acero, fy)
    if acero_estribo is None:
        return acero, fy, acero, fy
    mat = modelo.materiales.get(acero_estribo)
    if not es_acero(mat):
        raise ValueError("Elige un acero de refuerzo para los estribos")
    return acero, fy, acero_estribo, mat.fy


def d_superior(c):
    """De arriba al centro de las barras de arriba de una T (m): rec + d_estribo + db_sup/2."""
    return c.recubrimiento + _d_estribo(c.estribo) + (diametro_barra(c.barra_sup) / 2 if c.n_sup else 0.0)


def peralte_positivo(c):
    """d para el momento positivo (barras de abajo en tracción): h − d desde abajo."""
    return c.h - c.d


def peralte_negativo(c):
    """d para el momento negativo (barras de arriba en tracción): h − (rec + d_estribo + db_sup/2)."""
    return c.h - d_superior(c)


def area_inferior(c):
    """As de las barras de abajo (m²)."""
    return area_barra(c.barra, c.nx)


def area_superior(c):
    """As de las barras de arriba (m²); 0 si no tiene."""
    return area_barra(c.barra_sup, c.n_sup) if c.n_sup else 0.0


def _validar_T(modelo, material, c):
    mat = modelo.materiales.get(material)
    if mat is None or mat.fc is None:
        raise ValueError("Elige un material de concreto")
    propiedades_T(c.b, c.h, c.bf, c.hf)              # revisa las medidas (bf ≥ bw, hf < h)
    if c.recubrimiento <= 0:
        raise ValueError("El recubrimiento debe ser positivo")
    if not 0 < c.d < min(c.b / 2, c.h - c.hf):
        raise ValueError("Las barras de abajo no caben: rec + estribo + db/2 debe ser menor que bw/2 y que "
                         "la altura del alma (h − hf)")
    if c.nx < 1:
        raise ValueError("Pon al menos una barra abajo")
    if c.n_sup and not 0 < d_superior(c) < c.h / 2:
        raise ValueError("Las barras de arriba no caben: rec + estribo + db/2 debe ser menor que h/2")
    if c.estribo and c.s_estribo <= 0:
        raise ValueError("La separación de los estribos debe ser positiva")
    _positivos(fy=c.fy)
    return mat


def _igual_T(c, otra):
    return (c is not None and c.forma == "T" and c.barra == otra.barra and c.nx == otra.nx
            and c.barra_sup == otra.barra_sup and c.n_sup == otra.n_sup and c.estribo == otra.estribo
            and all(abs(x - y) < TOL for x, y in ((c.b, otra.b), (c.h, otra.h), (c.bf, otra.bf), (c.hf, otra.hf),
                                                  (c.d, otra.d), (c.recubrimiento, otra.recubrimiento),
                                                  (c.s_estribo, otra.s_estribo)))
            and abs(c.fy - otra.fy) < 1e-6 * otra.fy and abs(c.fyt - otra.fyt) < 1e-6 * otra.fyt
            and _mismo_acero(c, otra.acero)
            and (otra.acero_estribo is None or c.acero_estribo is None or c.acero_estribo == otra.acero_estribo))


def _nombre_de_T(c):
    return nombre_seccion_T(c.b, c.h, c.bf, c.hf, c.nx, c.barra, c.fy, c.barra_sup, c.n_sup, c.estribo,
                            c.s_estribo)


def nombre_automatico(c):
    """El nombre automático de una sección de concreto (rectangular o T), o None (circular)."""
    if c.forma == "T":
        return _nombre_de_T(c)
    if c.forma == "rectangular":
        return nombre_seccion(c.b, c.h, c.nx, c.ny, c.barra, c.fy)
    return None


def buscar_seccion_T(modelo, material, bw, h, bf, hf, d, barra, n, fy=FY_DEFECTO, acero=None, acero_estribo=None,
                     **refuerzo):
    """ID de una sección T con exactamente esos datos, ese material y esos aceros, o None (no crea
    nada). refuerzo: barra_sup, n_sup, rec, estribo y s_estribo (los de concreto_T)."""
    if acero is not None and es_acero(modelo.materiales.get(acero)):
        fy = modelo.materiales[acero].fy
    else:
        acero = buscar_acero(modelo, fy)
    fyt = modelo.materiales[acero_estribo].fy if es_acero(modelo.materiales.get(acero_estribo)) else fy
    buscada = concreto_T(0.0, bw, h, bf, hf, d, barra, n, fy, acero=acero,
                         acero_estribo=acero_estribo if acero_estribo is not None else acero, fyt=fyt, **refuerzo)
    for sid, sec in modelo.secciones.items():
        if sec.material == material and _igual_T(sec.concreto, buscada):
            return sid
    return None


def crear_seccion_T(modelo, material, bw, h, bf, hf, d, barra, n, fy=FY_DEFECTO, acero=None, acero_estribo=None,
                    **refuerzo):
    """Crea la sección T de concreto (con nombre y propiedades) y devuelve su ID. acero y acero_estribo:
    los de sus barras y sus estribos (sin ellos, el del modelo con ese fy). refuerzo: barra_sup, n_sup,
    rec, estribo y s_estribo (los de concreto_T)."""
    mat = modelo.materiales.get(material)
    if mat is None or mat.fc is None:
        raise ValueError("Elige un material de concreto")
    acero, fy, acero_estribo, fyt = _aceros_T(modelo, fy, acero, acero_estribo)
    c = concreto_T(mat.fc, bw, h, bf, hf, d, barra, n, fy, acero=acero, acero_estribo=acero_estribo, fyt=fyt,
                   **refuerzo)
    _validar_T(modelo, material, c)
    a, iy, iz, j, _ = propiedades_T(bw, h, bf, hf)
    return modelo.agregar_seccion(_nombre_de_T(c), a, iy, iz, j, c, material)


def buscar_o_crear_seccion_T(modelo, material, bw, h, bf, hf, d, barra, n, fy=FY_DEFECTO, acero=None,
                             acero_estribo=None, **refuerzo):
    """La T con esos datos: la que ya existe o una nueva. Devuelve (ID, True si es nueva)."""
    sid = buscar_seccion_T(modelo, material, bw, h, bf, hf, d, barra, n, fy, acero, acero_estribo, **refuerzo)
    if sid is not None:
        return sid, False
    return crear_seccion_T(modelo, material, bw, h, bf, hf, d, barra, n, fy, acero, acero_estribo, **refuerzo), True


def cambiar_seccion_T(modelo, sid, material, bw, h, bf, hf, d, barra, n, fy=FY_DEFECTO, acero=None,
                      acero_estribo=None, **refuerzo):
    """Cambia una sección en su lugar por una T (todas sus barras la toman, con su material).
    Devuelve las barras que la usan."""
    mat = modelo.materiales.get(material)
    if mat is None or mat.fc is None:
        raise ValueError("Elige un material de concreto")
    acero, fy, acero_estribo, fyt = _aceros_T(modelo, fy, acero, acero_estribo)
    c = concreto_T(mat.fc, bw, h, bf, hf, d, barra, n, fy, acero=acero, acero_estribo=acero_estribo, fyt=fyt,
                   **refuerzo)
    _validar_T(modelo, material, c)
    otra = buscar_seccion_T(modelo, material, bw, h, bf, hf, d, barra, n, fy, acero, acero_estribo, **refuerzo)
    if otra is not None and otra != sid:
        raise ValueError(f"Ya existe una sección igual: {modelo.secciones[otra].nombre}")
    sec = modelo.secciones[sid]
    sec.concreto = c
    sec.material = material
    sec.nombre = _nombre_de_T(c)
    sec.a, sec.iy, sec.iz, sec.j, _ = propiedades_T(bw, h, bf, hf)
    barras = uso_seccion(modelo, sid)
    for eid in barras:
        modelo.elementos[eid].material = material
    return barras


def refuerzo_T(c):
    """Los datos extra de una T, por nombre, para crear otra igual: barra_sup, n_sup, rec, estribo,
    s_estribo y sus aceros."""
    return {"barra_sup": c.barra_sup, "n_sup": c.n_sup, "rec": c.recubrimiento, "estribo": c.estribo,
            "s_estribo": c.s_estribo, "acero": c.acero, "acero_estribo": c.acero_estribo}


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
# Las carpetas de Definir. Materiales: Concreto y Acero de refuerzo (el que usan las secciones para sus
# barras; el acero ESTRUCTURAL quedó en la copia "utp"). Secciones: Concreto. Los materiales sin f'c ni
# fy y las secciones sin refuerzo (de archivos viejos, también los de acero estructural, o del código)
# van a "Otros", que solo aparece si hay alguno.
FAMILIAS_MATERIAL = {"concreto": "Concreto", "acero": "Acero de refuerzo"}
FAMILIAS_SECCION = {"concreto": "Concreto"}
FAMILIAS = {**FAMILIAS_MATERIAL, **FAMILIAS_SECCION}
NOMBRE_OTROS = "Otros"


def familias(tipo):
    """Las familias (carpetas) de "material" o de "seccion": {clave: nombre}."""
    return FAMILIAS_MATERIAL if tipo == "material" else FAMILIAS_SECCION


def nombre_familia(familia):
    return FAMILIAS.get(familia, NOMBRE_OTROS)


def familia_material(mat):
    """"concreto" si se definió por f'c; "acero" si es acero de refuerzo (tiene fy); "otros" si se
    dieron E y G directamente (viejos)."""
    if es_acero(mat):
        return "acero"
    return "concreto" if mat.fc is not None else "otros"


def familia_seccion(sec):
    """"concreto" si tiene geometría y refuerzo; "otros" si se dieron A, I y J directamente (viejas)."""
    return "concreto" if sec.concreto is not None else "otros"


def uso_material(modelo, mid):
    """(barras, secciones) que usan el material mid. Un acero de refuerzo lo usan las secciones que
    lo llevan en sus barras o en sus estribos (y, con ellas, sus barras)."""
    if es_acero(modelo.materiales.get(mid)):
        secciones = [sid for sid, sec in modelo.secciones.items() if sec.concreto is not None
                     and mid in (sec.concreto.acero, sec.concreto.acero_estribo)]
        barras = [eid for eid, el in modelo.elementos.items() if el.seccion in secciones]
        return barras, secciones
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
        gamma = GAMMA_CONCRETO if gamma is None else gamma
        e, g = modulos(fc, gamma)               # Ec con wc = γ (ACI 318-19 Ec. 19.2.2.1.a)
        return modelo.agregar_material(nombre.strip() or nombre_material(fc), e, g, fc=fc, gamma=gamma)
    _positivos(E=e, G=g)
    return modelo.agregar_material(nombre.strip() or "Material", e, g)


def cambiar_material(modelo, mid, nombre, fc=None, e=None, g=None, gamma=None, fy=None, norma=None):
    """Cambia el material en su lugar: todo el modelo lo toma.

    - Concreto: con el f'c nuevo se recalculan E y G, y las secciones que lo usan copian el f'c
      (para sus diagramas de interacción).
    - Acero de refuerzo: fy y norma nuevos; las secciones que lo usan copian el fy (en sus barras) o
      el fyt (en sus estribos), y su nombre automático se rehace (lleva el fy si no es Grado 60).
    - Otros: E y G nuevos.
    Las barras guardan el ID del material, así que usan los valores nuevos sin hacer nada más.
    Devuelve (barras, secciones) que lo usan.
    """
    mat = modelo.materiales[mid]
    if familia_material(mat) == "acero":
        _positivos(fy=fy)
        norma = mat.norma if norma is None else norma
        if norma not in NORMAS_ACERO:
            raise ValueError(f"La norma del acero debe ser una de {', '.join(NORMAS_ACERO)}")
        mat.fy, mat.norma = fy, norma
        mat.nombre = nombre.strip() or nombre_acero(fy)
        for sec in modelo.secciones.values():
            c = sec.concreto
            if c is None or mid not in (c.acero, c.acero_estribo):
                continue
            automatico = sec.nombre == nombre_automatico(c)
            if c.acero == mid:
                c.fy = fy
            if c.acero_estribo == mid:
                c.fyt = fy
            if automatico:
                sec.nombre = nombre_automatico(c)
    elif familia_material(mat) == "concreto":
        _positivos(**{"f'c": fc})
        mat.fc = fc
        if gamma is not None:
            mat.gamma = gamma
        mat.e, mat.g = modulos(fc, mat.gamma)   # E depende de f'c y de γ
        mat.nombre = nombre.strip() or nombre_material(fc)
        for sec in modelo.secciones.values():
            if sec.material == mid and sec.concreto is not None:
                sec.concreto.fc = fc
    else:
        _positivos(E=e, G=g)
        mat.e, mat.g = e, g
        mat.nombre = nombre.strip() or mat.nombre
    return uso_material(modelo, mid)


def cambiar_seccion(modelo, sid, material, b, h, d, barra, nx, ny, fy=FY_DEFECTO, acero=None):
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
    acero, fy = _acero(modelo, acero, fy)
    otra = buscar_seccion(modelo, material, b, h, d, barra, nx, ny, fy, acero)
    if otra is not None and otra != sid:
        raise ValueError(f"Ya existe una sección igual: {modelo.secciones[otra].nombre}")
    sec = modelo.secciones[sid]
    sec.concreto = Concreto(forma="rectangular", fc=mat.fc, d=d, barra=barra, b=b, h=h, nx=nx, ny=ny, fy=fy,
                            acero=acero, acero_estribo=acero, fyt=fy)
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
