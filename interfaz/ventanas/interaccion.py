"""Diagramas de interacción (2D y 3D), dibujados con matplotlib dentro de Qt.

- DiagramaInteraccion: el dibujo con sus controles (θ y, si se pide, 2D o 3D). Lo usan la ventana
  aparte (Ver 2D y Ver 3D de una sección) y la pestaña Interacción de Propiedades (columnas).
- VentanaDiagrama: una ventana con un DiagramaInteraccion.
El cálculo está en calculo/interaccion (sagrado); aquí solo se dibuja, en unidades de pantalla.
Se calcula solo cuando se pide (Ver 2D, Ver 3D o al abrir la pestaña): la superficie 3D son unos
2000 puntos. Lo calculado se guarda en unidades internas: si cambian las unidades, solo se vuelve a
dibujar; y si se pide otra vez la misma sección con los mismos datos, no se recalcula.
"""
from dataclasses import astuple

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registra la proyección 3D)
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from configuracion import colores, unidades
from interfaz import textos
from interfaz.paneles.comunes import CampoNumero
from modelo import interaccion as concreto


class DiagramaInteraccion(QWidget):
    """El diagrama de interacción de una sección de concreto con refuerzo.

    con_modo: agrega la lista 2D / 3D (la pestaña); sin ella, el modo lo da quien lo usa (la ventana).
    con_barra: la barra de matplotlib (zoom, mover, guardar)."""

    def __init__(self, parent=None, con_modo=False, con_barra=True):
        super().__init__(parent)
        self.seccion = None
        self.modo = "2D"
        self._datos = None                      # lo calculado, en unidades internas
        self._clave = None                      # (datos de la sección, modo, θ) de lo calculado
        self.figura = Figure(figsize=(7, 6))
        self.lienzo = FigureCanvasQTAgg(self.figura)
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(0, 0, 0, 0)
        if con_barra:
            diseno.addWidget(NavigationToolbar2QT(self.lienzo, self))
        fila = QHBoxLayout()
        self.selector_modo = None
        if con_modo:
            self.selector_modo = QComboBox()
            self.selector_modo.addItem("2D (P–M)", "2D")
            self.selector_modo.addItem("3D (superficie)", "3D")
            self.selector_modo.currentIndexChanged.connect(self._cambio_modo)
            fila.addWidget(self.selector_modo)
        self.etiqueta_theta = QLabel("Compresión hacia θ")
        self.etiqueta_theta.setToolTip("Dirección de la fibra más comprimida, en el plano de la sección")
        self.theta = CampoNumero(minimo=0, maximo=359, entero=True, unidad="°")
        self.theta.poner(0)
        self.theta.terminado.connect(self._al_cambiar_theta)
        fila.addWidget(self.etiqueta_theta)
        fila.addWidget(self.theta)
        fila.addStretch(1)
        diseno.addLayout(fila)
        self.aviso = QLabel()
        self.aviso.setWordWrap(True)
        self.aviso.hide()
        diseno.addWidget(self.aviso)
        diseno.addWidget(self.lienzo, 1)

    # ---------- Qué se muestra ----------
    def mostrar(self, seccion, modo=None):
        """Muestra el diagrama de la sección; lo calcula si hace falta. ValueError si los datos no
        sirven (por ejemplo, un refuerzo imposible)."""
        self.seccion = seccion
        if modo is not None:
            self.modo = modo
            if self.selector_modo is not None:
                self.selector_modo.blockSignals(True)
                self.selector_modo.setCurrentIndex(self.selector_modo.findData(modo))
                self.selector_modo.blockSignals(False)
        self._controles()
        self._calcular_si_cambio()

    def mostrar_error(self, texto):
        self.aviso.setText(texto)
        self.aviso.show()
        self.figura.clear()
        self.lienzo.draw_idle()
        self._datos = self._clave = None

    def _con_theta(self):
        return self.modo == "2D" and self.seccion is not None and self.seccion.concreto.forma == "rectangular"

    def _controles(self):
        self.etiqueta_theta.setVisible(self._con_theta())
        self.theta.setVisible(self._con_theta())

    def _cambio_modo(self, *_):
        self.modo = self.selector_modo.currentData()
        self._controles()
        self._probar(self._calcular_si_cambio)

    def _al_cambiar_theta(self):
        self._probar(self._calcular_si_cambio)

    def _probar(self, funcion):
        try:
            funcion()
        except ValueError as e:
            self.mostrar_error(f"No se pudo calcular: {e}")

    # ---------- Cálculo (solo si cambió algo) ----------
    def _clave_actual(self):
        theta = self.theta.valor() if self._con_theta() else 0
        return astuple(self.seccion.concreto), self.modo, theta

    def _calcular_si_cambio(self):
        if self.seccion is None:
            return
        if self._clave_actual() != self._clave:
            self.calcular()
        else:
            self.refrescar()

    def calcular(self):
        """Calcula (con el cursor de espera) y dibuja."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            sec = concreto.propiedades(self.seccion.concreto)
            if self.modo == "2D":
                theta = np.radians(self.theta.valor()) if self._con_theta() else 0.0
                self._datos = concreto.curva_2d(self.seccion.concreto, sec, theta)
            else:
                self._datos = concreto.superficie_3d(self.seccion.concreto, sec)
            self._clave = self._clave_actual()
        finally:
            QApplication.restoreOverrideCursor()
        self.aviso.hide()
        self.refrescar()

    # ---------- Dibujo ----------
    def refrescar(self):
        """Vuelve a dibujar lo calculado, en las unidades de pantalla vigentes."""
        if self._datos is None:
            return
        fu, mu = unidades.factor("fuerza"), unidades.factor("momento")
        sf, sm = unidades.simbolo("fuerza"), unidades.simbolo("momento")
        self.figura.clear()
        if self._clave[1] == "2D":
            Pn, Mn, PhiPn, PhiMn = self._datos
            ax = self.figura.add_subplot(111)
            ax.plot(Mn / mu, Pn / fu, color=colores.ELEMENTO, label="Nominal (Mn, Pn)")
            ax.plot(PhiMn / mu, PhiPn / fu, color=colores.SELECCIONADO, label="Diseño (φMn, φPn)")
            ax.axhline(0, color="k", linewidth=0.8)
            ax.axvline(0, color="k", linewidth=0.8)
            ax.set_xlabel(f"M ({sm})")
            ax.set_ylabel(f"P ({sf})")
            titulo = "Diagrama de interacción"
            if self._con_theta():
                titulo += f" — θ = {self._clave[2]}°"
            ax.set_title(titulo, fontsize=10)
            ax.grid(True, alpha=0.4)
            ax.legend(fontsize=8)
        else:
            X, Y, Z = self._datos
            ax = self.figura.add_subplot(111, projection="3d")
            ax.plot_surface(X / mu, Y / mu, Z / fu, cmap="Greys", alpha=0.85, linewidth=0)
            ax.set_xlabel(f"φMy ({sm})")
            ax.set_ylabel(f"φMx ({sm})")
            ax.set_zlabel(f"φPn ({sf})")
            ax.set_title("Superficie de interacción de diseño", fontsize=10)
        self.figura.tight_layout()
        self.lienzo.draw_idle()


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
            self.deleteLater()                  # no queda una ventana a medias
            raise

    def _titulo(self):
        self.setWindowTitle(f"Diagrama de interacción {self.modo} — {textos.nombre(self.seccion)}")

    def refrescar(self):
        """Las unidades cambiaron: el título y el dibujo, en las nuevas."""
        self._titulo()
        self.diagrama.refrescar()
