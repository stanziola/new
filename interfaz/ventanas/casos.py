"""Definir → Casos de carga y Definir → Combinaciones de carga: dos ventanas con una tabla.

- Casos: nombre y tipo (Muerta, Viva, Viento o Sismo). Los dos primeros son fijos (fondo gris, no se
  editan ni se eliminan): "Peso propio", que es automático (A·γ de cada viga y columna), y "Carga
  muerta adicional", donde van las cargas muertas puestas a mano. Las cargas se ponen en el caso
  activo con las herramientas de carga.
- Combinaciones: arriba, los datos del sismo, SDS y ρ (por ahora escritos a mano). En la tabla, un
  factor por TIPO de caso: D, L, W y E. Las predeterminadas (modelo/combinaciones.py: ASCE 7-05
  §2.3.2 y §12.4.2.3) van con fondo gris y no se editan: salen de la norma, con el SDS y el ρ de
  arriba; al pasar el mouse dicen de qué cláusula vienen. Debajo, las propias del usuario.
  Solo sirven para VER resultados (dibujo y diagramas): su resultado es la suma de los casos por sus
  factores (superposición), así que cambiarlas no obliga a volver a analizar.
Los cambios se aplican con Aceptar, todos juntos, en un solo paso de Deshacer. Primero se prueban
en una copia del modelo: si algo no sirve, se avisa y el modelo no se toca; si no cambió nada, no
se hace nada (ni se pierde el análisis).
"""
import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from configuracion import colores
from interfaz.paneles.comunes import CampoNumero, Lista
from modelo import combinaciones as comb
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


def _fijo(texto, ayuda=""):
    """Celda que no se edita ni se elige, con fondo gris."""
    celda = QTableWidgetItem(texto)
    celda.setFlags(Qt.ItemIsEnabled)
    celda.setBackground(QBrush(QColor(colores.INTERFAZ_HOVER)))
    celda.setToolTip(ayuda)
    return celda


def _nombre_tipo(tipo):
    return f"{TIPOS_CASO.get(tipo, tipo)} ({tipo})"


