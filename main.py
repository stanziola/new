import sys
from PySide6.QtWidgets import QApplication
from configuracion import configurar
from ejemplos.portico import crear_portico
from interfaz.ventana import Ventana

def main():
    configurar()
    app = QApplication(sys.argv)
    ventana = Ventana(crear_portico())
    ventana.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()