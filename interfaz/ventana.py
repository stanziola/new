import numpy as np
import pyvista as pv
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMainWindow, QToolBar
from pyvistaqt import QtInteractor
from interfaz.cubo_vistas import CuboVistas
from interfaz.dibujo import dibujar_modelo
from interfaz.iconos import icono_cursor
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

        self.vista = QtInteractor(self)        # vista 3D: rotar, zoom y desplazar con el mouse
        self.setCentralWidget(self.vista)
        self._crear_herramientas()

        self.redibujar()
        self.cubo = CuboVistas(self.vista)     # cubo de vistas, esquina superior derecha

        # Clic = presionar y soltar casi en el mismo punto. Arrastrar sigue rotando la vista.
        self.vista.iren.add_observer("LeftButtonPressEvent", self._al_presionar)
        self.vista.iren.add_observer("LeftButtonReleaseEvent", self._al_soltar)
        # Al pasar el mouse sobre el cubo se sombrea la vista que daría el clic.
        self.vista.iren.add_observer("MouseMoveEvent", self._al_mover)
        self.vista.iren.add_observer("LeaveEvent", lambda *_: self.cubo.quitar_resaltado())

    # ---------- Panel de herramientas (derecha) ----------
    def _crear_herramientas(self):
        self.herramientas = QToolBar("Herramientas", self)
        self.herramientas.setMovable(False)
        self.herramientas.setIconSize(QSize(es.TAMANO_ICONO, es.TAMANO_ICONO))
        self.addToolBar(Qt.RightToolBarArea, self.herramientas)

        grupo = QActionGroup(self)             # una sola herramienta activa a la vez
        self.accion_seleccionar = QAction(icono_cursor(es.TAMANO_ICONO), "Seleccionar", self)
        self.accion_seleccionar.setCheckable(True)
        self.accion_seleccionar.setChecked(True)   # herramienta por defecto
        self.accion_seleccionar.setToolTip("Seleccionar: clic sobre un nodo o una barra")
        grupo.addAction(self.accion_seleccionar)
        self.herramientas.addAction(self.accion_seleccionar)

    def redibujar(self):
        """Borra la vista y vuelve a dibujar el modelo."""
        self.vista.clear()
        self.vista.set_background(es.COLOR_FONDO)
        dibujar_modelo(self.vista, self.modelo)
        self.vista.add_axes()                  # ejes X, Y, Z en la esquina
        self.vista.view_isometric()
        self.vista.reset_camera()
        self.seleccion = None
        self.statusBar().showMessage("Listo")

    # ---------- Clic en la vista ----------
    def _al_presionar(self, *_):
        self.cubo.detener_animacion()          # si el cubo estaba girando, manda el usuario
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
        self.cubo.apagar()                     # apaga el cubo antes de cerrar la vista 3D
        self.vista.close()                     # libera la ventana 3D al cerrar
        super().closeEvent(evento)
