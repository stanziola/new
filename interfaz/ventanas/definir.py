"""Definir materiales y secciones: el árbol con carpetas, el menú de clic derecho y los cambios.

Materiales y secciones van SEPARADOS, y por ahora agrupados solo en Concreto:
- en el Explorador del modelo, las carpetas Materiales y Secciones, con las propiedades en el panel
  Propiedades;
- en las ventanas Materiales y Secciones (menú Definir y barra de arriba), cada una con su árbol
  y su propio panel de propiedades a la derecha.
Los materiales sin f'c y las secciones sin refuerzo (archivos viejos o creados desde el código) van
a una carpeta "Otros" que solo aparece si hay alguno, para poder revisarlos o borrarlos.

Cómo se usa (como en Civil 3D): clic muestra (otro clic, o un clic en el vacío, lo quita); doble
clic edita; clic derecho da el menú:
- en la carpeta Concreto: Nuevo…;
- en un material o una sección: Editar…, Copiar… (uno nuevo a partir de este) y Eliminar.

Qué cambia cada edición (decisión del usuario):
- editar un material o una sección aquí cambia todo el modelo: todas las barras que lo usan;
- editar las medidas de la sección de UNA barra (Propiedades de esa barra) crea otra sección solo
  para ella. Eso lo hace la ventana, no este módulo.
Todo pasa por ventana.antes_de_cambiar(), así que se puede deshacer con Ctrl+Z.
"""
import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QMenu, QPushButton, QSplitter, QTreeWidgetItem, QVBoxLayout

from modelo import concreto as cc
from interfaz.paneles.comunes import ArbolLimpio, carpeta
from interfaz.paneles.propiedades import PanelPropiedades
from interfaz.textos import nombre

DATO = Qt.UserRole              # ("material", id) o ("seccion", id): lo que se muestra al hacer clic
CLAVE = Qt.UserRole + 1         # nombre de la carpeta, para recordar si estaba abierta
CARPETA = Qt.UserRole + 2       # ("materiales", None) o ("familia", ("material", "concreto"))

TITULOS = {"material": "Materiales", "seccion": "Secciones"}


# ---------------------------------------------------------------- Árbol
def _carpeta(padre, texto, clave, info, abierto):
    item = carpeta(QTreeWidgetItem(padre, [texto]))
    item.setData(0, CLAVE, clave)
    item.setData(0, CARPETA, info)
    item.setExpanded(abierto(clave))
    return item


def _hoja(padre, texto, dato):
    item = QTreeWidgetItem(padre, [texto])
    item.setData(0, DATO, dato)
    return item


def llenar_definiciones(padre, modelo, abierto, tipo, con_raiz=False):
    """Las carpetas de un tipo ("material" o "seccion") y, adentro, cada uno por su nombre (el de
    pantalla, en las unidades vigentes).

    padre: el árbol o un ítem. abierto(clave) dice si una carpeta va abierta. Con con_raiz, todo va
    dentro de una carpeta "Materiales (n)" o "Secciones (n)" (así lo muestra el explorador).
    Devuelve {("material", id) o ("seccion", id): ítem} para poder marcarlos."""
    coleccion = modelo.materiales if tipo == "material" else modelo.secciones
    familia_de = cc.familia_material if tipo == "material" else cc.familia_seccion
    if con_raiz:
        raiz = TITULOS[tipo].lower()
        padre = _carpeta(padre, f"{TITULOS[tipo]} ({len(coleccion)})", raiz, (raiz, None), abierto)
    items = {}
    hay_otros = any(familia_de(o) == "otros" for o in coleccion.values())
    for familia in list(cc.FAMILIAS) + (["otros"] if hay_otros else []):
        clave = f"{tipo}_{familia}"
        grupo = _carpeta(padre, cc.nombre_familia(familia), clave, ("familia", (tipo, familia)), abierto)
        for ident, obj in coleccion.items():
            if familia_de(obj) == familia:
                items[(tipo, ident)] = _hoja(grupo, nombre(obj, modelo), (tipo, ident))
    return items


