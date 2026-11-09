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
- CampoNumero: un número con su unidad al lado (como en Ftool), sin flechas y de ancho fijo.
"""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (QAbstractSpinBox, QDoubleSpinBox, QHBoxLayout, QLabel, QMenu, QSpinBox,
                               QToolButton, QTreeWidget, QWidget)

from configuracion import formato, unidades
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


# ---------------------------------------------------------------- Campos numéricos
class _SinRueda:
    """Mezcla para las cajas: sin flechas, y la rueda del mouse no cambia el número (mueve el
    panel). Así no se cambia un valor sin querer al desplazarse por Propiedades."""

    def _preparar_caja(self):
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, evento):
        evento.ignore()


class _CajaReal(_SinRueda, QDoubleSpinBox):
    def __init__(self):
        super().__init__()
        self._preparar_caja()


class _CajaEntera(_SinRueda, QSpinBox):
    def __init__(self):
        super().__init__()
        self._preparar_caja()


class CampoNumero(QWidget):
    """Un número con la unidad al lado, sin flechas y de ancho fijo (no se estira con el panel).

    - Con `magnitud` ("longitud", "seccion", "fuerza", "peso_unitario"...), se muestra en la unidad
      de pantalla y valor()/poner() trabajan en unidades INTERNAS.
    - Recuerda el valor exacto que se le puso: si el usuario no lo cambia, valor() devuelve ese
      mismo número, sin el redondeo de los decimales de pantalla. Si las unidades cambian,
      valor() sigue siendo correcto y actualizar_unidades() lo vuelve a mostrar en las nuevas.
    - Sin magnitud, `unidad` es un texto fijo ("°") o nada (Nx, Ny); entero=True solo acepta
      enteros.
    Señales: `cambiado` con cada cambio (al escribir) y `terminado` al presionar Enter o salir.
    """
    cambiado = Signal()
    terminado = Signal()

    CIFRAS = 11                              # ancho de la caja, en cifras

    def __init__(self, magnitud=None, minimo=-1e9, maximo=1e9, decimales=None, entero=False, unidad="",
                 parent=None):
        super().__init__(parent)
        self.magnitud, self.entero = magnitud, entero
        self._minimo, self._maximo, self._decimales = minimo, maximo, decimales
        self.caja = _CajaEntera() if entero else _CajaReal()
        self.caja.setFixedWidth(self.caja.fontMetrics().horizontalAdvance("0" * self.CIFRAS) + 14)
        self.unidad = QLabel(unidad)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(6)
        fila.addWidget(self.caja)
        fila.addWidget(self.unidad)
        fila.addStretch(1)
        self._factor = 1.0
        self._exacto = None                  # el valor interno puesto con poner(), si no se tocó
        self.caja.valueChanged.connect(self._al_cambiar)
        self.caja.editingFinished.connect(self.terminado.emit)
        self._preparar()

    def _preparar(self):
        """Unidad, decimales y rango con las unidades vigentes."""
        self._factor = unidades.factor(self.magnitud) if self.magnitud else 1.0
        if self.magnitud:
            self.unidad.setText(unidades.simbolo(self.magnitud))
        self.caja.blockSignals(True)
        if self.entero:
            self.caja.setRange(int(self._minimo), int(min(self._maximo, 2**31 - 1)))
        else:
            if self._decimales is not None:
                decimales = self._decimales
            else:
                decimales = max(2, formato.decimales(self.magnitud)) if self.magnitud else 2
            self.caja.setDecimals(decimales)
            self.caja.setRange(self._minimo / self._factor, self._maximo / self._factor)
        self.caja.blockSignals(False)

    def _al_cambiar(self, *_):
        self._exacto = None                  # lo cambió el usuario: vale lo que se ve
        self.cambiado.emit()

    def valor(self):
        """Valor en unidades internas (int si es entero)."""
        if self._exacto is not None:
            return self._exacto
        return self.caja.value() if self.entero else self.caja.value() * self._factor

    def poner(self, valor):
        """Pone un valor en unidades internas, sin emitir `cambiado`."""
        self._exacto = int(valor) if self.entero else float(valor)
        self.caja.blockSignals(True)
        self.caja.setValue(self._exacto if self.entero else self._exacto / self._factor)
        self.caja.blockSignals(False)

    def actualizar_unidades(self):
        """Vuelve a mostrar el mismo valor en las unidades de pantalla vigentes."""
        valor = self.valor()
        self._preparar()
        self.poner(valor)
