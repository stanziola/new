"""Formularios y dibujos de materiales y secciones (los usan Propiedades y la ventana Definir).

Cada formulario tiene la misma forma de uso (polimorfismo, como las herramientas):
- cargar(obj): pone los datos de un material o una sección que ya existe;
- valores(): diccionario con lo escrito, en unidades internas;
- error(): texto del problema si los datos no sirven, o None.
Todo se muestra en las unidades de pantalla y se devuelve en las internas.
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QSpinBox,
                               QVBoxLayout, QWidget)

from calculo.interaccion.comun import area_barra
from configuracion import colores, formato, unidades
from modelo import interaccion as puente
from modelo import concreto as cc
from modelo.estructura import Concreto

BARRAS = list(range(3, 12))              # números de barra que se ofrecen (#3 a #11)


# ---------------------------------------------------------------- Campos con unidades
def campo(magnitud, minimo, maximo):
    """QDoubleSpinBox en la unidad de pantalla de la magnitud (minimo y maximo en internas)."""
    caja = QDoubleSpinBox()
    f = unidades.factor(magnitud)
    caja.setDecimals(max(2, formato.decimales(magnitud)))
    caja.setRange(minimo / f, maximo / f)
    caja.setSuffix(f" {unidades.simbolo(magnitud)}")
    caja.setProperty("magnitud", magnitud)
    return caja


def leer(caja):
    """Valor de un campo de campo(), en unidades internas."""
    return caja.value() * unidades.factor(caja.property("magnitud"))


def poner(caja, valor):
    caja.setValue(valor / unidades.factor(caja.property("magnitud")))


def campo_longitud(minimo=0.01, maximo=10.0):
    return campo("longitud", minimo, maximo)


def diametro_barra(numero):
    """Diámetro de la barra en m (del área del cálculo de interacción)."""
    return math.sqrt(4 * area_barra(numero).to("m^2").magnitude / math.pi)


def posiciones_barras(c):
    """Centros de las barras (x a lo ancho b, y a lo alto h), en m, desde la esquina inferior izquierda."""
    xs = [c.d + i * (c.b - 2 * c.d) / (c.nx - 1) for i in range(c.nx)] if c.nx > 1 else [c.b / 2]
    ys = [c.d + j * (c.h - 2 * c.d) / (c.ny - 1) for j in range(c.ny)] if c.ny > 1 else [c.h / 2]
    puntos = [(x, ys[0]) for x in xs] + [(x, ys[-1]) for x in xs]
    puntos += [(x, y) for y in ys[1:-1] for x in (xs[0], xs[-1])]
    return puntos


# ---------------------------------------------------------------- Dibujo de la sección
class VistaSeccion(QWidget):
    """Dibujo a escala de la sección: el rectángulo, las barras y las cotas b y h, en grises."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.concreto = None

    def mostrar(self, concreto):
        self.concreto = concreto
        self.update()

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(colores.INTERFAZ_FONDO))
        c = self.concreto
        if c is None or c.forma != "rectangular" or c.b <= 0 or c.h <= 0:
            p.end()
            return
        margen = 34
        escala = min((self.width() - 2 * margen) / c.b, (self.height() - 2 * margen) / c.h)
        ancho, alto = c.b * escala, c.h * escala
        x0, y0 = (self.width() - ancho) / 2, (self.height() - alto) / 2
        p.setPen(QPen(QColor(colores.INTERFAZ_TEXTO), 1.5))
        p.setBrush(QColor(colores.INTERFAZ_HOVER))
        p.drawRect(QRectF(x0, y0, ancho, alto))
        if c.nx >= 1 and c.ny >= 1 and 0 < c.d < min(c.b, c.h) / 2:
            radio = max(diametro_barra(c.barra) * escala / 2, 2.0)
            p.setBrush(QColor(colores.INTERFAZ_TEXTO))
            p.setPen(Qt.NoPen)
            for x, y in posiciones_barras(c):
                p.drawEllipse(QPointF(x0 + x * escala, y0 + (c.h - y) * escala), radio, radio)
        p.setPen(QPen(QColor(colores.INTERFAZ_DESHABILITADO), 1))
        p.drawText(QRectF(x0, y0 + alto + 4, ancho, margen - 8), Qt.AlignHCenter | Qt.AlignTop,
                   f"b = {formato.cantidad(c.b, 'longitud')}")
        p.save()
        p.translate(x0 - 6, y0 + alto / 2)
        p.rotate(-90)
        p.drawText(QRectF(-alto / 2, -margen + 8, alto, margen - 8), Qt.AlignHCenter | Qt.AlignBottom,
                   f"h = {formato.cantidad(c.h, 'longitud')}")
        p.restore()
        p.end()


