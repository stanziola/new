"""Guardar y abrir modelos en archivos .json (texto que se puede leer en cualquier editor).

- Los números están en unidades internas (kN y m), sin importar las unidades de pantalla.
- Se guardan los contadores de IDs ("siguiente_id"): así, al reabrir, un nodo nuevo nunca recibe
  el ID de uno que se borró antes (los IDs no se reutilizan).
- "vista" guarda datos de la interfaz que conviene recordar con el modelo. Este módulo no los
  interpreta: solo los guarda y los devuelve.
- Versión 2: guarda también los casos de carga y las cargas. Los archivos de la versión 1 se abren
  igual: la "carga" de cada nodo pasa a una carga nodal del caso Muerta, y los materiales de
  concreto reciben el peso unitario del concreto reforzado (para el peso propio).
- Versión 3: guarda también las combinaciones ({ID: {"nombre", "factores": {ID de caso: factor}}}).
  Los archivos de las versiones 1 y 2 se abren sin combinaciones.
"""
import json
from dataclasses import asdict
from pathlib import Path

from calculo.concreto import GAMMA_CONCRETO
from modelo.estructura import (CargaBarra, CargaNodal, Caso, Combinacion, Concreto, Elemento, Material, Modelo,
                               Nodo, Seccion)

VERSION_FORMATO = 3
VERSIONES_LEIDAS = (1, 2, 3)
CONTADORES = {"nodo", "elem", "mat", "sec", "caso", "carga", "combo"}
UNIDADES_INTERNAS = {"fuerza": "kN", "longitud": "m"}


def a_diccionario(modelo, vista=None):
    """El modelo como diccionario listo para JSON (las claves de los IDs pasan a texto)."""
    return {
        "programa": "Análisis estructural 3D",
        "version_formato": VERSION_FORMATO,
        "unidades": dict(UNIDADES_INTERNAS),
        "nodos": {str(i): asdict(n) for i, n in modelo.nodos.items()},
        "materiales": {str(i): asdict(m) for i, m in modelo.materiales.items()},
        "secciones": {str(i): asdict(s) for i, s in modelo.secciones.items()},
        "elementos": {str(i): asdict(e) for i, e in modelo.elementos.items()},
        "casos": {str(i): asdict(c) for i, c in modelo.casos.items()},
        "cargas": {str(i): {"clase": "nodal" if isinstance(c, CargaNodal) else "barra", **asdict(c)}
                   for i, c in modelo.cargas.items()},
        "combinaciones": {str(i): {"nombre": co.nombre, "factores": {str(c): f for c, f in co.factores.items()}}
                          for i, co in modelo.combinaciones.items()},
        "siguiente_id": dict(modelo._sig_id),
        "vista": dict(vista or {}),
    }


def guardar(modelo, ruta, vista=None):
    """Escribe el modelo en ruta. Primero en un archivo temporal: si algo falla a mitad de camino,
    el archivo anterior queda intacto."""
    ruta = Path(ruta)
    texto = json.dumps(a_diccionario(modelo, vista), indent=2, ensure_ascii=False)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(texto, encoding="utf-8")
    temporal.replace(ruta)


def _seccion(d):
    """Seccion desde su diccionario. "concreto" y "material" pueden faltar (archivos anteriores)."""
    d = dict(d)
    concreto = d.pop("concreto", None)
    return Seccion(**d, concreto=Concreto(**concreto) if concreto else None)


def _material(d):
    """Material desde su diccionario. Los de concreto viejos (sin "gamma") reciben el del concreto."""
    d = dict(d)
    if "gamma" not in d:
        d["gamma"] = GAMMA_CONCRETO if d.get("fc") is not None else 0.0
    return Material(**d)


def _carga(d):
    d = dict(d)
    clase = d.pop("clase")
    return CargaNodal(**d) if clase == "nodal" else CargaBarra(**d)


