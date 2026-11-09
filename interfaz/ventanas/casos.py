"""Definir → Casos de carga y Definir → Combinaciones de carga: dos ventanas con una tabla.

- Casos: nombre, tipo (las letras de ASCE 7-05 §2.3.2: D, L, Lr...) y el factor del peso propio
  (normalmente 1 en Muerta y 0 en los demás). Las cargas se ponen en el caso activo con las
  herramientas de carga.
- Combinaciones: nombre y un factor por caso (vacío = 0). Solo sirven para VER resultados (dibujo y
  diagramas): su resultado es la suma de los casos por sus factores (superposición), así que
  cambiarlas no obliga a volver a analizar. El generador del ASCE 7-05 y las envolventes son la
  etapa 3 completa.
Los cambios se aplican con Aceptar, todos juntos, en un solo paso de Deshacer. Primero se prueban
en una copia del modelo: si algo no sirve, se avisa y el modelo no se toca.
"""
import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from modelo.estructura import TIPOS_CASO

ID = Qt.UserRole                      # el ID del caso o la combinación de cada fila (None = nueva)


def _numero(texto, nombre):
    """El número escrito en una celda (acepta coma decimal). Vacío = 0."""
    texto = texto.strip().replace(",", ".")
    if not texto:
        return 0.0
    try:
        return float(texto)
    except ValueError:
        raise ValueError(f"{nombre}: «{texto}» no es un número") from None


def _texto(numero):
    return "" if numero == 0 else f"{numero:g}"


class _DialogoTabla(QDialog):
    """Base: una tabla, Nuevo y Eliminar a la izquierda; Cancelar y Aceptar a la derecha."""
    TITULO = ""
    NUEVO = "Nuevo"

    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.setWindowTitle(self.TITULO)
        self.resize(640, 380)
        self.tabla = QTableWidget()
        self.tabla.verticalHeader().hide()
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla.itemSelectionChanged.connect(self._actualizar_botones)
        self.nota = QLabel()
        self.nota.setWordWrap(True)
        nuevo = QPushButton(self.NUEVO)
        nuevo.clicked.connect(self._nueva_fila)
        self.eliminar = QPushButton("Eliminar")
        self.eliminar.clicked.connect(self._eliminar_fila)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        aceptar = QPushButton("Aceptar")
        aceptar.setDefault(True)
        aceptar.clicked.connect(self.accept)
        botones = QHBoxLayout()
        for b in (nuevo, self.eliminar):
            botones.addWidget(b)
        botones.addStretch(1)
        for b in (cancelar, aceptar):
            botones.addWidget(b)
        diseno = QVBoxLayout(self)
        diseno.addWidget(self.tabla, 1)
        diseno.addWidget(self.nota)
        diseno.addLayout(botones)
        self._borradas = []                    # IDs de las filas eliminadas (que ya existían)

    def _fila_actual(self):
        filas = self.tabla.selectionModel().selectedRows()
        return filas[0].row() if filas else None

    def _ident(self, fila):
        return self.tabla.item(fila, 0).data(ID)

    def _actualizar_botones(self):
        fila = self._fila_actual()
        motivo = self._no_se_puede_eliminar(fila) if fila is not None else "Elige una fila"
        self.eliminar.setEnabled(motivo is None)
        self.eliminar.setToolTip(motivo or "")

    def _no_se_puede_eliminar(self, fila):
        return None

    def _eliminar_fila(self):
        fila = self._fila_actual()
        if fila is None or self._no_se_puede_eliminar(fila) is not None:
            return
        ident = self._ident(fila)
        if ident is not None:
            self._borradas.append(ident)
        self.tabla.removeRow(fila)
        self._actualizar_botones()

    def accept(self):
        """Prueba los cambios en una copia; si sirven, los aplica en el modelo (un paso de Deshacer)."""
        try:
            self._aplicar(copy.deepcopy(self.ventana.modelo))
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, self.TITULO, str(e).strip("'\""))
            return
        self.ventana.antes_de_cambiar()
        texto = self._aplicar(self.ventana.modelo)
        super().accept()
        self._terminar(texto)


