"""Diseño de la vigueta de una losa: envolventes de todos sus sistemas, deflexiones y comprobaciones.

No es cálculo: junta los resultados de las franjas (modelo/losas.py, modelo/analisis.py) y llama a
las fórmulas de calculo/diseno/viga.py. Las comparaciones (cumple o no) y sus textos viven aquí.

Qué se hace (ACI 318-19; páginas del PDF de docs/codigos/):
1. Cada franja de la losa se resuelve con sus casos: peso propio, carga muerta adicional y una viva
   por claro (modelo/losas.sistema).
2. Diseño: para cada caso de viva (patrón, §6.4.2) y cada una de las 13 combinaciones de resistencia,
   la combinación con la viva solo en esos claros. De todas, en todas las franjas:
   - Mu+ máximo de cada claro (el mayor My positivo a lo largo del claro);
   - Mu− en la cara de cada apoyo (a b/2 del eje; §9.4.2.1, p. 132);
   - Vu en la cara de cada apoyo (§9.4.3.1: la vigueta llega al costado de la viga, apoyo indirecto,
     y la figura R9.4.3.2(e), p. 134, pone ahí la sección crítica; decisión del usuario).
3. Servicio y deflexiones (§24.2): Ma de cada claro por NIVEL de carga, el máximo entre los patrones:
   D (la carga muerta), D + L (CC-1a) y la sostenida D + 0.5L (CC-2). Con cada Ma, Ie del claro
   (Tabla 24.2.3.5; a media luz, §24.2.3.7) y la franja se vuelve a resolver con I = Ie claro por
   claro (un análisis por nivel). Así:
   - ΔL = Δ(D + L) − Δ(D), cada una con su Ie, contra ℓ/360 (Tabla 24.2.2, pisos);
   - lo que ocurre después de colocar los elementos no estructurales = λΔ·Δ(D + 0.5L) + ΔL, contra
     ℓ/480 si sostiene elementos que se dañan (o ℓ/240). Con la ΔL completa (del lado seguro: la
     tabla pide solo la de la viva adicional a la sostenida). λΔ = ξ/(1 + 50ρ'), con ρ' = 0 a media
     luz (el acero de arriba es de los apoyos).
   ℓ es el claro de eje a eje (la notación del ACI).
4. Comprobaciones: las de la hoja de SMath del usuario y las que le faltaban (tracción controlada,
   cortante, ℓ/360), cada una con su cláusula.
"""
from dataclasses import dataclass, field

import numpy as np

from calculo.concreto import propiedades_T
from calculo.diseno import viga as formulas
from modelo import combinaciones as comb
from modelo import concreto as cc
from modelo import losas as ml
from calculo.rigidez import diagramas
from modelo.analisis import ModeloAgrietado, analizar, analizar_con_inercias, desplazamientos_globales, geometria
from modelo.estructura import nombre_combinacion

PUNTOS_DEFLEXION = 41                  # puntos a lo largo de cada claro para buscar la deflexión máxima
N_FINO = 201                           # puntos de la integración de la deflexión (diagramas.deformada)


def niveles(losa):
    """Los niveles de carga de las deflexiones: {clave: (nombre, factores, fracción de L)}. La carga
    sostenida es D + ψL, con ψ = losa.sostenida (0.5 por defecto: la CC-2 de ASCE 7-05; 0 = solo D)."""
    psi = float(losa.sostenida)
    nombre_sost = "D" if psi == 0 else f"D + {psi:g}L"
    return {"D": ("Carga muerta (D)", {"D": 1.0}, 0.0),
            "D+L": ("D + L (servicio)", {"D": 1.0, "L": 1.0}, 1.0),
            "sostenida": (f"{nombre_sost} (sostenida)", {"D": 1.0, "L": psi} if psi else {"D": 1.0}, psi)}


