"""Losas de viguetas: losas nervadas en una dirección (ACI 318-19 §9.8, PDF p. 153–154).

No es cálculo: arma la geometría, los sistemas de vigueta y las cargas; las fórmulas están en
calculo/ (diseno/viga.py) y el análisis en modelo/analisis.py.

Qué es una losa aquí (decisiones del usuario, noviembre de 2026):
- Un conjunto de PAÑOS con la misma dirección de viguetas y la MISMA vigueta: una sección T para toda
  la losa. Cada paño va entre dos vigas paralelas del modelo (sus apoyos), al mismo nivel y que cubren
  el mismo tramo, de nodo a nodo (si una viga está partida en varias barras, se toman todas las que
  siguen en línea). Las viguetas van perpendiculares a esas vigas. Las vigas que unen las esquinas
  del paño por los lados, paralelas a las viguetas, son sus vigas laterales: se buscan solas.
- La separación s de las viguetas es una sola para toda la losa (si no, no seguirían de un paño al
  otro): s = ancho libre del paño de referencia / n, con n lo que da el usuario. Las viguetas van en
  una rejilla común, u = u_ref + s/2 + k·s, y cada paño lleva las que caben en su ancho libre.
- bf = el menor de s y el ancho efectivo de la Tabla 6.3.2.1 (PDF p. 75), con el claro libre menor de
  la losa. Cambiar n cambia s y, con él, bf: la losa pasa a una sección T con ese bf.
- FRANJAS (los "sistemas de vigueta"): a lo ancho de la losa, cada tramo con la misma secuencia de
  claros, anchos de apoyo y cargas es una vigueta continua con apoyos simples en los ejes de las vigas
  (como ejemplos/vigueta.py). Franjas con los mismos números son una sola, con varios tramos de
  ancho. Se generan TODAS, no solo la más larga: una más corta, con otra viva, puede mandar.
- Cargas de área por paño (kN/m²): la muerta adicional y la viva. El peso propio sale de la sección:
  (A_T + (s − bf)·hf)·γ por vigueta (si bf < s, la losa entre las alas también pesa).
- Casos de viva (patrones, §6.4.2, PDF p. 75) de cada franja: los automáticos (todos los claros, los
  impares, los pares y cada par de claros vecinos) y los que agregue el usuario, que se guardan con la
  losa por la firma de la franja (sus claros).
- Carga a las vigas del modelo 3D: la reacción de la vigueta en cada apoyo, por caso, dividida entre s,
  como uniforme hacia −Z en las barras de ese apoyo dentro de la franja (cargas_a_vigas). El peso
  propio de la losa va al caso de peso propio; la muerta adicional, al caso inicial (Carga muerta
  adicional); y la viva, con todos los claros cargados, al caso automático "Viva de losas" (tipo L).

Coordenadas: t es la dirección de las vigas de apoyo (horizontal), n la de las viguetas (t girado
90° alrededor de Z), u = p·t y v = p·n. Un paño ocupa [u0, u1] × [va, vb].

Simplificaciones (van en las limitaciones de CLAUDE.md):
- los claros de la vigueta van de eje a eje de las vigas, con la carga en todo el claro: el peso de la
  losa sobre media viga se cuenta en la vigueta y en la viga (del lado seguro);
- la carga sobre el ancho de una viga lateral va a los apoyos (la total no cambia);
- las barras de apoyo deben quedar enteras dentro de una franja (sin cargas parciales: tocarían
  calculo/); si no, se avisa dónde partir la viga;
- solo paños rectangulares y vigas de apoyo horizontales y paralelas.
"""
import math
from dataclasses import dataclass, field

import numpy as np

from calculo.concreto import propiedades_T
from calculo.diseno import viga as formulas
from calculo.rigidez.barra import angulos, rotacion
from calculo.tolerancias import TOL_LONGITUD

TOL = 1e-3                     # m: tolerancia de las posiciones de la losa (alineación de vigas y paños)
PARALELA = 0.999               # |coseno| desde el cual dos direcciones son paralelas
NOMBRE_VIVA_LOSAS = "Viva de losas"


# ---------------------------------------------------------------- Datos
@dataclass
class Pano:
    """Un paño de losa entre dos vigas de apoyo. Las cargas, en kN/m² (sobre la losa)."""
    apoyo_a: list                  # IDs de las barras del primer apoyo (en línea)
    apoyo_b: list                  # del segundo
    muerta: float = 0.0            # carga muerta adicional (baldosas, topping, tabiques…)
    viva: float = 0.0              # carga viva