def info_de(item):
    """Qué es un ítem del árbol: su dato (material o sección) o su carpeta. None si no es de Definir."""
    if item is None:
        return None
    dato = item.data(0, DATO)
    if dato is not None and tuple(dato)[0] in ("material", "seccion"):
        return tuple(dato)
    info = item.data(0, CARPETA)
    if info is None:
        return None
    clase, valor = info
    return (clase, tuple(valor) if isinstance(valor, (list, tuple)) else valor)


# ---------------------------------------------------------------- Menú de clic derecho
def menu_definir(parent, info, modelo, destino):
    """Menú de clic derecho para info (de info_de), o None si no hay nada que ofrecer."""
    if info is None:
        return None
    clase, valor = info
    menu = QMenu(parent)
    menu.setToolTipsVisible(True)

    def accion(texto, funcion, habilitada=True, ayuda=""):
        a = menu.addAction(texto)
        a.triggered.connect(lambda *_: funcion())
        a.setEnabled(habilitada)
        a.setToolTip(ayuda)
        return a

    if clase in ("materiales", "secciones"):
        tipo = "material" if clase == "materiales" else "seccion"
        for familia, nombre in cc.FAMILIAS.items():
            accion(f"Nuevo: {nombre}…" if tipo == "material" else f"Nueva: {nombre}…",
                   lambda t=tipo, f=familia: destino.nuevo(t, f))
    elif clase == "familia":
        tipo, familia = valor
        if familia in cc.FAMILIAS:                       # en "Otros" no se crean nuevos
            accion("Nuevo…" if tipo == "material" else "Nueva…", lambda: destino.nuevo(tipo, familia))
    elif clase == "material" and valor in modelo.materiales:
        accion("Editar…", lambda: destino.editar("material", valor))
        accion("Copiar…", lambda: destino.copiar("material", valor))
        menu.addSeparator()
        barras, secciones = cc.uso_material(modelo, valor)
        partes = ([f"{len(barras)} barra{'s' if len(barras) != 1 else ''}"] if barras else []) + \
                 ([f"{len(secciones)} sección{'es' if len(secciones) != 1 else ''}"] if secciones else [])
        accion("Eliminar" + (f" (en uso: {', '.join(partes)})" if partes else ""),
               lambda: destino.eliminar("material", valor), habilitada=not partes)
    elif clase == "seccion" and valor in modelo.secciones:
        sec = modelo.secciones[valor]
        rectangular = sec.concreto is None or sec.concreto.forma == "rectangular"
        accion("Editar…", lambda: destino.editar("seccion", valor), habilitada=rectangular,
               ayuda="" if rectangular else "Por ahora solo se editan las secciones rectangulares")
        accion("Copiar…", lambda: destino.copiar("seccion", valor), habilitada=rectangular)
        menu.addSeparator()
        barras = cc.uso_seccion(modelo, valor)
        accion("Eliminar" + (f" (en uso: {len(barras)} barra{'s' if len(barras) != 1 else ''})" if barras else ""),
               lambda: destino.eliminar("seccion", valor), habilitada=not barras)
    return menu if menu.actions() else None


