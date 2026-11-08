"""Íconos de la interfaz, dibujados con QPainter (sin archivos de imagen)."""
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF


def icono_cursor(tamano=32):
    """Flecha de puntero del mouse: herramienta Seleccionar."""
    pix = QPixmap(tamano, tamano)
    pix.fill(Qt.transparent)
    s = tamano / 32                          # los puntos están pensados para 32 x 32
    puntos = [(9, 4), (9, 26), (14, 21), (18, 29), (21.5, 27.5), (17.5, 19.5), (24, 19.5)]
    flecha = QPolygonF([QPointF(x * s, y * s) for x, y in puntos])
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("black"), 1.6 * s))
    p.setBrush(QColor("white"))
    p.drawPolygon(flecha)
    p.end()
    return QIcon(pix)