class DialogoCasos(_DialogoTabla):
    TITULO = "Casos de carga"
    NUEVO = "Nuevo caso"

    def __init__(self, ventana):
        super().__init__(ventana)
        modelo = ventana.modelo
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Nombre", "Tipo", "Peso propio ×"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for cid, caso in modelo.casos.items():
            self._agregar(cid, caso.nombre, caso.tipo, caso.peso_propio)
        self.nota.setText("Tipo: la letra de las combinaciones (ASCE 7-05 §2.3.2). El peso propio se suma "
                          "solo en los casos con factor distinto de 0 (normalmente, solo en Muerta). Un caso "
                          "con cargas o usado en una combinación no se puede eliminar.")
        self._actualizar_botones()

    def _agregar(self, cid, nombre, tipo, peso):
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)
        celda = QTableWidgetItem(nombre)
        celda.setData(ID, cid)
        self.tabla.setItem(fila, 0, celda)
        lista = QComboBox()
        for letra, propuesto in TIPOS_CASO.items():
            lista.addItem(f"{letra} ({propuesto.lower()})", letra)
        lista.setCurrentIndex(max(0, lista.findData(tipo)))
        self.tabla.setCellWidget(fila, 1, lista)
        self.tabla.setItem(fila, 2, QTableWidgetItem(f"{peso:g}"))

    def _nueva_fila(self):
        self._agregar(None, "", "L", 0.0)
        self.tabla.selectRow(self.tabla.rowCount() - 1)
        self.tabla.editItem(self.tabla.item(self.tabla.rowCount() - 1, 0))

    def _no_se_puede_eliminar(self, fila):
        cid = self._ident(fila)
        if self.tabla.rowCount() == 1:
            return "Tiene que quedar al menos un caso"
        if cid is None:
            return None
        cargas, combos = self.ventana.modelo.uso_caso(cid)
        if cargas or combos:
            return f"En uso: {len(cargas)} cargas y {len(combos)} combinaciones"
        return None

    def _filas(self):
        for fila in range(self.tabla.rowCount()):
            nombre = self.tabla.item(fila, 0).text()
            tipo = self.tabla.cellWidget(fila, 1).currentData()
            peso = _numero(self.tabla.item(fila, 2).text(), f"Fila {fila + 1}, peso propio")
            yield self._ident(fila), nombre, tipo, peso

    def _aplicar(self, modelo):
        for cid in self._borradas:
            modelo.eliminar_caso(cid)
        for cid, nombre, tipo, peso in list(self._filas()):
            if cid is None:
                modelo.agregar_caso(nombre, tipo, peso)
            else:
                modelo.cambiar_caso(cid, nombre, tipo, peso)
        return "Casos de carga actualizados"

    def _terminar(self, texto):
        self.ventana.modelo_cambiado(texto)                  # los casos cambian los resultados


class DialogoCombinaciones(_DialogoTabla):
    TITULO = "Combinaciones de carga"
    NUEVO = "Nueva combinación"

    def __init__(self, ventana):
        super().__init__(ventana)
        modelo = ventana.modelo
        self.casos = list(modelo.casos)
        self.tabla.setColumnCount(1 + len(self.casos))
        self.tabla.setHorizontalHeaderLabels(["Nombre"] + [f"{modelo.casos[c].nombre} ({modelo.casos[c].tipo})"
                                                           for c in self.casos])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for coid, co in modelo.combinaciones.items():
            automatico = co.nombre == modelo.nombre_combinacion(co.factores)
            self._agregar(coid, "" if automatico else co.nombre, co.factores)
        self.nota.setText("Un factor por caso (vacío = 0). Sin nombre, se arma solo: «1.2D + 1.6L». "
                          "Solo sirven para ver resultados (dibujo y diagramas), con Σ en la barra de arriba; "
                          "no hace falta volver a analizar. El viento del REP es de servicio: en las "
                          "combinaciones va 1.6W (REP 8.4; ACI 318-19 §5.3.5).")
        self._actualizar_botones()

    def _agregar(self, coid, nombre, factores):
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)
        celda = QTableWidgetItem(nombre)
        celda.setData(ID, coid)
        celda.setToolTip("Vacío: nombre automático")
        self.tabla.setItem(fila, 0, celda)
        for k, cid in enumerate(self.casos, start=1):
            valor = QTableWidgetItem(_texto(factores.get(cid, 0.0)))
            valor.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tabla.setItem(fila, k, valor)

    def _nueva_fila(self):
        self._agregar(None, "", {})
        fila = self.tabla.rowCount() - 1
        self.tabla.selectRow(fila)
        self.tabla.editItem(self.tabla.item(fila, 1))

    def _filas(self):
        for fila in range(self.tabla.rowCount()):
            factores = {cid: _numero(self.tabla.item(fila, k).text(), f"Fila {fila + 1}")
                        for k, cid in enumerate(self.casos, start=1)}
            yield self._ident(fila), self.tabla.item(fila, 0).text(), factores

    def _aplicar(self, modelo):
        for coid in self._borradas:
            modelo.eliminar_combinacion(coid)
        for coid, nombre, factores in list(self._filas()):
            if coid is None:
                modelo.agregar_combinacion(nombre, factores)
            else:
                modelo.cambiar_combinacion(coid, nombre, factores)
        return "Combinaciones actualizadas"

    def _terminar(self, texto):
        self.ventana.modelo_cambiado(texto, invalida=False)  # superposición: no hay que reanalizar
