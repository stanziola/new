"""Formularios y dibujos de materiales y secciones (los usan Propiedades y la ventana Definir).

Cada formulario tiene la misma forma de uso (polimorfismo, como las herramientas):
- cargar(obj): pone los datos de un material o una sección que ya existe;
- valores(): diccionario con lo escrito, en unidades internas;
- error(): texto del problema si los datos no sirven, o None;
- refrescar(): vuelve a escribir lo calculado (E, G, nombre...) en las unidades vigentes.
Todo se muestra en las unidades de pantalla y se devuelve en las internas. Los números son
CampoNumero (paneles/comunes.py): la unidad va al lado, sin flechas.
Las medidas de la sección (b, h, d) usan la magnitud "seccion" (cm por defecto), no la longitud.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from configuracion import colores, formato
from interfaz import textos
from interfaz.paneles.comunes import CampoNumero, Lista
from modelo import interaccion as puente
from modelo import acero as ac
from modelo import concreto as cc
from modelo.estructura import FY_DEFECTO, Acero, Concreto
from modelo.interaccion import diametro_barra, posiciones_barras

BARRAS = list(range(3, 12))              # números de barra que se ofrecen (#3 a #11)


# ---------------------------------------------------------------- Campos con unidades
def campo(magnitud, minimo, maximo):
    """CampoNumero en la unidad de pantalla de la magnitud (minimo y maximo en internas)."""
    return CampoNumero(magnitud, minimo, maximo)


def campo_seccion(minimo=0.01, maximo=10.0):
    """b, h o d: en la unidad de las dimensiones de sección (cm por defecto)."""
    return CampoNumero("seccion", minimo, maximo)


def campo_barras():
    """Nx o Ny: cantidad de barras, entero sin unidad."""
    return CampoNumero(minimo=2, maximo=30, entero=True)


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
        if isinstance(self.concreto, Acero):         # también dibuja las de acero (Propiedades, Asignar)
            pintar_acero(self, self.concreto)
            return
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
                   f"b = {formato.cantidad(c.b, 'seccion')}")
        p.save()
        p.translate(x0 - 6, y0 + alto / 2)
        p.rotate(-90)
        p.drawText(QRectF(-alto / 2, -margen + 8, alto, margen - 8), Qt.AlignHCenter | Qt.AlignBottom,
                   f"h = {formato.cantidad(c.h, 'seccion')}")
        p.restore()
        p.end()


# ---------------------------------------------------------------- Materiales
class FormularioConcreto(QWidget):
    """Material de concreto: nombre y f'c; E y G se calculan y se muestran al lado.

    El nombre automático ("Concreto f'c 28 MPa", en la unidad vigente) se ve en gris dentro del
    campo: si se deja vacío, el material queda con nombre automático, que sigue al f'c y a las
    unidades. Lo que se escriba ahí es un nombre propio y se guarda tal cual."""

    def __init__(self, modelo, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.nombre = QLineEdit()
        self.fc = campo("esfuerzo", 1000, 200000)                  # 1 a 200 MPa
        self.fc.poner(28000)
        self.gamma = campo("peso_unitario", 0.0, 100.0)            # peso propio (F/L³)
        self.gamma.poner(cc.GAMMA_CONCRETO)
        self.gamma.setToolTip("Peso unitario para el peso propio. Concreto reforzado: 150 lb/ft³ = "
                              "23.56 kN/m³ (ASCE 7-05, Tabla C3-2)")
        self.e, self.g = QLabel(), QLabel()
        self.fc.cambiado.connect(self._actualizar)
        forma = QFormLayout(self)
        forma.setContentsMargins(0, 0, 0, 0)
        forma.addRow("Nombre", self.nombre)
        forma.addRow("f'c", self.fc)
        forma.addRow("E (ACI 318-19 §19.2.2.1b)", self.e)
        forma.addRow("G (ν = 0.2)", self.g)
        forma.addRow("γ (peso propio)", self.gamma)
        self._actualizar()

    def cargar(self, mat):
        self.fc.poner(mat.fc)
        self.gamma.poner(mat.gamma)
        automatico = mat.nombre == cc.nombre_material(mat.fc)
        self.nombre.setText("" if automatico else mat.nombre)
        self._actualizar()

    def _actualizar(self, *_):
        e, g = cc.modulos(self.fc.valor())
        self.e.setText(formato.cantidad(e, "esfuerzo"))
        self.g.setText(formato.cantidad(g, "esfuerzo"))
        self.nombre.setPlaceholderText(textos.nombre_concreto(self.fc.valor()))

    def refrescar(self):
        self._actualizar()

    def valores(self):
        return {"nombre": self.nombre.text(), "fc": self.fc.valor(), "gamma": self.gamma.valor()}

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
        self.e.poner(200e6)
        self.g.poner(77e6)
        forma = QFormLayout(self)
        forma.setContentsMargins(0, 0, 0, 0)
        forma.addRow("Nombre", self.nombre)
        forma.addRow("E", self.e)
        forma.addRow("G", self.g)

    def cargar(self, mat):
        self.nombre.setText(mat.nombre)
        self.e.poner(mat.e)
        self.g.poner(mat.g)

    def refrescar(self):
        pass

    def valores(self):
        return {"nombre": self.nombre.text(), "e": self.e.valor(), "g": self.g.valor()}

    def error(self):
        return None


# ---------------------------------------------------------------- Secciones
class FormularioSeccion(QWidget):
    """Sección rectangular de concreto: material, b, h, d, barra, Nx, Ny y fy del acero; nombre y
    propiedades calculadas (con el aviso si la cuantía se sale de sus límites); y el dibujo debajo, que
    se actualiza con cada cambio."""

    def __init__(self, modelo, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.material = Lista()
        self.b, self.h, self.d = campo_seccion(), campo_seccion(), campo_seccion(0.005, 1.0)
        self.barra = Lista()
        for n in BARRAS:
            self.barra.addItem(f"#{n}", n)
        self.nx, self.ny = campo_barras(), campo_barras()
        self.fy = campo("esfuerzo", 100000, 1000000)               # 14.5 a 145 ksi
        self.fy.poner(FY_DEFECTO)
        self.fy.setToolTip("Fluencia del acero de refuerzo. Grado 60: 60 ksi = 420 MPa (lo usual en Panamá)")
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
        forma.addRow("fy (acero)", self.fy)
        forma.addRow("Nombre", self.nombre)
        forma.addRow(self.datos)
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        diseno.addLayout(forma)
        diseno.addWidget(self.vista, 1)
        for caja in (self.b, self.h, self.d, self.nx, self.ny, self.fy):
            caja.cambiado.connect(self._actualizar)
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
                self.material.addItem(textos.nombre(m), mid)
        i = self.material.findData(actual)
        self.material.setCurrentIndex(i if i >= 0 else 0)
        self.material.blockSignals(False)

    def cargar(self, sec):
        # El aviso de cuantía es la regla de columnas: solo si alguna columna usa esta sección
        sid = next((s for s, x in self.modelo.secciones.items() if x is sec), None)
        self._en_columna = sid is not None and puente.usada_en_columna(self.modelo, sid)
        self.cargar_concreto(sec.concreto, sec.material)

    def cargar_concreto(self, c, material):
        for combo in (self.barra, self.material):
            combo.blockSignals(True)
        self.b.poner(c.b)
        self.h.poner(c.h)
        self.d.poner(c.d)
        self.nx.poner(c.nx)
        self.ny.poner(c.ny)
        self.fy.poner(c.fy)
        i = self.barra.findData(c.barra)
        self.barra.setCurrentIndex(i if i >= 0 else BARRAS.index(6))
        if material is not None and self.material.findData(material) >= 0:
            self.material.setCurrentIndex(self.material.findData(material))
        for combo in (self.barra, self.material):
            combo.blockSignals(False)
        self._actualizar()

    def valores(self):
        return {"material": self.material.currentData(), "b": self.b.valor(), "h": self.h.valor(),
                "d": self.d.valor(), "barra": self.barra.currentData(), "nx": self.nx.valor(),
                "ny": self.ny.valor(), "fy": self.fy.valor()}

    def concreto(self):
        v = self.valores()
        mat = self.modelo.materiales.get(v["material"])
        return Concreto(forma="rectangular", fc=mat.fc if mat else 0.0, d=v["d"], barra=v["barra"],
                        b=v["b"], h=v["h"], nx=v["nx"], ny=v["ny"], fy=v["fy"])

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

    def refrescar(self):
        self.llenar_materiales()                 # los nombres de los materiales, en las unidades vigentes
        self._actualizar()

    def _actualizar(self, *_):
        v = self.valores()
        self.nombre.setText(textos.nombre_rectangular(v["b"], v["h"], v["nx"], v["ny"], v["barra"], v["fy"]))
        a, iy, iz, j = cc.propiedades_rectangulo(v["b"], v["h"])
        error = self.error()
        if error is None:
            p = puente.propiedades(self.concreto())
            aviso = (puente.aviso_cuantia(p["cuantia"], self.modelo.portico_especial)
                     if getattr(self, "_en_columna", False) else "")
            extra = (f"ρ = {p['cuantia']:.2f} %  ·  As = "
                     f"{formato.cantidad(p['As_total'].to('m^2').magnitude, 'area')}"
                     + (f"<br><b>ρ {aviso}</b>" if aviso else ""))
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
            caja.poner(valor)
        self.material = Lista()
        self.material.addItem("sin material", None)
        for mid, m in modelo.materiales.items():
            self.material.addItem(textos.nombre(m), mid)
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
            caja.poner(valor)
        self.material.setCurrentIndex(max(0, self.material.findData(sec.material)))

    def refrescar(self):
        pass

    def valores(self):
        return {"nombre": self.nombre.text(), "a": self.a.valor(), "iy": self.iy.valor(),
                "iz": self.iz.valor(), "j": self.j.valor(), "material": self.material.currentData()}

    def error(self):
        return None


# ---------------------------------------------------------------- Acero
class FormularioAcero(QWidget):
    """Material de acero: nombre, E, ν y γ; G = E/(2(1 + ν)) se calcula y se muestra al lado."""

    def __init__(self, modelo, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.nombre = QLineEdit()
        self.e = campo("esfuerzo", 1e6, 1e9)
        self.e.poner(ac.E_ACERO)
        self.e.setToolTip("Módulo de elasticidad. Acero estructural: 29 000 ksi ≈ 200 000 MPa")
        self.nu = CampoNumero(minimo=0.0, maximo=0.49)
        self.nu.poner(ac.POISSON_ACERO)
        self.gamma = campo("peso_unitario", 0.0, 200.0)
        self.gamma.poner(ac.GAMMA_ACERO)
        self.gamma.setToolTip("Peso unitario para el peso propio. Acero: 492 lb/ft³ = 77.3 kN/m³ "
                              "(ASCE 7-05, Tabla C3-2). 0 = sin peso propio")
        self.g = QLabel()
        for caja in (self.e, self.nu):
            caja.cambiado.connect(self._actualizar)
        forma = QFormLayout(self)
        forma.setContentsMargins(0, 0, 0, 0)
        forma.addRow("Nombre", self.nombre)
        forma.addRow("E", self.e)
        forma.addRow("ν", self.nu)
        forma.addRow("G = E/(2(1 + ν))", self.g)
        forma.addRow("γ (peso propio)", self.gamma)
        self._actualizar()

    def cargar(self, mat):
        self.e.poner(mat.e)
        self.nu.poner(round(ac.poisson(mat), 6))
        self.gamma.poner(mat.gamma)
        self.nombre.setText("" if mat.nombre == ac.nombre_material(mat.e) else mat.nombre)
        self._actualizar()

    def _actualizar(self, *_):
        try:
            self.g.setText(formato.cantidad(ac.modulo_cortante(self.e.valor(), self.nu.valor()), "esfuerzo"))
        except ValueError as e:
            self.g.setText(str(e))
        self.nombre.setPlaceholderText(ac.nombre_material(self.e.valor()))

    def refrescar(self):
        self._actualizar()

    def valores(self):
        return {"nombre": self.nombre.text(), "e": self.e.valor(), "nu": self.nu.valor(), "gamma": self.gamma.valor()}

    def error(self):
        try:
            ac.modulo_cortante(self.e.valor(), self.nu.valor())
        except ValueError as e:
            return str(e)
        return None


class VistaAcero(QWidget):
    """Dibujo a escala de una sección de acero (tubo o perfil I), con sus cotas, en grises."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.acero = None

    def mostrar(self, acero):
        self.acero = acero
        self.update()

    def paintEvent(self, _evento):
        pintar_acero(self, self.acero)


