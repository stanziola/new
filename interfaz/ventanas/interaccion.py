"""Diagramas de interacción (2D y 3D) dentro de Qt.

- DiagramaInteraccion: el dibujo con sus controles (2D o 3D, θ y, si hay, la tabla de puntos Pu–Mu).
  Lo usan la ventana aparte (Ver 2D y Ver 3D de una sección) y la pestaña Interacción de Propiedades
  (columnas).
- VentanaDiagrama: una ventana con un DiagramaInteraccion.
El cálculo está en calculo/interaccion (sagrado); aquí solo se dibuja, en unidades de pantalla.
El 2D se dibuja con matplotlib; el 3D, con VTK (interfaz/vista3d/superficie.py), que se crea la
primera vez que se pide.

Se calcula solo cuando se pide (Ver 2D, Ver 3D o al abrir la pestaña) y lo calculado se guarda en
unidades internas: si cambian las unidades solo se vuelve a dibujar, y lo ya calculado de la misma
sección no se recalcula.

Puntos Pu–Mu (solo en la pestaña de una columna, con resultados a la vista): uno por combinación y
por extremo de la columna (modelo/analisis.demandas_columna), listados en una tabla. Una columna de
un pórtico 3D tiene momento en sus dos ejes a la vez, así que cada punto se compara con el corte de
la superficie en la dirección de SU momento:
- 2D: P contra el momento resultante √(My² + Mz²), con la curva de la dirección del punto elegido
  en la tabla. Los puntos con esa misma dirección van rellenos; los demás, huecos (su curva es otra);
- 3D: todos los puntos en su lugar, (Mz, My, P), frente a la superficie.
Sin puntos, el 2D es el de siempre: la curva con la fibra más comprimida hacia θ.
"""
import math
from dataclasses import astuple

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView, QLabel, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from configuracion import colores, formato, unidades
from interfaz import textos
from interfaz.paneles.comunes import CampoNumero, Lista
from modelo import interaccion as concreto

MARCADOR = {"inferior": "v", "superior": "^", "tramo": "o"}     # cómo se dibuja cada punto en el 2D
MISMA_DIRECCION = math.radians(1.0)     # hasta aquí, dos momentos "van en la misma dirección"
AYUDA_THETA = ("θ: dirección de la fibra más comprimida, en el plano de la sección (0° = hacia b, 90° = hacia h). "
               "No es la dirección del momento resultante, salvo en 0°, 90°, 180° y 270°")


def _plegada(direccion):
    """La dirección llevada al primer cuadrante: la sección es doblemente simétrica, así que el
    diagrama es el mismo para ±My y ±Mz."""
    return math.atan2(abs(math.sin(direccion)), abs(math.cos(direccion)))


