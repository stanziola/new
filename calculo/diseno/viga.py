"""Vigas y viguetas de concreto reforzado: flexión, cortante y deflexiones. SAGRADO.

Fórmulas del ACI 318-19 (páginas del PDF de docs/codigos/), para secciones rectangulares o T (alma
bw y ala de ancho b y espesor hf del lado comprimido). Reciben números y devuelven números.

Unidades: todo en unidades internas (m, m², kN, kN/m², kN·m). Las fórmulas del ACI que llevan √f'c
están escritas en psi: se pasa f'c a psi, se calcula el esfuerzo en psi y se vuelve a kN/m²
(como Ec en calculo/concreto.py).

Flexión (bloque rectangular equivalente):
- εcu = 0.003 (§22.2.2.1, p. 400); 0.85f'c sobre a = β1·c (§22.2.2.4.1, p. 400); β1 de la Tabla
  22.2.2.4.3 (p. 401, la de calculo/interaccion/comun.py); Es = 29 000 ksi (§20.2.2.2, p. 376).
- a = As·fy / (0.85·f'c·b). Si a cabe en el ala (a ≤ hf) la T trabaja como rectángulo de ancho b;
  si no, como T: el ala saliente da Cf = 0.85·f'c·(b − bw)·hf y el alma el resto.
  Mn = As·fy·(d − a/2) (rectángulo) o Cf·(d − hf/2) + 0.85·f'c·bw·a·(d − a/2) (T).
  Supone que el acero en tracción fluye; si no fluye (εt < εty), la sección es controlada por
  compresión, que una viga no puede ser (§9.3.3.1).
- εt = 0.003·(d − c)/c y εty = fy/Es (§21.2.2.1, p. 394). φ de la Tabla 21.2.2 (p. 395), columna
  "otros": 0.65 si εt ≤ εty; 0.90 si εt ≥ εty + 0.003; entre ambos, 0.65 + 0.25·(εt − εty)/0.003.
- Vigas con Pu < 0.10·f'c·Ag: controladas por tracción, εt ≥ εty + 0.003 (§9.3.3.1, p. 132).
- As,min = el mayor de 3√f'c/fy·bw·d y 200/fy·bw·d, con fy ≤ 80 000 psi (§9.6.1.2, p. 137); no
  hace falta si As ≥ 4/3 del requerido (§9.6.1.3, p. 138).

Cortante (Nu = 0: vigas y viguetas sin carga axial):
- Vc de la Tabla 22.5.5.1 (p. 406). Con Av ≥ Av,min: el mayor de (a) 2λ√f'c·bw·d y (b)
  8λ·ρw^(1/3)·√f'c·bw·d (la tabla permite cualquiera de las dos). Con Av < Av,min (sin estribos):
  (c) 8·λs·λ·ρw^(1/3)·√f'c·bw·d, con λs = √(2/(1 + d/10)) ≤ 1, d en pulgadas (§22.5.5.1.3, p. 407) y
  ρw = As/(bw·d). Vc ≤ 5λ√f'c·bw·d (§22.5.5.1.1, p. 407).
- Av,min/s = el mayor de 0.75√f'c·bw/fyt y 50·bw/fyt (Tabla 9.6.3.4, p. 140).
- Vs = Av·fyt·d/s (§22.5.8.5.3, p. 412). φ = 0.75 (Tabla 21.2.1(b), p. 393).
- Dimensiones: Vu ≤ φ(Vc + 8√f'c·bw·d) (§22.5.1.2, p. 404).
- Viguetas: Vc se puede tomar 1.1 veces el de 22.5 (§9.8.1.5, p. 153).

Deflexiones:
- fr = 7.5λ√f'c (§19.2.3.1, p. 358) y Mcr = fr·Ig/yt (Ec. 24.2.3.5, p. 459).
- Icr: sección transformada agrietada, n = Es/Ec, sin acero en compresión (como el SMath del usuario).
  Eje neutro kd: en el ala, rectángulo de ancho b; si pasa al alma, T.
- Ie de la Tabla 24.2.3.5 (p. 459): Ig si Ma ≤ (2/3)Mcr; si no,
  Icr / [1 − ((2/3)Mcr/Ma)²·(1 − Icr/Ig)].
- λΔ = ξ/(1 + 50ρ') (Ec. 24.2.4.1.1, p. 460), ξ de la Tabla 24.2.4.1.3 (p. 460).

Viguetas (§9.8, p. 153–154) y geometría:
- nervio de al menos 4 in de ancho (§9.8.1.2); altura del nervio ≤ 3.5 veces su ancho mínimo
  (§9.8.1.3: se mide bajo la losa, h − hf, como en el SMath; el ACI dice "overall depth of ribs" sin
  definirla); separación libre entre nervios ≤ 30 in (§9.8.1.4); losa sobre encofrado removible de
  al menos 1/12 de la distancia libre entre nervios y 2 in (§9.8.3.1, p. 154).
- Ancho efectivo del ala (Tabla 6.3.2.1, p. 75): a cada lado del alma, el menor de 8h, sw/2 y ℓn/8;
  de un solo lado, el menor de 6h, sw/2 y ℓn/12 (h = espesor de la losa).
- Altura mínima de vigas no presforzadas (Tabla 9.3.1.1, p. 131): ℓ/16 simplemente apoyada, ℓ/18.5
  con un extremo continuo, ℓ/21 con ambos y ℓ/8 en voladizo; con fy ≠ 60 000 psi, por
  (0.4 + fy/100 000) (§9.3.1.1.1). Solo vale si no sostiene elementos que se dañen (§9.3.1.1, p. 130).
- Momento negativo en la cara interior del apoyo exterior de un miembro monolítico con su viga de
  borde (Tabla 6.5.2, p. 76): wu·ℓn²/24.
"""
import math
from dataclasses import dataclass

