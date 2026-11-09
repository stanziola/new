"""Ventana principal.

Organización:
- Arriba, menús con palabras (son categorías): Archivo, Definir y Configuración.
- Izquierda, las herramientas que cambian lo que hace el clic (una activa a la vez): Seleccionar,
  Nodo y Elemento. Solo íconos con tooltip.
- Abajo:
  - barra de comandos: qué se espera, un campo para escribir coordenadas exactas y los avisos;
  - barra de estado: a la izquierda, la posición del puntero; a la derecha, cómo se ve el modelo
    (Rejilla, Snap, Etiquetas) y Encuadre.
La lógica de cada herramienta está en herramientas.py; la del plano y el snap, en plano_trabajo.py.
"""
from pathlib import Path

import numpy as np
import pyvista as pv
from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QLabel, QLineEdit, QMainWindow,
                               QMessageBox, QSizePolicy, QToolBar)
from pyvistaqt import QtInteractor

from calculo import archivo
from calculo.modelo import Modelo
from configuracion import colores
from configuracion import interfaz as ui
from interfaz.camara import AnimadorCamara
from interfaz.cubo_vistas import CuboVistas
from interfaz.dialogo_configuracion import DialogoConfiguracion
from interfaz.dibujo import Previsualizacion, dibujar_modelo, dibujar_rejilla
from interfaz.herramientas import AgregarElemento, AgregarNodo, Seleccionar
from interfaz.iconos import icono
from interfaz.plano_trabajo import (PLANOS, Candidato, candidato, geometria_rejilla, interpretar,
                                    plano_por_defecto, texto_coordenadas)
from interfaz.tema import aplicar_tema

TECLAS_A_COMANDOS = set("0123456789.-@")   # escritas sobre la vista, van a la barra de comandos


