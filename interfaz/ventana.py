"""Ventana principal.

Organización (como ETABS y Civil 3D):
- Arriba: menús con palabras (Archivo, Editar, Ver, Definir, Configuración) y una barra con íconos:
  Deshacer y Rehacer, y luego Material y Sección (Definir).
- Izquierda: las herramientas que cambian lo que hace el clic (Seleccionar, Nodo, Elemento, Apoyo) y el
  Explorador del modelo (pestañas Modelo y Tablas).
- Derecha: Propiedades de lo seleccionado.
- Abajo: la barra de comandos (activa solo con Nodo o Elemento) y la barra de estado, con la
  posición del puntero a la izquierda y Rejilla, Snap, Etiquetas y Encuadre a la derecha.
Los paneles se pueden agrandar, mover de lado, cerrar y volver a abrir desde el menú Ver (no se
desacoplan como ventanas sueltas).
La lógica de cada herramienta está en herramientas.py; la del plano y el snap, en plano_trabajo.py.
"""
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (QApplication, QDockWidget, QFileDialog, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QSizePolicy, QToolBar)
from pyvistaqt import QtInteractor

from configuracion import colores
from configuracion import interfaz as ui
from interfaz.camara import AnimadorCamara
from interfaz.cubo_vistas import CuboVistas, viewport_esquina
from interfaz.definir import DialogoMateriales, DialogoSecciones
from interfaz.diagramas import VentanaDiagrama
from interfaz.dialogo_configuracion import DialogoConfiguracion
from interfaz.dibujo import ModeloDibujado, Previsualizacion, dibujar_modelo, dibujar_rejilla
from interfaz.explorador import Explorador
from interfaz.historial import Historial
from interfaz.herramientas import AgregarApoyo, AgregarElemento, AgregarNodo, Seleccionar
from interfaz.iconos import icono
from interfaz.plano_trabajo import (PLANOS, Candidato, candidato, geometria_rejilla, interpretar,
                                    plano_por_defecto, texto_coordenadas)
from interfaz.propiedades import Propiedades
from interfaz.seleccion import elemento_en
from interfaz.tablas import VentanaMatriz
from interfaz.tema import aplicar_tema
from modelo import Modelo, archivo
from modelo import concreto as cc

TECLAS_A_COMANDOS = set("0123456789.-@")   # escritas sobre la vista, van a la barra de comandos