from calculo.concreto import PSI
from calculo.interaccion.comun import DIAM_ESPECIAL, beta1 as _beta1, ureg

PULGADA = 0.0254                     # m
ES = 29000e3 * PSI                   # §20.2.2.2: 29 000 ksi, en kN/m²
EPS_CU = 0.003                       # §22.2.2.1
PHI_CORTANTE = 0.75                  # Tabla 21.2.1(b)
FACTOR_VC_VIGUETA = 1.1              # §9.8.1.5
FY_MAXIMO_AS_MIN = 80000 * PSI       # §9.6.1.2: fy no pasa de 80 000 psi en As,min
XI = {3: 1.0, 6: 1.2, 12: 1.4, 60: 2.0}      # Tabla 24.2.4.1.3: meses de carga sostenida -> ξ
H_MINIMA = {"simple": 16.0, "un_extremo": 18.5, "ambos": 21.0, "voladizo": 8.0}   # Tabla 9.3.1.1: ℓ / esto


def _raiz(fc):
    """√f'c con f'c en psi: el número de las fórmulas del ACI (un esfuerzo en psi)."""
    return math.sqrt(fc / PSI)


def diametro_barra(n):
    """Diámetro nominal de la barra #n, en m (n/8 in hasta la #8; Apéndice B desde la #9)."""
    return DIAM_ESPECIAL.get(n, n / 8) * PULGADA


def area_barra(n, cantidad=1):
    """Área de `cantidad` barras #n, en m² (π·db²/4, como en los diagramas de interacción)."""
    return cantidad * math.pi * diametro_barra(n) ** 2 / 4


def beta1(fc):
    """β1 (Tabla 22.2.2.4.3) para f'c en kN/m²."""
    return _beta1(fc / PSI / 1000 * ureg.ksi)


def phi_flexion(et, ety):
    """φ de la Tabla 21.2.2, columna "otros" (sin espiral)."""
    if et <= ety:
        return 0.65
    if et >= ety + 0.003:
        return 0.90
    return 0.65 + 0.25 * (et - ety) / 0.003


@dataclass
class Flexion:
    """Resistencia a flexión de una sección. a, c en m; mn y phi_mn en kN·m."""
    a: float
    c: float
    et: float
    ety: float
    phi: float
    mn: float
    phi_mn: float
    como_t: bool                     # el bloque de compresión pasó del ala al alma (trabaja como T)

    @property
    def controlada_traccion(self):
        """εt ≥ εty + 0.003 (§9.3.3.1 y Tabla 21.2.2)."""
        return self.et >= self.ety + 0.003 - 1e-12


