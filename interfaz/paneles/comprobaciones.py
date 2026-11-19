"""Pestaña Comprobaciones (Propiedades): el diseño de la vigueta de una losa.

- Arriba, lo que manda: Mu+ máximo, Mu− y Vu máximos en la cara de los apoyos, Ma (D + L) y las
  deflexiones, cada uno con la franja, el claro o apoyo, el caso de viva y la combinación de donde sale
  (modelo/diseno_vigueta.disenar_losa, sobre TODAS las franjas y sus casos de viva).
- Debajo, la lista de comprobaciones por grupo, cada una con su valor contra el límite y la cláusula
  del ACI 318-19 (página del PDF): en verde las que cumplen, en rojo las que no y en gris las
  informativas o no evaluadas (colores.CUMPLE y NO_CUMPLE: la excepción de color de la interfaz,
  como el aviso rojo de Interacción). El detalle sale al pasar el mouse.
- Abajo, la vigueta editable (alma, altura, losa, recubrimiento, estribos y barras): Aplicar cambia la
  vigueta de TODA la losa (un paso de Deshacer); bf no se escribe: sale de la separación s.
El cálculo lo pide la ventana cuando la pestaña está a la vista (tarda menos de un segundo).
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QFormLayout, QGroupBox, QHeaderView, QLabel, QPushButton,
                               QScrollArea, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from configuracion import colores, formato
from interfaz.paneles.comunes import CampoNumero
from interfaz.paneles.formularios import campo_seccion, lista_barras


def _texto(valor, magnitud):
    if valor is None:
        return "—"
    if magnitud:
        return formato.cantidad(valor, magnitud)
    return f"{valor:.4f}"


class PestanaComprobaciones(QWidget):
    vigueta_editada = Signal(int, object)        # (ID de losa, datos de la T)

    def __init__(self, parent=None):
        super().__init__(parent)
        contenido = QWidget()
        diseno = QVBoxLayout(contenido)
        self.titulo = QLabel()
        self.titulo.setWordWrap(True)
        self.resumen = QLabel()
        self.resumen.setTextFormat(Qt.RichText)
        self.resumen.setWordWrap(True)
        self.arbol = QTreeWidget()
        self.arbol.setColumnCount(3)
        self.arbol.setHeaderLabels(["Comprobación", "Valor", "Límite"])
        self.arbol.setIndentation(12)
        self.arbol.setSelectionMode(QAbstractItemView.NoSelection)
        self.arbol.setFocusPolicy(Qt.NoFocus)
        self.arbol.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.arbol.setTextElideMode(Qt.ElideRight)
        cabecera = self.arbol.header()
        cabecera.setStretchLastSection(False)
        cabecera.setSectionResizeMode(0, QHeaderView.Stretch)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.arbol.setMinimumHeight(260)

        caja = QGroupBox("Vigueta de la losa (cambia la de todos sus paños)")
        forma = QFormLayout(caja)
        self.bw, self.h, self.hf = campo_seccion(), campo_seccion(), campo_seccion()
        self.rec = campo_seccion(0.005, 0.5)
        self.estribo = lista_barras("Sin estribos")
        self.s_estribo = campo_seccion(0.01, 2.0)
        self.barra, self.barra_sup = lista_barras(), lista_barras()
        self.n = CampoNumero(minimo=1, maximo=30, entero=True)
        self.n_sup = CampoNumero(minimo=0, maximo=30, entero=True)
        for nombre, control in (("bw (alma)", self.bw), ("h (total)", self.h), ("hf (losa)", self.hf),
                                ("Recubrimiento libre", self.rec), ("Estribo", self.estribo),
                                ("Separación de estribos", self.s_estribo), ("Barra abajo", self.barra),
                                ("Barras abajo", self.n), ("Barra arriba", self.barra_sup),
                                ("Barras arriba", self.n_sup)):
            forma.addRow(nombre, control)
        self.estribo.currentIndexChanged.connect(lambda *_: self.s_estribo.setEnabled(bool(self.estribo.currentData())))
        self.aplicar = QPushButton("Aplicar")
        self.aplicar.setToolTip("Cambia la vigueta de toda la losa (bf sale de la separación) y vuelve a revisar")
        self.aplicar.clicked.connect(self._aplicar)
        forma.addRow(self.aplicar)
        self.caja = caja

        for w in (self.titulo, self.resumen):
            diseno.addWidget(w)
        diseno.addWidget(self.arbol, 1)
        diseno.addWidget(caja)
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setWidget(contenido)
        fuera = QVBoxLayout(self)
        fuera.setContentsMargins(0, 0, 0, 0)
        fuera.addWidget(desplazable)
        self._losa = None

    # ---------- Mostrar ----------
    def mostrar_error(self, texto):
        self.titulo.setText(f"<b>No se puede revisar la vigueta</b><br>{texto}")
        self.resumen.setText("")
        self.arbol.clear()

    def mostrar(self, modelo, losa_id, diseno, editable=True):
        """diseno: el DisenoLosa de la losa (modelo/diseno_vigueta.py)."""
        self._losa = losa_id
        self._poner_vigueta(modelo.secciones[modelo.losas[losa_id].seccion].concreto)
        self.caja.setEnabled(editable)
        if diseno.error:
            self.mostrar_error(diseno.error)
            return
        c = diseno.concreto
        fallan = sum(1 for x in diseno.comprobaciones if x.cumple is False)
        estado = (f"<span style='color:{colores.NO_CUMPLE}'><b>{fallan} no cumple{'n' if fallan != 1 else ''}</b></span>"
                  if fallan else f"<span style='color:{colores.CUMPLE}'><b>todo cumple</b></span>")
        self.titulo.setText(f"<b>{diseno.nombre}</b> — vigueta T {formato.cantidad(c.b, 'seccion', False)} × "
                            f"{formato.cantidad(c.h, 'seccion')}, s = {formato.cantidad(diseno.s, 'seccion')}, "
                            f"bf = {formato.cantidad(diseno.bf, 'seccion')} · {estado}")
        filas = [
            ("Mu+ máximo", formato.cantidad(diseno.mu_pos.valor, "momento"), diseno.mu_pos.detalle()),
            ("Mu− máximo (cara)", formato.cantidad(diseno.mu_neg.valor, "momento"), diseno.mu_neg.detalle()),
            ("Vu máximo (cara)", formato.cantidad(diseno.vu.valor, "fuerza"), diseno.vu.detalle()),
            ("Ma máximo (D + L)", formato.cantidad(diseno.ma.valor, "momento"), diseno.ma.detalle()),
            ("ΔL inmediata", formato.cantidad(diseno.delta_l.valor, "desplazamiento"), diseno.delta_l.detalle()),
            ("Δ después de los tabiques", formato.cantidad(diseno.delta_largo.valor, "desplazamiento"),
             diseno.delta_largo.detalle()),
            ("φMn+ / φMn−", f"{formato.cantidad(diseno.flexion_pos.phi_mn, 'momento')} / "
             + (formato.cantidad(diseno.flexion_neg.phi_mn, "momento") if diseno.flexion_neg else "sin acero arriba"),
             "Tabla 21.2.2: φ con εt"),
            ("Mcr+ / Ig / Icr", f"{formato.cantidad(diseno.mcr_pos, 'momento')} / {formato.cantidad(diseno.ig, 'inercia')}"
             f" / {formato.cantidad(diseno.icr_pos, 'inercia')}", "Ec. 24.2.3.5 y sección agrietada"),
        ]
        gris = colores.INTERFAZ_DESHABILITADO
        self.resumen.setText("<table cellspacing=2>" + "".join(
            f"<tr><td><b>{n}</b>&nbsp;</td><td align=right>{v}</td></tr>"
            f"<tr><td colspan=2 style='color:{gris}'>{d}</td></tr>" for n, v, d in filas) + "</table>")
        self.arbol.clear()
        grupos = {}
        for x in diseno.comprobaciones:
            grupo = grupos.get(x.grupo)
            if grupo is None:
                grupo = grupos[x.grupo] = QTreeWidgetItem(self.arbol, [x.grupo])
                grupo.setFirstColumnSpanned(True)
                grupo.setExpanded(True)
            signo = {True: "✓", False: "✗", None: "·"}[x.cumple]
            limite = "" if x.limite is None else f"{x.relacion} {_texto(x.limite, x.magnitud)}"
            fila = QTreeWidgetItem(grupo, [f"{signo} {x.nombre}", _texto(x.valor, x.magnitud), limite])
            color = {True: colores.CUMPLE, False: colores.NO_CUMPLE, None: colores.INTERFAZ_DESHABILITADO}[x.cumple]
            for columna in range(3):
                fila.setForeground(columna, QBrush(QColor(color)))
            tipo = "" if x.tipo == "obligatoria" else f" ({x.tipo})"
            ayuda = f"{x.clausula}{tipo}" + (f"\n{x.detalle}" if x.detalle else "")
            for columna in range(3):
                fila.setToolTip(columna, ayuda)

    def _poner_vigueta(self, c):
        for caja, valor in ((self.bw, c.b), (self.h, c.h), (self.hf, c.hf), (self.rec, c.recubrimiento),
                            (self.s_estribo, c.s_estribo or 0.20), (self.n, c.nx), (self.n_sup, c.n_sup)):
            caja.poner(valor)
        for lista, numero, defecto in ((self.barra, c.barra, 6), (self.barra_sup, c.barra_sup or 5, 5),
                                       (self.estribo, c.estribo, 0)):
            i = lista.findData(numero)
            lista.setCurrentIndex(i if i >= 0 else lista.findData(defecto))
        self.s_estribo.setEnabled(bool(c.estribo))

    def _aplicar(self):
        if self._losa is None:
            return
        estribo = self.estribo.currentData() or 0
        self.vigueta_editada.emit(self._losa, {
            "bw": self.bw.valor(), "h": self.h.valor(), "hf": self.hf.valor(), "rec": self.rec.valor(),
            "estribo": estribo, "s_estribo": self.s_estribo.valor() if estribo else 0.0,
            "barra": self.barra.currentData(), "n": self.n.valor(), "barra_sup": self.barra_sup.currentData(),
            "n_sup": self.n_sup.valor()})

    def actualizar_unidades(self):
        for campo_ in self.findChildren(CampoNumero):
            campo_.actualizar_unidades()
