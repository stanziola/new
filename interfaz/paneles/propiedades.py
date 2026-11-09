"""Panel de Propiedades (derecha): los datos de lo seleccionado, en unidades de pantalla.

- Muestra un nodo, una barra, un material o una sección. Una sección se ve con su dibujo y, si es
  de concreto, con los botones Ver 2D y Ver 3D del diagrama de interacción.
- Con la herramienta Apoyo activa muestra, en cambio, el panel para elegir el tipo de apoyo; con
  Carga en nodo o Carga en barra, el panel con los valores de la carga.
- Con un análisis hecho, un nodo muestra sus desplazamientos y su reacción, y una barra sus fuerzas
  extremas y el gráfico 2D del diagrama activo.
- En una barra, la sección se elige de la lista y sus medidas (b, h, barra, Nx, Ny) se pueden
  cambiar: eso crea (o reutiliza) otra sección solo para esa barra. La ventana hace el cambio.
- Editar un material o una sección (desde el Explorador o la ventana Definir) muestra aquí su
  formulario, con Guardar y Cancelar.
- Sin nada seleccionado, el panel queda vacío.
- Sin barra de desplazamiento horizontal: la columna Valor se ajusta al ancho del panel y lo que no
  cabe termina en "…" (el texto completo sale al pasar el mouse).

PanelPropiedades es el contenido; Propiedades es el panel acoplable que lo contiene. La ventana
Definir usa otro PanelPropiedades a su derecha.
"""
import numpy as np
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDockWidget, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QRadioButton,
                               QScrollArea, QSpinBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

from calculo.rigidez.barra import angulos
from configuracion import colores, formato
from configuracion import interfaz as ui
from configuracion.formato import FUERZAS, GDL_PANTALLA
from interfaz.paneles.formularios import campo
from interfaz.textos import DIRECCION, UNIDAD_CARGA, donde, texto_carga
from modelo.estructura import CargaNodal
from modelo import interaccion as puente
from modelo.apoyos import NOMBRES, TIPOS, describir, tipo_de
from interfaz.paneles.formularios import BARRAS, FORMULARIOS, VistaSeccion, campo_longitud, leer, poner
from interfaz.iconos import icono
from modelo import concreto as cc


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
            caja.setValue(0.0)
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
        return [leer(c) for c in self.campos]


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
            self.valores_por_tipo[self._tipo_actual] = leer(self.valor)
            self._rejilla.removeWidget(self.valor)
            self.valor.deleteLater()
        self.valor = campo(UNIDAD_CARGA[tipo], -1e9, 1e9)
        poner(self.valor, self.valores_por_tipo.get(tipo, -10.0))
        self._rejilla.addWidget(self.valor, 1, 1)
        self._tipo_actual = tipo
        self.a.setEnabled(tipo != "uniforme")

    def valores(self):
        """(tipo, valor, dirección, a) en unidades internas."""
        return self.tipo.currentData(), leer(self.valor), self.direccion.currentData(), leer(self.a)


