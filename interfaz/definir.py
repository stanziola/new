"""Definir materiales y secciones de concreto (menú Definir y barra de arriba).

- Materiales: concreto definido por f'c; E y G se calculan (modelo/concreto.py) y se muestran.
  Un material que ya existe no se edita: las secciones copiaron su f'c (para sus diagramas).
- Secciones: rectangulares de concreto con su refuerzo. El nombre es automático
  ("Concreto 20x20 Nx3 Ny3 #6") y A, Iy, Iz, J y ρ se calculan. La previsualización dibuja la
  sección a escala con sus barras.
Todo se muestra en las unidades de pantalla y se guarda en las internas.
Cada cambio pasa por ventana.antes_de_cambiar(), así que se puede deshacer con Ctrl+Z.
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QSpinBox, QVBoxLayout, QWidget)

from calculo.interaccion.comun import area_barra
from configuracion import colores, formato, unidades
from interfaz import concreto as puente
from modelo import concreto as cc
from modelo.estructura import Concreto

BARRAS = list(range(3, 12))              # números de barra que se ofrecen (#3 a #11)


def diametro_barra(numero):
    """Diámetro de la barra en m (del área del cálculo de interacción)."""
    return math.sqrt(4 * area_barra(numero).to("m^2").magnitude / math.pi)


def _campo_longitud(minimo=0.01, maximo=10.0):
    """QDoubleSpinBox en la unidad de longitud de pantalla."""
    campo = QDoubleSpinBox()
    f = unidades.factor("longitud")
    campo.setDecimals(max(2, formato.decimales("longitud")))
    campo.setRange(minimo / f, maximo / f)
    campo.setSuffix(f" {unidades.simbolo('longitud')}")
    return campo


def _metros(campo):
    return campo.value() * unidades.factor("longitud")


def _poner_metros(campo, valor):
    campo.setValue(valor / unidades.factor("longitud"))


# ---------------------------------------------------------------- Materiales
class DialogoMateriales(QDialog):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.setWindowTitle("Materiales")
        self.resize(560, 320)
        self.lista = QListWidget()
        self.lista.currentRowChanged.connect(self._mostrar_elegido)

        self.fc = QDoubleSpinBox()
        f = unidades.factor("esfuerzo")
        self.fc.setDecimals(max(1, formato.decimales("esfuerzo")))
        self.fc.setRange(1000 / f, 200000 / f)                   # 1 a 200 MPa
        self.fc.setSuffix(f" {unidades.simbolo('esfuerzo')}")
        self.fc.setValue(28000 / f)
        self.nombre = QLineEdit()
        self.e = QLabel()
        self.g = QLabel()
        self._nombre_propio = False
        self.nombre.textEdited.connect(lambda *_: setattr(self, "_nombre_propio", True))
        self.fc.valueChanged.connect(self._actualizar)

        formulario = QFormLayout()
        formulario.addRow("f'c", self.fc)
        formulario.addRow("Nombre", self.nombre)
        formulario.addRow("E (ACI 318-19 §19.2.2.1b)", self.e)
        formulario.addRow("G (ν = 0.2)", self.g)
        agregar = QPushButton("Agregar")
        agregar.clicked.connect(self.agregar)
        formulario.addRow(agregar)
        derecha = QWidget()
        derecha.setLayout(formulario)

        self.eliminar_boton = QPushButton("Eliminar")
        self.eliminar_boton.clicked.connect(self.eliminar)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.accept)
        izquierda = QVBoxLayout()
        izquierda.addWidget(QLabel("<b>Materiales</b>"))
        izquierda.addWidget(self.lista, 1)
        izquierda.addWidget(self.eliminar_boton)
        arriba = QHBoxLayout()
        arriba.addLayout(izquierda, 1)
        arriba.addWidget(derecha, 1)
        abajo = QHBoxLayout()
        abajo.addStretch(1)
        abajo.addWidget(cerrar)
        diseno = QVBoxLayout(self)
        diseno.addLayout(arriba, 1)
        diseno.addLayout(abajo)
        self._llenar()
        self._actualizar()

    def _llenar(self):
        self.lista.clear()
        for mid, m in self.ventana.modelo.materiales.items():
            texto = f"{m.nombre}  ·  E = {formato.cantidad(m.e, 'esfuerzo')}"
            item = QListWidgetItem(texto)
            item.setData(Qt.UserRole, mid)
            self.lista.addItem(item)
        self.eliminar_boton.setEnabled(self.lista.count() > 0)

    def _fc(self):
        return self.fc.value() * unidades.factor("esfuerzo")

    def _actualizar(self, *_):
        e, g = cc.modulos(self._fc())
        self.e.setText(formato.cantidad(e, "esfuerzo"))
        self.g.setText(formato.cantidad(g, "esfuerzo"))
        if not self._nombre_propio:
            self.nombre.setText(cc.nombre_material(self._fc()))

    def _mostrar_elegido(self, fila):
        item = self.lista.item(fila)
        mat = self.ventana.modelo.materiales.get(item.data(Qt.UserRole)) if item else None
        if mat is not None and mat.fc is not None:
            self.fc.setValue(mat.fc / unidades.factor("esfuerzo"))

    def agregar(self):
        nombre = self.nombre.text().strip() or cc.nombre_material(self._fc())
        e, g = cc.modulos(self._fc())
        self.ventana.antes_de_cambiar()
        mid = self.ventana.modelo.agregar_material(nombre, e, g, fc=self._fc())
        self.ventana.modelo_cambiado(f"Material {mid} agregado: {nombre}")
        self._nombre_propio = False
        self._llenar()
        self._actualizar()

    def eliminar(self):
        item = self.lista.currentItem()
        if item is None:
            return
        mid = item.data(Qt.UserRole)
        modelo = self.ventana.modelo
        barras = [eid for eid, el in modelo.elementos.items() if el.material == mid]
        secciones = [sid for sid, sec in modelo.secciones.items() if sec.material == mid]
        if barras or secciones:
            QMessageBox.information(self, "Materiales", f"El material está en uso (barras {barras}, "
                                                        f"secciones {secciones})")
            return
        self.ventana.antes_de_cambiar()
        self.ventana.modelo.eliminar_material(mid)
        self.ventana.modelo_cambiado(f"Material {mid} eliminado")
        self._llenar()


# ---------------------------------------------------------------- Secciones
class VistaSeccion(QWidget):
    """Dibujo a escala de la sección: el rectángulo, las barras y las cotas b y h, en grises."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.concreto = None

    def mostrar(self, concreto):
        self.concreto = concreto
        self.update()

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(colores.INTERFAZ_FONDO))
        c = self.concreto
        if c is None or c.b <= 0 or c.h <= 0:
            p.end()
            return
        margen = 34
        escala = min((self.width() - 2 * margen) / c.b, (self.height() - 2 * margen) / c.h)
        ancho, alto = c.b * escala, c.h * escala
        x0, y0 = (self.width() - ancho) / 2, (self.height() - alto) / 2
        p.setPen(QPen(QColor(colores.INTERFAZ_TEXTO), 1.5))
        p.setBrush(QColor(colores.INTERFAZ_HOVER))
        p.drawRect(QRectF(x0, y0, ancho, alto))
        # Barras: nx arriba y abajo, y las filas intermedias con una barra a cada lado
        radio = max(diametro_barra(c.barra) * escala / 2, 2.0)
        p.setBrush(QColor(colores.INTERFAZ_TEXTO))
        p.setPen(Qt.NoPen)
        for x, y in posiciones_barras(c):
            p.drawEllipse(QPointF(x0 + x * escala, y0 + (c.h - y) * escala), radio, radio)
        # Cotas
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