# ---------------------------------------------------------------- Cambios en el modelo
def _hacer(modelo, pedido):
    """Aplica el pedido a un modelo. Devuelve (item que queda a la vista, texto del aviso)."""
    tipo, familia, modo, ident, v = (pedido["tipo"], pedido["familia"], pedido["modo"], pedido["ident"],
                                     pedido["valores"])
    nuevo = modo in ("nuevo", "copiar")
    if tipo == "material":
        if nuevo:
            mid = cc.crear_material(modelo, v["nombre"], fc=v.get("fc"), e=v.get("e"), g=v.get("g"),
                                    gamma=v.get("gamma"))
            return ("material", mid), f"Material {mid} agregado: {nombre(modelo.materiales[mid])}"
        barras, secciones = cc.cambiar_material(modelo, ident, v["nombre"], fc=v.get("fc"), e=v.get("e"),
                                                g=v.get("g"), gamma=v.get("gamma"))
        texto = f"Material cambiado: {nombre(modelo.materiales[ident])}"
        if barras or secciones:
            texto += f" (lo usan {len(barras)} barras y {len(secciones)} secciones)"
        return ("material", ident), texto
    if familia == "concreto":
        args = (v["material"], v["b"], v["h"], v["d"], v["barra"], v["nx"], v["ny"], v["fy"])
        if nuevo:
            existente = cc.buscar_seccion(modelo, *args)
            if existente is not None:
                raise ValueError(f"Ya existe una sección igual: {nombre(modelo.secciones[existente], modelo)}")
            sid = cc.crear_seccion(modelo, *args)
            return ("seccion", sid), f"Sección {sid} agregada: {nombre(modelo.secciones[sid], modelo)}"
        barras = cc.cambiar_seccion(modelo, ident, *args)
    else:
        args = (v["nombre"], v["a"], v["iy"], v["iz"], v["j"], v["material"])
        if nuevo:
            sid = cc.crear_seccion_general(modelo, *args)
            return ("seccion", sid), f"Sección {sid} agregada: {nombre(modelo.secciones[sid], modelo)}"
        barras = cc.cambiar_seccion_general(modelo, ident, *args)
    texto = f"Sección cambiada: {nombre(modelo.secciones[ident], modelo)}"
    if barras:
        texto += f" (la usan {len(barras)} barras)"
    return ("seccion", ident), texto


def aplicar(ventana, pedido):
    """Aplica un pedido de Guardar. Primero lo prueba en una copia: si no sirve (ValueError), el
    modelo no se toca y no queda un paso vacío en Deshacer."""
    _hacer(copy.deepcopy(ventana.modelo), pedido)
    ventana.antes_de_cambiar()
    return _hacer(ventana.modelo, pedido)


def eliminar(ventana, tipo, ident):
    """Elimina un material o una sección que no esté en uso. Devuelve el texto del aviso."""
    modelo = ventana.modelo
    prueba = copy.deepcopy(modelo)
    (prueba.eliminar_material if tipo == "material" else prueba.eliminar_seccion)(ident)   # ValueError si en uso
    texto = nombre((modelo.materiales if tipo == "material" else modelo.secciones)[ident], modelo)
    ventana.antes_de_cambiar()
    (modelo.eliminar_material if tipo == "material" else modelo.eliminar_seccion)(ident)
    return f"{'Material eliminado' if tipo == 'material' else 'Sección eliminada'}: {texto}"


class Destino:
    """Dónde se muestran y se editan: un PanelPropiedades (el de la derecha o el de la ventana
    Definir). mostrar_item(item) recuerda qué debe verse cuando el modelo se actualice."""

    def __init__(self, ventana, panel, mostrar_item):
        self.ventana, self.panel, self.mostrar_item = ventana, panel, mostrar_item
        panel.guardar_definicion.connect(self.guardar)

    def _familia(self, tipo, ident):
        modelo = self.ventana.modelo
        if tipo == "material":
            return cc.familia_material(modelo.materiales[ident])
        return cc.familia_seccion(modelo.secciones[ident])

    def nuevo(self, tipo, familia):
        self.panel.editar(self.ventana.modelo, {"tipo": tipo, "familia": familia, "modo": "nuevo", "ident": None})

    def editar(self, tipo, ident):
        self.panel.editar(self.ventana.modelo, {"tipo": tipo, "familia": self._familia(tipo, ident),
                                                "modo": "editar", "ident": ident})

    def copiar(self, tipo, ident):
        self.panel.editar(self.ventana.modelo, {"tipo": tipo, "familia": self._familia(tipo, ident),
                                                "modo": "copiar", "ident": ident})

    def eliminar(self, tipo, ident):
        try:
            texto = eliminar(self.ventana, tipo, ident)
        except ValueError as e:
            self.ventana.mensaje(str(e))
            return
        self.mostrar_item(None)
        self.ventana.modelo_cambiado(texto)

    def guardar(self, pedido):
        try:
            item, texto = aplicar(self.ventana, pedido)
        except (ValueError, KeyError) as e:
            self.panel.mostrar_error(str(e).strip("'\""))
            return
        self.mostrar_item(item)
        self.ventana.modelo_cambiado(texto)


