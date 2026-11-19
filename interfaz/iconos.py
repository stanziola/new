"""Íconos de la interfaz: dibujos propios con QPainter (sin archivos de imagen ni derechos de autor).

Cada ícono es una función que dibuja en una cuadrícula de 24 x 24 con línea negra, sin relleno.
IconoVectorial los dibuja al tamaño exacto que pide la pantalla: se ven nítidos con cualquier
escala de Windows (100, 125, 150 %...). Un pixmap fijo, en cambio, se estira y queda borroso.
Deshabilitados se dibujan en gris. El color se lee al dibujar, así que sigue a Configuración.
"""
from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QIconEngine, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

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
    """Agregar elemento: una barra con sus dos nodos y el "+", como Nodo, Apoyo y Cargas."""
    p.drawLine(QPointF(4.5, 19.5), QPointF(14, 10))          # la barra
    _punto(p, color, (4.5, 19.5), 2.4)                       # sus dos nodos
    _punto(p, color, (14, 10), 2.4)
    _mas(p, (19.5, 5.5))


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


def _asignar_seccion(p, color):
    """Asignar sección: un perfil en I pequeño y una flecha que baja hasta una barra (sin "+": no
    crea nada, asigna)."""
    p.drawPolygon(_poligono([(3, 3), (11, 3), (11, 5), (8, 5), (8, 10), (11, 10), (11, 12),
                             (3, 12), (3, 10), (6, 10), (6, 5), (3, 5)]))
    p.drawLine(QPointF(16.5, 4), QPointF(16.5, 15))          # la flecha
    _punta(p, 16.5, 15, 0, 1, 2.6)
    p.drawLine(QPointF(3, 19.5), QPointF(21, 19.5))          # la barra
    _punto(p, color, (3, 19.5), 1.8)
    _punto(p, color, (21, 19.5), 1.8)


def _rayado(p, x0, x1, y):
    """Rayas inclinadas bajo una línea de suelo: el símbolo de "fijo al terreno"."""
    x = x0 + 1
    while x <= x1:
        p.drawLine(QPointF(x, y), QPointF(x - 3, y + 3))
        x += 4


def _apoyo_fijo(p, color):
    """Apoyo fijo: triángulo con el nodo en la punta, sobre el suelo rayado."""
    _punto(p, color, (12, 6), 2.2)
    p.drawPolygon(_poligono([(12, 7), (5.5, 16), (18.5, 16)]))
    p.drawLine(QPointF(3.5, 18), QPointF(20.5, 18))
    _rayado(p, 5, 20, 18)


def _empotrado(p, color):
    """Empotrado: el nodo unido a una placa pegada al suelo."""
    _punto(p, color, (12, 5), 2.2)
    p.drawLine(QPointF(12, 6), QPointF(12, 12))
    p.drawRect(QRectF(4.5, 12, 15, 4))
    _rayado(p, 6, 20, 16)


def _libre(p, color):
    """Libre: el nodo solo, sin nada que lo sujete."""
    _punto(p, color, (12, 12), 2.6)


def _apoyo(p, color):
    """Herramienta Apoyo: un apoyo fijo con el "+" de agregar."""
    _punto(p, color, (10, 8), 2.0)
    p.drawPolygon(_poligono([(10, 9), (4, 17), (16, 17)]))
    p.drawLine(QPointF(2.5, 19.5), QPointF(17.5, 19.5))
    _mas(p, (19.5, 5.5))


def _punta(p, x, y, dx, dy, largo=3.2):
    """Punta de flecha en (x, y), apuntando en la dirección (dx, dy)."""
    n = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / n, dy / n
    p.drawPolyline(_poligono([(x - largo * (ux - 0.6 * uy), y - largo * (uy + 0.6 * ux)), (x, y),
                              (x - largo * (ux + 0.6 * uy), y - largo * (uy - 0.6 * ux))]))