@dataclass
class Losa:
    """Losa de viguetas: sus paños, la vigueta (una sección T) y cómo se revisan sus deflexiones."""
    nombre: str
    seccion: int                   # ID de la sección T de la vigueta (la misma en toda la losa)
    panos: dict = field(default_factory=dict)        # ID de paño -> Pano
    referencia: int = None         # el paño donde se dio n (None: el primero)
    n_viguetas: int = 1            # viguetas en el paño de referencia
    xi: float = 2.0                # ξ de la Tabla 24.2.4.1.3: 2.0 con 60 meses o más
    fragiles: bool = True          # sostiene elementos que se dañan con deflexiones grandes: ℓ/480 (si no, ℓ/240)
    sostenida: float = 0.5         # fracción de la viva que es sostenida (la carga de largo plazo: D + 0.5L, CC-2)
    patrones: dict = field(default_factory=dict)     # firma de franja -> [[nombre, [claros]], ...] (del usuario)


# ---------------------------------------------------------------- Geometría de las barras
def _extremos(modelo, eid):
    el = modelo.elementos[eid]
    return np.asarray(modelo.nodos[el.ni].coords, float), np.asarray(modelo.nodos[el.nj].coords, float)


def marco(modelo, eid):
    """(t, n): la dirección horizontal de la barra eid y la perpendicular horizontal, las dos hacia
    +X (o hacia +Y si van en Y): así los claros de las viguetas se numeran de −X a +X (o de −Y a +Y)."""
    pi, pj = _extremos(modelo, eid)
    d = pj - pi
    d[2] = 0.0
    largo = np.linalg.norm(d)
    if largo < TOL_LONGITUD:
        raise ValueError(f"La barra {eid} es vertical: un apoyo de losa debe ser una viga")

    def positivo(u):
        return -u if u[0] < -TOL or (abs(u[0]) <= TOL and u[1] < 0) else u

    t = positivo(d / largo)
    return t, positivo(np.array([-t[1], t[0], 0.0]))


def _intervalo(modelo, eid, t, n):
    """(u0, u1, v, z) de una barra horizontal paralela a t."""
    pi, pj = _extremos(modelo, eid)
    if abs(pi[2] - pj[2]) > TOL:
        raise ValueError(f"La barra {eid} no es horizontal: un apoyo de losa debe ser una viga horizontal")
    d = pj - pi
    if abs(d @ t) / np.linalg.norm(d) < PARALELA:
        raise ValueError(f"La barra {eid} no es paralela a las demás vigas de apoyo de la losa")
    ua, ub = pi @ t, pj @ t
    return min(ua, ub), max(ua, ub), float((pi @ n + pj @ n) / 2), float(pi[2])


def ancho_en_planta(modelo, eid, n):
    """Ancho de la viga eid medido en la dirección horizontal n (m): de su sección y su giro α. 0 si
    no tiene sección de concreto."""
    el = modelo.elementos[eid]
    sec = modelo.secciones.get(el.seccion)
    c = sec.concreto if sec is not None else None
    if c is None:
        return 0.0
    pi, pj = _extremos(modelo, eid)
    beta, gamma, _ = angulos(pi, pj)
    r = rotacion(np.radians(el.alfa), beta, gamma)
    b, h = (c.D, c.D) if c.forma == "circular" else (c.b, c.h)
    return float(abs(r[1] @ n) * b + abs(r[2] @ n) * h)


def cara_superior(modelo, eid):
    """Altura (z global) de la cara de arriba de la viga eid: el eje más lo que hay del centroide a la
    fibra de arriba (h/2 en un rectángulo; h − yb en una T). Sin sección, el eje."""
    el = modelo.elementos[eid]
    sec = modelo.secciones.get(el.seccion)
    c = sec.concreto if sec is not None else None
    pi, pj = _extremos(modelo, eid)
    if c is None or c.forma == "circular":
        return float(pi[2])
    from modelo.concreto import contorno
    beta, gamma, _ = angulos(pi, pj)
    r = rotacion(np.radians(el.alfa), beta, gamma)
    return float(pi[2] + max((r[1] * y + r[2] * z)[2] for y, z in contorno(c)))