class _DialogoTabla(QDialog):
    """Base: una tabla, Nuevo y Eliminar a la izquierda; Cancelar y Aceptar a la derecha."""
    TITULO = ""
    NUEVO = "Nuevo"

    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.setWindowTitle(self.TITULO)
        self.resize(640, 400)
        self.tabla = QTableWidget()
        self.tabla.verticalHeader().hide()
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla.itemSelectionChanged.connect(self._actualizar_botones)
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
            b.setAutoDefault(False)
            botones.addWidget(b)
        botones.addStretch(1)
        for b in (cancelar, aceptar):
            botones.addWidget(b)
        self.diseno = QVBoxLayout(self)
        self.diseno.addWidget(self.tabla, 1)
        self.diseno.addLayout(botones)
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
        """Prueba los cambios en una copia; si sirven y cambian algo, los aplica en el modelo (un
        paso de Deshacer)."""
        self.tabla.setCurrentItem(None)        # cierra la celda que se estuviera editando
        prueba = copy.deepcopy(self.ventana.modelo)
        try:
            self._aplicar(prueba)
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, self.TITULO, str(e).strip("'\""))
            return
        if self._igual(prueba, self.ventana.modelo):
            super().accept()                   # no cambió nada: ni paso de Deshacer ni aviso
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
        self.tabla.setColumnCount(2)
        self.tabla.setHorizontalHeaderLabels(["Nombre", "Tipo"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla.setColumnWidth(1, 170)
        for cid, caso in modelo.casos.items():
            if modelo.es_fijo(cid):
                self._agregar_fijo(cid, caso, modelo.es_automatico(cid))
            else:
                self._agregar(cid, caso.nombre, caso.tipo)
        self._actualizar_botones()

    def _agregar_fijo(self, cid, caso, automatico):
        ayuda = ("Automático: el peso de cada viga y columna (A·γ). No recibe cargas a mano" if automatico
                 else "Aquí van las cargas muertas que pones a mano. Con el peso propio forma la carga muerta (D)")
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)
        celda = _fijo(caso.nombre + (" (automático)" if automatico else ""), ayuda)
        celda.setData(ID, cid)
        self.tabla.setItem(fila, 0, celda)
        self.tabla.setItem(fila, 1, _fijo(_nombre_tipo(caso.tipo), ayuda))

    def _agregar(self, cid, nombre, tipo):
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)
        celda = QTableWidgetItem(nombre)
        celda.setData(ID, cid)
        celda.setToolTip("Vacío: el nombre de su tipo (Viva, Viento…)")
        self.tabla.setItem(fila, 0, celda)
        lista = Lista(estirar=True)                 # llena su celda de la tabla
        for t in self.ventana.modelo.tipos_de_caso():
            lista.addItem(_nombre_tipo(t), t)
        lista.setCurrentIndex(max(0, lista.findData(tipo)))
        self.tabla.setCellWidget(fila, 1, lista)

    def _nueva_fila(self):
        self._agregar(None, "", "L")
        fila = self.tabla.rowCount() - 1
        self.tabla.selectRow(fila)
        self.tabla.editItem(self.tabla.item(fila, 0))

    def _es_fija(self, fila):
        cid = self._ident(fila)
        return cid is not None and self.ventana.modelo.es_fijo(cid)

    def _no_se_puede_eliminar(self, fila):
        if self._es_fija(fila):
            return "Este caso es fijo: no se elimina"
        cid = self._ident(fila)
        cargas = self.ventana.modelo.uso_caso(cid) if cid is not None else []
        return f"Tiene {len(cargas)} cargas: bórralas primero" if cargas else None

    def _aplicar(self, modelo):
        for cid in self._borradas:
            modelo.eliminar_caso(cid)
        for fila in range(self.tabla.rowCount()):
            if self._es_fija(fila):
                continue
            cid, nombre = self._ident(fila), self.tabla.item(fila, 0).text()
            tipo = self.tabla.cellWidget(fila, 1).currentData()
            if cid is None:
                modelo.agregar_caso(nombre, tipo)
            else:
                modelo.cambiar_caso(cid, nombre, tipo)
        return "Casos de carga actualizados"

    @staticmethod
    def _igual(a, b):
        return list(a.casos.items()) == list(b.casos.items())

    def _terminar(self, texto):
        self.ventana.modelo_cambiado(texto)                  # los casos cambian los resultados


