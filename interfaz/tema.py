"""Tema de la interfaz: solo blanco, negro y grises.

El estilo nativo de Windows 11 pinta en azul (su color de acento, #0067c0) el botón activo, el foco
y las selecciones, aunque nuestros colores sean grises. Con el estilo Fusion, en cambio, manda la
paleta de colores de la aplicación: basta con dársela en grises. La hoja de estilo agrega el
sombreado de los botones (al pasar el mouse, activo y presionado) y el aspecto de los menús.
Los árboles (explorador y Propiedades) usan cuadritos "+" y "−" unidos por líneas punteadas, en vez
de flechas: los dibuja EstiloArbol, una capa sobre Fusion que solo cambia ese dibujo.
Se puede volver a llamar después de cambiar colores en Configuración.
"""
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPalette, QPen
from PySide6.QtWidgets import QProxyStyle, QStyle, QStyleFactory

from configuracion import colores as c
from configuracion import interfaz as ui

LADO_CUADRITO = 9                     # cuadrito del "+" y el "−", en píxeles


class EstiloArbol(QProxyStyle):
    """Fusion, pero las ramas de los árboles con "+"/"−" y líneas punteadas en vez de flechas."""

    def drawPrimitive(self, elemento, opcion, p, widget=None):
        if elemento != QStyle.PE_IndicatorBranch:
            super().drawPrimitive(elemento, opcion, p, widget)
            return
        r, estado = opcion.rect, opcion.state
        cx, cy = r.center().x(), r.center().y()
        p.save()
        p.setPen(QPen(QColor(c.INTERFAZ_ACTIVO_BORDE), 1, Qt.DotLine))
        if estado & QStyle.State_Sibling:          # la línea sigue hacia el hermano de abajo
            p.drawLine(cx, r.top(), cx, r.bottom())
        elif estado & QStyle.State_Item:           # último de su grupo: la línea termina aquí
            p.drawLine(cx, r.top(), cx, cy)
        if estado & QStyle.State_Item:             # tramo horizontal hacia el texto
            p.drawLine(cx, cy, r.right(), cy)
        if estado & QStyle.State_Children:         # tiene hijos: cuadrito con "+" o "−"
            m = LADO_CUADRITO // 2
            caja = QRect(cx - m, cy - m, LADO_CUADRITO - 1, LADO_CUADRITO - 1)
            p.setPen(QPen(QColor(c.INTERFAZ_DESHABILITADO), 1))
            p.setBrush(QColor(c.INTERFAZ_FONDO))
            p.drawRect(caja)
            p.setPen(QPen(QColor(c.INTERFAZ_TEXTO), 1))
            p.drawLine(QPoint(cx - m + 2, cy), QPoint(cx + m - 2, cy))
            if not estado & QStyle.State_Open:
                p.drawLine(QPoint(cx, cy - m + 2), QPoint(cx, cy + m - 2))
        p.restore()


def _paleta():
    pal = QPalette()
    tonos = {
        QPalette.Window: c.INTERFAZ_FONDO,
        QPalette.WindowText: c.INTERFAZ_TEXTO,
        QPalette.Base: c.INTERFAZ_FONDO,
        QPalette.AlternateBase: c.INTERFAZ_HOVER,
        QPalette.Text: c.INTERFAZ_TEXTO,
        QPalette.PlaceholderText: c.INTERFAZ_DESHABILITADO,
        QPalette.Button: c.INTERFAZ_FONDO,
        QPalette.ButtonText: c.INTERFAZ_TEXTO,
        QPalette.BrightText: c.INTERFAZ_FONDO,
        QPalette.ToolTipBase: c.INTERFAZ_FONDO,
        QPalette.ToolTipText: c.INTERFAZ_TEXTO,
        QPalette.Highlight: c.INTERFAZ_ACTIVO,          # selecciones: gris claro, no azul
        QPalette.HighlightedText: c.INTERFAZ_TEXTO,
        QPalette.Accent: c.INTERFAZ_ACTIVO_BORDE,       # acento: gris, no azul
        QPalette.Link: c.INTERFAZ_TEXTO,
        QPalette.LinkVisited: c.INTERFAZ_TEXTO,
        QPalette.Light: c.INTERFAZ_FONDO,               # tonos que Fusion usa para relieves
        QPalette.Midlight: c.INTERFAZ_HOVER,
        QPalette.Mid: c.INTERFAZ_PRESIONADO,
        QPalette.Dark: c.INTERFAZ_ACTIVO_BORDE,
        QPalette.Shadow: c.INTERFAZ_DESHABILITADO,
    }
    for rol, color in tonos.items():
        pal.setColor(rol, QColor(color))
    for rol in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, rol, QColor(c.INTERFAZ_DESHABILITADO))
    return pal


