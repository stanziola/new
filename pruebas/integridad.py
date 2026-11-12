"""Integridad del cálculo sagrado (carpeta calculo/). Ejecutar desde la raíz:

    python -m pruebas.integridad             revisa
    python -m pruebas.integridad --aprobar   aprueba el estado actual (después de revisar un cambio)

Dos comprobaciones:
1. Huellas: el SHA-256 de cada archivo .py de calculo/ debe coincidir con el aprobado
   (pruebas/referencias/huellas_calculo.json). Dice qué archivo cambió, cuál es nuevo y cuál se
   borró. Los saltos de línea se normalizan, para que Windows y git no den falsas alarmas.
2. Resultados de referencia: recalcula un pórtico y puntos de los diagramas de interacción y los
   compara con pruebas/referencias/resultados.json. Así, un cambio en los números no pasa
   inadvertido aunque alguien apruebe las huellas.

El pórtico de referencia está definido aquí mismo (no en ejemplos/), para que cambiar el ejemplo
no dé una falsa alarma sobre el cálculo.
"""
import argparse
import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
CALCULO = RAIZ / "calculo"
REFERENCIAS = RAIZ / "pruebas" / "referencias"
ARCHIVO_HUELLAS = REFERENCIAS / "huellas_calculo.json"
ARCHIVO_RESULTADOS = REFERENCIAS / "resultados.json"
RTOL, ATOL = 1e-10, 1e-12

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