def _cadena(modelo, eid, t, n):
    """Las barras en línea con eid (misma recta, mismo nivel), unidas por sus nodos, ordenadas por u:
    [(u0, u1, ID)]."""
    u0, u1, v, z = _intervalo(modelo, eid, t, n)
    en_linea = []
    for otra in modelo.elementos:
        try:
            a, b, vo, zo = _intervalo(modelo, otra, t, n)
        except ValueError:
            continue
        if abs(vo - v) < TOL and abs(zo - z) < TOL:
            en_linea.append((a, b, otra))
    en_linea.sort()
    # Desde eid hacia los dos lados, mientras la siguiente barra empiece donde termina la anterior
    i = next(k for k, (_a, _b, e) in enumerate(en_linea) if e == eid)
    cadena = [en_linea[i]]
    for paso in (-1, 1):
        k = i
        while 0 <= k + paso < len(en_linea):
            sig = en_linea[k + paso]
            actual = cadena[0] if paso < 0 else cadena[-1]
            if (paso > 0 and abs(sig[0] - actual[1]) < TOL) or (paso < 0 and abs(sig[1] - actual[0]) < TOL):
                cadena.insert(0, sig) if paso < 0 else cadena.append(sig)
                k += paso
            else:
                break
    return cadena


def _tramo_de_cadena(cadena, u0, u1, eid):
    """Las barras de la cadena que cubren exactamente [u0, u1], o ValueError."""
    dentro = [c for c in cadena if c[0] >= u0 - TOL and c[1] <= u1 + TOL]
    if not dentro or abs(dentro[0][0] - u0) > TOL or abs(dentro[-1][1] - u1) > TOL:
        raise ValueError(f"La viga {eid} no llega de nodo a nodo al tramo del paño (de u = {u0:.3f} a {u1:.3f} m): "
                         "el paño debe ir de nodo a nodo en las dos vigas. Si una viga sigue más allá sin un "
                         "nodo en la esquina, pártela ahí")
    return [c[2] for c in dentro]


# ---------------------------------------------------------------- Paños
@dataclass
class GeometriaPano:
    """Dónde está un paño, en las coordenadas (u, v) de su losa. Lo calcula geometria_pano."""
    u0: float
    u1: float
    va: float                      # eje del apoyo de abajo (el de menor v)
    vb: float                      # eje del apoyo de arriba
    z: float                       # nivel de los ejes de las vigas de apoyo
    apoyo_a: list                  # barras del apoyo en va
    apoyo_b: list                  # barras del apoyo en vb
    ancho_a: float                 # ancho en planta de cada viga de apoyo (m)
    ancho_b: float
    lateral_0: list                # barras de la viga lateral en u0 ([] si no hay)
    lateral_1: list                # en u1
    ancho_0: float
    ancho_1: float
    tope: float                    # z de la cara de arriba de la losa (la de las vigas de apoyo)

    @property
    def claro(self):
        """Claro de eje a eje de las vigas de apoyo (m)."""
        return self.vb - self.va

    @property
    def claro_libre(self):
        """ℓn: de cara a cara de las vigas de apoyo (m)."""
        return self.claro - self.ancho_a / 2 - self.ancho_b / 2

    @property
    def libre_0(self):
        """Donde empieza el ancho libre (u): la cara de la viga lateral, o el borde del paño."""
        return self.u0 + self.ancho_0 / 2

    @property
    def libre_1(self):
        return self.u1 - self.ancho_1 / 2


def _lateral(modelo, u, va, vb, z, t, n):
    """Barras de la viga lateral que va de (u, va) a (u, vb) al nivel z, o [] si no la hay completa."""
    tramos = []
    for eid, el in modelo.elementos.items():
        pi, pj = _extremos(modelo, eid)
        if abs(pi[2] - z) > TOL or abs(pj[2] - z) > TOL or abs(pi @ t - u) > TOL or abs(pj @ t - u) > TOL:
            continue
        a, b = sorted((pi @ n, pj @ n))
        if a >= va - TOL and b <= vb + TOL and b - a > TOL:
            tramos.append((a, b, eid))
    tramos.sort()
    hasta = va
    for a, b, _e in tramos:
        if a > hasta + TOL:
            return []
        hasta = max(hasta, b)
    return [e for _a, _b, e in tramos] if hasta >= vb - TOL else []