def flexion(As, d, fc, fy, b, bw=None, hf=None):
    """Mn y φMn de una sección con As (m²) en tracción a la profundidad d (m), con el lado comprimido
    de ancho b. Si se dan bw y hf (y b > bw), es una T: ala de b × hf sobre un alma de ancho bw.
    El lado comprimido de una vigueta en momento positivo es el ala (b = bf); en momento negativo,
    el alma (b = bw, sin bw ni hf)."""
    if As <= 0 or d <= 0 or b <= 0:
        raise ValueError("As, d y b deben ser positivos")
    k = 0.85 * fc
    a = As * fy / (k * b)
    como_t = bw is not None and hf is not None and b > bw and a > hf
    if como_t:
        cf = k * (b - bw) * hf                          # el ala saliente
        a = (As * fy - cf) / (k * bw)                   # el bloque del alma
        mn = cf * (d - hf / 2) + k * bw * a * (d - a / 2)
    else:
        mn = As * fy * (d - a / 2)
    c = a / beta1(fc)
    et = EPS_CU * (d - c) / c
    ety = fy / ES
    phi = phi_flexion(et, ety)
    return Flexion(a, c, et, ety, phi, mn, phi * mn, como_t)


def as_maximo_traccion(d, fc, fy, b, bw=None, hf=None):
    """El As (m²) con el que la sección queda justo en el límite de tracción controlada,
    εt = εty + 0.003. Con más acero deja de serlo."""
    ety = fy / ES
    c = EPS_CU * d / (EPS_CU + ety + 0.003)
    a = beta1(fc) * c
    k = 0.85 * fc
    if bw is not None and hf is not None and b > bw and a > hf:
        return (k * (b - bw) * hf + k * bw * a) / fy
    return k * b * a / fy


def as_requerido(mu, d, fc, fy, b, bw=None, hf=None):
    """El As (m²) que da φMn = mu (kN·m), con la sección controlada por tracción. None si ni con el
    máximo de tracción controlada alcanza. 0 si mu ≤ 0."""
    if mu <= 0:
        return 0.0
    maximo = as_maximo_traccion(d, fc, fy, b, bw, hf)
    if flexion(maximo, d, fc, fy, b, bw, hf).phi_mn < mu:
        return None
    bajo, alto = 0.0, maximo
    for _ in range(80):                                  # bisección: φMn crece con As
        medio = (bajo + alto) / 2
        if medio > 0 and flexion(medio, d, fc, fy, b, bw, hf).phi_mn >= mu:
            alto = medio
        else:
            bajo = medio
    return alto


def as_minimo(fc, fy, bw, d):
    """As,min (m²) de §9.6.1.2: el mayor de 3√f'c/fy·bw·d y 200/fy·bw·d (f'c y fy en psi; fy hasta
    80 000 psi). En una viga isostática con el ala en tracción, bw es el menor de bf y 2bw: eso lo
    decide quien llama."""
    fy_psi = min(fy, FY_MAXIMO_AS_MIN) / PSI
    return max(3 * _raiz(fc) / fy_psi, 200 / fy_psi) * bw * d


def momento_agrietamiento(fc, ig, yt, lam=1.0):
    """(fr, Mcr): fr = 7.5λ√f'c (kN/m²) y Mcr = fr·Ig/yt (kN·m). yt: del centroide a la fibra en
    tracción (m)."""
    fr = 7.5 * lam * _raiz(fc) * PSI
    return fr, fr * ig / yt


def inercia_agrietada(As, d, n, b, bw=None, hf=None):
    """(kd, Icr): profundidad del eje neutro (m) e inercia de la sección transformada agrietada (m⁴),
    sin acero en compresión. n = Es/Ec. Lado comprimido de ancho b; con bw y hf, una T."""
    if As <= 0 or d <= 0 or b <= 0:
        raise ValueError("As, d y b deben ser positivos")
    rho = As / (b * d)
    kd = (math.sqrt((n * rho) ** 2 + 2 * n * rho) - n * rho) * d        # rectángulo de ancho b
    if bw is not None and hf is not None and b > bw and kd > hf:
        # T: b·hf·(kd − hf/2) + bw·(kd − hf)²/2 = n·As·(d − kd)  ->  A·kd² + B·kd + C = 0
        a2 = bw / 2
        b1 = (b - bw) * hf + n * As
        c0 = -((b - bw) * hf ** 2 / 2 + n * As * d)
        kd = (-b1 + math.sqrt(b1 ** 2 - 4 * a2 * c0)) / (2 * a2)
        # Comprimido: el ala saliente (b − bw) × hf y el alma bw × kd; más el acero transformado
        icr = ((b - bw) * hf ** 3 / 12 + (b - bw) * hf * (kd - hf / 2) ** 2 + bw * kd ** 3 / 3
               + n * As * (d - kd) ** 2)
        return kd, icr
    return kd, b * kd ** 3 / 3 + n * As * (d - kd) ** 2


