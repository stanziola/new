"""Combinaciones de carga que el programa trae cargadas (las predeterminadas): de resistencia y de
servicio.

RESISTENCIA (para Mu, Vu, Pu: el diseño). Son las de ASCE 7-05 §2.3.2 (PDF p. 34), que el REP 2021
§1.4.1 manda usar, con las sísmicas de §12.4.2.3 (PDF p. 156):

    1. 1.4(D + F)
    2. 1.2(D + F + T) + 1.6(L + H) + 0.5(Lr o S o R)
    3. 1.2D + 1.6(Lr o S o R) + (L o 0.8W)
    4. 1.2D + 1.6W + L + 0.5(Lr o S o R)
    5. (1.2 + 0.2·SDS)D + ρ·QE + L + 0.2S        (§12.4.2.3; en §2.3.2 es 1.2D + 1.0E + L + 0.2S)
    6. 0.9D + 1.6W + 1.6H
    7. (0.9 − 0.2·SDS)D + ρ·QE + 1.6H            (§12.4.2.3; en §2.3.2 es 0.9D + 1.0E + 1.6H)

El programa tiene casos tipo D, L, Lr (viva de techo), W y E; F, T, H, S y R valen cero (en Panamá no
hay nieve, y la lluvia es otro tema del REP), y quedan las 13 de TABLA. W y E van con los dos signos.
En la 3, "(L o 0.8W)" da tres: con L, con +0.8W y con −0.8W.
- L va siempre con su factor completo (1.0 en la 3, la 4 y la 5): NO se usa la opción de 0.5L
  (decisión del usuario: no reducir cargas).
- 1.6W: el viento del REP es de servicio y se multiplica por 1.6 (REP 2021 §8.4, PDF p. 101;
  ACI 318-19 §5.3.5). Es el mismo factor que ya trae ASCE 7-05.
- SDS y ρ son datos del modelo (Modelo.sds y Modelo.rho), por ahora escritos a mano. ρ es 1.0 o 1.3
  (ASCE 7-05 §12.3.4, PDF p. 155). Saldrán de la etapa de sismo.
- Los factores van por TIPO de caso: el de D se aplica a todos los casos tipo D (peso propio, carga
  muerta adicional y las demás muertas). Un tipo sin casos no aporta nada.

SERVICIO (para Ma de las deflexiones, ACI 318-19 §24.2.3.5, y las derivas: sin mayorar). El ACI no
trae combinaciones de servicio; las sugiere ASCE 7-05 en su Apéndice C, que es comentario (no
obligatorio):
    S1. D + L                (CC-1a, §CC.1.1, PDF p. 413): deformaciones de corto plazo
    S2. D + 0.5L             (CC-2, §CC.1.1, PDF p. 413): fluencia lenta y efectos de largo plazo
    S3. D + 0.5L ± 0.7W      (CC-3, §CC.1.2, PDF p. 414): deriva por viento
- CC-1b es D + 0.5S (nieve): no aplica en Panamá.
- 0.7W con el viento del REP, que es de servicio (REP §4.2) como el de ASCE 7-05, para el que se
  armó la CC-3.
- Para la deflexión inmediata por L sola (Tabla 24.2.2: ℓ/360) se restan dos deflexiones, la de D + L
  y la de D, cada una con su Ie: no es una combinación. D sola es "Carga muerta (D)".
- Las fuerzas de servicio salen del mismo análisis que las de resistencia (inercia agrietada,
  0.70Ig y 0.35Ig). Para las deflexiones laterales de servicio, ACI 318-19 §6.6.3.2.2 (PDF p. 80)
  permite 1.4 veces esas inercias: como 1.4 × 0.70 = 0.98 no pasa de Ig, todas suben en la misma
  proporción y las fuerzas no cambian (solo importa la rigidez relativa). Los desplazamientos sí:
  el programa los da con Ig (ver las limitaciones en CLAUDE.md). Ma sale de aquí; Ie se calcula
  aparte (§24.2.3.5).

Además, "Carga muerta (D)" = 1.0·D: no es de la norma; sirve para ver la muerta total (peso propio
más carga muerta adicional).

Lo que todavía NO hace (limitaciones):
- R (lluvia) y S (nieve);
- la opción de 0.5L en la 3, la 4 y la 5 (Lo ≤ 100 psf, salvo garajes y reunión pública): a propósito;
- W y E en X y en Y, y la torsión accidental (etapas 7 y 8): aquí cada tipo va en una sola dirección;
- Ev = 0 cuando SDS ≤ 0.125 (excepción de §12.4.2.2): no se aplica;
- cargas que no actúan (alternancia de la viva). La envolvente de las 13 está en
  modelo/analisis.envolvente, solo para ver resultados.
Por ahora sirven para ver resultados, no para diseñar. Las fórmulas viven aquí, en modelo/, y no
en calculo/ (sagrado): pasarlas allá es una decisión del usuario.

Los puntos Pu–Mu del diagrama de interacción de una columna salen de las 13 (aplicables), aunque falte
alguna carga: la que no está vale cero (decisión del usuario: se grafican todas). Las de servicio no
entran ahí ni en la envolvente: esas son de resistencia.
"""
from modelo.estructura import Combinacion, nombre_combinacion

