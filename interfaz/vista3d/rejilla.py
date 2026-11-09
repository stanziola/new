"""Rejilla 3D, dónde cae el puntero, el snap y las coordenadas escritas.

La rejilla es 3D, como la de ETABS: en cada nivel Z se repite la planta, con líneas paralelas a X
y a Y. Empieza en el origen: en cada eje hay N líneas separadas su distancia (X, Y y Z por
separado), de 0 a (N - 1)·d.

Dónde cae el puntero (candidato), en este orden:
1. con snap, el nodo más cercano en pantalla;
2. con snap, el cruce de la rejilla más cercano en pantalla, en cualquier nivel (si dos quedan igual
   de cerca, gana el más cercano a la cámara);
3. si no, el punto libre sobre el plano horizontal de la base (z del nodo más bajo, o 0).
Todo en unidades internas (m). No usa Qt: se puede probar sin abrir ventanas.
"""
import re
from dataclasses import dataclass

import numpy as np

from configuracion import formato, unidades
from configuracion import interfaz as ui
from interfaz.vista3d.seleccion import nodo_cercano, proyectar

NOMBRE_EJE = "XYZ"


@dataclass
class Rejilla:
    xs: np.ndarray           # posiciones de las líneas en X (m)
    ys: np.ndarray
    zs: np.ndarray           # niveles
    base: float              # z del plano horizontal donde caen los puntos libres (m)
    escala: float            # tamaño de referencia (m), para el pequeño corrimiento al dibujarla

    def puntos(self):
        """Todos los cruces de la rejilla, (nx·ny·nz) × 3."""
        x, y, z = np.meshgrid(self.xs, self.ys, self.zs, indexing="ij")
        return np.column_stack([x.ravel(), y.ravel(), z.ravel()])


def _lineas(n, distancia):
    return np.arange(int(n), dtype=float) * float(distancia)


def geometria_rejilla(modelo):
    """Rejilla 3D desde el origen, con REJILLA_LINEAS_X/Y/Z líneas separadas REJILLA_DISTANCIA_X/Y/Z."""
    xs = _lineas(ui.REJILLA_LINEAS_X, ui.REJILLA_DISTANCIA_X)
    ys = _lineas(ui.REJILLA_LINEAS_Y, ui.REJILLA_DISTANCIA_Y)
    zs = _lineas(ui.REJILLA_LINEAS_Z, ui.REJILLA_DISTANCIA_Z)
    tamano = max(xs[-1], ys[-1], zs[-1], 1.0)
    if modelo.nodos:
        puntos = np.array([n.coords for n in modelo.nodos.values()], dtype=float)
        escala = float(np.ptp(puntos, axis=0).max()) or tamano
    else:
        escala = tamano
    return Rejilla(xs, ys, zs, base_del_modelo(modelo), escala)


def base_del_modelo(modelo):
    """z del nodo más bajo, o 0 si el modelo está vacío: ahí caen los puntos libres."""
    return float(min((n.z for n in modelo.nodos.values()), default=0.0))


def _a_mundo(renderer, x, y, profundidad):
    renderer.SetDisplayPoint(x, y, profundidad)
    renderer.DisplayToWorld()
    w = np.array(renderer.GetWorldPoint(), dtype=float)
    return w[:3] / w[3]


def punto_en_base(renderer, x, y, base):
    """Punto donde el rayo del mouse corta el plano horizontal z = base, o None.

    El rayo va del plano cercano (profundidad 0) al lejano (1) de la cámara. Da None si el rayo es
    casi horizontal (la base vista de canto) o si el corte queda detrás de la cámara.
    """
    cerca, lejos = _a_mundo(renderer, x, y, 0.0), _a_mundo(renderer, x, y, 1.0)
    d = lejos - cerca
    if abs(d[2]) < 1e-9 * np.linalg.norm(d):
        return None
    t = (base - cerca[2]) / d[2]
    if t < 0:
        return None
    p = cerca + t * d
    p[2] = base
    return p


def cruce_cercano(renderer, x, y, rejilla, tol_px):
    """El cruce de la rejilla más cercano en pantalla a (x, y), a menos de tol_px, o None.

    Si dos quedan igual de cerca (los niveles se superponen en una vista desde arriba), gana el más
    cercano a la cámara."""
    puntos = rejilla.puntos()
    if not len(puntos):
        return None
    xy, profundidad, visibles = proyectar(renderer, puntos)
    distancia = np.hypot(xy[:, 0] - x, xy[:, 1] - y)
    distancia[~visibles] = np.inf
    cerca = distancia <= tol_px
    if not cerca.any():
        return None
    orden = np.lexsort((profundidad, np.round(distancia, 1)))   # primero la distancia, luego la cámara
    return puntos[orden[0]]


@dataclass
class Candidato:
    """Dónde quedaría un punto si se hace clic ahora."""
    punto: np.ndarray = None   # en m; None si el puntero no cae en el plano
    tipo: str = "fuera"        # "nodo", "rejilla" (un cruce), "libre" (en la base) o "fuera"
    nid: int = None            # si tipo es "nodo"


def candidato(renderer, x, y, modelo, rejilla, snap):
    """Punto bajo el puntero: nodo cercano, cruce de la rejilla 3D o, si no, el punto en la base."""
    if snap:
        nid = nodo_cercano(renderer, modelo, x, y, ui.TOL_SNAP_PX)
        if nid is not None:
            return Candidato(np.array(modelo.nodos[nid].coords, dtype=float), "nodo", nid)
        q = cruce_cercano(renderer, x, y, rejilla, ui.TOL_SNAP_PX)
        if q is not None:
            return Candidato(np.array(q, dtype=float), "rejilla")
    p = punto_en_base(renderer, x, y, rejilla.base)
    return Candidato() if p is None else Candidato(p, "libre")


def interpretar(texto, rejilla, ultimo=None):
    """Punto escrito en la barra de comandos, en unidades de pantalla -> punto en m.

    - "x, y, z": absoluto;
    - "x, y": sobre la base (z del nodo más bajo);
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
        return np.array([valores[0], valores[1], rejilla.base])
    raise ValueError("Escribe 3 números (x, y, z) o 2 (x, y sobre la base)")


def texto_coordenadas(cand, inicio=None):
    """Texto de la barra de estado: coordenadas del candidato, si se pegó a un nodo y el largo.

    Vacío si no hay punto: el mouse está fuera del dibujo, sobre el cubo o no cruza el plano."""
    u = unidades.simbolo("longitud")
    if cand.punto is None:
        return ""
    x, y, z = (formato.cantidad(c, "longitud", con_unidad=False) for c in cand.punto)
    texto = f"X {x}   Y {y}   Z {z}   {u}"
    if cand.tipo == "nodo":
        texto += f"   ·  nodo {cand.nid}"
    if inicio is not None:
        texto += f"   ·  L = {formato.cantidad(float(np.linalg.norm(cand.punto - inicio)), 'longitud')}"
    return texto
