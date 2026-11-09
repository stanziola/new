"""Panel de Propiedades (derecha): los datos de lo seleccionado, en unidades de pantalla.

- Muestra un nodo, una barra o una sección; para las secciones de concreto, además, los botones
  Ver 2D y Ver 3D del diagrama de interacción.
- Con la herramienta Apoyo activa muestra, en cambio, el panel para elegir el tipo de apoyo.
- En una barra, la sección se elige de la lista y sus medidas (b, h, barra, Nx, Ny) se pueden
  cambiar: eso crea (o reutiliza) otra sección solo para esa barra. La ventana hace el cambio.
- Sin barra de desplazamiento horizontal: la columna Valor se ajusta al ancho del panel y lo que no
  cabe termina en "…" (el texto completo sale al pasar el mouse).
"""
import numpy as np
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDockWidget, QGridLayout, QHBoxLayout,
                               QHeaderView, QLabel, QPushButton, QRadioButton, QSpinBox, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from calculo.elemento import angulos
from configuracion import formato
from configuracion import interfaz as ui
from configuracion.formato import FUERZAS, GDL_PANTALLA
from interfaz import concreto as puente
from interfaz.apoyos import NOMBRES, TIPOS, describir, tipo_de
from interfaz.iconos import icono


class PanelApoyo(QWidget):
    """Elegir el tipo de apoyo. Las casillas de los ejes solo muestran lo que restringe cada tipo:
    no se marcan a mano, así solo se pueden asignar combinaciones con sentido."""
    cambiado = Signal(str)

    ICONOS = {"empotrado": "empotrado", "fijo": "apoyo_fijo", "libre": "libre"}

    def __init__(self, parent=None):
        super().__init__(parent)
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        diseno.addWidget(QLabel("Tipo de apoyo (clic sobre un nodo para asignarlo):"))
        self.grupo = QButtonGroup(self)
        self.opciones = {}
        for tipo in TIPOS:
            boton = QRadioButton(NOMBRES[tipo])
            boton.setIcon(icono(self.ICONOS[tipo]))
            boton.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
            boton.toggled.connect(lambda activo, t=tipo: activo and self._elegido(t))
            self.grupo.addButton(boton)
            self.opciones[tipo] = boton
            diseno.addWidget(boton)
        diseno.addWidget(QLabel("Restringe:"))
        rejilla = QGridLayout()
        self.casillas = []
        for k, nombre in enumerate(GDL_PANTALLA):
            casilla = QCheckBox(nombre)
            casilla.setEnabled(False)              # solo informa
            rejilla.addWidget(casilla, k // 3, k % 3)
            self.casillas.append(casilla)
        diseno.addLayout(rejilla)
        diseno.addStretch(1)

    def poner(self, tipo):
        """Marca un tipo sin emitir `cambiado`."""
        self.blockSignals(True)
        self.opciones[tipo].setChecked(True)
        self._mostrar_casillas(tipo)
        self.blockSignals(False)

    def _mostrar_casillas(self, tipo):
        for casilla, restringido in zip(self.casillas, TIPOS[tipo]):
            casilla.setChecked(restringido)

    def _elegido(self, tipo):
        self._mostrar_casillas(tipo)
        self.cambiado.emit(tipo)


class Propiedades(QDockWidget):
    ver_diagrama = Signal(int, str)            # ID de la sección y "2D" o "3D"
    asignar_seccion = Signal(int, object)      # ID de la barra y ID de la sección (o None)
    editar_seccion = Signal(int, object)       # ID de la barra y (material, b, h, d, barra, nx, ny)

    def __init__(self, parent=None):
        super().__init__("Propiedades", parent)
        self.setObjectName("propiedades")
        contenido = QWidget()
        diseno = QVBoxLayout(contenido)
        self.titulo = QLabel("Nada seleccionado")
        self.arbol = QTreeWidget()
        self.arbol.setColumnCount(2)
        self.arbol.setHeaderLabels(["Propiedad", "Valor"])
        self.arbol.setIndentation(14)
        self.arbol.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.arbol.setTextElideMode(Qt.ElideRight)
        cabecera = self.arbol.header()
        cabecera.setStretchLastSection(True)
        cabecera.setSectionResizeMode(0, QHeaderView.Interactive)
        self.botones = QWidget()
        fila = QHBoxLayout(self.botones)
        fila.setContentsMargins(0, 0, 0, 0)
        for modo in ("2D", "3D"):
            boton = QPushButton(f"Ver {modo}")
            boton.setToolTip(f"Calcula y dibuja el diagrama de interacción {modo}")
            boton.clicked.connect(lambda *_, m=modo: self.ver_diagrama.emit(self._sid, m))
            fila.addWidget(boton)
        self.botones.hide()
        self.panel_apoyo = PanelApoyo()
        self.panel_apoyo.hide()
        diseno.addWidget(self.titulo)
        diseno.addWidget(self.arbol, 1)
        diseno.addWidget(self.panel_apoyo, 1)
        diseno.addWidget(self.botones)
        self.setWidget(contenido)
        self._sid = None

    # ---------- Panel de apoyo ----------
    def mostrar_panel_apoyo(self, tipo):
        """Lo usa la herramienta Apoyo: en vez de los datos, el panel para elegir el tipo."""
        self.titulo.setText("Apoyo")
        self.arbol.hide()
        self.botones.hide()
        self.panel_apoyo.poner(tipo)
        self.panel_apoyo.show()

    # ---------- Ayudas ----------
    def _grupo(self, nombre):
        item = QTreeWidgetItem(self.arbol, [nombre])
        item.setFirstColumnSpanned(True)
        item.setExpanded(True)
        return item

    @staticmethod
    def _fila(padre, nombre, valor):
        item = QTreeWidgetItem(padre, [nombre, valor])
        item.setToolTip(1, valor)               # el texto completo, si no cabe

    def _fila_control(self, padre, nombre, control):
        item = QTreeWidgetItem(padre, [nombre, ""])
        self.arbol.setItemWidget(item, 1, control)
        return control

    @staticmethod
    def _despues(senal, *args):
        """Emite la señal al volver al ciclo de eventos: el panel se rearma después del cambio, y no
        se puede borrar un control mientras todavía está atendiendo su propia señal."""
        QTimer.singleShot(0, lambda: senal.emit(*args))

    # ---------- Mostrar ----------
    def mostrar(self, modelo, item):
        """item: ("nodo", id), ("barra", id), ("seccion", id) o None."""
        self.panel_apoyo.hide()
        self.arbol.show()
        self.arbol.clear()
        self.botones.hide()
        self._sid = None
        tipo, ident = item if item else (None, None)
        if tipo == "nodo" and ident in modelo.nodos:
            self._nodo(modelo, ident)
        elif tipo == "barra" and ident in modelo.elementos:
            self._barra(modelo, ident)
        elif tipo == "seccion" and ident in modelo.secciones:
            self._seccion(modelo, ident)
        else:
            self.titulo.setText("Nada seleccionado")
        self.arbol.resizeColumnToContents(0)

    def _nodo(self, modelo, nid):
        n = modelo.nodos[nid]
        self.titulo.setText(f"Nodo {nid}")
        g = self._grupo("Posición")
        for eje, valor in zip("XYZ", n.coords):
            self._fila(g, eje, formato.cantidad(valor, "longitud"))
        g = self._grupo("Apoyo")
        self._fila(g, "Tipo", describir(n.apoyo).capitalize())
        if tipo_de(n.apoyo) != "libre":
            for nombre, restringido in zip(GDL_PANTALLA, n.apoyo):
                self._fila(g, nombre, "restringido" if restringido else "libre")
        if any(n.carga):
            g = self._grupo("Cargas")
            for nombre, valor in zip(FUERZAS, n.carga):
                if valor:
                    self._fila(g, nombre, formato.cantidad(valor, "fuerza" if nombre[0] == "F" else "momento"))
        barras = modelo.elementos_conectados(nid)
        self._fila(self._grupo("Conexiones"), "Barras", ", ".join(map(str, barras)) or "ninguna")

    def _barra(self, modelo, eid):
        el = modelo.elementos[eid]
        ni, nj = modelo.nodos[el.ni], modelo.nodos[el.nj]
        self.titulo.setText(f"Elemento {eid}")
        beta, gamma, largo = angulos(ni.coords, nj.coords)
        g = self._grupo("Geometría")
        self._fila(g, "Nodos", f"{el.ni} → {el.nj}")
        self._fila(g, "Longitud", formato.cantidad(largo, "longitud"))
        self._fila(g, "α (giro de la sección)", f"{el.alfa:g}°")
        self._fila(g, "β", f"{formato.numero(np.degrees(beta), 2)}°")      # sin "-0.00"
        self._fila(g, "γ", f"{formato.numero(np.degrees(gamma), 2)}°")
        g = self._grupo("Material")
        if el.material is None:
            self._fila(g, "Material", "sin asignar")
        else:
            mat = modelo.materiales[el.material]
            self._fila(g, "Nombre", mat.nombre)
            self._fila(g, "E", formato.cantidad(mat.e, "esfuerzo"))
            self._fila(g, "G", formato.cantidad(mat.g, "esfuerzo"))
        g = self._grupo("Sección")
        lista = QComboBox()
        lista.addItem("sin asignar", None)
        for sid, sec in modelo.secciones.items():
            lista.addItem(sec.nombre, sid)
        lista.setCurrentIndex(max(0, lista.findData(el.seccion)))
        lista.currentIndexChanged.connect(
            lambda *_: self._despues(self.asignar_seccion, eid, lista.currentData()))
        self._fila_control(g, "Sección", lista)
        if el.seccion is None:
            return
        sec = modelo.secciones[el.seccion]
        c = sec.concreto
        if c is not None and c.forma == "rectangular":
            self._medidas(g, eid, el, sec)
        self._fila(g, "A", formato.cantidad(sec.a, "area"))
        for nombre in ("iy", "iz", "j"):
            self._fila(g, nombre.capitalize() if nombre != "j" else "J", formato.cantidad(getattr(sec, nombre), "inercia"))

    def _medidas(self, g, eid, el, sec):
        """b, h, barra, Nx y Ny editables. Cambiar uno pide otra sección para esta barra."""
        from interfaz.definir import BARRAS, _campo_longitud, _metros, _poner_metros
        c = sec.concreto
        b, h = _campo_longitud(), _campo_longitud()
        _poner_metros(b, c.b)
        _poner_metros(h, c.h)
        barra = QComboBox()
        for n in BARRAS:
            barra.addItem(f"#{n}", n)
        barra.setCurrentIndex(max(0, barra.findData(c.barra)))
        nx, ny = QSpinBox(), QSpinBox()
        for campo, valor in ((nx, c.nx), (ny, c.ny)):
            campo.setRange(2, 30)
            campo.setValue(valor)
        material = sec.material if sec.material is not None else el.material

        def cambio(*_):
            nuevos = (material, _metros(b), _metros(h), c.d, barra.currentData(), nx.value(), ny.value())
            actuales = (material, c.b, c.h, c.d, c.barra, c.nx, c.ny)
            if any(abs(x - y) > 1e-9 if isinstance(x, float) else x != y for x, y in zip(nuevos, actuales)):
                self._despues(self.editar_seccion, eid, nuevos)

        for nombre, campo in (("b", b), ("h", h), ("Barra", barra), ("Nx", nx), ("Ny", ny)):
            self._fila_control(g, nombre, campo)
        for campo in (b, h, nx, ny):
            campo.editingFinished.connect(cambio)
        barra.currentIndexChanged.connect(cambio)

    def _datos_seccion(self, g, sec):
        self._fila(g, "Nombre", sec.nombre)
        self._fila(g, "A", formato.cantidad(sec.a, "area"))
        for nombre in ("iy", "iz", "j"):
            self._fila(g, nombre.capitalize() if nombre != "j" else "J", formato.cantidad(getattr(sec, nombre), "inercia"))

    def _seccion(self, modelo, sid):
        sec = modelo.secciones[sid]
        self.titulo.setText(f"Sección {sid}: {sec.nombre}")
        self._datos_seccion(self._grupo("Propiedades"), sec)
        c = sec.concreto
        if c is None:
            return
        g = self._grupo("Concreto y refuerzo")
        if c.forma == "circular":
            self._fila(g, "Forma", "circular")
            self._fila(g, "D", formato.cantidad(c.D, "longitud"))
        else:
            self._fila(g, "Forma", "rectangular")
            self._fila(g, "b × h", f"{formato.cantidad(c.b, 'longitud', False)} × {formato.cantidad(c.h, 'longitud')}")
        self._fila(g, "d (al centro de las barras)", formato.cantidad(c.d, "longitud"))
        self._fila(g, "f'c", formato.cantidad(c.fc, "esfuerzo"))
        try:
            p = puente.propiedades(c)
        except ValueError as e:
            self._fila(g, "Datos inválidos", str(e))
            return
        self._fila(g, "Barras", f"{p['nbarras']} #{c.barra}")
        self._fila(g, "As", formato.cantidad(p["As_total"].to("m^2").magnitude, "area"))
        self._fila(g, "Cuantía ρ", f"{p['cuantia']:.2f} %")
        self._fila(g, "β1", f"{p['beta1']:.3f}")
        self._fila(g, "fy", formato.cantidad(p["fy"].to("kN/m^2").magnitude, "esfuerzo"))
        self._sid = sid
        self.botones.show()