def inercia_efectiva(ma, mcr, ig, icr):
    """Ie de la Tabla 24.2.3.5 (m⁴), con el momento de servicio Ma (kN·m, en valor absoluto)."""
    ma = abs(ma)
    if ma <= 2 / 3 * mcr:
        return ig
    return min(ig, icr / (1 - (2 / 3 * mcr / ma) ** 2 * (1 - icr / ig)))


def lambda_delta(xi, rho_prima=0.0):
    """λΔ = ξ/(1 + 50ρ') (Ec. 24.2.4.1.1): multiplica la deflexión inmediata por carga sostenida."""
    return xi / (1 + 50 * rho_prima)


def lambda_s(d):
    """Factor de tamaño λs = √(2/(1 + d/10)) ≤ 1, con d en pulgadas (Ec. 22.5.5.1.3)."""
    return min(1.0, math.sqrt(2 / (1 + d / PULGADA / 10)))


def vc(fc, bw, d, As, con_av_min, lam=1.0):
    """(Vc en kN, ecuación de la Tabla 22.5.5.1 usada: "a", "b" o "c"), con Nu = 0.
    con_av_min: True si Av ≥ Av,min (entonces el mayor de (a) y (b)); False: la (c), con λs.
    Con el tope de §22.5.5.1.1."""
    raiz = _raiz(fc) * PSI                           # √f'c, como esfuerzo en kN/m²
    rho_w = max(As, 0.0) / (bw * d)
    if con_av_min:
        va = 2 * lam * raiz * bw * d
        vb = 8 * lam * rho_w ** (1 / 3) * raiz * bw * d
        valor, ecuacion = (va, "a") if va >= vb else (vb, "b")
    else:
        valor, ecuacion = 8 * lambda_s(d) * lam * rho_w ** (1 / 3) * raiz * bw * d, "c"
    return max(0.0, min(valor, 5 * lam * raiz * bw * d)), ecuacion


def av_minimo_por_s(fc, fyt, bw):
    """Av,min/s (m²/m) de la Tabla 9.6.3.4: el mayor de 0.75√f'c·bw/fyt y 50·bw/fyt (en psi)."""
    fyt_psi = fyt / PSI
    return max(0.75 * _raiz(fc) / fyt_psi, 50 / fyt_psi) * bw


def vs(av, fyt, d, s):
    """Vs = Av·fyt·d/s (kN), Ec. 22.5.8.5.3."""
    return av * fyt * d / s


def vn_maximo(fc, bw, d, vc_):
    """Vc + 8√f'c·bw·d (kN): Vu no puede pasar de φ veces esto (§22.5.1.2)."""
    return vc_ + 8 * _raiz(fc) * PSI * bw * d


def ancho_efectivo(bw, hf, sw, ln, un_lado=False):
    """bf (m) de la Tabla 6.3.2.1: el alma más el ala que trabaja, a cada lado (o de un solo lado).
    sw: distancia libre al alma vecina; ln: claro libre."""
    if un_lado:
        return bw + min(6 * hf, sw / 2, ln / 12)
    return bw + 2 * min(8 * hf, sw / 2, ln / 8)


def limites_vigueta(bw, h, hf, libre):
    """Límites de §9.8 para una vigueta de nervio bw, altura total h y losa hf, con `libre` la
    distancia libre entre nervios (m). {nombre: valor límite en m}:
    - "ancho_minimo": el nervio debe medir al menos esto (4 in, §9.8.1.2);
    - "altura_maxima": la altura del nervio bajo la losa, h − hf, no debe pasar de esto (3.5·bw, §9.8.1.3);
    - "separacion_maxima": la distancia libre entre nervios no debe pasar de esto (30 in, §9.8.1.4);
    - "losa_minima": la losa debe medir al menos esto (el mayor de libre/12 y 2 in, §9.8.3.1)."""
    return {"ancho_minimo": 4 * PULGADA, "altura_maxima": 3.5 * bw, "separacion_maxima": 30 * PULGADA,
            "losa_minima": max(libre / 12, 2 * PULGADA)}


def h_minima(largo, condicion, fy):
    """Altura mínima (m) de la Tabla 9.3.1.1 para el claro ℓ (m) y la condición de apoyo ("simple",
    "un_extremo", "ambos" o "voladizo"), con la corrección por fy de §9.3.1.1.1 (concreto de peso
    normal)."""
    return largo / H_MINIMA[condicion] * (0.4 + fy / PSI / 100000)


def momento_negativo_exterior(wu, ln):
    """wu·ℓn²/24 (kN·m): Tabla 6.5.2, cara interior del apoyo exterior de un miembro construido
    monolíticamente con su viga de borde."""
    return wu * ln ** 2 / 24
