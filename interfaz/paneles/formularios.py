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
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from configuracion import colores, formato
from interfaz import textos
from interfaz.paneles.comunes import CampoNumero, Lista
from modelo import interaccion as puente
from modelo import concreto as cc
from modelo.estructura import FY_DEFECTO, Concreto
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
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(colores.INTERFAZ_FONDO))
        c = self.concreto
        es_t = c is not None and c.forma == "T"
        if (c is None or c.forma not in ("rectangular", "T") or c.b <= 0 or c.h <= 0
                or (es_t and not (c.bf >= c.b and 0 < c.hf < c.h))):
            p.end()
            return
        margen = 34
        total = c.bf if es_t else c.b                     # ancho total (el ala, en la T)
        escala = min((self.width() - 2 * margen) / total, (self.height() - 2 * margen) / c.h)
        ancho, alto = total * escala, c.h * escala
        x0, y0 = (self.width() - ancho) / 2, (self.height() - alto) / 2
        centro_x, abajo = x0 + ancho / 2, y0 + alto        # eje de simetría y borde inferior, en pantalla
        zc = cc.centroide(c)
        p.setPen(QPen(QColor(colores.INTERFAZ_TEXTO), 1.5))
        p.setBrush(QColor(colores.INTERFAZ_HOVER))
        p.drawPolygon(QPolygonF([QPointF(centro_x + y * escala, abajo - (z + zc) * escala)
                                 for y, z in cc.contorno(c)]))
        con_barras = (c.nx >= 1 and 0 < c.d < min(c.b / 2, c.h - c.hf)) if es_t else \
                     (c.nx >= 1 and c.ny >= 1 and 0 < c.d < min(c.b, c.h) / 2)
        if con_barras:
            p.setBrush(QColor(colores.INTERFAZ_TEXTO))
            p.setPen(Qt.NoPen)
            for x, y, numero in posiciones_barras(c, con_numero=True):    # la T: abajo y arriba
                radio = max(diametro_barra(numero) * escala / 2, 2.0)
                p.drawEllipse(QPointF(centro_x + (x - c.b / 2) * escala, abajo - y * escala), radio, radio)
            if es_t and c.estribo and c.recubrimiento > 0:            # el estribo, en el alma (esquemático)
                r = c.recubrimiento
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(QColor(colores.INTERFAZ_TEXTO), max(diametro_barra(c.estribo) * escala, 1.0)))
                p.drawRect(QRectF(centro_x + (r - c.b / 2) * escala, abajo - (c.h - r) * escala,
                                  (c.b - 2 * r) * escala, (c.h - 2 * r) * escala))
        p.setPen(QPen(QColor(colores.INTERFAZ_DESHABILITADO), 1))
        p.drawText(QRectF(x0, y0 + alto + 4, ancho, margen - 8), Qt.AlignHCenter | Qt.AlignTop,
                   f"{'bw' if es_t else 'b'} = {formato.cantidad(c.b, 'seccion')}")
        if es_t:
            p.drawText(QRectF(x0, y0 - margen + 4, ancho, margen - 8), Qt.AlignHCenter | Qt.AlignBottom,
                       f"bf = {formato.cantidad(c.bf, 'seccion')}  ·  hf = {formato.cantidad(c.hf, 'seccion')}")
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
        self.gamma.setToolTip("Peso unitario para el peso propio y para Ec (es el wc de la Ec. 19.2.2.1.a).\n"
                              "Concreto reforzado: 150 lb/ft³ = 23.56 kN/m³ (ASCE 7-05, Tabla C3-2)")
        self.e, self.g = QLabel(), QLabel()
        self.fc.cambiado.connect(self._actualizar)
        self.gamma.cambiado.connect(self._actualizar)
        forma = QFormLayout(self)
        forma.setContentsMargins(0, 0, 0, 0)
        forma.addRow("Nombre", self.nombre)
        forma.addRow("f'c", self.fc)
        etiqueta_e = QLabel("E (ACI 318-19 §19.2.2.1)")
        etiqueta_e.setToolTip("Ec = wc^1.5·33·√f'c (psi), con wc = γ entre 90 y 160 lb/ft³ (Ec. 19.2.2.1.a);\n"
                              "fuera de ese rango, 57 000·√f'c (Ec. 19.2.2.1.b)")
        forma.addRow(etiqueta_e, self.e)
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
        e, g = cc.modulos(self.fc.valor(), self.gamma.valor())
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


