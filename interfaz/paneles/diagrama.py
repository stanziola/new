"""Panel Diagrama (abajo del dibujo): lo que se ve arriba, para UNA barra.

Sigue a la barra de arriba: muestra el resultado que está prendido ahí (Deformada, Axial, Cortante,
Momento o Torsión), del caso o la combinación activos, para la barra seleccionada. No tiene listas
propias: lo que cambia lo que se ve es siempre la barra de arriba.
- En el eje horizontal, la distancia x desde el nodo i, de 0 a L (el eje x local). Así una columna
  también se ve acostada y cabe en un panel ancho.
- Con un diagrama (N, Vy, Vz, T, My o Mz): el valor en el eje vertical, del mismo lado que en 3D
  (vista3d/resultados.DIRECCION): los momentos del lado de la tracción (positivo hacia abajo); N, V
  y T positivos hacia arriba. Las fuerzas internas van siempre en los ejes LOCALES de la barra (no
  existen en globales: N es "a lo largo de la barra").
- Con Deformada: los desplazamientos de la barra en ejes GLOBALES, sin amplificar: Δx, Δy y Δz
  juntos (Total) o solo el elegido arriba.
- El título es corto ("Elemento 2 — Momento My"); el detalle (nodos, en qué plano o ejes va el
  resultado y de qué caso o combinación es) sale al pasar el mouse sobre él.
- A la derecha, solo el valor de lo que se está viendo en el corte. El máximo y el mínimo no se
  listan: se ven en la curva, y el corte se lleva hasta ahí.
- Un deslizador (o el campo x) mueve el corte a lo largo de la barra. En una carga puntual justo en
  el corte, el valor es el de después de la carga.
Los números salen de modelo/analisis.py (fuerzas_en, fuerzas_en_x y desplazamientos_globales), que
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
from interfaz.vista3d.resultados import DEFORMADAS, DIRECCION
from modelo.analisis import desplazamientos_globales, envolvente_en_x, fuerzas_en, fuerzas_en_x, geometria

NOMBRE = {"deformada": "Deformada total", "Dx": "Desplazamiento Δx", "Dy": "Desplazamiento Δy",
          "Dz": "Desplazamiento Δz", "N": "Axial N", "Vy": "Cortante Vy", "Vz": "Cortante Vz", "T": "Torsión T",
          "My": "Momento My", "Mz": "Momento Mz"}
# En qué ejes está cada resultado: va en el tooltip del título
EJES = {"N": "a lo largo de x local; tracción +", "Vy": "en y local", "Vz": "en z local",
        "T": "alrededor de x local", "My": "flexión en el plano x–z local",
        "Mz": "flexión en el plano x–y local"}
GLOBALES = (("Dx", "Δx"), ("Dy", "Δy"), ("Dz", "Δz"))
SIMBOLO = dict(GLOBALES)


def magnitud_de(componente):
    return "fuerza" if componente in ("N", "Vy", "Vz") else "momento"


def _color_global(clave):
    """Δx, Δy y Δz, con los colores de los ejes X, Y y Z de la esquina del dibujo."""
    return {"Dx": colores.EJE_X, "Dy": colores.EJE_Y, "Dz": colores.EJE_Z}[clave]


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
        self._vaciar("Selecciona una barra")

    # ---------- Qué se muestra ----------
    def mostrar_envolvente(self, modelo, env, eid, resultado):
        """La envolvente de la barra eid: la curva de máximos y la de mínimos de la fuerza `resultado`
        y, en el corte, los dos valores con la combinación que da cada uno. Sin deformada."""
        if resultado not in EJES:
            self._vaciar("La envolvente es de fuerzas internas: elige arriba Axial, Cortante, Momento o Torsión")
        elif eid is None or eid not in env.barras:
            self._vaciar(f"Selecciona una barra para ver aquí la envolvente de {NOMBRE[resultado]}")
        else:
            self._mostrar(modelo, None, eid, resultado, env)

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
            self._mostrar(modelo, rc, eid, resultado, None)

    def _mostrar(self, modelo, rc, eid, resultado, env):
        otra = (eid != self._eid)
        self._modelo, self._rc, self._eid, self._resultado, self._env = modelo, rc, eid, resultado, env
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
        self._modelo = self._rc = self._eid = self._resultado = self._env = None
        self.titulo.setText("")
        self.titulo.setToolTip("")
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
        # Título corto; el detalle (nodos, ejes del resultado y caso o combinación), en su tooltip
        self.titulo.setText(f"<b>Elemento {eid}</b> — {NOMBRE[resultado]}")
        ejes = "ejes globales" if resultado in DEFORMADAS else EJES[resultado]
        self.titulo.setToolTip(f"{'Columna' if modelo.es_columna(eid) else 'Barra'} del nodo {el.ni} al {el.nj}"
                               f" · {NOMBRE[resultado]}: {ejes} · {(self._env or rc).nombre}")
        fl = unidades.factor("longitud")
        self.figura.clear()
        ax = self.figura.add_subplot(111)
        if resultado in DEFORMADAS:
            d = desplazamientos_globales(modelo, rc, eid)
            fd = unidades.factor("desplazamiento")
            claves = [c for c, _ in GLOBALES] if resultado == "deformada" else [resultado]
            for clave in claves:
                ax.plot(d["x"] / fl, d[clave] / fd, color=_color_global(clave), linewidth=1.4,
                        label=f"{SIMBOLO[clave]} (global)")
            if len(claves) > 1:
                ax.legend(fontsize=7, loc="best")
            nombre = "desplazamiento" if len(claves) > 1 else SIMBOLO[resultado]
            ax.set_ylabel(f"{nombre} ({unidades.simbolo('desplazamiento')})", fontsize=8)
        elif self._env is not None:                   # envolvente: la curva de máximos y la de mínimos
            magnitud = magnitud_de(resultado)
            d = self._env.barras[eid]
            maximo, minimo, _imax, _imin = d[resultado]
            x, f = d["x"] / fl, unidades.factor(magnitud)
            for y, estilo in ((maximo / f, "-"), (minimo / f, "--")):
                ax.plot(x, y, color=colores.DIAGRAMA_BORDE, linewidth=1, linestyle=estilo)
                ax.fill_between(x, y, 0, where=y >= 0, color=colores.DIAGRAMA_POSITIVO, alpha=0.55, interpolate=True)
                ax.fill_between(x, y, 0, where=y < 0, color=colores.DIAGRAMA_NEGATIVO, alpha=0.55, interpolate=True)
            if DIRECCION[resultado][1] < 0:
                ax.invert_yaxis()
            ax.set_ylabel(f"{resultado} ({unidades.simbolo(magnitud)})", fontsize=8)
            self.titulo.setText(f"<b>Elemento {eid}</b> — Envolvente de {NOMBRE[resultado]}")
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
        ax.axhline(0, color=colores.INTERFAZ_DESHABILITADO, linewidth=0.8)
        ax.set_xlim(0, self._largo / fl)
        ax.set_xlabel(f"x: distancia desde el nodo {el.ni} ({unidades.simbolo('longitud')})", fontsize=8)
        ax.tick_params(labelsize=7)
        self._linea = ax.axvline(self._x_actual() / fl, color=colores.SELECCIONADO, linewidth=1)
        self.lienzo.draw_idle()
        self._leer(self._x_actual())

    def _leer(self, x):
        """El valor en el corte x (m) de lo que se está viendo, y la línea del corte."""
        if self._eid is None:
            return
        self.x.poner(x)
        if self._resultado in DEFORMADAS:
            d = desplazamientos_globales(self._modelo, self._rc, self._eid, x=[x])
            valores = {clave: float(d[clave][0]) for clave, _ in GLOBALES}
            if self._resultado == "deformada":
                filas = [(simbolo, formato.cantidad(valores[clave], "desplazamiento")) for clave, simbolo in GLOBALES]
                filas.append(("|Δ|", formato.cantidad(float(np.linalg.norm(list(valores.values()))),
                                                      "desplazamiento")))
            else:
                filas = [(SIMBOLO[self._resultado], formato.cantidad(valores[self._resultado], "desplazamiento"))]
        elif self._env is not None:
            vmax, vmin, cmax, cmin = envolvente_en_x(self._env, self._eid, self._resultado, x)
            magnitud = magnitud_de(self._resultado)
            filas = [(f"{self._resultado} máx", formato.cantidad(vmax, magnitud)), ("", cmax),
                     (f"{self._resultado} mín", formato.cantidad(vmin, magnitud)), ("", cmin)]
        else:
            valor = fuerzas_en_x(self._modelo, self._rc, self._eid, x)[self._resultado]
            filas = [(self._resultado, formato.cantidad(valor, magnitud_de(self._resultado)))]

        gris = colores.INTERFAZ_DESHABILITADO

        def fila(nombre, valor):
            if not nombre:                                   # la combinación que da el valor de arriba
                return f"<tr><td colspan=2 style='color:{gris}'>{valor}</td></tr>"
            return f"<tr><td><b>{nombre}</b>&nbsp;&nbsp;</td><td align='right'><b>{valor}</b></td></tr>"

        self.lectura.setText("<table>" + "".join(fila(n, v) for n, v in filas) + "</table>")
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