class Ventana(QMainWindow):
    def __init__(self, modelo=None, ruta=None):
        super().__init__()
        self.resize(*ui.TAMANO_VENTANA)

        self.modelo = modelo if modelo is not None else Modelo()
        self.ruta = Path(ruta) if ruta else None   # archivo del modelo (None = todavía sin guardar)
        self.modificado = False
        self.seleccion = None                      # ("nodo", id), ("barra", id) o None
        self.actores = {}                          # lo dibujado: {"barras": actor, "rejilla": ...}
        self.plano, self.posicion_plano = plano_por_defecto(self.modelo)
        self.rejilla = None
        self.candidato = Candidato()               # dónde caería un clic ahora
        self._pos_presion = None                   # dónde se presionó el botón izquierdo
        self._mouse = None                         # última posición del mouse sobre la vista
        self._cerrando = False

        self.vista = QtInteractor(self)            # vista 3D: rotar, zoom y desplazar con el mouse
        self.setCentralWidget(self.vista)
        self.vista.add_axes()                      # ejes X, Y, Z en la esquina
        self.animador = AnimadorCamara(self.vista)  # giro suave de la cámara (cubo y Encuadre)
        self.previsualizacion = Previsualizacion(self.vista)

        self._crear_menus()
        self._crear_herramientas()
        self._crear_barra_comandos()
        self._crear_barra_inferior()

        self.redibujar(reiniciar_camara=True)
        self.cubo = CuboVistas(self.vista, self.animador)   # cubo de vistas, arriba a la derecha
        self._actualizar_titulo()
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
        """Botón de barra (QAction) con ícono, tooltip y, si se pide, atajo de teclado."""
        accion = QAction(icono(nombre_icono), texto, self)
        accion.setToolTip(ayuda)
        accion.setCheckable(activable)
        accion.setChecked(activa)
        if atajo:
            accion.setShortcut(QKeySequence(atajo))
        return accion

    # ---------- Menús (arriba) ----------
    def _crear_menus(self):
        menu = self.menuBar().addMenu("Archivo")
        for texto, atajo, funcion in (("Nuevo", "Ctrl+N", self.nuevo),
                                      ("Abrir…", "Ctrl+O", self.abrir),
                                      ("Guardar", "Ctrl+S", self.guardar),
                                      ("Guardar como…", "Ctrl+Shift+S", self.guardar_como)):
            accion = menu.addAction(texto)
            accion.setShortcut(QKeySequence(atajo))
            accion.triggered.connect(lambda *_, f=funcion: f())

        definir = self.menuBar().addMenu("Definir")         # etapas 1 y 3 de la hoja de ruta
        definir.setToolTipsVisible(True)
        for texto in ("Materiales…", "Secciones…", "Combinaciones de carga…"):
            accion = definir.addAction(texto)
            accion.setEnabled(False)
            accion.setToolTip("Próximamente")

        self.accion_configuracion = self.menuBar().addAction("Configuración")
        self.accion_configuracion.triggered.connect(self.abrir_configuracion)

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
                 AgregarElemento)):
            accion = self._accion(nombre, texto, ayuda, activable=True)
            herramienta = clase(self)
            accion.triggered.connect(lambda *_, h=herramienta: self.usar_herramienta(h))
            grupo.addAction(accion)
            self.herramientas.addAction(accion)
            self._herramientas.append((accion, herramienta))
        (self.accion_seleccionar, self.herramienta), (self.accion_nodo, _), (self.accion_elemento, _) = \
            self._herramientas
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
        self.actualizar_indicacion()
        self._actualizar_puntero()

    # ---------- Barra de comandos (abajo) ----------
    def _crear_barra_comandos(self):
        barra = QToolBar("Comandos", self)
        barra.setObjectName("barra_comandos")
        barra.setMovable(False)
        barra.setFloatable(False)
        self.indicacion = QLabel()                 # qué se espera del usuario
        self.comando = QLineEdit()                 # coordenadas exactas
        self.comando.setPlaceholderText("x, y, z")
        self.comando.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.comando.returnPressed.connect(self._ejecutar_comando)
        self.aviso = QLabel()                      # avisos cortos ("Nodo 6 agregado")
        for widget in (self.indicacion, self.comando, self.aviso):
            barra.addWidget(widget)
        self.addToolBar(Qt.BottomToolBarArea, barra)
        self._reloj_aviso = QTimer(self)
        self._reloj_aviso.setSingleShot(True)
        self._reloj_aviso.timeout.connect(self.aviso.clear)

    def actualizar_indicacion(self):
        self.indicacion.setText(self.herramienta.indicacion())

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
        """Esc: cancela lo que esté a medias; si no hay nada, vuelve a Seleccionar."""
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
                and evento.text() in TECLAS_A_COMANDOS
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

        self.accion_rejilla = self._accion("rejilla", "Rejilla", "", activable=True,
                                           activa=ui.REJILLA_VISIBLE, atajo=ui.ATAJO_REJILLA)
        self.accion_rejilla.toggled.connect(lambda activa: self._mostrar("rejilla", activa))
        self.accion_snap = self._accion("snap", "Snap", "", activable=True,
                                        activa=ui.SNAP_ACTIVO, atajo=ui.ATAJO_SNAP)
        self.accion_snap.toggled.connect(lambda *_: self._actualizar_puntero())
        self.accion_etiquetas = self._accion("etiqueta", "Etiquetas", "Etiquetas: números de nodo",
                                             activable=True, activa=ui.ETIQUETAS_VISIBLES)
        self.accion_etiquetas.toggled.connect(lambda activa: self._mostrar("etiquetas", activa))
        self.accion_encuadre = self._accion("encuadre", "Encuadre", "Encuadre: ajusta la vista al modelo")
        self.accion_encuadre.triggered.connect(self.encuadre)
        self._poner_ayudas()

        for accion in (self.accion_rejilla, self.accion_snap, self.accion_etiquetas):
            barra.addAction(accion)
        barra.addSeparator()                       # a la izquierda, estados; a la derecha, una acción
        barra.addAction(self.accion_encuadre)

        estado = self.statusBar()
        estado.setSizeGripEnabled(False)
        self.coordenadas = QLabel()                # posición del puntero
        estado.addWidget(self.coordenadas, 1)
        estado.addPermanentWidget(barra)
        self.barra_inferior = barra

    def _poner_ayudas(self):
        self.accion_rejilla.setToolTip(f"Rejilla ({ui.ATAJO_REJILLA})")
        self.accion_snap.setToolTip(f"Snap ({ui.ATAJO_SNAP}): pega el punto a nodos y a la rejilla")

    def _mostrar(self, nombre, visible, dibujar=True):
        """Muestra u oculta un actor de la vista ("rejilla", "etiquetas"...)."""
        actor = self.actores.get(nombre)
        if actor is not None:
            actor.SetVisibility(visible)
            if dibujar:
                self.vista.render()

    def encuadre(self):
        """Ajusta la vista al modelo sin cambiar la dirección, con el mismo giro suave del cubo."""
        self.animador.animar(lambda: self.vista.reset_camera(render=False))

    # ---------- Dibujo ----------
    def redibujar(self, reiniciar_camara=False):
        """Vuelve a dibujar el modelo y la rejilla. No mueve la cámara, salvo que se pida."""
        for actor in self.actores.values():
            self.vista.remove_actor(actor, render=False)
        self.vista.remove_actor("seleccion", render=False)
        self.seleccion = None
        self.vista.set_background(colores.FONDO_VISTA)
        self.actores = dibujar_modelo(self.vista, self.modelo)
        self.rejilla = geometria_rejilla(self.modelo, self.plano, self.posicion_plano)
        self.actores["rejilla"] = dibujar_rejilla(self.vista, self.rejilla,
                                                  cuenta_para_camara=not self.modelo.nodos)
        self._mostrar("rejilla", self.accion_rejilla.isChecked(), dibujar=False)
        self._mostrar("etiquetas", self.accion_etiquetas.isChecked(), dibujar=False)
        self.previsualizacion.actualizar_estilo()
        if reiniciar_camara:
            self.vista.view_isometric()
            self.vista.reset_camera()
        self.vista.renderer.ResetCameraClippingRange()
        self.vista.render()

    def modelo_cambiado(self, texto):
        """Lo llaman las herramientas después de agregar algo."""
        self.modificado = True
        self._actualizar_titulo()
        self.redibujar()
        self.mensaje(texto)
        self.actualizar_indicacion()
        self._actualizar_puntero()

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

    def _al_presionar(self, *_):
        self.animador.detener()                    # si la cámara estaba girando, manda el usuario
        self._pos_presion = self.vista.iren.get_event_position()

    def _al_mover(self, *_):
        if self._pos_presion is not None:          # arrastrando para rotar: no se recalcula nada
            return
        self._mouse = self.vista.iren.get_event_position()
        self.cubo.resaltar(*self._mouse)
        self._actualizar_puntero()

    def _al_salir(self, *_):
        self._mouse = None
        self.cubo.quitar_resaltado()
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
        """Resalta el nodo o la barra elegida. None quita la selección."""
        self.seleccion = seleccion
        self.vista.remove_actor("seleccion", render=False)
        if seleccion is not None:
            tipo, ident = seleccion
            if tipo == "nodo":
                punto = np.array([self.modelo.nodos[ident].coords], dtype=float)
                self.vista.add_points(punto, name="seleccion", color=colores.SELECCION,
                                      point_size=ui.TAMANO_SELECCION,
                                      render_points_as_spheres=True, reset_camera=False)
            else:
                el = self.modelo.elementos[ident]
                barra = pv.Line(self.modelo.nodos[el.ni].coords, self.modelo.nodos[el.nj].coords)
                self.vista.add_mesh(barra, name="seleccion", color=colores.SELECCION,
                                    line_width=ui.GROSOR_SELECCION, render_lines_as_tubes=True,
                                    reset_camera=False)
        self.vista.render()

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
        self._actualizar_titulo()
        self.mensaje(f"Guardado en {self.ruta.name}")
        return True

    def _cargar(self, modelo, ruta, vista):
        """Pone otro modelo en la ventana (Nuevo o Abrir)."""
        self.modelo, self.ruta, self.modificado = modelo, ruta, False
        plano, posicion = vista.get("plano"), vista.get("posicion")
        if plano in PLANOS and isinstance(posicion, (int, float)) and not isinstance(posicion, bool):
            self.plano, self.posicion_plano = plano, float(posicion)
        else:
            self.plano, self.posicion_plano = plano_por_defecto(modelo)
        for _, herramienta in self._herramientas:
            herramienta.reiniciar()
        self.redibujar(reiniciar_camara=True)
        self._actualizar_titulo()
        self.actualizar_indicacion()
        self._actualizar_puntero()

    # ---------- Configuración ----------
    def abrir_configuracion(self):
        dialogo = DialogoConfiguracion(self, self.plano, self.posicion_plano)
        if dialogo.exec() != QDialog.Accepted:
            return
        plano = dialogo.plano_elegido()
        if plano != (self.plano, self.posicion_plano):
            self.plano, self.posicion_plano = plano
            self.modificado = True                 # el plano se guarda con el modelo
        self.aplicar_configuracion()

    def aplicar_configuracion(self):
        """Toma los valores vigentes de configuracion/ (después de cambiarlos en el diálogo)."""
        aplicar_tema(QApplication.instance())
        self.herramientas.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        self.barra_inferior.setIconSize(QSize(ui.TAMANO_ICONO_INFERIOR, ui.TAMANO_ICONO_INFERIOR))
        self.accion_rejilla.setShortcut(QKeySequence(ui.ATAJO_REJILLA))
        self.accion_snap.setShortcut(QKeySequence(ui.ATAJO_SNAP))
        self._poner_ayudas()
        self.cubo.actualizar_colores()
        self.cubo.ajustar_tamano()
        self.redibujar()
        self._actualizar_titulo()
        self.actualizar_indicacion()
        self._actualizar_puntero()
        for barra in (self.herramientas, self.barra_inferior):
            barra.update()                         # los íconos se vuelven a pintar con su color

    # ---------- Ventana ----------
    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if hasattr(self, "cubo"):
            QTimer.singleShot(0, self._ajustar_cubo)   # después de que la vista tome su tamaño

    def _ajustar_cubo(self):
        if not self._cerrando:
            self.cubo.ajustar_tamano()
            self.vista.render()

    def closeEvent(self, evento):
        if not self._confirmar_descartar():
            evento.ignore()
            return
        self._cerrando = True
        self.animador.detener()                    # que el giro no siga con la ventana cerrándose
        self.cubo.apagar()                         # apaga el cubo antes de cerrar la vista 3D
        self.vista.close()                         # libera la ventana 3D al cerrar
        super().closeEvent(evento)
