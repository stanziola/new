"""Combinaciones de carga de resistencia que el programa trae cargadas (las predeterminadas).

Son las de ASCE 7-05 §2.3.2 (PDF p. 34), que el REP 2021 §1.4.1 manda usar, con las sísmicas de
§12.4.2.3 (PDF p. 156):

    1. 1.4(D + F)
    2. 1.2(D + F + T) + 1.6(L + H) + 0.5(Lr o S o R)
    3. 1.2D + 1.6(Lr o S o R) + (L o 0.8W)
    4. 1.2D + 1.6W + L + 0.5(Lr o S o R)
    5. (1.2 + 0.2·SDS)D + ρ·QE + L + 0.2S        (§12.4.2.3; en §2.3.2 es 1.2D + 1.0E + L + 0.2S)
    6. 0.9D + 1.6W + 1.6H
    7. (0.9 − 0.2·SDS)D + ρ·QE + 1.6H            (§12.4.2.3; en §2.3.2 es 0.9D + 1.0E + 1.6H)

El programa solo tiene casos tipo D, L, W y E, así que F, T, H, Lr, S y R valen cero y quedan las
12 de TABLA (las que estaban en scripts/combinaciones_asce7.py). W y E van con los dos signos.
- 1.6W: el viento del REP es de servicio y se multiplica por 1.6 (REP 2021 §8.4, PDF p. 101;
  ACI 318-19 §5.3.5). Es el mismo factor que ya trae ASCE 7-05.
- SDS y ρ son datos del modelo (Modelo.sds y Modelo.rho), por ahora escritos a mano. ρ es 1.0 o 1.3
  (ASCE 7-05 §12.3.4, PDF p. 155). Saldrán de la etapa de sismo.
- Los factores van por TIPO de caso: el de D se aplica a todos los casos tipo D (peso propio, carga
  muerta adicional y las demás muertas). Un tipo sin casos no aporta nada.

Además, "Carga muerta (D)" = 1.0·D: no es de la norma; sirve para ver la muerta total (peso propio
más carga muerta adicional).

Lo que todavía NO hace (limitaciones):
- Lr (viva de techo) y R (lluvia): faltan el 0.5Lr de la 2 y la 4 y el 1.6Lr de la 3;
- "1.2D + L" de la 3 (la otra opción de "L o 0.8W");
- la opción de 0.5L en la 3, la 4 y la 5 (Lo ≤ 100 psf, salvo garajes y reunión pública);
- W y E en X y en Y, y la torsión accidental (etapas 7 y 8): aquí cada tipo va en una sola dirección;
- Ev = 0 cuando SDS ≤ 0.125 (excepción de §12.4.2.2): no se aplica;
- envolventes y cargas que no actúan (alternancia).
Por ahora sirven para ver resultados, no para diseñar. Las fórmulas viven aquí, en modelo/, y no
en calculo/ (sagrado): pasarlas allá es una decisión del usuario.
"""
from modelo.estructura import Combinacion, nombre_combinacion

MUERTA = "D"                     # clave de "Carga muerta (D)"

# (clave, fórmula como en la norma, factores por tipo en función de SDS y ρ). La clave es "C" y el
# número de la combinación en la norma ("C3a", "C3b": los dos signos de W o de E). Lleva la letra para
# que no se confunda con el ID de una combinación propia, que es un entero: en una lista de Qt, el
# texto "1" y el número 1 se consideran iguales.
TABLA = (
    ("C1", "1.4D", lambda sds, rho: {"D": 1.4}),
    ("C2", "1.2D+1.6L", lambda sds, rho: {"D": 1.2, "L": 1.6}),
    ("C3a", "1.2D+0.8W", lambda sds, rho: {"D": 1.2, "W": 0.8}),
    ("C3b", "1.2D-0.8W", lambda sds, rho: {"D": 1.2, "W": -0.8}),
    ("C4a", "1.2D+1.6W+L", lambda sds, rho: {"D": 1.2, "W": 1.6, "L": 1.0}),
    ("C4b", "1.2D-1.6W+L", lambda sds, rho: {"D": 1.2, "W": -1.6, "L": 1.0}),
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


def numero(clave):
    """Número de la combinación en la norma: "C3a" -> "3"."""
    return clave[1:].rstrip("ab")


def predeterminadas(sds, rho):
    """{clave: Combinacion}: "Carga muerta (D)" y las 12 de la norma, con los factores ya calculados
    para ese SDS y ese ρ. El nombre lleva los números: "1.3D + 1.3E + L"."""
    combos = {MUERTA: Combinacion("Carga muerta (D)", {"D": 1.0})}
    for clave, _formula, factores in TABLA:
        f = factores(sds, rho)
        combos[clave] = Combinacion(nombre_combinacion(f), f)
    return combos


def referencia(clave):
    """De dónde sale una predeterminada, para mostrarlo al pasar el mouse."""
    if clave == MUERTA:
        return "Carga muerta total: todos los casos tipo D (peso propio + carga muerta adicional)"
    return f"{CLAUSULA[numero(clave)]}, combinación {numero(clave)}: {FORMULAS[clave]}"


def es_predeterminada(clave):
    """Las predeterminadas tienen clave de texto ("D", "C1", "C3a"...); las propias, su ID (un entero)."""
    return isinstance(clave, str)


def todas(modelo):
    """{clave: Combinacion}: las predeterminadas (con el SDS y el ρ del modelo) y luego las propias."""
    return {**predeterminadas(modelo.sds, modelo.rho), **modelo.combinaciones}
