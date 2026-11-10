"""Panel de Propiedades (derecha): los datos de lo seleccionado, en unidades de pantalla.

- Muestra un nodo, un apoyo, una barra, una carga, un material o una sección. Una sección se ve con
  su dibujo y, si es de concreto, con los botones Ver 2D y Ver 3D del diagrama de interacción.
- Con la herramienta Apoyo activa muestra, en cambio, el panel para elegir el tipo de apoyo; con
  Asignar sección, la sección que se asigna; con Carga en nodo o Carga en barra, el panel con los
  valores de la carga.
- Con un análisis hecho, un nodo (y su apoyo) muestra sus desplazamientos y su reacción. Los
  diagramas de una barra están en el panel Diagrama (abajo), no aquí.
- En una barra, la sección se elige de la lista y sus medidas (b, h, barra, Nx, Ny) se pueden
  cambiar: eso crea (o reutiliza) otra sección solo para esa barra. La ventana hace el cambio.
  Con editable=False (modo Combinaciones: solo se ven resultados) esos controles quedan en gris.
- Editar un material o una sección (desde el Explorador o la ventana Definir) muestra aquí su
  formulario, con Guardar y Cancelar.
- Sin nada seleccionado, el panel queda vacío.
- Sin barra de desplazamiento horizontal: la columna Valor se ajusta al ancho del panel y lo que no
  cabe termina en "…" (el texto completo sale al pasar el mouse).

PanelPropiedades es el contenido; Propiedades es el panel acoplable que lo contiene. Con una columna
de concreto con refuerzo seleccionada aparecen dos pestañas, Propiedades e Interacción (su diagrama
de interacción); con cualquier otra cosa no hay pestañas. La ventana Definir usa otro
PanelPropiedades a su derecha.
"""
import numpy as np
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDockWidget, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QRadioButton,
                               QScrollArea, QSizePolicy, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

from calculo.rigidez.barra import angulos
from configuracion import colores, formato
from configuracion import interfaz as ui
from configuracion.formato import FUERZAS, GDL_PANTALLA
from interfaz import textos
from interfaz.iconos import icono
from interfaz.paneles.comunes import CampoNumero
from interfaz.paneles.formularios import (BARRAS, FORMULARIOS, VistaSeccion, campo, campo_barras,
                                          campo_seccion)
from interfaz.textos import DIRECCION, UNIDAD_CARGA, donde, texto_carga
from interfaz.ventanas.interaccion import DiagramaInteraccion
from modelo import concreto as cc
from modelo import interaccion as puente
from modelo.analisis import carga_de_peso_propio
from modelo.apoyos import NOMBRES, TIPOS, describir, tipo_de
from modelo.estructura import CargaNodal


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


class PanelAsignar(QWidget):
    """Herramienta Asignar sección: qué sección se asigna (con su dibujo y su material).

    Cada clic sobre una barra le asigna esta sección y, con ella, su material. Las secciones se
    crean, editan y eliminan en Definir → Secciones."""
    cambiado = Signal(object)                  # ID de la sección elegida
    definir = Signal()                         # pedir la ventana de Secciones

    def __init__(self, parent=None):
        super().__init__(parent)
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        indicacion = QLabel("Elige la sección y haz clic sobre cada barra que la lleva "
                            "(se asigna también su material):")
        indicacion.setWordWrap(True)
        diseno.addWidget(indicacion)
        self.lista = QComboBox()
        self.lista.currentIndexChanged.connect(self._elegida)
        diseno.addWidget(self.lista)
        self.dibujo = VistaSeccion()
        self.dibujo.setFixedHeight(210)
        diseno.addWidget(self.dibujo)
        self.material = QLabel()
        self.material.setWordWrap(True)
        diseno.addWidget(self.material)
        self.vacio = QLabel("Todavía no hay secciones.")
        diseno.addWidget(self.vacio)
        boton = QPushButton("Definir secciones…")
        boton.setToolTip("Crear, editar o eliminar secciones (Definir → Secciones)")
        boton.clicked.connect(self.definir.emit)
        fila = QHBoxLayout()
        fila.addWidget(boton)
        fila.addStretch(1)
        diseno.addLayout(fila)
        diseno.addStretch(1)
        self._modelo = None

    def poner(self, modelo, sid):
        """Llena la lista con las secciones del modelo y marca sid, sin emitir `cambiado`."""
        self._modelo = modelo
        self.lista.blockSignals(True)
        self.lista.clear()
        for s, sec in modelo.secciones.items():
            self.lista.addItem(textos.nombre(sec, modelo), s)
        self.lista.setCurrentIndex(max(0, self.lista.findData(sid)))
        self.lista.blockSignals(False)
        hay = bool(modelo.secciones)
        self.lista.setVisible(hay)
        self.vacio.setVisible(not hay)
        self._dibujar()

    def _elegida(self, *_):
        self._dibujar()
        self.cambiado.emit(self.lista.currentData())

    def _dibujar(self):
        modelo = self._modelo
        sec = modelo.secciones.get(self.lista.currentData()) if modelo is not None else None
        c = sec.concreto if sec is not None else None
        self.dibujo.mostrar(c if c is not None and c.forma == "rectangular" else None)
        self.dibujo.setVisible(sec is not None)
        mat = modelo.materiales.get(sec.material) if sec is not None else None
        self.material.setText(f"Material: {textos.nombre(mat)}" if mat else "")


