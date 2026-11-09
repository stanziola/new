"""Diálogo de Configuración: cada cambio se aplica en el momento y se guarda.

- Abajo solo hay dos botones: Restablecer (vuelve todo a la personalización base) y Salir.
- Las pestañas se arman desde preferencias.PARAMETROS. La de Unidades es una tabla como la de
  Ftool: magnitud, unidad y decimales.
- Los valores con unidades se muestran en la unidad vigente. Si cambias una unidad, esos campos se
  vuelven a mostrar convertidos; el valor guardado (en unidades internas) no cambia.
- Los cambios se aplican con una pequeña espera (RETARDO_CONFIGURACION_MS): si escribes "125",
  no se redibuja con "1", "12" y "125", sino una sola vez.
"""
from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QFormLayout,
                               QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from configuracion import formato, preferencias, unidades
from configuracion import interfaz as ui
from interfaz.plano_trabajo import NOMBRE_EJE, PLANOS

GRUPOS = ["Unidades", "Rejilla", "Vista", "Interfaz", "Colores"]


class BotonColor(QPushButton):
    """Botón que muestra un color y abre el selector de colores al hacer clic."""
    cambiado = Signal(str)

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.poner_color(color)
        self.clicked.connect(self._elegir)

    def color(self):
        return self._color

    def poner_color(self, color):
        self._color = color
        muestra = QPixmap(28, 14)
        muestra.fill(QColor(color))
        self.setIcon(QIcon(muestra))
        self.setText(color.upper())

    def _elegir(self):
        nuevo = QColorDialog.getColor(QColor(self._color), self, "Elegir color")
        if nuevo.isValid() and nuevo.name() != self._color:
            self.poner_color(nuevo.name())
            self.cambiado.emit(nuevo.name())


