"""Ventana principal: vista 3D, barra de herramientas (izquierda) y barra inferior.

- Barra izquierda: herramientas que cambian lo que hace el clic (hoy, Seleccionar). Una activa a
  la vez, solo íconos con tooltip.
- Barra inferior, a la derecha: cómo se ve el modelo (Rejilla, Snap, Etiquetas) y Encuadre. A la
  izquierda de esa barra van los mensajes y los datos de lo seleccionado.
"""
import numpy as np
import pyvista as pv
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QMainWindow, QToolBar
from pyvistaqt import QtInteractor
from interfaz.camara import AnimadorCamara
from interfaz.cubo_vistas import CuboVistas
from interfaz.dibujo import dibujar_modelo, dibujar_rejilla
from interfaz.iconos import icono
from interfaz.seleccion import elemento_en, texto_seleccion
from interfaz import estilo as es


class Ventana(QMainWindow):
    def __init__(self, modelo):
        super().__init__()
        self.setWindowTitle(es.TITULO_VENTANA)
        self.resize(*es.TAMANO_VENTANA)

        self.modelo = modelo
        self.seleccion = None                  # ("nodo", id), ("barra", id) o None
        self._pos_presion = None               # dónde se presionó el botón izquierdo
        self.actores = {}                      # lo dibujado: {"barras": actor, "rejilla": actor...}

        self.vista = QtInteractor(self)        # vista 3D: rotar, zoom y desplazar con el mouse
        self.setCentralWidget(self.vista)
        self.animador = AnimadorCamara(self.vista)   # giro suave de la cámara (cubo y Encuadre)
        self._crear_herramientas()
        self._crear_barra_inferior()

        self.redibujar()
        self.cubo = CuboVistas(self.vista, self.animador)   # cubo de vistas, arriba a la derecha

        # Clic = presionar y soltar casi en el mismo punto. Arrastrar sigue rotando la vista.
        self.vista.iren.add_observer("LeftButtonPressEvent", self._al_presionar)
        self.vista.iren.add_observer("LeftButtonReleaseEvent", self._al_soltar)
        # Si el usuario desplaza o hace zoom a mitad de un giro, manda el usuario.
        for evento in ("MiddleButtonPressEvent", "RightButtonPressEvent",
                       "MouseWheelForwardEvent", "MouseWheelBackwardEvent"):
            self.vista.iren.add_observer(evento, lambda *_: self.animador.detener())
        # Al pasar el mouse sobre el cubo se sombrea la vista que daría el clic.
        self.vista.iren.add_observer("MouseMoveEvent", self._al_mover)
        self.vista.iren.add_observer("LeaveEvent", lambda *_: self.cubo.quitar_resaltado())

    def _accion(self, nombre_icono, texto, ayuda, activable=False, activa=False, atajo=None):
        """Botón de barra (QAction) con ícono, tooltip y, si se pide, atajo de teclado."""
        accion = QAction(icono(nombre_icono), texto, self)
        accion.setToolTip(ayuda)
        accion.setCheckable(activable)
        accion.setChecked(activa)
        if atajo:
            accion.setShortcut(QKeySequence(atajo))
        return accion

    # ---------- Panel de herramientas (izquierda) ----------
    def _crear_herramientas(self):
        self.herramientas = QToolBar("Herramientas", self)
        self.herramientas.setObjectName("herramientas")   # la hoja de estilo le pone un borde a la derecha
        self.herramientas.setMovable(False)
        self.herramientas.setFloatable(False)
        self.herramientas.setIconSize(QSize(es.TAMANO_ICONO, es.TAMANO_ICONO))
        self.addToolBar(Qt.LeftToolBarArea, self.herramientas)

        grupo = QActionGroup(self)             # una sola herramienta activa a la vez
        self.accion_seleccionar = self._accion(
            "seleccionar", "Seleccionar", "Seleccionar: clic sobre un nodo o una barra",
            activable=True, activa=True)       # herramienta por defecto
        grupo.addAction(self.accion_seleccionar)
        self.herramientas.addAction(self.accion_seleccionar)

    # ---------- Barra inferior (derecha de la barra de estado) ----------
    def _crear_barra_inferior(self):
        barra = QToolBar("Vista", self)
        barra.setObjectName("barra_inferior")
        barra.setMovable(False)
        barra.setFloatable(False)
        barra.setIconSize(QSize(es.TAMANO_ICONO_INFERIOR, es.TAMANO_ICONO_INFERIOR))

        self.accion_rejilla = self._accion(
            "rejilla", "Rejilla", f"Rejilla ({es.ATAJO_REJILLA})",
            activable=True, activa=es.REJILLA_VISIBLE, atajo=es.ATAJO_REJILLA)
        self.accion_rejilla.toggled.connect(lambda activa: self._mostrar("rejilla", activa))

        self.accion_snap = self._accion(
            "snap", "Snap", f"Snap ({es.ATAJO_SNAP}): disponible cuando exista la herramienta de dibujo",
            activable=True, atajo=es.ATAJO_SNAP)
        self.accion_snap.setEnabled(False)     # todavía no hay herramienta para dibujar

        self.accion_etiquetas = self._accion(
            "etiqueta", "Etiquetas", "Etiquetas: números de nodo",
            activable=True, activa=es.ETIQUETAS_VISIBLES)
        self.accion_etiquetas.toggled.connect(lambda activa: self._mostrar("etiquetas", activa))

        self.accion_encuadre = self._accion("encuadre", "Encuadre", "Encuadre: ajusta la vista al modelo")
        self.accion_encuadre.triggered.connect(self.encuadre)

        for accion in (self.accion_rejilla, self.accion_snap, self.accion_etiquetas):
            barra.addAction(accion)
        barra.addSeparator()                   # a la izquierda, estados; a la derecha, una acción
        barra.addAction(self.accion_encuadre)

        estado = self.statusBar()
        estado.setSizeGripEnabled(False)
        estado.addPermanentWidget(barra)       # a la derecha; los mensajes quedan a la izquierda
        self.barra_inferior = barra

    # ---------- Dibujo ----------
    def redibujar(self):
        """Borra la vista y vuelve a dibujar el modelo, con la rejilla y las etiquetas según sus botones."""
        self.vista.clear()
        self.vista.set_background(es.COLOR_FONDO)
        self.actores = dibujar_modelo(self.vista, self.modelo)   # {"barras": actor, ...}
        self.actores["rejilla"] = dibujar_rejilla(self.vista, self.modelo)
        self._mostrar("rejilla", self.accion_rejilla.isChecked(), dibujar=False)
        self._mostrar("etiquetas", self.accion_etiquetas.isChecked(), dibujar=False)
        self.vista.add_axes()                  # ejes X, Y, Z en la esquina
        self.vista.view_isometric()
        self.vista.reset_camera()
        self.seleccion = None
        self.statusBar().showMessage("Listo")

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

    # ---------- Clic en la vista ----------
    def _al_presionar(self, *_):
        self.animador.detener()                # si la cámara estaba girando, manda el usuario
        self._pos_presion = self.vista.iren.get_event_position()

    def _al_mover(self, *_):
        if self._pos_presion is None:          # mientras se arrastra para rotar, no se resalta
            self.cubo.resaltar(*self.vista.iren.get_event_position())

    def _al_soltar(self, *_):
        if self._pos_presion is None:
            return
        x, y = self.vista.iren.get_event_position()
        x0, y0 = self._pos_presion
        self._pos_presion = None
        if abs(x - x0) > es.TOL_CLIC_PX or abs(y - y0) > es.TOL_CLIC_PX:
            return                             # fue un arrastre para rotar, no un clic
        self._clic(x, y)

    def _clic(self, x, y):
        if self.cubo.clic(x, y):               # clic sobre el cubo: gira hasta esa vista
            return
        if self.accion_seleccionar.isChecked():
            self.seleccionar(elemento_en(self.vista.renderer, self.modelo, x, y,
                                         es.TOL_SELECCION_PX))

    # ---------- Selección ----------
    def seleccionar(self, seleccion):
        """Resalta el nodo o la barra elegida y muestra sus datos. None quita la selección."""
        self.seleccion = seleccion
        if seleccion is None:
            self.vista.remove_actor("seleccion")
            self.statusBar().showMessage("Listo")
            return
        tipo, ident = seleccion
        if tipo == "nodo":
            punto = np.array([self.modelo.nodos[ident].coords], dtype=float)
            self.vista.add_points(punto, name="seleccion", color=es.COLOR_SELECCION,
                                  point_size=es.TAMANO_SELECCION,
                                  render_points_as_spheres=True, reset_camera=False)
        else:
            el = self.modelo.elementos[ident]
            barra = pv.Line(self.modelo.nodos[el.ni].coords, self.modelo.nodos[el.nj].coords)
            self.vista.add_mesh(barra, name="seleccion", color=es.COLOR_SELECCION,
                                line_width=es.GROSOR_SELECCION, render_lines_as_tubes=True,
                                reset_camera=False)
        self.statusBar().showMessage(texto_seleccion(self.modelo, seleccion))

    def closeEvent(self, evento):
        self.animador.detener()                # que el giro no siga con la ventana cerrándose
        self.cubo.apagar()                     # apaga el cubo antes de cerrar la vista 3D
        self.vista.close()                     # libera la ventana 3D al cerrar
        super().closeEvent(evento)