def _carga_nodo(p, color):
    """Carga en nodo: una flecha que llega a un nodo, con el "+"."""
    _punto(p, color, (9, 17), 2.4)
    p.drawLine(QPointF(9, 4), QPointF(9, 14))
    _punta(p, 9, 14, 0, 1)
    _mas(p, (19.5, 5.5))


def _carga_barra(p, color):
    """Carga en barra: una barra con flechas repartidas encima, con el "+"."""
    p.drawLine(QPointF(2.5, 19), QPointF(17.5, 19))
    p.drawLine(QPointF(2.5, 9.5), QPointF(17.5, 9.5))
    for x in (4, 10, 16):
        p.drawLine(QPointF(x, 9.5), QPointF(x, 16.5))
        _punta(p, x, 16.5, 0, 1, 2.6)
    _mas(p, (20.5, 4.5), 2.5)


def _carga_uniforme(p, color):
    """Tipo de carga en barra: uniforme (una fila de flechas, unidas arriba, sobre toda la barra)."""
    p.drawLine(QPointF(3, 19), QPointF(21, 19))
    p.drawLine(QPointF(4, 7), QPointF(20, 7))
    for x in (4, 9.3, 14.7, 20):
        p.drawLine(QPointF(x, 7), QPointF(x, 16))
        _punta(p, x, 16, 0, 1, 2.4)


def _carga_trapezoidal(p, color):
    """Tipo de carga en barra: trapezoidal (flechas que crecen en línea recta, en un tramo de la barra)."""
    p.drawLine(QPointF(3, 19), QPointF(21, 19))
    p.drawLine(QPointF(7, 12), QPointF(20, 5))                 # la línea de la carga, inclinada
    for x in (7, 13.5, 20):
        arriba = 12 - (x - 7) * 7 / 13
        p.drawLine(QPointF(x, arriba), QPointF(x, 16))
        _punta(p, x, 16, 0, 1, 2.4)


def _carga_puntual(p, color):
    """Tipo de carga en barra: una fuerza puntual."""
    p.drawLine(QPointF(3, 19), QPointF(21, 19))
    p.drawLine(QPointF(12, 4), QPointF(12, 16))
    _punta(p, 12, 16, 0, 1, 3.4)


def _carga_momento(p, color):
    """Tipo de carga en barra: un momento concentrado (una flecha que gira sobre un punto de la barra)."""
    p.drawLine(QPointF(3, 19), QPointF(21, 19))
    _punto(p, color, (12, 19), 1.4)
    p.drawArc(QRectF(5.5, 6.5, 13, 13), -20 * 16, 220 * 16)       # de la derecha, por arriba, a la izquierda
    _punta(p, 5.9, 15.2, 0.35, 1, 3.0)


def _cargas(p, color):
    """Cargas visibles: flechas que bajan sobre una barra (sin "+": solo muestra u oculta)."""
    p.drawLine(QPointF(3, 19), QPointF(21, 19))
    for x in (6, 12, 18):
        p.drawLine(QPointF(x, 5), QPointF(x, 16))
        _punta(p, x, 16, 0, 1, 2.6)


def _reacciones(p, color):
    """Reacciones: un apoyo (triángulo sobre el suelo) y, debajo, la flecha de la reacción, que sube."""
    p.drawPolygon(_poligono([(12, 3), (6.5, 10.5), (17.5, 10.5)]))
    p.drawLine(QPointF(4, 10.5), QPointF(20, 10.5))
    p.drawLine(QPointF(12, 21), QPointF(12, 14))
    _punta(p, 12, 13.5, 0, -1, 3.0)


def _losa(p, color):
    """Agregar losa: la losa nervada en corte (la losa arriba y tres nervios) con el "+" de agregar."""
    p.drawRect(QRectF(2.5, 11, 19, 3))                                       # la losa
    for x in (4.5, 11, 17.5):                                                # los nervios
        p.drawPolyline(_poligono([(x, 14), (x, 20), (x + 2, 20), (x + 2, 14)]))
    _mas(p, (19, 5.5))