# ---------------------------------------------------------------- Ventanas Materiales y Secciones
class DialogoDefinir(QDialog):
    """Ventana Materiales o Secciones: su árbol a la izquierda y las propiedades a la derecha.

    No es modal: con ella abierta se puede seguir usando el programa (Ctrl+Z, Ver 2D...). Se
    actualiza sola cuando cambia el modelo (señal ventana.modelo_actualizado)."""

    def __init__(self, ventana, tipo):
        super().__init__(ventana)
        self.ventana, self.tipo = ventana, tipo
        self.setWindowTitle(TITULOS[tipo])
        self.resize(780, 560)
        self.actual = None                       # lo que se ve a la derecha
        self._abiertos = {f"{tipo}_{familia}" for familia in list(cc.FAMILIAS) + ["otros"]}
        self.arbol = ArbolLimpio()
        self.arbol.setContextMenuPolicy(Qt.CustomContextMenu)
        self.arbol.customContextMenuRequested.connect(self._menu)
        self.arbol.itemClicked.connect(self._clic)
        self.arbol.itemDoubleClicked.connect(self._doble_clic)
        self.arbol.vaciado.connect(self._vaciado)
        self.panel = PanelPropiedades()
        self.panel.ver_diagrama.connect(ventana.ver_diagrama)
        self.panel.cancelar_definicion.connect(self._mostrar_actual)
        self.destino = Destino(ventana, self.panel, self._recordar)
        divisor = QSplitter()
        divisor.addWidget(self.arbol)
        divisor.addWidget(self.panel)
        divisor.setSizes([280, 500])
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.close)
        abajo = QHBoxLayout()
        abajo.addStretch(1)
        abajo.addWidget(cerrar)
        diseno = QVBoxLayout(self)
        diseno.addWidget(divisor, 1)
        diseno.addLayout(abajo)
        ventana.modelo_actualizado.connect(self.actualizar)
        self.actualizar()

    def _recordar(self, item):
        self.actual = item

    def _recordar_abiertos(self):
        pila = [self.arbol.topLevelItem(i) for i in range(self.arbol.topLevelItemCount())]
        while pila:
            it = pila.pop()
            clave = it.data(0, CLAVE)
            if clave is not None:
                (self._abiertos.add if it.isExpanded() else self._abiertos.discard)(clave)
            pila += [it.child(i) for i in range(it.childCount())]

    def actualizar(self, *_):
        """Vuelve a armar el árbol con el modelo vigente y muestra lo que corresponda."""
        if self.arbol.topLevelItemCount():
            self._recordar_abiertos()
        self.arbol.clear()
        items = llenar_definiciones(self.arbol, self.ventana.modelo, lambda clave: clave in self._abiertos,
                                    self.tipo)
        if self.actual not in items:
            self.actual = None
        else:
            items[self.actual].setSelected(True)
        if self.panel.editando():
            self.panel.actualizar_unidades()     # el formulario a medias, en las unidades vigentes
        else:
            self._mostrar_actual()

    def _mostrar_actual(self):
        self.panel.mostrar(self.ventana.modelo, self.actual)

    def _clic(self, item, _columna):
        info = info_de(item)
        if info is not None and info[0] == self.tipo:
            self.actual = info
            self._mostrar_actual()

    def _vaciado(self):
        self.actual = None
        if not self.panel.editando():            # si está a mitad de una edición, no se pierde
            self._mostrar_actual()

    def _doble_clic(self, item, _columna):
        info = info_de(item)
        if info is not None and info[0] == self.tipo:
            self.actual = info
            self.destino.editar(*info)

    def _menu(self, posicion):
        item = self.arbol.itemAt(posicion)
        menu = menu_definir(self, info_de(item), self.ventana.modelo, self.destino)
        if menu is not None:
            menu.exec(self.arbol.viewport().mapToGlobal(posicion))
