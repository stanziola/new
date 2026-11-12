"""Diagramas de interacción (2D y 3D) dentro de Qt.

- DiagramaInteraccion: el dibujo con sus controles (2D o 3D, θ y, en la pestaña de una columna, las
  medidas de su sección, editables).
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
por extremo de la columna (modelo/analisis.demandas_columna). Los dos de la combinación que se ve
arriba (Σ y la lista Combinación) van en rojo; con un caso o la envolvente, ninguno. Una columna de un
pórtico 3D tiene momento en sus dos ejes a la vez, así que cada punto se compara con el corte de la
superficie en la dirección de SU momento:
- 2D: P contra el momento resultante √(My² + Mz²), con la curva de la dirección del punto rojo de mayor
  momento (sin combinación a la vista, la del punto de mayor momento). Los puntos con esa misma
  dirección van rellenos; los demás, huecos (su curva es otra);
- 3D: todos los puntos en su lugar, (Mz, My, P), frente a la superficie.
Sin puntos, el 2D es el de siempre: la curva con la fibra más comprimida hacia θ.

Sección editable (la pestaña de una columna rectangular): b, h, barra, Nx y Ny debajo del dibujo, con
la cuantía. Al terminar un cambio se emite `seccion_editada` y la ventana pone otra sección solo en esa
columna (y, si había resultados, vuelve a analizar): así se ajusta la sección mirando los puntos.
"""
import math
from dataclasses import astuple

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget

from configuracion import colores, formato, unidades
from interfaz import textos
from interfaz.paneles.comunes import CampoNumero, Lista
from modelo import interaccion as concreto

