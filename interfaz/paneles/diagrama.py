"""Panel Diagrama (abajo del dibujo): los diagramas de UNA barra, siempre en sus ejes locales.

- x local en el eje horizontal, de 0 (nodo i) a L (nodo j). Así una columna también se ve
  acostada y cabe en un panel ancho.
- El valor en el eje vertical, del mismo lado que en 3D (vista3d/resultados.DIRECCION): los momentos
  del lado de la tracción (positivo hacia abajo); N, V y T positivos hacia arriba.
- Un deslizador (o el campo x) mueve un corte a lo largo de la barra; a la derecha se leen N, Vy,
  Vz, T, My y Mz en ese corte. En una carga puntual justo en el corte, el valor es el de después.
- Muestra el caso o la combinación activos (los de la barra de arriba). El componente sigue al
  diagrama elegido arriba (My si no hay ninguno) y se puede cambiar aquí sin tocar el 3D.
Los números salen de modelo/analisis.py (fuerzas_en y fuerzas_en_x), que usa las fórmulas de
calculo/rigidez/diagramas.py: aquí no hay fórmulas.
"""
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QComboBox, QDockWidget, QGridLayout, QHBoxLayout, QLabel, QSlider, QVBoxLayout,
                               QWidget)

from configuracion import colores, formato, unidades
from configuracion import interfaz as ui
from interfaz.paneles.comunes import CampoNumero
from interfaz.vista3d.resultados import DIRECCION
from modelo.analisis import fuerzas_en, fuerzas_en_x, geometria

COMPONENTES = ("N", "Vy", "Vz", "T", "My", "Mz")
DESCRIPCION = {"N": "N: axial (+ tracción)", "Vy": "Vy: cortante en el plano x–y", "Vz": "Vz: cortante en el plano x–z",
               "T": "T: torsión", "My": "My: momento en el plano x–z", "Mz": "Mz: momento en el plano x–y"}


def magnitud_de(componente):
    return "fuerza" if componente in ("N", "Vy", "Vz") else "momento"


class _Contenido(QWidget):
    """Lo que va dentro del panel: un poco más alto de lo que Qt le daría solo."""

    def sizeHint(self):                          # noqa: N802 (nombre de Qt)
        return QSize(800, ui.ALTO_PANEL_DIAGRAMA)


