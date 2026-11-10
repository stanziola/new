"""Explorador del modelo (izquierda), como el de ETABS o Civil 3D.

- Pestaña Modelo: nodos, elementos, apoyos y cargas. Elegir uno lo selecciona en 3D y lo muestra
  en Propiedades. Un apoyo es un objeto aparte ("apoyo", ID del nodo): se puede elegir y borrar
  solo. Las cargas son las del caso activo (viendo una combinación no se listan: las cargas solo
  existen en los casos); en el caso de peso propio se lista el de cada barra, que es automático. Debajo, Materiales y Secciones con sus carpetas (interfaz/definir.py):
  clic los muestra en Propiedades, doble clic los edita ahí y el clic derecho da Nuevo, Editar,
  Copiar y Eliminar.
- Pestaña Tablas: la matriz de rigidez global de cada elemento y los diagramas de interacción de
  las secciones de concreto (agrupados por sección: todas las columnas con la misma sección tienen
  el mismo diagrama).
Arriba quedan solo los grupos principales, cerrados: se abren con el "+". Se recuerda cuáles
abrió el usuario, para que sigan abiertos al actualizar.
Cada ítem guarda qué representa, por ejemplo ("nodo", 3) o ("matriz", 2), y al elegirlo se emite
la señal `elegido` con eso. La ventana decide qué hacer.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QDockWidget, QTabWidget, QTreeWidgetItem

from configuracion import colores, formato
from interfaz import textos
from interfaz.textos import donde, texto_carga
from modelo.analisis import cargas_de_peso_propio
from modelo.apoyos import describir
from interfaz.ventanas.definir import CLAVE, info_de, llenar_definiciones
from interfaz.paneles.comunes import ArbolLimpio, carpeta


class Explorador(QDockWidget):
    elegido = Signal(object)                   # ("nodo", id), ("barra", id), ("material", id)...
    doble_clic = Signal(object)                # ("material", id) o ("seccion", id): editarlo
    menu_pedido = Signal(object, object)       # info de definir.info_de y posición en la pantalla
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
        self._abiertos = set()             # grupos que el usuario abrió (se respetan al actualizar)

    def _grupo(self, arbol, texto, clave):
        item = carpeta(QTreeWidgetItem(arbol, [texto]))   # se abre y se cierra, no se elige
        item.setData(0, CLAVE, clave)
        item.setExpanded(clave in self._abiertos)
        return item

    @staticmethod
    def _hoja(padre, texto, dato):
        item = QTreeWidgetItem(padre, [texto])
        item.setData(0, Qt.UserRole, dato)
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

    def actualizar(self, modelo, caso=None):
        """Vuelve a armar los dos árboles (al cambiar el modelo o las unidades). caso: el caso activo,
        cuyas cargas se listan (None: ninguna, como en el modo Combinaciones)."""
        self._recordar_abiertos()
        self.arbol_modelo.clear()
        self.arbol_tablas.clear()
        self._items, self._filas, self._enlazadas = {}, {}, []

        nodos = self._grupo(self.arbol_modelo, f"Nodos ({len(modelo.nodos)})", "nodos")
        for nid, n in modelo.nodos.items():
            xyz = ", ".join(formato.cantidad(c, "longitud", con_unidad=False) for c in n.coords)
            self._registrar(("nodo", nid), self._hoja(nodos, f"{nid}. ({xyz})", ("nodo", nid)), True)
        elementos = self._grupo(self.arbol_modelo, f"Elementos ({len(modelo.elementos)})", "elementos")
        for eid, el in modelo.elementos.items():
            self._registrar(("barra", eid), self._hoja(elementos, f"{eid}. nodos {el.ni} → {el.nj}", ("barra", eid)), True)
        con_apoyo = [(nid, n) for nid, n in modelo.nodos.items() if any(n.apoyo)]
        apoyos = self._grupo(self.arbol_modelo, f"Apoyos ({len(con_apoyo)})", "apoyos")
        for nid, n in con_apoyo:
            self._registrar(("apoyo", nid), self._hoja(apoyos, f"Nodo {nid}: {describir(n.apoyo)}", ("apoyo", nid)),
                            True)
        de_caso = [(cid, c) for cid, c in modelo.cargas.items() if c.caso == caso]
        propias = cargas_de_peso_propio(modelo, caso) if caso is not None else {}
        titulo = f"Cargas ({len(de_caso) + len(propias)})" if caso is not None else "Cargas (se ven en los casos)"
        cargas = self._grupo(self.arbol_modelo, titulo, "cargas")
        for eid, c in propias.items():                 # el peso propio no se guarda: elegirlo elige su barra
            self._hoja(cargas, f"Barra {eid}: peso propio, {texto_carga(c)}", ("barra", eid))
        for cid, c in de_caso:
            self._registrar(("carga", cid), self._hoja(cargas, f"{donde(c)}: {texto_carga(c)}", ("carga", cid)), True)
        abierto = lambda clave: clave in self._abiertos          # noqa: E731
        for tipo in ("material", "seccion"):                      # Materiales y Secciones, separados
            for clave, item in llenar_definiciones(self.arbol_modelo, modelo, abierto, tipo, con_raiz=True).items():
                self._registrar(clave, item, True)

        matrices = self._grupo(self.arbol_tablas, "Matrices de rigidez globales", "matrices")
        for eid in modelo.elementos:
            self._hoja(matrices, f"Elemento {eid}", ("matriz", eid))
        diagramas = self._grupo(self.arbol_tablas, "Diagramas de interacción", "diagramas")
        for sid, sec in modelo.secciones.items():
            if sec.concreto is not None:
                self._hoja(diagramas, f"{textos.nombre(sec, modelo)} ({sec.concreto.forma})", ("seccion", sid))

    @staticmethod
    def _abrir_grupos(fila):
        padre = fila.parent()
        while padre is not None:
            padre.setExpanded(True)
            padre = padre.parent()

    def marcar(self, item, mismos=(), enlazados=()):
        """Marca en el árbol Modelo lo seleccionado (sin volver a emitir `elegido`).

        - item y `mismos` (por ejemplo las cargas y el apoyo de un nodo): con el color de selección;
        - `enlazados` (por ejemplo las barras de un nodo): con un fondo más claro.
        Se abren sus grupos y lo principal queda a la vista."""
        arbol = self.arbol_modelo
        arbol.blockSignals(True)
        arbol.limpiar()                            # sin selección y sin fila actual
        for fila in self._enlazadas:
            fila.setBackground(0, QBrush())
        self._enlazadas = []
        claves = [tuple(item)] + [tuple(m) for m in mismos] if item else []
        for clave in claves:
            for fila in self._filas.get(clave, []):
                self._abrir_grupos(fila)
                fila.setSelected(True)
        for clave in enlazados:
            for fila in self._filas.get(tuple(clave), []):
                self._abrir_grupos(fila)
                fila.setBackground(0, QBrush(QColor(colores.INTERFAZ_ENLAZADO)))
                self._enlazadas.append(fila)
        principal = self._items.get(tuple(item)) if item else None
        if principal is not None:
            arbol.scrollToItem(principal)
        arbol.blockSignals(False)

    def _clic(self, item, _columna):
        dato = item.data(0, Qt.UserRole)
        if dato is not None:
            self.elegido.emit(tuple(dato))

    def _doble(self, item, _columna):
        info = info_de(item)
        if info is not None and info[0] in ("material", "seccion"):
            self.doble_clic.emit(info)

    def _menu(self, posicion):
        info = info_de(self.arbol_modelo.itemAt(posicion))
        if info is not None:
            self.menu_pedido.emit(info, self.arbol_modelo.viewport().mapToGlobal(posicion))
