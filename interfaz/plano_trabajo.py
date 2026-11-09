"""Plano de trabajo: la rejilla, dónde cae el puntero, el snap y las coordenadas escritas.

El plano de trabajo es donde se dibuja la rejilla y donde "cae" el puntero del mouse:
- "XY": horizontal, a una altura Z (plantas);
- "XZ": vertical, en una coordenada Y (elevaciones a lo largo de X);
- "YZ": vertical, en una coordenada X (elevaciones a lo largo de Y).
La rejilla empieza en el origen: en cada eje hay N líneas separadas una distancia d, de 0 a (N - 1)·d.
Todo en unidades internas (m). No usa Qt: se puede probar sin abrir ventanas.
"""
import re
from dataclasses import dataclass

import numpy as np

from configuracion import formato, unidades
from configuracion import interfaz as ui
from interfaz.seleccion import nodo_cercano

PLANOS = {"XY": 2, "XZ": 1, "YZ": 0}          # plano -> eje perpendicular (0 = x, 1 = y, 2 = z)
NOMBRE_EJE = "XYZ"


@dataclass
class Rejilla:
    plano: str               # "XY", "XZ" o "YZ"
    posicion: float          # coordenada del plano en su eje perpendicular (m)
    minimo: np.ndarray       # límites en los dos ejes del plano (m)
    maximo: np.ndarray
    paso: float              # distancia entre líneas (m)
    escala: float            # tamaño de referencia (m), para el pequeño corrimiento al dibujarla

    @property
    def normal(self):
        return PLANOS[self.plano]

    @property
    def ejes(self):
        """Los dos ejes que forman el plano, por ejemplo (0, 1) para XY."""
        return tuple(i for i in range(3) if i != self.normal)


def geometria_rejilla(modelo, plano="XY", posicion=0.0):
    """Rejilla del plano: desde el origen, con REJILLA_LINEAS_X/Y/Z líneas separadas REJILLA_DISTANCIA."""
    lineas = (ui.REJILLA_LINEAS_X, ui.REJILLA_LINEAS_Y, ui.REJILLA_LINEAS_Z)
    ejes = [i for i in range(3) if i != PLANOS[plano]]
    paso = float(ui.REJILLA_DISTANCIA)
    maximo = np.array([(lineas[e] - 1) * paso for e in ejes], dtype=float)
    if modelo.nodos:
        puntos = np.array([n.coords for n in modelo.nodos.values()], dtype=float)
        escala = float(np.ptp(puntos, axis=0).max()) or float(maximo.max())
    else:
        escala = float(maximo.max())
    return Rejilla(plano, float(posicion), np.zeros(2), maximo, paso, escala)


def plano_por_defecto(modelo):
    """Plano XY en la base del modelo (z mínimo), o en z = 0 si está vacío."""
    z = min((n.z for n in modelo.nodos.values()), default=0.0)
    return "XY", float(z)


def _a_mundo(renderer, x, y, profundidad):
    renderer.SetDisplayPoint(x, y, profundidad)
    renderer.DisplayToWorld()
    w = np.array(renderer.GetWorldPoint(), dtype=float)
    return w[:3] / w[3]


def punto_en_plano(renderer, x, y, rejilla):
    """Punto donde el rayo del mouse corta el plano de trabajo, o None.

    El rayo va del plano cercano (profundidad 0) al lejano (1) de la cámara. Da None si el rayo es
    casi paralelo al plano (por ejemplo, el plano XY visto de frente) o si el corte queda detrás
    de la cámara.
    """
    cerca, lejos = _a_mundo(renderer, x, y, 0.0), _a_mundo(renderer, x, y, 1.0)
    d = lejos - cerca
    k = rejilla.normal
    if abs(d[k]) < 1e-9 * np.linalg.norm(d):
        return None
    t = (rejilla.posicion - cerca[k]) / d[k]
    if t < 0:
        return None
    p = cerca + t * d
    p[k] = rejilla.posicion
    return p


@dataclass
class Candidato:
    """Dónde quedaría un punto si se hace clic ahora."""
    punto: np.ndarray = None   # en m; None si el puntero no cae en el plano
    tipo: str = "fuera"        # "nodo", "rejilla", "libre" o "fuera"
    nid: int = None            # si tipo es "nodo"


def candidato(renderer, x, y, modelo, rejilla, snap):
    """Punto bajo el puntero.

    Con snap: primero un nodo cercano en pantalla; si no, la intersección más cercana de la
    rejilla, solo si cae dentro de ella. Sin snap (o fuera de la rejilla): el punto libre.
    """
    if snap:
        nid = nodo_cercano(renderer, modelo, x, y, ui.TOL_SNAP_PX)
        if nid is not None:
            return Candidato(np.array(modelo.nodos[nid].coords, dtype=float), "nodo", nid)
    p = punto_en_plano(renderer, x, y, rejilla)
    if p is None:
        return Candidato()
    if not snap:
        return Candidato(p, "libre")
    q = p.copy()
    for k, e in enumerate(rejilla.ejes):
        q[e] = round(round(p[e] / rejilla.paso) * rejilla.paso, 10)
        if not (rejilla.minimo[k] - 1e-9 <= q[e] <= rejilla.maximo[k] + 1e-9):
            return Candidato(p, "libre")        # fuera de la rejilla: no se pega a nada
    return Candidato(q, "rejilla")


def interpretar(texto, rejilla, ultimo=None):
    """Punto escrito en la barra de comandos, en unidades de pantalla -> punto en m.

    - "x, y, z": absoluto;
    - "u, v": sobre el plano de la rejilla (el tercero es la posición del plano);
    - "@dx, dy, dz": relativo al último punto.
    Separadores: comas, punto y coma o espacios. El decimal es el punto.
    """
    t = texto.strip()
    relativo = t.startswith("@")
    partes = [p for p in re.split(r"[,;\s]+", t.lstrip("@")) if p]
    try:
        valores = [unidades.a_interna(float(p), "longitud") for p in partes]
    except ValueError:
        raise ValueError("Escribe números separados por comas, por ejemplo 2.5, 4, 3") from None
    if relativo:
        if len(valores) != 3:
            raise ValueError("Después de @ van tres números: @dx, dy, dz")
        if ultimo is None:
            raise ValueError("No hay un punto anterior para usar @")
        return np.asarray(ultimo, dtype=float) + valores
    if len(valores) == 3:
        return np.array(valores)
    if len(valores) == 2:
        p = np.zeros(3)
        p[list(rejilla.ejes)] = valores
        p[rejilla.normal] = rejilla.posicion
        return p
    raise ValueError("Escribe 3 números (x, y, z) o 2 (sobre el plano de la rejilla)")


def texto_coordenadas(cand, inicio=None):
    """Texto de la barra de estado: coordenadas del candidato, si se pegó a un nodo y el largo."""
    u = unidades.simbolo("longitud")
    if cand.punto is None:
        return f"X —   Y —   Z —   {u}"
    x, y, z = (formato.cantidad(c, "longitud", con_unidad=False) for c in cand.punto)
    texto = f"X {x}   Y {y}   Z {z}   {u}"
    if cand.tipo == "nodo":
        texto += f"   ·  nodo {cand.nid}"
    if inicio is not None:
        texto += f"   ·  L = {formato.cantidad(float(np.linalg.norm(cand.punto - inicio)), 'longitud')}"
    return texto