def pintar_acero(widget, s):
    """Dibuja en widget la sección de acero s (tubo o perfil I) a escala, con sus cotas."""
    if True:
        self = widget
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(colores.INTERFAZ_FONDO))
        try:
            ac.propiedades(s)
        except (ValueError, AttributeError):
            p.end()
            return
        ancho_real, alto_real = (s.D, s.D) if s.forma == "tubo" else (s.bf, s.d)
        margen = 34
        escala = min((self.width() - 2 * margen) / ancho_real, (self.height() - 2 * margen) / alto_real)
        cx, cy = self.width() / 2, self.height() / 2
        p.setPen(QPen(QColor(colores.INTERFAZ_TEXTO), 1.5))
        p.setBrush(QColor(colores.INTERFAZ_HOVER))
        if s.forma == "tubo":
            r = s.D * escala / 2
            camino = QPainterPath()
            camino.addEllipse(QPointF(cx, cy), r, r)
            ri = max(r - s.t * escala, 0.0)
            camino.addEllipse(QPointF(cx, cy), ri, ri)          # el hueco (regla par-impar)
            p.drawPath(camino)
            abajo = cy + r
            cotas = f"D = {formato.cantidad(s.D, 'seccion')}   ·   t = {formato.cantidad(s.t, 'seccion')}"
        else:
            bf, d, tw, tf = (v * escala for v in (s.bf, s.d, s.tw, s.tf))
            x0, y0 = cx - bf / 2, cy - d / 2
            puntos = [(0, 0), (bf, 0), (bf, tf), (bf / 2 + tw / 2, tf), (bf / 2 + tw / 2, d - tf), (bf, d - tf),
                      (bf, d), (0, d), (0, d - tf), (bf / 2 - tw / 2, d - tf), (bf / 2 - tw / 2, tf), (0, tf)]
            p.drawPolygon(QPolygonF([QPointF(x0 + x, y0 + y) for x, y in puntos]))
            abajo = cy + d / 2
            cotas = f"bf = {formato.cantidad(s.bf, 'seccion')}   ·   d = {formato.cantidad(s.d, 'seccion')}"
        p.setPen(QPen(QColor(colores.INTERFAZ_DESHABILITADO), 1))
        p.drawText(QRectF(0, abajo + 4, self.width(), margen - 8), Qt.AlignHCenter | Qt.AlignTop, cotas)
        p.end()