MUERTA = "D"                     # clave de "Carga muerta (D)"

# (clave, fórmula como en la norma, factores por tipo en función de SDS y ρ). La clave es "C" y el
# número de la combinación en la norma ("C3a", "C3b": los dos signos de W o de E). Lleva la letra para
# que no se confunda con el ID de una combinación propia, que es un entero: en una lista de Qt, el
# texto "1" y el número 1 se consideran iguales.
TABLA = (
    ("C1", "1.4D", lambda sds, rho: {"D": 1.4}),
    ("C2", "1.2D+1.6L+0.5Lr", lambda sds, rho: {"D": 1.2, "L": 1.6, "Lr": 0.5}),
    ("C3", "1.2D+1.6Lr+L", lambda sds, rho: {"D": 1.2, "Lr": 1.6, "L": 1.0}),
    ("C3a", "1.2D+1.6Lr+0.8W", lambda sds, rho: {"D": 1.2, "Lr": 1.6, "W": 0.8}),
    ("C3b", "1.2D+1.6Lr-0.8W", lambda sds, rho: {"D": 1.2, "Lr": 1.6, "W": -0.8}),
    ("C4a", "1.2D+1.6W+L+0.5Lr", lambda sds, rho: {"D": 1.2, "W": 1.6, "L": 1.0, "Lr": 0.5}),
    ("C4b", "1.2D-1.6W+L+0.5Lr", lambda sds, rho: {"D": 1.2, "W": -1.6, "L": 1.0, "Lr": 0.5}),
    ("C5a", "(1.2+0.2SDS)D+ρE+L", lambda sds, rho: {"D": round(1.2 + 0.2 * sds, 4), "E": rho, "L": 1.0}),
    ("C5b", "(1.2+0.2SDS)D-ρE+L", lambda sds, rho: {"D": round(1.2 + 0.2 * sds, 4), "E": -rho, "L": 1.0}),
    ("C6a", "0.9D+1.6W", lambda sds, rho: {"D": 0.9, "W": 1.6}),
    ("C6b", "0.9D-1.6W", lambda sds, rho: {"D": 0.9, "W": -1.6}),
    ("C7a", "(0.9-0.2SDS)D+ρE", lambda sds, rho: {"D": round(0.9 - 0.2 * sds, 4), "E": rho}),
    ("C7b", "(0.9-0.2SDS)D-ρE", lambda sds, rho: {"D": round(0.9 - 0.2 * sds, 4), "E": -rho}),
)
FORMULAS = {clave: formula for clave, formula, _f in TABLA}
CLAUSULA = {"1": "ASCE 7-05 §2.3.2", "2": "ASCE 7-05 §2.3.2", "3": "ASCE 7-05 §2.3.2", "4": "ASCE 7-05 §2.3.2",
            "5": "ASCE 7-05 §12.4.2.3", "6": "ASCE 7-05 §2.3.2", "7": "ASCE 7-05 §12.4.2.3"}

