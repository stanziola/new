"""Explorador del modelo (izquierda), como el de ETABS o Civil 3D.

- Pestaña Modelo: nodos, elementos y apoyos. Elegir uno lo selecciona en 3D y lo muestra en
  Propiedades.
- Pestaña Tablas: la matriz de rigidez global de cada elemento y los diagramas de interacción de
  las secciones de concreto (agrupados por sección: todas las columnas con la misma sección tienen
  el mismo diagrama).
Arriba quedan solo los grupos principales, cerrados: se abren con el "+". Se recuerda cuáles
abrió el usuario, para que sigan abiertos al actualizar.
Cada ítem guarda qué representa, por ejemplo ("nodo", 3) o ("matriz", 2), y al elegirlo se emite
la señal `elegido` con eso. La ventana decide qué hacer.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDockWidget, QTabWidget, QTreeWidget, QTreeWidgetItem

from configuracion import formato
from interfaz.apoyos import describir


class Explorador(QDockWidget):
    elegido = Signal(object)

    def __init__(self, parent=None):
        super().__init__("Explorador del modelo", parent)
        self.setObjectName("explorador")
        self.pestanas = QTabWidget()
        self.pestanas.setDocumentMode(True)        # pestañas pegadas al contenido, sin marco extra
        self.arbol_modelo = QTreeWidget()
        self.arbol_tablas = QTreeWidget()
        for arbol, nombre in ((self.arbol_modelo, "Modelo"), (self.arbol_tablas, "Tablas")):
            arbol.setHeaderHidden(True)
            arbol.setIndentation(14)
            arbol.setUniformRowHeights(True)
            arbol.itemClicked.connect(self._clic)
            self.pestanas.addTab(arbol, nombre)
        self.setWidget(self.pestanas)
        self._items = {}                   # ("nodo", id) o ("barra", id) -> ítem del árbol Modelo
        self._abiertos = set()             # grupos que el usuario abrió (se respetan al actualizar)

    def _grupo(self, arbol, texto, clave):
        item = QTreeWidgetItem(arbol, [texto])
        item.setData(0, Qt.UserRole + 1, clave)
        item.setExpanded(clave in self._abiertos)
        return item

    @staticmethod
    def _hoja(padre, texto, dato):
        item = QTreeWidgetItem(padre, [texto])
        item.setData(0, Qt.UserRole, dato)
        return item

    def _recordar_abiertos(self):
        for arbol in (self.arbol_modelo, self.arbol_tablas):
            for i in range(arbol.topLevelItemCount()):
                it = arbol.topLevelItem(i)
                (self._abiertos.add if it.isExpanded() else self._abiertos.discard)(it.data(0, Qt.UserRole + 1))

    def actualizar(self, modelo):
        """Vuelve a armar los dos árboles (al cambiar el modelo o las unidades)."""
        self._recordar_abiertos()
        self.arbol_modelo.clear()
        self.arbol_tablas.clear()
        self._items = {}

        nodos = self._grupo(self.arbol_modelo, f"Nodos ({len(modelo.nodos)})", "nodos")
        for nid, n in modelo.nodos.items():
            xyz = ", ".join(formato.cantidad(c, "longitud", con_unidad=False) for c in n.coords)
            self._items[("nodo", nid)] = self._hoja(nodos, f"{nid}. ({xyz})", ("nodo", nid))
        elementos = self._grupo(self.arbol_modelo, f"Elementos ({len(modelo.elementos)})", "elementos")
        for eid, el in modelo.elementos.items():
            self._items[("barra", eid)] = self._hoja(elementos, f"{eid}. nodos {el.ni} → {el.nj}", ("barra", eid))
        con_apoyo = [(nid, n) for nid, n in modelo.nodos.items() if any(n.apoyo)]
        apoyos = self._grupo(self.arbol_modelo, f"Apoyos ({len(con_apoyo)})", "apoyos")
        for nid, n in con_apoyo:
            self._hoja(apoyos, f"Nodo {nid}: {describir(n.apoyo)}", ("nodo", nid))

        matrices = self._grupo(self.arbol_tablas, "Matrices de rigidez globales", "matrices")
        for eid in modelo.elementos:
            self._hoja(matrices, f"Elemento {eid}", ("matriz", eid))
        diagramas = self._grupo(self.arbol_tablas, "Diagramas de interacción", "diagramas")
        for sid, sec in modelo.secciones.items():
            if sec.concreto is not None:
                self._hoja(diagramas, f"{sec.nombre} ({sec.concreto.forma})", ("seccion", sid))

    def marcar(self, item):
        """Marca en el árbol Modelo lo seleccionado en 3D (sin volver a emitir `elegido`).

        Si su grupo está cerrado, queda marcado igual pero no se abre: el usuario decide qué ver.
        """
        self.arbol_modelo.blockSignals(True)
        self.arbol_modelo.clearSelection()
        nodo_arbol = self._items.get(tuple(item)) if item else None
        if nodo_arbol is not None:
            nodo_arbol.setSelected(True)
            if nodo_arbol.parent() is None or nodo_arbol.parent().isExpanded():
                self.arbol_modelo.scrollToItem(nodo_arbol)
        self.arbol_modelo.blockSignals(False)

    def _clic(self, item, _columna):
        dato = item.data(0, Qt.UserRole)
        if dato is not None:
            self.elegido.emit(tuple(dato))
