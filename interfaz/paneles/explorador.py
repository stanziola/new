"""Explorador del modelo (izquierda), como el de ETABS o Civil 3D.

- Pestaña Modelo: nodos, elementos, apoyos y cargas. Elegir uno lo selecciona en 3D y lo muestra
  en Propiedades. Un apoyo es un objeto aparte ("apoyo", ID del nodo): se puede elegir y borrar
  solo. Las cargas son las del caso activo (viendo una combinación no se listan: las cargas solo
  existen en los casos); en el caso de peso propio se lista el de cada barra, que es automático. Debajo, Materiales y Secciones con sus carpetas (interfaz/definir.py):
  clic los muestra en Propiedades, doble clic los edita ahí y el clic derecho da Nuevo, Editar,
  Copiar y Eliminar.
  Losas: cada losa de viguetas con sus paños y sus franjas (los sistemas de vigueta), y en cada franja
  sus casos de viva. Clic en una losa o un paño los selecciona (con la pestaña Comprobaciones); doble
  clic en una franja la abre (lista Sistema); clic derecho: Nuevo caso de viva… en una franja y
  Eliminar en un caso de viva propio, un paño o una losa.
- Pestaña Tablas: la matriz de rigidez global de cada elemento y los diagramas de interacción de
  las secciones de concreto (agrupados por sección: todas las columnas con la misma sección tienen
  el mismo diagrama).
Arriba quedan solo los grupos principales, cerrados: se abren con el "+". Empiezan SIEMPRE cerrados
(al iniciar, con Nuevo y con Abrir) y NADA se abre solo (decisión del usuario, noviembre de 2026):
al seleccionar algo (en 3D o aquí), el grupo que lo contiene se sombrea con el color de selección y
los grupos con algo conectado (las barras de un nodo, su apoyo, sus cargas...) con el de lo
relacionado, con la cuenta: "Elementos (4) · 2 conectados". Las filas también quedan marcadas: se
ven al abrir el grupo. Se recuerda qué abrió el usuario, para que siga abierto al actualizar.
Cada fila y cada grupo llevan un ícono según lo que son (nodo, barra, apoyo según su tipo, carga
según la suya, losa, paño, franja, caso de viva, material, sección, matriz, diagrama).
Cada ítem guarda qué representa, por ejemplo ("nodo", 3) o ("matriz", 2), y al elegirlo se emite
la señal `elegido` con eso. La ventana decide qué hacer.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QDockWidget, QTabWidget, QTreeWidgetItem

from configuracion import colores, formato
from interfaz import textos
from interfaz.iconos import icono
from interfaz.textos import donde, texto_carga
from modelo.analisis import cargas_de_peso_propio
from modelo.apoyos import describir, tipo_de
from modelo.estructura import CargaNodal
from interfaz.ventanas.definir import CLAVE, info_de, llenar_definiciones
from interfaz.paneles.comunes import ArbolLimpio, carpeta

TEXTO_BASE = Qt.UserRole + 3            # el texto del grupo sin la cuenta " · n conectados"
# Cómo se dice "conectado" en cada grupo (el género de su nombre)
CONECTADAS = {"cargas", "losas", "secciones", "matrices"}
ICONO_APOYO = {"fijo": "apoyo_fijo", "empotrado": "empotrado", "libre": "libre"}


def _icono_carga(c):
    if isinstance(c, CargaNodal):
        return icono("carga_nodo_simple")
    return icono(f"carga_{c.tipo}")


class Explorador(QDockWidget):
    elegido = Signal(object)                   # ("nodo", id), ("barra", id), ("material", id)...
    doble_clic = Signal(object)                # ("material", id) o ("seccion", id): editarlo
    menu_pedido = Signal(object, object)       # info de definir.info_de y posición en la pantalla
    menu_losa = Signal(object, object)         # ("losa"|"pano"|"franja"|"patron", dato) y posición
    franja_abierta = Signal(object)            # doble clic en una franja: (ID de losa, letra)
    vaciado = Signal()                         # clic en el vacío o sobre lo ya elegido: nada elegido

    def __init__(self, parent=None):
        super().__init__("Explorador del modelo", parent)
        self.setObjectName("explorador")
        self.pestanas = QTabWidget()
        self.pestanas.setDocumentMode(True)        # pestañas pegadas al contenido, sin marco extra
        self.arbol_modelo = ArbolLimpio()          # sin fila "fantasma"; otro clic deselecciona
        self.arbol_tablas = ArbolLimpio()
        for arbol, nombre in ((self.arbol_modelo, "Modelo"), (self.arbol_tablas, "Tablas")):
            arbol.vaciado.connect(self.vaciado.emit)
            arbol.itemClicked.connect(self._clic)
            arbol.itemDoubleClicked.connect(self._doble)
            self.pestanas.addTab(arbol, nombre)
        self.arbol_modelo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.arbol_modelo.customContextMenuRequested.connect(self._menu)
        self.setWidget(self.pestanas)
        self._items = {}                   # ("nodo", id), ("barra", id)... -> su fila principal
        self._filas = {}                   # lo mismo -> todas sus filas (un nodo está en Nodos y en Apoyos)
        self._enlazadas = []               # filas pintadas como relacionadas (para limpiarlas)
        self._grupos_marcados = []         # grupos y carpetas sombreados (para limpiarlos)
        self._abiertos = set()             # grupos que el usuario abrió (se respetan al actualizar)

    def reiniciar(self):
        """Otro modelo (Nuevo o Abrir): todos los grupos vuelven a empezar cerrados."""
        self._abiertos = set()
        for arbol in (self.arbol_modelo, self.arbol_tablas):
            arbol.collapseAll()

    def ajustar_iconos(self):
        for arbol in (self.arbol_modelo, self.arbol_tablas):
            arbol.ajustar_iconos()

    def _grupo(self, arbol, texto, clave, simbolo=None):
        item = carpeta(QTreeWidgetItem(arbol, [texto]))   # se abre y se cierra, no se elige
        item.setData(0, CLAVE, clave)
        item.setData(0, TEXTO_BASE, texto)
        item.setExpanded(clave in self._abiertos)
        if simbolo:
            item.setIcon(0, icono(simbolo))
        return item

    @staticmethod
    def _hoja(padre, texto, dato, simbolo=None):
        item = QTreeWidgetItem(padre, [texto])
        item.setData(0, Qt.UserRole, dato)
        if simbolo is not None:
            item.setIcon(0, icono(simbolo) if isinstance(simbolo, str) else simbolo)
        return item

    def _recordar_abiertos(self):
        """Qué carpetas están abiertas, también las de adentro (Materiales → Concreto...)."""
        for arbol in (self.arbol_modelo, self.arbol_tablas):
            pila = [arbol.topLevelItem(i) for i in range(arbol.topLevelItemCount())]
            while pila:
                it = pila.pop()
                clave = it.data(0, CLAVE)
                if clave is not None:
                    (self._abiertos.add if it.isExpanded() else self._abiertos.discard)(clave)
                pila += [it.child(i) for i in range(it.childCount())]

    def _registrar(self, clave, item, principal=False):
        self._filas.setdefault(clave, []).append(item)
        if principal:
            self._items[clave] = item

    def actualizar(self, modelo, caso=None, cargas_losas=None, resumenes=None):
        """Vuelve a armar los dos árboles (al cambiar el modelo o las unidades). caso: el caso activo,
        cuyas cargas se listan (None: ninguna, como en el modo Combinaciones). cargas_losas: [(ID de
        barra, CargaBarra)] con la carga de las losas en ese caso; resumenes: {ID de losa: resumen}."""
        self._recordar_abiertos()
        self.ajustar_iconos()
        self.arbol_modelo.clear()
        self.arbol_tablas.clear()
        self._items, self._filas, self._enlazadas, self._grupos_marcados = {}, {}, [], []

        nodos = self._grupo(self.arbol_modelo, f"Nodos ({len(modelo.nodos)})", "nodos", "nodo_simple")
        for nid, n in modelo.nodos.items():
            xyz = ", ".join(formato.cantidad(c, "longitud", con_unidad=False) for c in n.coords)
            self._registrar(("nodo", nid), self._hoja(nodos, f"{nid}. ({xyz})", ("nodo", nid), "nodo_simple"), True)
        elementos = self._grupo(self.arbol_modelo, f"Elementos ({len(modelo.elementos)})", "elementos", "barra_simple")
        for eid, el in modelo.elementos.items():
            self._registrar(("barra", eid), self._hoja(elementos, f"{eid}. nodos {el.ni} → {el.nj}", ("barra", eid),
                                                       "barra_simple"), True)
        con_apoyo = [(nid, n) for nid, n in modelo.nodos.items() if any(n.apoyo)]
        apoyos = self._grupo(self.arbol_modelo, f"Apoyos ({len(con_apoyo)})", "apoyos", "apoyo_fijo")
        for nid, n in con_apoyo:
            simbolo = ICONO_APOYO.get(tipo_de(n.apoyo), "empotrado")
            self._registrar(("apoyo", nid), self._hoja(apoyos, f"Nodo {nid}: {describir(n.apoyo)}", ("apoyo", nid),
                                                       simbolo), True)
        de_caso = [(cid, c) for cid, c in modelo.cargas.items() if c.caso == caso]
        propias = cargas_de_peso_propio(modelo, caso) if caso is not None else {}
        de_losas = (cargas_losas or []) if caso is not None else []
        total = len(de_caso) + len(propias) + len(de_losas)
        titulo = f"Cargas ({total})" if caso is not None else "Cargas (se ven en los casos)"
        cargas = self._grupo(self.arbol_modelo, titulo, "cargas", "cargas")
        for eid, c in propias.items():                 # el peso propio no se guarda: elegirlo elige su barra
            self._hoja(cargas, f"Barra {eid}: peso propio, {texto_carga(c)}", ("barra", eid), _icono_carga(c))
        for eid, c in de_losas:                        # la de las losas tampoco: elegirla elige su viga
            self._hoja(cargas, f"Barra {eid}: de la losa, {texto_carga(c)}", ("barra", eid), _icono_carga(c))
        for cid, c in de_caso:
            self._registrar(("carga", cid), self._hoja(cargas, f"{donde(c)}: {texto_carga(c)}", ("carga", cid),
                                                       _icono_carga(c)), True)
        self._losas(modelo, resumenes or {})
        abierto = lambda clave: clave in self._abiertos          # noqa: E731
        for tipo in ("material", "seccion"):                      # Materiales y Secciones, separados
            for clave, item in llenar_definiciones(self.arbol_modelo, modelo, abierto, tipo, con_raiz=True).items():
                self._registrar(clave, item, True)
        for i in range(self.arbol_modelo.topLevelItemCount()):    # el texto base de todos los grupos
            it = self.arbol_modelo.topLevelItem(i)
            if it.data(0, TEXTO_BASE) is None:
                it.setData(0, TEXTO_BASE, it.text(0))

        matrices = self._grupo(self.arbol_tablas, "Matrices de rigidez globales", "matrices", "matriz")
        for eid in modelo.elementos:
            self._hoja(matrices, f"Elemento {eid}", ("matriz", eid), "matriz")
        diagramas = self._grupo(self.arbol_tablas, "Diagramas de interacción", "diagramas", "interaccion")
        for sid, sec in modelo.secciones.items():
            if sec.concreto is not None and sec.concreto.forma != "T":     # la T (vigas) no tiene diagrama
                self._hoja(diagramas, f"{textos.nombre(sec, modelo)} ({sec.concreto.forma})", ("seccion", sid),
                           "interaccion")

    def _losas(self, modelo, resumenes):
        """El grupo Losas: cada losa con sus paños y sus franjas (y los casos de viva de cada una)."""
        losas = getattr(modelo, "losas", {})
        if not losas:
            return
        from modelo import losas as ml
        grupo = self._grupo(self.arbol_modelo, f"Losas ({len(losas)})", "losas", "losa_simple")
        for lid, losa in losas.items():
            fila = self._hoja(grupo, f"{losa.nombre} ({len(losa.panos)} paño{'s' if len(losa.panos) != 1 else ''})",
                              ("losa", lid), "losa_simple")
            fila.setData(0, CLAVE, f"losa {lid}")
            fila.setExpanded(f"losa {lid}" in self._abiertos)
            self._registrar(("losa", lid), fila, True)
            for pid, pano in losa.panos.items():
                texto = (f"Paño {pid}: vigas {', '.join(map(str, pano.apoyo_a))} y {', '.join(map(str, pano.apoyo_b))}"
                         f" · D {formato.cantidad(pano.muerta, 'carga_area', False)}, L "
                         f"{formato.cantidad(pano.viva, 'carga_area')}")
                self._registrar(("pano", pid), self._hoja(fila, texto, ("pano", pid), "pano"), True)
            r = resumenes.get(lid, {})
            for f in r.get("franjas", []):
                claros = ", ".join(formato.cantidad(c, "longitud", False) for c in f.claros)
                rama = self._hoja(fila, f"{f.nombre}: {claros} {formato.unidades.simbolo('longitud')} (doble clic: "
                                        "verla)", ("franja", (lid, f.letra)), "franja")
                rama.setData(0, CLAVE, f"franja {lid} {f.letra}")
                rama.setExpanded(f"franja {lid} {f.letra}" in self._abiertos)
                for i, (nombre, claros_p, auto) in enumerate(ml.patrones(losa, f)):
                    self._hoja(rama, f"{nombre}: viva en {ml.describir_claros(claros_p)}" + ("" if auto else " (tuyo)"),
                               ("patron", (lid, f.letra, i, auto)), "caso_viva")

    @staticmethod
    def _ancestros(fila):
        """Los grupos y carpetas que contienen la fila, del más cercano al de arriba."""
        lista, padre = [], fila.parent()
        while padre is not None:
            lista.append(padre)
            padre = padre.parent()
        return lista

    def marcar(self, item, mismos=(), enlazados=()):
        """Marca en el árbol Modelo lo seleccionado (sin volver a emitir `elegido`), SIN abrir nada:

        - item y `mismos` (por ejemplo las cargas de un nodo): sus filas, con el color de selección;
        - `enlazados` (por ejemplo las barras y el apoyo de un nodo): sus filas, con un fondo más claro;
        - los grupos y carpetas que las contienen se sombrean igual (el de lo elegido, con el color de
          selección; los otros, con el de lo relacionado) y cada grupo dice cuántas filas conectadas
          tiene: "Elementos (4) · 2 conectados". Así se ve la conexión con los grupos cerrados.
        A la vista queda la fila de lo elegido, o su grupo si está cerrado."""
        arbol = self.arbol_modelo
        arbol.blockSignals(True)
        arbol.limpiar()                            # sin selección y sin fila actual
        for fila in self._enlazadas:
            fila.setBackground(0, QBrush())
        for grupo in self._grupos_marcados:        # los grupos, a su color y su texto de siempre
            grupo.setBackground(0, QBrush())
            base = grupo.data(0, TEXTO_BASE)
            if base is not None:
                grupo.setText(0, base)
        self._enlazadas, self._grupos_marcados = [], []
        elegidas = list(self._filas.get(tuple(item), [])) if item else []
        mismas = [f for clave in (mismos if item else ()) for f in self._filas.get(tuple(clave), [])]
        for fila in elegidas + mismas:
            fila.setSelected(True)
        relacionadas = []
        for clave in enlazados:
            for fila in self._filas.get(tuple(clave), []):
                fila.setBackground(0, QBrush(QColor(colores.INTERFAZ_ENLAZADO)))
                self._enlazadas.append(fila)
                relacionadas.append(fila)
        oscuros = {id(p): p for f in elegidas for p in self._ancestros(f)}
        cuenta = {}                                # grupo de arriba -> [grupo, filas conectadas]
        for fila in mismas + relacionadas:
            ancestros = self._ancestros(fila)
            if ancestros:
                cuenta.setdefault(id(ancestros[-1]), [ancestros[-1], 0])[1] += 1
            for p in ancestros:
                if id(p) not in oscuros:
                    p.setBackground(0, QBrush(QColor(colores.INTERFAZ_ENLAZADO)))
                    self._grupos_marcados.append(p)
        for p in oscuros.values():
            p.setBackground(0, QBrush(QColor(colores.INTERFAZ_SELECCION)))
            self._grupos_marcados.append(p)
        for grupo, n in cuenta.values():
            base = grupo.data(0, TEXTO_BASE) or grupo.text(0)
            palabra = "conectada" if grupo.data(0, CLAVE) in CONECTADAS else "conectado"
            grupo.setText(0, f"{base} · {n} {palabra}{'s' if n != 1 else ''}")
            self._grupos_marcados.append(grupo)
        principal = self._items.get(tuple(item)) if item else None
        if principal is not None:
            visible = principal
            for p in self._ancestros(principal):   # con su grupo cerrado, a la vista queda el grupo
                if not p.isExpanded():
                    visible = p
            arbol.scrollToItem(visible)
        arbol.blockSignals(False)

    def _clic(self, item, _columna):
        dato = item.data(0, Qt.UserRole)
        if dato is not None:
            tipo = dato[0]
            if tipo == "franja":                   # una franja o un caso de viva eligen su losa
                dato = ("losa", dato[1][0])
            elif tipo == "patron":
                dato = ("losa", dato[1][0])
            self.elegido.emit(tuple(dato))

    def _doble(self, item, _columna):
        dato = item.data(0, Qt.UserRole)
        if dato is not None and dato[0] == "franja":
            self.franja_abierta.emit(tuple(dato[1]))
            return
        info = info_de(item)
        if info is not None and info[0] in ("material", "seccion"):
            self.doble_clic.emit(info)

    def _menu(self, posicion):
        item = self.arbol_modelo.itemAt(posicion)
        dato = item.data(0, Qt.UserRole) if item is not None else None
        global_ = self.arbol_modelo.viewport().mapToGlobal(posicion)
        if dato is not None and dato[0] in ("losa", "pano", "franja", "patron"):
            self.menu_losa.emit(tuple(dato), global_)
            return
        info = info_de(item)
        if info is not None:
            self.menu_pedido.emit(info, global_)