def _medir(p, color):
    """Medir: una regla inclinada con sus marcas."""
    p.drawPolygon(_poligono([(2.5, 16), (16, 2.5), (21.5, 8), (8, 21.5)]))
    for k in range(1, 6):                                                     # las marcas
        x, y = 2.5 + k * 2.25, 16 - k * 2.25
        largo = 3.0 if k % 2 else 1.8
        p.drawLine(QPointF(x, y), QPointF(x + largo * 0.707, y + largo * 0.707))


def _combinaciones(p, color):
    """Combinaciones: la Σ de la suma de los casos por sus factores."""
    p.drawPolyline(_poligono([(18, 7), (18, 4.5), (6, 4.5), (12.5, 12), (6, 19.5), (18, 19.5), (18, 17)]))


def _analizar(p, color):
    """Analizar: el triángulo de "play", relleno."""
    p.setBrush(color)
    p.drawPolygon(_poligono([(7, 4.5), (19.5, 12), (7, 19.5)]))
    p.setBrush(Qt.NoBrush)


def _deformada(p, color):
    """Deformada: la barra recta (punteada) y la curva deformada."""
    pluma = p.pen()
    punteada = QPen(pluma)
    punteada.setStyle(Qt.DashLine)
    punteada.setWidthF(1.0)
    p.setPen(punteada)
    p.drawLine(QPointF(3, 8), QPointF(21, 8))
    p.setPen(pluma)
    camino = QPainterPath(QPointF(3, 8))
    camino.cubicTo(QPointF(8, 19), QPointF(16, 19), QPointF(21, 8))
    p.drawPath(camino)
    for x in (3, 21):
        _punto(p, color, (x, 8), 1.6)


def _axial(p, color):
    """Axial: una barra con dos flechas que la estiran, y la N."""
    p.drawLine(QPointF(6, 15), QPointF(18, 15))
    p.drawLine(QPointF(2, 15), QPointF(6, 15))
    p.drawLine(QPointF(18, 15), QPointF(22, 15))
    _punta(p, 2.5, 15, -1, 0, 2.6)
    _punta(p, 21.5, 15, 1, 0, 2.6)
    p.drawPolyline(_poligono([(8.5, 10), (8.5, 3.5), (15.5, 10), (15.5, 3.5)]))


def _cortante(p, color):
    """Cortante: el diagrama en escalón de una viga simple con carga al centro."""
    p.drawLine(QPointF(3, 12), QPointF(21, 12))
    p.drawPolyline(_poligono([(3, 12), (3, 6), (12, 6), (12, 18), (21, 18), (21, 12)]))


def _momento(p, color):
    """Momento: el diagrama parabólico de una viga con carga repartida."""
    p.drawLine(QPointF(3, 7), QPointF(21, 7))
    camino = QPainterPath(QPointF(3, 7))
    camino.quadTo(QPointF(12, 27), QPointF(21, 7))
    p.drawPath(camino)


def _torsion(p, color):
    """Torsión: una barra con una flecha que gira a su alrededor."""
    p.drawLine(QPointF(2, 12), QPointF(22, 12))
    p.drawArc(QRectF(7, 5, 10, 14), 30 * 16, 300 * 16)
    _punta(p, 16.3, 8.4, 0.5, 1, 2.6)


def _cerrar(p, color):
    """Una x: cerrar un panel."""
    p.drawLine(QPointF(6, 6), QPointF(18, 18))
    p.drawLine(QPointF(18, 6), QPointF(6, 18))


def _deshacer(p, color):
    """Flecha curva hacia la izquierda."""
    camino = QPainterPath(QPointF(19.5, 18))
    camino.cubicTo(QPointF(19.5, 9), QPointF(12, 8.5), QPointF(5, 9))
    p.drawPath(camino)
    p.drawPolyline(_poligono([(8.8, 5.2), (5, 9), (8.8, 12.8)]))


def _rehacer(p, color):
    """La misma flecha, hacia la derecha."""
    p.translate(24, 0)
    p.scale(-1, 1)
    _deshacer(p, color)