@dataclass
class Valor:
    """Un valor de diseño y dónde sale: franja, claro o apoyo, caso de viva y combinación."""
    valor: float = 0.0
    franja: str = ""
    lugar: str = ""                    # "claro 2", "apoyo 3 (cara izquierda)"
    caso: str = ""                     # caso de viva
    combinacion: str = ""

    def detalle(self):
        partes = [p for p in (self.franja, self.lugar, self.caso, self.combinacion) if p]
        return " · ".join(partes)


@dataclass
class Comprobacion:
    """Una comprobación: el valor contra el límite, si cumple y de qué cláusula sale.
    cumple: True, False o None (informativa o no evaluada)."""
    grupo: str                         # "Viguetas (§9.8)", "Flexión", "Cortante", "Deflexión"
    nombre: str
    valor: float
    limite: float
    relacion: str                      # "≥" o "≤": valor relacion limite
    magnitud: str                      # para mostrar con unidades: "seccion", "momento", "fuerza", "desplazamiento", ""
    cumple: object
    clausula: str
    detalle: str = ""
    tipo: str = "obligatoria"          # "obligatoria", "recomendada" o "informativa"


@dataclass
class ResultadoFranja:
    sistema: object                    # losas.SistemaVigueta
    resultados: dict                   # {ID de caso: ResultadoCaso}
    mu_pos: list = field(default_factory=list)     # Valor por claro
    mu_neg: list = field(default_factory=list)     # Valor por apoyo (el mayor de sus dos caras)
    vu: list = field(default_factory=list)         # Valor por apoyo
    ma: dict = field(default_factory=dict)         # nivel -> [Ma por claro] (kN·m)
    ie: dict = field(default_factory=dict)         # nivel -> [Ie por claro] (m⁴)
    delta_l: list = field(default_factory=list)    # Valor por claro (m, hacia abajo)
    delta_largo: list = field(default_factory=list)
    mu_exterior: list = field(default_factory=list)   # wu·ℓn²/24 en cada apoyo exterior (kN·m)


@dataclass
class DisenoLosa:
    """Todo lo de la vigueta de una losa: sección, propiedades, resultados por franja, lo máximo y las
    comprobaciones."""
    losa: int
    nombre: str
    concreto: object
    s: float
    bf: float
    ig: float
    yb: float
    mcr_pos: float
    icr_pos: float
    flexion_pos: object
    flexion_neg: object                # None si no tiene acero arriba
    franjas: list
    mu_pos: Valor
    mu_neg: Valor
    vu: Valor
    delta_l: Valor
    delta_largo: Valor
    ma: Valor                          # el mayor Ma de D + L
    comprobaciones: list
    error: str = ""


def _max(actual, valor, **donde):
    return Valor(valor, **donde) if valor > actual.valor else actual


def combinaciones_efectivas(m):
    """Las 13 de resistencia reducidas a los tipos de caso que hay en la vigueta (D y L): las que dan
    lo mismo se juntan. [(nombre efectivo, factores, claves de la norma)], por ejemplo
    ("1.2D + 1.6L", {"D": 1.2, "L": 1.6}, ["C2"])."""
    tipos = {c.tipo for c in m.casos.values()}
    unicas = {}
    for clave, co in comb.aplicables(m).items():
        f = {t: v for t, v in co.factores.items() if t in tipos}
        llave = tuple(sorted(f.items()))
        if llave in unicas:
            unicas[llave][2].append(clave)
        else:
            unicas[llave] = (nombre_combinacion(f), f, [clave])
    return list(unicas.values())


def _suma(por_caso, m, factores, casos, k, i):
    """Σ factor del tipo × (arreglo i del caso) en la barra k, con los casos dados (superposición)."""
    total = 0.0
    for c in casos:
        f = factores.get(m.casos[c].tipo, 0.0)
        if f:
            total = total + f * por_caso[c][k][i]
    return np.asarray(total, dtype=float)


