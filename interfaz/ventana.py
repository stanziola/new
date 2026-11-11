"""Ventana principal.

Organización (como ETABS y Civil 3D):
- Arriba: menús con palabras (Archivo, Editar, Ver, Definir, Configuración) y una barra con íconos:
  Deshacer y Rehacer; Caso, Σ y Combinación; Analizar (▶); y los resultados.
- Izquierda: las herramientas que cambian lo que hace el clic (Seleccionar, Nodo, Elemento, Asignar
  sección, Apoyo y cargas) y el Explorador del modelo (pestañas Modelo y Tablas).
- Derecha: Propiedades de lo seleccionado (y, con una columna, la pestaña Interacción).
- Abajo del dibujo: el panel Diagrama (Ver → Diagrama), que muestra para la barra elegida lo mismo
  que está prendido en la barra de arriba.
- Abajo de todo: la barra de comandos (activa solo con Nodo o Elemento) y la barra de estado, con
  la posición del puntero a la izquierda y Rejilla, Snap, Etiquetas, Sección real, Transparencia,
  Cargas, Reacciones y Encuadre a la derecha.
Los paneles se pueden agrandar, mover de lado, cerrar y volver a abrir desde el menú Ver (no se
desacoplan como ventanas sueltas).

Tres estados (los aplica _actualizar_modo; lo que no se usa en cada uno queda en gris):
1. Editar: se cambia el modelo con las herramientas de la izquierda y se ven las cargas del caso
   elegido. Los resultados, Σ y la lista de combinaciones, en gris.
2. Resultados de un caso: se ve la deformada o un diagrama del caso elegido. Las herramientas de la
   izquierda (todas, también Seleccionar) y la lista de combinaciones, en gris. No se dibujan
   cargas. El clic sobre un nodo, un apoyo o una barra sigue seleccionando (para ver sus datos en
   Propiedades y en Diagrama).
3. Resultados de una combinación (Σ marcado): igual, con la lista de casos en gris.
De Editar a los resultados se pasa con ▶ (Analizar), que queda marcado; de vuelta, con otro clic en
▶. Cualquier cambio del modelo vuelve a Editar y borra el análisis.
Los desplazamientos (Deformada ▾: total, Δx, Δy o Δz) van en ejes globales; las fuerzas internas (N,
V, M y T), en los ejes locales de cada barra, que se dibujan sobre la barra seleccionada.
La lógica de cada herramienta está en herramientas.py; la de la rejilla 3D y el snap, en vista3d/rejilla.py.
"""
from pathlib import Path

import numpy as np

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (QApplication, QDockWidget, QFileDialog, QLabel, QLineEdit, QMainWindow, QMenu,
                               QMessageBox, QSizePolicy, QSlider, QToolBar, QToolButton)
from pyvistaqt import QtInteractor

from configuracion import colores
from configuracion import interfaz as ui
from interfaz import textos
from interfaz.vista3d.camara import AnimadorCamara
from interfaz.vista3d.cubo import CuboVistas, viewport_esquina
from interfaz.ventanas.casos import DialogoCasos, DialogoCombinaciones
from interfaz.ventanas.definir import Destino, DialogoDefinir, menu_definir
from interfaz.ventanas.interaccion import VentanaDiagrama
from interfaz.ventanas.dialogo_configuracion import DialogoConfiguracion
from interfaz.vista3d.cargas import dibujar_cargas
from interfaz.vista3d.dibujo import (ModeloDibujado, Previsualizacion, dibujar_ejes_locales, dibujar_modelo,
                                     dibujar_rejilla)
from interfaz.vista3d.resultados import (DEFORMADAS, NOMBRE_DEFORMADA, dibujar_deformada, dibujar_diagrama,
                                         dibujar_reacciones)
from interfaz.paneles.diagrama import PanelDiagrama
from interfaz.paneles.explorador import Explorador
from interfaz.historial import Historial
from interfaz.herramientas import (AgregarApoyo, AgregarCargaBarra, AgregarCargaNodo, AgregarElemento,
                                   AgregarNodo, AsignarSeccion, Seleccionar)
from interfaz.iconos import icono
from interfaz.paneles.comunes import Lista, MenuPersistente, poner_titulo
from interfaz.vista3d.rejilla import Candidato, candidato, geometria_rejilla, interpretar, texto_coordenadas
from interfaz.paneles.propiedades import Propiedades
from interfaz.vista3d.seleccion import elemento_en
from interfaz.ventanas.matriz import VentanaMatriz
from interfaz.tema import aplicar_tema
from modelo import Modelo, archivo
from modelo import combinaciones as comb
from modelo import concreto as cc
from modelo.analisis import analizar, combinar
from modelo.apoyos import TIPOS

TECLAS_A_COMANDOS = set("0123456789.-@")   # escritas sobre la vista, van a la barra de comandos
HERRAMIENTAS_DE_CARGA = ("carga_nodo", "carga_barra")


def _plural(n, palabra):
    return f"{n} {palabra}{'s' if n != 1 else ''}"


def _factor_texto(factor):
    """×236, ×12.5 o ×0.75: el factor de la deformada, sin decimales de más."""
    decimales = 0 if factor >= 100 else 1 if factor >= 10 else 2
    texto = f"{factor:.{decimales}f}"
    return texto.rstrip("0").rstrip(".") if "." in texto else texto