class PanelPropiedades(QWidget):
    ver_diagrama = Signal(int, str)            # ID de la sección y "2D" o "3D"
    asignar_seccion = Signal(int, object)      # ID de la barra y ID de la sección (o None)
    editar_seccion = Signal(int, object)       # ID de la barra y (material, b, h, d, barra, nx, ny)
    guardar_definicion = Signal(object)        # pedido: tipo, familia, modo, ident y valores
    cancelar_definicion = Signal()

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
        self.panel_carga_nodo = PanelCargaNodo()
        self.panel_carga_barra = PanelCargaBarra()
        self.grafico = None                        # gráfico 2D del diagrama (se crea al usarlo)
        self._crear_edicion()
        diseno.addWidget(self.titulo)
        diseno.addWidget(self.dibujo)
        diseno.addWidget(self.arbol, 1)
        diseno.addWidget(self.panel_apoyo, 1)
        diseno.addWidget(self.panel_carga_nodo, 1)
        diseno.addWidget(self.panel_carga_barra, 1)
        diseno.addWidget(self.edicion, 1)
        self._diseno = diseno
        diseno.addWidget(self.botones)
        self._sid = None
        self._pedido = None
        self._formulario = None
        self._vaciar()

    # ---------- Estados ----------
    def _vaciar(self):
        """Todo oculto: lo que se va a mostrar se vuelve a encender."""
        for w in (self.titulo, self.dibujo, self.arbol, self.panel_apoyo, self.panel_carga_nodo,
                  self.panel_carga_barra, self.edicion, self.botones, self.grafico):
            if w is not None:
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

    def mostrar_panel_carga(self, tipo, nombre_caso):
        """Lo usan las herramientas de carga: el panel con los valores ("nodo" o "barra")."""
        self._vaciar()
        self.titulo.setText("Carga en nodo" if tipo == "nodo" else "Carga en barra")
        self.titulo.show()
        panel = self.panel_carga_nodo if tipo == "nodo" else self.panel_carga_barra
        panel.caso.setText(f"Caso: {nombre_caso}")
        panel.show()

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
    def mostrar(self, modelo, item, caso=None, rc=None, componente=None):
        """item: ("nodo", id), ("barra", id), ("carga", id), ("material", id), ("seccion", id) o None.

        caso: el caso activo (sus cargas se muestran); rc: sus resultados, si hay análisis;
        componente: el diagrama activo ("N", "Vy"...), para el gráfico de una barra."""
        self._vaciar()
        self._caso, self._rc, self._componente = caso, rc, componente
        tipo, ident = item if item else (None, None)
        if tipo == "nodo" and ident in modelo.nodos:
            self._nodo(modelo, ident)
        elif tipo == "barra" and ident in modelo.elementos:
            self._barra(modelo, ident)
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
            g = self._grupo(f"Desplazamientos ({modelo.casos[rc.caso].nombre})")
            for k, (nombre, valor) in enumerate(zip(GDL_PANTALLA, rc.res.desplazamientos[nid])):
                self._fila(g, nombre, formato.cantidad(valor, "longitud") if k < 3 else f"{formato.numero(valor, 6)} rad")
            if nid in rc.res.reacciones:
                g = self._grupo(f"Reacción ({modelo.casos[rc.caso].nombre})")
                for k, (nombre, valor) in enumerate(zip(FUERZAS, rc.res.reacciones[nid])):
                    self._fila(g, nombre, formato.cantidad(valor, "fuerza" if k < 3 else "momento"))

    def _cargas(self, modelo, tipo, ident):
        """Las cargas del nodo o la barra en el caso activo."""
        caso = self._caso if self._caso is not None else modelo.caso_inicial()
        ids = modelo.cargas_en(tipo, ident, caso)
        if ids:
            g = self._grupo(f"Cargas ({modelo.casos[caso].nombre})")
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

    def _barra(self, modelo, eid):
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
        self._cargas(modelo, "barra", eid)
        self._resultados_barra(modelo, eid)

    def _resultados_barra(self, modelo, eid):
        """Máximos y mínimos de N, V, T y M a lo largo de la barra, y el gráfico del diagrama activo."""
        rc = self._rc
        if rc is None or eid not in rc.res.fuerzas:
            return
        from modelo.analisis import fuerzas_en
        d = fuerzas_en(modelo, rc, eid)
        g = self._grupo(f"Fuerzas internas ({modelo.casos[rc.caso].nombre})")
        for comp in ("N", "Vy", "Vz", "T", "My", "Mz"):
            magnitud = "fuerza" if comp in ("N", "Vy", "Vz") else "momento"
            self._fila(g, f"{comp} mín / máx", f"{formato.cantidad(d[comp].min(), magnitud, False)} / "
                                                f"{formato.cantidad(d[comp].max(), magnitud)}")
        self._graficar(d, self._componente if self._componente in d else "My")

    def _graficar(self, d, comp):
        """Gráfico 2D del diagrama de la barra (x en el eje horizontal, el valor en el vertical)."""
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        from configuracion import unidades
        if self.grafico is None:
            self.grafico = FigureCanvasQTAgg(Figure(figsize=(3.2, 2.2), tight_layout=True))
            self.grafico.setMinimumHeight(190)
            self._diseno.insertWidget(self._diseno.indexOf(self.botones), self.grafico)
        magnitud = "fuerza" if comp in ("N", "Vy", "Vz") else "momento"
        x = d["x"] / unidades.factor("longitud")
        y = d[comp] / unidades.factor(magnitud)
        fig = self.grafico.figure
        fig.clear()
        ax = fig.add_subplot(111)
        ax.plot(x, y, color=colores.DIAGRAMA_BORDE, linewidth=1)
        ax.fill_between(x, y, 0, where=y >= 0, color=colores.DIAGRAMA_POSITIVO, alpha=0.8, interpolate=True)
        ax.fill_between(x, y, 0, where=y < 0, color=colores.DIAGRAMA_NEGATIVO, alpha=0.8, interpolate=True)
        ax.axhline(0, color=colores.INTERFAZ_DESHABILITADO, linewidth=0.8)
        ax.set_xlabel(f"x ({unidades.simbolo('longitud')})", fontsize=8)
        ax.set_ylabel(f"{comp} ({unidades.simbolo(magnitud)})", fontsize=8)
        ax.tick_params(labelsize=7)
        self.grafico.draw()
        self.grafico.show()

    def _medidas(self, g, eid, el, sec):
        """b, h, barra, Nx y Ny editables. Cambiar uno pide otra sección para esta barra."""
        c = sec.concreto
        b, h = campo_longitud(), campo_longitud()
        poner(b, c.b)
        poner(h, c.h)
        barra = QComboBox()
        for n in BARRAS:
            barra.addItem(f"#{n}", n)
        barra.setCurrentIndex(max(0, barra.findData(c.barra)))
        nx, ny = QSpinBox(), QSpinBox()
        for caja, valor in ((nx, c.nx), (ny, c.ny)):
            caja.setRange(2, 30)
            caja.setValue(valor)
        material = sec.material if sec.material is not None else el.material

        def cambio(*_):
            nuevos = (material, leer(b), leer(h), c.d, barra.currentData(), nx.value(), ny.value())
            actuales = (material, c.b, c.h, c.d, c.barra, c.nx, c.ny)
            if any(abs(x - y) > 1e-9 if isinstance(x, float) else x != y for x, y in zip(nuevos, actuales)):
                self._despues(self.editar_seccion, eid, nuevos)

        for nombre, caja in (("b", b), ("h", h), ("Barra", barra), ("Nx", nx), ("Ny", ny)):
            self._fila_control(g, nombre, caja)
        for caja in (b, h, nx, ny):
            caja.editingFinished.connect(cambio)
        barra.currentIndexChanged.connect(cambio)

    def _material(self, modelo, mid):
        mat = modelo.materiales[mid]
        familia = cc.familia_material(mat)
        self._ver(mat.nombre)
        g = self._grupo("Material")
        self._fila(g, "Familia", cc.nombre_familia(familia))
        if familia == "concreto":
            self._fila(g, "f'c", formato.cantidad(mat.fc, "esfuerzo"))
        self._fila(g, "E", formato.cantidad(mat.e, "esfuerzo"))
        self._fila(g, "G", formato.cantidad(mat.g, "esfuerzo"))
        if familia == "concreto":
            self._fila(g, "ν", f"{cc.POISSON:g}")
        self._fila(g, "γ (peso propio)", f"{formato.numero(mat.gamma, 2)} kN/m³")
        barras, secciones = cc.uso_material(modelo, mid)
        g = self._grupo("Uso")
        self._fila(g, "Barras", ", ".join(map(str, barras)) or "ninguna")
        self._fila(g, "Secciones", ", ".join(modelo.secciones[s].nombre for s in secciones) or "ninguna")

    def _seccion(self, modelo, sid):
        sec = modelo.secciones[sid]
        self._ver(sec.nombre)
        c = sec.concreto
        if c is not None and c.forma == "rectangular":
            self.dibujo.mostrar(c)
            self.dibujo.show()
        g = self._grupo("Sección")
        self._fila(g, "Familia", cc.nombre_familia(cc.familia_seccion(sec)))
        mat = modelo.materiales.get(sec.material)
        self._fila(g, "Material", mat.nombre if mat else "sin material")
        self._fila(g, "A", formato.cantidad(sec.a, "area"))
        for nombre in ("iy", "iz", "j"):
            self._fila(g, nombre.capitalize() if nombre != "j" else "J", formato.cantidad(getattr(sec, nombre), "inercia"))
        self._fila(g, "Barras", ", ".join(map(str, cc.uso_seccion(modelo, sid))) or "ninguna")
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
            if modo == "copiar" and isinstance(getattr(formulario, "nombre", None), QLineEdit):
                formulario.nombre.setText(f"{objeto.nombre} (copia)")      # el de concreto es automático
                formulario._nombre_propio = True
        if modo == "editar":
            titulo = f"Editar: {objeto.nombre}"
        elif modo == "copiar":
            titulo = f"Copia de {objeto.nombre}"
        else:
            titulo = ("Nuevo material: " if tipo == "material" else "Nueva sección: ") + cc.nombre_familia(familia)
        self.titulo.setText(titulo)
        self.titulo.show()
        self._pedido, self._formulario = dict(pedido), formulario
        self._desplazable.setWidget(formulario)
        self.error.clear()
        self.edicion.show()

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
    """El panel acoplable de la derecha, con un PanelPropiedades adentro."""

    def __init__(self, parent=None):
        super().__init__("Propiedades", parent)
        self.setObjectName("propiedades")
        self.panel = PanelPropiedades()
        self.setWidget(self.panel)
        # Atajos al contenido (la ventana los usa como si fueran del panel acoplable)
        p = self.panel
        self.ver_diagrama, self.asignar_seccion, self.editar_seccion = p.ver_diagrama, p.asignar_seccion, p.editar_seccion
        self.guardar_definicion, self.cancelar_definicion = p.guardar_definicion, p.cancelar_definicion
        self.mostrar, self.mostrar_panel_apoyo, self.editar = p.mostrar, p.mostrar_panel_apoyo, p.editar
        self.mostrar_panel_carga = p.mostrar_panel_carga
        self.arbol, self.panel_apoyo, self.titulo = p.arbol, p.panel_apoyo, p.titulo