def geometria_pano(modelo, pano, ejes=None):
    """GeometriaPano del paño. ejes = (t, n) de su losa (None: los de su primer apoyo). ValueError
    con un texto claro si el paño no sirve (las vigas no son paralelas, no están al mismo nivel, no
    cubren el mismo tramo, no tienen sección...)."""
    for eid in pano.apoyo_a + pano.apoyo_b:
        if eid not in modelo.elementos:
            raise ValueError(f"La viga {eid} del paño ya no existe")
    t, n = ejes if ejes is not None else marco(modelo, pano.apoyo_a[0])
    lados = []
    for apoyo in (pano.apoyo_a, pano.apoyo_b):
        cadena = _cadena(modelo, apoyo[0], t, n)
        datos = [_intervalo(modelo, e, t, n) for e in apoyo]
        lados.append((min(d[0] for d in datos), max(d[1] for d in datos), datos[0][2], datos[0][3], cadena, apoyo))
    (a0, a1, va, za, cadena_a, apoyo_a), (b0, b1, vb, zb, cadena_b, apoyo_b) = lados
    if abs(za - zb) > TOL:
        raise ValueError(f"Las dos vigas deben estar al mismo nivel (z = {za:.3f} y {zb:.3f} m)")
    if abs(va - vb) < TOL:
        raise ValueError("Las dos vigas están en la misma línea: elige dos vigas paralelas, una frente a la otra")
    if min(a1, b1) - max(a0, b0) < TOL:
        raise ValueError("Las dos vigas no se enfrentan: no tienen un tramo en común")
    # El tramo del paño: primero el de la viga más larga (la otra se completa con las barras que siguen
    # en línea: una viga partida por un nodo intermedio); si no se puede, el de la más corta
    largo, corto = ((a0, a1), (b0, b1)) if a1 - a0 >= b1 - b0 else ((b0, b1), (a0, a1))
    error = None
    for u0, u1 in (largo, corto):
        try:
            apoyo_a = _tramo_de_cadena(cadena_a, u0, u1, lados[0][5][0])
            apoyo_b = _tramo_de_cadena(cadena_b, u0, u1, lados[1][5][0])
            break
        except ValueError as e:
            error = error or e
    else:
        raise error
    if va > vb:
        va, vb, apoyo_a, apoyo_b = vb, va, apoyo_b, apoyo_a
    for eid in apoyo_a + apoyo_b:
        if modelo.elementos[eid].seccion is None:
            raise ValueError(f"La viga {eid} no tiene sección: asígnala (hace falta su ancho para la cara del apoyo)")
    ancho_a = max(ancho_en_planta(modelo, e, n) for e in apoyo_a)
    ancho_b = max(ancho_en_planta(modelo, e, n) for e in apoyo_b)
    if va + ancho_a / 2 >= vb - ancho_b / 2:
        raise ValueError("Las dos vigas se tocan: no queda claro libre para las viguetas")
    lat0 = _lateral(modelo, u0, va, vb, za, t, n)
    lat1 = _lateral(modelo, u1, va, vb, za, t, n)
    ancho0 = max((ancho_en_planta(modelo, e, t) for e in lat0), default=0.0)
    ancho1 = max((ancho_en_planta(modelo, e, t) for e in lat1), default=0.0)
    tope = max(cara_superior(modelo, e) for e in apoyo_a + apoyo_b)
    return GeometriaPano(u0, u1, va, vb, za, apoyo_a, apoyo_b, ancho_a, ancho_b, lat0, lat1, ancho0, ancho1, tope)


def ejes_losa(modelo, losa):
    """(t, n) de la losa: los de la primera viga de apoyo de su primer paño."""
    pano = next(iter(losa.panos.values()))
    return marco(modelo, pano.apoyo_a[0])


def geometrias(modelo, losa):
    """{ID de paño: GeometriaPano}, todos en los ejes de la losa. ValueError si alguno no sirve o si
    sus viguetas no van en la misma dirección que las del resto."""
    if not losa.panos:
        return {}
    ejes = ejes_losa(modelo, losa)
    geos = {}
    for pid, pano in losa.panos.items():
        try:
            geos[pid] = geometria_pano(modelo, pano, ejes)
        except ValueError as e:
            raise ValueError(f"Paño {pid}: {e}") from e
    # Que no se encimen
    lista = list(geos.items())
    for i, (p1, g1) in enumerate(lista):
        for p2, g2 in lista[i + 1:]:
            if (min(g1.u1, g2.u1) - max(g1.u0, g2.u0) > TOL and min(g1.vb, g2.vb) - max(g1.va, g2.va) > TOL
                    and abs(g1.z - g2.z) < TOL):
                raise ValueError(f"Los paños {p1} y {p2} se enciman")
    return geos


# ---------------------------------------------------------------- Viguetas: separación y bf
def concreto(modelo, losa):
    """El Concreto de la vigueta de la losa."""
    return modelo.secciones[losa.seccion].concreto


def paño_referencia(losa):
    return losa.referencia if losa.referencia in losa.panos else next(iter(losa.panos))


def separacion(geos, losa):
    """s (m): el ancho libre del paño de referencia entre n."""
    g = geos[paño_referencia(losa)]
    return (g.libre_1 - g.libre_0) / max(1, losa.n_viguetas)


