"""Datos del modelo: nodos, materiales, secciones (con su refuerzo), barras, casos, cargas y
combinaciones.

No es cálculo. Todo en unidades internas: kN y m (E, G y f'c en kN/m²; A en m²; I y J en m⁴;
peso unitario en kN/m³; cargas en kN, kN/m y kN·m).

Casos de carga: "Muerta" (D, con el peso propio de las barras) y los que defina el usuario (Viva,
Viento...), cada uno con su tipo (las letras de ASCE 7-05 §2.3.2: D, L, Lr, R, W, E, H, F, T).
Cada carga pertenece a un caso.
Combinaciones: un factor por caso (1.2D + 1.6L). Como el análisis es lineal, su resultado es la
suma de los resultados de los casos por sus factores (modelo/analisis.py, combinar). Por ahora
solo sirven para ver resultados; el generador del ASCE 7-05 y las envolventes son la etapa 3.
Tipos de carga:
- CargaNodal: fuerzas y momentos en un nodo, en ejes globales [Fx, Fy, Fz, Mx, My, Mz].
- CargaBarra: en una barra, "uniforme" (kN/m, en toda la barra), "puntual" (kN) o "momento"
  (kN·m) a una distancia a del nodo i. Su dirección es global ("X", "Y", "Z") o local de la barra
  ("x", "y", "z"). El signo dice el sentido: Z con valor negativo es hacia abajo (gravedad).
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
    fc: float = None         # f'c en kN/m² si es concreto (E y G se calcularon con él); si no, None
    gamma: float = 0.0       # peso unitario en kN/m³, para el peso propio (0 = sin peso propio)

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
    material: int = None        # material de la sección: al asignarla a una barra, se asigna también

@dataclass
class Elemento:
    ni: int            # ID del nodo inicial
    nj: int            # ID del nodo final
    material: int      # ID del material (None = sin asignar todavía)
    seccion: int       # ID de la sección (None = sin asignar todavía)
    alfa: float = 0.0  # giro de la sección, en GRADOS

@dataclass
class Caso:
    """Caso de carga. tipo es la letra de las combinaciones (D, L, Lr, W, E...)."""
    nombre: str
    tipo: str = "D"
    peso_propio: float = 1.0   # multiplicador del peso propio de las barras (0 = no lo incluye)

@dataclass
class Combinacion:
    """Combinación de carga: un factor por caso, {ID de caso: factor}."""
    nombre: str
    factores: dict = field(default_factory=dict)

# Tipos de caso: las letras de ASCE 7-05 §2.3.2 (sin S, nieve, que en Panamá no aplica) y un nombre
# propuesto para cada uno
TIPOS_CASO = {"D": "Muerta", "L": "Viva", "Lr": "Viva de techo", "R": "Lluvia", "W": "Viento",
              "E": "Sismo", "H": "Empuje de suelo", "F": "Fluidos", "T": "Temperatura"}

@dataclass
class CargaNodal:
    caso: int
    nodo: int
    fuerzas: list              # [Fx, Fy, Fz, Mx, My, Mz] en ejes globales (kN y kN·m)

@dataclass
class CargaBarra:
    caso: int
    barra: int
    tipo: str                  # "uniforme" (kN/m), "puntual" (kN) o "momento" (kN·m)
    valor: float
    direccion: str             # "X", "Y", "Z" (globales) o "x", "y", "z" (locales de la barra)
    a: float = 0.0             # puntual y momento: distancia desde el nodo i, en m

TIPOS_CARGA_BARRA = ("uniforme", "puntual", "momento")
DIRECCIONES = ("X", "Y", "Z", "x", "y", "z")

class Modelo:
    def __init__(self):
        self.nodos = {}        # id -> Nodo
        self.elementos = {}    # id -> Elemento
        self.materiales = {}   # id -> Material
        self.secciones = {}    # id -> Seccion
        self.casos = {1: Caso("Muerta", "D", 1.0)}   # Muerta (con peso propio) y los que se definan
        self.cargas = {}       # id -> CargaNodal o CargaBarra
        self.combinaciones = {}  # id -> Combinacion
        self._sig_id = {"nodo": 1, "elem": 1, "mat": 1, "sec": 1, "caso": 2, "carga": 1, "combo": 1}

    def _nuevo_id(self, tipo):
        i = self._sig_id[tipo]
        self._sig_id[tipo] += 1
        return i

    def agregar_nodo(self, x, y, z):
        nid = self._nuevo_id("nodo")
        self.nodos[nid] = Nodo(x, y, z)
        return nid

    def agregar_material(self, nombre, e, g, fc=None, gamma=0.0):
        mid = self._nuevo_id("mat")
        self.materiales[mid] = Material(nombre, e, g, fc, gamma)
        return mid

    def agregar_seccion(self, nombre, a, iy, iz, j, concreto=None, material=None):
        if material is not None and material not in self.materiales:
            raise KeyError(f"El material {material} no existe")
        sid = self._nuevo_id("sec")
        self.secciones[sid] = Seccion(nombre, a, iy, iz, j, concreto, material)
        return sid

    def asignar_seccion(self, eid, sid):
        """Asigna la sección sid a la barra eid y, si la sección tiene material, también ese material.
        sid = None deja la barra sin sección."""
        if eid not in self.elementos:
            raise KeyError(f"El elemento {eid} no existe")
        if sid is not None and sid not in self.secciones:
            raise KeyError(f"La sección {sid} no existe")
        el = self.elementos[eid]
        el.seccion = sid
        if sid is not None and self.secciones[sid].material is not None:
            el.material = self.secciones[sid].material

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

    def es_columna(self, eid):
        """True si la barra es vertical: eso la hace columna (las horizontales son vigas)."""
        el = self.elementos[eid]
        a, b = self.nodos[el.ni], self.nodos[el.nj]
        dx, dy, dz = b.x - a.x, b.y - a.y, b.z - a.z
        return abs(dz) > 0 and math.hypot(dx, dy) <= TOL_RELATIVA * (abs(dx) + abs(dy) + abs(dz))

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

    # ---------- CARGAS ----------
    def caso_inicial(self):
        """El primer caso (Muerta): ahí van las cargas si no se dice otro."""
        return min(self.casos)

    def cargar(self, nid, fx=0.0, fy=0.0, fz=0.0, mx=0.0, my=0.0, mz=0.0, caso=None):
        """Carga nodal (ejes globales). Devuelve su ID."""
        return self.agregar_carga_nodal(nid, [fx, fy, fz, mx, my, mz], caso)

    def agregar_carga_nodal(self, nid, fuerzas, caso=None):
        caso = self.caso_inicial() if caso is None else caso
        if nid not in self.nodos:
            raise KeyError(f"El nodo {nid} no existe")
        if caso not in self.casos:
            raise KeyError(f"El caso {caso} no existe")
        if len(fuerzas) != 6:
            raise ValueError("Una carga nodal tiene 6 valores: Fx, Fy, Fz, Mx, My, Mz")
        cid = self._nuevo_id("carga")
        self.cargas[cid] = CargaNodal(caso, nid, [float(f) for f in fuerzas])
        return cid

    def agregar_carga_barra(self, eid, tipo, valor, direccion, a=0.0, caso=None):
        caso = self.caso_inicial() if caso is None else caso
        if eid not in self.elementos:
            raise KeyError(f"El elemento {eid} no existe")
        if caso not in self.casos:
            raise KeyError(f"El caso {caso} no existe")
        if tipo not in TIPOS_CARGA_BARRA:
            raise ValueError(f"Tipo de carga desconocido: {tipo}")
        if direccion not in DIRECCIONES:
            raise ValueError(f"Dirección desconocida: {direccion}")
        el = self.elementos[eid]
        largo = self.nodos[el.ni].distancia(self.nodos[el.nj])
        if tipo != "uniforme" and not 0 <= a <= largo + TOL_LONGITUD:
            raise ValueError(f"La distancia a debe estar entre 0 y el largo de la barra ({largo:.3f} m)")
        cid = self._nuevo_id("carga")
        self.cargas[cid] = CargaBarra(caso, eid, tipo, float(valor), direccion, float(a))
        return cid

    def cargas_en(self, tipo, ident, caso=None):
        """IDs de las cargas de un nodo (tipo "nodo") o de una barra (tipo "barra"), de un caso o de todos."""
        clase = CargaNodal if tipo == "nodo" else CargaBarra
        return [cid for cid, c in self.cargas.items() if isinstance(c, clase)
                and (c.nodo if clase is CargaNodal else c.barra) == ident
                and (caso is None or c.caso == caso)]

    def eliminar_carga(self, cid):
        if cid not in self.cargas:
            raise KeyError(f"La carga {cid} no existe")
        del self.cargas[cid]

    # ---------- CASOS ----------
    def agregar_caso(self, nombre, tipo="L", peso_propio=0.0):
        """Caso nuevo. Sin nombre, toma el propuesto para su tipo ("Viva" para L). Devuelve su ID."""
        self._revisar_caso(tipo, peso_propio)
        cid = self._nuevo_id("caso")
        self.casos[cid] = Caso(nombre.strip() or TIPOS_CASO[tipo], tipo, float(peso_propio))
        return cid

    def cambiar_caso(self, cid, nombre, tipo, peso_propio):
        if cid not in self.casos:
            raise KeyError(f"El caso {cid} no existe")
        self._revisar_caso(tipo, peso_propio)
        caso = self.casos[cid]
        caso.nombre, caso.tipo, caso.peso_propio = nombre.strip() or TIPOS_CASO[tipo], tipo, float(peso_propio)

    @staticmethod
    def _revisar_caso(tipo, peso_propio):
        if tipo not in TIPOS_CASO:
            raise ValueError(f"Tipo de caso desconocido: {tipo}")
        if not math.isfinite(float(peso_propio)) or peso_propio < 0:
            raise ValueError("El factor del peso propio debe ser 0 o positivo")

    def uso_caso(self, cid):
        """(cargas, combinaciones) que usan el caso cid."""
        return ([c for c, carga in self.cargas.items() if carga.caso == cid],
                [k for k, co in self.combinaciones.items() if cid in co.factores])

    def eliminar_caso(self, cid):
        """Elimina un caso sin cargas que no esté en ninguna combinación. Siempre queda uno."""
        if cid not in self.casos:
            raise KeyError(f"El caso {cid} no existe")
        if len(self.casos) == 1:
            raise ValueError("Tiene que quedar al menos un caso de carga")
        cargas, combos = self.uso_caso(cid)
        if cargas or combos:
            raise ValueError(f"El caso {self.casos[cid].nombre} está en uso ({len(cargas)} cargas y "
                             f"{len(combos)} combinaciones)")
        del self.casos[cid]

    # ---------- COMBINACIONES ----------
    def _factores(self, factores):
        """Los factores limpios: {ID de caso: factor}, sin los 0. ValueError si no queda ninguno."""
        limpios = {}
        for cid, f in factores.items():
            cid, f = int(cid), float(f)
            if cid not in self.casos:
                raise KeyError(f"El caso {cid} no existe")
            if not math.isfinite(f):
                raise ValueError("Los factores deben ser números")
            if f != 0:
                limpios[cid] = f
        if not limpios:
            raise ValueError("La combinación necesita al menos un factor distinto de 0")
        return limpios

    def nombre_combinacion(self, factores):
        """Nombre automático: "1.2D + 1.6L" (con el nombre del caso si hay dos del mismo tipo)."""
        tipos = [c.tipo for c in self.casos.values()]
        texto = ""
        for cid, f in factores.items():
            caso = self.casos[cid]
            etiqueta = caso.tipo if tipos.count(caso.tipo) == 1 else f" {caso.nombre}"
            numero = "" if abs(f) == 1 else f"{abs(f):g}"
            termino = f"{numero}{etiqueta}".strip()
            texto += (" - " if f < 0 else " + ") + termino if texto else ("-" if f < 0 else "") + termino
        return texto

    def agregar_combinacion(self, nombre, factores):
        """Combinación nueva. Sin nombre, el automático. Devuelve su ID."""
        factores = self._factores(factores)
        coid = self._nuevo_id("combo")
        self.combinaciones[coid] = Combinacion(nombre.strip() or self.nombre_combinacion(factores), factores)
        return coid

    def cambiar_combinacion(self, coid, nombre, factores):
        if coid not in self.combinaciones:
            raise KeyError(f"La combinación {coid} no existe")
        factores = self._factores(factores)
        co = self.combinaciones[coid]
        co.nombre, co.factores = nombre.strip() or self.nombre_combinacion(factores), factores

    def eliminar_combinacion(self, coid):
        if coid not in self.combinaciones:
            raise KeyError(f"La combinación {coid} no existe")
        del self.combinaciones[coid]

    # ---------- ELIMINAR ----------
    def eliminar_elemento(self, eid):
        """Elimina la barra y sus cargas."""
        if eid not in self.elementos:
            raise KeyError(f"El elemento {eid} no existe")
        for cid in self.cargas_en("barra", eid):
            del self.cargas[cid]
        del self.elementos[eid]

    def eliminar_nodo(self, nid):
        """Elimina el nodo y las barras conectadas. Devuelve los IDs de barras borradas."""
        if nid not in self.nodos:
            raise KeyError(f"El nodo {nid} no existe")
        borradas = self.elementos_conectados(nid)
        for eid in borradas:
            self.eliminar_elemento(eid)          # con sus cargas
        for cid in self.cargas_en("nodo", nid):
            del self.cargas[cid]
        del self.nodos[nid]
        return borradas

    def eliminar_material(self, mid):
        if mid not in self.materiales:
            raise KeyError(f"El material {mid} no existe")
        en_uso = [eid for eid, el in self.elementos.items() if el.material == mid]
        if en_uso:
            raise ValueError(f"El material {mid} está en uso en las barras {en_uso}")
        secciones = [sid for sid, sec in self.secciones.items() if sec.material == mid]
        if secciones:
            raise ValueError(f"El material {mid} está en uso en las secciones {secciones}")
        del self.materiales[mid]

    def eliminar_seccion(self, sid):
        if sid not in self.secciones:
            raise KeyError(f"La sección {sid} no existe")
        en_uso = [eid for eid, el in self.elementos.items() if el.seccion == sid]
        if en_uso:
            raise ValueError(f"La sección {sid} está en uso en las barras {en_uso}")
        del self.secciones[sid]