def _puntos(sv, ln_caras):
    """Los puntos de cada claro donde se evalúan los diagramas (41 parejos y las dos caras de los
    apoyos) y en qué posición quedan las caras: [(x, i_cara_i, i_cara_j)]."""
    salida = []
    for k, largo in enumerate(sv.franja.claros):
        xi, xj = ln_caras[k], largo - ln_caras[k + 1]
        x = np.unique(np.concatenate([np.linspace(0.0, largo, 41), [xi, xj]]))
        salida.append((x, int(np.argmin(np.abs(x - xi))), int(np.argmin(np.abs(x - xj)))))
    return salida


def _diagramas_por_caso(m, res, puntos):
    """{ID de caso: [(My, Vz) de cada claro, en sus puntos]}: cada caso una sola vez; las combinaciones
    salen sumando estos arreglos (el análisis es lineal)."""
    barras = sorted(m.elementos)
    salida = {}
    for cid, rc in res.items():
        lista = []
        for k, eid in enumerate(barras):
            _r, _t, largo = geometria(m, eid)
            d = diagramas.internas(largo, rc.res.fuerzas[eid], rc.cargas_locales.get(eid, []), x=puntos[k][0])
            lista.append((np.asarray(d["My"], dtype=float), np.asarray(d["Vz"], dtype=float)))
        salida[cid] = lista
    return salida


def _envolventes(sv, por_caso, puntos):
    """Mu+ por claro, Mu− y Vu por apoyo (en las caras), con dónde salen, en la franja sv: todos los
    casos de viva × las combinaciones de resistencia (las efectivas)."""
    m = sv.modelo
    n = len(sv.franja.claros)
    mu_pos = [Valor() for _ in range(n)]
    mu_neg = [Valor() for _ in range(n + 1)]
    vu = [Valor() for _ in range(n + 1)]
    for nombre_co, factores, _claves in combinaciones_efectivas(m):
        patrones = sv.patrones if "L" in factores else [("", (), True)]    # sin L, el caso de viva no cuenta
        for nombre_caso, claros, _auto in patrones:
            casos = sv.casos_de(claros)
            caso = f"{nombre_caso} ({ml.describir_claros(claros)})" if claros else ""
            for k in range(n):
                my = _suma(por_caso, m, factores, casos, k, 0)
                vz = _suma(por_caso, m, factores, casos, k, 1)
                if my.ndim == 0:
                    continue
                i = int(np.argmax(my))
                mu_pos[k] = _max(mu_pos[k], float(my[i]), franja=sv.franja.nombre, lugar=f"claro {k + 1}",
                                 caso=caso, combinacion=nombre_co)
                _x, ii, ij = puntos[k]
                for lado, idx, j in (("derecha", ii, k), ("izquierda", ij, k + 1)):
                    lugar = f"apoyo {j + 1} (cara {lado})"
                    mu_neg[j] = _max(mu_neg[j], -float(my[idx]), franja=sv.franja.nombre, lugar=lugar,
                                     caso=caso, combinacion=nombre_co)
                    vu[j] = _max(vu[j], abs(float(vz[idx])), franja=sv.franja.nombre, lugar=lugar,
                                 caso=caso, combinacion=nombre_co)
    return mu_pos, mu_neg, vu


def _momentos_servicio(sv, por_caso, niveles_):
    """{nivel: [Ma de cada claro]}: el mayor momento positivo de servicio de cada claro, entre los
    casos de viva."""
    m = sv.modelo
    n = len(sv.franja.claros)
    salida = {}
    for nivel, (_nombre, factores, _fl) in niveles_.items():
        lista = [0.0] * n
        patrones = sv.patrones if "L" in factores else [("", (), True)]
        for _n, claros, _a in patrones:
            casos = sv.casos_de(claros)
            for k in range(n):
                my = _suma(por_caso, m, factores, casos, k, 0)
                if my.ndim:
                    lista[k] = max(lista[k], float(my.max()))
        salida[nivel] = lista
    return salida