def posiciones(geo, s, u_ref, bw):
    """Posiciones u de las viguetas que caben en el ancho libre del paño (la rejilla común de la losa:
    u_ref + k·s), con su alma entera dentro."""
    k0 = math.ceil((geo.libre_0 + bw / 2 - u_ref) / s - 1e-9)
    k1 = math.floor((geo.libre_1 - bw / 2 - u_ref) / s + 1e-9)
    return [u_ref + k * s for k in range(k0, k1 + 1)]


def rejilla(geos, losa, bw):
    """(s, u_ref): la separación y el origen de la rejilla de viguetas de la losa: la primera
    vigueta del paño de referencia va a s/2 de su borde libre."""
    s = separacion(geos, losa)
    return s, geos[paño_referencia(losa)].libre_0 + s / 2


def bordes(geo, us, bw):
    """(izquierdo, derecho): distancia libre del alma de la primera y la última vigueta a la cara de
    la viga lateral (o al borde del paño), en m. None si el paño no tiene viguetas."""
    if not us:
        return None
    return us[0] - bw / 2 - geo.libre_0, geo.libre_1 - (us[-1] + bw / 2)


def claro_libre_minimo(geos):
    return min(g.claro_libre for g in geos.values())


def ala_efectiva(geos, losa, bw, hf):
    """bf (m): el menor de s y el ancho efectivo de la Tabla 6.3.2.1 (con el claro libre menor)."""
    s = separacion(geos, losa)
    return min(s, formulas.ancho_efectivo(bw, hf, s - bw, claro_libre_minimo(geos)))


def actualizar_seccion(modelo, losa):
    """Pone a la losa la sección T con el bf que le toca (según s). Si cambió, usa o crea otra T con
    los mismos datos y ese bf. Devuelve True si cambió."""
    from modelo import concreto as cc
    geos = geometrias(modelo, losa)
    if not geos:
        return False
    sec = modelo.secciones[losa.seccion]
    c = sec.concreto
    bf = ala_efectiva(geos, losa, c.b, c.hf)
    if abs(bf - c.bf) < 1e-6:
        return False
    if bf <= c.b + 1e-6:
        raise ValueError(f"Con {losa.n_viguetas} viguetas, la separación ({bf * 100:.1f} cm) no deja ala: pon menos")
    sid, _nueva = cc.buscar_o_crear_seccion_T(modelo, sec.material, c.b, c.h, round(bf, 6), c.hf, c.d, c.barra, c.nx,
                                              c.fy, **cc.refuerzo_T(c))
    losa.seccion = sid
    return True


# ---------------------------------------------------------------- Franjas (sistemas de vigueta)
@dataclass
class Tramo:
    """Un pedazo de una franja a lo ancho de la losa."""
    u0: float
    u1: float
    va: float                      # posición del primer apoyo
    panos: list                    # ID del paño de cada claro
    apoyos: list                   # por línea de apoyo: las barras de esa viga dentro de [u0, u1]


@dataclass
class Franja:
    """Una vigueta continua de la losa: sus claros, apoyos y cargas, y dónde está (sus tramos)."""
    letra: str
    claros: list                   # m, de eje a eje
    anchos: list                   # ancho de cada viga de apoyo (m): uno más que los claros
    muerta: list                   # kN/m² de cada claro
    viva: list
    tramos: list = field(default_factory=list)

    @property
    def nombre(self):
        n = len(self.claros)
        return f"Franja {self.letra} ({n} claro{'s' if n != 1 else ''})"

    @property
    def ancho(self):
        return sum(t.u1 - t.u0 for t in self.tramos)

    @property
    def firma(self):
        """Clave de los casos de viva del usuario: los claros, en mm."""
        return "|".join(f"{c * 1000:.0f}" for c in self.claros)

    def libre(self, k):
        """ℓn del claro k (0, 1…): de cara a cara."""
        return self.claros[k] - self.anchos[k] / 2 - self.anchos[k + 1] / 2


def _letra(i):
    letras = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        letras = chr(65 + r) + letras
    return letras