def _seccion_real(p, color):
    """Una barra con volumen (prisma): dibujar las barras con su sección."""
    p.drawRect(QRectF(3.5, 11, 6.5, 8))                                  # cara de la sección
    p.drawPolyline(_poligono([(3.5, 11), (14, 4.5), (20.5, 4.5), (10, 11)]))   # cara de arriba
    p.drawPolyline(_poligono([(20.5, 4.5), (20.5, 12.5), (10, 19)]))          # cara del costado


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


# ---------------------------------------------------------------- Íconos del Explorador (sin "+")
# Las filas y los grupos del árbol: lo que ES cada cosa, no una acción (por eso sin el "+" de agregar).
def _nodo_simple(p, color):
    """Un nodo: el punto con dos barras cortas que llegan a él."""
    p.drawLine(QPointF(3, 12), QPointF(12, 12))
    p.drawLine(QPointF(12, 12), QPointF(12, 21))
    _punto(p, color, (12, 12), 3.2)


def _barra_simple(p, color):
    """Un elemento: la barra con sus dos nodos."""
    p.drawLine(QPointF(4.5, 19.5), QPointF(19.5, 4.5))
    _punto(p, color, (4.5, 19.5), 2.4)
    _punto(p, color, (19.5, 4.5), 2.4)


def _carga_nodo_simple(p, color):
    """Una carga en un nodo: la flecha que llega al punto."""
    _punto(p, color, (12, 18), 2.6)
    p.drawLine(QPointF(12, 3.5), QPointF(12, 14.5))
    _punta(p, 12, 14.5, 0, 1, 3.0)


def _losa_simple(p, color):
    """Una losa de viguetas: la losa en corte con sus nervios."""
    p.drawRect(QRectF(2.5, 7, 19, 3.5))
    for x in (4.5, 11, 17.5):
        p.drawPolyline(_poligono([(x, 10.5), (x, 18), (x + 2, 18), (x + 2, 10.5)]))


def _pano(p, color):
    """Un paño: el rectángulo en planta entre dos vigas (las gruesas) y las viguetas que lo cruzan."""
    p.drawRect(QRectF(4, 4, 16, 16))
    grueso = QPen(p.pen())
    grueso.setWidthF(p.pen().widthF() * 2)
    fino = p.pen()
    p.setPen(grueso)
    p.drawLine(QPointF(4, 4), QPointF(4, 20))
    p.drawLine(QPointF(20, 4), QPointF(20, 20))
    p.setPen(fino)
    for y in (8, 12, 16):
        p.drawLine(QPointF(4, y), QPointF(20, y))


def _franja(p, color):
    """Una franja (sistema de vigueta): la vigueta continua sobre sus apoyos."""
    p.drawLine(QPointF(2.5, 11), QPointF(21.5, 11))
    for x in (3.5, 12, 20.5):
        p.drawPolygon(_poligono([(x, 11), (x - 2.6, 16), (x + 2.6, 16)]))


def _caso_viva(p, color):
    """Un caso de viva: flechas solo sobre algunos claros de la vigueta."""
    p.drawLine(QPointF(2.5, 18), QPointF(21.5, 18))
    for x in (2.5, 12, 21.5):
        _punto(p, color, (x, 18), 1.3)
    p.drawLine(QPointF(3.5, 6), QPointF(11, 6))
    for x in (4.5, 10):
        p.drawLine(QPointF(x, 6), QPointF(x, 14.5))
        _punta(p, x, 14.5, 0, 1, 2.4)


def _material_simple(p, color):
    """Un material (concreto): el bloque."""
    p.drawPolygon(_poligono([(4, 9), (12, 5), (20, 9), (12, 13)]))
    p.drawPolyline(_poligono([(4, 9), (4, 16), (12, 20), (20, 16), (20, 9)]))
    p.drawLine(QPointF(12, 13), QPointF(12, 20))


def _acero(p, color):
    """Acero de refuerzo: una barra corrugada (dos líneas con las corrugas entre ellas)."""
    p.drawLine(QPointF(3, 9.5), QPointF(21, 9.5))
    p.drawLine(QPointF(3, 14.5), QPointF(21, 14.5))
    for x in range(5, 21, 3):
        p.drawLine(QPointF(x, 14.5), QPointF(x + 2, 9.5))


