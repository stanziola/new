"""Piezas de los paneles: la barra de título propia, el menú que no se cierra y los árboles.

- TituloPanel: reemplaza la barra de título de un QDockWidget. El estilo Fusion dibuja la x de
  cerrar dentro de un recuadro; aquí es solo una x (nuestro ícono) que se sombrea al pasar el
  mouse. Los clics fuera del botón no se atienden aquí y pasan al panel, así que se sigue
  arrastrando por el título para moverlo de lado.
- MenuPersistente: un QMenu que, al marcar o desmarcar una opción activable (como los paneles del
  menú Ver), la cambia sin cerrarse. Así se pueden prender y apagar varias seguidas.
- ArbolLimpio: el árbol del explorador y de Definir. Qt, al darle el foco a un árbol, deja la
  primera fila como "actual" y la dibuja marcada aunque nadie la haya elegido; este árbol no toma
  el foco, así que eso no pasa. Además, un clic en el vacío o sobre la fila ya elegida la
  deselecciona (señal `vaciado`), y las carpetas no se eligen: un clic las abre o las cierra.
"""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QToolButton, QTreeWidget, QWidget

from interfaz.iconos import icono

TAMANO_X = 12                          # la x de cerrar, en píxeles


class TituloPanel(QWidget):
    def __init__(self, panel):
        super().__init__(panel)
        self.setObjectName("titulo_panel")
        self.setAttribute(Qt.WA_StyledBackground, True)     # para que la hoja de estilo le dé fondo
        fila = QHBoxLayout(self)
        fila.setContentsMargins(8, 3, 3, 3)
        self.texto = QLabel(panel.windowTitle())
        self.cerrar = QToolButton()
        self.cerrar.setObjectName("cerrar_panel")
        self.cerrar.setIcon(icono("cerrar"))
        self.cerrar.setIconSize(QSize(TAMANO_X, TAMANO_X))
        self.cerrar.setAutoRaise(True)
        self.cerrar.setToolTip("Cerrar (se vuelve a abrir desde Ver)")
        self.cerrar.clicked.connect(panel.close)
        fila.addWidget(self.texto, 1)
        fila.addWidget(self.cerrar)
        panel.windowTitleChanged.connect(self.texto.setText)


def poner_titulo(panel):
    """Le pone a un QDockWidget la barra de título propia."""
    panel.setTitleBarWidget(TituloPanel(panel))


class MenuPersistente(QMenu):
    """Menú que no se cierra al cambiar una opción activable."""

    def _cambiar(self):
        accion = self.activeAction()
        if accion is not None and accion.isEnabled() and accion.isCheckable():
            accion.trigger()
            return True
        return False

    def mouseReleaseEvent(self, evento):
        if self._cambiar():
            evento.accept()
            return
        super().mouseReleaseEvent(evento)

    def keyPressEvent(self, evento):
        if evento.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space) and self._cambiar():
            evento.accept()
            return
        super().keyPressEvent(evento)


def carpeta(item):
    """Convierte un ítem en carpeta: se abre y se cierra, pero no se elige."""
    item.setFlags(Qt.ItemIsEnabled)
    return item


class ArbolLimpio(QTreeWidget):
    """Árbol sin fila "fantasma", que deselecciona con un clic en el vacío o en lo ya elegido."""
    vaciado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)          # sin foco: Qt no marca una fila por su cuenta
        self.setHeaderHidden(True)
        self.setIndentation(14)
        self.setUniformRowHeights(True)
        self.setExpandsOnDoubleClick(False)      # las carpetas se abren con un clic

        self._atendido = False                   # este clic lo resolvió el árbol, no Qt

    def limpiar(self):
        """Nada elegido y ninguna fila actual."""
        self.clearSelection()
        self.selectionModel().clearCurrentIndex()

    def focusInEvent(self, evento):
        """Si igual recibe el foco (por código), Qt no deja la primera fila marcada."""
        super().focusInEvent(evento)
        if not self.selectedItems():
            self.selectionModel().clearCurrentIndex()

    def _resuelto(self):
        self._atendido = True

    def mousePressEvent(self, evento):
        self._atendido = False
        if evento.button() != Qt.LeftButton:
            super().mousePressEvent(evento)
            return
        posicion = evento.position().toPoint()
        item = self.itemAt(posicion)
        if item is None:                                   # clic en el vacío
            self.limpiar()
            self.vaciado.emit()
            return self._resuelto()
        if posicion.x() < self.visualItemRect(item).left():
            super().mousePressEvent(evento)                # el "+" o "−": Qt abre o cierra
            return
        if not item.flags() & Qt.ItemIsSelectable:         # carpeta: un clic la abre o la cierra
            item.setExpanded(not item.isExpanded())
            return self._resuelto()
        if item.isSelected():                              # otro clic sobre lo elegido: se deselecciona
            self.limpiar()
            self.vaciado.emit()
            return self._resuelto()
        super().mousePressEvent(evento)

    def mouseReleaseEvent(self, evento):
        """Si el clic ya lo resolvió el árbol, Qt no debe "repetirlo" al soltar el botón: recordaría
        la fila del clic anterior y la volvería a elegir."""
        if self._atendido:
            self._atendido = False
            evento.accept()
            return
        super().mouseReleaseEvent(evento)
