"""Explorador del modelo (izquierda), como el de ETABS o Civil 3D.

- Pestaña Modelo: nodos, elementos y apoyos. Elegir uno lo selecciona en 3D y lo muestra en
  Propiedades.
- Pestaña Tablas: la matriz de rigidez global de cada elemento y los diagramas de interacción de
  las secciones de concreto (agrupados por sección: todas las columnas con la misma sección tienen
  el mismo diagrama).
Cada ítem guarda qué representa, por ejemplo ("nodo", 3) o ("matriz", 2), y al elegirlo se emite
la señal `elegido` con eso. La ventana decide qué hacer.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDockWidget, QTabWidget, QTreeWidget, QTreeWidgetItem

from configuracion import formato
from interfaz.propiedades import describir_apoyo


class Explorador(QDockWidget):
    elegido = Signal(object)

    def __init__(self, parent=None):
        super().__init__("Explorador del modelo", parent)
        self.setObjectName("explorador")
        self.pestanas = QTabWidget()
        self.arbol_modelo = QTreeWidget()
        self.arbol_tablas = QTreeWidget()
        for arbol, nombre in ((self.arbol_modelo, "Modelo"), (self.arbol_tablas, "Tablas")):
            arbol.setHeaderHidden(True)
            arbol.itemClicked.connect(self._clic)
            self.pestanas.addTab(arbol, nombre)
        self.setWidget(self.pestanas)
        self._items = {}                   # ("nodo", id) o ("barra", id) -> ítem del árbol Modelo
        self._cerrados = set()             # grupos que el usuario cerró (se respetan al actualizar)

    def _grupo(self, padre, texto, clave):
        item = QTreeWidgetItem(padre, [texto])
        item.setData(0, Qt.UserRole + 1, clave)
        item.setExpanded(clave not in self._cerrados)
        return item

    @staticmethod
    def _hoja(padre, texto, dato):
        item = QTreeWidgetItem(padre, [texto])
        item.setData(0, Qt.UserRole, dato)
        return item

    def _recordar_cerrados(self):
        for arbol in (self.arbol_modelo, self.arbol_tablas):
            pila = [arbol.topLevelItem(i) for i in range(arbol.topLevelItemCount())]
            while pila:
                it = pila.pop()
                clave = it.data(0, Qt.UserRole + 1)
                if clave is not None:
                    (self._cerrados.discard if it.isExpanded() else self._cerrados.add)(clave)
                pila += [it.child(i) for i in range(it.childCount())]

    def actualizar(self, modelo):
        """Vuelve a armar los dos árboles (al cambiar el modelo o las unidades)."""
        self._recordar_cerrados()
        self.arbol_modelo.clear()
        self.arbol_tablas.clear()
        self._items = {}

        raiz = self._grupo(self.arbol_modelo, "Modelo", "modelo")
        nodos = self._grupo(raiz, f"Nodos ({len(modelo.nodos)})", "nodos")
        for nid, n in modelo.nodos.items():
            xyz = ", ".join(formato.cantidad(c, "longitud", con_unidad=False) for c in n.coords)
            self._items[("nodo", nid)] = self._hoja(nodos, f"{nid}  ·  ({xyz})", ("nodo", nid))
        elementos = self._grupo(raiz, f"Elementos ({len(modelo.elementos)})", "elementos")
        for eid, el in modelo.elementos.items():
            self._items[("barra", eid)] = self._hoja(elementos, f"{eid}  ·  nodos {el.ni} → {el.nj}", ("barra", eid))
        con_apoyo = [(nid, n) for nid, n in modelo.nodos.items() if any(n.apoyo)]
        apoyos = self._grupo(raiz, f"Apoyos ({len(con_apoyo)})", "apoyos")
        for nid, n in con_apoyo:
            self._hoja(apoyos, f"Nodo {nid}  ·  {describir_apoyo(n.apoyo)}", ("nodo", nid))

        matrices = self._grupo(self.arbol_tablas, "Matrices de rigidez globales", "matrices")
        for eid in modelo.elementos:
            self._hoja(matrices, f"Elemento {eid}", ("matriz", eid))
        diagramas = self._grupo(self.arbol_tablas, "Diagramas de interacción", "diagramas")
        for sid, sec in modelo.secciones.items():
            if sec.concreto is not None:
                self._hoja(diagramas, f"{sec.nombre}  ·  {sec.concreto.forma}", ("seccion", sid))

    def marcar(self, item):
        """Marca en el árbol Modelo lo seleccionado en 3D (sin volver a emitir `elegido`)."""
        self.arbol_modelo.blockSignals(True)
        self.arbol_modelo.clearSelection()
        nodo_arbol = self._items.get(tuple(item)) if item else None
        if nodo_arbol is not None:
            nodo_arbol.setSelected(True)
            self.arbol_modelo.scrollToItem(nodo_arbol)
        self.arbol_modelo.blockSignals(False)

    def _clic(self, item, _columna):
        dato = item.data(0, Qt.UserRole)
        if dato is not None:
            self.elegido.emit(tuple(dato))
