"""Diálogo de Configuración: se arma solo a partir de preferencias.PARAMETROS.

Cada parámetro dice su tipo (entero, real, color...) y su pestaña, y según el tipo se crea el
control. Así, para agregar una opción nueva a Configuración basta una línea en PARAMETROS.

Unidades: los valores con magnitud (por ejemplo, el paso de la rejilla) se muestran en las unidades
de pantalla vigentes al abrir el diálogo y se guardan en internas. Si el usuario no toca un valor,
se conserva el original exacto: así, abrir y aceptar en ft no deja restos de redondeo en los datos.
"""
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFormLayout, QKeySequenceEdit, QLabel, QMessageBox,
                               QPushButton, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from configuracion import preferencias, unidades
from interfaz.plano_trabajo import NOMBRE_EJE, PLANOS

GRUPOS = ["Unidades", "Formato", "Rejilla", "Vista", "Interfaz", "Colores"]


class BotonColor(QPushButton):
    """Botón que muestra un color y abre el selector de colores al hacer clic."""

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
        if nuevo.isValid():
            self.poner_color(nuevo.name())


class DialogoConfiguracion(QDialog):
    def __init__(self, ventana, plano, posicion):
        super().__init__(ventana)
        self.setWindowTitle("Configuración")
        self.resize(560, 520)
        # Factores de las unidades que se ven al abrir (aunque el usuario cambie las unidades aquí)
        self._factores = {m: unidades.factor(m) for m in unidades.MAGNITUDES}
        self._controles = {}        # Parametro -> control
        self._iniciales = {}        # Parametro -> lo que mostraba el control al abrir

        pestanas = QTabWidget()
        formularios = {}
        for grupo in GRUPOS:
            contenido = QWidget()
            formularios[grupo] = QFormLayout(contenido)
            desplazable = QScrollArea()
            desplazable.setWidgetResizable(True)
            desplazable.setWidget(contenido)
            pestanas.addTab(desplazable, grupo)

        # Plano de trabajo: es de este modelo (se guarda en su archivo), no una preferencia
        self._plano = QComboBox()
        self._plano.addItems(list(PLANOS))
        self._plano.setCurrentText(plano)
        self._posicion_original = posicion
        self._posicion = QDoubleSpinBox()
        self._posicion.setDecimals(4)
        self._posicion.setRange(-1e7, 1e7)
        self._posicion.setSuffix(" " + unidades.simbolo("longitud"))
        self._posicion.setValue(posicion / self._factores["longitud"])
        self._posicion_inicial = self._posicion.value()
        self._etiqueta_posicion = QLabel()
        self._plano.currentTextChanged.connect(self._nombrar_posicion)
        self._nombrar_posicion()
        formularios["Rejilla"].addRow("Plano de trabajo (de este modelo)", self._plano)
        formularios["Rejilla"].addRow(self._etiqueta_posicion, self._posicion)

        for p in preferencias.PARAMETROS:
            control = self._crear_control(p)
            self._mostrar(p, control, p.valor())
            self._controles[p] = control
            self._iniciales[p] = self._leer(p, control)
            formularios[p.grupo].addRow(p.etiqueta, control)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel
                                   | QDialogButtonBox.RestoreDefaults)
        botones.button(QDialogButtonBox.Ok).setText("Aceptar")
        botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botones.button(QDialogButtonBox.RestoreDefaults).setText("Restablecer valores base")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        botones.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self._restablecer)

        diseno = QVBoxLayout(self)
        diseno.addWidget(pestanas)
        diseno.addWidget(botones)

    # ---------- Controles según el tipo ----------
    def _factor(self, p):
        return self._factores[p.magnitud] if p.magnitud else 1.0

    def _crear_control(self, p):
        if p.tipo == "entero":
            control = QSpinBox()
            control.setRange(int(p.minimo), int(min(p.maximo, 2**31 - 1)))
            return control
        if p.tipo == "real":
            control = QDoubleSpinBox()
            control.setDecimals(p.decimales)
            control.setRange(p.minimo / self._factor(p), p.maximo / self._factor(p))
            if p.magnitud:
                control.setSuffix(" " + unidades.simbolo(p.magnitud))
            return control
        if p.tipo == "bool":
            return QCheckBox()
        if p.tipo == "opcion":
            control = QComboBox()
            control.addItems(list(p.opciones))
            return control
        if p.tipo == "color":
            return BotonColor(p.valor())
        if p.tipo == "atajo":
            control = QKeySequenceEdit()
            control.setClearButtonEnabled(True)
            return control
        raise ValueError(f"Tipo de parámetro desconocido: {p.tipo}")

    def _mostrar(self, p, control, valor):
        """Pone en el control un valor dado en unidades internas."""
        if p.tipo == "entero":
            control.setValue(int(valor))
        elif p.tipo == "real":
            control.setValue(valor / self._factor(p))
        elif p.tipo == "bool":
            control.setChecked(bool(valor))
        elif p.tipo == "opcion":
            control.setCurrentText(valor)
        elif p.tipo == "color":
            control.poner_color(valor)
        elif p.tipo == "atajo":
            control.setKeySequence(QKeySequence(valor))

    def _leer(self, p, control):
        """Lo que muestra el control, tal cual (en unidades de pantalla)."""
        if p.tipo in ("entero", "real"):
            return control.value()
        if p.tipo == "bool":
            return control.isChecked()
        if p.tipo == "opcion":
            return control.currentText()
        if p.tipo == "color":
            return control.color()
        return control.keySequence().toString()

    def _nombrar_posicion(self):
        eje = NOMBRE_EJE[PLANOS[self._plano.currentText()]]
        self._etiqueta_posicion.setText(f"Posición del plano ({eje} =)")

    def _restablecer(self):
        for p, control in self._controles.items():
            self._mostrar(p, control, preferencias.base(p))

    # ---------- Resultado ----------
    def _valor_final(self, p, control):
        """Valor interno a guardar. Si el control no cambió, el original exacto; si quedó como la
        base, la base exacta; si no, lo escrito convertido a internas."""
        leido = self._leer(p, control)
        if leido == self._iniciales[p]:
            return p.valor()                              # no lo tocó: el original exacto
        if p.tipo != "real":
            return leido                                  # enteros, textos y colores no se convierten
        base = preferencias.base(p)
        if abs(leido - base / self._factor(p)) < 0.5 * 10.0 ** -control.decimals():
            return base                                   # lo dejó en la base: la base exacta
        return leido * self._factor(p)

    def plano_elegido(self):
        """(plano, posición en m) elegidos para el modelo."""
        if self._posicion.value() == self._posicion_inicial:
            posicion = self._posicion_original
        else:
            posicion = self._posicion.value() * self._factores["longitud"]
        return self._plano.currentText(), posicion

    def accept(self):
        valores = {p: self._valor_final(p, c) for p, c in self._controles.items()}
        for p, valor in valores.items():
            p.poner(valor)
        try:
            preferencias.guardar()
        except OSError as e:
            QMessageBox.warning(self, "Configuración", f"No se pudieron guardar las preferencias:\n{e}")
        super().accept()
