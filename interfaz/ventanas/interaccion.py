"""Ventanas de diagramas de interacción (2D y 3D), dibujadas con matplotlib dentro de Qt.

El cálculo está en calculo/interaccion (sagrado); aquí solo se dibuja, en unidades de pantalla.
Se calcula solo cuando el usuario presiona Ver 2D o Ver 3D: la superficie 3D son unos 2000 puntos.
Lo calculado se guarda en unidades internas: si cambian las unidades, solo se vuelve a dibujar.
"""
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registra la proyección 3D)
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from configuracion import colores, unidades
from modelo import interaccion as concreto


class VentanaDiagrama(QWidget):
    def __init__(self, seccion, modo, parent=None):
        super().__init__(parent, Qt.Window)
        self.seccion, self.modo = seccion, modo
        self.setWindowTitle(f"Diagrama de interacción {modo} — {seccion.nombre}")
        self.resize(760, 680)
        self.sec = concreto.propiedades(seccion.concreto)
        self._datos = None                       # lo calculado, en unidades internas

        self.figura = Figure(figsize=(7, 6))
        self.lienzo = FigureCanvasQTAgg(self.figura)
        diseno = QVBoxLayout(self)
        diseno.addWidget(NavigationToolbar2QT(self.lienzo, self))
        self.theta = None
        if modo == "2D" and seccion.concreto.forma == "rectangular":
            fila = QHBoxLayout()
            fila.addWidget(QLabel("Dirección de la compresión θ (°)"))
            self.theta = QSpinBox()
            self.theta.setRange(0, 359)
            self.theta.setWrapping(True)
            self.theta.valueChanged.connect(lambda *_: self.calcular())
            fila.addWidget(self.theta)
            fila.addStretch(1)
            diseno.addLayout(fila)
        diseno.addWidget(self.lienzo, 1)
        self.calcular()

    def calcular(self):
        """Calcula (con el cursor de espera) y dibuja."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.modo == "2D":
                theta = np.radians(self.theta.value()) if self.theta is not None else 0.0
                self._datos = concreto.curva_2d(self.seccion.concreto, self.sec, theta)
            else:
                self._datos = concreto.superficie_3d(self.seccion.concreto, self.sec)
        finally:
            QApplication.restoreOverrideCursor()
        self.refrescar()

    def refrescar(self):
        """Vuelve a dibujar lo calculado, en las unidades de pantalla vigentes."""
        fu, mu = unidades.factor("fuerza"), unidades.factor("momento")
        sf, sm = unidades.simbolo("fuerza"), unidades.simbolo("momento")
        self.figura.clear()
        if self.modo == "2D":
            Pn, Mn, PhiPn, PhiMn = self._datos
            ax = self.figura.add_subplot(111)
            ax.plot(Mn / mu, Pn / fu, color=colores.ELEMENTO, label="Nominal (Mn, Pn)")
            ax.plot(PhiMn / mu, PhiPn / fu, color=colores.SELECCIONADO, label="Diseño (φMn, φPn)")
            ax.axhline(0, color="k", linewidth=0.8)
            ax.axvline(0, color="k", linewidth=0.8)
            ax.set_xlabel(f"M ({sm})")
            ax.set_ylabel(f"P ({sf})")
            titulo = "Diagrama de interacción"
            if self.theta is not None:
                titulo += f" — θ = {self.theta.value()}°"
            ax.set_title(titulo)
            ax.grid(True, alpha=0.4)
            ax.legend()
        else:
            X, Y, Z = self._datos
            ax = self.figura.add_subplot(111, projection="3d")
            ax.plot_surface(X / mu, Y / mu, Z / fu, cmap="Greys", alpha=0.85, linewidth=0)
            ax.set_xlabel(f"φMy ({sm})")
            ax.set_ylabel(f"φMx ({sm})")
            ax.set_zlabel(f"φPn ({sf})")
            ax.set_title("Superficie de interacción de diseño")
        self.figura.tight_layout()
        self.lienzo.draw_idle()
