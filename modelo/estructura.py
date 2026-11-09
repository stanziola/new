"""Datos del modelo: nodos, materiales, secciones (con su refuerzo) y barras. No es cálculo.

Todo en unidades internas: kN y m (E, G y f'c en kN/m²; A en m²; I y J en m⁴).
"""
import math
from dataclasses import dataclass, field
from calculo.tolerancias import TOL_LONGITUD, TOL_RELATIVA

@dataclass
class Nodo:
    x: float
    y: float
    z: float
    apoyo: list = field(default_factory=lambda: [False] * 6)   # Dx, Dy, Dz, Phix, Phiy, Phiz
    carga: list = field(default_factory=lambda: [0.0] * 6)     # Fx, Fy, Fz, Mx, My, Mz

    @property
    def coords(self):
        return (self.x, self.y, self.z)

    def distancia(self, otro):
        """Distancia entre este nodo y otro."""
        return math.dist(self.coords, otro.coords)

@dataclass
class Material:
    nombre: str
    e: float
    g: float

@dataclass
class Concreto:
    """Geometría y refuerzo de una sección de concreto, para su diagrama de interacción.

    Todo en unidades internas (m y kN/m²). Rectangular: b, h, nx (barras en las caras de arriba y
    abajo) y ny (filas). Circular: D y nbarras. En las dos: d (del borde al centro de las barras),
    f'c y el número de barra.
    """
    forma: str               # "rectangular" o "circular"
    fc: float                # f'c, en kN/m²
    d: float                 # del borde al centro de las barras, en m
    barra: int               # número de barra (#)
    b: float = 0.0           # rectangular: ancho, en m
    h: float = 0.0           # rectangular: alto, en m
    nx: int = 0              # rectangular: barras en las caras de arriba y abajo
    ny: int = 0              # rectangular: filas de barras
    D: float = 0.0           # circular: diámetro, en m
    nbarras: int = 0         # circular: cantidad de barras

@dataclass
class Seccion:
    nombre: str
    a: float
    iy: float
    iz: float
    j: float
    concreto: Concreto = None   # geometría y refuerzo (None si no es de concreto o no se definió)

@dataclass
class Elemento:
    ni: int            # ID del nodo inicial
    nj: int            # ID del nodo final
    material: int      # ID del material (None = sin asignar todavía)
    seccion: int       # ID de la sección (None = sin asignar todavía)
    alfa: float = 0.0  # giro de la sección, en GRADOS

