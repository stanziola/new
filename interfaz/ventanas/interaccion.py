"""Diagramas de interacción (2D y 3D) dentro de Qt.

- DiagramaInteraccion: el dibujo con sus controles (2D o 3D, el deslizador de la dirección del momento
  y, en la pestaña de una columna, las medidas de su sección, editables).
  Lo usan la ventana aparte (Ver 2D y Ver 3D de una sección) y la pestaña Interacción de Propiedades
  (columnas).
- VentanaDiagrama: una ventana con un DiagramaInteraccion.
El cálculo está en calculo/interaccion (sagrado); aquí solo se dibuja, en unidades de pantalla.
El 2D se dibuja con matplotlib; el 3D, con VTK (interfaz/vista3d/superficie.py), que se crea la
primera vez que se pide.

Se calcula solo cuando se pide (Ver 2D, Ver 3D o al abrir la pestaña) y lo calculado se guarda en
unidades internas: si cambian las unidades solo se vuelve a dibujar, y lo ya calculado de la misma
sección no se recalcula.

El 2D es siempre el corte de la superficie de interacción en una dirección λ del MOMENTO resultante
(modelo/interaccion.curva_direccion), que se elige con un deslizador de 0° (flexión hacia b, solo Mz)
a 90° (flexión hacia h, solo My); abre en 90°. Con la doble simetría de la sección basta ese cuadrante.
No se usa la curva con la fibra más comprimida hacia θ (biaxial.curva): con θ intermedio no es la
resistencia en esa dirección y da de más (en una 30×60 a 45°, un 34 a 40 %). Cada dirección tarda unos
0.2 s: se calcula al soltar el deslizador (o al dejarlo quieto un momento) y se guarda, a 1°.

Puntos Pu–Mu (solo en la pestaña de una columna, con resultados a la vista): uno por combinación de la
norma (las 13) y por extremo de la columna (modelo/analisis.demandas_columna). Los dos de la
combinación que se ve arriba (Σ y la lista Combinación) van en rojo; con un caso o la envolvente,
ninguno. Una columna de un pórtico 3D tiene momento en sus dos ejes a la vez, así que cada punto se
compara con el corte de la superficie en la dirección de SU momento:
- 2D: P contra el momento resultante √(My² + Mz²). Al llegar los puntos, el deslizador se pone en la
  dirección del punto rojo de mayor momento (sin combinación a la vista, la del punto de mayor
  momento), y se puede mover. Los puntos con la dirección del deslizador van rellenos; los demás,
  huecos (su curva es otra);
- 3D: todos los puntos en su lugar, (Mz, My, P), frente a la superficie.
En los dos, un aviso en rojo dice qué puntos quedan fuera del diagrama de diseño, cada uno revisado
contra la curva de su propia dirección (modelo/interaccion.dentro_del_diagrama). Es un aviso, no la
relación demanda/capacidad del diseño (etapa 4).

Sección editable (la pestaña de una columna rectangular): b, h, barra, Nx y Ny debajo del dibujo, con
la cuantía. Al terminar un cambio se emite `seccion_editada` y la ventana pone otra sección solo en esa
columna (y, si había resultados, vuelve a analizar): así se ajusta la sección mirando los puntos.
"""
import math
from dataclasses import astuple

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QApplication, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QSlider, QStackedWidget,
                               QVBoxLayout, QWidget)

from configuracion import colores, formato, unidades
from interfaz import textos
from interfaz.paneles.comunes import Lista
from modelo import interaccion as concreto

MARCADOR = "o"                  # todos los puntos Pu–Mu, círculos
MISMA_DIRECCION = math.radians(1.0)     # hasta aquí, dos momentos "van en la misma dirección"
DIRECCION_INICIAL = 90          # grados: flexión hacia h (solo My), el eje fuerte si h > b
ESPERA_DESLIZADOR_MS = 150      # quieto este tiempo mientras se arrastra, se calcula esa dirección
MAXIMO_EN_AVISO = 4             # puntos fuera que se nombran en el aviso (los demás, "y N más")
AYUDA_DIRECCION = ("Dirección del momento resultante en el plano de la sección: 0° = flexión hacia b (solo Mz) y "
                   "90° = flexión hacia h (solo My). El diagrama es el corte de la superficie de interacción en esa "
                   "dirección. Por la simetría de la sección, basta de 0° a 90°")


def _plegada(direccion):
    """La dirección llevada al primer cuadrante: la sección es doblemente simétrica, así que el
    diagrama es el mismo para ±My y ±Mz."""
    return math.atan2(abs(math.sin(direccion)), abs(math.cos(direccion)))


