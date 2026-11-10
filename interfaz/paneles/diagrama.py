"""Panel Diagrama (abajo del dibujo): lo que se ve arriba, para UNA barra y en sus ejes locales.

Sigue a la barra de arriba: muestra el resultado que está prendido ahí (Deformada, Axial, Cortante,
Momento o Torsión), del caso o la combinación activos, para la barra seleccionada. No tiene listas
propias: lo que cambia lo que se ve es siempre la barra de arriba.
- x local en el eje horizontal, de 0 (nodo i) a L (nodo j). Así una columna también se ve acostada
  y cabe en un panel ancho.
- Con un diagrama (N, Vy, Vz, T, My o Mz): el valor en el eje vertical, del mismo lado que en 3D
  (vista3d/resultados.DIRECCION): los momentos del lado de la tracción (positivo hacia abajo); N, V
  y T positivos hacia arriba. A la derecha, las seis fuerzas en el corte.
- Con Deformada: los desplazamientos de la barra en sus ejes locales, v (en y) y w (en z), sin
  amplificar. A la derecha, u, v, w y el giro φx en el corte.
- Un deslizador (o el campo x) mueve el corte a lo largo de la barra. En una carga puntual justo en
  el corte, el valor es el de después de la carga.
Los números salen de modelo/analisis.py (fuerzas_en, fuerzas_en_x y desplazamientos_locales), que
usa las fórmulas de calculo/rigidez/diagramas.py: aquí no hay fórmulas.
"""
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QDockWidget, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from configuracion import colores, formato, unidades
from configuracion import interfaz as ui
from interfaz.paneles.comunes import CampoNumero
from interfaz.vista3d.resultados import DIRECCION
from modelo.analisis import desplazamientos_locales, fuerzas_en, fuerzas_en_x, geometria

FUERZAS = ("N", "Vy", "Vz", "T", "My", "Mz")
NOMBRE = {"deformada": "Deformada", "N": "Axial N", "Vy": "Cortante Vy", "Vz": "Cortante Vz", "T": "Torsión T",
          "My": "Momento My", "Mz": "Momento Mz"}