class FormularioSeccionAcero(QWidget):
    """Sección de acero: material, forma (tubo circular o perfil I), sus medidas y un nombre (vacío: el
    automático, en mm). Debajo, A, I y J calculados y el dibujo."""

    ETIQUETAS = {"D": "D (diámetro exterior)", "t": "t (espesor)", "d": "d (peralte, eje local z)",
                 "bf": "bf (ancho de alas, eje local y)", "tw": "tw (alma)", "tf": "tf (alas)"}

    def __init__(self, modelo, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.material = Lista()
        self.forma_lista = Lista()
        for clave, texto in ac.FORMAS.items():
            self.forma_lista.addItem(texto, clave)
        self.medidas = {m: campo_seccion(0.0005, 5.0) for m in ("D", "t", "d", "bf", "tw", "tf")}
        for m, v in {"D": 0.1143, "t": 0.00602, "d": 0.462, "bf": 0.192, "tw": 0.0105, "tf": 0.0177}.items():
            self.medidas[m].poner(v)
        self.nombre = QLineEdit()
        self.datos = QLabel()
        self.datos.setTextFormat(Qt.RichText)
        self.vista = VistaAcero()
        self.forma = QFormLayout()
        self.forma.addRow("Material", self.material)
        self.forma.addRow("Forma", self.forma_lista)
        for m, caja in self.medidas.items():
            self.forma.addRow(self.ETIQUETAS[m], caja)
            caja.cambiado.connect(self._actualizar)
        self.forma.addRow("Nombre", self.nombre)
        self.forma.addRow(self.datos)
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        diseno.addLayout(self.forma)
        diseno.addWidget(self.vista, 1)
        self.forma_lista.currentIndexChanged.connect(self._actualizar)
        self.material.currentIndexChanged.connect(self._actualizar)
        self.llenar_materiales()
        self._actualizar()

    def llenar_materiales(self):
        actual = self.material.currentData()
        self.material.blockSignals(True)
        self.material.clear()
        for mid, m in self.modelo.materiales.items():
            if cc.familia_material(m) == ac.FAMILIA:
                self.material.addItem(textos.nombre(m), mid)
        i = self.material.findData(actual)
        self.material.setCurrentIndex(i if i >= 0 else 0)
        self.material.blockSignals(False)

    def cargar(self, sec):
        s = sec.acero
        self.forma_lista.blockSignals(True)
        self.forma_lista.setCurrentIndex(self.forma_lista.findData(s.forma))
        self.forma_lista.blockSignals(False)
        for m in ac.MEDIDAS[s.forma]:
            self.medidas[m].poner(getattr(s, m))
        if self.material.findData(sec.material) >= 0:
            self.material.setCurrentIndex(self.material.findData(sec.material))
        self.nombre.setText("" if sec.nombre == ac.nombre_seccion(s) else sec.nombre)
        self._actualizar()

    def acero(self):
        forma = self.forma_lista.currentData()
        return Acero(forma=forma, **{m: self.medidas[m].valor() for m in ac.MEDIDAS[forma]})

    def valores(self):
        return {"material": self.material.currentData(), "acero": self.acero(), "nombre": self.nombre.text()}

    def error(self):
        if self.material.currentData() is None:
            return "Primero crea un material de acero"
        try:
            ac.propiedades(self.acero())
        except ValueError as e:
            return str(e)
        return None

    def refrescar(self):
        self.llenar_materiales()
        self._actualizar()

    def _actualizar(self, *_):
        forma = self.forma_lista.currentData()
        for m, caja in self.medidas.items():
            self.forma.setRowVisible(caja, m in ac.MEDIDAS[forma])
        error = self.error()
        if error is None:
            s = self.acero()
            a, iy, iz, j = ac.propiedades(s)
            self.nombre.setPlaceholderText(ac.nombre_seccion(s))
            self.datos.setText(f"A = {formato.cantidad(a, 'area')}<br>Iy = {formato.cantidad(iy, 'inercia')}"
                               f"<br>Iz = {formato.cantidad(iz, 'inercia')}<br>J = {formato.cantidad(j, 'inercia')}")
        else:
            self.datos.setText(f"<span style='color:{colores.INTERFAZ_DESHABILITADO}'>{error}</span>")
        self.vista.mostrar(self.acero())


FORMULARIOS = {
    ("material", "concreto"): FormularioConcreto,
    ("material", "acero"): FormularioAcero,
    ("material", "otros"): FormularioOtroMaterial,
    ("seccion", "concreto"): FormularioSeccion,
    ("seccion", "acero"): FormularioSeccionAcero,
    ("seccion", "otros"): FormularioOtraSeccion,
}