class DiagramaInteraccion(QWidget):
    """El diagrama de interacción de una sección de concreto con refuerzo.

    con_modo: agrega la lista 2D / 3D (la pestaña); sin ella, el modo lo da quien lo usa (la ventana).
    con_barra: la barra de matplotlib (zoom, mover, guardar), solo en 2D.
    con_edicion: las medidas de la sección, editables (la pestaña de una columna)."""

    seccion_editada = Signal(object)            # (material, b, h, d, barra, nx, ny, fy, acero): medidas nuevas

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
        # La dirección del momento: un deslizador de 0° a 90° y su valor al lado
        self.etiqueta_direccion = QLabel("M hacia" if con_modo else "Momento hacia")    # corto en la pestaña
        self.direccion = QSlider(Qt.Horizontal)
        self.direccion.setRange(0, 90)
        self.direccion.setSingleStep(1)
        self.direccion.setPageStep(15)
        self.direccion.setValue(DIRECCION_INICIAL)
        self.direccion.setMinimumWidth(100)
        self.valor_direccion = QLabel()
        self.valor_direccion.setMinimumWidth(self.valor_direccion.fontMetrics().horizontalAdvance("90°") + 4)
        for control in (self.etiqueta_direccion, self.direccion, self.valor_direccion):
            control.setToolTip(AYUDA_DIRECCION)
        self._poner_direccion(DIRECCION_INICIAL)
        # Arrastrando se calcula solo cuando el deslizador se queda quieto un momento (o al soltarlo):
        # cada dirección nueva tarda unos 0.2 s
        self._espera = QTimer(self)
        self._espera.setSingleShot(True)
        self._espera.setInterval(ESPERA_DESLIZADOR_MS)
        self._espera.timeout.connect(lambda: self._probar(self.refrescar))
        self.direccion.valueChanged.connect(self._direccion_movida)
        self.direccion.sliderReleased.connect(self._direccion_soltada)
        fila.addWidget(self.etiqueta_direccion)
        fila.addWidget(self.direccion, 1)
        fila.addWidget(self.valor_direccion)
        if not con_modo:
            fila.addStretch(1)                  # en la ventana aparte, el deslizador no ocupa todo el ancho
        diseno.addLayout(fila)
        self.aviso = QLabel()                   # errores del cálculo
        self.aviso.setWordWrap(True)
        self.aviso.hide()
        diseno.addWidget(self.aviso)
        self.alerta = QLabel()                  # puntos Pu–Mu fuera del diagrama de diseño (2D y 3D)
        self.alerta.setWordWrap(True)
        self.alerta.setTextFormat(Qt.RichText)
        self.alerta.hide()
        diseno.addWidget(self.alerta)
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
        self.seccion_editada.emit((self.seccion.material, b, h, c.d, barra, nx, ny, c.fy, c.acero))

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
        referencia = self._referencia()
        if referencia is not None and referencia.m > 1e-9 and seccion.concreto.forma == "rectangular":
            # El deslizador va a la dirección del punto de referencia (y luego se puede mover)
            self._poner_direccion(round(math.degrees(self._plegada_de(referencia))))
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

    def _texto_alerta(self, fuera):
        """El aviso de los puntos fuera del diagrama de diseño (en rojo), o "" si no hay ninguno."""
        if not fuera:
            return ""
        nombres = [f"{p.combinacion} ({p.lugar})" for p in fuera]
        lista = " · ".join(nombres[:MAXIMO_EN_AVISO])
        if len(nombres) > MAXIMO_EN_AVISO:
            lista += f" y {len(nombres) - MAXIMO_EN_AVISO} más"
        cuantos = (f"{len(fuera)} de {len(self.puntos)} puntos Pu–Mu quedan" if len(fuera) > 1
                   else f"1 de {len(self.puntos)} puntos Pu–Mu queda")
        return (f"<span style='color:{colores.INTERACCION_ELEGIDO}'>⚠ <b>{cuantos} fuera del diagrama de "
                f"diseño:</b> {lista}</span>")

    # ---------- Dirección del momento ----------
    def _con_direccion(self):
        """El deslizador se ve en el 2D de una sección rectangular (en la circular la dirección no importa)."""
        return self.modo == "2D" and self.seccion is not None and self.seccion.concreto.forma == "rectangular"

    def _poner_direccion(self, grados):
        """Pone el deslizador en esos grados (sin calcular nada) y su valor al lado."""
        self.direccion.blockSignals(True)
        self.direccion.setValue(int(grados))
        self.direccion.blockSignals(False)
        self.valor_direccion.setText(f"{self.direccion.value()}°")

    def _direccion_movida(self, grados):
        """El deslizador cambió: su valor al lado enseguida y el dibujo cuando se quede quieto."""
        self.valor_direccion.setText(f"{grados}°")
        self._espera.start()

    def _direccion_soltada(self):
        """Al soltar el deslizador se dibuja ya, si quedó algo pendiente."""
        if self._espera.isActive():
            self._espera.stop()
            self._probar(self.refrescar)

    def _direccion_vigente(self):
        """La dirección (rad) del corte que se dibuja: la del deslizador (0 en la circular)."""
        if self.seccion is None or self.seccion.concreto.forma == "circular":
            return 0.0
        return math.radians(self.direccion.value())

    @staticmethod
    def _plegada_de(p):
        """La dirección (rad) del momento del punto p, en el primer cuadrante."""
        return _plegada(concreto.direccion_momento(p.my, p.mz))

    def _direccion_de(self, p):
        """La dirección (rad) de la curva contra la que se revisa el punto p: la de su momento, a 1°. En
        la circular, o si el punto no tiene momento, da igual (el techo y la tracción son los mismos en
        todas las direcciones): la del deslizador, que ya está calculada."""
        if self.seccion.concreto.forma == "circular" or p.m < 1e-9:
            return self._direccion_vigente()
        return math.radians(round(math.degrees(self._plegada_de(p))))

    def _fuera(self):
        """Los puntos que quedan fuera del diagrama de diseño, cada uno revisado contra la curva de SU
        dirección (no contra la que se dibuja)."""
        fuera = []
        for p in self.puntos:
            _pn, _mn, phi_pn, phi_mn = self._datos("direccion", self._direccion_de(p))
            if not concreto.dentro_del_diagrama(phi_pn, phi_mn, p.p, p.m):
                fuera.append(p)
        return fuera

    def _cambio_modo(self, *_):
        self.modo = self.selector_modo.currentData()
        self._probar(self.refrescar)

    def _probar(self, funcion):
        try:
            funcion()
        except ValueError as e:
            self.mostrar_error(f"No se pudo calcular: {e}")

    def _referencia(self):
        """El punto en cuya dirección se pone el deslizador al llegar los puntos (y el del título): el
        rojo de mayor momento o, sin rojos, el de mayor momento de todos. None si no hay puntos."""
        indices = self.rojos or list(range(len(self.puntos)))
        return self.puntos[max(indices, key=lambda i: self.puntos[i].m)] if indices else None

    # ---------- Cálculo (solo lo que falte) ----------
    def _datos(self, que, parametro=0.0):
        """Lo calculado para la sección vigente: "direccion" (el corte en esa dirección del momento, en
        rad) o "superficie". Con el cursor de espera."""
        datos_seccion = astuple(self.seccion.concreto)
        if datos_seccion != self._de_seccion:
            self._calculado, self._de_seccion = {}, datos_seccion
        clave = (que, round(float(parametro), 4))
        if clave not in self._calculado:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                c = self.seccion.concreto
                sec = concreto.propiedades(c)
                if que == "direccion":
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
        for control in (self.etiqueta_direccion, self.direccion, self.valor_direccion):
            control.setVisible(self._con_direccion())
        if self.barra is not None:
            self.barra.setVisible(self.modo == "2D")
        self.pista.setText(self._texto_bajo())  # en las unidades vigentes
        self.pista.setVisible(bool(self.pista.text()))
        self.alerta.setText(self._texto_alerta(self._fuera()))
        self.alerta.setVisible(bool(self.alerta.text()))
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
        circular = self.seccion.concreto.forma == "circular"
        direccion = self._direccion_vigente()
        Pn, Mn, PhiPn, PhiMn = self._datos("direccion", direccion)
        elegido = self._referencia()
        if elegido is not None:
            titulo = f"{elegido.combinacion}, {elegido.lugar}" if self.rojos else "Puntos Pu–Mu de las combinaciones"
        else:
            titulo = "Diagrama de interacción"
        if not circular:
            titulo += f" — momento a {math.degrees(direccion):.0f}°"
        self.figura.clear()
        ax = self.figura.add_subplot(111)
        ax.plot(Mn / mu, Pn / fu, color=colores.ELEMENTO, label="Nominal (Mn, Pn)")
        ax.plot(PhiMn / mu, PhiPn / fu, color=colores.SELECCIONADO, label="Diseño (φMn, φPn)")
        # Relleno: el momento del punto va en la dirección del corte dibujado; hueco: su curva es otra
        iguales = [circular or p.m < 1e-9 or abs(self._plegada_de(p) - direccion) <= MISMA_DIRECCION
                   for p in self.puntos]
        for i, (p, igual) in enumerate(zip(self.puntos, iguales)):
            rojo = i in self.rojos
            color = colores.INTERACCION_ELEGIDO if rojo else colores.INTERACCION_PUNTO
            ax.plot(p.m / mu, p.p / fu, MARCADOR, color=color, markersize=9 if rojo else 6,
                    markerfacecolor=color if igual else "none", zorder=4 if rojo else 3)
        if self.puntos:
            ax.plot([], [], MARCADOR, color=colores.INTERACCION_PUNTO, markersize=6, linestyle="none",
                    label="Pu–Mu (combinaciones)")
            if not all(iguales):
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