# ---------------------------------------------------------------- Materiales
class FormularioConcreto(QWidget):
    """Material de concreto: nombre y f'c; E y G se calculan y se muestran al lado."""

    def __init__(self, modelo, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.nombre = QLineEdit()
        self.fc = campo("esfuerzo", 1000, 200000)                  # 1 a 200 MPa
        poner(self.fc, 28000)
        self.gamma = QDoubleSpinBox()                              # kN/m³ (peso propio)
        self.gamma.setDecimals(2)
        self.gamma.setRange(0.0, 100.0)
        self.gamma.setSuffix(" kN/m³")
        self.gamma.setValue(cc.GAMMA_CONCRETO)
        self.gamma.setToolTip("Peso unitario para el peso propio. Concreto reforzado: 150 lb/ft³ = "
                              "23.56 kN/m³ (ASCE 7-05, Tabla C3-2)")
        self.e, self.g = QLabel(), QLabel()
        self._nombre_propio = False
        self.nombre.textEdited.connect(lambda *_: setattr(self, "_nombre_propio", True))
        self.fc.valueChanged.connect(self._actualizar)
        forma = QFormLayout(self)
        forma.setContentsMargins(0, 0, 0, 0)
        forma.addRow("Nombre", self.nombre)
        forma.addRow("f'c", self.fc)
        forma.addRow("E (ACI 318-19 §19.2.2.1b)", self.e)
        forma.addRow("G (ν = 0.2)", self.g)
        forma.addRow("γ (peso propio)", self.gamma)
        self._actualizar()

    def cargar(self, mat):
        self.fc.blockSignals(True)
        poner(self.fc, mat.fc)
        self.fc.blockSignals(False)
        self.gamma.setValue(mat.gamma)
        self.nombre.setText(mat.nombre)
        self._nombre_propio = mat.nombre != cc.nombre_material(mat.fc)
        self._actualizar()

    def _actualizar(self, *_):
        e, g = cc.modulos(leer(self.fc))
        self.e.setText(formato.cantidad(e, "esfuerzo"))
        self.g.setText(formato.cantidad(g, "esfuerzo"))
        if not self._nombre_propio:
            self.nombre.setText(cc.nombre_material(leer(self.fc)))

    def valores(self):
        return {"nombre": self.nombre.text(), "fc": leer(self.fc), "gamma": self.gamma.value()}

    def error(self):
        return None


class FormularioOtroMaterial(QWidget):
    """Material dado por E y G (familia "otros": los viejos, sin f'c)."""

    def __init__(self, modelo, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.nombre = QLineEdit("Material")
        self.e = campo("esfuerzo", 1, 1e10)
        self.g = campo("esfuerzo", 1, 1e10)
        poner(self.e, 200e6)
        poner(self.g, 77e6)
        forma = QFormLayout(self)
        forma.setContentsMargins(0, 0, 0, 0)
        forma.addRow("Nombre", self.nombre)
        forma.addRow("E", self.e)
        forma.addRow("G", self.g)

    def cargar(self, mat):
        self.nombre.setText(mat.nombre)
        poner(self.e, mat.e)
        poner(self.g, mat.g)

    def valores(self):
        return {"nombre": self.nombre.text(), "e": leer(self.e), "g": leer(self.g)}

    def error(self):
        return None


# ---------------------------------------------------------------- Secciones
class FormularioSeccion(QWidget):
    """Sección rectangular de concreto: material, b, h, d, barra, Nx y Ny; nombre y propiedades
    calculadas; y el dibujo debajo, que se actualiza con cada cambio."""

    def __init__(self, modelo, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.material = QComboBox()
        self.b, self.h, self.d = campo_longitud(), campo_longitud(), campo_longitud(0.005, 1.0)
        self.barra = QComboBox()
        for n in BARRAS:
            self.barra.addItem(f"#{n}", n)
        self.nx, self.ny = QSpinBox(), QSpinBox()
        for caja in (self.nx, self.ny):
            caja.setRange(2, 30)
        self.nombre = QLabel()
        self.datos = QLabel()
        self.datos.setTextFormat(Qt.RichText)
        self.vista = VistaSeccion()
        forma = QFormLayout()
        forma.addRow("Material", self.material)
        forma.addRow("b (eje local y)", self.b)
        forma.addRow("h (eje local z)", self.h)
        forma.addRow("d (al centro de las barras)", self.d)
        forma.addRow("Barra", self.barra)
        forma.addRow("Nx (arriba y abajo)", self.nx)
        forma.addRow("Ny (filas)", self.ny)
        forma.addRow("Nombre", self.nombre)
        forma.addRow(self.datos)
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        diseno.addLayout(forma)
        diseno.addWidget(self.vista, 1)
        for caja in (self.b, self.h, self.d, self.nx, self.ny):
            caja.valueChanged.connect(self._actualizar)
        for combo in (self.material, self.barra):
            combo.currentIndexChanged.connect(self._actualizar)
        self.llenar_materiales()
        self.cargar_concreto(Concreto(forma="rectangular", fc=0, d=0.06, barra=6, b=0.4, h=0.4, nx=3, ny=3), None)

    def llenar_materiales(self):
        actual = self.material.currentData()
        self.material.blockSignals(True)
        self.material.clear()
        for mid, m in self.modelo.materiales.items():
            if m.fc is not None:
                self.material.addItem(m.nombre, mid)
        i = self.material.findData(actual)
        self.material.setCurrentIndex(i if i >= 0 else 0)
        self.material.blockSignals(False)

    def cargar(self, sec):
        self.cargar_concreto(sec.concreto, sec.material)

    def cargar_concreto(self, c, material):
        cajas = (self.b, self.h, self.d, self.nx, self.ny, self.barra, self.material)
        for caja in cajas:
            caja.blockSignals(True)
        poner(self.b, c.b)
        poner(self.h, c.h)
        poner(self.d, c.d)
        self.nx.setValue(c.nx)
        self.ny.setValue(c.ny)
        i = self.barra.findData(c.barra)
        self.barra.setCurrentIndex(i if i >= 0 else BARRAS.index(6))
        if material is not None and self.material.findData(material) >= 0:
            self.material.setCurrentIndex(self.material.findData(material))
        for caja in cajas:
            caja.blockSignals(False)
        self._actualizar()

    def valores(self):
        return {"material": self.material.currentData(), "b": leer(self.b), "h": leer(self.h),
                "d": leer(self.d), "barra": self.barra.currentData(), "nx": self.nx.value(),
                "ny": self.ny.value()}

    def concreto(self):
        v = self.valores()
        mat = self.modelo.materiales.get(v["material"])
        return Concreto(forma="rectangular", fc=mat.fc if mat else 0.0, d=v["d"], barra=v["barra"],
                        b=v["b"], h=v["h"], nx=v["nx"], ny=v["ny"])

    def error(self):
        v = self.valores()
        if v["material"] is None:
            return "Primero crea un material de concreto"
        if not 0 < v["d"] < min(v["b"], v["h"]) / 2:
            return "d debe ser menor que la mitad de b y de h"
        try:
            puente.propiedades(self.concreto())
        except ValueError as e:
            return str(e)
        return None

    def _actualizar(self, *_):
        v = self.valores()
        self.nombre.setText(cc.nombre_seccion(v["b"], v["h"], v["nx"], v["ny"], v["barra"]))
        a, iy, iz, j = cc.propiedades_rectangulo(v["b"], v["h"])
        error = self.error()
        if error is None:
            p = puente.propiedades(self.concreto())
            extra = (f"ρ = {p['cuantia']:.2f} %  ·  As = "
                     f"{formato.cantidad(p['As_total'].to('m^2').magnitude, 'area')}")
        else:
            extra = f"<span style='color:{colores.INTERFAZ_DESHABILITADO}'>{error}</span>"
        self.datos.setText(
            f"A = {formato.cantidad(a, 'area')}<br>Iy = {formato.cantidad(iy, 'inercia')}"
            f"<br>Iz = {formato.cantidad(iz, 'inercia')}<br>J = {formato.cantidad(j, 'inercia')}<br>{extra}")
        self.vista.mostrar(self.concreto())


class FormularioOtraSeccion(QWidget):
    """Sección dada por A, Iy, Iz y J (familia "otros": las viejas, sin refuerzo)."""

    def __init__(self, modelo, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.nombre = QLineEdit("Sección")
        self.a = campo("area", 1e-8, 1e3)
        self.iy, self.iz, self.j = (campo("inercia", 1e-14, 1e3) for _ in range(3))
        for caja, valor in ((self.a, 0.04), (self.iy, 1.333e-4), (self.iz, 1.333e-4), (self.j, 2.25e-4)):
            poner(caja, valor)
        self.material = QComboBox()
        self.material.addItem("sin material", None)
        for mid, m in modelo.materiales.items():
            self.material.addItem(m.nombre, mid)
        forma = QFormLayout(self)
        forma.setContentsMargins(0, 0, 0, 0)
        forma.addRow("Nombre", self.nombre)
        forma.addRow("A", self.a)
        forma.addRow("Iy", self.iy)
        forma.addRow("Iz", self.iz)
        forma.addRow("J", self.j)
        forma.addRow("Material", self.material)

    def cargar(self, sec):
        self.nombre.setText(sec.nombre)
        for caja, valor in ((self.a, sec.a), (self.iy, sec.iy), (self.iz, sec.iz), (self.j, sec.j)):
            poner(caja, valor)
        self.material.setCurrentIndex(max(0, self.material.findData(sec.material)))

    def valores(self):
        return {"nombre": self.nombre.text(), "a": leer(self.a), "iy": leer(self.iy),
                "iz": leer(self.iz), "j": leer(self.j), "material": self.material.currentData()}

    def error(self):
        return None


FORMULARIOS = {
    ("material", "concreto"): FormularioConcreto,
    ("material", "otros"): FormularioOtroMaterial,
    ("seccion", "concreto"): FormularioSeccion,
    ("seccion", "otros"): FormularioOtraSeccion,
}
