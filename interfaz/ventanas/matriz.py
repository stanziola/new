"""Tabla de la matriz de rigidez global de un elemento (12 x 12), en unidades de pantalla.

La matriz sale de calculo.rigidez.barra.k_global_barra (el mismo cálculo que usa el ensamble): aquí no
se repite ninguna fórmula, solo se convierte y se muestra.

Unidades por bloque (análisis dimensional). Cada término K[i, j] es "fuerza o momento en i por
desplazamiento o giro unitario en j":
- traslación-traslación: fuerza / longitud (kN/m);
- traslación-giro y giro-traslación: fuerza (kN por radián, o kN·m por m);
- giro-giro: momento (kN·m por radián).
"""
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from calculo.rigidez.barra import k_global_barra
from configuracion import formato, unidades
from configuracion.formato import GDL_PANTALLA


def bloque(i, j):
    """Exponentes (fuerza, longitud) y magnitud de decimales del término K[i, j]."""
    fila_traslacion, columna_traslacion = i % 6 < 3, j % 6 < 3
    if fila_traslacion and columna_traslacion:
        return (1, -1), "fuerza"          # F/L
    if not fila_traslacion and not columna_traslacion:
        return (1, 1), "momento"          # F·L (por radián)
    return (1, 0), "fuerza"               # F


def matriz_elemento(modelo, eid):
    """K global 12 x 12 de la barra eid, en unidades internas."""
    el = modelo.elementos[eid]
    if el.material is None or el.seccion is None:
        raise ValueError(f"El elemento {eid} no tiene material o sección asignados")
    mat, sec = modelo.materiales[el.material], modelo.secciones[el.seccion]
    ni, nj = modelo.nodos[el.ni], modelo.nodos[el.nj]
    return k_global_barra(mat.e, mat.g, sec.a, sec.iy, sec.iz, sec.j, ni.coords, nj.coords,
                          np.radians(el.alfa))


class VentanaMatriz(QWidget):
    """Una sola ventana, reutilizable: muestra la matriz del elemento que se elija."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.resize(1150, 520)
        self.titulo = QLabel()
        self.nota = QLabel()
        self.nota.setWordWrap(True)
        self.tabla = QTableWidget(12, 12)
        copiar = QPushButton("Copiar")
        copiar.setToolTip("Copia la tabla para pegarla en Excel")
        copiar.clicked.connect(self.copiar)
        abajo = QHBoxLayout()
        abajo.addWidget(self.nota, 1)
        abajo.addWidget(copiar)
        diseno = QVBoxLayout(self)
        diseno.addWidget(self.titulo)
        diseno.addWidget(self.tabla, 1)
        diseno.addLayout(abajo)
        self._modelo = self._eid = None

    def mostrar(self, modelo, eid):
        self._modelo, self._eid = modelo, eid
        self.refrescar()
        self.show()
        self.raise_()

    def refrescar(self, modelo=None):
        """Vuelve a calcular y mostrar (por ejemplo, después de cambiar las unidades o el modelo)."""
        if modelo is not None:
            self._modelo = modelo
        if self._eid is None or self._modelo is None or self._eid not in self._modelo.elementos:
            self.close()
            return
        el = self._modelo.elementos[self._eid]
        texto = f"Matriz de rigidez global — Elemento {self._eid} (nodos {el.ni} → {el.nj})"
        self.setWindowTitle(texto)
        self.titulo.setText(texto)
        try:
            K = matriz_elemento(self._modelo, self._eid)
        except ValueError as e:
            self.tabla.clearContents()
            self.nota.setText(str(e))
            return
        etiquetas = [f"{g}{n}" for n in (el.ni, el.nj) for g in GDL_PANTALLA]
        self.tabla.setHorizontalHeaderLabels(etiquetas)
        self.tabla.setVerticalHeaderLabels(etiquetas)
        for i in range(12):
            for j in range(12):
                (a, b), magnitud = bloque(i, j)
                factor, _ = unidades.compuesta(a, b)
                celda = QTableWidgetItem(formato.numero(K[i, j] / factor, formato.decimales(magnitud)))
                celda.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                celda.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.tabla.setItem(i, j, celda)
        self.tabla.resizeColumnsToContents()
        tt, tr, rr = (unidades.compuesta(*e)[1] for e in ((1, -1), (1, 0), (1, 1)))
        self.nota.setText(f"Unidades: traslación–traslación en {tt}; traslación–giro y giro–traslación "
                          f"en {tr}; giro–giro en {rr} (por radián).")

    def copiar(self):
        """Copia la tabla (con encabezados) separada por tabuladores, lista para pegar en Excel."""
        filas = ["\t" + "\t".join(self.tabla.horizontalHeaderItem(j).text() for j in range(12))]
        for i in range(12):
            celdas = [self.tabla.item(i, j).text() if self.tabla.item(i, j) else "" for j in range(12)]
            filas.append(self.tabla.verticalHeaderItem(i).text() + "\t" + "\t".join(celdas))
        QApplication.clipboard().setText("\n".join(filas))