class DialogoCombinaciones(_DialogoTabla):
    TITULO = "Combinaciones de carga"
    NUEVO = "Nueva combinación"

    def __init__(self, ventana):
        super().__init__(ventana)
        self.resize(660, 560)
        modelo = ventana.modelo
        self.tipos = modelo.tipos_de_caso()

        # Datos del sismo, arriba de la tabla
        self.sds = CampoNumero(minimo=0.0, maximo=5.0, decimales=3)
        self.sds.poner(modelo.sds)
        self.sds.setToolTip("SDS: aceleración espectral de diseño para periodos cortos (ASCE 7-05 §11.4.4).\n"
                            "Entra en las combinaciones 5 y 7: (1.2 + 0.2·SDS)D y (0.9 − 0.2·SDS)D (§12.4.2.3).\n"
                            "Por ahora se escribe a mano; saldrá de la etapa de sismo.")
        self.rho = Lista()
        self.rho.addItem("1.3", 1.3)
        self.rho.addItem("1.0", 1.0)
        self.rho.setCurrentIndex(max(0, self.rho.findData(modelo.rho)))
        self.rho.setToolTip("ρ, factor de redundancia (ASCE 7-05 §12.3.4): 1.0 en las categorías de diseño\n"
                            "sísmico B y C; 1.3 en D, E y F, salvo que se cumpla una de las dos excepciones.")
        self.especial = QCheckBox("Pórtico especial (SMF)")
        self.especial.setChecked(modelo.portico_especial)
        self.especial.setToolTip("Pórticos especiales resistentes a momento (lo usual en Panamá, CDS D).\n"
                                 "Cambia la cuantía máxima de las columnas: 6 % en vez de 8 % "
                                 "(ACI 318-19 §18.7.4.1 y §10.6.1.1).")
        arriba = QHBoxLayout()
        etiqueta_sds, etiqueta_rho = QLabel("SDS"), QLabel("ρ")
        etiqueta_sds.setToolTip(self.sds.toolTip())
        etiqueta_rho.setToolTip(self.rho.toolTip())
        for w in (etiqueta_sds, self.sds, etiqueta_rho, self.rho, self.especial):
            arriba.addWidget(w)
        arriba.addStretch(1)
        self.diseno.insertLayout(0, arriba)

        self.tabla.setColumnCount(1 + len(self.tipos))
        self.tabla.setHorizontalHeaderLabels(["Nombre"] + self.tipos)
        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.Stretch)
        for k, tipo in enumerate(self.tipos, start=1):
            self.tabla.horizontalHeaderItem(k).setToolTip(f"Factor de todos los casos tipo {_nombre_tipo(tipo)}")
            self.tabla.setColumnWidth(k, 70)
        self.claves = list(comb.predeterminadas(modelo.sds, modelo.rho))     # filas fijas, arriba
        for _ in self.claves:
            self.tabla.insertRow(self.tabla.rowCount())
        self._poner_predeterminadas()
        for coid, co in modelo.combinaciones.items():
            self._agregar(coid, co.nombre, co.factores)
        self.sds.cambiado.connect(self._poner_predeterminadas)
        self.rho.currentIndexChanged.connect(self._poner_predeterminadas)
        self._actualizar_botones()

    def _poner_predeterminadas(self, *_):
        """Las filas de la norma, con el SDS y el ρ que están escritos arriba."""
        combos = comb.predeterminadas(self.sds.valor(), self.rho.currentData())
        for fila, clave in enumerate(self.claves):
            co, ayuda = combos[clave], comb.referencia(clave)
            self.tabla.setItem(fila, 0, _fijo(co.nombre, ayuda))
            for k, tipo in enumerate(self.tipos, start=1):
                celda = _fijo(_texto(co.factores.get(tipo, 0.0)), ayuda)
                celda.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla.setItem(fila, k, celda)

    def _agregar(self, coid, nombre, factores):
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)
        celda = QTableWidgetItem(nombre)
        celda.setData(ID, coid)
        celda.setToolTip("Vacío: nombre automático, como «1.2D + 1.6L»")
        self.tabla.setItem(fila, 0, celda)
        for k, tipo in enumerate(self.tipos, start=1):
            valor = QTableWidgetItem(_texto(factores.get(tipo, 0.0)))
            valor.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tabla.setItem(fila, k, valor)

    def _nueva_fila(self):
        self._agregar(None, "", {})
        fila = self.tabla.rowCount() - 1
        self.tabla.selectRow(fila)
        self.tabla.scrollToBottom()
        self.tabla.editItem(self.tabla.item(fila, 1))

    def _no_se_puede_eliminar(self, fila):
        return "Las predeterminadas no se eliminan" if fila < len(self.claves) else None

    def _aplicar(self, modelo):
        modelo.poner_sismo(self.sds.valor(), self.rho.currentData(), self.especial.isChecked())
        for coid in self._borradas:
            modelo.eliminar_combinacion(coid)
        for fila in range(len(self.claves), self.tabla.rowCount()):
            nombre = self.tabla.item(fila, 0).text()
            factores = {tipo: _numero(self.tabla.item(fila, k).text(), f"Fila {fila + 1}")
                        for k, tipo in enumerate(self.tipos, start=1)}
            coid = self._ident(fila)
            if coid is None:
                modelo.agregar_combinacion(nombre, factores)
            else:
                # el nombre automático sigue a los factores: si no lo cambió a mano, se rearma
                automatico = nombre == modelo.combinaciones[coid].nombre == \
                    comb.nombre_combinacion(modelo.combinaciones[coid].factores)
                modelo.cambiar_combinacion(coid, "" if automatico else nombre, factores)
        return "Combinaciones actualizadas"

    @staticmethod
    def _igual(a, b):
        return ((a.combinaciones, a.sds, a.rho, a.portico_especial)
                == (b.combinaciones, b.sds, b.rho, b.portico_especial))

    def _terminar(self, texto):
        self.ventana.modelo_cambiado(texto, invalida=False)  # superposición: no hay que reanalizar
