"""Panel de Propiedades (derecha): los datos de lo seleccionado, en unidades de pantalla.

Por ahora es de solo lectura. Muestra un nodo, una barra o una sección; para las secciones de
concreto, además, los botones Ver 2D y Ver 3D del diagrama de interacción.
"""
import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QDockWidget, QHBoxLayout, QLabel, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from calculo.elemento import angulos
from configuracion import formato
from configuracion.formato import FUERZAS, GDL
from interfaz import concreto as puente


def describir_apoyo(apoyo):
    """'empotrado', 'articulado', 'libre' o la lista de GDL restringidos."""
    if all(apoyo):
        return "empotrado"
    if apoyo == [True, True, True, False, False, False]:
        return "articulado"
    if not any(apoyo):
        return "libre"
    return ", ".join(g for g, r in zip(GDL, apoyo) if r)


class Propiedades(QDockWidget):
    ver_diagrama = Signal(int, str)            # ID de la sección y "2D" o "3D"

    def __init__(self, parent=None):
        super().__init__("Propiedades", parent)
        self.setObjectName("propiedades")
        contenido = QWidget()
        diseno = QVBoxLayout(contenido)
        self.titulo = QLabel("Nada seleccionado")
        self.arbol = QTreeWidget()
        self.arbol.setColumnCount(2)
        self.arbol.setHeaderLabels(["Propiedad", "Valor"])
        self.botones = QWidget()
        fila = QHBoxLayout(self.botones)
        fila.setContentsMargins(0, 0, 0, 0)
        for modo in ("2D", "3D"):
            boton = QPushButton(f"Ver {modo}")
            boton.setToolTip(f"Calcula y dibuja el diagrama de interacción {modo}")
            boton.clicked.connect(lambda *_, m=modo: self.ver_diagrama.emit(self._sid, m))
            fila.addWidget(boton)
        self.botones.hide()
        diseno.addWidget(self.titulo)
        diseno.addWidget(self.arbol, 1)
        diseno.addWidget(self.botones)
        self.setWidget(contenido)
        self._sid = None

    # ---------- Ayudas ----------
    def _grupo(self, nombre):
        item = QTreeWidgetItem(self.arbol, [nombre])
        item.setExpanded(True)
        return item

    @staticmethod
    def _fila(padre, nombre, valor):
        QTreeWidgetItem(padre, [nombre, valor])

    # ---------- Mostrar ----------
    def mostrar(self, modelo, item):
        """item: ("nodo", id), ("barra", id), ("seccion", id) o None."""
        self.arbol.clear()
        self.botones.hide()
        self._sid = None
        tipo, ident = item if item else (None, None)
        if tipo == "nodo" and ident in modelo.nodos:
            self._nodo(modelo, ident)
        elif tipo == "barra" and ident in modelo.elementos:
            self._barra(modelo, ident)
        elif tipo == "seccion" and ident in modelo.secciones:
            self._seccion(modelo, ident)
        else:
            self.titulo.setText("Nada seleccionado")
        self.arbol.resizeColumnToContents(0)

    def _nodo(self, modelo, nid):
        n = modelo.nodos[nid]
        self.titulo.setText(f"Nodo {nid}")
        g = self._grupo("Posición")
        for eje, valor in zip("XYZ", n.coords):
            self._fila(g, eje, formato.cantidad(valor, "longitud"))
        self._fila(self._grupo("Apoyo"), "Restricción", describir_apoyo(n.apoyo))
        if any(n.carga):
            g = self._grupo("Cargas")
            for nombre, valor in zip(FUERZAS, n.carga):
                if valor:
                    self._fila(g, nombre, formato.cantidad(valor, "fuerza" if nombre[0] == "F" else "momento"))
        barras = modelo.elementos_conectados(nid)
        self._fila(self._grupo("Conexiones"), "Barras", ", ".join(map(str, barras)) or "ninguna")

    def _barra(self, modelo, eid):
        el = modelo.elementos[eid]
        ni, nj = modelo.nodos[el.ni], modelo.nodos[el.nj]
        self.titulo.setText(f"Elemento {eid}")
        beta, gamma, largo = angulos(ni.coords, nj.coords)
        g = self._grupo("Geometría")
        self._fila(g, "Nodos", f"{el.ni} → {el.nj}")
        self._fila(g, "Longitud", formato.cantidad(largo, "longitud"))
        self._fila(g, "α (giro de la sección)", f"{el.alfa:g}°")
        self._fila(g, "β", f"{np.degrees(beta):.2f}°")
        self._fila(g, "γ", f"{np.degrees(gamma):.2f}°")
        g = self._grupo("Material")
        if el.material is None:
            self._fila(g, "Material", "sin asignar")
        else:
            mat = modelo.materiales[el.material]
            self._fila(g, "Nombre", mat.nombre)
            self._fila(g, "E", formato.cantidad(mat.e, "esfuerzo"))
            self._fila(g, "G", formato.cantidad(mat.g, "esfuerzo"))
        g = self._grupo("Sección")
        if el.seccion is None:
            self._fila(g, "Sección", "sin asignar")
        else:
            self._datos_seccion(g, modelo.secciones[el.seccion])

    def _datos_seccion(self, g, sec):
        self._fila(g, "Nombre", sec.nombre)
        self._fila(g, "A", formato.cantidad(sec.a, "area"))
        for nombre in ("iy", "iz", "j"):
            self._fila(g, nombre.capitalize() if nombre != "j" else "J", formato.cantidad(getattr(sec, nombre), "inercia"))

    def _seccion(self, modelo, sid):
        sec = modelo.secciones[sid]
        self.titulo.setText(f"Sección {sid} — {sec.nombre}")
        self._datos_seccion(self._grupo("Propiedades"), sec)
        c = sec.concreto
        if c is None:
            return
        g = self._grupo("Concreto y refuerzo")
        if c.forma == "circular":
            self._fila(g, "Forma", "circular")
            self._fila(g, "D", formato.cantidad(c.D, "longitud"))
        else:
            self._fila(g, "Forma", "rectangular")
            self._fila(g, "b × h", f"{formato.cantidad(c.b, 'longitud', False)} × {formato.cantidad(c.h, 'longitud')}")
        self._fila(g, "d (al centro de las barras)", formato.cantidad(c.d, "longitud"))
        self._fila(g, "f'c", formato.cantidad(c.fc, "esfuerzo"))
        try:
            p = puente.propiedades(c)
        except ValueError as e:
            self._fila(g, "Datos inválidos", str(e))
            return
        self._fila(g, "Barras", f"{p['nbarras']} #{c.barra}")
        self._fila(g, "As", formato.cantidad(p["As_total"].to("m^2").magnitude, "area"))
        self._fila(g, "Cuantía ρ", f"{p['cuantia']:.2f} %")
        self._fila(g, "β1", f"{p['beta1']:.3f}")
        self._fila(g, "fy", formato.cantidad(p["fy"].to("kN/m^2").magnitude, "esfuerzo"))
        self._sid = sid
        self.botones.show()
