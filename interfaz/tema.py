"""Tema de la interfaz: solo blanco, negro y grises.

El estilo nativo de Windows 11 pinta en azul (su color de acento, #0067c0) el botón activo, el foco
y las selecciones, aunque nuestros colores sean grises. Con el estilo Fusion, en cambio, manda la
paleta de colores de la aplicación: basta con dársela en grises. La hoja de estilo agrega el
sombreado de los botones (al pasar el mouse, activo y presionado).
"""
from PySide6.QtGui import QColor, QPalette

from interfaz import estilo as es


def _paleta():
    pal = QPalette()
    colores = {
        QPalette.Window: es.INTERFAZ_FONDO,
        QPalette.WindowText: es.INTERFAZ_TEXTO,
        QPalette.Base: es.INTERFAZ_FONDO,
        QPalette.AlternateBase: es.INTERFAZ_HOVER,
        QPalette.Text: es.INTERFAZ_TEXTO,
        QPalette.PlaceholderText: es.INTERFAZ_DESHABILITADO,
        QPalette.Button: es.INTERFAZ_FONDO,
        QPalette.ButtonText: es.INTERFAZ_TEXTO,
        QPalette.BrightText: es.INTERFAZ_FONDO,
        QPalette.ToolTipBase: es.INTERFAZ_FONDO,
        QPalette.ToolTipText: es.INTERFAZ_TEXTO,
        QPalette.Highlight: es.INTERFAZ_ACTIVO,          # selecciones: gris claro, no azul
        QPalette.HighlightedText: es.INTERFAZ_TEXTO,
        QPalette.Accent: es.INTERFAZ_ACTIVO_BORDE,       # acento: gris, no azul
        QPalette.Link: es.INTERFAZ_TEXTO,
        QPalette.LinkVisited: es.INTERFAZ_TEXTO,
        QPalette.Light: es.INTERFAZ_FONDO,               # tonos que Fusion usa para relieves
        QPalette.Midlight: es.INTERFAZ_HOVER,
        QPalette.Mid: es.INTERFAZ_PRESIONADO,
        QPalette.Dark: es.INTERFAZ_ACTIVO_BORDE,
        QPalette.Shadow: es.INTERFAZ_DESHABILITADO,
    }
    for rol, color in colores.items():
        pal.setColor(rol, QColor(color))
    for rol in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, rol, QColor(es.INTERFAZ_DESHABILITADO))
    return pal


def _hoja_de_estilo():
    return f"""
        QToolBar {{ background: {es.INTERFAZ_FONDO}; border: none; spacing: 2px; padding: 3px; }}
        QToolBar#herramientas {{ border-right: 1px solid {es.INTERFAZ_BORDE}; }}
        QToolBar::separator:horizontal {{ background: {es.INTERFAZ_BORDE}; width: 1px; margin: 3px 5px; }}
        QToolBar::separator:vertical {{ background: {es.INTERFAZ_BORDE}; height: 1px; margin: 5px 3px; }}
        QToolButton {{ background: transparent; border: 1px solid transparent;
                       border-radius: 4px; padding: 3px; }}
        QToolButton:hover {{ background: {es.INTERFAZ_HOVER}; }}
        QToolButton:checked {{ background: {es.INTERFAZ_ACTIVO}; border-color: {es.INTERFAZ_ACTIVO_BORDE}; }}
        QToolButton:pressed {{ background: {es.INTERFAZ_PRESIONADO}; }}
        QToolButton:disabled {{ background: transparent; border-color: transparent; }}
        QStatusBar {{ background: {es.INTERFAZ_FONDO}; color: {es.INTERFAZ_TEXTO};
                      border-top: 1px solid {es.INTERFAZ_BORDE}; }}
        QStatusBar::item {{ border: none; }}
        QToolTip {{ background: {es.INTERFAZ_FONDO}; color: {es.INTERFAZ_TEXTO};
                    border: 1px solid {es.INTERFAZ_ACTIVO_BORDE}; padding: 3px; }}
    """


def aplicar_tema(app):
    """Pone el tema en blanco y negro a toda la aplicación (llamar recién creada la QApplication)."""
    app.setStyle("Fusion")
    app.setPalette(_paleta())
    app.setStyleSheet(_hoja_de_estilo())