def _seccion_rectangular(p, color):
    """Una sección rectangular de concreto con sus barras en las esquinas."""
    p.drawRect(QRectF(6, 3, 12, 18))
    for x, y in ((8.6, 5.6), (15.4, 5.6), (8.6, 18.4), (15.4, 18.4)):
        _punto(p, color, (x, y), 1.2)


def _seccion_t(p, color):
    """Una sección T (viga o vigueta con su losa) con su barra abajo."""
    p.drawPolygon(_poligono([(2.5, 4), (21.5, 4), (21.5, 9), (14.5, 9), (14.5, 20.5), (9.5, 20.5), (9.5, 9),
                             (2.5, 9)]))
    _punto(p, color, (12, 17.5), 1.3)


def _matriz(p, color):
    """Una matriz: los corchetes con sus términos."""
    p.drawPolyline(_poligono([(7, 4), (4, 4), (4, 20), (7, 20)]))
    p.drawPolyline(_poligono([(17, 4), (20, 4), (20, 20), (17, 20)]))
    for x in (8.5, 12, 15.5):
        for y in (8, 12, 16):
            _punto(p, color, (x, y), 0.9)


def _interaccion(p, color):
    """Un diagrama de interacción: los ejes M y P y la curva."""
    p.drawLine(QPointF(4, 21), QPointF(4, 3))
    p.drawLine(QPointF(4, 12), QPointF(21, 12))
    camino = QPainterPath(QPointF(4, 3.5))
    camino.cubicTo(QPointF(13, 4.5), QPointF(19, 9), QPointF(17, 14))
    camino.cubicTo(QPointF(15, 18), QPointF(9, 20.5), QPointF(4, 20.5))
    p.drawPath(camino)


_DIBUJOS = {
    "seleccionar": _seleccionar,
    "nodo": _nodo,
    "elemento": _elemento,
    "apoyo": _apoyo,
    "apoyo_fijo": _apoyo_fijo,
    "empotrado": _empotrado,
    "libre": _libre,
    "cerrar": _cerrar,
    "carga_nodo": _carga_nodo,
    "carga_barra": _carga_barra,
    "carga_uniforme": _carga_uniforme,
    "carga_trapezoidal": _carga_trapezoidal,
    "carga_puntual": _carga_puntual,
    "carga_momento": _carga_momento,
    "analizar": _analizar,
    "deformada": _deformada,
    "axial": _axial,
    "cortante": _cortante,
    "momento": _momento,
    "torsion": _torsion,
    "deshacer": _deshacer,
    "rehacer": _rehacer,
    "seccion_real": _seccion_real,
    "material": _material,
    "seccion": _seccion,
    "asignar_seccion": _asignar_seccion,
    "cargas": _cargas,
    "reacciones": _reacciones,
    "combinaciones": _combinaciones,
    "losa": _losa,
    "medir": _medir,
    "rejilla": _rejilla,
    "snap": _snap,
    "etiqueta": _etiqueta,
    "encuadre": _encuadre,
    # Explorador (sin "+")
    "nodo_simple": _nodo_simple,
    "barra_simple": _barra_simple,
    "carga_nodo_simple": _carga_nodo_simple,
    "losa_simple": _losa_simple,
    "pano": _pano,
    "franja": _franja,
    "caso_viva": _caso_viva,
    "material_simple": _material_simple,
    "acero": _acero,
    "seccion_rectangular": _seccion_rectangular,
    "seccion_t": _seccion_t,
    "matriz": _matriz,
    "interaccion": _interaccion,
}


def icono(nombre):
    """QIcon vectorial por su nombre (las claves de _DIBUJOS: "seleccionar", "nodo", "elemento",
    "asignar_seccion", "cargas", "combinaciones"...)."""
    return QIcon(IconoVectorial(_DIBUJOS[nombre]))