class Modelo:
    def __init__(self):
        self.nodos = {}        # id -> Nodo
        self.elementos = {}    # id -> Elemento
        self.materiales = {}   # id -> Material
        self.secciones = {}    # id -> Seccion
        self._sig_id = {"nodo": 1, "elem": 1, "mat": 1, "sec": 1}

    def _nuevo_id(self, tipo):
        i = self._sig_id[tipo]
        self._sig_id[tipo] += 1
        return i

    def agregar_nodo(self, x, y, z):
        nid = self._nuevo_id("nodo")
        self.nodos[nid] = Nodo(x, y, z)
        return nid

    def agregar_material(self, nombre, e, g):
        mid = self._nuevo_id("mat")
        self.materiales[mid] = Material(nombre, e, g)
        return mid

    def agregar_seccion(self, nombre, a, iy, iz, j, concreto=None):
        sid = self._nuevo_id("sec")
        self.secciones[sid] = Seccion(nombre, a, iy, iz, j, concreto)
        return sid

    def agregar_elemento(self, ni, nj, material=None, seccion=None, alfa=0.0):
        """Agrega una barra. El material y la sección pueden quedar sin asignar (None): la barra
        se dibuja, pero el análisis se niega hasta que se asignen."""
        # 1. Que los nodos existan
        for nid in (ni, nj):
            if nid not in self.nodos:
                raise KeyError(f"El nodo {nid} no existe")

        # 2. Que no sea el mismo nodo
        if ni == nj:
            raise ValueError("Una barra no puede empezar y terminar en el mismo nodo")

        # 3. Que los nodos no estén en la misma posición
        a, b = self.nodos[ni], self.nodos[nj]
        if a.distancia(b) < TOL_LONGITUD:
            raise ValueError(f"Los nodos {ni} y {nj} están en la misma posición: {a.coords} y {b.coords}")

        # 4. Que el material y la sección existan (si se dieron)
        if material is not None and material not in self.materiales:
            raise KeyError(f"El material {material} no existe")
        if seccion is not None and seccion not in self.secciones:
            raise KeyError(f"La sección {seccion} no existe")

        # 5. Ordenar según la convención y guardar
        ni, nj = self._ordenar(ni, nj)
        eid = self._nuevo_id("elem")
        self.elementos[eid] = Elemento(ni, nj, material, seccion, alfa)
        return eid

    def _ordenar(self, ni, nj):
        a, b = self.nodos[ni], self.nodos[nj]
        dx, dy, dz = b.x - a.x, b.y - a.y, b.z - a.z
        tol = TOL_RELATIVA * (abs(dx) + abs(dy) + abs(dz))
        if abs(dz) > tol:
            invertir = dz < 0
        elif abs(dx) > tol:
            invertir = dx < 0
        else:
            invertir = dy < 0
        return (nj, ni) if invertir else (ni, nj)

    # ---------- CONSULTAS ----------
    def elementos_conectados(self, nid):
        """IDs de las barras que llegan al nodo nid."""
        return [eid for eid, el in self.elementos.items() if nid in (el.ni, el.nj)]

    def nodo_en(self, x, y, z):
        """ID del nodo que está en (x, y, z), o None (con la tolerancia TOL_LONGITUD)."""
        for nid, n in self.nodos.items():
            if math.dist(n.coords, (x, y, z)) < TOL_LONGITUD:
                return nid
        return None

    def elemento_entre(self, ni, nj):
        """ID de la barra que une los nodos ni y nj (en cualquier orden), o None."""
        for eid, el in self.elementos.items():
            if {el.ni, el.nj} == {ni, nj}:
                return eid
        return None

    def sin_asignar(self):
        """IDs de las barras a las que les falta el material o la sección."""
        return [eid for eid, el in self.elementos.items()
                if el.material is None or el.seccion is None]

    # ---------- MODIFICAR ----------
    def mover_nodo(self, nid, x, y, z):
        if nid not in self.nodos:
            raise KeyError(f"El nodo {nid} no existe")
        nuevo = Nodo(x, y, z)
        for eid in self.elementos_conectados(nid):
            el = self.elementos[eid]
            otro = el.nj if el.ni == nid else el.ni
            if nuevo.distancia(self.nodos[otro]) < TOL_LONGITUD:
                raise ValueError(f"Mover el nodo {nid} ahí deja la barra {eid} con longitud 0")
        n = self.nodos[nid]
        n.x, n.y, n.z = x, y, z
        for eid in self.elementos_conectados(nid):      # puede haber cambiado la dirección
            el = self.elementos[eid]
            el.ni, el.nj = self._ordenar(el.ni, el.nj)

    def restringir(self, nid, dx=True, dy=True, dz=True, phix=True, phiy=True, phiz=True):
        if nid not in self.nodos:
            raise KeyError(f"El nodo {nid} no existe")
        self.nodos[nid].apoyo = [dx, dy, dz, phix, phiy, phiz]

    def cargar(self, nid, fx=0.0, fy=0.0, fz=0.0, mx=0.0, my=0.0, mz=0.0):
        if nid not in self.nodos:
            raise KeyError(f"El nodo {nid} no existe")
        self.nodos[nid].carga = [fx, fy, fz, mx, my, mz]

    # ---------- ELIMINAR ----------
    def eliminar_elemento(self, eid):
        if eid not in self.elementos:
            raise KeyError(f"El elemento {eid} no existe")
        del self.elementos[eid]

    def eliminar_nodo(self, nid):
        """Elimina el nodo y las barras conectadas. Devuelve los IDs de barras borradas."""
        if nid not in self.nodos:
            raise KeyError(f"El nodo {nid} no existe")
        borradas = self.elementos_conectados(nid)
        for eid in borradas:
            del self.elementos[eid]
        del self.nodos[nid]
        return borradas

    def eliminar_material(self, mid):
        if mid not in self.materiales:
            raise KeyError(f"El material {mid} no existe")
        en_uso = [eid for eid, el in self.elementos.items() if el.material == mid]
        if en_uso:
            raise ValueError(f"El material {mid} está en uso en las barras {en_uso}")
        del self.materiales[mid]

    def eliminar_seccion(self, sid):
        if sid not in self.secciones:
            raise KeyError(f"La sección {sid} no existe")
        en_uso = [eid for eid, el in self.elementos.items() if el.seccion == sid]
        if en_uso:
            raise ValueError(f"La sección {sid} está en uso en las barras {en_uso}")
        del self.secciones[sid]