# Las de servicio: (clave, factores, de dónde salen y para qué). Clave "S" y el número; no dependen
# de SDS ni de ρ (el sismo no tiene combinación de servicio: la deriva sísmica sale de E con Cd/Ie).
SERVICIO = (
    ("S1", {"D": 1.0, "L": 1.0},
     "ASCE 7-05 Apéndice C §CC.1.1, ec. CC-1a: D + L. Deformaciones de corto plazo (deflexiones)"),
    ("S2", {"D": 1.0, "L": 0.5},
     "ASCE 7-05 Apéndice C §CC.1.1, ec. CC-2: D + 0.5L. Efectos de largo plazo (fluencia lenta)"),
    ("S3a", {"D": 1.0, "L": 0.5, "W": 0.7},
     "ASCE 7-05 Apéndice C §CC.1.2, ec. CC-3: D + 0.5L + 0.7W. Deriva por viento"),
    ("S3b", {"D": 1.0, "L": 0.5, "W": -0.7},
     "ASCE 7-05 Apéndice C §CC.1.2, ec. CC-3: D + 0.5L - 0.7W. Deriva por viento"),
)
REFERENCIA_SERVICIO = {clave: texto for clave, _f, texto in SERVICIO}


def numero(clave):
    """Número de la combinación en la norma: "C3a" -> "3"."""
    return clave[1:].rstrip("ab")


def aplicables(modelo):
    """{clave: Combinacion}: las combinaciones de la norma que se revisan en el modelo: las 13 de
    resistencia, aunque falte alguna carga (la que no está vale cero; por ejemplo, sin viento
    0.9D + 1.6W y 0.9D − 1.6W dan el mismo punto, y se grafican igual: decisión del usuario). Sin
    "Carga muerta (D)", las de servicio ni las propias. Son las de la envolvente.

    ACI 318-19 §10.4.2.1 (PDF p. 158) pide considerar Pu y Mu simultáneos de cada combinación
    aplicable."""
    return resistencia(modelo.sds, modelo.rho)


def resistencia(sds, rho):
    """{clave: Combinacion}: las 13 de resistencia, con los factores ya calculados para ese SDS y ese
    ρ. El nombre lleva los números: "1.3D + 1.3E + L"."""
    combos = {}
    for clave, _formula, factores in TABLA:
        f = factores(sds, rho)
        combos[clave] = Combinacion(nombre_combinacion(f), f)
    return combos


def servicio():
    """{clave: Combinacion}: las 4 de servicio. El nombre dice que lo son: "D + L (servicio)"."""
    return {clave: Combinacion(f"{nombre_combinacion(f)} (servicio)", dict(f)) for clave, f, _t in SERVICIO}


def predeterminadas(sds, rho):
    """{clave: Combinacion}: "Carga muerta (D)", las 13 de resistencia (con ese SDS y ese ρ) y las 4
    de servicio, en ese orden."""
    return {MUERTA: Combinacion("Carga muerta (D)", {"D": 1.0}), **resistencia(sds, rho), **servicio()}


def es_servicio(clave):
    return clave in REFERENCIA_SERVICIO


def referencia(clave):
    """De dónde sale una predeterminada, para mostrarlo al pasar el mouse."""
    if clave == MUERTA:
        return "Carga muerta total: todos los casos tipo D (peso propio + carga muerta adicional)"
    if es_servicio(clave):
        return f"Servicio (sin mayorar). {REFERENCIA_SERVICIO[clave]}"
    return f"Resistencia. {CLAUSULA[numero(clave)]}, combinación {numero(clave)}: {FORMULAS[clave]}"


def es_predeterminada(clave):
    """Las predeterminadas tienen clave de texto ("D", "C1", "C3a"...); las propias, su ID (un entero)."""
    return isinstance(clave, str)


def todas(modelo):
    """{clave: Combinacion}: las predeterminadas (con el SDS y el ρ del modelo) y luego las propias."""
    return {**predeterminadas(modelo.sds, modelo.rho), **modelo.combinaciones}