def posiciones_barras(c):
    """Centros de las barras (x a lo ancho b, y a lo alto h), en m, desde la esquina inferior izquierda."""
    xs = [c.d + i * (c.b - 2 * c.d) / (c.nx - 1) for i in range(c.nx)] if c.nx > 1 else [c.b / 2]
    ys = [c.d + j * (c.h - 2 * c.d) / (c.ny - 1) for j in range(c.ny)] if c.ny > 1 else [c.h / 2]
    puntos = [(x, ys[0]) for x in xs] + [(x, ys[-1]) for x in xs]
    puntos += [(x, y) for y in ys[1:-1] for x in (xs[0], xs[-1])]
    return puntos


class FormularioSeccion(QWidget):
    """Material, b, h, d, barra, Nx y Ny; nombre y propiedades calculadas; previsualización."""

    def __init__(self, modelo, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.material = QComboBox()
        self.b, self.h, self.d = _campo_longitud(), _campo_longitud(), _campo_longitud(0.005, 1.0)
        self.barra = QComboBox()
        for n in BARRAS:
            self.barra.addItem(f"#{n}", n)
        self.nx, self.ny = QSpinBox(), QSpinBox()
        for campo in (self.nx, self.ny):
            campo.setRange(2, 30)
        self.nombre = QLabel()
        self.datos = QLabel()
        self.datos.setTextFormat(Qt.RichText)
        self.vista = VistaSeccion()
        formulario = QFormLayout()
        formulario.addRow("Material", self.material)
        formulario.addRow("b (eje local y)", self.b)
        formulario.addRow("h (eje local z)", self.h)
        formulario.addRow("d (al centro de las barras)", self.d)
        formulario.addRow("Barra", self.barra)
        formulario.addRow("Nx (arriba y abajo)", self.nx)
        formulario.addRow("Ny (filas)", self.ny)
        formulario.addRow("Nombre", self.nombre)
        formulario.addRow(self.datos)
        diseno = QHBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        diseno.addLayout(formulario, 1)
        diseno.addWidget(self.vista, 1)
        for campo in (self.b, self.h, self.d):
            campo.valueChanged.connect(self._actualizar)
        for campo in (self.nx, self.ny):
            campo.valueChanged.connect(self._actualizar)
        for combo in (self.material, self.barra):
            combo.currentIndexChanged.connect(self._actualizar)
        self.llenar_materiales()
        self.poner(Concreto(forma="rectangular", fc=0, d=0.06, barra=6, b=0.4, h=0.4, nx=3, ny=3), None)

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
        self._actualizar()

    def poner(self, c, material):
        """Carga los datos de un Concreto (para editar o para partir de una sección)."""
        for campo in (self.b, self.h, self.d, self.nx, self.ny, self.barra, self.material):
            campo.blockSignals(True)
        _poner_metros(self.b, c.b)
        _poner_metros(self.h, c.h)
        _poner_metros(self.d, c.d)
        self.nx.setValue(c.nx)
        self.ny.setValue(c.ny)
        i = self.barra.findData(c.barra)
        self.barra.setCurrentIndex(i if i >= 0 else BARRAS.index(6))
        if material is not None and self.material.findData(material) >= 0:
            self.material.setCurrentIndex(self.material.findData(material))
        for campo in (self.b, self.h, self.d, self.nx, self.ny, self.barra, self.material):
            campo.blockSignals(False)
        self._actualizar()

    def valores(self):
        """(material, b, h, d, barra, nx, ny) en unidades internas."""
        return (self.material.currentData(), _metros(self.b), _metros(self.h), _metros(self.d),
                self.barra.currentData(), self.nx.value(), self.ny.value())

    def concreto(self):
        material, b, h, d, barra, nx, ny = self.valores()
        mat = self.modelo.materiales.get(material)
        return Concreto(forma="rectangular", fc=mat.fc if mat else 0.0, d=d, barra=barra, b=b, h=h,
                        nx=nx, ny=ny)

    def error(self):
        """Texto del problema si los datos no sirven, o None."""
        material, b, h, d, barra, nx, ny = self.valores()
        if material is None:
            return "Primero agrega un material de concreto (Definir → Materiales)"
        if not 0 < d < min(b, h) / 2:
            return "d debe ser menor que la mitad de b y de h"
        try:
            puente.propiedades(self.concreto())
        except ValueError as e:
            return str(e)
        return None

    def _actualizar(self, *_):
        material, b, h, d, barra, nx, ny = self.valores()
        self.nombre.setText(cc.nombre_seccion(b, h, nx, ny, barra))
        a, iy, iz, j = cc.propiedades_rectangulo(b, h)
        error = self.error()
        if error is None:
            p = puente.propiedades(self.concreto())
            extra = f"ρ = {p['cuantia']:.2f} %  ·  As = {formato.cantidad(p['As_total'].to('m^2').magnitude, 'area')}"
        else:
            extra = f"<span style='color:{colores.INTERFAZ_DESHABILITADO}'>{error}</span>"
        self.datos.setText(
            f"A = {formato.cantidad(a, 'area')}<br>Iy = {formato.cantidad(iy, 'inercia')}"
            f"<br>Iz = {formato.cantidad(iz, 'inercia')}<br>J = {formato.cantidad(j, 'inercia')}<br>{extra}")
        self.vista.mostrar(self.concreto())


class DialogoSecciones(QDialog):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.setWindowTitle("Secciones de concreto")
        self.resize(820, 440)
        self.lista = QListWidget()
        self.lista.currentRowChanged.connect(self._elegida)
        self.formulario = FormularioSeccion(ventana.modelo)
        agregar = QPushButton("Agregar como nueva")
        agregar.clicked.connect(self.agregar)
        self.guardar_boton = QPushButton("Guardar cambios")
        self.guardar_boton.setToolTip("Cambia la sección elegida; si alguna barra la usa, se crea otra")
        self.guardar_boton.clicked.connect(self.guardar)
        self.eliminar_boton = QPushButton("Eliminar")
        self.eliminar_boton.clicked.connect(self.eliminar)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.accept)

        izquierda = QVBoxLayout()
        izquierda.addWidget(QLabel("<b>Secciones</b>"))
        izquierda.addWidget(self.lista, 1)
        izquierda.addWidget(self.eliminar_boton)
        botones = QHBoxLayout()
        botones.addWidget(agregar)
        botones.addWidget(self.guardar_boton)
        botones.addStretch(1)
        botones.addWidget(cerrar)
        derecha = QVBoxLayout()
        derecha.addWidget(self.formulario, 1)
        derecha.addLayout(botones)
        diseno = QHBoxLayout(self)
        diseno.addLayout(izquierda, 1)
        diseno.addLayout(derecha, 3)
        self._llenar()

    def _llenar(self, elegir=None):
        self.formulario.modelo = self.ventana.modelo
        self.formulario.llenar_materiales()
        self.lista.blockSignals(True)
        self.lista.clear()
        for sid, sec in self.ventana.modelo.secciones.items():
            item = QListWidgetItem(sec.nombre)
            item.setData(Qt.UserRole, sid)
            self.lista.addItem(item)
            if sid == elegir:
                self.lista.setCurrentItem(item)
        self.lista.blockSignals(False)
        hay = self.lista.currentItem() is not None
        self.guardar_boton.setEnabled(hay)
        self.eliminar_boton.setEnabled(hay)

    def _sid(self):
        item = self.lista.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _elegida(self, *_):
        sec = self.ventana.modelo.secciones.get(self._sid())
        es_rectangular = sec is not None and sec.concreto is not None and sec.concreto.forma == "rectangular"
        if es_rectangular:
            self.formulario.poner(sec.concreto, sec.material)
        self.guardar_boton.setEnabled(es_rectangular)
        self.eliminar_boton.setEnabled(sec is not None)

    def _revisar(self):
        error = self.formulario.error()
        if error:
            QMessageBox.information(self, "Secciones", error)
        return error is None

    def agregar(self):
        if not self._revisar():
            return
        modelo = self.ventana.modelo
        existente = cc.buscar_seccion(modelo, *self.formulario.valores())
        if existente is not None:
            QMessageBox.information(self, "Secciones", f"Ya existe: {modelo.secciones[existente].nombre}")
            self._llenar(existente)
            return
        self.ventana.antes_de_cambiar()
        sid = cc.crear_seccion(self.ventana.modelo, *self.formulario.valores())
        self.ventana.modelo_cambiado(f"Sección {sid} agregada: {self.ventana.modelo.secciones[sid].nombre}")
        self._llenar(sid)

    def guardar(self):
        sid = self._sid()
        if sid is None or not self._revisar():
            return
        modelo = self.ventana.modelo
        en_uso = [eid for eid, el in modelo.elementos.items() if el.seccion == sid]
        if en_uso:                                    # no se cambian barras sin que se note
            self.agregar()
            return
        material, b, h, d, barra, nx, ny = self.formulario.valores()
        self.ventana.antes_de_cambiar()
        sec = self.ventana.modelo.secciones[sid]
        sec.concreto = self.formulario.concreto()
        sec.material = material
        sec.nombre = cc.nombre_seccion(b, h, nx, ny, barra)
        sec.a, sec.iy, sec.iz, sec.j = cc.propiedades_rectangulo(b, h)
        self.ventana.modelo_cambiado(f"Sección {sid} cambiada: {sec.nombre}")
        self._llenar(sid)

    def eliminar(self):
        sid = self._sid()
        if sid is None:
            return
        en_uso = [eid for eid, el in self.ventana.modelo.elementos.items() if el.seccion == sid]
        if en_uso:
            QMessageBox.information(self, "Secciones", f"La sección está en uso en las barras {en_uso}")
            return
        self.ventana.antes_de_cambiar()
        self.ventana.modelo.eliminar_seccion(sid)
        self.ventana.modelo_cambiado(f"Sección {sid} eliminada")
        self._llenar()