def _hoja_de_estilo():
    return f"""
        QToolBar {{ background: {c.INTERFAZ_FONDO}; border: none; spacing: 2px; padding: 3px; }}
        QToolBar#herramientas {{ border-right: 1px solid {c.INTERFAZ_BORDE}; }}
        QToolBar#definir {{ border-bottom: 1px solid {c.INTERFAZ_BORDE}; }}
        QDockWidget::title {{ background: {c.INTERFAZ_HOVER}; padding: 5px;
                             border-bottom: 1px solid {c.INTERFAZ_BORDE}; }}
        QTreeWidget {{ border: none; }}
        QTreeView::item {{ padding: 1px 0px; }}
        QTabWidget::pane {{ border: none; border-top: 1px solid {c.INTERFAZ_BORDE}; top: -1px; }}
        QTabBar::tab {{ background: transparent; border: 1px solid transparent; padding: 4px 12px;
                        margin: 0px; color: {c.INTERFAZ_TEXTO}; }}
        QTabBar::tab:selected {{ background: {c.INTERFAZ_FONDO}; border-color: {c.INTERFAZ_BORDE};
                                 border-bottom-color: {c.INTERFAZ_FONDO}; }}
        QMainWindow::separator {{ background: {c.INTERFAZ_ACTIVO_BORDE};
                                  width: {ui.ANCHO_SEPARADOR}px; height: {ui.ANCHO_SEPARADOR}px; }}
        QMainWindow::separator:hover {{ background: {c.INTERFAZ_DESHABILITADO}; }}
        QToolBar#barra_comandos {{ border-top: 1px solid {c.INTERFAZ_BORDE}; spacing: 8px; }}
        QToolBar::separator:horizontal {{ background: {c.INTERFAZ_BORDE}; width: 1px; margin: 3px 5px; }}
        QToolBar::separator:vertical {{ background: {c.INTERFAZ_BORDE}; height: 1px; margin: 5px 3px; }}
        QToolButton {{ background: transparent; border: 1px solid transparent;
                       border-radius: 4px; padding: 3px; }}
        QToolButton:hover {{ background: {c.INTERFAZ_HOVER}; }}
        QToolButton:checked {{ background: {c.INTERFAZ_ACTIVO}; border-color: {c.INTERFAZ_ACTIVO_BORDE}; }}
        QToolButton:pressed {{ background: {c.INTERFAZ_PRESIONADO}; }}
        QToolButton:disabled {{ background: transparent; border-color: transparent; }}
        QStatusBar {{ background: {c.INTERFAZ_FONDO}; color: {c.INTERFAZ_TEXTO};
                      border-top: 1px solid {c.INTERFAZ_BORDE}; }}
        QStatusBar::item {{ border: none; }}
        QMenuBar {{ background: {c.INTERFAZ_FONDO}; border-bottom: 1px solid {c.INTERFAZ_BORDE}; }}
        QMenuBar::item {{ background: transparent; padding: 4px 10px; }}
        QMenuBar::item:selected {{ background: {c.INTERFAZ_HOVER}; }}
        QMenuBar::item:pressed {{ background: {c.INTERFAZ_ACTIVO}; }}
        QMenu {{ background: {c.INTERFAZ_FONDO}; border: 1px solid {c.INTERFAZ_ACTIVO_BORDE}; padding: 3px; }}
        QMenu::item {{ padding: 4px 28px 4px 16px; }}
        QMenu::item:selected {{ background: {c.INTERFAZ_ACTIVO}; color: {c.INTERFAZ_TEXTO}; }}
        QMenu::item:disabled {{ color: {c.INTERFAZ_DESHABILITADO}; }}
        QMenu::separator {{ height: 1px; background: {c.INTERFAZ_BORDE}; margin: 4px 8px; }}
        QLineEdit {{ background: {c.INTERFAZ_FONDO}; border: 1px solid {c.INTERFAZ_ACTIVO_BORDE};
                     border-radius: 3px; padding: 2px 4px; selection-background-color: {c.INTERFAZ_ACTIVO};
                     selection-color: {c.INTERFAZ_TEXTO}; }}
        QLineEdit:focus {{ border-color: {c.INTERFAZ_TEXTO}; }}
        QToolTip {{ background: {c.INTERFAZ_FONDO}; color: {c.INTERFAZ_TEXTO};
                    border: 1px solid {c.INTERFAZ_ACTIVO_BORDE}; padding: 3px; }}
    """


def aplicar_tema(app):
    """Pone el tema en blanco y negro a toda la aplicación (y lo actualiza si cambian los colores)."""
    app.setStyle(EstiloArbol(QStyleFactory.create("Fusion")))
    app.setPalette(_paleta())
    app.setStyleSheet(_hoja_de_estilo())