def desde_diccionario(datos):
    """Arma el modelo desde el diccionario leído. Devuelve (modelo, vista)."""
    if not isinstance(datos, dict):
        raise ValueError("El archivo no contiene un modelo")
    version = datos.get("version_formato")
    if version not in VERSIONES_LEIDAS:
        raise ValueError(f"Versión de formato {version!r} no reconocida "
                         f"(se esperaba una de {VERSIONES_LEIDAS})")
    if datos.get("unidades") != UNIDADES_INTERNAS:
        raise ValueError(f"Las unidades del archivo {datos.get('unidades')!r} no son las internas "
                         f"{UNIDADES_INTERNAS}")
    m = Modelo()
    try:
        cargas_viejas = {}                     # versión 1: la carga estaba dentro de cada nodo
        m.nodos = {}
        for i, d in datos["nodos"].items():
            d = dict(d)
            carga = d.pop("carga", None)
            if carga and any(carga):
                cargas_viejas[int(i)] = [float(c) for c in carga]
            m.nodos[int(i)] = Nodo(**d)
        m.materiales = {int(i): _material(d) for i, d in datos["materiales"].items()}
        m.secciones = {int(i): _seccion(d) for i, d in datos["secciones"].items()}
        m.elementos = {int(i): Elemento(**d) for i, d in datos["elementos"].items()}
        m._sig_id = {tipo: int(v) for tipo, v in datos["siguiente_id"].items()}
        if version >= 2:
            m.casos = {int(i): Caso(**d) for i, d in datos["casos"].items()}
            m.cargas = {int(i): _carga(d) for i, d in datos["cargas"].items()}
        else:
            m._sig_id.setdefault("caso", max(m.casos) + 1)
            m._sig_id.setdefault("carga", 1)
            for nid, fuerzas in cargas_viejas.items():
                m.agregar_carga_nodal(nid, fuerzas)
        if version >= 3:
            m.combinaciones = {int(i): Combinacion(d["nombre"], {int(c): float(f) for c, f in d["factores"].items()})
                               for i, d in datos["combinaciones"].items()}
        else:
            m._sig_id.setdefault("combo", 1)
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        raise ValueError(f"El archivo no tiene el formato esperado: {e!r}") from e
    _revisar(m)
    return m, datos.get("vista") or {}


def _revisar(m):
    """Que cada barra apunte a cosas que existen y que los contadores no repitan IDs."""
    problemas = []
    for eid, el in m.elementos.items():
        for nid in (el.ni, el.nj):
            if nid not in m.nodos:
                problemas.append(f"la barra {eid} usa el nodo {nid}, que no existe")
        if el.material is not None and el.material not in m.materiales:
            problemas.append(f"la barra {eid} usa el material {el.material}, que no existe")
        if el.seccion is not None and el.seccion not in m.secciones:
            problemas.append(f"la barra {eid} usa la sección {el.seccion}, que no existe")
    for sid, sec in m.secciones.items():
        if sec.material is not None and sec.material not in m.materiales:
            problemas.append(f"la sección {sid} usa el material {sec.material}, que no existe")
    if not m.casos:
        problemas.append("no hay casos de carga")
    for cid, c in m.cargas.items():
        if c.caso not in m.casos:
            problemas.append(f"la carga {cid} es del caso {c.caso}, que no existe")
        if isinstance(c, CargaNodal) and c.nodo not in m.nodos:
            problemas.append(f"la carga {cid} está en el nodo {c.nodo}, que no existe")
        if isinstance(c, CargaBarra) and c.barra not in m.elementos:
            problemas.append(f"la carga {cid} está en la barra {c.barra}, que no existe")
    for coid, co in m.combinaciones.items():
        for caso in co.factores:
            if caso not in m.casos:
                problemas.append(f"la combinación {coid} usa el caso {caso}, que no existe")
    if set(m._sig_id) != CONTADORES:
        problemas.append(f"faltan contadores de IDs: {sorted(m._sig_id)}")
    else:
        for tipo, ids in (("nodo", m.nodos), ("elem", m.elementos), ("mat", m.materiales),
                          ("sec", m.secciones), ("caso", m.casos), ("carga", m.cargas),
                          ("combo", m.combinaciones)):
            if ids and m._sig_id[tipo] <= max(ids):
                problemas.append(f"el contador de '{tipo}' ({m._sig_id[tipo]}) no es mayor que "
                                 f"el ID {max(ids)}: se repetirían IDs")
    if problemas:
        raise ValueError("El archivo tiene datos inconsistentes:\n- " + "\n- ".join(problemas))


def abrir(ruta):
    """Lee un modelo de ruta. Devuelve (modelo, vista). Si el archivo no sirve, ValueError."""
    ruta = Path(ruta)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{ruta.name} no es un JSON válido: {e}") from e
    return desde_diccionario(datos)
