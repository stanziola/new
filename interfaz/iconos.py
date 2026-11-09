"""Íconos de la interfaz: dibujos propios con QPainter (sin archivos de imagen ni derechos de autor).

Cada ícono es una función que dibuja en una cuadrícula de 24 x 24 con línea negra, sin relleno.
IconoVectorial los dibuja al tamaño exacto que pide la pantalla: se ven nítidos con cualquier
escala de Windows (100, 125, 150 %...). Un pixmap fijo, en cambio, se estira y queda borroso.
Deshabilitados se dibujan en gris. El color se lee al dibujar, así que sigue a Configuración.
"""
from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QIconEngine, QPainter, QPen, QPixmap, QPolygonF

from configuracion import colores
from configuracion import interfaz as ui

_vivos = []   # copias hechas por clone(): se guardan para que Python no las libere antes que Qt


class IconoVectorial(QIconEngine):
    """Motor de ícono que llama a una función de dibujo en la cuadrícula de 24 x 24."""

    def __init__(self, dibujar):
        super().__init__()
        self._dibujar = dibujar

    def paint(self, painter, rect, mode, state):
        color = QColor(colores.ICONO_DESHABILITADO if mode == QIcon.Mode.Disabled else colores.ICONO)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(rect.x(), rect.y())
        painter.scale(rect.width() / 24, rect.height() / 24)
        painter.setPen(QPen(color, ui.ICONO_GROSOR, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        self._dibujar(painter, color)
        painter.restore()

    def pixmap(self, size, mode, state):
        return self.scaledPixmap(size, mode, state, 1.0)

    def scaledPixmap(self, size, mode, state, escala):
        """Pixmap con los píxeles reales de la pantalla (tamaño x escala)."""
        pix = QPixmap(size * escala)
        pix.setDevicePixelRatio(escala)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        self.paint(p, QRect(0, 0, size.width(), size.height()), mode, state)
        p.end()
        return pix

    def clone(self):
        copia = IconoVectorial(self._dibujar)
        _vivos.append(copia)
        return copia


def _poligono(puntos):
    return QPolygonF([QPointF(x, y) for x, y in puntos])


# Flecha de puntero: punta arriba a la izquierda
_FLECHA = [(0, 0), (0, 15.5), (4, 11.7), (6.8, 17.5), (9.1, 16.4), (6.4, 10.8), (11.8, 10.8)]


def _flecha(punta, escala=1.0):
    return _poligono([(punta[0] + escala * x, punta[1] + escala * y) for x, y in _FLECHA])


def _punto(p, color, centro, radio):
    """Punto relleno (un nodo)."""
    p.setBrush(color)
    p.drawEllipse(QPointF(*centro), radio, radio)
    p.setBrush(Qt.NoBrush)


def _seleccionar(p, color):
    p.drawPolygon(_flecha((6.5, 3.5)))


def _nodo(p, color):
    _punto(p, color, (9.5, 14.5), 3.2)                      # el nodo
    p.drawLine(QPointF(17.5, 3.5), QPointF(17.5, 11.5))     # el "+" de agregar
    p.drawLine(QPointF(13.5, 7.5), QPointF(21.5, 7.5))


def _elemento(p, color):
    p.drawLine(QPointF(6, 18), QPointF(18, 6))               # la barra
    _punto(p, color, (6, 18), 2.4)                           # sus dos nodos
    _punto(p, color, (18, 6), 2.4)


def _mas(p, centro, brazo=3.0):
    """El "+" de agregar."""
    x, y = centro
    p.drawLine(QPointF(x, y - brazo), QPointF(x, y + brazo))
    p.drawLine(QPointF(x - brazo, y), QPointF(x + brazo, y))


def _material(p, color):
    """Un bloque (cubo en perspectiva) con un "+": agregar material."""
    p.drawPolygon(_poligono([(3, 9), (9, 6), (15, 9), (9, 12)]))               # cara de arriba
    p.drawPolyline(_poligono([(3, 9), (3, 17), (9, 20), (15, 17), (15, 9)]))   # contorno de abajo
    p.drawLine(QPointF(9, 12), QPointF(9, 20))                                 # arista del frente
    _mas(p, (19.5, 5.5))


def _seccion(p, color):
    """Un perfil en I con un "+": agregar sección."""
    p.drawPolygon(_poligono([(3, 5), (15, 5), (15, 8), (10.5, 8), (10.5, 16), (15, 16), (15, 19),
                             (3, 19), (3, 16), (7.5, 16), (7.5, 8), (3, 8)]))
    _mas(p, (19.5, 5.5))


def _rejilla(p, color):
    p.drawRoundedRect(QRectF(4, 4, 16, 16), 1.5, 1.5)
    for c in (4 + 16 / 3, 4 + 32 / 3):
        p.drawLine(QPointF(c, 4), QPointF(c, 20))
        p.drawLine(QPointF(4, c), QPointF(20, c))


def _snap(p, color):
    _punto(p, color, (7, 7), 2.2)                            # el nodo
    p.drawPolygon(_flecha((10, 10), 0.68))                   # el cursor, con la punta tocando el nodo


def _etiqueta(p, color):
    p.translate(12, 12)                     # etiqueta en diagonal, con la punta arriba a la izquierda
    p.rotate(45)
    p.translate(-12, -12)
    p.drawPolygon(_poligono([(3.5, 12), (8.5, 7), (20, 7), (20, 17), (8.5, 17)]))
    p.drawEllipse(QPointF(9, 12), 1.4, 1.4)  # el agujero


def _encuadre(p, color):
    a, b, l = 4, 20, 5.5                    # cuadro de 4 a 20; cada esquina mide l
    for (x, y), (dx, dy) in (((a, a), (1, 1)), ((b, a), (-1, 1)), ((b, b), (-1, -1)), ((a, b), (1, -1))):
        p.drawPolyline(_poligono([(x, y + dy * l), (x, y), (x + dx * l, y)]))


_DIBUJOS = {
    "seleccionar": _seleccionar,
    "nodo": _nodo,
    "elemento": _elemento,
    "material": _material,
    "seccion": _seccion,
    "rejilla": _rejilla,
    "snap": _snap,
    "etiqueta": _etiqueta,
    "encuadre": _encuadre,
}


def icono(nombre):
    """QIcon vectorial: "seleccionar", "nodo", "elemento", "material", "seccion", "rejilla", "snap",
    "etiqueta" o "encuadre"."""
    return QIcon(IconoVectorial(_DIBUJOS[nombre]))