def _deflexiones(sv, ie, ig, niveles_):
    """{nivel: {(caso, claros): [deflexión hacia abajo de cada claro, en PUNTOS_DEFLEXION puntos]}} (m).
    Cada nivel se resuelve con su Ie por claro; dentro de un nivel, la deflexión de cada caso se
    calcula una vez y los casos de viva salen sumando (el análisis con esas inercias es lineal)."""
    m = sv.modelo
    barras = sorted(m.elementos)
    por_nivel = {}
    for nivel, (_nombre, factores, _fl) in niveles_.items():
        inercias = {eid: ie[nivel][k] / ig for k, eid in enumerate(barras)}
        res = analizar_con_inercias(m, inercias)
        # La curva entre nodos se integra con la sección de la vista (Ie), como la resolvió el análisis
        vista = ModeloAgrietado(m, inercias)
        por_caso = {cid: [(-np.asarray(desplazamientos_globales(
            vista, rc, eid, np.linspace(0, sv.franja.claros[k], PUNTOS_DEFLEXION), n_fino=N_FINO)["Dz"], dtype=float),)
            for k, eid in enumerate(barras)] for cid, rc in res.items()}
        patrones = sv.patrones if "L" in factores else [("", (), True)]
        por_nivel[nivel] = {(nombre_caso, claros): [_suma(por_caso, m, factores, sv.casos_de(claros), k, 0)
                                                    for k in range(len(barras))]
                            for nombre_caso, claros, _a in patrones}
    return por_nivel


