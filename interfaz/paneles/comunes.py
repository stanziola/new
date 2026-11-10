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
- CampoNumero: un número con su unidad al lado (como en Ftool), sin flechas y de ancho fijo. Es una
  caja de texto: deja escribir libremente y revisa el número al terminar.
"""
import math

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMenu, QToolButton, QTreeWidget, QWidget

from configuracion import colores, formato, unidades
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
class _Caja(QLineEdit):
    """La caja de texto de un CampoNumero.

    - Al entrar (con un clic o con Tab) queda todo seleccionado: lo que se escriba reemplaza el
      valor. Después de escribir o de un primer clic, otro clic pone el cursor donde se quiera.
    - Enter confirma el número, lo deja seleccionado y se queda ahí: no pasa al botón por defecto de
      la ventana (si no, escribir un número y presionar Enter cerraría el diálogo)."""

    def __init__(self):
        super().__init__()
        self._primer_clic = False            # el primer clic después de entrar selecciona todo

    def focusInEvent(self, evento):
        super().focusInEvent(evento)
        self._primer_clic = True
        if evento.reason() != Qt.MouseFocusReason:
            self.selectAll()                 # con un clic se selecciona al soltar (el clic deselecciona)

    def mouseReleaseEvent(self, evento):
        super().mouseReleaseEvent(evento)
        if self._primer_clic:
            self._primer_clic = False
            if not self.hasSelectedText():   # si arrastró para elegir una parte, se respeta
                self.selectAll()

    def keyPressEvent(self, evento):
        super().keyPressEvent(evento)
        self._primer_clic = False            # ya está escribiendo: un clic pone el cursor
        if evento.key() in (Qt.Key_Return, Qt.Key_Enter):
            evento.accept()
            self.selectAll()


class CampoNumero(QWidget):
    """Un número con la unidad al lado, sin flechas y de ancho fijo (no se estira con el panel).

    Es una caja de texto, no un QSpinBox: un QSpinBox rechaza cada tecla que deja el texto fuera del
    rango o con decimales de más (con "3" y máximo 8 no deja escribir "32"; con "1.000" no deja
    agregar cifras), y sin flechas parece que el campo no deja escribir. Aquí se escribe libremente
    y el número se revisa después:
    - mientras se escribe, el texto va en gris si todavía no es un número dentro del rango; cuando lo
      es, va en negro, el campo toma ese valor y emite `cambiado` (para las vistas previas);
    - al terminar (Enter o salir del campo) emite `terminado`: se acepta coma o punto, un número
      fuera del rango se lleva al límite, y si no es un número vuelve el valor anterior.

    Valores:
    - con `magnitud` ("longitud", "seccion", "fuerza", "peso_unitario"...), se muestra en la unidad
      de pantalla y valor()/poner() trabajan en unidades INTERNAS;
    - recuerda el valor exacto que se le puso: si el usuario no lo cambia, valor() devuelve ese
      mismo número, sin el redondeo de los decimales de pantalla. Si las unidades cambian, valor()
      sigue siendo correcto y actualizar_unidades() lo vuelve a mostrar en las nuevas;
    - sin magnitud, `unidad` es un texto fijo ("°") o nada (Nx, Ny); entero=True solo acepta enteros;
    - `cifras`: ancho de la caja en cifras, si conviene otro que el normal (CIFRAS).
    """
    cambiado = Signal()
    terminado = Signal()

    CIFRAS = 11                              # ancho de la caja, en cifras

    def __init__(self, magnitud=None, minimo=-1e9, maximo=1e9, decimales=None, entero=False, unidad="",
                 cifras=None, parent=None):
        super().__init__(parent)
        self.magnitud, self.entero = magnitud, entero
        self._minimo, self._maximo, self._decimales = minimo, maximo, decimales
        self.caja = _Caja()
        self.caja.setFixedWidth(self.caja.fontMetrics().horizontalAdvance("0" * (cifras or self.CIFRAS)) + 14)
        self.unidad = QLabel(unidad)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(6)
        fila.addWidget(self.caja)
        fila.addWidget(self.unidad)
        fila.addStretch(1)
        self.setFocusProxy(self.caja)
        self._factor = 1.0
        self._valor = int(min(max(0, minimo), maximo)) if entero else float(min(max(0.0, minimo), maximo))
        self._valor_escrito = self._valor    # el valor que tenía cuando el programa escribió el texto
        self._editado = False                # el usuario cambió el texto desde entonces
        self.caja.textEdited.connect(self._al_escribir)
        self.caja.editingFinished.connect(self._al_terminar)
        self._preparar()
        self._escribir()

    # ---------- Unidades y texto ----------
    def _preparar(self):
        """Factor y símbolo de la unidad de pantalla vigente."""
        self._factor = unidades.factor(self.magnitud) if self.magnitud else 1.0
        if self.magnitud:
            self.unidad.setText(unidades.simbolo(self.magnitud))

    def _cifras(self):
        if self._decimales is not None:
            return self._decimales
        return max(2, formato.decimales(self.magnitud)) if self.magnitud else 2

    def _escribir(self):
        """Pone en la caja el valor vigente, con su formato."""
        if self.entero:
            texto = str(int(self._valor))
        else:
            texto = formato.numero(self._valor / self._factor, self._cifras())
        self.caja.setText(texto)             # setText no emite textEdited
        self.caja.setCursorPosition(0)       # si no cabe, se ve el principio del número
        self._valor_escrito = self._valor
        self._editado = False
        self._pintar(True)

    def _pintar(self, valido):
        """Negro si lo escrito ya es un valor válido; gris mientras no lo es."""
        paleta = self.caja.palette()
        color = QColor(colores.INTERFAZ_TEXTO if valido else colores.INTERFAZ_DESHABILITADO)
        for grupo in (QPalette.Active, QPalette.Inactive):
            paleta.setColor(grupo, QPalette.Text, color)
        self.caja.setPalette(paleta)

    def _leer(self, texto):
        """El número escrito, en unidades internas (int si es entero); None si no es un número."""
        try:
            numero = float(texto.strip().replace(",", "."))
        except ValueError:
            return None
        if not math.isfinite(numero):
            return None
        if self.entero:
            return int(round(numero)) if abs(numero - round(numero)) < 1e-9 else None
        return numero * self._factor

    def _en_rango(self, valor):
        holgura = 0 if self.entero else 1e-9 * max(1.0, abs(valor))
        return self._minimo - holgura <= valor <= self._maximo + holgura

    # ---------- Lo que hace el usuario ----------
    def _al_escribir(self, texto):
        self._editado = True
        valor = self._leer(texto)
        valido = valor is not None and self._en_rango(valor)
        self._pintar(valido)
        if valido and valor != self._valor:
            self._valor = valor
            self.cambiado.emit()

    def _al_terminar(self):
        if self._editado:
            valor = self._leer(self.caja.text())
            if valor is None:
                valor = self._valor_escrito  # no es un número: vuelve el valor que había antes de escribir
            else:
                valor = min(max(valor, self._minimo), self._maximo)      # al rango
                if self.entero:
                    valor = int(valor)
            cambio = valor != self._valor
            self._valor = valor
            self._escribir()                 # con su formato
            if cambio:
                self.cambiado.emit()
        self.terminado.emit()

    # ---------- Para el programa ----------
    def valor(self):
        """Valor en unidades internas (int si es entero)."""
        return self._valor

    def poner(self, valor):
        """Pone un valor en unidades internas, sin emitir `cambiado`."""
        self._valor = int(valor) if self.entero else float(valor)
        self._escribir()

    def actualizar_unidades(self):
        """Vuelve a mostrar el mismo valor en las unidades (y con los decimales) vigentes. Si el
        usuario está a mitad de escribir en este campo, no se le cambia el texto."""
        self._preparar()
        if not (self._editado and self.caja.hasFocus()):
            self._escribir()
