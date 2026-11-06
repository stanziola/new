from PySide6.QtWidgets import QMainWindow
from pyvistaqt import QtInteractor
from interfaz.dibujo import dibujar_modelo
from interfaz import estilo as es


class Ventana(QMainWindow):
    def __init__(self, modelo):
        super().__init__()
        self.setWindowTitle(es.TITULO_VENTANA)
        self.resize(*es.TAMANO_VENTANA)

        self.modelo = modelo
        self.vista = QtInteractor(self)        # vista 3D: rotar, zoom y desplazar con el mouse
        self.setCentralWidget(self.vista)

        self.redibujar()

    def redibujar(self):
        """Borra la vista y vuelve a dibujar el modelo."""
        self.vista.clear()
        self.vista.set_background(es.COLOR_FONDO)
        dibujar_modelo(self.vista, self.modelo)
        self.vista.add_axes()                  # ejes X, Y, Z en la esquina
        self.vista.view_isometric()
        self.vista.reset_camera()

    def closeEvent(self, evento):
        self.vista.close()                     # libera la ventana 3D al cerrar
        super().closeEvent(evento)