MARCADOR = "o"                  # todos los puntos Pu–Mu, círculos
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
    con_barra: la barra de matplotlib (zoom, mover, guardar), solo en 2D.
    con_edicion: las medidas de la sección, editables (la pestaña de una columna)."""

    seccion_editada = Signal(object)            # (material, b, h, d, barra, nx, ny, fy): medidas nuevas

    def __init__(self, parent=None, con_modo=False, con_barra=True, con_edicion=False):
        super().__init__(parent)
        self.seccion = None
        self.modo = "2D"
        self.puntos = []                        # Demanda de cada combinación y extremo (vacío: sin puntos)
        self.rojos = []                         # índices de los puntos de la combinación a la vista
        self._pista = ""                        # qué decir bajo el gráfico si no hay puntos
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
        # Debajo: la combinación en rojo (o cómo ver los puntos) y la sección editable
        self.pista = QLabel()
        self.pista.setWordWrap(True)
        self.pista.setTextFormat(Qt.RichText)
        self.pista.hide()
        diseno.addWidget(self.pista)
        self.grupo_seccion = None
        if con_edicion:
            self._crear_edicion(diseno)

    # ---------- Sección editable ----------
    def _crear_edicion(self, diseno):
        from interfaz.paneles.formularios import BARRAS, campo_barras, campo_seccion   # aquí: evita un ciclo
        self.grupo_seccion = QGroupBox("Sección de esta columna")
        self.grupo_seccion.setToolTip("Cambiar una medida pone otra sección solo en esta columna (Deshacer la "
                                      "devuelve). Con resultados a la vista, se vuelve a analizar solo")
        forma = QFormLayout(self.grupo_seccion)
        self.campo_b, self.campo_h = campo_seccion(), campo_seccion()
        self.campo_barra = Lista()
        for n in BARRAS:
            self.campo_barra.addItem(f"#{n}", n)
        self.campo_nx, self.campo_ny = campo_barras(), campo_barras()
        fila = QHBoxLayout()
        for texto, campo in (("b", self.campo_b), ("h", self.campo_h)):
            fila.addWidget(QLabel(texto))
            fila.addWidget(campo)
        fila.addStretch(1)
        forma.addRow(fila)
        fila = QHBoxLayout()
        for texto, campo in (("Barra", self.campo_barra), ("Nx", self.campo_nx), ("Ny", self.campo_ny)):
            fila.addWidget(QLabel(texto))
            fila.addWidget(campo)
        fila.addStretch(1)
        forma.addRow(fila)
        self.cuantia = QLabel()
        self.cuantia.setWordWrap(True)
        forma.addRow(self.cuantia)
        for campo in (self.campo_b, self.campo_h, self.campo_nx, self.campo_ny):
            campo.terminado.connect(self._medidas_cambiadas)
        self.campo_barra.currentIndexChanged.connect(self._medidas_cambiadas)
        self.grupo_seccion.hide()
        diseno.addWidget(self.grupo_seccion)

    def _llenar_edicion(self, especial=True):
        """Pone las medidas de la sección a la vista (solo rectangular de concreto) y su cuantía."""
        if self.grupo_seccion is None:
            return
        c = self.seccion.concreto if self.seccion is not None else None
        hay = c is not None and c.forma == "rectangular"
        self.grupo_seccion.setVisible(hay)
        if not hay:
            return
        self.campo_barra.blockSignals(True)
        self.campo_b.poner(c.b)
        self.campo_h.poner(c.h)
        self.campo_nx.poner(c.nx)
        self.campo_ny.poner(c.ny)
        self.campo_barra.setCurrentIndex(max(0, self.campo_barra.findData(c.barra)))
        self.campo_barra.blockSignals(False)
        try:
            p = concreto.propiedades(c)
            aviso = concreto.aviso_cuantia(p["cuantia"], especial)
            self.cuantia.setText(f"{p['nbarras']} #{c.barra}  ·  ρ = {p['cuantia']:.2f} %" + (f" — {aviso}" if aviso else ""))
        except ValueError as e:
            self.cuantia.setText(str(e))

    def _medidas_cambiadas(self, *_):
        c = self.seccion.concreto if self.seccion is not None else None
        if c is None:
            return
        nuevas = (self.campo_b.valor(), self.campo_h.valor(), self.campo_barra.currentData(),
                  int(self.campo_nx.valor()), int(self.campo_ny.valor()))
        actuales = (c.b, c.h, c.barra, c.nx, c.ny)
        if all((abs(x - y) < 1e-9) if isinstance(x, float) else x == y for x, y in zip(nuevas, actuales)):
            return
        b, h, barra, nx, ny = nuevas
        self.seccion_editada.emit((self.seccion.material, b, h, c.d, barra, nx, ny, c.fy))

    # ---------- Qué se muestra ----------
    def mostrar(self, seccion, modo=None, puntos=None, pista="", activa=None, especial=True):
        """Muestra el diagrama de la sección; lo calcula si hace falta. ValueError si los datos no
        sirven (por ejemplo, un refuerzo imposible).

        puntos: lista de Demanda (los puntos Pu–Mu de una columna), o None o vacía si no hay.
        pista: texto bajo el gráfico cuando no hay puntos (por ejemplo, que falta analizar).
        activa: clave de la combinación que se ve arriba: sus puntos van en rojo (None: ninguno).
        especial: pórtico especial (para el aviso de cuantía de la sección editable)."""
        self.seccion = seccion
        if modo is not None:
            self.modo = modo
            if self.selector_modo is not None:
                self.selector_modo.blockSignals(True)
                self.selector_modo.setCurrentIndex(self.selector_modo.findData(modo))
                self.selector_modo.blockSignals(False)
        self.puntos = list(puntos or [])
        self.rojos = [i for i, p in enumerate(self.puntos) if activa is not None and p.clave == activa]
        self._pista = pista
        self._llenar_edicion(especial)
        self.refrescar()

    def _texto_bajo(self):
        """La línea bajo el gráfico: la combinación en rojo con sus puntos, o la pista."""
        if not self.puntos:
            return f"<span style='color:{colores.INTERFAZ_DESHABILITADO}'>{self._pista}</span>" if self._pista else ""
        if not self.rojos:
            return (f"<span style='color:{colores.INTERFAZ_DESHABILITADO}'>{len(self.puntos)} puntos Pu–Mu. Para ver "
                    "uno en rojo, elige una combinación arriba (Σ)</span>")
        partes = [f"{p.lugar}: Pu {formato.cantidad(p.p, 'fuerza')}, M {formato.cantidad(p.m, 'momento')}"
                  for p in (self.puntos[i] for i in self.rojos)]
        return (f"<b style='color:{colores.INTERACCION_ELEGIDO}'>{self.puntos[self.rojos[0]].combinacion}</b> — "
                + " · ".join(partes))

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

    def _referencia(self):
        """El punto que define la dirección del corte 2D: el rojo de mayor momento o, sin rojos, el de
        mayor momento de todos. None si no hay puntos."""
        indices = self.rojos or list(range(len(self.puntos)))
        return self.puntos[max(indices, key=lambda i: self.puntos[i].m)] if indices else None

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
        self.pista.setText(self._texto_bajo())  # en las unidades vigentes
        self.pista.setVisible(bool(self.pista.text()))
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
        elegido = self._referencia()
        if elegido is not None:
            direccion = _plegada(concreto.direccion_momento(elegido.my, elegido.mz)) if elegido.m > 1e-9 else 0.0
            Pn, Mn, PhiPn, PhiMn = self._datos("direccion", direccion)
            titulo = f"{elegido.combinacion}, {elegido.lugar}" if self.rojos else "Puntos Pu–Mu de las combinaciones"
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
            rojo = i in self.rojos
            color = colores.INTERACCION_ELEGIDO if rojo else colores.INTERACCION_PUNTO
            ax.plot(p.m / mu, p.p / fu, MARCADOR, color=color, markersize=9 if rojo else 6,
                    markerfacecolor=color if igual else "none", zorder=4 if rojo else 3)
        if self.puntos:
            ax.plot([], [], MARCADOR, color=colores.INTERACCION_PUNTO, markersize=6, linestyle="none",
                    label="Pu–Mu (combinaciones)")
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
            self.paginas.addWidget(self.vista3d)
        self.vista3d.mostrar(X, Y, Z, [(p.mz, p.my, p.p) for p in self.puntos], self.rojos)

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
