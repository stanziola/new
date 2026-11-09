"""Animación de la cámara de la vista 3D: la usan el cubo de vistas y el botón Encuadre.

Hay un solo animador para toda la ventana. Si empieza un giro nuevo, reemplaza al que estaba en
curso: así el cubo y Encuadre nunca se pelean por la cámara.

Cómo funciona: un QTimer llama a _paso cada pocos milisegundos. En cada cuadro se calcula una
cámara intermedia con interfaz/animacion.py (slerp de cuaterniones) según el tiempo transcurrido.
Al terminar se emite la señal `terminada`; el cubo la usa para actualizar su resaltado.
"""
import numpy as np
from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Signal

from configuracion import interfaz as ui
from interfaz.animacion import interpolar_camara, suavizar


def leer_camara(camara):
    """(posición, foco, arriba) de una cámara de VTK, como arreglos de numpy."""
    return (np.array(camara.GetPosition()), np.array(camara.GetFocalPoint()),
            np.array(camara.GetViewUp()))


def poner_camara(camara, posicion, foco, arriba):
    camara.SetFocalPoint(*foco)
    camara.SetPosition(*posicion)
    camara.SetViewUp(*arriba)


class AnimadorCamara(QObject):
    """Gira la cámara suavemente desde donde está hasta una vista final."""

    terminada = Signal()                    # se emite al llegar a la vista final

    def __init__(self, vista):
        super().__init__(vista)             # la vista es su "padre" en Qt: se libera junto con ella
        self.vista = vista
        self._timer = QTimer(self)
        self._timer.setInterval(ui.ANIM_CAMARA_INTERVALO_MS)
        self._timer.timeout.connect(self._paso)
        self._reloj = QElapsedTimer()       # mide el tiempo real desde que empezó el giro
        self._inicio = self._fin = None     # cámaras de inicio y fin: (posición, foco, arriba)

    def activa(self):
        return self._timer.isActive()

    def animar(self, poner_destino):
        """Gira desde la cámara actual hasta la que deja poner_destino().

        poner_destino es una función que pone la vista final sin dibujar (por ejemplo,
        view_vector o reset_camera con render=False). Se usa solo para calcularla: la cámara
        vuelve al inicio y el giro la lleva hasta ahí.
        """
        camara = self.vista.renderer.GetActiveCamera()
        self._inicio = leer_camara(camara)
        poner_destino()
        self._fin = leer_camara(camara)
        poner_camara(camara, *self._inicio)
        self._reloj.start()
        self._timer.start()

    def detener(self):
        """Corta el giro; la cámara se queda donde iba (por ejemplo, si el usuario empieza a rotar)."""
        self._timer.stop()

    def _paso(self):
        """Un cuadro de la animación: pone la cámara intermedia según el tiempo transcurrido."""
        duracion = ui.ANIM_CAMARA_DURACION_MS
        t = 1.0 if duracion <= 0 else min(self._reloj.elapsed() / duracion, 1.0)   # 0 = sin animación
        camara = self.vista.renderer.GetActiveCamera()
        if t < 1.0:
            poner_camara(camara, *interpolar_camara(self._inicio, self._fin, suavizar(t)))
        else:
            poner_camara(camara, *self._fin)   # el último cuadro, exacto
            self._timer.stop()
        self.vista.renderer.ResetCameraClippingRange()   # que no se corte el modelo al moverse
        self.vista.render()
        if t >= 1.0:
            self.terminada.emit()
