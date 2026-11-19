"""Datos del modelo: nodos, materiales, secciones (con su refuerzo), barras, casos, cargas y
combinaciones.

No es cálculo. Todo en unidades internas: kN y m (E, G y f'c en kN/m²; A en m²; I y J en m⁴;
peso unitario en kN/m³; cargas en kN, kN/m y kN·m).

Casos de carga. Cada carga pertenece a un caso, y cada caso tiene un tipo (la letra de las
combinaciones de ASCE 7-05 §2.3.2; por ahora D muerta, L viva, Lr viva de techo, W viento y E sismo):
- "Peso propio" (D): automático. Sus cargas no se guardan: salen de A·γ de cada barra, por el
  factor `peso_propio` del caso (modelo/analisis.py). Un caso con ese factor distinto de 0 es
  "automático": en la interfaz no recibe cargas a mano.
- "Carga muerta adicional" (D): las cargas muertas que pone el usuario. Es el caso inicial: ahí van
  las cargas si no se dice otro.
- Los que agregue el usuario (Viva, Viento, Sismo u otra Muerta).
La carga muerta total (D) es la suma de todos los casos tipo D: peso propio más la adicional.

Combinaciones: un factor por TIPO de caso ({"D": 1.2, "L": 1.6}), que se aplica a todos los casos
de ese tipo. Como el análisis es lineal, su resultado es la suma de los resultados de los casos por
sus factores (modelo/analisis.py, combinar). Aquí se guardan las propias del usuario; las
predeterminadas (ASCE 7-05) salen de modelo/combinaciones.py con los datos del sismo del modelo
(SDS y ρ). Por ahora solo sirven para ver resultados.

Tipos de carga:
- CargaNodal: fuerzas y momentos en un nodo, en ejes globales [Fx, Fy, Fz, Mx, My, Mz].
- CargaBarra: en una barra, "uniforme" (kN/m, en toda la barra), "puntual" (kN) o "momento"
  (kN·m) a una distancia a del nodo i. Su dirección es global ("X", "Y", "Z") o local de la barra
  ("x", "y", "z"). El signo dice el sentido: Z con valor negativo es hacia abajo (gravedad).
"""
import math
from dataclasses import dataclass, field
from calculo.tolerancias import TOL_LONGITUD, TOL_RELATIVA

