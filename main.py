import sys
from PySide6.QtWidgets import QApplication
from configuracion import preferencias
from configuracion.formato import configurar
from ejemplos.marco_acero import crear_marco
from interfaz.tema import aplicar_tema
from interfaz.ventana import Ventana

def main():
    preferencias.cargar()                 # cambios del usuario encima de la personalización base
    configurar()
    app = QApplication(sys.argv)
    aplicar_tema(app)                     # interfaz en blanco y negro
    ventana = Ventana(crear_marco())            # el marco de acero de la tarea (ejemplos/portico.py: el de prueba)
    ventana.showMaximized()               # siempre abre maximizada
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