class PanelDiagrama(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Diagrama", parent)
        self.setObjectName("diagrama")
        contenido = _Contenido()
        izquierda = QVBoxLayout()
        arriba = QHBoxLayout()
        self.titulo = QLabel()
        self.selector = QComboBox()
        for comp in COMPONENTES:
            self.selector.addItem(DESCRIPCION[comp], comp)
        self.selector.setCurrentIndex(COMPONENTES.index("My"))
        self.selector.setToolTip("Qué diagrama se ve aquí (no cambia el dibujo 3D)")
        self.selector.currentIndexChanged.connect(lambda *_: self._dibujar())
        arriba.addWidget(self.titulo, 1)
        arriba.addWidget(self.selector)
        izquierda.addLayout(arriba)
        self.aviso = QLabel()
        self.aviso.setAlignment(Qt.AlignCenter)
        self.aviso.setStyleSheet(f"color: {colores.INTERFAZ_DESHABILITADO};")
        izquierda.addWidget(self.aviso, 1)
        self.figura = Figure(figsize=(7, 1.8), tight_layout=True)
        self.lienzo = FigureCanvasQTAgg(self.figura)
        self.lienzo.setMinimumHeight(120)
        izquierda.addWidget(self.lienzo, 1)
        abajo = QHBoxLayout()
        self.deslizador = QSlider(Qt.Horizontal)
        self.deslizador.setRange(0, ui.PASOS_DESLIZADOR)
        self.deslizador.setToolTip("Mueve el corte a lo largo de la barra")
        self.deslizador.valueChanged.connect(self._deslizado)
        self.x = CampoNumero("longitud", 0.0, 1e6)
        self.x.setToolTip("Distancia del corte desde el nodo i (eje x local)")
        self.x.terminado.connect(self._x_escrito)
        abajo.addWidget(QLabel("Corte en x ="))
        abajo.addWidget(self.deslizador, 1)
        abajo.addWidget(self.x)
        izquierda.addLayout(abajo)

        derecha = QGridLayout()
        derecha.addWidget(QLabel("<b>En el corte</b>"), 0, 0, 1, 2)
        self.lectura = {}
        for k, comp in enumerate(COMPONENTES, start=1):
            derecha.addWidget(QLabel(comp), k, 0)
            valor = QLabel()
            valor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            valor.setMinimumWidth(110)
            derecha.addWidget(valor, k, 1)
            self.lectura[comp] = valor
        self.extremos = QLabel()
        self.extremos.setWordWrap(True)
        derecha.addWidget(self.extremos, len(COMPONENTES) + 1, 0, 1, 2)
        derecha.setRowStretch(len(COMPONENTES) + 2, 1)

        diseno = QHBoxLayout(contenido)
        diseno.addLayout(izquierda, 1)
        diseno.addLayout(derecha)
        self.setWidget(contenido)
        self._modelo = self._rc = self._eid = None
        self._largo = 0.0
        self._linea = None
        self._vaciar("Selecciona una barra")

    # ---------- Qué se muestra ----------
    def mostrar(self, modelo, rc, eid, componente=None):
        """La barra eid con los resultados rc (de un caso o de una combinación). componente: el
        diagrama elegido arriba ("N", "My"...), que pasa a ser el de este panel."""
        if componente in COMPONENTES:
            self.selector.blockSignals(True)
            self.selector.setCurrentIndex(COMPONENTES.index(componente))
            self.selector.blockSignals(False)
        if eid is None or eid not in modelo.elementos:
            self._vaciar("Selecciona una barra para ver sus diagramas")
            return
        if rc is None or eid not in rc.res.fuerzas:
            self._vaciar("Analiza el modelo (▶) para ver los diagramas")
            return
        nuevo = (eid != self._eid)
        self._modelo, self._rc, self._eid = modelo, rc, eid
        self._largo = geometria(modelo, eid)[2]
        self.x.actualizar_unidades()
        if nuevo:
            self.deslizador.blockSignals(True)
            self.deslizador.setValue(ui.PASOS_DESLIZADOR // 2)        # el corte empieza al centro
            self.deslizador.blockSignals(False)
        for w in (self.lienzo, self.deslizador, self.x, self.selector):
            w.setEnabled(True)
        self.lienzo.show()
        self.aviso.hide()
        self._dibujar()

    def _vaciar(self, texto):
        self._modelo = self._rc = self._eid = None
        self.titulo.setText("")
        self.aviso.setText(texto)
        self.aviso.show()
        self.lienzo.hide()
        for w in (self.deslizador, self.x):
            w.setEnabled(False)
        for valor in self.lectura.values():
            valor.setText("")
        self.extremos.setText("")

    def _x_actual(self):
        return self._largo * self.deslizador.value() / ui.PASOS_DESLIZADOR

    # ---------- Dibujo ----------
    def _dibujar(self):
        if self._eid is None:
            return
        comp = self.selector.currentData()
        magnitud = magnitud_de(comp)
        d = fuerzas_en(self._modelo, self._rc, self._eid)
        el = self._modelo.elementos[self._eid]
        tipo = "Columna" if self._modelo.es_columna(self._eid) else "Elemento"
        self.titulo.setText(f"<b>{tipo} {self._eid}</b> (nodo {el.ni} → {el.nj}, x local) — {self._rc.nombre}")
        x = d["x"] / unidades.factor("longitud")
        y = d[comp] / unidades.factor(magnitud)
        self.figura.clear()
        ax = self.figura.add_subplot(111)
        ax.plot(x, y, color=colores.DIAGRAMA_BORDE, linewidth=1)
        ax.fill_between(x, y, 0, where=y >= 0, color=colores.DIAGRAMA_POSITIVO, alpha=0.8, interpolate=True)
        ax.fill_between(x, y, 0, where=y < 0, color=colores.DIAGRAMA_NEGATIVO, alpha=0.8, interpolate=True)
        ax.axhline(0, color=colores.INTERFAZ_DESHABILITADO, linewidth=0.8)
        if DIRECCION[comp][1] < 0:                # momentos: del lado de la tracción (positivo abajo)
            ax.invert_yaxis()
        ax.set_xlim(0, self._largo / unidades.factor("longitud"))
        ax.set_xlabel(f"x ({unidades.simbolo('longitud')})", fontsize=8)
        ax.set_ylabel(f"{comp} ({unidades.simbolo(magnitud)})", fontsize=8)
        ax.tick_params(labelsize=7)
        corte = self._x_actual() / unidades.factor("longitud")
        self._linea = ax.axvline(corte, color=colores.SELECCIONADO, linewidth=1)
        self.extremos.setText(f"{comp}: máx {formato.cantidad(float(np.max(d[comp])), magnitud)}<br>"
                              f"{comp}: mín {formato.cantidad(float(np.min(d[comp])), magnitud)}")
        self.lienzo.draw_idle()
        self._leer(self._x_actual())

    def _leer(self, x):
        """Los valores en el corte x (m) y la línea del corte en el gráfico."""
        if self._eid is None:
            return
        self.x.poner(x)
        valores = fuerzas_en_x(self._modelo, self._rc, self._eid, x)
        for comp, etiqueta in self.lectura.items():
            etiqueta.setText(formato.cantidad(valores[comp], magnitud_de(comp)))
        if self._linea is not None:
            corte = x / unidades.factor("longitud")
            self._linea.set_xdata([corte, corte])
            self.lienzo.draw_idle()

    def _deslizado(self, *_):
        self._leer(self._x_actual())

    def _x_escrito(self):
        """El corte en una x exacta: el deslizador va a la posición más cercana."""
        if self._eid is None or self._largo <= 0:
            return
        x = min(max(self.x.valor(), 0.0), self._largo)
        self.deslizador.blockSignals(True)
        self.deslizador.setValue(round(x / self._largo * ui.PASOS_DESLIZADOR))
        self.deslizador.blockSignals(False)
        self._leer(x)
