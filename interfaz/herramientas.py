"""Herramientas: lo que hace un clic (o un punto escrito en la barra de comandos) sobre la vista.

Cada herramienta es una clase con los mismos métodos: clic, punto_escrito, previsualizar,
cancelar, indicacion... La ventana no necesita saber cuál está activa: le pasa los eventos a la
herramienta actual y cada una responde a su manera. Eso es polimorfismo. Para agregar una
herramienta nueva (apoyos, cargas...) basta otra clase con estos métodos.

Los puntos llegan siempre en unidades internas (m).
"""
import numpy as np

from configuracion import interfaz as ui
from configuracion import unidades
from calculo.tolerancias import TOL_LONGITUD
from modelo.apoyos import NOMBRES, TIPOS
from interfaz.vista3d.seleccion import barra_cercana, elemento_en, nodo_cercano


class Herramienta:
    """Base: no hace nada. Las herramientas concretas redefinen lo que necesitan."""
    usa_previsualizacion = False

    def __init__(self, ventana):
        self.ventana = ventana

    def indicacion(self):
        """Plantilla gris dentro de la barra de comandos: qué valor se espera (vacía si no la usa)."""
        return ""

    def mostrar_panel(self):
        """Si la herramienta usa el panel de Propiedades, lo muestra y devuelve True."""
        return False

    def clic(self, x, y, cand):
        """Clic en (x, y) de la pantalla; cand es el punto candidato (con snap si está activo)."""

    def punto_escrito(self, punto):
        self.ventana.mensaje("Elige Nodo o Elemento para colocar en una posición exacta")

    def previsualizar(self, cand):
        self.ventana.previsualizacion.ocultar()

    def inicio(self):
        """Punto de referencia para mostrar la longitud L, o None."""
        return None

    def ultimo_punto(self):
        """Punto desde el que se mide @dx, dy, dz, o None."""
        return None

    def cancelar(self):
        """Cancela lo que esté a medias. Devuelve True si había algo que cancelar."""
        return False

    def reiniciar(self):
        """Olvida todo lo que la herramienta recuerda (por ejemplo, al abrir otro modelo)."""
        self.cancelar()


class Seleccionar(Herramienta):
    def clic(self, x, y, cand):
        v = self.ventana
        v.seleccionar(elemento_en(v.vista.renderer, v.modelo, x, y, ui.TOL_SELECCION_PX))


class AgregarNodo(Herramienta):
    usa_previsualizacion = True

    def __init__(self, ventana):
        super().__init__(ventana)
        self._ultimo = None

    def indicacion(self):
        return f"x, y, z  ({unidades.simbolo('longitud')})"

    def previsualizar(self, cand):
        self.ventana.previsualizacion.mostrar(cand.punto)

    def ultimo_punto(self):
        return self._ultimo

    def reiniciar(self):
        self._ultimo = None

    def clic(self, x, y, cand):
        if cand.punto is None:
            self.ventana.mensaje("Acércate a un punto de la rejilla o a un nodo, o escribe x, y, z")
            return
        self.colocar(cand.punto)

    def punto_escrito(self, punto):
        self.colocar(punto)

    def colocar(self, punto):
        modelo = self.ventana.modelo
        x, y, z = (float(c) for c in punto)
        self._ultimo = np.array([x, y, z])
        existente = modelo.nodo_en(x, y, z)
        if existente is not None:
            self.ventana.mensaje(f"Ya hay un nodo ahí (nodo {existente})")
            return
        self.ventana.antes_de_cambiar()
        nid = modelo.agregar_nodo(x, y, z)
        self.ventana.modelo_cambiado(f"Nodo {nid} agregado")


class AgregarElemento(Herramienta):
    """Una barra por cada dos puntos (inicial y final). No encadena."""
    usa_previsualizacion = True

    def __init__(self, ventana):
        super().__init__(ventana)
        self._inicio = None              # punto inicial ya elegido, o None
        self._ultimo = None              # último punto final, para @ en la barra siguiente

    def indicacion(self):
        u = unidades.simbolo("longitud")
        if self._inicio is None:
            return f"x, y, z del punto inicial  ({u})"
        return f"x, y, z o @dx, dy, dz del punto final  ({u})"

    def inicio(self):
        return self._inicio

    def ultimo_punto(self):
        return self._inicio if self._inicio is not None else self._ultimo

    def previsualizar(self, cand):
        self.ventana.previsualizacion.mostrar(cand.punto, desde=self._inicio)

    def cancelar(self):
        habia = self._inicio is not None
        self._inicio = None
        return habia

    def reiniciar(self):
        self._inicio = self._ultimo = None

    def clic(self, x, y, cand):
        if cand.punto is None:
            self.ventana.mensaje("Acércate a un punto de la rejilla o a un nodo, o escribe x, y, z")
            return
        self.poner(cand.punto)

    def punto_escrito(self, punto):
        self.poner(punto)

    def poner(self, punto):
        punto = np.asarray(punto, dtype=float)
        if self._inicio is None:                    # primer punto: solo se recuerda
            self._inicio = punto
            return
        inicio, self._inicio = self._inicio, None   # segundo punto: se crea la barra
        self._ultimo = punto
        if np.linalg.norm(punto - inicio) < TOL_LONGITUD:
            self.ventana.mensaje("La barra tendría longitud cero")
            return
        modelo = self.ventana.modelo
        ni, nj = modelo.nodo_en(*inicio), modelo.nodo_en(*punto)
        if ni is not None and nj is not None:
            existente = modelo.elemento_entre(ni, nj)
            if existente is not None:
                self.ventana.mensaje(f"Ya existe la barra {existente} entre los nodos {ni} y {nj}")
                return
        # Los nodos que falten se crean ahora, no en el primer clic: si se cancela, no quedan sueltos
        self.ventana.antes_de_cambiar()
        if ni is None:
            ni = modelo.agregar_nodo(*(float(c) for c in inicio))
        if nj is None:
            nj = modelo.agregar_nodo(*(float(c) for c in punto))
        material = min(modelo.materiales) if modelo.materiales else None
        seccion = min(modelo.secciones) if modelo.secciones else None
        if seccion is not None and modelo.secciones[seccion].material is not None:
            material = modelo.secciones[seccion].material     # la sección lleva su material
        eid = modelo.agregar_elemento(ni, nj, material, seccion)
        texto = f"Elemento {eid} agregado (nodos {ni} y {nj})"
        if material is None or seccion is None:
            texto += ": sin material o sección, se asignarán en Definir"
        self.ventana.modelo_cambiado(texto)