# ---------- 1. Huellas ----------
def huella(ruta):
    """SHA-256 del archivo, con los saltos de línea normalizados (\\r\\n -> \\n)."""
    return hashlib.sha256(Path(ruta).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def huellas_actuales(carpeta=CALCULO):
    carpeta = Path(carpeta)
    return {r.relative_to(carpeta.parent).as_posix(): huella(r)
            for r in sorted(carpeta.rglob("*.py")) if "__pycache__" not in r.parts}


def revisar_huellas(carpeta=CALCULO, archivo=ARCHIVO_HUELLAS):
    """Diferencias entre las huellas actuales y las aprobadas (lista de textos; vacía = igual)."""
    if not Path(archivo).exists():
        return ["no hay huellas aprobadas: corre  python -m pruebas.integridad --aprobar"]
    aprobadas = json.loads(Path(archivo).read_text(encoding="utf-8"))["archivos"]
    actuales = huellas_actuales(carpeta)
    diferencias = []
    for ruta in sorted(set(aprobadas) | set(actuales)):
        if ruta not in actuales:
            diferencias.append(f"se borró {ruta}")
        elif ruta not in aprobadas:
            diferencias.append(f"archivo nuevo: {ruta}")
        elif aprobadas[ruta] != actuales[ruta]:
            diferencias.append(f"cambió {ruta}")
    return diferencias


# ---------- 2. Resultados de referencia ----------
KSI = 6894.757293168361      # kN/m² por ksi


def portico_referencia():
    """El pórtico 3D de 5 nodos y 4 barras (los mismos datos del ejemplo, fijos aquí)."""
    from modelo import Modelo
    m = Modelo()
    m.agregar_material("Acero", e=200e6, g=77e6)
    m.agregar_material("Concreto", e=25e6, g=10e6)
    m.agregar_seccion("Viga 30x50", a=0.15, iy=3.125e-3, iz=1.125e-3, j=2.8e-3)
    m.agregar_seccion("Col 40x40", a=0.16, iy=2.133e-3, iz=2.133e-3, j=3.6e-3)
    for p in ((0, 0, 0), (0, 0, 3), (5, 0, 3), (5, 0, 0), (5, 4, 3)):
        m.agregar_nodo(*p)
    m.agregar_elemento(2, 1, 2, 2)
    m.agregar_elemento(3, 2, 2, 1)
    m.agregar_elemento(4, 3, 2, 2, alfa=90)
    m.agregar_elemento(5, 3, 1, 1)
    m.restringir(1)
    m.restringir(4, phix=False, phiy=False, phiz=False)
    m.cargar(3, fx=10, fz=-20)
    return m


def vigas_referencia():
    """Vigas con cargas en la barra (uniforme, puntual y momento, en ejes locales y globales).

    Una viga de 6 m en X con los dos extremos empotrados y otra simplemente apoyada, más una
    columna inclinada con carga global. Cubren las FEF y los diagramas a lo largo de la barra."""
    from modelo import Modelo
    casos = {}
    for nombre, apoyo_j in (("biempotrada", (True,) * 6), ("simple", (True, True, True, True, False, False))):
        m = Modelo()
        m.agregar_material("C", e=25e6, g=10e6)
        m.agregar_seccion("S", a=0.15, iy=3.125e-3, iz=1.125e-3, j=2.8e-3)
        m.agregar_nodo(0, 0, 0)
        m.agregar_nodo(6, 0, 0)
        m.agregar_elemento(1, 2, 1, 1)
        m.restringir(1, *((True, True, True, True, False, False) if nombre == "simple" else (True,) * 6))
        m.restringir(2, *apoyo_j)
        m.agregar_carga_barra(1, "uniforme", -10, "Z")
        m.agregar_carga_barra(1, "puntual", 15, "y", a=2.0)
        m.agregar_carga_barra(1, "momento", 8, "z", a=4.5)
        m.agregar_carga_barra(1, "puntual", -12, "x", a=1.5)
        casos[nombre] = m
    m = Modelo()
    m.agregar_material("C", e=25e6, g=10e6)
    m.agregar_seccion("S", a=0.16, iy=2.133e-3, iz=2.133e-3, j=3.6e-3)
    m.agregar_nodo(0, 0, 0)
    m.agregar_nodo(2, 1, 3)
    m.agregar_elemento(1, 2, 1, 1, alfa=25)
    m.restringir(1)
    m.agregar_carga_barra(1, "uniforme", -4, "Z")
    m.agregar_carga_barra(1, "momento", 3, "X", a=1.0)
    m.cargar(2, fx=5)
    casos["inclinada"] = m
    return casos


def calcular_resultados():
    """Resultados de referencia calculados con el cálculo actual."""
    from calculo.interaccion import biaxial, circular, rectangular
    from calculo.interaccion.comun import propiedades_seccion, ureg
    from modelo.analisis import analizar_caso, fuerzas_en

    res = analizar_caso(portico_referencia(), 1).res
    resultados = {"portico": {"K": res.K.tolist(), "U": res.U.tolist(), "R": res.R.tolist(),
                              "fuerzas": {str(k): v.tolist() for k, v in res.fuerzas.items()}}}

    vigas = {}
    for nombre, m in vigas_referencia().items():
        rc = analizar_caso(m, 1)
        d = fuerzas_en(m, rc, 1)
        vigas[nombre] = {"U": rc.res.U.tolist(), "R": rc.res.R.tolist(), "fuerzas": rc.res.fuerzas[1].tolist(),
                         "diagramas": {k: np.asarray(d[k]).tolist() for k in ("x", "N", "Vy", "Vz", "T", "My", "Mz")}}
    resultados["vigas"] = vigas

    rect = []
    for b, h, d, nx, ny, fc, nob in ((0.65, 0.65, 0.075, 5, 5, 4, 8), (0.40, 0.60, 0.06, 3, 4, 6.5, 9)):
        sec = propiedades_seccion(b * ureg.m, h * ureg.m, d * ureg.m, nx, ny, fc * ureg.ksi, nob)
        for c in np.geomspace(0.01 * h, 2 * h, 10):
            phi, pn, mn, ppn, pmn = rectangular.phipnmn(c * ureg.m, sec)
            rect.append([phi, pn.magnitude, mn.magnitude, ppn.magnitude, pmn.magnitude])
    resultados["rectangular"] = rect

    sec = circular.propiedades_circular(0.7335 * ureg.m, 0.075 * ureg.m, 16, 4 * ureg.ksi, 8)
    D = sec["D"].to("inch").magnitude
    resultados["circular"] = [list(circular.phipnmn_circ(c, sec)) for c in np.geomspace(0.01 * D, 2 * D, 10)]

    # Con f'c y fy en kN/m² (como los manda la interfaz) y fy distinto de 60 ksi: que las unidades
    # en que llegan los datos no cambien el resultado
    kn_m2 = ureg.kilonewton / ureg.meter ** 2
    sec = propiedades_seccion(0.40 * ureg.m, 0.60 * ureg.m, 0.06 * ureg.m, 3, 4, 5 * KSI * kn_m2, 8, 75 * KSI * kn_m2)
    unidades = []
    for c in np.geomspace(0.006, 1.2, 8):
        phi, pn, mn, ppn, pmn = rectangular.phipnmn(c * ureg.m, sec)
        unidades.append([phi, pn.magnitude, mn.magnitude, ppn.magnitude, pmn.magnitude])
    resultados["rectangular_kn_m2"] = unidades

    sec = propiedades_seccion(0.40 * ureg.m, 0.60 * ureg.m, 0.06 * ureg.m, 3, 4, 5 * ureg.ksi, 8)
    bi = []
    for deg in (0, 30, 90, 225):
        th = math.radians(deg)
        for c in (2.0, 6.0, 12.0, 20.0, 35.0, 60.0):
            bi.append([float(x) for x in biaxial.phipnmn_biaxial(c, th, sec)])
    resultados["biaxial"] = bi
    # El corte de la superficie en la dirección del momento (la misma sección, tres direcciones)
    resultados["biaxial_direccion"] = [[float(x) for x in lista] for deg in (20, 45, 70)
                                       for lista in biaxial.curva_direccion(sec, math.radians(deg), 12)]
    return resultados


def _aplanar(x):
    if isinstance(x, dict):
        return [v for k in sorted(x) for v in _aplanar(x[k])]
    if isinstance(x, (list, tuple)):
        return [v for e in x for v in _aplanar(e)]
    return [float(x)]


def revisar_resultados(archivo=ARCHIVO_RESULTADOS):
    """Diferencias entre los resultados actuales y los de referencia (lista de textos)."""
    if not Path(archivo).exists():
        return ["no hay resultados de referencia: corre  python -m pruebas.integridad --aprobar"]
    referencia = json.loads(Path(archivo).read_text(encoding="utf-8"))
    actual = calcular_resultados()
    diferencias = []
    for parte in sorted(set(referencia) | set(actual)):
        a, r = np.array(_aplanar(actual.get(parte, []))), np.array(_aplanar(referencia.get(parte, [])))
        if a.shape != r.shape:
            diferencias.append(f"{parte}: cambió la cantidad de valores ({r.size} -> {a.size})")
        elif not np.allclose(a, r, rtol=RTOL, atol=ATOL):
            peor = np.max(np.abs(a - r) / np.maximum(np.abs(r), ATOL))
            diferencias.append(f"{parte}: los resultados cambiaron (diferencia relativa máx {peor:.2e})")
    return diferencias


# ---------- Revisar y aprobar ----------
def revisar(imprimir=print):
    """Corre las dos comprobaciones. Devuelve True si todo está igual a lo aprobado."""
    ok = True
    for titulo, diferencias in (("huellas de calculo/", revisar_huellas()),
                                ("resultados de referencia", revisar_resultados())):
        if diferencias:
            ok = False
            for d in diferencias:
                imprimir(f"  ✗ {titulo}: {d}")
        else:
            imprimir(f"  ✓ {titulo}: iguales a lo aprobado")
    if not ok:
        imprimir("    Si el cambio fue revisado y aprobado:  python -m pruebas.integridad --aprobar")
    return ok


def aprobar(imprimir=print):
    """Guarda las huellas y los resultados actuales como los aprobados."""
    REFERENCIAS.mkdir(parents=True, exist_ok=True)
    for d in revisar_resultados():
        imprimir(f"  ! {d}")
    ARCHIVO_HUELLAS.write_text(json.dumps({"aprobado": date.today().isoformat(),
                                           "archivos": huellas_actuales()}, indent=2), encoding="utf-8")
    ARCHIVO_RESULTADOS.write_text(json.dumps(calcular_resultados()), encoding="utf-8")
    imprimir(f"  ✓ aprobado el estado actual de calculo/ ({len(huellas_actuales())} archivos)")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Integridad del cálculo sagrado (calculo/)")
    parser.add_argument("--aprobar", action="store_true",
                        help="aprobar el estado actual, después de revisar el cambio")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n===== INTEGRIDAD DEL CÁLCULO (calculo/) =====")
    if args.aprobar:
        aprobar()
        return 0
    return 0 if revisar() else 1


if __name__ == "__main__":
    sys.exit(main())