class DialogoConfiguracion(QDialog):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.setWindowTitle("Configuración")
        self.resize(620, 560)
        self._controles = {}                       # Parametro -> control
        self._reloj = QTimer(self)
        self._reloj.setSingleShot(True)
        self._reloj.setInterval(ui.RETARDO_CONFIGURACION_MS)
        self._reloj.timeout.connect(self._aplicar)

        pestanas = QTabWidget()
        paginas = {}
        for grupo in GRUPOS:
            contenido = QWidget()
            paginas[grupo] = contenido
            desplazable = QScrollArea()
            desplazable.setWidgetResizable(True)
            desplazable.setWidget(contenido)
            pestanas.addTab(desplazable, grupo)
        por_clave = {p.clave: p for p in preferencias.PARAMETROS}

        # ---------- Unidades: tabla magnitud | unidad | decimales (como Ftool) ----------
        tabla = QGridLayout(paginas["Unidades"])
        for col, texto in enumerate(("Magnitud", "Unidad", "Decimales")):
            tabla.addWidget(QLabel(f"<b>{texto}</b>"), 0, col)
        for fila, magnitud in enumerate(unidades.UNIDADES, start=1):
            tabla.addWidget(QLabel(unidades.NOMBRES[magnitud]), fila, 0)
            for col, clave in ((1, f"unidades.{magnitud.upper()}"), (2, f"formato.DECIMALES_{magnitud.upper()}")):
                p = por_clave[clave]
                tabla.addWidget(self._registrar(p), fila, col)
        tabla.setRowStretch(len(unidades.UNIDADES) + 1, 1)

        # ---------- Rejilla: primero el plano de trabajo (de este modelo) ----------
        formularios = {g: QFormLayout(paginas[g]) for g in GRUPOS if g != "Unidades"}
        self._plano = QComboBox()
        self._plano.addItems(list(PLANOS))
        self._posicion = QDoubleSpinBox()
        self._posicion.setDecimals(4)
        self._posicion.setRange(-1e7, 1e7)
        self._etiqueta_posicion = QLabel()
        formularios["Rejilla"].addRow("Plano de trabajo (de este modelo)", self._plano)
        formularios["Rejilla"].addRow(self._etiqueta_posicion, self._posicion)
        self._plano.currentTextChanged.connect(self._cambio_plano)
        self._posicion.valueChanged.connect(self._cambio_plano)

        for p in preferencias.PARAMETROS:
            if p.grupo != "Unidades":
                formularios[p.grupo].addRow(p.etiqueta, self._registrar(p))

        # ---------- Abajo: Restablecer a la izquierda, Salir a la derecha ----------
        restablecer = QPushButton("Restablecer")
        restablecer.setToolTip("Vuelve todo a la personalización base")
        restablecer.clicked.connect(self._restablecer)
        salir = QPushButton("Salir")
        salir.clicked.connect(self.accept)
        abajo = QHBoxLayout()
        abajo.addWidget(restablecer)
        abajo.addStretch(1)
        abajo.addWidget(salir)

        diseno = QVBoxLayout(self)
        diseno.addWidget(pestanas)
        diseno.addLayout(abajo)
        self._mostrar_todo()

    # ---------- Controles ----------
    def _registrar(self, p):
        """Crea el control del parámetro y lo conecta: cada cambio se aplica."""
        if p.tipo == "entero":
            control = QSpinBox()
            control.setRange(int(p.minimo), int(min(p.maximo, 2**31 - 1)))
            control.valueChanged.connect(lambda *_, p=p: self._cambio(p))
        elif p.tipo == "real":
            control = QDoubleSpinBox()
            control.setDecimals(p.decimales)
            control.valueChanged.connect(lambda *_, p=p: self._cambio(p))
        elif p.tipo == "opcion":
            control = QComboBox()
            control.addItems(list(p.opciones))
            control.currentTextChanged.connect(lambda *_, p=p: self._cambio(p))
        elif p.tipo == "color":
            control = BotonColor(p.valor())
            control.cambiado.connect(lambda *_, p=p: self._cambio(p))
        else:
            raise ValueError(f"Tipo de parámetro sin control: {p.tipo}")
        self._controles[p] = control
        return control

    def _factor(self, p):
        return unidades.factor(p.magnitud) if p.magnitud else 1.0

    def _mostrar(self, p, control):
        """Pone en el control el valor vigente del parámetro, sin disparar un cambio."""
        control.blockSignals(True)
        valor = p.valor()
        if p.tipo == "entero":
            control.setValue(int(valor))
        elif p.tipo == "real":
            f = self._factor(p)
            control.setRange(p.minimo / f, p.maximo / f)
            control.setSuffix(f" {unidades.simbolo(p.magnitud)}" if p.magnitud else "")
            control.setValue(valor / f)
        elif p.tipo == "opcion":
            control.setCurrentText(valor)
        elif p.tipo == "color":
            control.poner_color(valor)
        control.blockSignals(False)

    def _mostrar_plano(self):
        for control in (self._plano, self._posicion):
            control.blockSignals(True)
        self._plano.setCurrentText(self.ventana.plano)
        self._posicion.setSuffix(f" {unidades.simbolo('longitud')}")
        self._posicion.setValue(self.ventana.posicion_plano / unidades.factor("longitud"))
        self._etiqueta_posicion.setText(f"Posición del plano ({NOMBRE_EJE[PLANOS[self.ventana.plano]]} =)")
        for control in (self._plano, self._posicion):
            control.blockSignals(False)

    def _mostrar_todo(self):
        for p, control in self._controles.items():
            self._mostrar(p, control)
        self._mostrar_plano()

    # ---------- Cambios ----------
    def _leer(self, p, control):
        if p.tipo in ("entero", "real"):
            valor = control.value()
            return valor * self._factor(p) if p.tipo == "real" else valor
        if p.tipo == "opcion":
            return control.currentText()
        return control.color()

    def _cambio(self, p):
        p.poner(self._leer(p, self._controles[p]))
        if p.modulo is unidades:                   # cambió una unidad: reconvertir lo que la usa
            for otro, control in self._controles.items():
                if otro.magnitud:
                    self._mostrar(otro, control)
            self._mostrar_plano()
        self._reloj.start()

    def _cambio_plano(self, *_):
        plano = self._plano.currentText()
        posicion = self._posicion.value() * unidades.factor("longitud")
        if abs(posicion - self.ventana.posicion_plano) < 0.5 * 10.0 ** -4 * unidades.factor("longitud"):
            posicion = self.ventana.posicion_plano          # no la tocó: se conserva exacta
        self.ventana.cambiar_plano(plano, posicion)
        self._mostrar_plano()

    def _restablecer(self):
        preferencias.restablecer()
        self._mostrar_todo()
        self._reloj.start()

    def _aplicar(self):
        try:
            preferencias.guardar()
        except OSError as e:
            QMessageBox.warning(self, "Configuración", f"No se pudieron guardar las preferencias:\n{e}")
        self.ventana.aplicar_configuracion()

    def done(self, resultado):
        """Al salir (con Salir, Esc o la X), aplica lo que estuviera esperando."""
        if self._reloj.isActive():
            self._reloj.stop()
            self._aplicar()
        super().done(resultado)