class PanelCargaNodo(QWidget):
    """Valores de la carga en nodo: fuerzas y momentos globales, y si se suman o reemplazan."""

    def __init__(self, parent=None):
        super().__init__(parent)
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        diseno.addWidget(QLabel("Clic sobre un nodo para cargarlo (ejes globales):"))
        rejilla = QGridLayout()
        self.campos = []
        for k, nombre in enumerate(FUERZAS):
            caja = campo("fuerza" if k < 3 else "momento", -1e9, 1e9)
            caja.poner(0.0)
            rejilla.addWidget(QLabel(nombre), k, 0)
            rejilla.addWidget(caja, k, 1)
            self.campos.append(caja)
        diseno.addLayout(rejilla)
        self.sumar = QRadioButton("Sumar a la que ya tiene")
        self.reemplazar = QRadioButton("Reemplazar la que tiene")
        self.reemplazar.setChecked(True)
        diseno.addWidget(self.sumar)
        diseno.addWidget(self.reemplazar)
        self.caso = QLabel()
        diseno.addWidget(self.caso)
        diseno.addStretch(1)

    def valores(self):
        return [c.valor() for c in self.campos]


class PanelCargaBarra(QWidget):
    """Valores de la carga en barra: tipo, valor, dirección, distancia a y sumar o reemplazar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        diseno.addWidget(QLabel("Clic sobre una barra para cargarla:"))
        rejilla = QGridLayout()
        self.tipo = QComboBox()
        for tipo, texto in (("uniforme", "Uniforme (en toda la barra)"), ("puntual", "Fuerza puntual"),
                            ("momento", "Momento concentrado")):
            self.tipo.addItem(texto, tipo)
        self.direccion = QComboBox()
        for d in ("Z", "X", "Y", "x", "y", "z"):
            self.direccion.addItem(DIRECCION[d], d)
        self.a = campo("longitud", 0.0, 1e4)
        self.a.poner(0.0)
        self._valor_fila = QLabel("Valor")
        self.valores_por_tipo = {}
        self.valor = None
        rejilla.addWidget(QLabel("Tipo"), 0, 0)
        rejilla.addWidget(self.tipo, 0, 1)
        rejilla.addWidget(self._valor_fila, 1, 0)
        rejilla.addWidget(QLabel("Dirección"), 2, 0)
        rejilla.addWidget(self.direccion, 2, 1)
        rejilla.addWidget(QLabel("a (desde el nodo i)"), 3, 0)
        rejilla.addWidget(self.a, 3, 1)
        self._rejilla = rejilla
        diseno.addLayout(rejilla)
        diseno.addWidget(QLabel("El signo da el sentido: Z global negativo es hacia abajo."))
        self.sumar = QRadioButton("Sumar a las que ya tiene")
        self.reemplazar = QRadioButton("Reemplazar las que tiene")
        self.sumar.setChecked(True)
        diseno.addWidget(self.sumar)
        diseno.addWidget(self.reemplazar)
        self.caso = QLabel()
        diseno.addWidget(self.caso)
        diseno.addStretch(1)
        self.tipo.currentIndexChanged.connect(self._cambio_tipo)
        self._cambio_tipo()

    def _cambio_tipo(self, *_):
        """El campo del valor cambia de unidad con el tipo (kN/m, kN o kN·m)."""
        tipo = self.tipo.currentData()
        if self.valor is not None:
            self.valores_por_tipo[self._tipo_actual] = self.valor.valor()
            self._rejilla.removeWidget(self.valor)
            self.valor.deleteLater()
        self.valor = campo(UNIDAD_CARGA[tipo], -1e9, 1e9)
        self.valor.poner(self.valores_por_tipo.get(tipo, -10.0))
        self._rejilla.addWidget(self.valor, 1, 1)
        self._tipo_actual = tipo
        self.a.setEnabled(tipo != "uniforme")

    def valores(self):
        """(tipo, valor, dirección, a) en unidades internas."""
        return self.tipo.currentData(), self.valor.valor(), self.direccion.currentData(), self.a.valor()


class PanelPropiedades(QWidget):
    ver_diagrama = Signal(int, str)            # ID de la sección y "2D" o "3D"
    asignar_seccion = Signal(int, object)      # ID de la barra y ID de la sección (o None)
    editar_seccion = Signal(int, object)       # ID de la barra y (material, b, h, d, barra, nx, ny)
    guardar_definicion = Signal(object)        # pedido: tipo, familia, modo, ident y valores
    cancelar_definicion = Signal()
    formulario_abierto = Signal()              # se abrió un formulario (Propiedades lo pone a la vista)

    def __init__(self, parent=None):
        super().__init__(parent)
        diseno = QVBoxLayout(self)
        self.titulo = QLabel()
        self.dibujo = VistaSeccion()               # el dibujo de una sección
        self.dibujo.setFixedHeight(210)
        self.arbol = QTreeWidget()
        self.arbol.setColumnCount(2)
        self.arbol.setHeaderLabels(["Propiedad", "Valor"])
        self.arbol.setIndentation(14)
        self.arbol.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.arbol.setTextElideMode(Qt.ElideRight)
        self.arbol.setSelectionMode(QAbstractItemView.NoSelection)    # solo lectura: no se marcan filas
        self.arbol.setFocusPolicy(Qt.NoFocus)
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
        self.panel_apoyo = PanelApoyo()
        self.panel_asignar = PanelAsignar()
        self.panel_carga_nodo = PanelCargaNodo()
        self.panel_carga_barra = PanelCargaBarra()
        self._crear_edicion()
        diseno.addWidget(self.titulo)
        diseno.addWidget(self.dibujo)
        diseno.addWidget(self.arbol, 1)
        for panel in (self.panel_apoyo, self.panel_asignar, self.panel_carga_nodo, self.panel_carga_barra,
                      self.edicion):
            diseno.addWidget(panel, 1)
        diseno.addWidget(self.botones)
        self._sid = None
        self._pedido = None
        self._formulario = None
        self._caso = self._rc = None
        self._vaciar()

    # ---------- Estados ----------
    def _vaciar(self):
        """Todo oculto: lo que se va a mostrar se vuelve a encender."""
        for w in (self.titulo, self.dibujo, self.arbol, self.panel_apoyo, self.panel_asignar,
                  self.panel_carga_nodo, self.panel_carga_barra, self.edicion, self.botones):
            w.hide()
        self.arbol.clear()
        self._sid = None

    def mostrar_panel_apoyo(self, tipo):
        """Lo usa la herramienta Apoyo: en vez de los datos, el panel para elegir el tipo."""
        self._vaciar()
        self.titulo.setText("Apoyo")
        self.titulo.show()
        self.panel_apoyo.poner(tipo)
        self.panel_apoyo.show()

    def mostrar_panel_asignar(self, modelo, sid):
        """Lo usa la herramienta Asignar sección: la sección que se asigna con cada clic."""
        self._vaciar()
        self.titulo.setText("Asignar sección")
        self.titulo.show()
        self.panel_asignar.poner(modelo, sid)
        self.panel_asignar.show()

    def mostrar_panel_carga(self, tipo, nombre_caso):
        """Lo usan las herramientas de carga: el panel con los valores ("nodo" o "barra")."""
        self._vaciar()
        self.titulo.setText("Carga en nodo" if tipo == "nodo" else "Carga en barra")
        self.titulo.show()
        panel = self.panel_carga_nodo if tipo == "nodo" else self.panel_carga_barra
        panel.caso.setText(f"Caso: {nombre_caso}")
        panel.show()

    def actualizar_unidades(self):
        """Las unidades cambiaron: los campos (paneles de carga, formulario abierto) muestran el
        mismo valor en las nuevas, y el formulario vuelve a escribir lo calculado."""
        for campo_ in self.findChildren(CampoNumero):
            campo_.actualizar_unidades()
        if self._formulario is not None and self.editando():
            self._formulario.refrescar()

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

    def _ver(self, titulo):
        self.titulo.setText(titulo)
        self.titulo.show()
        self.arbol.show()

    # ---------- Mostrar ----------
    def mostrar(self, modelo, item, caso=None, rc=None, editable=True):
        """item: ("nodo", id), ("apoyo", id), ("barra", id), ("carga", id), ("material", id),
        ("seccion", id) o None.

        caso: el caso activo, cuyas cargas se listan (None: no se listan, como en el modo
        Combinaciones); rc: los resultados que se muestran (de un caso o de una combinación), si hay
        análisis; editable: False deja en gris los controles que cambian el modelo."""
        self._vaciar()
        self._caso, self._rc = caso, rc
        tipo, ident = item if item else (None, None)
        if tipo == "nodo" and ident in modelo.nodos:
            self._nodo(modelo, ident)
        elif tipo == "apoyo" and ident in modelo.nodos and any(modelo.nodos[ident].apoyo):
            self._apoyo(modelo, ident)
        elif tipo == "barra" and ident in modelo.elementos:
            self._barra(modelo, ident, editable)
        elif tipo == "carga" and ident in modelo.cargas:
            self._carga(modelo, ident)
        elif tipo == "material" and ident in modelo.materiales:
            self._material(modelo, ident)
        elif tipo == "seccion" and ident in modelo.secciones:
            self._seccion(modelo, ident)
        self.arbol.resizeColumnToContents(0)

    def _nodo(self, modelo, nid):
        n = modelo.nodos[nid]
        self._ver(f"Nodo {nid}")
        g = self._grupo("Posición")
        for eje, valor in zip("XYZ", n.coords):
            self._fila(g, eje, formato.cantidad(valor, "longitud"))
        g = self._grupo("Apoyo")
        self._fila(g, "Tipo", describir(n.apoyo).capitalize())
        if tipo_de(n.apoyo) != "libre":
            for nombre, restringido in zip(GDL_PANTALLA, n.apoyo):
                self._fila(g, nombre, "restringido" if restringido else "libre")
        self._cargas(modelo, "nodo", nid)
        barras = modelo.elementos_conectados(nid)
        self._fila(self._grupo("Conexiones"), "Barras", ", ".join(map(str, barras)) or "ninguna")
        rc = self._rc
        if rc is not None and nid in rc.res.desplazamientos:
            g = self._grupo(f"Desplazamientos ({rc.nombre})")
            for k, (nombre, valor) in enumerate(zip(GDL_PANTALLA, rc.res.desplazamientos[nid])):
                self._fila(g, nombre, formato.cantidad(valor, "desplazamiento") if k < 3
                           else f"{formato.numero(valor, 6)} rad")
            self._reaccion(nid)

    def _reaccion(self, nid):
        rc = self._rc
        if rc is not None and nid in rc.res.reacciones:
            g = self._grupo(f"Reacción ({rc.nombre})")
            for k, (nombre, valor) in enumerate(zip(FUERZAS, rc.res.reacciones[nid])):
                self._fila(g, nombre, formato.cantidad(valor, "fuerza" if k < 3 else "momento"))

    def _apoyo(self, modelo, nid):
        """El apoyo de un nodo, como objeto aparte: se puede seleccionar y eliminar solo (Supr)."""
        n = modelo.nodos[nid]
        self._ver(f"Apoyo del nodo {nid}")
        g = self._grupo("Apoyo")
        self._fila(g, "Tipo", describir(n.apoyo).capitalize())
        for nombre, restringido in zip(GDL_PANTALLA, n.apoyo):
            self._fila(g, nombre, "restringido" if restringido else "libre")
        self._reaccion(nid)

    def _cargas(self, modelo, tipo, ident):
        """Las cargas del nodo o la barra en el caso activo (ninguna si se ve una combinación). En el
        caso de peso propio, la barra muestra el suyo, que es automático."""
        if self._caso is None or self._caso not in modelo.casos:
            return
        ids = modelo.cargas_en(tipo, ident, self._caso)
        propio = carga_de_peso_propio(modelo, ident, self._caso) if tipo == "barra" else None
        if ids or propio is not None:
            g = self._grupo(f"Cargas ({modelo.casos[self._caso].nombre})")
            if propio is not None:
                self._fila(g, "Peso propio (A·γ)", texto_carga(propio))
            for cid in ids:
                self._fila(g, f"Carga {cid}", texto_carga(modelo.cargas[cid]))

    def _carga(self, modelo, cid):
        c = modelo.cargas[cid]
        self._ver(f"Carga {cid}")
        g = self._grupo("Carga")
        self._fila(g, "Caso", modelo.casos[c.caso].nombre)
        self._fila(g, "En", donde(c))
        if isinstance(c, CargaNodal):
            for k, (nombre, valor) in enumerate(zip(FUERZAS, c.fuerzas)):
                self._fila(g, nombre, formato.cantidad(valor, "fuerza" if k < 3 else "momento"))
        else:
            self._fila(g, "Tipo", c.tipo)
            self._fila(g, "Valor", formato.cantidad(c.valor, UNIDAD_CARGA[c.tipo]))
            self._fila(g, "Dirección", DIRECCION[c.direccion])
            if c.tipo != "uniforme":
                self._fila(g, "a (desde el nodo i)", formato.cantidad(c.a, "longitud"))

    def _barra(self, modelo, eid, editable=True):
        el = modelo.elementos[eid]
        ni, nj = modelo.nodos[el.ni], modelo.nodos[el.nj]
        self._ver(f"Elemento {eid}")
        beta, gamma, largo = angulos(ni.coords, nj.coords)
        g = self._grupo("Geometría")
        self._fila(g, "Nodos", f"{el.ni} → {el.nj}")
        self._fila(g, "Longitud", formato.cantidad(largo, "longitud"))
        self._fila(g, "α (giro de la sección)", f"{el.alfa:g}°")
        self._fila(g, "β", f"{formato.numero(np.degrees(beta), 2)}°")      # sin "-0.00"
        self._fila(g, "γ", f"{formato.numero(np.degrees(gamma), 2)}°")
        if modelo.es_columna(eid):
            self._fila(g, "Tipo", "columna (vertical)")
        g = self._grupo("Material")
        if el.material is None:
            self._fila(g, "Material", "sin asignar")
        else:
            mat = modelo.materiales[el.material]
            self._fila(g, "Nombre", textos.nombre(mat))
            self._fila(g, "E", formato.cantidad(mat.e, "esfuerzo"))
            self._fila(g, "G", formato.cantidad(mat.g, "esfuerzo"))
        g = self._grupo("Sección")
        lista = QComboBox()
        lista.addItem("sin asignar", None)
        for sid, sec in modelo.secciones.items():
            lista.addItem(textos.nombre(sec, modelo), sid)
        lista.setCurrentIndex(max(0, lista.findData(el.seccion)))
        lista.currentIndexChanged.connect(
            lambda *_: self._despues(self.asignar_seccion, eid, lista.currentData()))
        lista.setEnabled(editable)
        self._fila_control(g, "Sección", lista)
        if el.seccion is None:
            self._cargas(modelo, "barra", eid)
            return
        sec = modelo.secciones[el.seccion]
        c = sec.concreto
        if c is not None and c.forma == "rectangular":
            self._medidas(g, eid, el, sec, editable)
        self._fila(g, "A", formato.cantidad(sec.a, "area"))
        for nombre in ("iy", "iz", "j"):
            self._fila(g, nombre.capitalize() if nombre != "j" else "J", formato.cantidad(getattr(sec, nombre), "inercia"))
        self._cargas(modelo, "barra", eid)

    def _medidas(self, g, eid, el, sec, editable=True):
        """b, h, barra, Nx y Ny editables. Cambiar uno pide otra sección para esta barra."""
        c = sec.concreto
        b, h = campo_seccion(), campo_seccion()
        b.poner(c.b)
        h.poner(c.h)
        barra = QComboBox()
        for n in BARRAS:
            barra.addItem(f"#{n}", n)
        barra.setCurrentIndex(max(0, barra.findData(c.barra)))
        nx, ny = campo_barras(), campo_barras()
        nx.poner(c.nx)
        ny.poner(c.ny)
        material = sec.material if sec.material is not None else el.material

        def cambio(*_):
            nuevos = (material, b.valor(), h.valor(), c.d, barra.currentData(), nx.valor(), ny.valor())
            actuales = (material, c.b, c.h, c.d, c.barra, c.nx, c.ny)
            if any(abs(x - y) > 1e-9 if isinstance(x, float) else x != y for x, y in zip(nuevos, actuales)):
                self._despues(self.editar_seccion, eid, nuevos)

        for nombre, caja in (("b", b), ("h", h), ("Barra", barra), ("Nx", nx), ("Ny", ny)):
            caja.setEnabled(editable)
            self._fila_control(g, nombre, caja)
        for caja in (b, h, nx, ny):
            caja.terminado.connect(cambio)
        barra.currentIndexChanged.connect(cambio)

    def _material(self, modelo, mid):
        mat = modelo.materiales[mid]
        familia = cc.familia_material(mat)
        self._ver(textos.nombre(mat))
        g = self._grupo("Material")
        self._fila(g, "Familia", cc.nombre_familia(familia))
        if familia == "concreto":
            self._fila(g, "f'c", formato.cantidad(mat.fc, "esfuerzo"))
        self._fila(g, "E", formato.cantidad(mat.e, "esfuerzo"))
        self._fila(g, "G", formato.cantidad(mat.g, "esfuerzo"))
        if familia == "concreto":
            self._fila(g, "ν", f"{cc.POISSON:g}")
        self._fila(g, "γ (peso propio)", formato.cantidad(mat.gamma, "peso_unitario"))
        barras, secciones = cc.uso_material(modelo, mid)
        g = self._grupo("Uso")
        self._fila(g, "Barras", ", ".join(map(str, barras)) or "ninguna")
        self._fila(g, "Secciones", ", ".join(textos.nombre(modelo.secciones[s], modelo) for s in secciones)
                   or "ninguna")

    def _seccion(self, modelo, sid):
        sec = modelo.secciones[sid]
        self._ver(textos.nombre(sec, modelo))
        c = sec.concreto
        if c is not None and c.forma == "rectangular":
            self.dibujo.mostrar(c)
            self.dibujo.show()
        g = self._grupo("Sección")
        self._fila(g, "Familia", cc.nombre_familia(cc.familia_seccion(sec)))
        mat = modelo.materiales.get(sec.material)
        self._fila(g, "Material", textos.nombre(mat) if mat else "sin material")
        self._fila(g, "A", formato.cantidad(sec.a, "area"))
        for nombre in ("iy", "iz", "j"):
            self._fila(g, nombre.capitalize() if nombre != "j" else "J", formato.cantidad(getattr(sec, nombre), "inercia"))
        self._fila(g, "Barras", ", ".join(map(str, cc.uso_seccion(modelo, sid))) or "ninguna")
        if c is None:
            return
        g = self._grupo("Concreto y refuerzo")
        if c.forma == "circular":
            self._fila(g, "Forma", "circular")
            self._fila(g, "D", formato.cantidad(c.D, "seccion"))
        else:
            self._fila(g, "Forma", "rectangular")
            self._fila(g, "b × h", f"{formato.cantidad(c.b, 'seccion', False)} × {formato.cantidad(c.h, 'seccion')}")
        self._fila(g, "d (al centro de las barras)", formato.cantidad(c.d, "seccion"))
        self._fila(g, "f'c", formato.cantidad(c.fc, "esfuerzo"))
        try:
            p = puente.propiedades(c)
        except ValueError as e:
            self._fila(g, "Datos inválidos", str(e))
            return
        self._fila(g, "Barras de refuerzo", f"{p['nbarras']} #{c.barra}")
        self._fila(g, "As", formato.cantidad(p["As_total"].to("m^2").magnitude, "area"))
        self._fila(g, "Cuantía ρ", f"{p['cuantia']:.2f} %")
        self._fila(g, "β1", f"{p['beta1']:.3f}")
        self._fila(g, "fy", formato.cantidad(p["fy"].to("kN/m^2").magnitude, "esfuerzo"))
        self._sid = sid
        self.botones.show()

    # ---------- Editar un material o una sección ----------
    def _crear_edicion(self):
        self.edicion = QWidget()
        diseno = QVBoxLayout(self.edicion)
        diseno.setContentsMargins(0, 0, 0, 0)
        self._desplazable = QScrollArea()
        self._desplazable.setWidgetResizable(True)
        self._desplazable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._desplazable.setFrameShape(QScrollArea.NoFrame)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet(f"color: {colores.INTERFAZ_DESHABILITADO};")
        guardar = QPushButton("Guardar")
        guardar.setDefault(True)
        guardar.clicked.connect(self._guardar)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.cancelar_definicion.emit)
        botones = QHBoxLayout()
        botones.addStretch(1)
        botones.addWidget(cancelar)
        botones.addWidget(guardar)
        diseno.addWidget(self._desplazable, 1)
        diseno.addWidget(self.error)
        diseno.addLayout(botones)

    def editar(self, modelo, pedido):
        """Muestra el formulario del pedido: {"tipo": "material"|"seccion", "familia": ...,
        "modo": "nuevo"|"editar"|"copiar", "ident": ID o None}."""
        self._vaciar()
        tipo, familia, modo, ident = pedido["tipo"], pedido["familia"], pedido["modo"], pedido["ident"]
        formulario = FORMULARIOS[(tipo, familia)](modelo)
        objeto = (modelo.materiales if tipo == "material" else modelo.secciones).get(ident)
        if objeto is not None:
            formulario.cargar(objeto)
            nombre = getattr(formulario, "nombre", None)
            # La copia de un nombre propio lleva "(copia)"; la de uno automático sigue automática
            if modo == "copiar" and isinstance(nombre, QLineEdit) and nombre.text():
                nombre.setText(f"{nombre.text()} (copia)")
        if modo == "editar":
            titulo = f"Editar: {textos.nombre(objeto, modelo)}"
        elif modo == "copiar":
            titulo = f"Copia de {textos.nombre(objeto, modelo)}"
        else:
            titulo = ("Nuevo material: " if tipo == "material" else "Nueva sección: ") + cc.nombre_familia(familia)
        self.titulo.setText(titulo)
        self.titulo.show()
        self._pedido, self._formulario = dict(pedido), formulario
        self._desplazable.setWidget(formulario)
        self.error.clear()
        self.edicion.show()
        self.formulario_abierto.emit()

    def editando(self):
        return self.edicion.isVisible()

    def mostrar_error(self, texto):
        self.error.setText(texto)

    def _guardar(self):
        error = self._formulario.error() if self._formulario else "Nada que guardar"
        if error:
            self.mostrar_error(error)
            return
        self.guardar_definicion.emit({**self._pedido, "valores": self._formulario.valores()})


class Propiedades(QDockWidget):
    """El panel acoplable de la derecha: un PanelPropiedades y, solo cuando aplica, la pestaña
    Interacción con el diagrama de interacción de la columna elegida (barra vertical de concreto con
    refuerzo), que se calcula al abrir la pestaña. Si no aplica, no hay pestañas a la vista."""

    def __init__(self, parent=None):
        super().__init__("Propiedades", parent)
        self.setObjectName("propiedades")
        self.panel = PanelPropiedades()
        self.interaccion = DiagramaInteraccion(con_modo=True, con_barra=False)
        # Que la pestaña no ensanche el panel al aparecer: toma el ancho que haya
        self.interaccion.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.pestanas = QTabWidget()
        self.pestanas.setDocumentMode(True)
        self.pestanas.addTab(self.panel, "Propiedades")
        self.pestanas.addTab(self.interaccion, "Interacción")
        self.pestanas.setTabToolTip(1, "Diagrama de interacción (flexocompresión) de la sección de la "
                                       "columna elegida. Solo para columnas de concreto con refuerzo")
        self.pestanas.setTabVisible(1, False)
        self.pestanas.tabBar().hide()              # una sola pestaña: no hace falta mostrarla
        self.pestanas.currentChanged.connect(lambda *_: self._ver_interaccion())
        self.setWidget(self.pestanas)
        self._columna = None                       # sección de la columna elegida, o None
        # Atajos al contenido (la ventana los usa como si fueran del panel acoplable)
        p = self.panel
        self.ver_diagrama, self.asignar_seccion, self.editar_seccion = p.ver_diagrama, p.asignar_seccion, p.editar_seccion
        self.guardar_definicion, self.cancelar_definicion = p.guardar_definicion, p.cancelar_definicion
        self.arbol, self.panel_apoyo, self.panel_asignar, self.titulo = p.arbol, p.panel_apoyo, p.panel_asignar, p.titulo
        p.formulario_abierto.connect(lambda: self._poner_columna(None))

    # ---------- Lo que se muestra (siempre en la pestaña Propiedades, salvo una columna) ----------
    def mostrar(self, modelo, item, caso=None, rc=None, editable=True):
        self.panel.mostrar(modelo, item, caso, rc, editable)
        self._poner_columna(self._seccion_columna(modelo, item))

    def mostrar_panel_apoyo(self, tipo):
        self.panel.mostrar_panel_apoyo(tipo)
        self._poner_columna(None)

    def mostrar_panel_asignar(self, modelo, sid):
        self.panel.mostrar_panel_asignar(modelo, sid)
        self._poner_columna(None)

    def mostrar_panel_carga(self, tipo, nombre_caso):
        self.panel.mostrar_panel_carga(tipo, nombre_caso)
        self._poner_columna(None)

    def editar(self, modelo, pedido):
        self.panel.editar(modelo, pedido)

    def actualizar_unidades(self):
        self.panel.actualizar_unidades()
        self.interaccion.refrescar()

    # ---------- Pestaña Interacción ----------
    @staticmethod
    def _seccion_columna(modelo, item):
        """La sección (de concreto, con refuerzo) si item es una columna; si no, None."""
        if not item or item[0] != "barra" or item[1] not in modelo.elementos:
            return None
        sec = modelo.secciones.get(modelo.elementos[item[1]].seccion)
        if sec is None or sec.concreto is None or not modelo.es_columna(item[1]):
            return None
        return sec

    def _poner_columna(self, seccion):
        """Con una columna (su sección), aparecen las pestañas; sin ella, solo se ve Propiedades."""
        self._columna = seccion
        hay = seccion is not None
        if not hay:
            self.pestanas.setCurrentIndex(0)
        self.pestanas.setTabVisible(1, hay)
        self.pestanas.tabBar().setVisible(hay)
        if hay:
            self._ver_interaccion()

    def _ver_interaccion(self):
        """Calcula (si hace falta) el diagrama, solo con la pestaña Interacción a la vista."""
        if self.pestanas.currentIndex() != 1 or self._columna is None:
            return
        try:
            self.interaccion.mostrar(self._columna)
        except ValueError as e:
            self.interaccion.mostrar_error(f"No se pudo calcular el diagrama: {e}")