def lista_barras(con_ninguna=None):
    """Lista de números de barra (#3 a #11). con_ninguna: el texto de la opción 0 ("Sin estribos"...)."""
    lista = Lista()
    if con_ninguna:
        lista.addItem(con_ninguna, 0)
    for n in BARRAS:
        lista.addItem(f"#{n}", n)
    return lista


class FormularioSeccionT(QWidget):
    """Sección T de concreto (vigas y viguetas con su losa): material, bw, h, bf, hf, recubrimiento
    libre, estribo (número y separación, o sin estribos), barras de abajo (número y cuántas), barras
    de arriba (número y cuántas; 0 = sin acero arriba) y fy; nombre, propiedades (con el centroide
    yb y los peraltes d+ y d−) y el dibujo debajo. d sale del recubrimiento, como en el SMath:
    d = rec + d_estribo + db/2. Sin diagrama de interacción ni aviso de cuantía (es de vigas)."""

    def __init__(self, modelo, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.material = Lista()
        self.bw, self.h, self.bf, self.hf = campo_seccion(), campo_seccion(), campo_seccion(), campo_seccion()
        self.rec = campo_seccion(0.005, 0.5)
        self.rec.setToolTip("Recubrimiento libre: del borde de concreto al estribo (o a la barra, sin estribos).\n"
                            "Viguetas no expuestas a la intemperie, #11 o menor: 3/4 in = 1.9 cm "
                            "(ACI 318-19 Tabla 20.5.1.3.1)")
        self.estribo = lista_barras("Sin estribos")
        self.s_estribo = campo_seccion(0.01, 2.0)
        self.s_estribo.setToolTip("Separación de los estribos a lo largo de la vigueta")
        self.barra = lista_barras()
        self.n = CampoNumero(minimo=1, maximo=30, entero=True)
        self.barra_sup = lista_barras()
        self.n_sup = CampoNumero(minimo=0, maximo=30, entero=True)
        self.n_sup.setToolTip("Barras de arriba (momento negativo, sobre los apoyos). 0 = sin acero arriba")
        self.fy = campo("esfuerzo", 100000, 1000000)
        self.fy.poner(FY_DEFECTO)
        self.nombre = QLabel()
        self.datos = QLabel()
        self.datos.setTextFormat(Qt.RichText)
        self.vista = VistaSeccion()
        forma = QFormLayout()
        forma.addRow("Material", self.material)
        forma.addRow("bw (alma, eje local y)", self.bw)
        forma.addRow("h (total, eje local z)", self.h)
        forma.addRow("bf (ancho del ala)", self.bf)
        forma.addRow("hf (espesor del ala)", self.hf)
        forma.addRow("Recubrimiento libre", self.rec)
        forma.addRow("Estribo", self.estribo)
        forma.addRow("Separación de estribos", self.s_estribo)
        forma.addRow("Barra abajo", self.barra)
        forma.addRow("Barras abajo", self.n)
        forma.addRow("Barra arriba", self.barra_sup)
        forma.addRow("Barras arriba", self.n_sup)
        forma.addRow("fy (acero)", self.fy)
        forma.addRow("Nombre", self.nombre)
        forma.addRow(self.datos)
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        diseno.addLayout(forma)
        diseno.addWidget(self.vista, 1)
        for caja in (self.bw, self.h, self.bf, self.hf, self.rec, self.s_estribo, self.n, self.n_sup, self.fy):
            caja.cambiado.connect(self._actualizar)
        for combo in (self.material, self.barra, self.barra_sup, self.estribo):
            combo.currentIndexChanged.connect(self._actualizar)
        self.llenar_materiales()
        # La vigueta de la tarea: 15 × 45, ala 50 × 10, rec 3/4 in, sin estribos, 1 #6 abajo y 2 #5 arriba
        self.cargar_concreto(cc.concreto_T(0.0, 0.15, 0.45, 0.50, 0.10, 0.0, 6, 1, barra_sup=5, n_sup=2,
                                           rec=0.75 * 0.0254), None)

    llenar_materiales = FormularioSeccion.llenar_materiales

    def cargar(self, sec):
        self.cargar_concreto(sec.concreto, sec.material)

    def cargar_concreto(self, c, material):
        combos = (self.barra, self.barra_sup, self.estribo, self.material)
        for combo in combos:
            combo.blockSignals(True)
        for caja, valor in ((self.bw, c.b), (self.h, c.h), (self.bf, c.bf), (self.hf, c.hf),
                            (self.rec, c.recubrimiento), (self.s_estribo, c.s_estribo or 0.20),
                            (self.n, c.nx), (self.n_sup, c.n_sup), (self.fy, c.fy)):
            caja.poner(valor)
        for combo, numero, defecto in ((self.barra, c.barra, 6), (self.barra_sup, c.barra_sup or 5, 5),
                                       (self.estribo, c.estribo, 0)):
            i = combo.findData(numero)
            combo.setCurrentIndex(i if i >= 0 else combo.findData(defecto))
        if material is not None and self.material.findData(material) >= 0:
            self.material.setCurrentIndex(self.material.findData(material))
        for combo in combos:
            combo.blockSignals(False)
        self._actualizar()

    def valores(self):
        """Lo escrito, en unidades internas. "d" (de abajo al centro de las barras de abajo) sale del
        recubrimiento."""
        estribo = self.estribo.currentData() or 0
        c = cc.concreto_T(0.0, self.bw.valor(), self.h.valor(), self.bf.valor(), self.hf.valor(), 0.0,
                          self.barra.currentData(), self.n.valor(), rec=self.rec.valor(), estribo=estribo,
                          s_estribo=self.s_estribo.valor() if estribo else 0.0)
        return {"material": self.material.currentData(), "bw": self.bw.valor(), "h": self.h.valor(),
                "bf": self.bf.valor(), "hf": self.hf.valor(), "d": c.d, "barra": self.barra.currentData(),
                "n": self.n.valor(), "fy": self.fy.valor(), "barra_sup": self.barra_sup.currentData(),
                "n_sup": self.n_sup.valor(), "rec": self.rec.valor(), "estribo": estribo,
                "s_estribo": c.s_estribo}

    @staticmethod
    def refuerzo(v):
        """Los datos extra de la T (para crear_seccion_T y las demás), desde valores()."""
        return {k: v[k] for k in ("barra_sup", "n_sup", "rec", "estribo", "s_estribo")}

    def concreto(self):
        v = self.valores()
        mat = self.modelo.materiales.get(v["material"])
        return cc.concreto_T(mat.fc if mat else 0.0, v["bw"], v["h"], v["bf"], v["hf"], v["d"], v["barra"],
                             v["n"], v["fy"], **self.refuerzo(v))

    def error(self):
        v = self.valores()
        if v["material"] is None:
            return "Primero crea un material de concreto"
        try:
            cc._validar_T(self.modelo, v["material"], self.concreto())
        except ValueError as e:
            return str(e)
        return None

    def refrescar(self):
        self.llenar_materiales()
        self._actualizar()

    def _actualizar(self, *_):
        v = self.valores()
        self.s_estribo.setEnabled(bool(v["estribo"]))
        self.barra_sup.setEnabled(v["n_sup"] > 0)
        self.nombre.setText(textos.nombre_T(v["bw"], v["h"], v["bf"], v["hf"], v["n"], v["barra"], v["fy"],
                                            v["barra_sup"] if v["n_sup"] else 0, v["n_sup"], v["estribo"],
                                            v["s_estribo"]))
        error = self.error()
        if error is None:
            c = self.concreto()
            a, iy, iz, j, yb = cc.propiedades_T(v["bw"], v["h"], v["bf"], v["hf"])
            arriba = (f"<br>As arriba = {formato.cantidad(cc.area_superior(c), 'area')}  ·  d− = "
                      f"{formato.cantidad(cc.peralte_negativo(c), 'seccion')}" if c.n_sup else "<br>Sin acero arriba")
            self.datos.setText(
                f"A = {formato.cantidad(a, 'area')}<br>yb = {formato.cantidad(yb, 'seccion')} (centroide, desde abajo)"
                f"<br>Iy = {formato.cantidad(iy, 'inercia')}<br>Iz = {formato.cantidad(iz, 'inercia')}"
                f"<br>J = {formato.cantidad(j, 'inercia')} (aproximada)"
                f"<br>As abajo = {formato.cantidad(cc.area_inferior(c), 'area')}  ·  d+ = "
                f"{formato.cantidad(cc.peralte_positivo(c), 'seccion')}{arriba}")
        else:
            self.datos.setText(f"<span style='color:{colores.INTERFAZ_DESHABILITADO}'>{error}</span>")
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


FORMULARIOS = {
    ("material", "concreto"): FormularioConcreto,
    ("material", "otros"): FormularioOtroMaterial,
    ("seccion", "concreto"): FormularioSeccion,
    ("seccion", "concreto", "T"): FormularioSeccionT,
    ("seccion", "otros"): FormularioOtraSeccion,
}