def franjas(modelo, losa, geos=None):
    """Las franjas de la losa, de izquierda a derecha (en u). ValueError si una barra de apoyo queda
    partida entre dos franjas distintas (habría que partir la viga en ese punto)."""
    geos = geometrias(modelo, losa) if geos is None else geos
    if not geos:
        return []
    t = ejes_losa(modelo, losa)[0]
    cortes = sorted({round(x, 6) for g in geos.values() for x in (g.u0, g.u1)})
    unicos = [cortes[0]]
    for x in cortes[1:]:
        if x - unicos[-1] > TOL:
            unicos.append(x)
    elementales = []                                   # (u0, u1, [paños en orden de v])
    for a, b in zip(unicos, unicos[1:]):
        cubren = sorted((g.va, pid) for pid, g in geos.items() if g.u0 <= a + TOL and g.u1 >= b - TOL)
        corrida = []
        for _va, pid in cubren:
            if corrida and abs(geos[corrida[-1]].vb - geos[pid].va) > TOL:
                elementales.append((a, b, corrida))
                corrida = []
            corrida.append(pid)
        if corrida:
            elementales.append((a, b, corrida))

    def firma_numerica(corrida):
        gs = [geos[p] for p in corrida]
        anchos = [gs[0].ancho_a] + [max(g.ancho_b, h.ancho_a) for g, h in zip(gs, gs[1:])] + [gs[-1].ancho_b]
        return (tuple(round(g.claro, 6) for g in gs), tuple(round(x, 6) for x in anchos),
                tuple(round(losa.panos[p].muerta, 6) for p in corrida), tuple(round(losa.panos[p].viva, 6) for p in corrida))

    # Tramos: elementales seguidos (en u) con los mismos paños se unen
    tramos = []                                        # (u0, u1, corrida)
    for a, b, corrida in elementales:
        previo = next((t for t in tramos if abs(t[1] - a) < TOL and t[2] == corrida), None)
        if previo is not None:
            tramos[tramos.index(previo)] = (previo[0], b, corrida)
        else:
            tramos.append((a, b, corrida))
    por_firma = {}
    for a, b, corrida in sorted(tramos, key=lambda t: (t[0], geos[t[2][0]].va)):
        f = firma_numerica(corrida)
        gs = [geos[p] for p in corrida]
        lineas = [gs[0].apoyo_a] + [g.apoyo_b + h.apoyo_a for g, h in zip(gs, gs[1:])] + [gs[-1].apoyo_b]
        apoyos = []
        for barras in lineas:
            dentro = []
            for eid in dict.fromkeys(barras):          # sin repetir, en orden
                u0, u1 = sorted(p @ t for p in _extremos(modelo, eid))
                if u1 <= a + TOL or u0 >= b - TOL:
                    continue                           # fuera de este tramo
                if u0 < a - TOL or u1 > b + TOL:
                    raise ValueError(f"La viga {eid} queda partida entre dos franjas distintas (en u = "
                                     f"{a if u0 < a - TOL else b:.3f} m): pártela en ese punto con un nodo")
                dentro.append(eid)
            apoyos.append(dentro)
        tramo = Tramo(a, b, gs[0].va, list(corrida), apoyos)
        if f not in por_firma:
            claros, anchos, muerta, viva = f
            por_firma[f] = Franja(_letra(len(por_firma)), list(claros), list(anchos), list(muerta), list(viva))
        por_firma[f].tramos.append(tramo)
    return list(por_firma.values())


# ---------------------------------------------------------------- Casos de viva (patrones)
def patrones_automaticos(n):
    """Los casos de viva de §6.4.2 (PDF p. 75) para n claros: [(nombre, claros)]. Todos cargados; los
    impares y los pares (el M+ máximo de un claro sale con L en él y en los alternos); y cada par de
    claros vecinos (el M− máximo de un apoyo, con L solo en los dos claros que llegan a él)."""
    todos = tuple(range(1, n + 1))
    lista = [todos]
    if n >= 2:
        lista += [tuple(range(1, n + 1, 2)), tuple(range(2, n + 1, 2))]
        lista += [(i, i + 1) for i in range(1, n)]
    unicos = list(dict.fromkeys(c for c in lista if c))
    return [(f"Caso {k}", claros) for k, claros in enumerate(unicos, start=1)]


def patrones(losa, franja):
    """Todos los casos de viva de la franja: [(nombre, claros, automatico)]. Los del usuario van al
    final, numerados después de los automáticos."""
    auto = patrones_automaticos(len(franja.claros))
    lista = [(nombre, claros, True) for nombre, claros in auto]
    vistos = {claros for _n, claros, _a in lista}
    for nombre, claros in losa.patrones.get(franja.firma, []):
        claros = tuple(int(c) for c in claros)
        if claros and claros not in vistos and all(1 <= c <= len(franja.claros) for c in claros):
            lista.append((nombre, claros, False))
            vistos.add(claros)
    return lista


def describir_claros(claros):
    """"claros 1, 2 y 3" o "claro 2"."""
    nombres = [str(c) for c in claros]
    if len(nombres) == 1:
        return f"claro {nombres[0]}"
    return "claros " + ", ".join(nombres[:-1]) + " y " + nombres[-1]