class Ventana(QMainWindow):
    modelo_actualizado = Signal()               # el modelo o las unidades cambiaron (Definir lo escucha)

    def __init__(self, modelo=None, ruta=None):
        super().__init__()
        self.resize(*ui.TAMANO_VENTANA)

        self.modelo = modelo if modelo is not None else Modelo()
        self.ruta = Path(ruta) if ruta else None   # archivo del modelo (None = todavía sin guardar)
        self.modificado = False
        self.seleccion = None                      # ("nodo", id), ("apoyo", id), ("barra", id), ("carga", id) o None
        self.resaltado = None                      # lo que está bajo el mouse con Seleccionar
        self._en_propiedades = None                # lo que muestra el panel Propiedades
        self.dibujado = ModeloDibujado()
        self.rejilla = None                        # rejilla 3D (se rehace en cada redibujar)
        self.candidato = Candidato()               # dónde caería un clic ahora
        self._pos_presion = None                   # dónde se presionó el botón izquierdo
        self._mouse = None                         # última posición del mouse sobre la vista
        self._cerrando = False
        self.diagramas = []                        # ventanas de diagramas de interacción abiertas
        self.historial = Historial()               # Deshacer (Ctrl+Z) y Rehacer (Ctrl+Y)
        self.resultados = None                     # {caso: ResultadoCaso} del último análisis vigente
        self.modo_resultados = False               # True: se ven resultados y no se edita (▶ marcado)
        self.ver_combinaciones = False             # en resultados: se ve una combinación (Σ), no un caso
        self.resultado_visible = None              # None, "deformada", "Dx", "Dy", "Dz", "N", "Vy", "Vz", "T", "My" o "Mz"
        self._ultimo_resultado = "deformada"       # lo último que se vio: es lo que muestra ▶ al entrar
        self.factor_deformada = None               # cuánto se amplificó la deformada dibujada
        self._combinados = {}                      # {clave de combinación: ResultadoCaso} (caché)
        self.opacidad_concreto = 1.0               # de las cajas de la sección real (deslizador de abajo)
        self._transparencia_anterior = 60          # % al que vuelve un clic en el ícono de transparencia
        self._ancho_normal = None                  # ancho de Propiedades antes de ensancharlo (pestaña Interacción)

        # Tres luces blancas: los grises se ven grises (las de pyvista por defecto los tiñen)
        self.vista = QtInteractor(self, lighting="three lights")
        self.setCentralWidget(self.vista)
        # Ejes X (rojo), Y (verde) y Z (azul) abajo a la izquierda: los mismos colores de los ejes
        # locales x, y, z de la barra seleccionada
        self.vista.add_axes(x_color=colores.EJE_X, y_color=colores.EJE_Y, z_color=colores.EJE_Z)
        self.animador = AnimadorCamara(self.vista)  # giro suave de la cámara (cubo y Encuadre)
        self.previsualizacion = Previsualizacion(self.vista)
        self.ventana_matriz = VentanaMatriz(self)

        self._crear_paneles()
        self._crear_menus()
        self._crear_barra_definir()
        self._crear_herramientas()
        self._crear_barra_comandos()
        self._crear_barra_inferior()

        self._actualizar_modo()
        self.redibujar(reiniciar_camara=True)
        self.cubo = CuboVistas(self.vista, self.animador)   # cubo de vistas, arriba a la derecha
        self.explorador.actualizar(self.modelo, self.caso_activo())
        self._mostrar_propiedades(None)
        self._actualizar_titulo()
        self._actualizar_deshacer()
        self.actualizar_indicacion()
        self._actualizar_puntero()

        iren = self.vista.iren
        # Clic = presionar y soltar casi en el mismo punto. Arrastrar sigue rotando la vista.
        iren.add_observer("LeftButtonPressEvent", self._al_presionar)
        iren.add_observer("LeftButtonReleaseEvent", self._al_soltar)
        # Si el usuario desplaza o hace zoom a mitad de un giro, manda el usuario.
        for evento in ("MiddleButtonPressEvent", "RightButtonPressEvent",
                       "MouseWheelForwardEvent", "MouseWheelBackwardEvent"):
            iren.add_observer(evento, lambda *_: self.animador.detener())
        iren.add_observer("MouseMoveEvent", self._al_mover)
        iren.add_observer("LeaveEvent", self._al_salir)
        self.vista.installEventFilter(self)       # números escritos sobre la vista -> comandos
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.activated.connect(self.cancelar)

    def _accion(self, nombre_icono, texto, ayuda, activable=False, activa=False, atajo=None):
        """Botón (QAction) con ícono, tooltip y, si se pide, atajo de teclado."""
        accion = QAction(icono(nombre_icono), texto, self)
        accion.setToolTip(ayuda)
        accion.setCheckable(activable)
        accion.setChecked(activa)
        if atajo:
            accion.setShortcut(QKeySequence(atajo))
        return accion

    # ---------- Paneles (izquierda, derecha y abajo) ----------
    def _crear_paneles(self):
        self.explorador = Explorador(self)
        self.propiedades = Propiedades(self)
        self.diagrama = PanelDiagrama(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.explorador)
        self.addDockWidget(Qt.RightDockWidgetArea, self.propiedades)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.diagrama)
        # Las esquinas de abajo son de los paneles de los lados: el Diagrama queda solo bajo el dibujo
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        for panel in (self.explorador, self.propiedades, self.diagrama):   # sin el botón de desacoplar
            panel.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
            poner_titulo(panel)                                            # la x sola, sin recuadro
        self.resizeDocks([self.explorador, self.propiedades], [260, 300], Qt.Horizontal)
        self.diagrama.hide()                                               # se abre desde Ver → Diagrama
        self.diagrama.visibilityChanged.connect(lambda visible: visible and self._refrescar_diagrama())
        self.explorador.elegido.connect(self._elegido_en_explorador)
        self.explorador.vaciado.connect(lambda: self.seleccionar(None))
        self.propiedades.ver_diagrama.connect(self.ver_diagrama)
        self.propiedades.asignar_seccion.connect(self._asignar_seccion)
        self.propiedades.editar_seccion.connect(self._editar_seccion)
        self.propiedades.interaccion_a_la_vista.connect(self._ancho_propiedades)
        # Materiales y secciones desde el Explorador: se muestran y se editan en Propiedades
        self.destino = Destino(self, self.propiedades.panel, self._ver_en_propiedades)
        self.propiedades.cancelar_definicion.connect(lambda: self._mostrar_propiedades(self._en_propiedades))
        self.explorador.doble_clic.connect(lambda info: self.destino.editar(*info))
        self.explorador.menu_pedido.connect(self._menu_definir)
        self._dialogos_definir = {}               # "material" y "seccion": una ventana para cada uno

    def _ancho_propiedades(self, interaccion):
        """Con la pestaña Interacción a la vista, el panel Propiedades se ensancha para que el
        diagrama se aprecie (ui.ANCHO_PANEL_INTERACCION, sin pasar del 60 % de la ventana); al volver
        a la pestaña Propiedades, o al dejar de tener una columna elegida, recupera el ancho que
        tenía."""
        if interaccion:
            self._ancho_normal = self.propiedades.width()
            ancho = max(self._ancho_normal, min(ui.ANCHO_PANEL_INTERACCION, int(0.6 * self.width())))
        elif self._ancho_normal is not None:
            ancho, self._ancho_normal = self._ancho_normal, None
        else:
            return
        self.resizeDocks([self.propiedades], [ancho], Qt.Horizontal)

    def _mostrar_propiedades(self, item):
        """Propiedades muestra lo seleccionado, salvo que la herramienta use el panel (Apoyo...).
        También pone al día el panel Diagrama, que sigue a la barra seleccionada."""
        self._en_propiedades = item
        if not self.herramienta.mostrar_panel():
            caso = None if self.modo_combinaciones else self.caso_activo()
            self.propiedades.mostrar(self.modelo, item, caso=caso, rc=self._rc(),
                                     editable=not self.modo_resultados)
        self._refrescar_diagrama()

    def _refrescar_diagrama(self):
        """El panel Diagrama: la barra seleccionada (o la de la carga elegida), con el caso o la
        combinación activos y el resultado prendido arriba. Si el panel está cerrado no se calcula."""
        if not hasattr(self, "diagrama") or not self.diagrama.isVisible():
            return
        elegido = self._en_3d(self.seleccion)
        eid = elegido[1] if elegido and elegido[0] == "barra" else None
        self.diagrama.mostrar(self.modelo, self._rc(), eid, self.resultado_visible)

    def _tipo_apoyo(self, tipo):
        self.herramienta_apoyo.tipo = tipo

    def _seccion_a_asignar(self, sid):
        self.herramienta_asignar.seccion = sid

    def _ver_en_propiedades(self, item):
        """Después de guardar o eliminar en Propiedades: lo que debe quedar a la vista."""
        self.seleccion = None
        self._en_propiedades = item

    def _menu_definir(self, info, posicion):
        menu = menu_definir(self, info, self.modelo, self.destino)
        if menu is not None:
            menu.exec(posicion)

    def abrir_definir(self, tipo="material"):
        """La ventana de Materiales o la de Secciones (una de cada una)."""
        dialogo = self._dialogos_definir.get(tipo)
        if dialogo is None:
            dialogo = self._dialogos_definir[tipo] = DialogoDefinir(self, tipo)
        dialogo.actualizar()
        dialogo.show()
        dialogo.raise_()
        dialogo.activateWindow()
        return dialogo

    def abrir_casos(self):
        """Definir → Casos de carga (con Aceptar, un paso de Deshacer)."""
        DialogoCasos(self).exec()

    def abrir_combinaciones(self):
        """Definir → Combinaciones de carga (con Aceptar, un paso de Deshacer)."""
        DialogoCombinaciones(self).exec()

    def _elegido_en_explorador(self, item):
        tipo, ident = item
        if tipo in ("nodo", "apoyo", "barra", "carga"):
            self.seleccionar(item)
        elif tipo == "matriz":
            self.seleccionar(("barra", ident))
            self.ventana_matriz.mostrar(self.modelo, ident)
        elif tipo in ("seccion", "material"):
            self.seleccionar(None)
            self._mostrar_propiedades(item)

    def ver_diagrama(self, sid, modo):
        """Abre la ventana del diagrama de interacción (2D o 3D) de la sección sid."""
        sec = self.modelo.secciones.get(sid)
        if sec is None or sec.concreto is None:
            return None
        try:
            ventana = VentanaDiagrama(sec, modo, self)
        except ValueError as e:
            QMessageBox.warning(self, "Diagrama de interacción", f"No se pudo calcular:\n\n{e}")
            return None
        ventana.setAttribute(Qt.WA_DeleteOnClose)
        self.diagramas.append(ventana)
        ventana.destroyed.connect(lambda *_, v=ventana: self.diagramas.remove(v) if v in self.diagramas else None)
        ventana.show()
        return ventana

    # ---------- Menús y barra de arriba ----------
    def _crear_menus(self):
        menu = self.menuBar().addMenu("Archivo")
        for texto, atajo, funcion in (("Nuevo", "Ctrl+N", self.nuevo),
                                      ("Abrir…", "Ctrl+O", self.abrir),
                                      ("Guardar", "Ctrl+S", self.guardar),
                                      ("Guardar como…", "Ctrl+Shift+S", self.guardar_como)):
            accion = menu.addAction(texto)
            accion.setShortcut(QKeySequence(atajo))
            accion.triggered.connect(lambda *_, f=funcion: f())

        editar = self.menuBar().addMenu("Editar")
        self.accion_deshacer = self._accion("deshacer", "Deshacer", "Deshacer (Ctrl+Z)", atajo="Ctrl+Z")
        self.accion_rehacer = self._accion("rehacer", "Rehacer", "Rehacer (Ctrl+Y)", atajo="Ctrl+Y")
        self.accion_eliminar = QAction("Eliminar", self)
        self.accion_eliminar.setShortcut(QKeySequence(Qt.Key_Delete))
        self.accion_deshacer.triggered.connect(self.deshacer)
        self.accion_rehacer.triggered.connect(self.rehacer)
        self.accion_eliminar.triggered.connect(self.eliminar)
        for accion in (self.accion_deshacer, self.accion_rehacer):
            editar.addAction(accion)
        self.addAction(self.accion_eliminar)      # no está en el menú, pero Supr sigue borrando

        ver = MenuPersistente("Ver", self)                  # no se cierra al prender o apagar un panel
        self.menuBar().addMenu(ver)
        ver.addAction(self.explorador.toggleViewAction())
        ver.addAction(self.propiedades.toggleViewAction())
        ver.addAction(self.diagrama.toggleViewAction())

        definir = self.menuBar().addMenu("Definir")         # etapas 1 y 3 de la hoja de ruta
        definir.setToolTipsVisible(True)
        self.accion_material = self._accion("material", "Materiales…", "Materiales de concreto: crear, editar y eliminar")
        self.accion_seccion = self._accion("seccion", "Secciones…", "Secciones de concreto: crear, editar y eliminar")
        self.accion_material.triggered.connect(lambda *_: self.abrir_definir("material"))
        self.accion_seccion.triggered.connect(lambda *_: self.abrir_definir("seccion"))
        self.accion_casos = QAction("Casos de carga…", self)
        self.accion_casos.setToolTip("Casos de carga: peso propio, carga muerta adicional y los que agregues "
                                     "(viva, muerta, viento o sismo)")
        self.accion_casos.triggered.connect(lambda *_: self.abrir_casos())
        self.accion_combinaciones = QAction("Combinaciones de carga…", self)
        self.accion_combinaciones.setToolTip("Combinaciones: las predeterminadas (ASCE 7-05), SDS y ρ, y las "
                                             "tuyas. Solo para ver resultados")
        self.accion_combinaciones.triggered.connect(lambda *_: self.abrir_combinaciones())
        for accion in (self.accion_material, self.accion_seccion):
            definir.addAction(accion)
        definir.addSeparator()
        for accion in (self.accion_casos, self.accion_combinaciones):
            definir.addAction(accion)

        self.accion_configuracion = self.menuBar().addAction("Configuración")
        self.accion_configuracion.triggered.connect(self.abrir_configuracion)

    def _crear_barra_definir(self):
        self.barra_definir = QToolBar("Barra de arriba", self)
        self.barra_definir.setObjectName("definir")
        self.barra_definir.setMovable(False)
        self.barra_definir.setFloatable(False)
        self.barra_definir.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        self.barra_definir.addAction(self.accion_deshacer)
        self.barra_definir.addAction(self.accion_rehacer)
        self.barra_definir.addSeparator()
        # Caso, Σ (ver una combinación) y Combinación; lo que no se usa queda en gris
        self.etiqueta_caso = QLabel(" Caso ")
        self.barra_definir.addWidget(self.etiqueta_caso)
        self.selector_caso = Lista()               # abre hacia abajo; el caso vigente, sombreado
        self.selector_caso.setToolTip("Caso de carga. Editando: las cargas nuevas van a este caso y se ven las "
                                      "suyas. Con resultados: se ven los de este caso")
        self.selector_caso.currentIndexChanged.connect(self._cambio_caso)
        self.barra_definir.addWidget(self.selector_caso)
        self.accion_ver_combinaciones = self._accion(
            "combinaciones", "Combinaciones",
            "Σ: ver los resultados de una combinación en vez de los de un caso (disponible con resultados "
            "a la vista). Se definen en Definir → Combinaciones de carga", activable=True)
        self.accion_ver_combinaciones.triggered.connect(self._cambio_fuente)
        self.barra_definir.addAction(self.accion_ver_combinaciones)
        self.etiqueta_combinacion = QLabel(" Combinación ")
        self.barra_definir.addWidget(self.etiqueta_combinacion)
        self.selector_combinacion = Lista()
        self.selector_combinacion.setToolTip("Combinación cuyos resultados se muestran (con Σ marcado)")
        self.selector_combinacion.currentIndexChanged.connect(self._cambio_combinacion)
        self.barra_definir.addWidget(self.selector_combinacion)
        self.barra_definir.addSeparator()
        self.accion_analizar = self._accion("analizar", "Analizar",
                                            "Analizar (▶): resuelve todos los casos y pasa a ver los resultados. "
                                            "Otro clic aquí vuelve a editar", activable=True)
        self.accion_analizar.triggered.connect(self._alternar_resultados)
        self.barra_definir.addAction(self.accion_analizar)
        self.barra_definir.addSeparator()
        # Resultados: uno a la vez (otro clic sobre el activo lo apaga). Los desplazamientos van en
        # ejes globales; las fuerzas internas, en los locales de cada barra
        self.botones_resultado = {}
        for clave, icono_, texto, opciones in (
                ("deformada", "deformada", "Deformada",
                 (("deformada", "Total: la deformada completa"),
                  ("Dx", "Δx: solo el desplazamiento en X global"),
                  ("Dy", "Δy: solo el desplazamiento en Y global"),
                  ("Dz", "Δz: solo el desplazamiento en Z global"))),
                ("N", "axial", "Axial (N): a lo largo de x local; tracción +", None),
                ("V", "cortante", "Cortante", (("Vy", "Vy: en el plano x–y local"), ("Vz", "Vz: en el plano x–z local"))),
                ("M", "momento", "Momento", (("My", "My: alrededor de y local (flexión en x–z)"),
                                              ("Mz", "Mz: alrededor de z local (flexión en x–y)"))),
                ("T", "torsion", "Torsión (T): alrededor de x local", None)):
            boton = QToolButton()
            boton.setIcon(icono(icono_))
            boton.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
            boton.setCheckable(True)
            boton.setEnabled(False)
            if opciones:
                boton.setToolTip(f"{texto}: elige " + ("qué ver" if clave == "deformada" else "el eje"))
                boton.setPopupMode(QToolButton.InstantPopup)
                menu = QMenu(boton)
                for componente, descripcion in opciones:
                    accion = menu.addAction(descripcion)
                    accion.triggered.connect(lambda *_, c=componente: self.ver_resultado(c))
                boton.setMenu(menu)
            else:
                boton.setToolTip(texto)
                boton.clicked.connect(lambda *_, c=clave: self.ver_resultado(c))
            self.barra_definir.addWidget(boton)
            self.botones_resultado[clave] = boton
        self.addToolBar(Qt.TopToolBarArea, self.barra_definir)
        self._llenar_casos()
        self._llenar_combinaciones()

    # ---------- Casos, combinaciones, análisis y los tres estados ----------
    @property
    def modo_combinaciones(self):
        """True si lo que se ve son los resultados de una combinación (estado 3)."""
        return self.modo_resultados and self.ver_combinaciones

    def _llenar_casos(self):
        """La lista Caso, con el modelo vigente. Si lo elegido ya no existe, queda el caso inicial
        (Carga muerta adicional), que es donde van las cargas."""
        actual = self.selector_caso.currentData()
        self.selector_caso.blockSignals(True)
        self.selector_caso.clear()
        for cid, caso in self.modelo.casos.items():
            self.selector_caso.addItem(f"{caso.nombre} ({caso.tipo})", cid)
        i = self.selector_caso.findData(actual)
        if i < 0:
            i = self.selector_caso.findData(self.modelo.caso_inicial())
        self.selector_caso.setCurrentIndex(max(i, 0))
        self.selector_caso.blockSignals(False)

    def _llenar_combinaciones(self):
        """La lista Combinación: las predeterminadas (con el SDS y el ρ del modelo) y las propias."""
        actual = self.selector_combinacion.currentData()
        self.selector_combinacion.blockSignals(True)
        self.selector_combinacion.clear()
        for clave, co in comb.todas(self.modelo).items():
            self.selector_combinacion.addItem(co.nombre, clave)
            if comb.es_predeterminada(clave):
                self.selector_combinacion.setItemData(self.selector_combinacion.count() - 1,
                                                      comb.referencia(clave), Qt.ToolTipRole)
        i = self.selector_combinacion.findData(actual)
        self.selector_combinacion.setCurrentIndex(max(i, 0))
        self.selector_combinacion.blockSignals(False)

    def caso_activo(self):
        caso = self.selector_caso.currentData()
        return caso if caso in self.modelo.casos else self.modelo.caso_inicial()

    def combinacion_activa(self):
        """Clave de la combinación elegida ("D", "C1", "C3a"… o el ID de una propia), o None."""
        clave = self.selector_combinacion.currentData()
        return clave if clave in comb.todas(self.modelo) else None

    def _cambio_caso(self, *_):
        self.redibujar()
        self._refrescar_paneles()
        if not self.modo_resultados and self.modelo.es_automatico(self.caso_activo()):
            self.mensaje("Peso propio: automático (A·γ de cada barra). Las cargas a mano van en otro caso")
        else:
            self._aviso_deformada()

    def _cambio_combinacion(self, *_):
        if self.modo_combinaciones:
            self._cambio_caso()

    def _cambio_fuente(self, marcado):
        """Σ: se ven los resultados de una combinación (marcado) o los de un caso."""
        self.ver_combinaciones = bool(marcado)
        self.redibujar()
        self._refrescar_paneles()
        self._aviso_deformada("Resultados de la combinación. " if self.modo_combinaciones
                              else "Resultados del caso. ")

    def _actualizar_modo(self):
        """Aplica el estado vigente (ver la tabla del principio): habilita lo que se usa en él y deja
        en gris lo demás."""
        resultados, combos = self.modo_resultados, self.modo_combinaciones
        self.accion_analizar.setChecked(resultados)
        self.accion_ver_combinaciones.setEnabled(resultados)
        self.accion_ver_combinaciones.setChecked(combos)
        for widget in (self.etiqueta_caso, self.selector_caso):
            widget.setEnabled(not combos)
        for widget in (self.etiqueta_combinacion, self.selector_combinacion):
            widget.setEnabled(combos)
        self._actualizar_resultados()
        self.accion_cargas.setEnabled(not resultados)        # las cargas se ven al editar
        self.accion_reacciones.setEnabled(resultados)        # las reacciones, con resultados
        # Herramientas: con resultados quedan todas en gris, también Seleccionar (el clic sobre un
        # nodo o una barra sigue seleccionando: es la herramienta activa, aunque su botón no se
        # pueda tocar). En el caso de peso propio (automático) no se ponen cargas a mano
        automatico = self.modelo.es_automatico(self.caso_activo())
        for nombre, (accion, _h) in self._por_nombre.items():
            accion.setEnabled(not resultados and not (automatico and nombre in HERRAMIENTAS_DE_CARGA))
        actual = next(accion for accion, h in self._herramientas if h is self.herramienta)
        if not actual.isEnabled():
            self.usar_herramienta(self._por_nombre["seleccionar"][1])

    def _rc(self):
        """Resultados que se muestran: los de la combinación (con Σ) o los del caso elegido. None si
        se está editando o no hay análisis vigente."""
        if not self.modo_resultados or not self.resultados:
            return None
        if self.ver_combinaciones:
            clave = self.combinacion_activa()
            if clave is None:
                return None
            if clave not in self._combinados:
                self._combinados[clave] = combinar(self.modelo, self.resultados, comb.todas(self.modelo)[clave])
            return self._combinados[clave]
        return self.resultados.get(self.caso_activo())

    def _alternar_resultados(self, marcado):
        """▶: entra a los resultados (analizando si hace falta) o vuelve a editar."""
        if marcado:
            self.analizar()
        else:
            self.salir_de_resultados()

    def analizar(self):
        """Resuelve todos los casos (si el análisis vigente ya no sirve) y pasa a ver resultados: lo
        último que se vio, o la deformada."""
        if self.resultados is None:
            try:
                self.resultados = analizar(self.modelo)
            except (ValueError, KeyError) as e:
                self.resultados = None
                QMessageBox.warning(self, "Analizar", f"No se pudo analizar:\n\n{e}")
                self._actualizar_modo()            # ▶ vuelve a quedar sin marcar
                return
            self._combinados = {}
        self.modo_resultados = True
        self.resultado_visible = self._ultimo_resultado
        self.redibujar()
        self._refrescar_paneles()
        self._aviso_deformada("Análisis listo. ")

    def salir_de_resultados(self, *_):
        """Vuelve a Editar (otro clic en ▶). El análisis sigue vigente mientras el modelo no cambie:
        ▶ lo vuelve a mostrar sin recalcular."""
        if not self.modo_resultados:
            return
        self._ultimo_resultado = self.resultado_visible or self._ultimo_resultado
        self.modo_resultados = False
        self.resultado_visible = None
        self.redibujar()
        self._refrescar_paneles()
        self.mensaje("Editar. Para ver los resultados otra vez: ▶")

    def _invalidar_resultados(self):
        """El modelo cambió: los resultados ya no valen. Se vuelve a Editar (hay que analizar de
        nuevo). Quien llama pone después los botones al día (_actualizar_modo)."""
        if self.resultados is not None:
            self.mensaje("El modelo cambió: vuelve a analizar (▶)")
        self.resultados = None
        self._combinados = {}
        self._ultimo_resultado = self.resultado_visible or self._ultimo_resultado
        self.modo_resultados = False
        self.resultado_visible = None

    def ver_resultado(self, componente):
        """Muestra la deformada o un diagrama; otro clic sobre el mismo lo apaga."""
        self.resultado_visible = None if componente == self.resultado_visible else componente
        self._ultimo_resultado = self.resultado_visible or self._ultimo_resultado
        self._actualizar_resultados()
        self.redibujar()
        self._mostrar_propiedades(self._en_propiedades)
        self._aviso_deformada()

    def _aviso_deformada(self, antes=""):
        """Aviso: `antes` y, con la deformada a la vista, cuánto se amplificaron los desplazamientos
        (×1 sería el tamaño real). Si se pidió una sola componente y es cero, lo dice."""
        if self.resultado_visible in DEFORMADAS and self._rc() is not None:
            cual = NOMBRE_DEFORMADA[self.resultado_visible]
            if self.factor_deformada is None:
                self.mensaje(f"{antes}Deformada {cual}: sin desplazamientos"
                             + (" en esa dirección" if self.resultado_visible != "deformada" else ""))
            else:
                tipo = "automática" if ui.DEFORMADA_AUTOMATICA else "fija"
                self.mensaje(f"{antes}Deformada {cual} ×{_factor_texto(self.factor_deformada)} "
                             f"({tipo}; 1 = tamaño real)")
        elif antes:
            self.mensaje(antes.strip())

    def _actualizar_resultados(self):
        """Los botones de resultados: habilitados con resultados a la vista y marcado el que se ve."""
        grupo = {"N": "N", "Vy": "V", "Vz": "V", "T": "T", "My": "M", "Mz": "M", **dict.fromkeys(DEFORMADAS, "deformada")}
        activo = grupo.get(self.resultado_visible)
        for clave, boton in self.botones_resultado.items():
            boton.setEnabled(self.modo_resultados)
            boton.setChecked(clave == activo)

    # ---------- Herramientas (izquierda) ----------
    def _crear_herramientas(self):
        self.herramientas = QToolBar("Herramientas", self)
        self.herramientas.setObjectName("herramientas")   # la hoja de estilo le pone un borde
        self.herramientas.setMovable(False)
        self.herramientas.setFloatable(False)
        self.herramientas.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        self.addToolBar(Qt.LeftToolBarArea, self.herramientas)

        grupo = QActionGroup(self)                 # una sola herramienta activa a la vez
        self._herramientas = []                    # (acción, herramienta)
        self._por_nombre = {}                      # nombre -> (acción, herramienta)
        for nombre, texto, ayuda, clase in (
                ("seleccionar", "Seleccionar", "Seleccionar: clic sobre un nodo, un apoyo o una barra", Seleccionar),
                ("nodo", "Nodo", "Agregar nodo: clic sobre un punto de la rejilla o escribe x, y, z", AgregarNodo),
                ("elemento", "Elemento", "Agregar elemento: clic en el punto inicial y en el final "
                 "(queda sin sección)", AgregarElemento),
                ("asignar_seccion", "Asignar sección", "Asignar sección: elige la sección en Propiedades y "
                 "haz clic sobre cada barra (lleva también su material)", AsignarSeccion),
                ("apoyo", "Apoyo", "Apoyo: elige el tipo en Propiedades y haz clic sobre un nodo",
                 AgregarApoyo),
                ("carga_nodo", "Carga en nodo", "Carga en nodo: escribe los valores en Propiedades y haz clic "
                 "sobre un nodo", AgregarCargaNodo),
                ("carga_barra", "Carga en barra", "Carga en barra: elige el tipo y el valor en Propiedades y "
                 "haz clic sobre una barra", AgregarCargaBarra)):
            accion = self._accion(nombre, texto, ayuda, activable=True)
            herramienta = clase(self)
            accion.triggered.connect(lambda *_, h=herramienta: self.usar_herramienta(h))
            grupo.addAction(accion)
            self.herramientas.addAction(accion)
            self._herramientas.append((accion, herramienta))
            self._por_nombre[nombre] = (accion, herramienta)
        self.accion_seleccionar, self.herramienta = self._por_nombre["seleccionar"]
        self.herramienta_apoyo = self._por_nombre["apoyo"][1]
        self.herramienta_asignar = self._por_nombre["asignar_seccion"][1]
        self.propiedades.panel_apoyo.cambiado.connect(self._tipo_apoyo)
        self.propiedades.panel_asignar.cambiado.connect(self._seccion_a_asignar)
        self.propiedades.panel_asignar.definir.connect(lambda: self.abrir_definir("seccion"))
        self.accion_seleccionar.setChecked(True)   # herramienta por defecto

    def usar_herramienta(self, herramienta):
        """Cambia la herramienta activa (desde su botón o desde el código)."""
        for accion, h in self._herramientas:
            if h is herramienta:
                accion.setChecked(True)
        if herramienta is self.herramienta:
            return
        self.herramienta.cancelar()
        self.herramienta = herramienta
        self.comando.clear()
        self.resaltado = None                      # el resaltado es solo de Seleccionar
        if herramienta.muestra_cargas and not self.accion_cargas.isChecked():
            self.accion_cargas.setChecked(True)    # para ver la carga que se va a poner
        self.pintar()
        self._mostrar_propiedades(self.seleccion)  # el panel de la herramienta, o de nuevo lo seleccionado
        self.actualizar_indicacion()
        self._actualizar_puntero()

    # ---------- Barra de comandos (abajo) ----------
    def _crear_barra_comandos(self):
        self.barra_comandos = QToolBar("Comandos", self)
        self.barra_comandos.setObjectName("barra_comandos")
        self.barra_comandos.setMovable(False)
        self.barra_comandos.setFloatable(False)
        self.comando = QLineEdit()                 # coordenadas exactas; la guía es la plantilla gris
        self.comando.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.comando.returnPressed.connect(self._ejecutar_comando)
        self.comando.textChanged.connect(self._validar_comando)
        self.aviso = QLabel()                      # avisos cortos ("Nodo 6 agregado")
        for widget in (self.comando, self.aviso):
            self.barra_comandos.addWidget(widget)
        self.addToolBar(Qt.BottomToolBarArea, self.barra_comandos)
        self._reloj_aviso = QTimer(self)
        self._reloj_aviso.setSingleShot(True)
        self._reloj_aviso.timeout.connect(self.aviso.clear)

    def actualizar_indicacion(self):
        """Plantilla de la barra de comandos. Solo está activa con Nodo o Elemento."""
        self.comando.setPlaceholderText(self.herramienta.indicacion())
        self.barra_comandos.setEnabled(self.herramienta.usa_previsualizacion)
        self._validar_comando()

    def comando_valido(self, texto=None):
        """True si lo escrito ya es un punto válido (se puede colocar con Enter)."""
        texto = self.comando.text() if texto is None else texto
        if not texto.strip() or self.rejilla is None:
            return False
        try:
            interpretar(texto, self.rejilla, self.herramienta.ultimo_punto())
        except ValueError:
            return False
        return True

    def _validar_comando(self, *_):
        """Gris mientras lo escrito todavía no es un punto válido; negro cuando ya lo es."""
        paleta = self.comando.palette()
        color = colores.INTERFAZ_TEXTO if self.comando_valido() else colores.INTERFAZ_DESHABILITADO
        paleta.setColor(QPalette.Text, QColor(color))
        self.comando.setPalette(paleta)

    def mensaje(self, texto):
        """Aviso corto en la barra de comandos; se borra solo."""
        self.aviso.setText(texto)
        self._reloj_aviso.start(ui.DURACION_MENSAJE_MS)

    def _ejecutar_comando(self):
        texto = self.comando.text().strip()
        if not texto:
            return
        try:
            punto = interpretar(texto, self.rejilla, self.herramienta.ultimo_punto())
        except ValueError as e:
            self.mensaje(str(e))
            self.comando.selectAll()               # lo próximo que se escriba lo reemplaza
            return
        self.comando.clear()
        self.herramienta.punto_escrito(punto)
        self.actualizar_indicacion()
        self._actualizar_puntero()

    def cancelar(self):
        """Esc: cancela lo que esté a medias; si no hay nada, vuelve a Seleccionar o deselecciona."""
        self.comando.clear()
        seleccionar = self._por_nombre["seleccionar"][1]
        if self.herramienta.cancelar():
            self.mensaje("Cancelado")
        elif self.herramienta is not seleccionar:
            self.usar_herramienta(seleccionar)
        elif self.seleccion is not None:
            self.seleccionar(None)
        self.actualizar_indicacion()
        self._actualizar_puntero()

    def eventFilter(self, objeto, evento):
        if objeto is self.vista and evento.type() == QEvent.Resize and hasattr(self, "cubo"):
            # La vista cambió de tamaño (la ventana, o un panel que se ensancha): el cubo y los ejes
            # vuelven a quedar cuadrados, después de que la vista tome su tamaño
            QTimer.singleShot(0, self._ajustar_y_dibujar)
        if (objeto is self.vista and evento.type() == QEvent.KeyPress and evento.text()
                and evento.text() in TECLAS_A_COMANDOS and self.barra_comandos.isEnabled()
                and not evento.modifiers() & (Qt.ControlModifier | Qt.AltModifier)):
            if not self.comando.hasFocus():
                self.comando.clear()               # escribir sobre la vista empieza un comando nuevo
            self.comando.setFocus()
            self.comando.insert(evento.text())
            return True
        return super().eventFilter(objeto, evento)

    # ---------- Barra inferior: coordenadas y vista ----------
    def _crear_barra_inferior(self):
        barra = QToolBar("Vista", self)
        barra.setObjectName("barra_inferior")
        barra.setMovable(False)
        barra.setFloatable(False)
        tamano = QSize(ui.TAMANO_ICONO_INFERIOR, ui.TAMANO_ICONO_INFERIOR)
        barra.setIconSize(tamano)

        self.accion_rejilla = self._accion("rejilla", "Rejilla", f"Rejilla ({ui.ATAJO_REJILLA})",
                                           activable=True, activa=ui.REJILLA_VISIBLE, atajo=ui.ATAJO_REJILLA)
        self.accion_rejilla.toggled.connect(lambda *_: self._aplicar_visibilidad())
        self.accion_snap = self._accion("snap", "Snap",
                                        f"Snap ({ui.ATAJO_SNAP}): pega el punto a nodos y a la rejilla",
                                        activable=True, activa=ui.SNAP_ACTIVO, atajo=ui.ATAJO_SNAP)
        self.accion_snap.toggled.connect(lambda *_: self._actualizar_puntero())
        self.boton_etiquetas = QToolButton()
        self.boton_etiquetas.setIcon(icono("etiqueta"))
        self.boton_etiquetas.setIconSize(tamano)
        self.boton_etiquetas.setToolTip("Etiquetas: qué textos se ven en el dibujo, y los ejes locales de la "
                                        "barra seleccionada")
        self.boton_etiquetas.setPopupMode(QToolButton.InstantPopup)
        menu = MenuPersistente(self.boton_etiquetas)
        self.etiquetas = {}
        for nombre, texto, activa in (("etiquetas", "Números de nodo", ui.ETIQUETAS_VISIBLES),
                                      ("numeros_barras", "Números de barra", False),
                                      ("valores_cargas", "Valores de las cargas", True),
                                      ("valores_resultados", "Valores de los resultados", True),
                                      ("valores_reacciones", "Valores de las reacciones", True),
                                      ("ejes_locales", "Ejes locales de la barra seleccionada",
                                       ui.EJES_LOCALES_VISIBLES)):
            accion = menu.addAction(texto)
            accion.setCheckable(True)
            accion.setChecked(activa)
            accion.toggled.connect(lambda *_: self._aplicar_visibilidad())
            self.etiquetas[nombre] = accion
        self.boton_etiquetas.setMenu(menu)
        self.accion_seccion_real = self._accion("seccion_real", "Sección real",
                                                "Sección real: barras con sus medidas b × h (o como líneas)",
                                                activable=True, activa=ui.SECCION_REAL_VISIBLE)
        self.accion_seccion_real.toggled.connect(self._cambio_seccion_real)
        # Transparencia del concreto: ícono (un clic: opaco ↔ transparente) y deslizador, como el del volumen
        self.boton_transparencia = QToolButton()
        self.boton_transparencia.setIcon(icono("transparencia"))
        self.boton_transparencia.setIconSize(tamano)
        self.boton_transparencia.setToolTip("Transparencia del concreto: deja ver el acero de columnas y vigas. "
                                            "Un clic alterna entre opaco y transparente")
        self.boton_transparencia.clicked.connect(self._alternar_transparencia)
        self.deslizador_transparencia = QSlider(Qt.Horizontal)
        self.deslizador_transparencia.setRange(0, round((1 - ui.OPACIDAD_MINIMA) * 100))
        self.deslizador_transparencia.setFixedWidth(ui.ANCHO_DESLIZADOR_PX)
        self.deslizador_transparencia.setToolTip("Transparencia del concreto: 0 % (opaco)")
        self.deslizador_transparencia.valueChanged.connect(self._cambio_transparencia)
        for control in (self.boton_transparencia, self.deslizador_transparencia):
            control.setEnabled(ui.SECCION_REAL_VISIBLE)
        self.accion_cargas = self._accion("cargas", "Cargas",
                                          "Cargas: muestra u oculta las cargas del caso activo (al editar)",
                                          activable=True, activa=ui.CARGAS_VISIBLES)
        self.accion_cargas.toggled.connect(lambda *_: self._aplicar_visibilidad())
        self.accion_reacciones = self._accion("reacciones", "Reacciones",
                                              "Reacciones: muestra las reacciones de los apoyos para el caso o la "
                                              "combinación que se ve (con resultados a la vista)",
                                              activable=True, activa=ui.REACCIONES_VISIBLES)
        self.accion_reacciones.toggled.connect(lambda *_: self._aplicar_visibilidad())
        self.accion_encuadre = self._accion("encuadre", "Encuadre", "Encuadre: ajusta la vista al modelo")
        self.accion_encuadre.triggered.connect(self.encuadre)

        barra.addAction(self.accion_rejilla)
        barra.addAction(self.accion_snap)
        barra.addWidget(self.boton_etiquetas)
        barra.addAction(self.accion_seccion_real)
        barra.addWidget(self.boton_transparencia)
        barra.addWidget(self.deslizador_transparencia)
        barra.addAction(self.accion_cargas)
        barra.addAction(self.accion_reacciones)
        barra.addSeparator()                       # a la izquierda, estados; a la derecha, una acción
        barra.addAction(self.accion_encuadre)

        estado = self.statusBar()
        estado.setSizeGripEnabled(False)
        self.coordenadas = QLabel()                # posición del puntero
        estado.addWidget(self.coordenadas, 1)
        estado.addPermanentWidget(barra)
        self.barra_inferior = barra

    def _mostrar(self, nombre, visible):
        """Muestra u oculta un actor de la vista ("rejilla", "etiquetas"...), sin redibujar."""
        actor = self.dibujado.actores.get(nombre)
        if actor is not None:
            actor.SetVisibility(visible)

    def _aplicar_visibilidad(self, dibujar=True):
        """Rejilla, etiquetas, cargas y reacciones, según sus botones. Los valores de las cargas y de
        las reacciones se ven solo si se ven sus flechas."""
        cargas, reacciones = self.accion_cargas.isChecked(), self.accion_reacciones.isChecked()
        visibles = {"rejilla": self.accion_rejilla.isChecked(), "cargas": cargas, "reacciones": reacciones}
        for nombre, accion in self.etiquetas.items():
            visibles[nombre] = accion.isChecked()
        visibles["valores_cargas"] = visibles["valores_cargas"] and cargas
        visibles["valores_reacciones"] = visibles["valores_reacciones"] and reacciones
        visibles["letras_ejes_locales"] = visibles["ejes_locales"]       # las letras x, y, z, con sus flechas
        for nombre, visible in visibles.items():
            self._mostrar(nombre, visible)
        if dibujar:
            self.vista.render()

    def _cambio_seccion_real(self, activa):
        """Sección real: las barras como cajas b × h o como líneas. La transparencia es de las cajas."""
        for control in (self.boton_transparencia, self.deslizador_transparencia):
            control.setEnabled(bool(activa))
        self.redibujar()

    def _cambio_transparencia(self, porcentaje):
        """Deslizador: opacidad de las cajas de concreto. Solo se redibuja al pasar de opaco a
        transparente o al revés (aparece o desaparece el acero); si no, basta cambiar la opacidad."""
        nueva = 1.0 - porcentaje / 100
        cruza = (nueva < 1) != (self.opacidad_concreto < 1)
        self.opacidad_concreto = nueva
        if porcentaje:
            self._transparencia_anterior = porcentaje
        self.deslizador_transparencia.setToolTip(f"Transparencia del concreto: {porcentaje} %"
                                                 + (" (opaco)" if not porcentaje else ""))
        actor = self.dibujado.actores.get("solidos")
        if cruza:
            self.redibujar()
        elif actor is not None:
            actor.GetProperty().SetOpacity(nueva)
            self.vista.render()

    def _alternar_transparencia(self):
        """Clic en el ícono: de opaco a la última transparencia usada, y de vuelta."""
        self.deslizador_transparencia.setValue(0 if self.deslizador_transparencia.value()
                                               else self._transparencia_anterior)

    def encuadre(self):
        """Ajusta la vista al modelo sin cambiar la dirección, con el mismo giro suave del cubo."""
        self.animador.animar(lambda: self.vista.reset_camera(render=False))

    # ---------- Dibujo ----------
    def _vigente(self, item):
        """El item si todavía existe en el modelo; si no, None."""
        if item is None:
            return None
        tipo, ident = item
        if tipo == "apoyo":
            nodo = self.modelo.nodos.get(ident)
            return item if nodo is not None and any(nodo.apoyo) else None
        coleccion = {"nodo": self.modelo.nodos, "barra": self.modelo.elementos, "carga": self.modelo.cargas}
        return item if ident in coleccion.get(tipo, {}) else None

    def _tamano(self):
        """Tamaño del modelo (m), para dibujar cargas y resultados en proporción."""
        if not self.modelo.nodos:
            return 1.0
        puntos = np.array([n.coords for n in self.modelo.nodos.values()], dtype=float)
        return float(np.ptp(puntos, axis=0).max()) or 1.0

    def redibujar(self, reiniciar_camara=False):
        """Vuelve a dibujar el modelo y la rejilla. No mueve la cámara, salvo que se pida.
        Editando se dibujan las cargas del caso elegido; con resultados, lo prendido arriba y las
        reacciones."""
        for actor in self.dibujado.actores.values():
            self.vista.remove_actor(actor, render=False)
        self.vista.set_background(colores.FONDO_VISTA)
        real = self.accion_seccion_real.isChecked()
        self.dibujado = dibujar_modelo(self.vista, self.modelo, real, self.opacidad_concreto if real else 1.0)
        self.rejilla = geometria_rejilla(self.modelo)
        self.dibujado.actores["rejilla"] = dibujar_rejilla(self.vista, self.rejilla,
                                                           cuenta_para_camara=not self.modelo.nodos)
        tamano = self._tamano()
        rc = self._rc()
        self.factor_deformada = None
        if not self.modo_resultados:
            self.dibujado.actores.update(dibujar_cargas(self.vista, self.modelo, self.caso_activo(), tamano,
                                                        seccion_real=real))
        elif rc is not None:
            if self.resultado_visible in DEFORMADAS:
                actores, self.factor_deformada = dibujar_deformada(self.vista, self.modelo, rc, tamano,
                                                                   self.resultado_visible)
                self.dibujado.actores.update(actores)
            elif self.resultado_visible:
                self.dibujado.actores.update(dibujar_diagrama(self.vista, self.modelo, rc, self.resultado_visible,
                                                              tamano))
            self.dibujado.actores.update(dibujar_reacciones(self.vista, self.modelo, rc, tamano))
        boton = self.botones_resultado["deformada"]
        boton.setToolTip("Deformada: total, Δx, Δy o Δz (ejes globales)"
                         + (f". Ahora, ×{_factor_texto(self.factor_deformada)} el tamaño real"
                            if self.factor_deformada is not None else ""))
        self.seleccion, self.resaltado = self._vigente(self.seleccion), self._vigente(self.resaltado)
        self._dibujar_ejes_locales()
        self._aplicar_visibilidad(dibujar=False)
        self.dibujado.pintar(self.resaltado, self._en_3d(self.seleccion), self._enlazados())
        self.previsualizacion.actualizar_estilo()
        if reiniciar_camara:
            self.vista.view_isometric()
            self.vista.reset_camera()
        self.vista.renderer.ResetCameraClippingRange()
        self.vista.render()

    def _dibujar_ejes_locales(self):
        """Los ejes locales x, y, z de la barra seleccionada (o de la barra de la carga elegida). Se
        rehacen al cambiar la selección y al redibujar; el menú Etiquetas los muestra u oculta.
        Sirven para leer los diagramas (N, V, M y T están en esos ejes) y las cargas en x, y, z."""
        for nombre in ("ejes_locales", "letras_ejes_locales"):
            actor = self.dibujado.actores.pop(nombre, None)
            if actor is not None:
                self.vista.remove_actor(actor, render=False)
        elegido = self._en_3d(self.seleccion)
        if elegido is None or elegido[0] != "barra":
            return
        actores = dibujar_ejes_locales(self.vista, self.modelo, elegido[1], self._tamano(),
                                       self.accion_seccion_real.isChecked())
        visible = self.etiquetas["ejes_locales"].isChecked()
        for actor in actores.values():
            actor.SetVisibility(visible)
        self.dibujado.actores.update(actores)

    def _relacionados(self, seleccion):
        """Lo relacionado con la selección: (mismos, enlazados).

        - nodo: mismos = sus cargas del caso activo; enlazados = su apoyo y sus barras;
        - apoyo: enlazado = su nodo;
        - barra: mismos = sus cargas; enlazados = sus nodos y los apoyos de esos nodos;
        - carga: enlazado = su nodo o su barra.
        En 3D lo enlazado va en el gris intermedio y lo seleccionado en gris oscuro. Viendo una
        combinación no hay cargas a la vista."""
        if seleccion is None:
            return [], []
        tipo, ident = seleccion
        caso = self.caso_activo()

        def cargas(clase, i):
            return [] if self.modo_combinaciones else [("carga", c) for c in self.modelo.cargas_en(clase, i, caso)]

        def apoyos(nodos):
            return [("apoyo", n) for n in nodos if any(self.modelo.nodos[n].apoyo)]

        if tipo == "nodo":
            return (cargas("nodo", ident),
                    apoyos([ident]) + [("barra", e) for e in self.modelo.elementos_conectados(ident)])
        if tipo == "apoyo":
            return [], [("nodo", ident)]
        if tipo == "barra":
            el = self.modelo.elementos[ident]
            return cargas("barra", ident), [("nodo", el.ni), ("nodo", el.nj)] + apoyos([el.ni, el.nj])
        c = self.modelo.cargas[ident]
        return [], [("nodo", c.nodo) if hasattr(c, "nodo") else ("barra", c.barra)]

    def _en_3d(self, seleccion):
        """Qué se pinta como seleccionado en 3D: una carga elegida se ve en su nodo o su barra."""
        if seleccion is not None and seleccion[0] == "carga":
            return self._relacionados(seleccion)[1][0]
        return seleccion

    def _enlazados(self):
        """Lo que se pinta como relacionado en 3D junto con la selección (sin las cargas)."""
        if self.seleccion is None or self.seleccion[0] == "carga":
            return []
        return [r for r in self._relacionados(self.seleccion)[1] if r[0] != "carga"]

    def pintar(self):
        """Colores vigentes: gris; un gris intermedio lo relacionado y lo que está bajo el mouse;
        gris oscuro lo seleccionado."""
        self.dibujado.pintar(self.resaltado, self._en_3d(self.seleccion), self._enlazados())
        self.vista.render()

    # ---------- Cambios, Deshacer y Eliminar ----------
    def antes_de_cambiar(self):
        """Lo llama todo lo que va a cambiar el modelo: guarda una copia para Deshacer."""
        self.historial.guardar(self.modelo, not self.modificado)
        self._actualizar_deshacer()

    def _actualizar_deshacer(self):
        self.accion_deshacer.setEnabled(self.historial.puede_deshacer())
        self.accion_rehacer.setEnabled(self.historial.puede_rehacer())

    def _volver(self, modelo, guardado, texto):
        """Pone una copia del historial como modelo actual."""
        self.modelo, self.modificado = modelo, not guardado
        self._invalidar_resultados()
        self.herramienta.cancelar()
        self._actualizar_titulo()
        self._llenar_casos()
        self._llenar_combinaciones()
        self._actualizar_modo()
        self.redibujar()
        self.seleccionar(self.seleccion)
        self._refrescar_paneles()
        self._actualizar_deshacer()
        self.mensaje(texto)
        self._actualizar_puntero()

    def deshacer(self):
        if self.historial.puede_deshacer():
            self._volver(*self.historial.deshacer(self.modelo, not self.modificado), "Deshecho")

    def rehacer(self):
        if self.historial.puede_rehacer():
            self._volver(*self.historial.rehacer(self.modelo, not self.modificado), "Rehecho")

    def eliminar(self):
        """Supr: borra lo seleccionado y lo que depende de ello:
        - un apoyo: solo el apoyo (el nodo queda libre, con sus barras);
        - un nodo: el nodo con su apoyo, sus cargas y sus barras (una barra no existe sin sus nodos);
        - una barra: la barra con sus cargas (los nodos quedan);
        - una carga: la carga."""
        if self.modo_resultados:
            self.mensaje("Con resultados a la vista no se edita: vuelve a editar con ▶")
            return
        if self.seleccion is None:
            self.mensaje("Selecciona un nodo, un apoyo, una barra o una carga para eliminar")
            return
        tipo, ident = self.seleccion
        self.antes_de_cambiar()
        if tipo == "carga":
            self.modelo.eliminar_carga(ident)
            texto = f"Carga {ident} eliminada"
        elif tipo == "apoyo":
            self.modelo.restringir(ident, *TIPOS["libre"])
            texto = f"Apoyo del nodo {ident} eliminado"
        elif tipo == "nodo":
            apoyo = any(self.modelo.nodos[ident].apoyo)
            conectadas = self.modelo.elementos_conectados(ident)
            n_cargas = len(self.modelo.cargas_en("nodo", ident)) + sum(
                len(self.modelo.cargas_en("barra", e)) for e in conectadas)
            barras = self.modelo.eliminar_nodo(ident)
            partes = (["su apoyo"] if apoyo else []) + ([_plural(len(barras), "barra")] if barras else []) + \
                     ([_plural(n_cargas, "carga")] if n_cargas else [])
            texto = f"Nodo {ident} eliminado"
            if partes:
                texto += " (con " + (", ".join(partes[:-1]) + " y " + partes[-1] if len(partes) > 1 else partes[0]) + ")"
        else:
            self.modelo.eliminar_elemento(ident)
            texto = f"Elemento {ident} eliminado (sus nodos quedan)"
        self.seleccion = None
        self.modelo_cambiado(texto)

    def _asignar_seccion(self, eid, sid):
        el = self.modelo.elementos.get(eid)
        if el is None or el.seccion == sid:
            return
        self.antes_de_cambiar()
        self.modelo.asignar_seccion(eid, sid)
        nombre = textos.nombre(self.modelo.secciones[sid], self.modelo) if sid is not None else "sin sección"
        self.modelo_cambiado(f"Elemento {eid}: {nombre}")

    def _editar_seccion(self, eid, valores):
        """Medidas nuevas para la sección de una barra: se usa (o crea) otra sección solo para ella."""
        if eid not in self.modelo.elementos:
            return
        material, b, h, d, barra, nx, ny = valores
        mat = self.modelo.materiales.get(material)
        error = None
        if mat is None or mat.fc is None:
            error = "La sección necesita un material de concreto (Definir → Materiales)"
        elif not 0 < d < min(b, h) / 2:
            error = "d debe ser menor que la mitad de b y de h"
        else:
            from modelo import interaccion as puente
            from modelo.estructura import Concreto
            try:
                puente.propiedades(Concreto("rectangular", mat.fc, d, barra, b, h, nx, ny))
            except ValueError as e:
                error = str(e)
        if error:
            self.mensaje(error)
            self._mostrar_propiedades(self._en_propiedades)      # vuelven los valores anteriores
            return
        self.antes_de_cambiar()
        sid, nueva = cc.buscar_o_crear_seccion(self.modelo, material, b, h, d, barra, nx, ny)
        self.modelo.asignar_seccion(eid, sid)
        texto = f"Elemento {eid}: {textos.nombre(self.modelo.secciones[sid], self.modelo)}"
        self.modelo_cambiado(texto + (" (sección nueva)" if nueva else ""))

    def modelo_cambiado(self, texto, invalida=True):
        """Lo llaman las herramientas y los paneles después de cambiar el modelo.

        invalida=False: el cambio no toca los resultados de los casos (editar combinaciones, que se
        calculan sumando esos resultados); solo se rehacen las combinaciones."""
        self.modificado = True
        if invalida:
            self._invalidar_resultados()
        else:
            self._combinados = {}
        self._actualizar_deshacer()
        self._actualizar_titulo()
        self._llenar_casos()
        self._llenar_combinaciones()
        self._actualizar_modo()
        self.redibujar()
        self._refrescar_paneles()
        self.mensaje(texto)
        self.actualizar_indicacion()
        self._actualizar_puntero()

    def _refrescar_paneles(self):
        """Los botones del estado vigente, el Explorador, Propiedades, Diagrama y las ventanas
        abiertas, con el modelo y las unidades vigentes."""
        self._llenar_casos()
        self._llenar_combinaciones()
        self._actualizar_modo()
        self.explorador.actualizar(self.modelo, None if self.modo_combinaciones else self.caso_activo())
        self.explorador.marcar(self.seleccion, *self._relacionados(self.seleccion))
        self._mostrar_propiedades(self._en_propiedades)
        self.modelo_actualizado.emit()
        if self.ventana_matriz.isVisible():
            self.ventana_matriz.refrescar(self.modelo)
        for ventana in self.diagramas:
            ventana.refrescar()

    # ---------- Mouse ----------
    def _actualizar_puntero(self):
        """Recalcula dónde caería un clic: coordenadas en la barra de estado y previsualización gris."""
        if self._mouse is None or self.cubo.contiene(*self._mouse):
            cand = Candidato()
        else:
            cand = candidato(self.vista.renderer, *self._mouse, self.modelo, self.rejilla,
                             self.accion_snap.isChecked())
        self.candidato = cand
        self.coordenadas.setText(texto_coordenadas(cand, self.herramienta.inicio()))
        habia = self.previsualizacion.visible
        if self.herramienta.usa_previsualizacion:
            self.herramienta.previsualizar(cand)
        else:
            self.previsualizacion.ocultar()
        if habia or self.previsualizacion.visible:
            self.vista.render()

    def _actualizar_resaltado(self):
        """Con Seleccionar, el nodo, el apoyo o la barra bajo el mouse se ve en el gris intermedio."""
        nuevo = None
        if (self._mouse is not None and isinstance(self.herramienta, Seleccionar)
                and not self.cubo.contiene(*self._mouse)):
            nuevo = elemento_en(self.vista.renderer, self.modelo, *self._mouse, ui.TOL_SELECCION_PX,
                                self.dibujado.cajas_apoyo, self.dibujado.cajas_nudo)
        if nuevo != self.resaltado:
            self.resaltado = nuevo
            self.pintar()

    def _al_presionar(self, *_):
        self.animador.detener()                    # si la cámara estaba girando, manda el usuario
        self._pos_presion = self.vista.iren.get_event_position()

    def _al_mover(self, *_):
        if self._pos_presion is not None:          # arrastrando para rotar: no se recalcula nada
            return
        self._mouse = self.vista.iren.get_event_position()
        self.cubo.resaltar(*self._mouse)
        self._actualizar_resaltado()
        self._actualizar_puntero()

    def _al_salir(self, *_):
        self._mouse = None
        self.cubo.quitar_resaltado()
        self._actualizar_resaltado()
        self._actualizar_puntero()

    def _al_soltar(self, *_):
        if self._pos_presion is None:
            return
        x, y = self.vista.iren.get_event_position()
        x0, y0 = self._pos_presion
        self._pos_presion = None
        if abs(x - x0) > ui.TOL_CLIC_PX or abs(y - y0) > ui.TOL_CLIC_PX:
            return                                 # fue un arrastre para rotar, no un clic
        self._clic(x, y)

    def _clic(self, x, y):
        if self.cubo.clic(x, y):                   # clic sobre el cubo: gira hasta esa vista
            return
        self._mouse = (x, y)
        self._actualizar_puntero()
        self.herramienta.clic(x, y, self.candidato)
        self.actualizar_indicacion()
        self._actualizar_puntero()

    # ---------- Selección ----------
    def seleccionar(self, seleccion):
        """Selecciona un ("nodo", id), ("apoyo", id), ("barra", id) o ("carga", id): gris oscuro en
        3D (con lo relacionado en un gris más tenue), marcado en el explorador con todo lo
        relacionado y sus datos en Propiedades. None quita la selección."""
        self.seleccion = self._vigente(seleccion)
        self._dibujar_ejes_locales()
        self.pintar()
        self.explorador.marcar(self.seleccion, *self._relacionados(self.seleccion))
        self._mostrar_propiedades(self.seleccion)

    # ---------- Archivo ----------
    def _actualizar_titulo(self):
        nombre = self.ruta.name if self.ruta else "Sin título"
        self.setWindowTitle(f"{ui.TITULO_VENTANA} — {nombre}{'*' if self.modificado else ''}")

    def _carpeta(self):
        return str(self.ruta.parent) if self.ruta else str(Path.home())

    def _confirmar_descartar(self):
        """True si se puede seguir: no hay cambios, se guardaron o el usuario los descarta."""
        if not self.modificado:
            return True
        respuesta = QMessageBox.question(
            self, "Cambios sin guardar", "El modelo tiene cambios sin guardar. ¿Quieres guardarlos?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if respuesta == QMessageBox.Save:
            return self.guardar()
        return respuesta == QMessageBox.Discard

    def nuevo(self):
        if self._confirmar_descartar():
            self._cargar(Modelo(), None, {})

    def abrir(self, ruta=None):
        if not self._confirmar_descartar():
            return False
        if ruta is None:
            ruta, _ = QFileDialog.getOpenFileName(self, "Abrir modelo", self._carpeta(), "Modelos (*.json)")
            if not ruta:
                return False
        try:
            modelo, vista = archivo.abrir(ruta)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Abrir", f"No se pudo abrir {Path(ruta).name}:\n\n{e}")
            return False
        self._cargar(modelo, Path(ruta), vista)
        return True

    def guardar(self):
        return self._escribir(self.ruta) if self.ruta else self.guardar_como()

    def guardar_como(self, ruta=None):
        if ruta is None:
            sugerido = str(self.ruta) if self.ruta else str(Path(self._carpeta()) / "modelo.json")
            ruta, _ = QFileDialog.getSaveFileName(self, "Guardar modelo como", sugerido, "Modelos (*.json)")
            if not ruta:
                return False
        ruta = Path(ruta)
        if ruta.suffix.lower() != ".json":
            ruta = ruta.with_name(ruta.name + ".json")
        return self._escribir(ruta)

    def _escribir(self, ruta):
        try:
            archivo.guardar(self.modelo, ruta)
        except OSError as e:
            QMessageBox.warning(self, "Guardar", f"No se pudo guardar {Path(ruta).name}:\n\n{e}")
            return False
        self.ruta = Path(ruta)
        self.modificado = False
        self.historial.marcar_sin_guardar()       # solo el estado actual coincide con el archivo
        self._actualizar_titulo()
        self.mensaje(f"Guardado en {self.ruta.name}")
        return True

    def _cargar(self, modelo, ruta, vista):
        """Pone otro modelo en la ventana (Nuevo o Abrir)."""
        self.modelo, self.ruta, self.modificado = modelo, ruta, False
        self.ver_combinaciones = False
        self._ultimo_resultado = "deformada"
        self._invalidar_resultados()
        self._llenar_casos()
        self._llenar_combinaciones()
        self.historial.vaciar()
        self._actualizar_deshacer()
        for _, herramienta in self._herramientas:
            herramienta.reiniciar()
        self.seleccion = self.resaltado = self._en_propiedades = None
        self.ventana_matriz.close()
        for ventana in list(self.diagramas):
            ventana.close()
        self._actualizar_modo()
        self.redibujar(reiniciar_camara=True)
        self._refrescar_paneles()
        self._actualizar_titulo()
        self.actualizar_indicacion()
        self._actualizar_puntero()

    # ---------- Configuración ----------
    def abrir_configuracion(self):
        """El diálogo aplica cada cambio en el momento; aquí solo se abre."""
        DialogoConfiguracion(self).exec()

    def aplicar_configuracion(self):
        """Toma los valores vigentes de configuracion/ (lo llama el diálogo en cada cambio)."""
        aplicar_tema(QApplication.instance())
        for barra in (self.herramientas, self.barra_definir):
            barra.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        for boton in self.botones_resultado.values():
            boton.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        inferior = QSize(ui.TAMANO_ICONO_INFERIOR, ui.TAMANO_ICONO_INFERIOR)
        self.barra_inferior.setIconSize(inferior)
        for boton in (self.boton_etiquetas, self.boton_transparencia):
            boton.setIconSize(inferior)
        self.cubo.actualizar_colores()
        self._ajustar_esquinas()
        self.propiedades.actualizar_unidades()     # campos a medias (cargas, formularios) en las nuevas
        self.redibujar()
        self._refrescar_paneles()
        self.actualizar_indicacion()
        self._actualizar_puntero()
        for barra in (self.herramientas, self.barra_definir, self.barra_inferior):
            barra.update()                         # los íconos se vuelven a pintar con su color

    # ---------- Ventana ----------
    def _ajustar_esquinas(self):
        """Cubo arriba a la derecha y ejes abajo a la izquierda: cuadrados y con el mismo margen."""
        ancho, alto = self.vista.ren_win.GetSize()
        if ancho <= 0 or alto <= 0:
            return
        self.cubo.ajustar_tamano()
        ejes = self.vista.renderer.axes_widget
        if ejes is not None:
            ejes.SetViewport(*viewport_esquina(ancho, alto, ui.EJES_TAMANO, "abajo_izquierda"))

    def showEvent(self, evento):
        super().showEvent(evento)
        QTimer.singleShot(0, self._ajustar_y_dibujar)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if hasattr(self, "cubo"):
            QTimer.singleShot(0, self._ajustar_y_dibujar)   # después de que la vista tome su tamaño

    def _ajustar_y_dibujar(self):
        if not self._cerrando:
            self._ajustar_esquinas()
            self.vista.render()

    def closeEvent(self, evento):
        if not self._confirmar_descartar():
            evento.ignore()
            return
        self._cerrando = True
        self.animador.detener()                    # que el giro no siga con la ventana cerrándose
        for ventana in list(self.diagramas):
            ventana.close()
        self.ventana_matriz.close()
        self.cubo.apagar()                         # apaga el cubo antes de cerrar la vista 3D
        self.vista.close()                         # libera la ventana 3D al cerrar
        super().closeEvent(evento)