class DiagramaInteraccion(QWidget):
    """El diagrama de interacción de una sección de concreto con refuerzo.

    con_modo: agrega la lista 2D / 3D (la pestaña); sin ella, el modo lo da quien lo usa (la ventana).
    con_barra: la barra de matplotlib (zoom, mover, guardar), solo en 2D."""

    def __init__(self, parent=None, con_modo=False, con_barra=True):
        super().__init__(parent)
        self.seccion = None
        self.modo = "2D"
        self.puntos = []                        # Demanda de cada combinación y extremo (vacío: sin puntos)
        self.elegido = None                     # índice del punto elegido en la tabla
        self._calculado = {}                    # (qué, parámetro) -> datos en unidades internas, de _de_seccion
        self._de_seccion = None                 # los datos de la sección de lo calculado
        self.vista3d = None                     # VistaSuperficie: se crea la primera vez que se pide 3D
        # layout="tight": los márgenes se recalculan en cada dibujo, también cuando el panel cambia
        # de ancho (con la pestaña Interacción, Propiedades se ensancha)
        self.figura = Figure(figsize=(7, 6), layout="tight")
        self.lienzo = FigureCanvasQTAgg(self.figura)
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        self.barra = NavigationToolbar2QT(self.lienzo, self) if con_barra else None
        if self.barra is not None:
            diseno.addWidget(self.barra)
        fila = QHBoxLayout()
        self.selector_modo = None
        if con_modo:
            self.selector_modo = Lista()
            self.selector_modo.addItem("2D (P–M)", "2D")
            self.selector_modo.addItem("3D (superficie)", "3D")
            self.selector_modo.currentIndexChanged.connect(self._cambio_modo)
            fila.addWidget(self.selector_modo)
        self.etiqueta_theta = QLabel("θ" if con_modo else "Compresión hacia θ")     # corto en la pestaña
        self.etiqueta_theta.setToolTip(AYUDA_THETA)
        self.theta = CampoNumero(minimo=0, maximo=359, entero=True, unidad="°", cifras=5)
        self.theta.setToolTip(AYUDA_THETA)
        self.theta.poner(0)
        self.theta.terminado.connect(lambda: self._probar(self.refrescar))
        fila.addWidget(self.etiqueta_theta)
        fila.addWidget(self.theta)
        fila.addStretch(1)
        diseno.addLayout(fila)
        self.aviso = QLabel()
        self.aviso.setWordWrap(True)
        self.aviso.hide()
        diseno.addWidget(self.aviso)
        self.paginas = QStackedWidget()         # página 0: el 2D (matplotlib); página 1: el 3D (VTK)
        self.paginas.addWidget(self.lienzo)
        diseno.addWidget(self.paginas, 3)
        # Puntos Pu–Mu: la tabla, o una línea que dice cómo verlos
        self.pista = QLabel()
        self.pista.setWordWrap(True)
        self.pista.setStyleSheet(f"color: {colores.INTERFAZ_DESHABILITADO};")
        self.pista.hide()
        diseno.addWidget(self.pista)
        self.tabla = QTableWidget(0, 5)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.verticalHeader().hide()
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for columna in range(1, 5):
            self.tabla.horizontalHeader().setSectionResizeMode(columna, QHeaderView.ResizeToContents)
        self.tabla.setToolTip("Fuerzas de cada combinación en los extremos de la columna (primer orden, sin "
                              "esbeltez). Pu > 0 es compresión. Elige una fila para ver su punto")
        self.tabla.itemSelectionChanged.connect(self._fila_elegida)
        self.tabla.hide()
        diseno.addWidget(self.tabla, 2)

    # ---------- Qué se muestra ----------
    def mostrar(self, seccion, modo=None, puntos=None, pista=""):
        """Muestra el diagrama de la sección; lo calcula si hace falta. ValueError si los datos no
        sirven (por ejemplo, un refuerzo imposible).

        puntos: lista de Demanda (los puntos Pu–Mu de una columna), o None o vacía si no hay.
        pista: texto bajo el gráfico cuando no hay puntos (por ejemplo, que falta analizar)."""
        self.seccion = seccion
        if modo is not None:
            self.modo = modo
            if self.selector_modo is not None:
                self.selector_modo.blockSignals(True)
                self.selector_modo.setCurrentIndex(self.selector_modo.findData(modo))
                self.selector_modo.blockSignals(False)
        anteriores = [(p.clave, p.lugar) for p in self.puntos]
        self.puntos = list(puntos or [])
        if [(p.clave, p.lugar) for p in self.puntos] != anteriores or self.elegido is None:
            # Otros puntos: empieza elegido el de mayor momento
            self.elegido = max(range(len(self.puntos)), key=lambda i: self.puntos[i].m) if self.puntos else None
        self.pista.setText(pista)
        self.pista.setVisible(bool(pista) and not self.puntos)
        self._llenar_tabla()
        self.refrescar()

    def mostrar_error(self, texto):
        self.aviso.setText(texto)
        self.aviso.show()
        self.figura.clear()
        self.lienzo.draw_idle()
        self.paginas.setCurrentIndex(0)

    def _con_theta(self):
        return (self.modo == "2D" and not self.puntos and self.seccion is not None
                and self.seccion.concreto.forma == "rectangular")

    def _cambio_modo(self, *_):
        self.modo = self.selector_modo.currentData()
        self._probar(self.refrescar)

    def _probar(self, funcion):
        try:
            funcion()
        except ValueError as e:
            self.mostrar_error(f"No se pudo calcular: {e}")

    # ---------- Tabla de puntos ----------
    def _llenar_tabla(self):
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(len(self.puntos))
        sf, sm = unidades.simbolo("fuerza"), unidades.simbolo("momento")
        self.tabla.setHorizontalHeaderLabels(["Combinación", "Extremo", f"Pu ({sf})", f"My ({sm})", f"Mz ({sm})"])
        for fila, p in enumerate(self.puntos):
            celdas = [p.combinacion, p.lugar, formato.cantidad(p.p, "fuerza", False),
                      formato.cantidad(p.my, "momento", False), formato.cantidad(p.mz, "momento", False)]
            for columna, texto in enumerate(celdas):
                item = QTableWidgetItem(texto)
                if columna >= 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla.setItem(fila, columna, item)
        if self.elegido is not None:
            self.tabla.selectRow(self.elegido)
        self.tabla.blockSignals(False)
        self.tabla.setVisible(bool(self.puntos))

    def _fila_elegida(self):
        filas = self.tabla.selectionModel().selectedRows()
        if filas and filas[0].row() != self.elegido:
            self.elegido = filas[0].row()
            self._probar(self.refrescar)

    def elegir(self, indice):
        """Elige el punto de ese índice (por ejemplo, con un clic sobre él en el 3D)."""
        if 0 <= indice < len(self.puntos):
            self.tabla.selectRow(indice)

    # ---------- Cálculo (solo lo que falte) ----------
    def _datos(self, que, parametro=0.0):
        """Lo calculado para la sección vigente: "theta" (curva con la fibra comprimida hacia θ),
        "direccion" (corte en esa dirección del momento) o "superficie". Con el cursor de espera."""
        datos_seccion = astuple(self.seccion.concreto)
        if datos_seccion != self._de_seccion:
            self._calculado, self._de_seccion = {}, datos_seccion
        clave = (que, round(float(parametro), 4))
        if clave not in self._calculado:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                c = self.seccion.concreto
                sec = concreto.propiedades(c)
                if que == "theta":
                    self._calculado[clave] = concreto.curva_2d(c, sec, clave[1])
                elif que == "direccion":
                    self._calculado[clave] = concreto.curva_direccion(c, sec, clave[1])
                else:
                    self._calculado[clave] = concreto.superficie_3d(c, sec)
            finally:
                QApplication.restoreOverrideCursor()
        return self._calculado[clave]

    def calcular(self):
        """Olvida lo calculado y vuelve a calcular y dibujar."""
        self._de_seccion = None
        self.refrescar()

    # ---------- Dibujo ----------
    def refrescar(self):
        """Dibuja el diagrama (calculando lo que falte), en las unidades de pantalla vigentes."""
        if self.seccion is None:
            return
        self.etiqueta_theta.setVisible(self._con_theta())
        self.theta.setVisible(self._con_theta())
        if self.barra is not None:
            self.barra.setVisible(self.modo == "2D")
        if self.tabla.isVisible():
            self._llenar_tabla()                # los valores, en las unidades vigentes
        if self.modo == "2D":
            self._dibujar_2d()
            self.paginas.setCurrentIndex(0)
        else:
            self._dibujar_3d()
            self.paginas.setCurrentIndex(1)
        self.aviso.hide()

    def _dibujar_2d(self):
        fu, mu = unidades.factor("fuerza"), unidades.factor("momento")
        sf, sm = unidades.simbolo("fuerza"), unidades.simbolo("momento")
        titulo = "Diagrama de interacción"
        circular = self.seccion.concreto.forma == "circular"
        elegido = self.puntos[self.elegido] if self.puntos and self.elegido is not None else None
        if elegido is not None:
            direccion = _plegada(concreto.direccion_momento(elegido.my, elegido.mz)) if elegido.m > 1e-9 else 0.0
            Pn, Mn, PhiPn, PhiMn = self._datos("direccion", direccion)
            titulo = f"{elegido.combinacion}, {elegido.lugar}"
            if not circular:
                titulo += f" — momento a {math.degrees(direccion):.1f}°"
        elif self._con_theta():
            Pn, Mn, PhiPn, PhiMn = self._datos("theta", np.radians(self.theta.valor()))
            titulo += f" — θ = {self.theta.valor()}°"
        else:
            Pn, Mn, PhiPn, PhiMn = self._datos("theta", 0.0)
        self.figura.clear()
        ax = self.figura.add_subplot(111)
        ax.plot(Mn / mu, Pn / fu, color=colores.ELEMENTO, label="Nominal (Mn, Pn)")
        ax.plot(PhiMn / mu, PhiPn / fu, color=colores.SELECCIONADO, label="Diseño (φMn, φPn)")
        for i, p in enumerate(self.puntos):
            igual = (circular or p.m < 1e-9 or elegido.m < 1e-9
                     or abs(_plegada(concreto.direccion_momento(p.my, p.mz)) - direccion) <= MISMA_DIRECCION)
            color = colores.INTERACCION_ELEGIDO if i == self.elegido else colores.INTERACCION_PUNTO
            ax.plot(p.m / mu, p.p / fu, MARCADOR[p.lugar], color=color, markersize=9 if i == self.elegido else 6,
                    markerfacecolor=color if igual else "none", zorder=4 if i == self.elegido else 3)
        if self.puntos:
            for lugar in dict.fromkeys(p.lugar for p in self.puntos):
                ax.plot([], [], MARCADOR[lugar], color=colores.INTERACCION_PUNTO, markersize=6, linestyle="none",
                        label=f"Pu–Mu, {lugar}")
            if any(not (circular or p.m < 1e-9 or abs(_plegada(concreto.direccion_momento(p.my, p.mz)) - direccion)
                        <= MISMA_DIRECCION) for p in self.puntos):
                ax.plot([], [], "o", color=colores.INTERACCION_PUNTO, markerfacecolor="none", markersize=6,
                        linestyle="none", label="momento en otra dirección")
        ax.axhline(0, color="k", linewidth=0.8)
        ax.axvline(0, color="k", linewidth=0.8)
        ax.set_xlabel(f"M resultante ({sm})" if self.puntos else f"M ({sm})")
        ax.set_ylabel(f"P ({sf})")
        ax.set_title(titulo, fontsize=10)
        ax.grid(True, alpha=0.4)
        ax.legend(fontsize=8)
        self.lienzo.draw_idle()

    def _dibujar_3d(self):
        X, Y, Z = self._datos("superficie")
        if self.vista3d is None:
            from interfaz.vista3d.superficie import VistaSuperficie     # aquí: crea una ventana 3D
            self.vista3d = VistaSuperficie(self)
            self.vista3d.punto_elegido.connect(self.elegir)
            self.paginas.addWidget(self.vista3d)
        self.vista3d.mostrar(X, Y, Z, [(p.mz, p.my, p.p) for p in self.puntos], self.elegido)

    def cerrar(self):
        """Libera la vista 3D, si se llegó a crear (antes de cerrar la ventana que contiene al diagrama)."""
        if self.vista3d is not None:
            self.vista3d.cerrar()


class VentanaDiagrama(QWidget):
    """Ventana aparte con el diagrama de una sección (Ver 2D o Ver 3D)."""

    def __init__(self, seccion, modo, parent=None):
        super().__init__(parent, Qt.Window)
        self.seccion, self.modo = seccion, modo
        self.resize(760, 680)
        self.diagrama = DiagramaInteraccion(self)
        diseno = QVBoxLayout(self)
        diseno.addWidget(self.diagrama)
        self._titulo()
        try:
            self.diagrama.mostrar(seccion, modo)
        except ValueError:
            self.diagrama.cerrar()
            self.deleteLater()                  # no queda una ventana a medias
            raise

    def _titulo(self):
        self.setWindowTitle(f"Diagrama de interacción {self.modo} — {textos.nombre(self.seccion)}")

    def refrescar(self):
        """Las unidades cambiaron: el título y el dibujo, en las nuevas."""
        self._titulo()
        self.diagrama.refrescar()

    def closeEvent(self, evento):
        self.diagrama.cerrar()
        super().closeEvent(evento)