# ---------------------------------------------------------------- El modelo de una franja
@dataclass
class SistemaVigueta:
    """Una franja armada como modelo: la vigueta continua con sus casos."""
    losa: int
    franja: Franja
    modelo: object                 # el Modelo generado (no se edita)
    s: float                       # separación de las viguetas (m)
    bf: float
    casos_viva: dict               # claro (1, 2…) -> ID del caso "Viva claro k" en el modelo generado
    patrones: list                 # [(nombre, claros, automatico)]
    caso_peso: int                 # IDs de los casos tipo D del modelo generado
    caso_muerta: int
    casos_patron: dict = field(default_factory=dict)   # índice del patrón -> ID de su caso (con_patrones)

    def casos_de(self, claros):
        """IDs de los casos que entran en una combinación con L en esos claros: los dos de D y los de
        viva de esos claros."""
        return {self.caso_peso, self.caso_muerta} | {self.casos_viva[k] for k in claros}

    @property
    def casos_muertos(self):
        return {self.caso_peso, self.caso_muerta}

    def casos_vista(self, indice):
        """En la vista del sistema (con_patrones): los casos que entran en una combinación con el caso de
        viva número `indice`: los dos de D y el caso de ese patrón."""
        return self.casos_muertos | {self.casos_patron[indice]}

    def es_caso_interno(self, cid):
        """True si el caso es una viva por claro (no se muestra en la lista de casos de la vista)."""
        return cid in self.casos_viva.values()


def sistema(modelo, losa_id, franja, geos=None, con_patrones=False):
    """El SistemaVigueta de una franja: un Modelo con la vigueta en X (de eje a eje de las vigas),
    apoyo fijo en cada apoyo (y φx en el primero, para que la línea no gire sobre su eje: no cambia
    los momentos), la sección T de la losa y sus casos: Peso propio (A·γ, más (s − bf)·hf·γ si
    bf < s), Carga muerta adicional (q·s) y una viva por claro (q·s, solo en ese claro).
    con_patrones: además, un caso por cada caso de viva ("Viva – Caso 2 (claros 1 y 3)"), con la viva
    en sus claros: es lo que muestra la vista del sistema. Las combinaciones del diseño usan las vivas
    por claro (casos_de); en la vista se combina con casos_vista."""
    from modelo.estructura import Modelo
    losa = modelo.losas[losa_id]
    geos = geometrias(modelo, losa) if geos is None else geos
    sec = modelo.secciones[losa.seccion]
    mat = modelo.materiales[sec.material]
    c = sec.concreto
    s = separacion(geos, losa)
    m = Modelo()
    mid = m.agregar_material(mat.nombre, mat.e, mat.g, mat.fc, mat.gamma)
    sid = m.agregar_seccion(sec.nombre, sec.a, sec.iy, sec.iz, sec.j, c, mid)
    xs = [0.0]
    for claro in franja.claros:
        xs.append(xs[-1] + claro)
    nodos = [m.agregar_nodo(x, 0.0, 0.0) for x in xs]
    barras = [m.agregar_elemento(a, b, mid, sid) for a, b in zip(nodos, nodos[1:])]
    for nid in nodos:
        m.restringir(nid, phix=False, phiy=False, phiz=False)          # apoyo fijo
    m.restringir(nodos[0], phix=True, phiy=False, phiz=False)          # y el giro de la línea sobre su eje
    caso_peso = next(cid for cid, caso in m.casos.items() if caso.peso_propio)
    caso_muerta = m.caso_inicial()
    extra = max(0.0, s - c.bf) * c.hf * mat.gamma                      # la losa entre alas, si bf < s
    casos_viva = {}
    for k, eid in enumerate(barras, start=1):
        if extra > 0:
            m.agregar_carga_barra(eid, "uniforme", -extra, "Z", caso=caso_peso)
        if franja.muerta[k - 1]:
            m.agregar_carga_barra(eid, "uniforme", -franja.muerta[k - 1] * s, "Z", caso=caso_muerta)
    for k, eid in enumerate(barras, start=1):
        casos_viva[k] = m.agregar_caso(f"Viva claro {k}", "L")
        if franja.viva[k - 1]:
            m.agregar_carga_barra(eid, "uniforme", -franja.viva[k - 1] * s, "Z", caso=casos_viva[k])
    sv = SistemaVigueta(losa_id, franja, m, s, c.bf, casos_viva, patrones(losa, franja), caso_peso, caso_muerta)
    if con_patrones:
        for i, (nombre, claros, _auto) in enumerate(sv.patrones):
            cid = m.agregar_caso(f"Viva – {nombre} ({describir_claros(claros)})", "L")
            sv.casos_patron[i] = cid
            for k in claros:
                if franja.viva[k - 1]:
                    m.agregar_carga_barra(barras[k - 1], "uniforme", -franja.viva[k - 1] * s, "Z", caso=cid)
    return sv