FY_DEFECTO = 60 * 6894.757293168361      # 60 ksi en kN/m² (acero Grado 60)

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
    abajo) y ny (filas). Circular: D y nbarras (siempre con aros: estribos circulares). T (vigas y
    viguetas, sin diagrama de interacción): b es el ancho del alma (bw), h la altura total, bf y hf
    el ala, nx las barras de abajo en el alma (ny = 1, número `barra`) y n_sup las de arriba (número
    `barra_sup`; 0 = sin acero arriba), con el recubrimiento libre y el estribo (número y separación;
    0 = sin estribos). En la T, d (de abajo al centro de las barras de abajo) sale del recubrimiento:
    d = rec + d_estribo + db/2. En todas: d (del borde al centro de las barras), f'c, el número de
    barra y fy del refuerzo.
    """
    forma: str               # "rectangular", "circular" o "T"
    fc: float                # f'c, en kN/m²
    d: float                 # del borde al centro de las barras, en m
    barra: int               # número de barra (#)
    b: float = 0.0           # rectangular: ancho, en m
    h: float = 0.0           # rectangular: alto, en m
    nx: int = 0              # rectangular: barras en las caras de arriba y abajo
    ny: int = 0              # rectangular: filas de barras
    D: float = 0.0           # circular: diámetro, en m
    nbarras: int = 0         # circular: cantidad de barras
    fy: float = FY_DEFECTO   # fluencia del refuerzo, en kN/m² (Grado 60 por defecto)
    bf: float = 0.0          # T: ancho del ala, en m (b es el ancho del alma, bw)
    hf: float = 0.0          # T: espesor del ala, en m
    barra_sup: int = 0       # T: número de las barras de arriba (momento negativo); 0 = sin barras
    n_sup: int = 0           # T: cuántas barras arriba
    recubrimiento: float = 0.0   # T: recubrimiento libre (al estribo, o a la barra si no hay), en m
    estribo: int = 0         # T: número del estribo (0 = sin estribos)
    s_estribo: float = 0.0   # T: separación de los estribos, en m

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
    """Caso de carga. tipo es la letra de las combinaciones (D, L, Lr, W o E)."""
    nombre: str
    tipo: str = "D"
    peso_propio: float = 0.0   # multiplicador del peso propio de las barras (0 = no lo incluye)
    viva_losas: bool = False   # el caso automático con la viva de las losas (sus cargas no se guardan)

@dataclass
class Combinacion:
    """Combinación de carga: un factor por tipo de caso, {"D": 1.2, "L": 1.6}."""
    nombre: str
    factores: dict = field(default_factory=dict)

# Tipos de caso que se pueden crear por ahora: la letra de ASCE 7-05 §2.3.2 y su nombre
TIPOS_CASO = {"D": "Muerta", "L": "Viva", "Lr": "Viva de techo", "W": "Viento", "E": "Sismo"}
NOMBRE_PESO_PROPIO = "Peso propio"
NOMBRE_MUERTA_ADICIONAL = "Carga muerta adicional"


def nombre_combinacion(factores):
    """Nombre automático de una combinación: "1.2D + 1.6L", "0.9D - 1.6W", "D"."""
    texto = ""
    for tipo, f in factores.items():
        termino = ("" if abs(f) == 1 else f"{abs(f):g}") + tipo
        if texto:
            texto += (" - " if f < 0 else " + ") + termino
        else:
            texto = ("-" if f < 0 else "") + termino
    return texto

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
        # Peso propio se muestra primero (el orden del diccionario), pero lleva el ID 2: el caso 1 sigue
        # siendo el caso inicial, donde van las cargas si no se dice otro.
        self.casos = {2: Caso(NOMBRE_PESO_PROPIO, "D", 1.0), 1: Caso(NOMBRE_MUERTA_ADICIONAL, "D", 0.0)}
        self.cargas = {}       # id -> CargaNodal o CargaBarra
        self.combinaciones = {}  # id -> Combinacion: las propias (las predeterminadas, modelo/combinaciones.py)
        # Datos del sismo para las combinaciones 5 y 7 (ASCE 7-05 §12.4.2.3). Provisionales, a mano: los
        # valores reales saldrán de la etapa de sismo (SDS del sitio; ρ = 1.0 o 1.3, §12.3.4).
        self.sds, self.rho = 0.5, 1.3
        # Pórticos especiales (SMF), lo usual en Panamá (CDS D): cuantía de columnas ≤ 6 % (ACI §18.7.4.1)
        self.portico_especial = True
        self.losas = {}        # id -> Losa (modelo/losas.py): losas de viguetas, con sus paños
        self._sig_id = {"nodo": 1, "elem": 1, "mat": 1, "sec": 1, "caso": 3, "carga": 1, "combo": 1,
                        "losa": 1, "pano": 1}

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
        """El caso donde van las cargas si no se dice otro: el primero que no es automático
        (Carga muerta adicional). Si todos lo fueran, el primero."""
        manuales = [cid for cid, c in self.casos.items() if not c.peso_propio and not c.viva_losas]
        return min(manuales) if manuales else min(self.casos)

    def es_automatico(self, cid):
        """True si el caso es automático: el de peso propio (sus cargas salen de A·γ de cada barra) o el
        de la viva de las losas (sale de las losas). No reciben cargas a mano."""
        return bool(self.casos[cid].peso_propio) or self.casos[cid].viva_losas

    def caso_viva_losas(self):
        """ID del caso automático "Viva de losas", o None si no hay."""
        return next((cid for cid, c in self.casos.items() if c.viva_losas), None)

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
    def tipos_de_caso(self):
        """Los tipos que se pueden usar: los de TIPOS_CASO y, si un archivo viejo trae otro, ese también."""
        return list(TIPOS_CASO) + [c.tipo for c in self.casos.values() if c.tipo not in TIPOS_CASO]

    def agregar_caso(self, nombre, tipo="L", peso_propio=0.0):
        """Caso nuevo. Sin nombre, toma el de su tipo ("Viva" para L). Devuelve su ID."""
        self._revisar_caso(tipo, peso_propio)
        cid = self._nuevo_id("caso")
        self.casos[cid] = Caso(nombre.strip() or TIPOS_CASO.get(tipo, tipo), tipo, float(peso_propio))
        return cid

    def cambiar_caso(self, cid, nombre, tipo, peso_propio=None):
        """Cambia el nombre y el tipo de un caso (y su factor de peso propio, si se da)."""
        if cid not in self.casos:
            raise KeyError(f"El caso {cid} no existe")
        caso = self.casos[cid]
        peso_propio = caso.peso_propio if peso_propio is None else peso_propio
        self._revisar_caso(tipo, peso_propio)
        caso.nombre, caso.tipo, caso.peso_propio = nombre.strip() or TIPOS_CASO.get(tipo, tipo), tipo, float(peso_propio)

    def _revisar_caso(self, tipo, peso_propio):
        if tipo not in self.tipos_de_caso():
            raise ValueError(f"Tipo de caso desconocido: {tipo}")
        if not math.isfinite(float(peso_propio)) or peso_propio < 0:
            raise ValueError("El factor del peso propio debe ser 0 o positivo")

    def uso_caso(self, cid):
        """IDs de las cargas del caso cid."""
        return [c for c, carga in self.cargas.items() if carga.caso == cid]

    def es_fijo(self, cid):
        """True si el caso no se puede eliminar ni cambiar: el de peso propio y el caso inicial (así
        siempre hay peso propio y siempre hay dónde poner cargas)."""
        return self.es_automatico(cid) or cid == self.caso_inicial()

    def eliminar_caso(self, cid):
        """Elimina un caso sin cargas. Los fijos (peso propio y caso inicial) no se eliminan."""
        if cid not in self.casos:
            raise KeyError(f"El caso {cid} no existe")
        if self.es_fijo(cid):
            raise ValueError(f"El caso {self.casos[cid].nombre} no se puede eliminar")
        cargas = self.uso_caso(cid)
        if cargas:
            raise ValueError(f"El caso {self.casos[cid].nombre} tiene {len(cargas)} cargas: bórralas primero")
        del self.casos[cid]

    # ---------- COMBINACIONES ----------
    def _factores(self, factores):
        """Los factores limpios: {tipo de caso: factor}, sin los 0. ValueError si no queda ninguno."""
        limpios = {}
        permitidos = self.tipos_de_caso()
        for tipo, f in factores.items():
            f = float(f)
            if tipo not in permitidos:
                raise ValueError(f"Tipo de caso desconocido: {tipo}")
            if not math.isfinite(f):
                raise ValueError("Los factores deben ser números")
            if f != 0:
                limpios[tipo] = f
        if not limpios:
            raise ValueError("La combinación necesita al menos un factor distinto de 0")
        return limpios

    def agregar_combinacion(self, nombre, factores):
        """Combinación propia nueva: {tipo de caso: factor}. Sin nombre, el automático. Devuelve su ID."""
        factores = self._factores(factores)
        coid = self._nuevo_id("combo")
        self.combinaciones[coid] = Combinacion(nombre.strip() or nombre_combinacion(factores), factores)
        return coid

    def cambiar_combinacion(self, coid, nombre, factores):
        if coid not in self.combinaciones:
            raise KeyError(f"La combinación {coid} no existe")
        factores = self._factores(factores)
        co = self.combinaciones[coid]
        co.nombre, co.factores = nombre.strip() or nombre_combinacion(factores), factores

    def eliminar_combinacion(self, coid):
        if coid not in self.combinaciones:
            raise KeyError(f"La combinación {coid} no existe")
        del self.combinaciones[coid]

    def poner_sismo(self, sds, rho, portico_especial=None):
        """Datos del sismo para las combinaciones 5 y 7 (ASCE 7-05 §12.4.2.3): SDS y la redundancia ρ,
        que solo puede ser 1.0 o 1.3 (§12.3.4). portico_especial (None: no se cambia): si los pórticos
        son especiales (cambia, por ejemplo, la cuantía máxima de las columnas, ACI 318-19 §18.7.4.1)."""
        sds, rho = float(sds), float(rho)
        if not math.isfinite(sds) or sds < 0:
            raise ValueError("SDS debe ser 0 o positivo")
        if min(abs(rho - 1.0), abs(rho - 1.3)) > 1e-9:
            raise ValueError("ρ solo puede ser 1.0 o 1.3 (ASCE 7-05 §12.3.4)")
        self.sds, self.rho = sds, rho
        if portico_especial is not None:
            self.portico_especial = bool(portico_especial)

    # ---------- LOSAS ----------
    def agregar_losa(self, nombre, seccion, n_viguetas=1):
        """Losa de viguetas nueva (sin paños), con la sección T de su vigueta. Crea el caso automático
        "Viva de losas" si no existe. Devuelve su ID."""
        from modelo.losas import NOMBRE_VIVA_LOSAS, Losa
        sec = self.secciones.get(seccion)
        if sec is None or sec.concreto is None or sec.concreto.forma != "T":
            raise ValueError("La vigueta debe ser una sección T de concreto (Definir → Secciones → Nueva T…)")
        if int(n_viguetas) < 1:
            raise ValueError("Pon al menos una vigueta")
        lid = self._nuevo_id("losa")
        self.losas[lid] = Losa(nombre.strip() or f"Losa {lid}", seccion, n_viguetas=int(n_viguetas))
        if self.caso_viva_losas() is None:
            cid = self._nuevo_id("caso")
            self.casos[cid] = Caso(NOMBRE_VIVA_LOSAS, "L", 0.0, True)
        return lid

    def agregar_pano(self, lid, viga_a, viga_b, muerta=0.0, viva=0.0):
        """Paño de la losa lid entre las vigas viga_a y viga_b (dos barras paralelas, enfrentadas; si
        una está partida, se toman las que siguen en línea). Cargas en kN/m². Devuelve su ID.
        ValueError si el paño no sirve (y la losa queda como estaba)."""
        from modelo import losas as ml
        if lid not in self.losas:
            raise KeyError(f"La losa {lid} no existe")
        if muerta < 0 or viva < 0:
            raise ValueError("Las cargas de la losa van positivas (hacia abajo)")
        losa = self.losas[lid]
        ejes = ml.ejes_losa(self, losa) if losa.panos else None
        if ejes is not None:
            t = ml.marco(self, viga_a)[0]
            if abs(t @ ejes[0]) < ml.PARALELA:
                raise ValueError("Las viguetas de una losa van todas en la misma dirección: estas vigas no son "
                                 "paralelas a las de los otros paños (crea otra losa)")
        geo = ml.geometria_pano(self, ml.Pano([viga_a], [viga_b]), ejes)
        pid = self._sig_id["pano"]
        losa.panos[pid] = ml.Pano(geo.apoyo_a, geo.apoyo_b, float(muerta), float(viva))
        try:
            ml.geometrias(self, losa)                 # que no se enciman con los demás
            ml.franjas(self, losa)                    # y que las vigas no queden partidas entre franjas
            if losa.referencia is None:
                losa.referencia = pid
            ml.actualizar_seccion(self, losa)
        except ValueError:
            del losa.panos[pid]
            raise
        self._sig_id["pano"] += 1
        return pid

    def losa_de_pano(self, pid):
        """ID de la losa que tiene el paño pid, o None."""
        return next((lid for lid, losa in self.losas.items() if pid in losa.panos), None)

    def eliminar_pano(self, pid):
        """Elimina el paño (y su losa, si se queda sin paños)."""
        lid = self.losa_de_pano(pid)
        if lid is None:
            raise KeyError(f"El paño {pid} no existe")
        losa = self.losas[lid]
        del losa.panos[pid]
        if not losa.panos:
            self.eliminar_losa(lid)
            return
        if losa.referencia == pid:
            losa.referencia = next(iter(losa.panos))

    def eliminar_losa(self, lid):
        """Elimina la losa. Sin losas, el caso "Viva de losas" ya no hace falta y se quita."""
        if lid not in self.losas:
            raise KeyError(f"La losa {lid} no existe")
        del self.losas[lid]
        cid = self.caso_viva_losas()
        if not self.losas and cid is not None and not self.uso_caso(cid):
            del self.casos[cid]

    # ---------- ELIMINAR ----------
    def eliminar_elemento(self, eid):
        """Elimina la barra y sus cargas, y los paños de losa que se apoyan en ella."""
        if eid not in self.elementos:
            raise KeyError(f"El elemento {eid} no existe")
        for cid in self.cargas_en("barra", eid):
            del self.cargas[cid]
        for losa in list(self.losas.values()):
            for pid, pano in list(losa.panos.items()):
                if eid in pano.apoyo_a or eid in pano.apoyo_b:
                    self.eliminar_pano(pid)
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
        losas = [losa.nombre for losa in self.losas.values() if losa.seccion == sid]
        if losas:
            raise ValueError(f"La sección {sid} es la vigueta de {', '.join(losas)}")
        del self.secciones[sid]