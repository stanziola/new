"""Guardar y abrir modelos en archivos .json (texto que se puede leer en cualquier editor).

- Los números están en unidades internas (kN y m), sin importar las unidades de pantalla.
- Se guardan los contadores de IDs ("siguiente_id"): así, al reabrir, un nodo nuevo nunca recibe
  el ID de uno que se borró antes (los IDs no se reutilizan).
- "vista" guarda datos de la interfaz que conviene recordar con el modelo, como el plano de la
  rejilla. Este módulo no los interpreta: solo los guarda y los devuelve.
"""
import json
from dataclasses import asdict
from pathlib import Path

from calculo.modelo import Elemento, Material, Modelo, Nodo, Seccion

VERSION_FORMATO = 1
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


def desde_diccionario(datos):
    """Arma el modelo desde el diccionario leído. Devuelve (modelo, vista)."""
    if not isinstance(datos, dict):
        raise ValueError("El archivo no contiene un modelo")
    if datos.get("version_formato") != VERSION_FORMATO:
        raise ValueError(f"Versión de formato {datos.get('version_formato')!r} no reconocida "
                         f"(se esperaba {VERSION_FORMATO})")
    if datos.get("unidades") != UNIDADES_INTERNAS:
        raise ValueError(f"Las unidades del archivo {datos.get('unidades')!r} no son las internas "
                         f"{UNIDADES_INTERNAS}")
    m = Modelo()
    try:
        m.nodos = {int(i): Nodo(**d) for i, d in datos["nodos"].items()}
        m.materiales = {int(i): Material(**d) for i, d in datos["materiales"].items()}
        m.secciones = {int(i): Seccion(**d) for i, d in datos["secciones"].items()}
        m.elementos = {int(i): Elemento(**d) for i, d in datos["elementos"].items()}
        m._sig_id = {tipo: int(v) for tipo, v in datos["siguiente_id"].items()}
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
    if set(m._sig_id) != {"nodo", "elem", "mat", "sec"}:
        problemas.append(f"faltan contadores de IDs: {sorted(m._sig_id)}")
    else:
        for tipo, ids in (("nodo", m.nodos), ("elem", m.elementos),
                          ("mat", m.materiales), ("sec", m.secciones)):
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