DESPLAZAMIENTOS = (("u", "u (en x)"), ("v", "v (en y)"), ("w", "w (en z)"))


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
        self.titulo = QLabel()
        izquierda.addWidget(self.titulo)
        self.aviso = QLabel()
        self.aviso.setAlignment(Qt.AlignCenter)
        self.aviso.setWordWrap(True)
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
        self.etiqueta_corte = QLabel("Corte en x =")
        abajo.addWidget(self.etiqueta_corte)
        abajo.addWidget(self.deslizador, 1)
        abajo.addWidget(self.x)
        izquierda.addLayout(abajo)

        self.lectura = QLabel()                    # los valores en el corte, como una tabla
        self.lectura.setTextFormat(Qt.RichText)
        self.lectura.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lectura.setMinimumWidth(190)

        diseno = QHBoxLayout(contenido)
        diseno.addLayout(izquierda, 1)
        diseno.addWidget(self.lectura)
        self.setWidget(contenido)
        self._modelo = self._rc = self._eid = self._resultado = None
        self._largo = 0.0
        self._linea = None
        self._extremos = ""
        self._vaciar("Selecciona una barra")

    # ---------- Qué se muestra ----------
    def mostrar(self, modelo, rc, eid, resultado):
        """La barra eid con los resultados rc (de un caso o de una combinación) y el resultado que
        está prendido en la barra de arriba: "deformada", una fuerza ("N", "My"...) o None."""
        if rc is None:
            self._vaciar("Analiza el modelo (▶) para ver aquí los resultados de una barra")
        elif resultado not in NOMBRE:
            self._vaciar("Elige arriba qué ver: Deformada, Axial, Cortante, Momento o Torsión")
        elif eid is None or eid not in modelo.elementos or eid not in rc.res.fuerzas:
            self._vaciar(f"Selecciona una barra para ver aquí: {NOMBRE[resultado]}")
        else:
            otra = (eid != self._eid)
            self._modelo, self._rc, self._eid, self._resultado = modelo, rc, eid, resultado
            self._largo = geometria(modelo, eid)[2]
            self.x.actualizar_unidades()
            if otra:
                self.deslizador.blockSignals(True)
                self.deslizador.setValue(ui.PASOS_DESLIZADOR // 2)    # el corte empieza al centro
                self.deslizador.blockSignals(False)
            for w in (self.deslizador, self.x, self.etiqueta_corte):
                w.setEnabled(True)
            self.aviso.hide()
            self.lienzo.show()
            self._dibujar()

    def _vaciar(self, texto):
        self._modelo = self._rc = self._eid = self._resultado = None
        self.titulo.setText("")
        self.aviso.setText(texto)
        self.aviso.show()
        self.lienzo.hide()
        for w in (self.deslizador, self.x, self.etiqueta_corte):
            w.setEnabled(False)
        self.lectura.setText("")

    def _x_actual(self):
        return self._largo * self.deslizador.value() / ui.PASOS_DESLIZADOR

    # ---------- Dibujo ----------
    def _dibujar(self):
        if self._eid is None:
            return
        modelo, rc, eid, resultado = self._modelo, self._rc, self._eid, self._resultado
        el = modelo.elementos[eid]
        tipo = "Columna" if modelo.es_columna(eid) else "Elemento"
        self.titulo.setText(f"<b>{tipo} {eid}</b> (nodo {el.ni} → {el.nj}, ejes locales) — "
                            f"<b>{NOMBRE[resultado]}</b> — {rc.nombre}")
        fl = unidades.factor("longitud")
        self.figura.clear()
        ax = self.figura.add_subplot(111)
        if resultado == "deformada":
            d = desplazamientos_locales(modelo, rc, eid)
            fd = unidades.factor("desplazamiento")
            ax.plot(d["x"] / fl, d["w"] / fd, color=colores.DEFORMADA, linewidth=1.4, label="w (en z local)")
            ax.plot(d["x"] / fl, d["v"] / fd, color=colores.DEFORMADA, linewidth=1.0, linestyle="--",
                    label="v (en y local)")
            ax.legend(fontsize=7, loc="best")
            ax.set_ylabel(f"desplazamiento ({unidades.simbolo('desplazamiento')})", fontsize=8)
            self._extremos = ""
        else:
            magnitud = magnitud_de(resultado)
            d = fuerzas_en(modelo, rc, eid)
            x, y = d["x"] / fl, d[resultado] / unidades.factor(magnitud)
            ax.plot(x, y, color=colores.DIAGRAMA_BORDE, linewidth=1)
            ax.fill_between(x, y, 0, where=y >= 0, color=colores.DIAGRAMA_POSITIVO, alpha=0.8, interpolate=True)
            ax.fill_between(x, y, 0, where=y < 0, color=colores.DIAGRAMA_NEGATIVO, alpha=0.8, interpolate=True)
            if DIRECCION[resultado][1] < 0:           # momentos: del lado de la tracción (positivo abajo)
                ax.invert_yaxis()
            ax.set_ylabel(f"{resultado} ({unidades.simbolo(magnitud)})", fontsize=8)
            self._extremos = (f"<tr><td colspan=2><br>{resultado} máx: {formato.cantidad(float(np.max(d[resultado])), magnitud)}"
                              f"<br>{resultado} mín: {formato.cantidad(float(np.min(d[resultado])), magnitud)}</td></tr>")
        ax.axhline(0, color=colores.INTERFAZ_DESHABILITADO, linewidth=0.8)
        ax.set_xlim(0, self._largo / fl)
        ax.set_xlabel(f"x local ({unidades.simbolo('longitud')})", fontsize=8)
        ax.tick_params(labelsize=7)
        self._linea = ax.axvline(self._x_actual() / fl, color=colores.SELECCIONADO, linewidth=1)
        self.lienzo.draw_idle()
        self._leer(self._x_actual())

    def _leer(self, x):
        """Los valores en el corte x (m) y la línea del corte en el gráfico."""
        if self._eid is None:
            return
        self.x.poner(x)
        filas = []
        if self._resultado == "deformada":
            d = desplazamientos_locales(self._modelo, self._rc, self._eid, x=[x])
            for clave, nombre in DESPLAZAMIENTOS:
                filas.append((nombre, formato.cantidad(float(d[clave][0]), "desplazamiento"), False))
            filas.append(("φx (giro)", f"{formato.numero(float(d['phi'][0]), 6)} rad", False))
        else:
            valores = fuerzas_en_x(self._modelo, self._rc, self._eid, x)
            for comp in FUERZAS:
                filas.append((comp, formato.cantidad(valores[comp], magnitud_de(comp)), comp == self._resultado))
        cuerpo = "".join(f"<tr><td>{'<b>' if activo else ''}{nombre}{'</b>' if activo else ''}&nbsp;&nbsp;</td>"
                         f"<td align='right'>{'<b>' if activo else ''}{valor}{'</b>' if activo else ''}</td></tr>"
                         for nombre, valor, activo in filas)
        self.lectura.setText(f"<b>En el corte</b><table>{cuerpo}{self._extremos}</table>")
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
