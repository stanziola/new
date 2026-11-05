import math
from dataclasses import dataclass, field
from configuracion import TOL_LONGITUD, TOL_RELATIVA

@dataclass
class Nodo:
    x: float
    y: float
    z: float
    apoyo: list = field(default_factory=lambda: [False] * 6)   # ux, uy, uz, rx, ry, rz
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
class Seccion:
    nombre: str
    a: float
    iy: float
    iz: float
    j: float

@dataclass
class Elemento:
    ni: int            # ID del nodo inicial
    nj: int            # ID del nodo final
    material: int      # ID del material
    seccion: int       # ID de la sección
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

    def agregar_seccion(self, nombre, a, iy, iz, j):
        sid = self._nuevo_id("sec")
        self.secciones[sid] = Seccion(nombre, a, iy, iz, j)
        return sid

    def agregar_elemento(self, ni, nj, material, seccion, alfa=0.0):
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

        # 4. Que el material y la sección existan
        if material not in self.materiales:
            raise KeyError(f"El material {material} no existe")
        if seccion not in self.secciones:
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