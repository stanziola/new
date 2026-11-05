import math
from dataclasses import dataclass, field
from configuracion import TOL_LONGITUD, TOL_RELATIVA

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

    # ---------- CONSULTAS ----------
    def elementos_conectados(self, nid):
        """IDs de las barras que llegan al nodo nid."""
        return [eid for eid, el in self.elementos.items() if nid in (el.ni, el.nj)]

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