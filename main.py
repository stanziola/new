import sys
from PySide6.QtWidgets import QApplication
from configuracion import preferencias
from configuracion.formato import configurar
from ejemplos.portico import crear_portico
from interfaz.tema import aplicar_tema
from interfaz.ventana import Ventana

def main():
    preferencias.cargar()                 # cambios del usuario encima de la personalización base
    configurar()
    app = QApplication(sys.argv)
    aplicar_tema(app)                     # interfaz en blanco y negro
    ventana = Ventana(crear_portico())
    ventana.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