class Ventana(QMainWindow):
    def __init__(self, modelo=None, ruta=None):
        super().__init__()
        self.resize(*ui.TAMANO_VENTANA)

        self.modelo = modelo if modelo is not None else Modelo()
        self.ruta = Path(ruta) if ruta else None   # archivo del modelo (None = todavía sin guardar)
        self.modificado = False
        self.seleccion = None                      # ("nodo", id), ("barra", id) o None
        self.resaltado = None                      # lo que está bajo el mouse con Seleccionar
        self._en_propiedades = None                # lo que muestra el panel Propiedades
        self.dibujado = ModeloDibujado()
        self.plano, self.posicion_plano = plano_por_defecto(self.modelo)
        self.rejilla = None
        self.candidato = Candidato()               # dónde caería un clic ahora
        self._pos_presion = None                   # dónde se presionó el botón izquierdo
        self._mouse = None                         # última posición del mouse sobre la vista
        self._cerrando = False
        self.diagramas = []                        # ventanas de diagramas abiertas
        self.historial = Historial()               # Deshacer (Ctrl+Z) y Rehacer (Ctrl+Y)

        # Tres luces blancas: los grises se ven grises (las de pyvista por defecto los tiñen)
        self.vista = QtInteractor(self, lighting="three lights")
        self.setCentralWidget(self.vista)
        self.vista.add_axes(x_color=colores.EJE_X)  # ejes X (rojo), Y, Z abajo a la izquierda
        self.animador = AnimadorCamara(self.vista)  # giro suave de la cámara (cubo y Encuadre)
        self.previsualizacion = Previsualizacion(self.vista)
        self.ventana_matriz = VentanaMatriz(self)

        self._crear_paneles()
        self._crear_menus()
        self._crear_barra_definir()
        self._crear_herramientas()
        self._crear_barra_comandos()
        self._crear_barra_inferior()

        self.redibujar(reiniciar_camara=True)
        self.cubo = CuboVistas(self.vista, self.animador)   # cubo de vistas, arriba a la derecha
        self.explorador.actualizar(self.modelo)
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

    # ---------- Paneles (izquierda y derecha) ----------
    def _crear_paneles(self):
        self.explorador = Explorador(self)
        self.propiedades = Propiedades(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.explorador)
        self.addDockWidget(Qt.RightDockWidgetArea, self.propiedades)
        for panel in (self.explorador, self.propiedades):   # sin el botón de desacoplar
            panel.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self.resizeDocks([self.explorador, self.propiedades], [260, 300], Qt.Horizontal)
        self.explorador.elegido.connect(self._elegido_en_explorador)
        self.propiedades.ver_diagrama.connect(self.ver_diagrama)
        self.propiedades.asignar_seccion.connect(self._asignar_seccion)
        self.propiedades.editar_seccion.connect(self._editar_seccion)

    def _mostrar_propiedades(self, item):
        """Propiedades muestra lo seleccionado, salvo que la herramienta use el panel (Apoyo)."""
        self._en_propiedades = item
        if not self.herramienta.mostrar_panel():
            self.propiedades.mostrar(self.modelo, item)

    def _tipo_apoyo(self, tipo):
        self.herramienta_apoyo.tipo = tipo

    def _elegido_en_explorador(self, item):
        tipo, ident = item
        if tipo in ("nodo", "barra"):
            self.seleccionar(item)
        elif tipo == "matriz":
            self.seleccionar(("barra", ident))
            self.ventana_matriz.mostrar(self.modelo, ident)
        elif tipo == "seccion":
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

    # ---------- Menús y barra Definir (arriba) ----------
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
        editar.addSeparator()
        editar.addAction(self.accion_eliminar)

        ver = self.menuBar().addMenu("Ver")                 # cerrar y volver a abrir los paneles
        ver.addAction(self.explorador.toggleViewAction())
        ver.addAction(self.propiedades.toggleViewAction())

        definir = self.menuBar().addMenu("Definir")         # etapas 1 y 3 de la hoja de ruta
        definir.setToolTipsVisible(True)
        self.accion_material = self._accion("material", "Materiales…", "Materiales de concreto")
        self.accion_seccion = self._accion("seccion", "Secciones…", "Secciones de concreto")
        self.accion_material.triggered.connect(lambda *_: DialogoMateriales(self).exec())
        self.accion_seccion.triggered.connect(lambda *_: DialogoSecciones(self).exec())
        self.accion_combinaciones = QAction("Combinaciones de carga…", self)
        self.accion_combinaciones.setToolTip("Próximamente")
        self.accion_combinaciones.setEnabled(False)
        for accion in (self.accion_material, self.accion_seccion, self.accion_combinaciones):
            definir.addAction(accion)

        self.accion_configuracion = self.menuBar().addAction("Configuración")
        self.accion_configuracion.triggered.connect(self.abrir_configuracion)

    def _crear_barra_definir(self):
        self.barra_definir = QToolBar("Definir", self)
        self.barra_definir.setObjectName("definir")
        self.barra_definir.setMovable(False)
        self.barra_definir.setFloatable(False)
        self.barra_definir.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        self.barra_definir.addAction(self.accion_deshacer)
        self.barra_definir.addAction(self.accion_rehacer)
        self.barra_definir.addSeparator()
        self.barra_definir.addAction(self.accion_material)
        self.barra_definir.addAction(self.accion_seccion)
        self.addToolBar(Qt.TopToolBarArea, self.barra_definir)

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
        for nombre, texto, ayuda, clase in (
                ("seleccionar", "Seleccionar", "Seleccionar: clic sobre un nodo o una barra", Seleccionar),
                ("nodo", "Nodo", "Agregar nodo: clic sobre la rejilla o escribe x, y, z", AgregarNodo),
                ("elemento", "Elemento", "Agregar elemento: clic en el punto inicial y en el final",
                 AgregarElemento),
                ("apoyo", "Apoyo", "Apoyo: elige el tipo en Propiedades y haz clic sobre un nodo",
                 AgregarApoyo)):
            accion = self._accion(nombre, texto, ayuda, activable=True)
            herramienta = clase(self)
            accion.triggered.connect(lambda *_, h=herramienta: self.usar_herramienta(h))
            grupo.addAction(accion)
            self.herramientas.addAction(accion)
            self._herramientas.append((accion, herramienta))
        ((self.accion_seleccionar, self.herramienta), (self.accion_nodo, _), (self.accion_elemento, _),
         (self.accion_apoyo, self.herramienta_apoyo)) = self._herramientas
        self.propiedades.panel_apoyo.cambiado.connect(self._tipo_apoyo)
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
        self.resaltado = None                      # el resaltado gris oscuro es solo de Seleccionar
        self.pintar()
        self._mostrar_propiedades(self.seleccion)  # el panel de Apoyo, o de nuevo lo seleccionado
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
        seleccionar = self._herramientas[0][1]
        if self.herramienta.cancelar():
            self.mensaje("Cancelado")
        elif self.herramienta is not seleccionar:
            self.usar_herramienta(seleccionar)
        elif self.seleccion is not None:
            self.seleccionar(None)
        self.actualizar_indicacion()
        self._actualizar_puntero()

    def eventFilter(self, objeto, evento):
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
        barra.setIconSize(QSize(ui.TAMANO_ICONO_INFERIOR, ui.TAMANO_ICONO_INFERIOR))

        self.accion_rejilla = self._accion("rejilla", "Rejilla", f"Rejilla ({ui.ATAJO_REJILLA})",
                                           activable=True, activa=ui.REJILLA_VISIBLE, atajo=ui.ATAJO_REJILLA)
        self.accion_rejilla.toggled.connect(lambda activa: self._mostrar("rejilla", activa))
        self.accion_snap = self._accion("snap", "Snap",
                                        f"Snap ({ui.ATAJO_SNAP}): pega el punto a nodos y a la rejilla",
                                        activable=True, activa=ui.SNAP_ACTIVO, atajo=ui.ATAJO_SNAP)
        self.accion_snap.toggled.connect(lambda *_: self._actualizar_puntero())
        self.accion_etiquetas = self._accion("etiqueta", "Etiquetas", "Etiquetas: números de nodo",
                                             activable=True, activa=ui.ETIQUETAS_VISIBLES)
        self.accion_etiquetas.toggled.connect(lambda activa: self._mostrar("etiquetas", activa))
        self.accion_seccion_real = self._accion("seccion_real", "Sección real",
                                                "Sección real: barras con sus medidas b × h (o como líneas)",
                                                activable=True, activa=ui.SECCION_REAL_VISIBLE)
        self.accion_seccion_real.toggled.connect(lambda *_: self.redibujar())
        self.accion_encuadre = self._accion("encuadre", "Encuadre", "Encuadre: ajusta la vista al modelo")
        self.accion_encuadre.triggered.connect(self.encuadre)

        for accion in (self.accion_rejilla, self.accion_snap, self.accion_etiquetas, self.accion_seccion_real):
            barra.addAction(accion)
        barra.addSeparator()                       # a la izquierda, estados; a la derecha, una acción
        barra.addAction(self.accion_encuadre)

        estado = self.statusBar()
        estado.setSizeGripEnabled(False)
        self.coordenadas = QLabel()                # posición del puntero
        estado.addWidget(self.coordenadas, 1)
        estado.addPermanentWidget(barra)
        self.barra_inferior = barra

    def _mostrar(self, nombre, visible, dibujar=True):
        """Muestra u oculta un actor de la vista ("rejilla", "etiquetas"...)."""
        actor = self.dibujado.actores.get(nombre)
        if actor is not None:
            actor.SetVisibility(visible)
            if dibujar:
                self.vista.render()

    def encuadre(self):
        """Ajusta la vista al modelo sin cambiar la dirección, con el mismo giro suave del cubo."""
        self.animador.animar(lambda: self.vista.reset_camera(render=False))

    # ---------- Dibujo ----------
    def _vigente(self, item):
        """El item si todavía existe en el modelo; si no, None."""
        if item is None:
            return None
        tipo, ident = item
        return item if ident in (self.modelo.nodos if tipo == "nodo" else self.modelo.elementos) else None

    def redibujar(self, reiniciar_camara=False):
        """Vuelve a dibujar el modelo y la rejilla. No mueve la cámara, salvo que se pida."""
        for actor in self.dibujado.actores.values():
            self.vista.remove_actor(actor, render=False)
        self.vista.set_background(colores.FONDO_VISTA)
        self.dibujado = dibujar_modelo(self.vista, self.modelo, self.accion_seccion_real.isChecked())
        self.rejilla = geometria_rejilla(self.modelo, self.plano, self.posicion_plano)
        self.dibujado.actores["rejilla"] = dibujar_rejilla(self.vista, self.rejilla,
                                                           cuenta_para_camara=not self.modelo.nodos)
        self._mostrar("rejilla", self.accion_rejilla.isChecked(), dibujar=False)
        self._mostrar("etiquetas", self.accion_etiquetas.isChecked(), dibujar=False)
        self.seleccion, self.resaltado = self._vigente(self.seleccion), self._vigente(self.resaltado)
        self.dibujado.pintar(self.resaltado, self.seleccion)
        self.previsualizacion.actualizar_estilo()
        if reiniciar_camara:
            self.vista.view_isometric()
            self.vista.reset_camera()
        self.vista.renderer.ResetCameraClippingRange()
        self.vista.render()

    def pintar(self):
        """Colores vigentes: gris, gris oscuro bajo el mouse y negro lo seleccionado."""
        self.dibujado.pintar(self.resaltado, self.seleccion)
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
        self.herramienta.cancelar()
        self._actualizar_titulo()
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
        """Supr: borra el nodo (con sus barras) o la barra seleccionada."""
        if self.seleccion is None:
            self.mensaje("Selecciona un nodo o una barra para eliminar")
            return
        tipo, ident = self.seleccion
        self.antes_de_cambiar()
        if tipo == "nodo":
            barras = self.modelo.eliminar_nodo(ident)
            texto = f"Nodo {ident} eliminado" + (f" (y {len(barras)} barra{'s' if len(barras) != 1 else ''})"
                                                 if barras else "")
        else:
            self.modelo.eliminar_elemento(ident)
            texto = f"Elemento {ident} eliminado"
        self.seleccion = None
        self.modelo_cambiado(texto)

    def _asignar_seccion(self, eid, sid):
        el = self.modelo.elementos.get(eid)
        if el is None or el.seccion == sid:
            return
        self.antes_de_cambiar()
        self.modelo.asignar_seccion(eid, sid)
        nombre = self.modelo.secciones[sid].nombre if sid is not None else "sin sección"
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
            from interfaz import concreto as puente
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
        texto = f"Elemento {eid}: {self.modelo.secciones[sid].nombre}"
        self.modelo_cambiado(texto + (" (sección nueva)" if nueva else ""))

    def modelo_cambiado(self, texto):
        """Lo llaman las herramientas y los paneles después de cambiar el modelo."""
        self.modificado = True
        self._actualizar_deshacer()
        self._actualizar_titulo()
        self.redibujar()
        self._refrescar_paneles()
        self.mensaje(texto)
        self.actualizar_indicacion()
        self._actualizar_puntero()

    def _refrescar_paneles(self):
        """Explorador, Propiedades y ventanas abiertas, con el modelo y las unidades vigentes."""
        self.explorador.actualizar(self.modelo)
        self.explorador.marcar(self.seleccion)
        self._mostrar_propiedades(self._en_propiedades)
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
        """Con Seleccionar, el nodo o la barra bajo el mouse se ve en gris oscuro."""
        nuevo = None
        if (self._mouse is not None and isinstance(self.herramienta, Seleccionar)
                and not self.cubo.contiene(*self._mouse)):
            nuevo = elemento_en(self.vista.renderer, self.modelo, *self._mouse, ui.TOL_SELECCION_PX)
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
        """Selecciona un ("nodo", id) o ("barra", id): negro en 3D, marcado en el explorador y sus
        datos en Propiedades. None quita la selección."""
        self.seleccion = self._vigente(seleccion)
        self.pintar()
        self.explorador.marcar(self.seleccion)
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
            archivo.guardar(self.modelo, ruta, vista={"plano": self.plano, "posicion": self.posicion_plano})
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
        self.historial.vaciar()
        self._actualizar_deshacer()
        plano, posicion = vista.get("plano"), vista.get("posicion")
        if plano in PLANOS and isinstance(posicion, (int, float)) and not isinstance(posicion, bool):
            self.plano, self.posicion_plano = plano, float(posicion)
        else:
            self.plano, self.posicion_plano = plano_por_defecto(modelo)
        for _, herramienta in self._herramientas:
            herramienta.reiniciar()
        self.seleccion = self.resaltado = self._en_propiedades = None
        self.ventana_matriz.close()
        for ventana in list(self.diagramas):
            ventana.close()
        self.redibujar(reiniciar_camara=True)
        self._refrescar_paneles()
        self._actualizar_titulo()
        self.actualizar_indicacion()
        self._actualizar_puntero()

    # ---------- Configuración ----------
    def abrir_configuracion(self):
        """El diálogo aplica cada cambio en el momento; aquí solo se abre."""
        DialogoConfiguracion(self).exec()

    def cambiar_plano(self, plano, posicion):
        """Plano de trabajo (de este modelo: se guarda con su archivo)."""
        if (plano, posicion) == (self.plano, self.posicion_plano):
            return
        self.plano, self.posicion_plano = plano, posicion
        self.modificado = True
        self._actualizar_titulo()
        self.redibujar()
        self._actualizar_puntero()

    def aplicar_configuracion(self):
        """Toma los valores vigentes de configuracion/ (lo llama el diálogo en cada cambio)."""
        aplicar_tema(QApplication.instance())
        for barra in (self.herramientas, self.barra_definir):
            barra.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        self.barra_inferior.setIconSize(QSize(ui.TAMANO_ICONO_INFERIOR, ui.TAMANO_ICONO_INFERIOR))
        self.cubo.actualizar_colores()
        self._ajustar_esquinas()
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