def sistemas(modelo, losa_id):
    """Los SistemaVigueta de todas las franjas de la losa."""
    losa = modelo.losas[losa_id]
    geos = geometrias(modelo, losa)
    return [sistema(modelo, losa_id, f, geos) for f in franjas(modelo, losa, geos)]


# ---------------------------------------------------------------- Carga de la losa a las vigas
def cargas_a_vigas(modelo):
    """La carga de las losas sobre las vigas del modelo, por caso del modelo: {ID de caso: {ID de
    barra: w}}, con w en kN/m, positiva hacia abajo (−Z global).

    Para cada franja se resuelven sus casos y la reacción de cada apoyo (por vigueta) se divide entre s:
    - peso propio de la losa -> cada caso de peso propio del modelo (por su factor);
    - muerta adicional -> el caso inicial (Carga muerta adicional);
    - viva, con todos los claros cargados -> el caso "Viva de losas".
    ValueError si una losa no se puede armar."""
    from modelo.analisis import analizar
    salida = {}
    if not getattr(modelo, "losas", None):
        return salida
    pesos = {cid: caso.peso_propio for cid, caso in modelo.casos.items() if caso.peso_propio}
    muerta = modelo.caso_inicial()
    viva = modelo.caso_viva_losas()
    for lid, losa in modelo.losas.items():
        if not losa.panos:
            continue
        try:
            lista = sistemas(modelo, lid)
        except ValueError as e:
            raise ValueError(f"{losa.nombre}: {e}") from e
        for sv in lista:
            res = analizar(sv.modelo)
            nodos = sorted(sv.modelo.nodos)

            def reacciones(casos):
                return [sum(float(res[c].res.reacciones[nid][2]) for c in casos) for nid in nodos]

            por_caso = [(pesos, reacciones([sv.caso_peso])), ({muerta: 1.0}, reacciones([sv.caso_muerta])),
                        ({viva: 1.0} if viva is not None else {}, reacciones(list(sv.casos_viva.values())))]
            for destinos, rz in por_caso:
                for cid, factor in destinos.items():
                    cargas = salida.setdefault(cid, {})
                    for tramo in sv.franja.tramos:
                        for j, barras in enumerate(tramo.apoyos):
                            for eid in barras:
                                cargas[eid] = cargas.get(eid, 0.0) + factor * rz[j] / sv.s
    return salida


# ---------------------------------------------------------------- Resumen de la losa (para mostrar)
def resumen(modelo, losa_id):
    """Datos de la losa para Propiedades: s, bf, viguetas por paño, bordes libres y franjas. Un dict;
    con "error" si la losa no se puede armar."""
    losa = modelo.losas[losa_id]
    try:
        geos = geometrias(modelo, losa)
        if not geos:
            return {"error": "La losa no tiene paños"}
        c = concreto(modelo, losa)
        s, u_ref = rejilla(geos, losa, c.b)
        panos = {}
        for pid, g in geos.items():
            us = posiciones(g, s, u_ref, c.b)
            panos[pid] = {"geo": g, "viguetas": us, "bordes": bordes(g, us, c.b)}
        return {"s": s, "u_ref": u_ref, "bf": ala_efectiva(geos, losa, c.b, c.hf), "panos": panos,
                "franjas": franjas(modelo, losa, geos), "ejes": ejes_losa(modelo, losa), "geos": geos,
                "ln_min": claro_libre_minimo(geos)}
    except ValueError as e:
        return {"error": str(e)}


def area_total(geos):
    """Área de la losa (m²), de eje a eje."""
    return sum((g.u1 - g.u0) * g.claro for g in geos.values())


def peso_por_area(modelo, losa, s=None):
    """Peso propio de la losa por m² (kN/m²): (A_T + (s − bf)·hf)·γ / s."""
    sec = modelo.secciones[losa.seccion]
    mat = modelo.materiales[sec.material]
    c = sec.concreto
    if s is None:
        s = separacion(geometrias(modelo, losa), losa)
    area = propiedades_T(c.b, c.h, c.bf, c.hf)[0] + max(0.0, s - c.bf) * c.hf
    return area * mat.gamma / s