def disenar_losa(modelo, losa_id):
    """El DisenoLosa de la losa: analiza todas sus franjas. Si la losa no se puede armar, el error va
    en `error` y lo demás queda vacío."""
    losa = modelo.losas[losa_id]
    sec = modelo.secciones.get(losa.seccion)
    c = sec.concreto if sec is not None else None
    vacio = Valor()
    try:
        if c is None or c.forma != "T":
            raise ValueError("La vigueta debe ser una sección T de concreto")
        mat = modelo.materiales[sec.material]
        geos = ml.geometrias(modelo, losa)
        if not geos:
            raise ValueError("La losa no tiene paños")
        lista = [ml.sistema(modelo, losa_id, f, geos) for f in ml.franjas(modelo, losa, geos)]
    except (ValueError, KeyError) as e:
        return DisenoLosa(losa_id, losa.nombre, c, 0, 0, 0, 0, 0, 0, None, None, [], vacio, vacio, vacio, vacio,
                          vacio, vacio, [], str(e))
    fc, fy = c.fc, c.fy
    _a, ig, _iz, _j, yb = propiedades_T(c.b, c.h, c.bf, c.hf)
    s = lista[0].s
    dpos, dneg = cc.peralte_positivo(c), cc.peralte_negativo(c)
    as_inf, as_sup = cc.area_inferior(c), cc.area_superior(c)
    _fr, mcr = formulas.momento_agrietamiento(fc, ig, yb)
    n_mod = formulas.ES / mat.e
    _kd, icr = formulas.inercia_agrietada(as_inf, dpos, n_mod, c.bf, c.b, c.hf)
    fpos = formulas.flexion(as_inf, dpos, fc, fy, c.bf, c.b, c.hf)
    fneg = formulas.flexion(as_sup, dneg, fc, fy, c.b) if c.n_sup else None
    lam = formulas.lambda_delta(losa.xi, 0.0)

    franjas = []
    tot = {"mu_pos": Valor(), "mu_neg": Valor(), "vu": Valor(), "dl": Valor(), "dlargo": Valor(), "ma": Valor()}
    niveles_ = niveles(losa)
    for sv in lista:
        res = analizar(sv.modelo)
        puntos = _puntos(sv, [a / 2 for a in sv.franja.anchos])
        por_caso = _diagramas_por_caso(sv.modelo, res, puntos)
        mu_pos, mu_neg, vu = _envolventes(sv, por_caso, puntos)
        ma = _momentos_servicio(sv, por_caso, niveles_)
        ie = {nivel: [formulas.inercia_efectiva(x, mcr, ig, icr) for x in valores] for nivel, valores in ma.items()}
        por_nivel = _deflexiones(sv, ie, ig, niveles_)
        r = ResultadoFranja(sv, res, mu_pos, mu_neg, vu, ma, ie)
        d_muerta = por_nivel["D"][("", ())]
        for k, largo in enumerate(sv.franja.claros):
            dl, dlargo = Valor(), Valor()
            for (nombre_caso, claros), deflexion in por_nivel["D+L"].items():
                caso = f"{nombre_caso} ({ml.describir_claros(claros)})"
                d_l = deflexion[k] - d_muerta[k]
                tabla = por_nivel["sostenida"]               # sin viva sostenida: una sola, la de D
                sost = tabla.get((nombre_caso, claros), tabla.get(("", ())))[k]
                dl = _max(dl, float(d_l.max()), franja=sv.franja.nombre, lugar=f"claro {k + 1}", caso=caso)
                dlargo = _max(dlargo, float((lam * sost + d_l).max()), franja=sv.franja.nombre,
                              lugar=f"claro {k + 1}", caso=caso)
            r.delta_l.append(dl)
            r.delta_largo.append(dlargo)
        # wu·ℓn²/24 en los apoyos exteriores (Tabla 6.5.2): wu con todos los claros cargados
        for k in (0, len(sv.franja.claros) - 1):        # el claro de cada extremo
            wu = 1.2 * (_peso_por_m(sv) + sv.franja.muerta[k] * s) + 1.6 * sv.franja.viva[k] * s
            r.mu_exterior.append(formulas.momento_negativo_exterior(wu, sv.franja.libre(k)))
        for clave, lista_valores in (("mu_pos", mu_pos), ("mu_neg", mu_neg), ("vu", vu), ("dl", r.delta_l),
                                     ("dlargo", r.delta_largo)):
            for v in lista_valores:
                if v.valor > tot[clave].valor:
                    tot[clave] = v
        for k, x in enumerate(ma["D+L"]):
            if x > tot["ma"].valor:
                tot["ma"] = Valor(x, sv.franja.nombre, f"claro {k + 1}", "el mayor de los casos de viva",
                                  "D + L (servicio)")
        franjas.append(r)
    d = DisenoLosa(losa_id, losa.nombre, c, s, c.bf, ig, yb, mcr, icr, fpos, fneg, franjas, tot["mu_pos"],
                   tot["mu_neg"], tot["vu"], tot["dl"], tot["dlargo"], tot["ma"], [])
    d.comprobaciones = comprobaciones(modelo, losa, d, geos)
    return d


def _peso_por_m(sv):
    """Peso propio de la vigueta por metro (kN/m), con la losa entre alas si bf < s."""
    m = sv.modelo
    sec = next(iter(m.secciones.values()))
    mat = next(iter(m.materiales.values()))
    c = sec.concreto
    return (sec.a + max(0.0, sv.s - c.bf) * c.hf) * mat.gamma


# ---------------------------------------------------------------- Comprobaciones
PAG = {"9.8.1.2": 153, "9.8.1.3": 153, "9.8.1.4": 153, "9.8.1.5": 153, "9.8.1.6": 153, "9.8.1.7": 153,
       "9.8.3.1": 154, "6.3.2.1": 75, "9.3.1.1": 131, "9.5.1.1": 135, "9.3.3.1": 132, "9.6.1.2": 137,
       "22.5.5.1": 406, "22.5.1.2": 404, "24.2.2": 458, "6.5.2": 76, "9.6.3.1": 138}


def _cita(clausula, texto=None):
    """"ACI 318-19 §9.8.1.2 (p. 153)"; con texto (que ya dice sus páginas), ese texto."""
    if texto:
        return f"ACI 318-19 {texto}"
    pag = PAG.get(clausula)
    return f"ACI 318-19 §{clausula}" + (f" (p. {pag})" if pag else "")