class AgregarApoyo(Herramienta):
    """Asigna el tipo de apoyo elegido en Propiedades al nodo sobre el que se hace clic."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.tipo = "empotrado"

    def mostrar_panel(self):
        self.ventana.propiedades.mostrar_panel_apoyo(self.tipo)
        return True

    def clic(self, x, y, cand):
        v = self.ventana
        nid = nodo_cercano(v.vista.renderer, v.modelo, x, y, ui.TOL_SELECCION_PX)
        if nid is None:
            v.mensaje("Haz clic sobre un nodo")
            return
        if v.modelo.nodos[nid].apoyo == TIPOS[self.tipo]:
            v.mensaje(f"El nodo {nid} ya es {NOMBRES[self.tipo].lower()}")
            return
        v.antes_de_cambiar()
        v.modelo.restringir(nid, *TIPOS[self.tipo])
        texto = "sin apoyo" if self.tipo == "libre" else NOMBRES[self.tipo].lower()
        v.modelo_cambiado(f"Nodo {nid}: {texto}")


class AgregarCargaNodo(Herramienta):
    """Carga en el nodo sobre el que se hace clic, con los valores del panel de Propiedades, en el
    caso de carga activo. Reemplaza las cargas que tenía en ese caso o se suma a ellas."""

    def mostrar_panel(self):
        v = self.ventana
        v.propiedades.mostrar_panel_carga("nodo", v.modelo.casos[v.caso_activo()].nombre)
        return True

    def clic(self, x, y, cand):
        v = self.ventana
        nid = nodo_cercano(v.vista.renderer, v.modelo, x, y, ui.TOL_SELECCION_PX)
        if nid is None:
            v.mensaje("Haz clic sobre un nodo")
            return
        panel = v.propiedades.panel.panel_carga_nodo
        valores = panel.valores()
        if not any(valores):
            v.mensaje("Escribe algún valor de fuerza o momento")
            return
        caso = v.caso_activo()
        v.antes_de_cambiar()
        if panel.reemplazar.isChecked():
            for cid in v.modelo.cargas_en("nodo", nid, caso):
                v.modelo.eliminar_carga(cid)
        v.modelo.agregar_carga_nodal(nid, valores, caso)
        v.modelo_cambiado(f"Carga en el nodo {nid}")


class AgregarCargaBarra(Herramienta):
    """Carga en la barra sobre la que se hace clic (uniforme, puntual o momento), con los valores del
    panel de Propiedades, en el caso activo. Se suma a las que tenía o las reemplaza."""

    def mostrar_panel(self):
        v = self.ventana
        v.propiedades.mostrar_panel_carga("barra", v.modelo.casos[v.caso_activo()].nombre)
        return True

    def clic(self, x, y, cand):
        v = self.ventana
        eid = barra_cercana(v.vista.renderer, v.modelo, x, y, ui.TOL_SELECCION_PX)
        if eid is None:
            v.mensaje("Haz clic sobre una barra")
            return
        panel = v.propiedades.panel.panel_carga_barra
        tipo, valor, direccion, a = panel.valores()
        if valor == 0:
            v.mensaje("Escribe el valor de la carga")
            return
        el = v.modelo.elementos[eid]
        largo = v.modelo.nodos[el.ni].distancia(v.modelo.nodos[el.nj])
        if tipo != "uniforme" and a > largo + TOL_LONGITUD:
            v.mensaje(f"a es mayor que el largo de la barra {eid} ({largo:.3f} m)")
            return
        caso = v.caso_activo()
        v.antes_de_cambiar()
        if panel.reemplazar.isChecked():
            for cid in v.modelo.cargas_en("barra", eid, caso):
                v.modelo.eliminar_carga(cid)
        v.modelo.agregar_carga_barra(eid, tipo, valor, direccion, a, caso)
        v.modelo_cambiado(f"Carga en la barra {eid}")