def comprobaciones(modelo, losa, d, geos):
    """La lista de Comprobacion de la vigueta (en el orden en que se muestran)."""
    c = d.concreto
    fc, fy = c.fc, c.fy
    lista = []

    def agregar(grupo, nombre, valor, relacion, limite, magnitud, clausula, detalle="", tipo="obligatoria",
                cumple=None, cita=None):
        if cumple is None and tipo != "informativa" and limite is not None and valor is not None:
            holgura = max(1e-9, 1e-6 * abs(limite))          # que un redondeo no haga fallar una igualdad
            cumple = valor >= limite - holgura if relacion == "≥" else valor <= limite + holgura
        lista.append(Comprobacion(grupo, nombre, valor, limite, relacion, magnitud, cumple,
                                  _cita(clausula, cita), detalle, tipo))

    # ---- Viguetas (§9.8)
    resumen = ml.resumen(modelo, d.losa)
    lim = formulas.limites_vigueta(c.b, c.h, c.hf, d.s - c.b)
    g = "Viguetas (§9.8)"
    agregar(g, "Ancho del nervio bw", c.b, "≥", lim["ancho_minimo"], "seccion", "9.8.1.2")
    agregar(g, "Altura del nervio bajo la losa h − hf", c.h - c.hf, "≤", lim["altura_maxima"], "seccion", "9.8.1.3",
            "3.5·bw")
    libre = d.s - c.b
    peor, donde = libre, "entre viguetas"
    for pid, datos in resumen.get("panos", {}).items():
        if datos["bordes"] is not None:
            for lado, gap in zip(("borde 1", "borde 2"), datos["bordes"]):
                if gap > peor:
                    peor, donde = gap, f"paño {pid}, {lado} (a la viga o al borde)"
        elif datos["geo"].libre_1 - datos["geo"].libre_0 > peor:
            peor, donde = datos["geo"].libre_1 - datos["geo"].libre_0, f"paño {pid}: no le cabe ninguna vigueta"
    agregar(g, "Separación libre entre nervios", peor, "≤", lim["separacion_maxima"], "seccion", "9.8.1.4", donde)
    lim_losa = formulas.limites_vigueta(c.b, c.h, c.hf, peor)["losa_minima"]
    agregar(g, "Espesor de la losa hf", c.hf, "≥", lim_losa, "seccion", "9.8.3.1",
            "el mayor de (libre)/12 y 2 in (encofrado removible)")
    agregar(g, "Barra inferior continua en cada nervio", 1.0, "≥", 1.0, "", "9.8.1.6",
            "el programa la dibuja y la supone continua y anclada en los apoyos", tipo="informativa", cumple=True)
    agregar(g, "Refuerzo de la losa perpendicular a los nervios", None, "", None, "", "9.8.1.7",
            "flexión de la losa y al menos el de retracción y temperatura (24.4): todavía no se evalúa",
            tipo="informativa", cumple=None)
    efectivo = formulas.ancho_efectivo(c.b, c.hf, d.s - c.b, resumen.get("ln_min", 0.0) or 0.0)
    agregar("Geometría", "Ancho del ala bf", c.bf, "≤", min(d.s, efectivo), "seccion", "6.3.2.1",
            f"el menor de s = {d.s * 100:.1f} cm y el ancho efectivo de la tabla")
    for pid, datos in resumen.get("panos", {}).items():
        geo = datos["geo"]
        for lado, lateral in (("1", geo.lateral_0), ("2", geo.lateral_1)):
            if not lateral:
                agregar("Geometría", f"Paño {pid}: borde {lado} sin viga lateral", None, "", None, "", "6.3.2.1",
                        "la vigueta del borde tiene ala de un solo lado: el menor de 6h, sw/2 y ℓn/12; se diseña "
                        "con la misma T (revísala si el borde carga más)", tipo="informativa", cumple=None)
    for r in d.franjas:
        n = len(r.sistema.franja.claros)
        for k, largo in enumerate(r.sistema.franja.claros):
            condicion = "simple" if n == 1 else ("un_extremo" if k in (0, n - 1) else "ambos")
            texto = {"simple": "ℓ/16", "un_extremo": "ℓ/18.5", "ambos": "ℓ/21"}[condicion]
            agregar("Geometría", f"{r.sistema.franja.nombre}, claro {k + 1}: altura h", c.h, "≥",
                    formulas.h_minima(largo, condicion, fy), "seccion", "9.3.1.1",
                    f"{texto} con ℓ = {largo:.2f} m. Informativa: con tabiques que se dañan no exime de calcular "
                    "la deflexión", tipo="informativa", cumple=c.h >= formulas.h_minima(largo, condicion, fy) - 1e-9)

    # ---- Flexión
    g = "Flexión"
    agregar(g, "φMn+ ≥ Mu+ (máximo)", d.flexion_pos.phi_mn, "≥", d.mu_pos.valor, "momento", "9.5.1.1",
            d.mu_pos.detalle())
    agregar(g, "Positivo: controlada por tracción εt", d.flexion_pos.et, "≥", d.flexion_pos.ety + 0.003, "", "9.3.3.1",
            "εt ≥ εty + 0.003 (Tabla 21.2.2)")
    asmin_pos = formulas.as_minimo(fc, fy, c.b, cc.peralte_positivo(c))
    asreq_pos = formulas.as_requerido(d.mu_pos.valor, cc.peralte_positivo(c), fc, fy, c.bf, c.b, c.hf) or 0.0
    agregar(g, "Positivo: As ≥ As,min", cc.area_inferior(c), "≥", min(asmin_pos, 4 / 3 * asreq_pos) if asreq_pos else asmin_pos,
            "area", "9.6.1.2", "el mayor de 3√f'c/fy·bw·d y 200/fy·bw·d, o 4/3 del requerido (§9.6.1.3)")
    agregar(g, "Positivo: bloque de compresión en el ala (a ≤ hf)", d.flexion_pos.a, "≤", c.hf, "seccion",
            "22.2.2.4.1", "si no, la T se calcula como T (el programa lo hace)", tipo="informativa",
            cumple=d.flexion_pos.a <= c.hf, cita="§22.2.2.4.1 (p. 400)")
    if d.flexion_neg is not None:
        agregar(g, "φMn− ≥ Mu− (en la cara)", d.flexion_neg.phi_mn, "≥", d.mu_neg.valor, "momento", "9.5.1.1",
                d.mu_neg.detalle())
        agregar(g, "Negativo: controlada por tracción εt", d.flexion_neg.et, "≥", d.flexion_neg.ety + 0.003, "",
                "9.3.3.1", "εt ≥ εty + 0.003 (Tabla 21.2.2)")
        asmin_neg = formulas.as_minimo(fc, fy, c.b, cc.peralte_negativo(c))
        asreq_neg = formulas.as_requerido(d.mu_neg.valor, cc.peralte_negativo(c), fc, fy, c.b) or 0.0
        agregar(g, "Negativo: As ≥ As,min", cc.area_superior(c), "≥",
                min(asmin_neg, 4 / 3 * asreq_neg) if asreq_neg else asmin_neg, "area", "9.6.1.2",
                "el mayor de 3√f'c/fy·bw·d y 200/fy·bw·d, o 4/3 del requerido (§9.6.1.3)")
        exterior = max((x for r in d.franjas for x in r.mu_exterior), default=0.0)
        agregar(g, "Apoyo exterior: φMn− ≥ wu·ℓn²/24", d.flexion_neg.phi_mn, "≥", exterior, "momento", "6.5.2",
                "el modelo con apoyos simples da M− = 0 en el borde; una vigueta monolítica con su viga de borde "
                "tiene este momento (Tabla 6.5.2)", tipo="recomendada")
    else:
        agregar(g, "Acero arriba para Mu− (en la cara)", 0.0, "≥", d.mu_neg.valor, "momento", "9.5.1.1",
                "la sección no tiene barras arriba: " + d.mu_neg.detalle(), cumple=d.mu_neg.valor <= 1e-9)

    # ---- Cortante (en la cara del apoyo)
    g = "Cortante"
    if c.n_sup:
        as_v, d_v = cc.area_superior(c), cc.peralte_negativo(c)
    else:
        as_v, d_v = cc.area_inferior(c), cc.peralte_positivo(c)
    av = 2 * formulas.area_barra(c.estribo) if c.estribo else 0.0
    con_min = bool(c.estribo) and av / c.s_estribo >= formulas.av_minimo_por_s(fc, fy, c.b) - 1e-12
    vc, ecuacion = formulas.vc(fc, c.b, d_v, as_v, con_min)
    vs = formulas.vs(av, fy, d_v, c.s_estribo) if c.estribo else 0.0
    phi_vn = formulas.PHI_CORTANTE * (formulas.FACTOR_VC_VIGUETA * vc + vs)
    texto_vc = {"a": "(a) 2λ√f'c·bw·d", "b": "(b) 8λρw^(1/3)√f'c·bw·d",
                "c": "(c) 8λsλρw^(1/3)√f'c·bw·d, sin Av,min"}[ecuacion]
    agregar(g, "φ(1.1·Vc + Vs) ≥ Vu (en la cara)", phi_vn, "≥", d.vu.valor, "fuerza", "22.5.5.1",
            f"Vc con {texto_vc}; × 1.1 de viguetas (§9.8.1.5); φ = 0.75. {d.vu.detalle()}",
            cita="§22.5.5.1, Tabla 22.5.5.1 y §9.8.1.5 (p. 406 y 153)")
    agregar(g, "Dimensiones: Vu ≤ φ(Vc + 8√f'c·bw·d)", d.vu.valor, "≤",
            formulas.PHI_CORTANTE * formulas.vn_maximo(fc, c.b, d_v, vc), "fuerza", "22.5.1.2")
    if not c.estribo:
        agregar(g, "Sin estribos: Vu ≤ φ·1.1·Vc", d.vu.valor, "≤", formulas.PHI_CORTANTE * formulas.FACTOR_VC_VIGUETA * vc,
                "fuerza", "9.6.3.1", "en viguetas, Av,min no hace falta si Vu ≤ φVc (Tabla 9.6.3.1)",
                cita="Tabla 9.6.3.1 (p. 138)")

    # ---- Deflexión
    g = "Deflexión"
    for r in d.franjas:
        for k, largo in enumerate(r.sistema.franja.claros):
            nombre = f"{r.sistema.franja.nombre}, claro {k + 1}"
            agregar(g, f"{nombre}: ΔL inmediata ≤ ℓ/360", r.delta_l[k].valor, "≤", largo / 360, "desplazamiento",
                    "24.2.2", f"{r.delta_l[k].caso}; Ie(D+L) = {r.ie['D+L'][k] / d.ig:.2f}·Ig",
                    cita="Tabla 24.2.2 (p. 458)")
            limite = largo / (480 if losa.fragiles else 240)
            agregar(g, f"{nombre}: λΔ·Δsost + ΔL ≤ ℓ/{480 if losa.fragiles else 240}", r.delta_largo[k].valor, "≤",
                    limite, "desplazamiento", "24.2.2",
                    f"{r.delta_largo[k].caso}; sostenida {niveles(losa)['sostenida'][0].split(' (')[0]}; "
                    f"λΔ = {formulas.lambda_delta(losa.xi):.2f} (ξ = {losa.xi:g}, ρ' = 0); ℓ/"
                    f"{480 if losa.fragiles else 240}: {'sostiene' if losa.fragiles else 'no sostiene'} elementos "
                    "que se dañan", cita="Tabla 24.2.2 y §24.2.4.1 (p. 458 y 460)")
    return lista
