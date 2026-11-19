"""Ventana principal.

Organización (como ETABS y Civil 3D):
- Arriba: menús con palabras (Archivo, Editar, Ver, Definir, Configuración) y una barra con íconos:
  Deshacer y Rehacer; Caso, Σ y Combinación; Analizar (▶); y los resultados.
- Izquierda: las herramientas que cambian lo que hace el clic (Seleccionar, Nodo, Elemento, Asignar
  sección, Apoyo y cargas) y el Explorador del modelo (pestañas Modelo y Tablas).
- Derecha: Propiedades de lo seleccionado (y, con una columna, la pestaña Interacción).
- Abajo del dibujo: el panel Diagrama (abierto al iniciar; se cierra y se abre desde Ver), que
  muestra para la barra elegida lo mismo que está prendido en la barra de arriba.
- Abajo de todo: la barra de comandos (activa solo con Nodo o Elemento) y la barra de estado, con
  la posición del puntero a la izquierda y Rejilla, Snap, Etiquetas, Sección real con el deslizador
  de transparencia, Cargas, Reacciones y Encuadre a la derecha.
Los paneles se pueden agrandar, mover de lado, cerrar y volver a abrir desde el menú Ver (no se
desacoplan como ventanas sueltas).

Tres estados (los aplica _actualizar_modo; lo que no se usa en cada uno queda en gris):
1. Editar: se cambia el modelo con las herramientas de la izquierda y se ven las cargas del caso
   elegido. Los resultados, Σ y la lista de combinaciones, en gris.
2. Resultados de un caso: se ve la deformada o un diagrama del caso elegido. Las herramientas de la
   izquierda (todas, también Seleccionar) y la lista de combinaciones, en gris. No se dibujan
   cargas. El clic sobre un nodo, un apoyo o una barra sigue seleccionando (para ver sus datos en
   Propiedades y en Diagrama).
3. Resultados de una combinación (Σ marcado): igual, con la lista de casos en gris.
De Editar a los resultados se pasa con ▶ (Analizar), que queda marcado; de vuelta, con otro clic en
▶. Cualquier cambio del modelo vuelve a Editar y borra el análisis.
Al entrar a los resultados la Sección real se apaga sola (los diagramas y la deformada se leen mejor
sobre las barras como líneas); se puede prender a mano y, al volver a Editar, queda como estaba.
Los desplazamientos (Deformada ▾: total, Δx, Δy o Δz) van en ejes globales; las fuerzas internas (N,
V, M y T), en los ejes locales de cada barra, que se dibujan sobre la barra seleccionada (menos con la
deformada a la vista, para que no se confundan con los globales).
La lógica de cada herramienta está en herramientas.py; la de la rejilla 3D y el snap, en vista3d/rejilla.py.
"""
from pathlib import Path

import numpy as np

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (QApplication, QDockWidget, QFileDialog, QLabel, QLineEdit, QMainWindow, QMenu,
                               QMessageBox, QSizePolicy, QSlider, QToolBar, QToolButton, QWidget)
from pyvistaqt import QtInteractor

from configuracion import colores
from configuracion import interfaz as ui
from interfaz import textos
from interfaz.vista3d.camara import AnimadorCamara
from interfaz.vista3d.cubo import CuboVistas, viewport_esquina
from interfaz.ventanas.casos import DialogoCasos, DialogoCombinaciones
from interfaz.ventanas.definir import Destino, DialogoDefinir, menu_definir
from interfaz.ventanas.interaccion import VentanaDiagrama
from interfaz.ventanas.dialogo_configuracion import DialogoConfiguracion
from interfaz.vista3d.cargas import dibujar_cargas
from interfaz.vista3d.dibujo import (ModeloDibujado, Previsualizacion, dibujar_ejes_locales, dibujar_modelo,
                                     dibujar_rejilla)
from interfaz.vista3d.resultados import (DEFORMADAS, NOMBRE_DEFORMADA, dibujar_deformada, dibujar_diagrama,
                                         dibujar_envolvente, dibujar_reacciones)
from interfaz.paneles.diagrama import PanelDiagrama
from interfaz.paneles.explorador import Explorador
from interfaz.historial import Historial
from interfaz.herramientas import (AgregarApoyo, AgregarCargaBarra, AgregarCargaNodo, AgregarElemento,
                                   AgregarLosa, AgregarNodo, AsignarSeccion, Seleccionar)
from interfaz.vista3d.losas import cargas_de_area, cortes_superiores, resumenes as resumenes_losas
from interfaz.vista3d.medicion import Medicion
from interfaz.iconos import icono
from interfaz.paneles.comunes import Lista, ListaDosColumnas, MenuPersistente, poner_titulo
from interfaz.vista3d.rejilla import Candidato, candidato, geometria_rejilla, interpretar, texto_coordenadas
from interfaz.paneles.propiedades import Propiedades
from interfaz.vista3d.seleccion import elemento_en
from interfaz.ventanas.matriz import VentanaMatriz
from interfaz.tema import aplicar_tema
from modelo import Modelo, archivo
from modelo import combinaciones as comb
from modelo import concreto as cc
from modelo import losas as ml
from modelo.analisis import analizar, cargas_de_losas, combinar, demandas_columna, envolvente
from modelo.apoyos import TIPOS
from modelo.diseno_vigueta import disenar_losa

ENVOLVENTE = "ENV"            # clave de la envolvente de diseño en la lista Combinación (y en la caché _combinados)
ENVOLVENTE_SERVICIO = "ENVS"  # la de servicio (las 4 combinaciones sin mayorar: de ahí sale Ma)
ENVOLVENTES = (ENVOLVENTE, ENVOLVENTE_SERVICIO)
DISENO, SERVICIO = 0, 1       # columnas de la lista Combinación
TECLAS_A_COMANDOS = set("0123456789.-@")   # escritas sobre la vista, van a la barra de comandos
HERRAMIENTAS_DE_CARGA = ("carga_nodo", "carga_barra")


def _plural(n, palabra):
    return f"{n} {palabra}{'s' if n != 1 else ''}"


def _factor_texto(factor):
    """×236, ×12.5 o ×0.75: el factor de la deformada, sin decimales de más."""
    decimales = 0 if factor >= 100 else 1 if factor >= 10 else 2
    texto = f"{factor:.{decimales}f}"
    return texto.rstrip("0").rstrip(".") if "." in texto else texto


class Ventana(QMainWindow):
    modelo_actualizado = Signal()               # el modelo o las unidades cambiaron (Definir lo escucha)

    def __init__(self, modelo=None, ruta=None):
        super().__init__()
        self.resize(*ui.TAMANO_VENTANA)

        self.modelo = modelo if modelo is not None else Modelo()
        self.ruta = Path(ruta) if ruta else None   # archivo del modelo (None = todavía sin guardar)
        self.modificado = False
        self.seleccion = None                      # ("nodo", id), ("apoyo", id), ("barra", id), ("carga", id) o None
        self.resaltado = None                      # lo que está bajo el mouse con Seleccionar
        self.marcados = []                         # barras de la sección o el material elegidos en el Explorador
        self._en_propiedades = None                # lo que muestra el panel Propiedades
        self.dibujado = ModeloDibujado()
        self.rejilla = None                        # rejilla 3D (se rehace en cada redibujar)
        self.candidato = Candidato()               # dónde caería un clic ahora
        self._pos_presion = None                   # dónde se presionó el botón izquierdo
        self._mouse = None                         # última posición del mouse sobre la vista
        self._cerrando = False
        self.diagramas = []                        # ventanas de diagramas de interacción abiertas
        self.historial = Historial()               # Deshacer (Ctrl+Z) y Rehacer (Ctrl+Y)
        self.resultados = None                     # {caso: ResultadoCaso} del último análisis vigente
        self.modo_resultados = False               # True: se ven resultados y no se edita (▶ marcado)
        self.ver_combinaciones = False             # en resultados: se ve una combinación (Σ), no un caso
        self.resultado_visible = None              # None, "deformada", "Dx", "Dy", "Dz", "N", "Vy", "Vz", "T", "My" o "Mz"
        self._ultimo_resultado = "deformada"       # lo último que se vio: es lo que muestra ▶ al entrar
        self.factor_deformada = None               # cuánto se amplificó la deformada dibujada
        self._escala_diagrama = 0.0                # la del diagrama dibujado (para el corte del panel Diagrama)
        self._corte = None                         # (ID de barra, x) del corte del panel Diagrama, o None
        self._combinados = {}                      # {clave de combinación: ResultadoCaso} (caché)
        self.opacidad_concreto = 1.0               # de las cajas de la sección real (deslizador de abajo)
        self._ancho_normal = None                  # ancho de Propiedades antes de ensancharlo (pestaña Interacción)
        self._seccion_real_antes = None            # cómo estaba Sección real antes de analizar (None: editando)
        self._cambiando_seccion_real = False       # la está cambiando el programa: no redibujar dos veces
        # Sistemas de vigueta (lista Sistema): con uno a la vista, self.modelo es el modelo generado de su
        # franja (no se edita) y el modelo 3D espera en _principal, con sus resultados
        self.sistema = None                        # (ID de losa, letra de la franja) que se ve, o None
        self._sv = None                            # su SistemaVigueta (con un caso por cada caso de viva)
        self._principal = None
        self._resultados_principal = None
        self._cache = {}                           # cálculos de las losas: "resumenes", "cargas", ("diseno", ID)

        # Tres luces blancas: los grises se ven grises (las de pyvista por defecto los tiñen)
        self.vista = QtInteractor(self, lighting="three lights")
        self.setCentralWidget(self.vista)
        # Transparencia bien ordenada (depth peeling). Sin esto VTK dibuja lo translúcido sin ordenar:
        # con 1 % de transparencia el acero y las caras interiores de los nudos aparecían de golpe
        try:
            self.vista.enable_depth_peeling(number_of_peels=6, occlusion_ratio=0.0)
        except Exception:                          # tarjetas que no lo soportan: se ve igual, menos preciso
            pass
        # Ejes X (rojo), Y (verde) y Z (azul) abajo a la izquierda: los mismos colores de los ejes
        # locales x, y, z de la barra seleccionada
        self.vista.add_axes(x_color=colores.EJE_X, y_color=colores.EJE_Y, z_color=colores.EJE_Z)
        self.animador = AnimadorCamara(self.vista)  # giro suave de la cámara (cubo y Encuadre)
        self.previsualizacion = Previsualizacion(self.vista)
        self.medicion = Medicion(self)              # Medir (barra de arriba, a la derecha)
        self.ventana_matriz = VentanaMatriz(self)

        self._crear_paneles()
        self._crear_menus()
        self._crear_barra_definir()
        self._crear_herramientas()
        self._crear_barra_comandos()
        self._crear_barra_inferior()

        self._actualizar_modo()
        self.redibujar(reiniciar_camara=True)
        self.cubo = CuboVistas(self.vista, self.animador)   # cubo de vistas, arriba a la derecha
        self.explorador.actualizar(self.modelo, self.caso_activo())
        self._mostrar_propiedades(None)
        self._actualizar_titulo()
        self._actualizar_deshacer()
        self.actualizar_indicacion()
        self._actualizar_puntero()

        iren = self.vista.iren
        # Clic = presionar y soltar casi en el mismo punto. Arrastrar sigue rotando la vista.
        iren.add_observer("LeftButtonPressEvent", self._al_presionar)
        iren.add_observer("LeftButtonReleaseEvent", self._al_soltar)
        # Si el usuario desplaza o hace zoom a mitad de un giro, manda el usuario.
        for evento in ("MiddleButtonPressEvent", "RightButtonPressEvent",
                       "MouseWheelForwardEvent", "MouseWheelBackwardEvent"):
            iren.add_observer(evento, lambda *_: self.animador.detener())
        iren.add_observer("MouseMoveEvent", self._al_mover)
        iren.add_observer("LeaveEvent", self._al_salir)
        self.vista.installEventFilter(self)       # números escritos sobre la vista -> comandos
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.activated.connect(self.cancelar)

    def _accion(self, nombre_icono, texto, ayuda, activable=False, activa=False, atajo=None):
        """Botón (QAction) con ícono, tooltip y, si se pide, atajo de teclado."""
        accion = QAction(icono(nombre_icono), texto, self)
        accion.setToolTip(ayuda)
        accion.setCheckable(activable)
        accion.setChecked(activa)
        if atajo:
            accion.setShortcut(QKeySequence(atajo))
        return accion

    # ---------- Paneles (izquierda, derecha y abajo) ----------
    def _crear_paneles(self):
        self.explorador = Explorador(self)
        self.propiedades = Propiedades(self)
        self.diagrama = PanelDiagrama(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.explorador)
        self.addDockWidget(Qt.RightDockWidgetArea, self.propiedades)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.diagrama)
        # Las esquinas de abajo son de los paneles de los lados: el Diagrama queda solo bajo el dibujo
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        for panel in (self.explorador, self.propiedades, self.diagrama):   # sin el botón de desacoplar
            panel.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
            poner_titulo(panel)                                            # la x sola, sin recuadro
        self.resizeDocks([self.explorador, self.propiedades], [260, 300], Qt.Horizontal)
        self.diagrama.setVisible(ui.DIAGRAMA_VISIBLE)                      # se cierra y se abre desde Ver
        self.diagrama.visibilityChanged.connect(lambda visible: visible and self._refrescar_diagrama())
        self.diagrama.corte.connect(self._dibujar_corte)          # el punto verde sobre la barra
        self.explorador.elegido.connect(self._elegido_en_explorador)
        self.explorador.vaciado.connect(lambda: self.seleccionar(None))
        self.propiedades.ver_diagrama.connect(self.ver_diagrama)
        self.propiedades.asignar_seccion.connect(self._asignar_seccion)
        self.propiedades.editar_seccion.connect(self._editar_seccion)
        self.propiedades.interaccion_a_la_vista.connect(self._ancho_propiedades)
        self.propiedades.seccion_columna_editada.connect(self._editar_seccion_columna)
        self.propiedades.losa_editada.connect(self._editar_losa)
        self.propiedades.pano_editado.connect(self._editar_pano)
        self.propiedades.vigueta_editada.connect(self._editar_vigueta)
        self.explorador.menu_losa.connect(self._menu_losa)
        self.explorador.franja_abierta.connect(self.abrir_sistema)
        # Materiales y secciones desde el Explorador: se muestran y se editan en Propiedades
        self.destino = Destino(self, self.propiedades.panel, self._ver_en_propiedades)
        self.propiedades.cancelar_definicion.connect(lambda: self._mostrar_propiedades(self._en_propiedades))
        self.explorador.doble_clic.connect(lambda info: self.destino.editar(*info))
        self.explorador.menu_pedido.connect(self._menu_definir)
        self._dialogos_definir = {}               # "material" y "seccion": una ventana para cada uno

    def _ancho_propiedades(self, interaccion):
        """Con la pestaña Interacción a la vista, el panel Propiedades se ensancha para que el
        diagrama se aprecie (ui.ANCHO_PANEL_INTERACCION, sin pasar del 60 % de la ventana); al volver
        a la pestaña Datos, o al dejar de tener una columna elegida, recupera el ancho que tenía."""
        if interaccion:
            self._ancho_normal = self.propiedades.width()
            ancho = max(self._ancho_normal, min(ui.ANCHO_PANEL_INTERACCION, int(0.6 * self.width())))
        elif self._ancho_normal is not None:
            ancho, self._ancho_normal = self._ancho_normal, None
        else:
            return
        self.resizeDocks([self.propiedades], [ancho], Qt.Horizontal)

    def _mostrar_propiedades(self, item):
        """Propiedades muestra lo seleccionado, salvo que la herramienta use el panel (Apoyo...).
        También pone al día el panel Diagrama, que sigue a la barra seleccionada."""
        self._en_propiedades = item
        if not self.herramienta.mostrar_panel():
            caso = None if self.modo_combinaciones else self.caso_activo()
            self.propiedades.mostrar(self.modelo, item, caso=caso, rc=self._rc(),
                                     editable=not self.modo_resultados and self.sistema is None,
                                     puntos=self._puntos_columna if self.modo_resultados and self.resultados else None,
                                     activa=self._combinacion_a_la_vista(), losa=self._losa_de(item),
                                     diseno=self._diseno)
        self._refrescar_diagrama()

    # ---------- Losas: lo calculado se guarda hasta que cambie el modelo ----------
    def _modelo_real(self):
        """El modelo 3D, aunque se esté viendo un sistema de vigueta."""
        return self._principal if self._principal is not None else self.modelo

    def _calculado(self, clave, funcion):
        if clave not in self._cache:
            self._cache[clave] = funcion()
        return self._cache[clave]

    def _resumenes(self):
        """{ID de losa: resumen} de las losas del modelo 3D (modelo/losas.resumen)."""
        return self._calculado("resumenes", lambda: resumenes_losas(self._modelo_real()))

    def _cargas_losas(self):
        """{ID de caso: {ID de barra: w}}: la carga de las losas sobre sus vigas (vacío si no se puede armar)."""
        def calcular():
            try:
                return ml.cargas_a_vigas(self._modelo_real())
            except ValueError:
                return {}
        return self._calculado("cargas", calcular)

    def _diseno(self, lid):
        """El DisenoLosa de la losa (Comprobaciones), calculado una vez por cambio del modelo."""
        return self._calculado(("diseno", lid), lambda: disenar_losa(self._modelo_real(), lid))

    def _losa_de(self, item):
        """(modelo 3D, ID de losa) que se revisa en Comprobaciones: la del sistema a la vista, o la de la
        losa o el paño elegidos; None si no hay."""
        if self.sistema is not None:
            return self._principal, self.sistema[0]
        modelo = self.modelo
        if not item or not getattr(modelo, "losas", None):
            return None
        if item[0] == "losa" and item[1] in modelo.losas:
            return modelo, item[1]
        if item[0] == "pano":
            lid = modelo.losa_de_pano(item[1])
            return (modelo, lid) if lid is not None else None
        return None

    def _combinacion_a_la_vista(self):
        """Clave de la combinación que se ve (Σ y la lista Combinación), o None con un caso o la envolvente."""
        if not self.modo_combinaciones or self.viendo_envolvente():
            return None
        return self.combinacion_activa()

    def _puntos_columna(self, eid):
        """Puntos Pu–Mu de la columna eid para el diagrama de interacción: los dos extremos, en cada
        combinación de la norma que aplica al modelo (comb.aplicables) y en la que está a la vista, si
        no es una de esas (una propia, o una de la norma sin su carga principal), para que siempre se
        pueda ver en rojo. Las combinaciones se suman una vez y se guardan con las demás (hasta que
        cambie el análisis, SDS o ρ)."""
        lista = dict(comb.aplicables(self.modelo))
        activa = self._combinacion_a_la_vista()
        if activa is not None and activa not in lista:
            lista[activa] = comb.todas(self.modelo)[activa]
        combinados = {}
        for clave, co in lista.items():
            if clave not in self._combinados:
                self._combinados[clave] = combinar(self.modelo, self.resultados, co)
            combinados[clave] = self._combinados[clave]
        return demandas_columna(self.modelo, combinados, eid)

    def _refrescar_diagrama(self):
        """El panel Diagrama: la barra seleccionada (o la de la carga elegida), con el caso o la
        combinación activos y el resultado prendido arriba. Si el panel está cerrado no se calcula."""
        if not hasattr(self, "diagrama") or not self.diagrama.isVisible():
            return
        elegido = self._en_3d(self.seleccion)
        eid = elegido[1] if elegido and elegido[0] == "barra" else None
        env = self._env()
        if env is not None:
            self.diagrama.mostrar_envolvente(self.modelo, env, eid, self.resultado_visible)
        else:
            self.diagrama.mostrar(self.modelo, self._rc(), eid, self.resultado_visible)

    def _tipo_apoyo(self, tipo):
        self.herramienta_apoyo.tipo = tipo

    def _seccion_a_asignar(self, sid):
        self.herramienta_asignar.seccion = sid

    def _ver_en_propiedades(self, item):
        """Después de guardar o eliminar en Propiedades: lo que debe quedar a la vista."""
        self.seleccion = None
        self._en_propiedades = item

    def _menu_definir(self, info, posicion):
        menu = menu_definir(self, info, self.modelo, self.destino)
        if menu is not None:
            menu.exec(posicion)

    def abrir_definir(self, tipo="material"):
        """La ventana de Materiales o la de Secciones (una de cada una)."""
        dialogo = self._dialogos_definir.get(tipo)
        if dialogo is None:
            dialogo = self._dialogos_definir[tipo] = DialogoDefinir(self, tipo)
        dialogo.actualizar()
        dialogo.show()
        dialogo.raise_()
        dialogo.activateWindow()
        return dialogo

    def abrir_casos(self):
        """Definir → Casos de carga (con Aceptar, un paso de Deshacer)."""
        DialogoCasos(self).exec()

    def abrir_combinaciones(self):
        """Definir → Combinaciones de carga (con Aceptar, un paso de Deshacer)."""
        DialogoCombinaciones(self).exec()

    def _elegido_en_explorador(self, item):
        tipo, ident = item
        if tipo in ("nodo", "apoyo", "barra", "carga", "losa", "pano"):
            self.seleccionar(item)
        elif tipo == "matriz":
            self.seleccionar(("barra", ident))
            self.ventana_matriz.mostrar(self.modelo, ident)
        elif tipo in ("seccion", "material"):
            self.seleccionar(None)
            self._marcar_uso(item)
            self._mostrar_propiedades(item)

    def _marcar_uso(self, item):
        """Las barras que usan la sección o el material elegidos se pintan en gris oscuro, como lo
        seleccionado. Se quitan al seleccionar otra cosa o al cambiar el modelo."""
        tipo, ident = item
        if tipo == "seccion" and ident in self.modelo.secciones:
            barras = cc.uso_seccion(self.modelo, ident)
        elif tipo == "material" and ident in self.modelo.materiales:
            barras = cc.uso_material(self.modelo, ident)[0]
        else:
            barras = []
        self.marcados = [("barra", eid) for eid in barras]
        self.pintar()

    def ver_diagrama(self, sid, modo):
        """Abre la ventana del diagrama de interacción (2D o 3D) de la sección sid."""
        sec = self.modelo.secciones.get(sid)
        if sec is None or sec.concreto is None:
            return None
        try:
            ventana = VentanaDiagrama(sec, modo, self)
        except ValueError as e:
            QMessageBox.warning(self, "Diagrama de interacción", f"No se pudo calcular:\n\n{e}")
            return None
        ventana.setAttribute(Qt.WA_DeleteOnClose)
        self.diagramas.append(ventana)
        ventana.destroyed.connect(lambda *_, v=ventana: self.diagramas.remove(v) if v in self.diagramas else None)
        ventana.show()
        return ventana

    # ---------- Menús y barra de arriba ----------
    def _crear_menus(self):
        menu = self.menuBar().addMenu("Archivo")
        for texto, atajo, funcion in (("Nuevo", "Ctrl+N", self.nuevo),
                                      ("Abrir…", "Ctrl+O", self.abrir),
                                      ("Guardar", "Ctrl+S", self.guardar),
                                      ("Guardar como…", "Ctrl+Shift+S", self.guardar_como)):
            accion = menu.addAction(texto)
            accion.setShortcut(QKeySequence(atajo))
            accion.triggered.connect(lambda *_, f=funcion: f())

        editar = self.menuBar().addMenu("Editar")
        self.accion_deshacer = self._accion("deshacer", "Deshacer", "Deshacer (Ctrl+Z)", atajo="Ctrl+Z")
        self.accion_rehacer = self._accion("rehacer", "Rehacer", "Rehacer (Ctrl+Y)", atajo="Ctrl+Y")
        self.accion_eliminar = QAction("Eliminar", self)
        self.accion_eliminar.setShortcut(QKeySequence(Qt.Key_Delete))
        self.accion_deshacer.triggered.connect(self.deshacer)
        self.accion_rehacer.triggered.connect(self.rehacer)
        self.accion_eliminar.triggered.connect(self.eliminar)
        for accion in (self.accion_deshacer, self.accion_rehacer):
            editar.addAction(accion)
        self.addAction(self.accion_eliminar)      # no está en el menú, pero Supr sigue borrando

        ver = MenuPersistente("Ver", self)                  # no se cierra al prender o apagar un panel
        self.menuBar().addMenu(ver)
        ver.addAction(self.explorador.toggleViewAction())
        ver.addAction(self.propiedades.toggleViewAction())
        ver.addAction(self.diagrama.toggleViewAction())

        definir = self.menuBar().addMenu("Definir")         # etapas 1 y 3 de la hoja de ruta
        definir.setToolTipsVisible(True)
        self.accion_material = self._accion("material", "Materiales…", "Materiales de concreto: crear, editar y eliminar")
        self.accion_seccion = self._accion("seccion", "Secciones…", "Secciones de concreto: crear, editar y eliminar")
        self.accion_material.triggered.connect(lambda *_: self.abrir_definir("material"))
        self.accion_seccion.triggered.connect(lambda *_: self.abrir_definir("seccion"))
        self.accion_casos = QAction("Casos de carga…", self)
        self.accion_casos.setToolTip("Casos de carga: peso propio, carga muerta adicional y los que agregues "
                                     "(viva, muerta, viento o sismo)")
        self.accion_casos.triggered.connect(lambda *_: self.abrir_casos())
        self.accion_combinaciones = QAction("Combinaciones de carga…", self)
        self.accion_combinaciones.setToolTip("Combinaciones: las predeterminadas (ASCE 7-05), SDS y ρ, y las "
                                             "tuyas. Solo para ver resultados")
        self.accion_combinaciones.triggered.connect(lambda *_: self.abrir_combinaciones())
        for accion in (self.accion_material, self.accion_seccion):
            definir.addAction(accion)
        definir.addSeparator()
        for accion in (self.accion_casos, self.accion_combinaciones):
            definir.addAction(accion)

        self.accion_configuracion = self.menuBar().addAction("Configuración")
        self.accion_configuracion.triggered.connect(self.abrir_configuracion)

    def _crear_barra_definir(self):
        self.barra_definir = QToolBar("Barra de arriba", self)
        self.barra_definir.setObjectName("definir")
        self.barra_definir.setMovable(False)
        self.barra_definir.setFloatable(False)
        self.barra_definir.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        self.barra_definir.addAction(self.accion_deshacer)
        self.barra_definir.addAction(self.accion_rehacer)
        self.barra_definir.addSeparator()
        # Sistema: el modelo 3D o un sistema de vigueta de una losa (la vigueta continua de una franja)
        self.etiqueta_sistema = QLabel(" Sistema ")
        self.barra_definir.addWidget(self.etiqueta_sistema)
        self.selector_sistema = Lista()
        self.selector_sistema.setToolTip(
            "Qué se ve y se analiza: el modelo 3D, o un sistema de vigueta de una losa (la vigueta continua de "
            "una franja, con apoyos simples en las vigas y sus casos de viva). Los sistemas los arman solas las "
            "losas; no se editan: se ven y se analizan")
        self.selector_sistema.currentIndexChanged.connect(self._cambio_sistema)
        self.barra_definir.addWidget(self.selector_sistema)
        self.barra_definir.addSeparator()
        # Caso, Σ (ver una combinación) y Combinación; lo que no se usa queda en gris
        self.etiqueta_caso = QLabel(" Caso ")
        self.barra_definir.addWidget(self.etiqueta_caso)
        self.selector_caso = Lista()               # abre hacia abajo; el caso vigente, sombreado
        self.selector_caso.setToolTip("Caso de carga. Editando: las cargas nuevas van a este caso y se ven las "
                                      "suyas. Con resultados: se ven los de este caso")
        self.selector_caso.currentIndexChanged.connect(self._cambio_caso)
        self.barra_definir.addWidget(self.selector_caso)
        self.accion_ver_combinaciones = self._accion(
            "combinaciones", "Combinaciones",
            "Σ: ver los resultados de una combinación en vez de los de un caso (disponible con resultados "
            "a la vista). Se definen en Definir → Combinaciones de carga", activable=True)
        self.accion_ver_combinaciones.triggered.connect(self._cambio_fuente)
        self.barra_definir.addAction(self.accion_ver_combinaciones)
        self.etiqueta_combinacion = QLabel(" Combinación ")
        self.barra_definir.addWidget(self.etiqueta_combinacion)
        self.selector_combinacion = ListaDosColumnas(("Diseño", "Servicio"))
        self.selector_combinacion.setToolTip("Combinación cuyos resultados se muestran (con Σ marcado): a la "
                                             "izquierda las de diseño (resistencia), a la derecha las de servicio")
        self.selector_combinacion.currentIndexChanged.connect(self._cambio_combinacion)
        self.barra_definir.addWidget(self.selector_combinacion)
        self.barra_definir.addSeparator()
        self.accion_analizar = self._accion("analizar", "Analizar",
                                            "Analizar (▶): resuelve todos los casos y pasa a ver los resultados. "
                                            "Otro clic aquí vuelve a editar", activable=True)
        self.accion_analizar.triggered.connect(self._alternar_resultados)
        self.barra_definir.addAction(self.accion_analizar)
        self.barra_definir.addSeparator()
        # Resultados: uno a la vez (otro clic sobre el activo lo apaga). Los desplazamientos van en
        # ejes globales; las fuerzas internas, en los locales de cada barra
        self.botones_resultado = {}
        for clave, icono_, texto, opciones in (
                ("deformada", "deformada", "Deformada",
                 (("deformada", "Total: la deformada completa"),
                  ("Dx", "Δx: solo el desplazamiento en X global"),
                  ("Dy", "Δy: solo el desplazamiento en Y global"),
                  ("Dz", "Δz: solo el desplazamiento en Z global"))),
                ("N", "axial", "Axial (N): a lo largo de x local; tracción +", None),
                ("V", "cortante", "Cortante", (("Vy", "Vy: en el plano x–y local"), ("Vz", "Vz: en el plano x–z local"))),
                ("M", "momento", "Momento", (("My", "My: alrededor de y local (flexión en x–z)"),
                                              ("Mz", "Mz: alrededor de z local (flexión en x–y)"))),
                ("T", "torsion", "Torsión (T): alrededor de x local", None)):
            boton = QToolButton()
            boton.setIcon(icono(icono_))
            boton.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
            boton.setCheckable(True)
            boton.setEnabled(False)
            if opciones:
                boton.setToolTip(f"{texto}: elige " + ("qué ver" if clave == "deformada" else "el eje"))
                boton.setPopupMode(QToolButton.InstantPopup)
                menu = QMenu(boton)
                for componente, descripcion in opciones:
                    accion = menu.addAction(descripcion)
                    accion.triggered.connect(lambda *_, c=componente: self.ver_resultado(c))
                if clave == "deformada":
                    self._opciones_escala(menu)
                boton.setMenu(menu)
            else:
                boton.setToolTip(texto)
                boton.clicked.connect(lambda *_, c=clave: self.ver_resultado(c))
            self.barra_definir.addWidget(boton)
            self.botones_resultado[clave] = boton
        # Medir, a la derecha (decisión del usuario): no cambia el modelo y sirve en todos los estados
        espacio = QWidget()
        espacio.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.barra_definir.addWidget(espacio)
        self.accion_medir = self._accion(
            "medir", "Medir", "Medir: distancia entre dos puntos, con snap a nodos, esquinas, puntos medios, la "
            "perpendicular (la distancia libre entre caras de vigas) y los ejes. Dos clics; Esc la borra",
            activable=True)
        self.accion_medir.toggled.connect(self._cambio_medir)
        self.barra_definir.addAction(self.accion_medir)
        self.addToolBar(Qt.TopToolBarArea, self.barra_definir)
        self._llenar_sistemas()
        self._llenar_casos()
        self._llenar_combinaciones()

    def _opciones_escala(self, menu):
        """La escala de la deformada, al final del menú Deformada ▾ (es donde se usa): automática (el
        desplazamiento mayor mide una fracción del modelo), el tamaño real (×1) u otra escala fija. Es
        lo mismo que Configuración → Vista, y se guarda en las preferencias."""
        menu.addSeparator()
        self.accion_escala_automatica = menu.addAction("Escala automática")
        self.accion_escala_automatica.setCheckable(True)
        self.accion_escala_automatica.setChecked(ui.DEFORMADA_AUTOMATICA)
        self.accion_escala_automatica.setToolTip("El desplazamiento mayor mide una fracción fija del modelo")
        self.accion_escala_automatica.triggered.connect(lambda marcada: self._poner_escala(bool(marcada), None))
        menu.addAction("Tamaño real (×1)").triggered.connect(lambda *_: self._poner_escala(False, 1.0))
        menu.addAction("Otra escala fija…").triggered.connect(self._pedir_escala)
        menu.setToolTipsVisible(True)
        menu.aboutToShow.connect(lambda: self.accion_escala_automatica.setChecked(ui.DEFORMADA_AUTOMATICA))

    def _pedir_escala(self, *_):
        from PySide6.QtWidgets import QInputDialog
        factor, ok = QInputDialog.getDouble(self, "Escala de la deformada",
                                            "Factor que multiplica los desplazamientos reales (1 = tamaño real):",
                                            ui.FACTOR_DEFORMADA, 0.01, 1e7, 2)
        if ok:
            self._poner_escala(False, factor)

    def _poner_escala(self, automatica, factor):
        """Cambia la escala de la deformada (automática o un factor fijo), la guarda en las
        preferencias y redibuja. factor None: no cambia el factor fijo."""
        from configuracion import preferencias
        ui.DEFORMADA_AUTOMATICA = automatica
        if factor is not None:
            ui.FACTOR_DEFORMADA = float(factor)
        try:
            preferencias.guardar()
        except OSError as e:
            self.mensaje(f"No se pudieron guardar las preferencias: {e}")
        if self.resultado_visible not in DEFORMADAS and self.modo_resultados and not self.viendo_envolvente():
            self.ver_resultado("deformada")
            return
        self.redibujar()
        self._aviso_deformada()

    # ---------- Casos, combinaciones, análisis y los tres estados ----------
    @property
    def modo_combinaciones(self):
        """True si lo que se ve son los resultados de una combinación (estado 3)."""
        return self.modo_resultados and self.ver_combinaciones

    def _llenar_casos(self):
        """La lista Caso, con el modelo vigente. Si lo elegido ya no existe, queda el caso inicial
        (Carga muerta adicional), que es donde van las cargas. En un sistema de vigueta: el peso propio,
        la muerta adicional y sus casos de viva (no las vivas por claro, que son internas)."""
        actual = self.selector_caso.currentData()
        self.selector_caso.blockSignals(True)
        self.selector_caso.clear()
        # Los fijos primero (Peso propio, Carga muerta adicional y Carga viva), y luego los del usuario
        orden = sorted(self.modelo.casos, key=lambda c: not self.modelo.es_fijo(c))
        for cid in orden:
            caso = self.modelo.casos[cid]
            if self._sv is not None and self._sv.es_caso_interno(cid):
                continue
            self.selector_caso.addItem(f"{caso.nombre} ({caso.tipo})", cid)
        i = self.selector_caso.findData(actual)
        if i < 0:
            i = self.selector_caso.findData(self.modelo.caso_inicial())
        self.selector_caso.setCurrentIndex(max(i, 0))
        self.selector_caso.blockSignals(False)

    def _llenar_sistemas(self):
        """La lista Sistema: el modelo 3D y, por cada losa, sus franjas (los sistemas de vigueta)."""
        lista = self.selector_sistema
        lista.blockSignals(True)
        lista.clear()
        lista.addItem("Modelo 3D", None)
        principal = self._modelo_real()
        for lid, r in self._resumenes().items():
            for f in r.get("franjas", []):
                lista.addItem(f"{principal.losas[lid].nombre} · {f.nombre}", (lid, f.letra))
                lista.setItemData(lista.count() - 1, "Claros " + ", ".join(f"{c:.2f}" for c in f.claros) + " m",
                                  Qt.ToolTipRole)
        # findData de Qt no compara bien las tuplas de Python: se busca a mano
        datos = [lista.itemData(k) for k in range(lista.count())]
        i = next((k for k, d in enumerate(datos) if d is not None and tuple(d) == self.sistema), 0)
        lista.setCurrentIndex(i)
        lista.blockSignals(False)
        lista.setEnabled(lista.count() > 1)
        self.etiqueta_sistema.setEnabled(lista.count() > 1)

    def _cambio_sistema(self, *_):
        clave = self.selector_sistema.currentData()
        clave = tuple(clave) if clave is not None else None
        if clave == self.sistema:
            return
        if clave is None:
            self.salir_de_sistema()
        else:
            self.abrir_sistema(clave)

    def abrir_sistema(self, clave):
        """Muestra el sistema de vigueta (ID de losa, letra de la franja): su modelo generado, con un caso
        por cada caso de viva. Se ve y se analiza; no se edita (la vigueta se cambia en Comprobaciones)."""
        clave = tuple(clave)
        principal = self._modelo_real()
        try:
            losa = principal.losas[clave[0]]
            geos = ml.geometrias(principal, losa)
            franja = next(f for f in ml.franjas(principal, losa, geos) if f.letra == clave[1])
            sv = ml.sistema(principal, clave[0], franja, geos, con_patrones=True)
        except (KeyError, StopIteration, ValueError) as e:
            self.mensaje(f"No se puede abrir ese sistema: {e}")
            self._llenar_sistemas()
            return
        if self.modo_resultados:
            self.salir_de_resultados()
        self.herramienta.cancelar()
        self.usar_herramienta(self._por_nombre["seleccionar"][1])
        if self._principal is None:                     # se entra desde el modelo 3D: se guardan sus resultados
            self._principal, self._resultados_principal = self.modelo, self.resultados
        self.modelo, self._sv, self.sistema = sv.modelo, sv, clave
        self.resultados, self._combinados = None, {}
        self.seleccion = self.resaltado = self._en_propiedades = None
        self.marcados = []
        self._llenar_sistemas()
        self._llenar_casos()
        self._llenar_combinaciones()
        self._actualizar_modo()
        self._actualizar_deshacer()
        self.redibujar(reiniciar_camara=True)
        self._refrescar_paneles()
        self.mensaje(f"{losa.nombre} · {franja.nombre}: la vigueta con apoyos simples en las vigas. ▶ la analiza; "
                     "la lista Caso tiene sus casos de viva. Comprobaciones, a la derecha")

    def salir_de_sistema(self, redibujar=True):
        """Vuelve al modelo 3D (con sus resultados, si seguían vigentes)."""
        if self.sistema is None:
            return
        if self.modo_resultados:
            self.salir_de_resultados()
        self.modelo, self.resultados = self._principal, self._resultados_principal
        self._principal = self._resultados_principal = self._sv = self.sistema = None
        self._combinados = {}
        self.seleccion = self.resaltado = self._en_propiedades = None
        if redibujar:
            self._llenar_sistemas()
            self._llenar_casos()
            self._llenar_combinaciones()
            self._actualizar_modo()
            self._actualizar_deshacer()
            self.redibujar(reiniciar_camara=True)
            self._refrescar_paneles()
            self.mensaje("Modelo 3D")

    def _patron_activo(self):
        """En un sistema: el índice del caso de viva elegido en la lista Caso (si se eligió uno de D, el
        primero: todos los claros cargados)."""
        caso = self.caso_activo()
        for i, cid in self._sv.casos_patron.items():
            if cid == caso:
                return i
        return 0

    def _llenar_combinaciones(self):
        """La lista Combinación, en dos columnas. Diseño: la carga muerta, las 13 de resistencia (con el
        SDS y el ρ del modelo), las propias y la envolvente de diseño. Servicio: las 4 de servicio y su
        envolvente, de donde sale Ma (el momento de servicio de las deflexiones)."""
        lista = self.selector_combinacion
        actual = lista.currentData()
        lista.blockSignals(True)
        lista.clear()
        for clave, co in comb.todas(self.modelo).items():
            columna = SERVICIO if comb.es_servicio(clave) else DISENO
            lista.agregar(co.nombre, clave, columna, comb.referencia(clave) if comb.es_predeterminada(clave) else None)
        # Las envolventes, al final de cada columna: máximos y mínimos (solo fuerzas internas)
        lista.agregar("Envolvente de diseño", ENVOLVENTE, DISENO,
                      "Máximo y mínimo de cada fuerza entre las 13 combinaciones de resistencia de ASCE 7-05 (sin "
                      "las de servicio, las propias ni la carga muerta). Solo fuerzas internas: sin deformada ni "
                      "reacciones")
        lista.agregar("Envolvente de servicio", ENVOLVENTE_SERVICIO, SERVICIO,
                      "Máximo y mínimo de cada fuerza entre las 4 combinaciones de servicio (sin mayorar). De aquí "
                      "sale Ma, el momento de servicio de las deflexiones (ACI 318-19 Tabla 24.2.3.5). Solo fuerzas "
                      "internas: sin deformada ni reacciones")
        i = lista.findData(actual)
        lista.setCurrentIndex(max(i, 0))
        lista.blockSignals(False)

    def caso_activo(self):
        caso = self.selector_caso.currentData()
        return caso if caso in self.modelo.casos else self.modelo.caso_inicial()

    def combinacion_activa(self):
        """Clave de la combinación elegida ("D", "C1", "C3a"… o el ID de una propia), o None."""
        clave = self.selector_combinacion.currentData()
        return clave if clave in ENVOLVENTES or clave in comb.todas(self.modelo) else None

    def viendo_envolvente(self):
        """True si lo que se ve son los resultados de una envolvente (de diseño o de servicio)."""
        return self.modo_combinaciones and self.combinacion_activa() in ENVOLVENTES

    def _cambio_caso(self, *_):
        self.redibujar()
        self._refrescar_paneles()
        caso = self.modelo.casos.get(self.caso_activo())
        if not self.modo_resultados and self.sistema is None and caso is not None and caso.viva_losas:
            self.mensaje("Carga viva: la viva de las losas llega sola (todos los paños cargados; se escribe en "
                         "cada paño). Aquí también van las vivas que pongas a mano")
        elif not self.modo_resultados and self.sistema is None and self.modelo.es_automatico(self.caso_activo()):
            self.mensaje("Peso propio: automático (A·γ de cada barra y el de las losas). Las cargas a mano van en "
                         "otro caso")
        else:
            self._aviso_deformada()

    def _cambio_combinacion(self, *_):
        if self.modo_combinaciones:
            self._ajustar_a_envolvente()
            self._actualizar_modo()
            self._cambio_caso()

    def _ajustar_a_envolvente(self):
        """La envolvente no tiene deformada: si estaba a la vista (o nada), se pasa al momento My."""
        if self.viendo_envolvente() and (self.resultado_visible is None or self.resultado_visible in DEFORMADAS):
            self.resultado_visible = "My"
            self._ultimo_resultado = "My"

    def _cambio_fuente(self, marcado):
        """Σ: se ven los resultados de una combinación (marcado) o los de un caso."""
        self.ver_combinaciones = bool(marcado)
        self._ajustar_a_envolvente()
        self._actualizar_modo()
        self.redibujar()
        self._refrescar_paneles()
        self._aviso_deformada("Resultados de la combinación. " if self.modo_combinaciones
                              else "Resultados del caso. ")

    def _actualizar_modo(self):
        """Aplica el estado vigente (ver la tabla del principio): habilita lo que se usa en él y deja
        en gris lo demás."""
        resultados, combos = self.modo_resultados, self.modo_combinaciones
        en_sistema = self.sistema is not None
        self.accion_analizar.setChecked(resultados)
        self.accion_ver_combinaciones.setEnabled(resultados)
        self.accion_ver_combinaciones.setChecked(combos)
        # En un sistema de vigueta, con Σ la lista Caso elige el caso de viva de la combinación
        for widget in (self.etiqueta_caso, self.selector_caso):
            widget.setEnabled(not combos or en_sistema)
        for widget in (self.etiqueta_combinacion, self.selector_combinacion):
            widget.setEnabled(combos)
        self._actualizar_resultados()
        self.accion_cargas.setEnabled(not resultados)        # las cargas se ven al editar
        self.accion_reacciones.setEnabled(resultados and not self.viendo_envolvente())   # sin envolvente
        # Herramientas: con resultados quedan todas en gris, también Seleccionar (el clic sobre un
        # nodo o una barra sigue seleccionando: es la herramienta activa, aunque su botón no se
        # pueda tocar). En el caso automático (peso propio) no se ponen cargas a
        # mano. Un sistema de vigueta no se edita: como con resultados
        automatico = self.modelo.es_automatico(self.caso_activo())
        for nombre, (accion, _h) in self._por_nombre.items():
            accion.setEnabled(not resultados and not en_sistema
                              and not (automatico and nombre in HERRAMIENTAS_DE_CARGA))
        for accion in (self.accion_material, self.accion_seccion, self.accion_casos, self.accion_combinaciones):
            accion.setEnabled(not en_sistema)
        actual = next(accion for accion, h in self._herramientas if h is self.herramienta)
        if not actual.isEnabled():
            self.usar_herramienta(self._por_nombre["seleccionar"][1])

    def _rc(self):
        """Resultados que se muestran: los de la combinación (con Σ) o los del caso elegido. None si
        se está editando o no hay análisis vigente."""
        if not self.modo_resultados or not self.resultados:
            return None
        if self.ver_combinaciones:
            clave = self.combinacion_activa()
            if clave is None or clave in ENVOLVENTES:
                return None
            if self._sv is not None:                    # en un sistema: con el caso de viva elegido
                i = self._patron_activo()
                guardada = (clave, "caso de viva", i)
                if guardada not in self._combinados:
                    co = comb.todas(self.modelo)[clave]
                    rc = combinar(self.modelo, self.resultados, co, self._sv.casos_vista(i))
                    rc.nombre = f"{co.nombre} con {self._sv.patrones[i][0]}"
                    self._combinados[guardada] = rc
                return self._combinados[guardada]
            if clave not in self._combinados:
                self._combinados[clave] = combinar(self.modelo, self.resultados, comb.todas(self.modelo)[clave])
            return self._combinados[clave]
        return self.resultados.get(self.caso_activo())

    def _env(self):
        """La envolvente que se ve (de diseño: las 13 de resistencia; de servicio: las 4 de servicio),
        o None. Se calcula la primera vez y se guarda con las combinaciones, hasta que cambie el
        análisis o SDS y ρ."""
        if not self.modo_resultados or not self.resultados or not self.viendo_envolvente():
            return None
        clave = self.combinacion_activa()
        if clave not in self._combinados:
            if clave == ENVOLVENTE:
                combos, nombre = comb.aplicables(self.modelo), "Envolvente de diseño"
            else:
                combos, nombre = comb.servicio(), "Envolvente de servicio"
            if self._sv is not None:                    # en un sistema: todas × todos sus casos de viva
                nombre += " (todos los casos de viva)"
                combos = {(c, i): (f"{co.nombre} · {self._sv.patrones[i][0]}", co, self._sv.casos_vista(i))
                          for c, co in combos.items() for i in self._sv.casos_patron}
            env = envolvente(self.modelo, self.resultados, combos)
            env.nombre = nombre
            self._combinados[clave] = env
        return self._combinados[clave]

    def _alternar_resultados(self, marcado):
        """▶: entra a los resultados (analizando si hace falta) o vuelve a editar."""
        if marcado:
            self.analizar()
        else:
            self.salir_de_resultados()

    def analizar(self):
        """Resuelve todos los casos (si el análisis vigente ya no sirve) y pasa a ver resultados: lo
        último que se vio, o la deformada."""
        if self.resultados is None:
            try:
                self.resultados = analizar(self.modelo)
            except (ValueError, KeyError) as e:
                self.resultados = None
                QMessageBox.warning(self, "Analizar", f"No se pudo analizar:\n\n{e}")
                self._actualizar_modo()            # ▶ vuelve a quedar sin marcar
                return
            self._combinados = {}
        if not self.modo_resultados:
            # Los resultados se leen mejor sobre las barras como líneas: la sección real se apaga
            # sola (se puede volver a prender a mano) y al volver a Editar queda como estaba
            self._seccion_real_antes = self.accion_seccion_real.isChecked()
            self._poner_seccion_real(False)
        self.modo_resultados = True
        self.resultado_visible = self._ultimo_resultado
        self.redibujar()
        self._refrescar_paneles()
        self._aviso_deformada("Análisis listo. ")

    def salir_de_resultados(self, *_):
        """Vuelve a Editar (otro clic en ▶). El análisis sigue vigente mientras el modelo no cambie:
        ▶ lo vuelve a mostrar sin recalcular."""
        if not self.modo_resultados:
            return
        self._ultimo_resultado = self.resultado_visible or self._ultimo_resultado
        self.modo_resultados = False
        self.resultado_visible = None
        self._restaurar_seccion_real()
        self.redibujar()
        self._refrescar_paneles()
        self.mensaje("Editar. Para ver los resultados otra vez: ▶")

    def _invalidar_resultados(self):
        """El modelo cambió: los resultados ya no valen. Se vuelve a Editar (hay que analizar de
        nuevo). Quien llama pone después los botones al día (_actualizar_modo)."""
        if self.resultados is not None:
            self.mensaje("El modelo cambió: vuelve a analizar (▶)")
        self.resultados = None
        self._combinados = {}
        self._ultimo_resultado = self.resultado_visible or self._ultimo_resultado
        self.modo_resultados = False
        self.resultado_visible = None
        self._restaurar_seccion_real()

    def ver_resultado(self, componente):
        """Muestra la deformada o un diagrama; otro clic sobre el mismo lo apaga."""
        self.resultado_visible = None if componente == self.resultado_visible else componente
        self._ultimo_resultado = self.resultado_visible or self._ultimo_resultado
        self._actualizar_resultados()
        self.redibujar()
        self._mostrar_propiedades(self._en_propiedades)
        self._aviso_deformada()

    def _aviso_deformada(self, antes=""):
        """Aviso: `antes` y, con la deformada a la vista, cuánto se amplificaron los desplazamientos
        (×1 sería el tamaño real). Si se pidió una sola componente y es cero, lo dice."""
        if self.resultado_visible in DEFORMADAS and self._rc() is not None:
            cual = NOMBRE_DEFORMADA[self.resultado_visible]
            if self.factor_deformada is None:
                self.mensaje(f"{antes}Deformada {cual}: sin desplazamientos"
                             + (" en esa dirección" if self.resultado_visible != "deformada" else ""))
            else:
                tipo = "automática" if ui.DEFORMADA_AUTOMATICA else "fija"
                self.mensaje(f"{antes}Deformada {cual} ×{_factor_texto(self.factor_deformada)} "
                             f"({tipo}; 1 = tamaño real), con la inercia bruta Ig")
        elif antes:
            self.mensaje(antes.strip())

    def _actualizar_resultados(self):
        """Los botones de resultados: habilitados con resultados a la vista y marcado el que se ve."""
        grupo = {"N": "N", "Vy": "V", "Vz": "V", "T": "T", "My": "M", "Mz": "M", **dict.fromkeys(DEFORMADAS, "deformada")}
        activo = grupo.get(self.resultado_visible)
        for clave, boton in self.botones_resultado.items():
            # la envolvente es de fuerzas internas: sin deformada
            boton.setEnabled(self.modo_resultados and not (clave == "deformada" and self.viendo_envolvente()))
            boton.setChecked(clave == activo)

    # ---------- Herramientas (izquierda) ----------
    def _crear_herramientas(self):
        self.herramientas = QToolBar("Herramientas", self)
        self.herramientas.setObjectName("herramientas")   # la hoja de estilo le pone un borde
        self.herramientas.setMovable(False)
        self.herramientas.setFloatable(False)
        self.herramientas.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        self.addToolBar(Qt.LeftToolBarArea, self.herramientas)

        grupo = QActionGroup(self)                 # una sola herramienta activa a la vez
        self._herramientas = []                    # (acción, herramienta)
        self._por_nombre = {}                      # nombre -> (acción, herramienta)
        for nombre, texto, ayuda, clase in (
                ("seleccionar", "Seleccionar", "Seleccionar: clic sobre un nodo, un apoyo o una barra", Seleccionar),
                ("nodo", "Nodo", "Agregar nodo: clic sobre un punto de la rejilla o escribe x, y, z", AgregarNodo),
                ("elemento", "Elemento", "Agregar elemento: clic en el punto inicial y en el final "
                 "(queda sin sección)", AgregarElemento),
                ("asignar_seccion", "Asignar sección", "Asignar sección: elige la sección en Propiedades y "
                 "haz clic sobre cada barra (lleva también su material)", AsignarSeccion),
                ("apoyo", "Apoyo", "Apoyo: elige el tipo en Propiedades y haz clic sobre un nodo",
                 AgregarApoyo),
                ("losa", "Agregar losa", "Agregar losa de viguetas: elige la losa, la vigueta y las cargas en "
                 "Propiedades; clic en la primera viga de apoyo y en la de enfrente", AgregarLosa),
                ("carga_nodo", "Carga en nodo", "Carga en nodo: escribe los valores en Propiedades y haz clic "
                 "sobre un nodo", AgregarCargaNodo),
                ("carga_barra", "Carga en barra", "Carga en barra: elige el tipo y el valor en Propiedades y "
                 "haz clic sobre una barra", AgregarCargaBarra)):
            accion = self._accion(nombre, texto, ayuda, activable=True)
            herramienta = clase(self)
            accion.triggered.connect(lambda *_, h=herramienta: self.usar_herramienta(h))
            grupo.addAction(accion)
            self.herramientas.addAction(accion)
            self._herramientas.append((accion, herramienta))
            self._por_nombre[nombre] = (accion, herramienta)
        self.accion_seleccionar, self.herramienta = self._por_nombre["seleccionar"]
        self.herramienta_apoyo = self._por_nombre["apoyo"][1]
        self.herramienta_asignar = self._por_nombre["asignar_seccion"][1]
        self.propiedades.panel_apoyo.cambiado.connect(self._tipo_apoyo)
        self.propiedades.panel_asignar.cambiado.connect(self._seccion_a_asignar)
        self.propiedades.panel_asignar.definir.connect(lambda: self.abrir_definir("seccion"))
        self.propiedades.panel_losa.definir.connect(lambda: self.abrir_definir("seccion"))
        self.propiedades.panel_losa.losa.currentIndexChanged.connect(
            lambda *_: setattr(self._por_nombre["losa"][1], "losa", self.propiedades.panel_losa.losa.currentData()))
        self.accion_seleccionar.setChecked(True)   # herramienta por defecto

    def usar_herramienta(self, herramienta):
        """Cambia la herramienta activa (desde su botón o desde el código)."""
        for accion, h in self._herramientas:
            if h is herramienta:
                accion.setChecked(True)
        if herramienta is self.herramienta:
            return
        self.herramienta.cancelar()
        self.herramienta = herramienta
        self.comando.clear()
        self.resaltado = None                      # el resaltado es solo de Seleccionar
        if herramienta.muestra_cargas and not self.accion_cargas.isChecked():
            self.accion_cargas.setChecked(True)    # para ver la carga que se va a poner
        self.pintar()
        self._mostrar_propiedades(self.seleccion)  # el panel de la herramienta, o de nuevo lo seleccionado
        self.actualizar_indicacion()
        self._actualizar_puntero()

    # ---------- Barra de comandos (abajo) ----------
    def _crear_barra_comandos(self):
        self.barra_comandos = QToolBar("Comandos", self)
        self.barra_comandos.setObjectName("barra_comandos")
        self.barra_comandos.setMovable(False)
        self.barra_comandos.setFloatable(False)
        self.comando = QLineEdit()                 # coordenadas exactas; la guía es la plantilla gris
        self.comando.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.comando.returnPressed.connect(self._ejecutar_comando)
        self.comando.textChanged.connect(self._validar_comando)
        self.aviso = QLabel()                      # avisos cortos ("Nodo 6 agregado")
        for widget in (self.comando, self.aviso):
            self.barra_comandos.addWidget(widget)
        self.addToolBar(Qt.BottomToolBarArea, self.barra_comandos)
        self._reloj_aviso = QTimer(self)
        self._reloj_aviso.setSingleShot(True)
        self._reloj_aviso.timeout.connect(self.aviso.clear)

    def actualizar_indicacion(self):
        """Plantilla de la barra de comandos. Solo está activa con Nodo o Elemento."""
        self.comando.setPlaceholderText(self.herramienta.indicacion())
        self.barra_comandos.setEnabled(self.herramienta.usa_previsualizacion)
        self._validar_comando()

    def comando_valido(self, texto=None):
        """True si lo escrito ya es un punto válido (se puede colocar con Enter)."""
        texto = self.comando.text() if texto is None else texto
        if not texto.strip() or self.rejilla is None:
            return False
        try:
            interpretar(texto, self.rejilla, self.herramienta.ultimo_punto())
        except ValueError:
            return False
        return True

    def _validar_comando(self, *_):
        """Gris mientras lo escrito todavía no es un punto válido; negro cuando ya lo es."""
        paleta = self.comando.palette()
        color = colores.INTERFAZ_TEXTO if self.comando_valido() else colores.INTERFAZ_DESHABILITADO
        paleta.setColor(QPalette.Text, QColor(color))
        self.comando.setPalette(paleta)

    def mensaje(self, texto):
        """Aviso corto en la barra de comandos; se borra solo."""
        self.aviso.setText(texto)
        self._reloj_aviso.start(ui.DURACION_MENSAJE_MS)

    def _ejecutar_comando(self):
        texto = self.comando.text().strip()
        if not texto:
            return
        try:
            punto = interpretar(texto, self.rejilla, self.herramienta.ultimo_punto())
        except ValueError as e:
            self.mensaje(str(e))
            self.comando.selectAll()               # lo próximo que se escriba lo reemplaza
            return
        self.comando.clear()
        self.herramienta.punto_escrito(punto)
        self.actualizar_indicacion()
        self._actualizar_puntero()

    def _cambio_medir(self, activa):
        """Medir prendido: los clics miden (no seleccionan ni editan). Apagado: se borra la medición."""
        if activa:
            self.previsualizacion.ocultar()
            self.mensaje("Medir: clic en el primer punto y en el segundo (con snap). Esc borra; otro Esc apaga Medir")
        else:
            self.medicion.cancelar()
            self._actualizar_puntero()

    def cancelar(self):
        """Esc: cancela lo que esté a medias; si no hay nada, vuelve a Seleccionar o deselecciona. Con
        Medir: borra la medición y, si no había, apaga Medir."""
        if self.accion_medir.isChecked():
            if not self.medicion.cancelar():
                self.accion_medir.setChecked(False)
            return
        self.comando.clear()
        seleccionar = self._por_nombre["seleccionar"][1]
        if self.herramienta.cancelar():
            self.mensaje("Cancelado")
        elif self.herramienta is not seleccionar:
            self.usar_herramienta(seleccionar)
        elif self.seleccion is not None:
            self.seleccionar(None)
        self.actualizar_indicacion()
        self._actualizar_puntero()

    def eventFilter(self, objeto, evento):
        if objeto is self.vista and evento.type() == QEvent.Resize and hasattr(self, "cubo"):
            # La vista cambió de tamaño (la ventana, o un panel que se ensancha): el cubo y los ejes
            # vuelven a quedar cuadrados, después de que la vista tome su tamaño
            QTimer.singleShot(0, self._ajustar_y_dibujar)
        if (objeto is self.vista and evento.type() == QEvent.KeyPress and evento.text()
                and evento.text() in TECLAS_A_COMANDOS and self.barra_comandos.isEnabled()
                and not evento.modifiers() & (Qt.ControlModifier | Qt.AltModifier)):
            if not self.comando.hasFocus():
                self.comando.clear()               # escribir sobre la vista empieza un comando nuevo
            self.comando.setFocus()
            self.comando.insert(evento.text())
            return True
        return super().eventFilter(objeto, evento)

    # ---------- Barra inferior: coordenadas y vista ----------
    def _crear_barra_inferior(self):
        barra = QToolBar("Vista", self)
        barra.setObjectName("barra_inferior")
        barra.setMovable(False)
        barra.setFloatable(False)
        tamano = QSize(ui.TAMANO_ICONO_INFERIOR, ui.TAMANO_ICONO_INFERIOR)
        barra.setIconSize(tamano)

        self.accion_rejilla = self._accion("rejilla", "Rejilla", f"Rejilla ({ui.ATAJO_REJILLA})",
                                           activable=True, activa=ui.REJILLA_VISIBLE, atajo=ui.ATAJO_REJILLA)
        self.accion_rejilla.toggled.connect(lambda *_: self._aplicar_visibilidad())
        self.accion_snap = self._accion("snap", "Snap",
                                        f"Snap ({ui.ATAJO_SNAP}): pega el punto a nodos y a la rejilla",
                                        activable=True, activa=ui.SNAP_ACTIVO, atajo=ui.ATAJO_SNAP)
        self.accion_snap.toggled.connect(lambda *_: self._actualizar_puntero())
        self.boton_etiquetas = QToolButton()
        self.boton_etiquetas.setIcon(icono("etiqueta"))
        self.boton_etiquetas.setIconSize(tamano)
        self.boton_etiquetas.setToolTip("Etiquetas: qué textos se ven en el dibujo, y los ejes locales de la "
                                        "barra seleccionada (no con la deformada, que va en ejes globales)")
        self.boton_etiquetas.setPopupMode(QToolButton.InstantPopup)
        menu = MenuPersistente(self.boton_etiquetas)
        self.etiquetas = {}
        for nombre, texto, activa in (("etiquetas", "Números de nodo", ui.ETIQUETAS_VISIBLES),
                                      ("numeros_barras", "Números de barra", False),
                                      ("valores_cargas", "Valores de las cargas", True),
                                      ("valores_resultados", "Valores de los resultados", True),
                                      ("valores_reacciones", "Valores de las reacciones", True),
                                      ("ejes_locales", "Ejes locales de la barra seleccionada",
                                       ui.EJES_LOCALES_VISIBLES)):
            accion = menu.addAction(texto)
            accion.setCheckable(True)
            accion.setChecked(activa)
            accion.toggled.connect(lambda *_: self._aplicar_visibilidad())
            self.etiquetas[nombre] = accion
        self.boton_etiquetas.setMenu(menu)
        self.accion_seccion_real = self._accion("seccion_real", "Sección real",
                                                "Sección real: barras con sus medidas b × h (o como líneas). Al "
                                                "analizar se apaga sola (se puede prender) y vuelve al editar",
                                                activable=True, activa=ui.SECCION_REAL_VISIBLE)
        self.accion_seccion_real.toggled.connect(self._cambio_seccion_real)
        # Transparencia del concreto: un deslizador junto a Sección real (deja ver el acero)
        self.deslizador_transparencia = QSlider(Qt.Horizontal)
        self.deslizador_transparencia.setRange(0, round((1 - ui.OPACIDAD_MINIMA) * 100))
        self.deslizador_transparencia.setFixedWidth(ui.ANCHO_DESLIZADOR_PX)
        self.deslizador_transparencia.setToolTip("Transparencia del concreto: 0 % (opaco)")
        self.deslizador_transparencia.valueChanged.connect(self._cambio_transparencia)
        self.deslizador_transparencia.setEnabled(ui.SECCION_REAL_VISIBLE)
        self.accion_cargas = self._accion("cargas", "Cargas",
                                          "Cargas: muestra u oculta las cargas del caso activo (al editar). La "
                                          "flecha elige cuáles: en nodos y barras, de área o de las losas a las vigas",
                                          activable=True, activa=ui.CARGAS_VISIBLES)
        self.accion_cargas.toggled.connect(lambda *_: self._aplicar_visibilidad())
        # Qué cargas se dibujan (un menú que no se cierra al marcar, como Etiquetas)
        menu_cargas = MenuPersistente(self)
        self.cargas_tipo = {}
        for nombre, texto, ayuda in (
                ("barras", "En nodos y barras", "Las puestas a mano y el peso propio de vigas y columnas"),
                ("areas", "De área (losas)", "La muerta adicional y la viva de cada paño (y el peso de la losa en "
                                             "el caso de peso propio), como una lámina sobre el paño"),
                ("losas", "De las losas a las vigas", "Lo que las losas le pasan a sus vigas: las viguetas a las de "
                                                      "apoyo y la franja de cada lateral (no se guarda)")):
            accion = menu_cargas.addAction(texto)
            accion.setCheckable(True)
            accion.setChecked(True)
            accion.setToolTip(ayuda)
            accion.toggled.connect(lambda *_: self.redibujar())
            self.cargas_tipo[nombre] = accion
        menu_cargas.setToolTipsVisible(True)
        self.accion_cargas.setMenu(menu_cargas)
        self.accion_reacciones = self._accion("reacciones", "Reacciones",
                                              "Reacciones: muestra las reacciones de los apoyos para el caso o la "
                                              "combinación que se ve (con resultados a la vista)",
                                              activable=True, activa=ui.REACCIONES_VISIBLES)
        self.accion_reacciones.toggled.connect(lambda *_: self._aplicar_visibilidad())
        self.accion_encuadre = self._accion("encuadre", "Encuadre", "Encuadre: ajusta la vista al modelo")
        self.accion_encuadre.triggered.connect(self.encuadre)

        barra.addAction(self.accion_rejilla)
        barra.addAction(self.accion_snap)
        barra.addWidget(self.boton_etiquetas)
        barra.addAction(self.accion_seccion_real)
        barra.addWidget(self.deslizador_transparencia)
        barra.addAction(self.accion_cargas)
        boton_cargas = barra.widgetForAction(self.accion_cargas)
        if isinstance(boton_cargas, QToolButton):  # clic: muestra u oculta; la flecha: cuáles
            boton_cargas.setPopupMode(QToolButton.MenuButtonPopup)
        barra.addAction(self.accion_reacciones)
        barra.addSeparator()                       # a la izquierda, estados; a la derecha, una acción
        barra.addAction(self.accion_encuadre)

        estado = self.statusBar()
        estado.setSizeGripEnabled(False)
        self.coordenadas = QLabel()                # posición del puntero
        estado.addWidget(self.coordenadas, 1)
        estado.addPermanentWidget(barra)
        self.barra_inferior = barra

    def _mostrar(self, nombre, visible):
        """Muestra u oculta un actor de la vista ("rejilla", "etiquetas"...), sin redibujar."""
        actor = self.dibujado.actores.get(nombre)
        if actor is not None:
            actor.SetVisibility(visible)

    def _aplicar_visibilidad(self, dibujar=True):
        """Rejilla, etiquetas, cargas y reacciones, según sus botones. Los valores de las cargas y de
        las reacciones se ven solo si se ven sus flechas."""
        cargas, reacciones = self.accion_cargas.isChecked(), self.accion_reacciones.isChecked()
        visibles = {"rejilla": self.accion_rejilla.isChecked(), "reacciones": reacciones}
        visibles.update({nombre: cargas for nombre in ("cargas", "cargas_relleno", "cargas_bordes", "cargas_areas")})
        for nombre, accion in self.etiquetas.items():
            visibles[nombre] = accion.isChecked()
        visibles["valores_cargas"] = visibles["valores_cargas"] and cargas
        visibles["valores_reacciones"] = visibles["valores_reacciones"] and reacciones
        visibles["letras_ejes_locales"] = visibles["ejes_locales"]       # las letras x, y, z, con sus flechas
        for nombre, visible in visibles.items():
            self._mostrar(nombre, visible)
        if dibujar:
            self.vista.render()

    def _cambio_seccion_real(self, activa):
        """Sección real: las barras como cajas b × h o como líneas. La transparencia es de las cajas."""
        self.deslizador_transparencia.setEnabled(bool(activa))
        if not self._cambiando_seccion_real:
            self.redibujar()

    def _poner_seccion_real(self, activa):
        """Prende o apaga Sección real desde el programa (al entrar a los resultados y al salir), sin
        redibujar: lo hace quien llama, una sola vez."""
        self._cambiando_seccion_real = True
        self.accion_seccion_real.setChecked(activa)
        self._cambiando_seccion_real = False

    def _restaurar_seccion_real(self):
        """Al dejar los resultados, Sección real vuelve a como estaba antes de analizar."""
        if self._seccion_real_antes is not None:
            self._poner_seccion_real(self._seccion_real_antes)
            self._seccion_real_antes = None

    def _cambio_transparencia(self, porcentaje):
        """Deslizador: opacidad de las cajas de concreto. No se redibuja: el acero ya está dibujado
        dentro (lo tapa el concreto opaco) y basta cambiar la opacidad. Con depth peeling el acero
        aparece poco a poco, sin saltos."""
        self.opacidad_concreto = 1.0 - porcentaje / 100
        self.deslizador_transparencia.setToolTip(f"Transparencia del concreto: {porcentaje} %"
                                                 + (" (opaco)" if not porcentaje else ""))
        for nombre in ("solidos", "losas"):
            actor = self.dibujado.actores.get(nombre)
            if actor is not None:
                actor.GetProperty().SetOpacity(self.opacidad_concreto)
        self.vista.render()

    def encuadre(self):
        """Ajusta la vista al modelo sin cambiar la dirección, con el mismo giro suave del cubo."""
        self.animador.animar(lambda: self.vista.reset_camera(render=False))

    # ---------- Dibujo ----------
    def _vigente(self, item):
        """El item si todavía existe en el modelo; si no, None."""
        if item is None:
            return None
        tipo, ident = item
        if tipo == "apoyo":
            nodo = self.modelo.nodos.get(ident)
            return item if nodo is not None and any(nodo.apoyo) else None
        if tipo == "pano":
            return item if getattr(self.modelo, "losas", None) and self.modelo.losa_de_pano(ident) is not None else None
        coleccion = {"nodo": self.modelo.nodos, "barra": self.modelo.elementos, "carga": self.modelo.cargas,
                     "losa": getattr(self.modelo, "losas", {})}
        return item if ident in coleccion.get(tipo, {}) else None

    def _tamano(self):
        """Tamaño del modelo (m), para dibujar cargas y resultados en proporción."""
        if not self.modelo.nodos:
            return 1.0
        puntos = np.array([n.coords for n in self.modelo.nodos.values()], dtype=float)
        return float(np.ptp(puntos, axis=0).max()) or 1.0

    def redibujar(self, reiniciar_camara=False):
        """Vuelve a dibujar el modelo y la rejilla. No mueve la cámara, salvo que se pida.
        Editando se dibujan las cargas del caso elegido; con resultados, lo prendido arriba y las
        reacciones."""
        for actor in self.dibujado.actores.values():
            self.vista.remove_actor(actor, render=False)
        self.vista.set_background(colores.FONDO_VISTA)
        real = self.accion_seccion_real.isChecked()
        # Las losas se dibujan solo al editar el modelo 3D: con resultados (también la deformada) se ven
        # vigas y columnas (decisión del usuario). En un sistema de vigueta, el acero de arriba va
        # solo sobre los apoyos
        losas = self._resumenes() if (not self.modo_resultados and self.sistema is None
                                      and getattr(self.modelo, "losas", None)) else None
        cortes = cortes_superiores(self._sv.franja, self.modelo) if self._sv is not None else None
        self.dibujado = dibujar_modelo(self.vista, self.modelo, real, self.opacidad_concreto if real else 1.0,
                                       losas=losas, cortes=cortes)
        self.rejilla = geometria_rejilla(self.modelo)
        self.dibujado.actores["rejilla"] = dibujar_rejilla(self.vista, self.rejilla,
                                                           cuenta_para_camara=not self.modelo.nodos)
        tamano = self._tamano()
        rc = self._rc()
        self.factor_deformada = None
        self._escala_diagrama = 0.0
        if not self.modo_resultados:
            extra = areas = None
            if self.sistema is None and getattr(self.modelo, "losas", None):
                if self.cargas_tipo["losas"].isChecked():
                    extra = [c for _eid, c in cargas_de_losas(self.modelo, self.caso_activo(), self._cargas_losas())]
                if self.cargas_tipo["areas"].isChecked():
                    areas = cargas_de_area(self.modelo, self._resumenes(), self.caso_activo())
            self.dibujado.actores.update(dibujar_cargas(self.vista, self.modelo, self.caso_activo(), tamano,
                                                        seccion_real=real, extra=extra, areas=areas,
                                                        con_barras=self.cargas_tipo["barras"].isChecked()))
        elif rc is not None:
            if self.resultado_visible in DEFORMADAS:
                actores, self.factor_deformada = dibujar_deformada(self.vista, self.modelo, rc, tamano,
                                                                   self.resultado_visible)
                self.dibujado.actores.update(actores)
            elif self.resultado_visible:
                actores, self._escala_diagrama = dibujar_diagrama(self.vista, self.modelo, rc, self.resultado_visible,
                                                                  tamano)
                self.dibujado.actores.update(actores)
            self.dibujado.actores.update(dibujar_reacciones(self.vista, self.modelo, rc, tamano))
        elif self._env() is not None and self.resultado_visible and self.resultado_visible not in DEFORMADAS:
            actores, self._escala_diagrama = dibujar_envolvente(self.vista, self.modelo, self._env(),
                                                                self.resultado_visible, tamano)
            self.dibujado.actores.update(actores)
        boton = self.botones_resultado["deformada"]
        boton.setToolTip("Deformada: total, Δx, Δy o Δz (ejes globales), con la inercia bruta Ig. Las fuerzas "
                         "internas y las reacciones van con la agrietada del concreto (0.70·Ig columnas, 0.35·Ig vigas)"
                         + (f". Ahora, ×{_factor_texto(self.factor_deformada)} el tamaño real"
                            if self.factor_deformada is not None else ""))
        self.seleccion, self.resaltado = self._vigente(self.seleccion), self._vigente(self.resaltado)
        self._dibujar_ejes_locales()
        self._dibujar_corte(self._corte, dibujar=False)
        self._aplicar_visibilidad(dibujar=False)
        self.marcados = [m for m in self.marcados if m[1] in self.modelo.elementos]
        self.dibujado.pintar(self.resaltado, self._en_3d(self.seleccion), self._enlazados(), self.marcados)
        self.previsualizacion.actualizar_estilo()
        if reiniciar_camara:
            self.vista.view_isometric()
            self.vista.reset_camera()
        self.vista.renderer.ResetCameraClippingRange()
        self.vista.render()

    def _dibujar_corte(self, dato, dibujar=True):
        """El punto verde del corte del panel Diagrama sobre su barra (pedido del usuario): dice en qué
        barra y en qué punto se lee. dato: (ID de barra, x desde el nodo i) o None (sin corte).
        - Con un diagrama (o la envolvente): el punto en el eje y una línea verde hasta la curva (las dos
          curvas en la envolvente), con la escala del dibujo.
        - Con la deformada: el punto sobre la curva deformada, con el mismo factor.
        Solo con resultados a la vista (al editar el panel no tiene corte)."""
        self._corte = dato
        for nombre in ("corte", "corte_linea"):
            actor = self.dibujado.actores.pop(nombre, None)
            if actor is not None:
                self.vista.remove_actor(actor, render=False)
        if dato is None or not self.modo_resultados or dato[0] not in self.modelo.elementos:
            if dibujar:
                self.vista.render()
            return
        import pyvista as pv
        from interfaz.vista3d.resultados import punto_del_diagrama
        from modelo.analisis import desplazamientos_globales, envolvente_en_x, fuerzas_en_x, geometria
        eid, x = dato
        x = min(max(float(x), 0.0), geometria(self.modelo, eid)[2])
        rc, env, comp = self._rc(), self._env(), self.resultado_visible
        base, topes = punto_del_diagrama(self.modelo, eid, x, 0.0, "My", 0.0)[0], []
        if comp in DEFORMADAS and rc is not None and self.factor_deformada is not None:
            d = desplazamientos_globales(self.modelo, rc, eid, x=[x])
            delta = np.array([d["Dx"][0], d["Dy"][0], d["Dz"][0]])
            if DEFORMADAS[comp] is not None:
                solo = np.zeros(3)
                solo[DEFORMADAS[comp]] = 1.0
                delta = delta * solo
            base = base + delta * self.factor_deformada
        elif comp and comp not in DEFORMADAS and self._escala_diagrama:
            if env is not None and eid in env.barras:
                valores = envolvente_en_x(env, eid, comp, x)[:2]
            elif rc is not None:
                valores = (fuerzas_en_x(self.modelo, rc, eid, x)[comp],)
            else:
                valores = ()
            topes = [punto_del_diagrama(self.modelo, eid, x, v, comp, self._escala_diagrama)[1] for v in valores]
        comunes = dict(pickable=False, reset_camera=False, render=False)
        self.dibujado.actores["corte"] = self.vista.add_points(
            np.array([base]), color=colores.CORTE, point_size=ui.TAMANO_CORTE_PX, render_points_as_spheres=True,
            name="corte", **comunes)
        if topes:                                   # del eje a la curva (en la envolvente, a las dos)
            puntos = [base, topes[0]] if len(topes) == 1 else [topes[0], base, topes[1]]
            self.dibujado.actores["corte_linea"] = self.vista.add_mesh(
                pv.lines_from_points(np.array(puntos)), color=colores.CORTE, line_width=3, name="corte_linea",
                **comunes)
        for nombre in ("corte", "corte_linea"):
            if nombre in self.dibujado.actores:
                self.dibujado.actores[nombre].SetUseBounds(False)
        if dibujar:
            self.vista.render()

    def _dibujar_ejes_locales(self):
        """Los ejes locales x, y, z de la barra seleccionada (o de la barra de la carga elegida). Se
        rehacen al cambiar la selección y al redibujar; el menú Etiquetas los muestra u oculta.
        Sirven para leer los diagramas (N, V, M y T están en esos ejes) y las cargas en x, y, z.
        Con la deformada a la vista NO se dibujan: los desplazamientos van en ejes globales, y los
        locales (con los mismos colores) harían creer que Δx es a lo largo de la barra."""
        for nombre in ("ejes_locales", "letras_ejes_locales"):
            actor = self.dibujado.actores.pop(nombre, None)
            if actor is not None:
                self.vista.remove_actor(actor, render=False)
        elegido = self._en_3d(self.seleccion)
        if elegido is None or elegido[0] != "barra":
            return
        if self.modo_resultados and self.resultado_visible in DEFORMADAS:
            return
        actores = dibujar_ejes_locales(self.vista, self.modelo, elegido[1], self._tamano(),
                                       self.accion_seccion_real.isChecked())
        visible = self.etiquetas["ejes_locales"].isChecked()
        for actor in actores.values():
            actor.SetVisibility(visible)
        self.dibujado.actores.update(actores)

    def _relacionados(self, seleccion):
        """Lo relacionado con la selección: (mismos, enlazados).

        - nodo: mismos = sus cargas del caso activo; enlazados = su apoyo y sus barras;
        - apoyo: enlazado = su nodo;
        - barra: mismos = sus cargas; enlazados = sus nodos y los apoyos de esos nodos;
        - carga: enlazado = su nodo o su barra.
        En 3D lo enlazado va en el gris intermedio y lo seleccionado en gris oscuro. Viendo una
        combinación no hay cargas a la vista."""
        if seleccion is None:
            return [], []
        tipo, ident = seleccion
        caso = self.caso_activo()

        def cargas(clase, i):
            return [] if self.modo_combinaciones else [("carga", c) for c in self.modelo.cargas_en(clase, i, caso)]

        def apoyos(nodos):
            return [("apoyo", n) for n in nodos if any(self.modelo.nodos[n].apoyo)]

        if tipo == "nodo":
            return (cargas("nodo", ident),
                    apoyos([ident]) + [("barra", e) for e in self.modelo.elementos_conectados(ident)])
        if tipo == "apoyo":
            return [], [("nodo", ident)]
        if tipo == "barra":
            el = self.modelo.elementos[ident]
            return cargas("barra", ident), [("nodo", el.ni), ("nodo", el.nj)] + apoyos([el.ni, el.nj])
        if tipo == "losa":                             # sus paños, y las vigas en que se apoya
            losa = self.modelo.losas[ident]
            vigas = {e for p in losa.panos.values() for e in p.apoyo_a + p.apoyo_b}
            return [("pano", p) for p in losa.panos], [("barra", e) for e in sorted(vigas)]
        if tipo == "pano":                             # su losa y sus dos vigas de apoyo
            lid = self.modelo.losa_de_pano(ident)
            pano = self.modelo.losas[lid].panos[ident]
            return [], [("losa", lid)] + [("barra", e) for e in pano.apoyo_a + pano.apoyo_b]
        c = self.modelo.cargas[ident]
        return [], [("nodo", c.nodo) if hasattr(c, "nodo") else ("barra", c.barra)]

    def _en_3d(self, seleccion):
        """Qué se pinta como seleccionado en 3D: una carga elegida se ve en su nodo o su barra."""
        if seleccion is not None and seleccion[0] == "carga":
            return self._relacionados(seleccion)[1][0]
        return seleccion

    def _enlazados(self):
        """Lo que se pinta como relacionado en 3D junto con la selección (sin las cargas; de un paño,
        sus vigas y no toda su losa)."""
        if self.seleccion is None or self.seleccion[0] == "carga":
            return []
        return [r for r in self._relacionados(self.seleccion)[1] if r[0] not in ("carga", "losa")]

    def pintar(self):
        """Colores vigentes: gris; un gris intermedio lo relacionado y lo que está bajo el mouse;
        gris oscuro lo seleccionado."""
        self.dibujado.pintar(self.resaltado, self._en_3d(self.seleccion), self._enlazados(), self.marcados)
        self.vista.render()

    # ---------- Cambios, Deshacer y Eliminar ----------
    def antes_de_cambiar(self):
        """Lo llama todo lo que va a cambiar el modelo: guarda una copia para Deshacer."""
        self.historial.guardar(self.modelo, not self.modificado)
        self._actualizar_deshacer()

    def _actualizar_deshacer(self):
        en_sistema = self.sistema is not None             # un sistema no se edita: tampoco se deshace
        self.accion_deshacer.setEnabled(self.historial.puede_deshacer() and not en_sistema)
        self.accion_rehacer.setEnabled(self.historial.puede_rehacer() and not en_sistema)

    def _volver(self, modelo, guardado, texto):
        """Pone una copia del historial como modelo actual."""
        self.salir_de_sistema(redibujar=False)
        self._cache = {}
        self.modelo, self.modificado = modelo, not guardado
        self._invalidar_resultados()
        self.herramienta.cancelar()
        self._actualizar_titulo()
        self._llenar_casos()
        self._llenar_combinaciones()
        self._actualizar_modo()
        self.redibujar()
        self.seleccionar(self.seleccion)
        self._refrescar_paneles()
        self._actualizar_deshacer()
        self.mensaje(texto)
        self._actualizar_puntero()

    def deshacer(self):
        if self.historial.puede_deshacer():
            self._volver(*self.historial.deshacer(self.modelo, not self.modificado), "Deshecho")

    def rehacer(self):
        if self.historial.puede_rehacer():
            self._volver(*self.historial.rehacer(self.modelo, not self.modificado), "Rehecho")

    def eliminar(self):
        """Supr: borra lo seleccionado y lo que depende de ello:
        - un apoyo: solo el apoyo (el nodo queda libre, con sus barras);
        - un nodo: el nodo con su apoyo, sus cargas y sus barras (una barra no existe sin sus nodos);
        - una barra: la barra con sus cargas (los nodos quedan);
        - una carga: la carga."""
        if self.modo_resultados:
            self.mensaje("Con resultados a la vista no se edita: vuelve a editar con ▶")
            return
        if self.sistema is not None:
            self.mensaje("Un sistema de vigueta no se edita: vuelve al Modelo 3D (lista Sistema)")
            return
        if self.seleccion is None:
            self.mensaje("Selecciona un nodo, un apoyo, una barra, una carga, un paño o una losa para eliminar")
            return
        tipo, ident = self.seleccion
        self.antes_de_cambiar()
        if tipo == "pano":
            lid = self.modelo.losa_de_pano(ident)
            nombre = self.modelo.losas[lid].nombre
            self.modelo.eliminar_pano(ident)
            texto = f"Paño {ident} de {nombre} eliminado" + ("" if lid in self.modelo.losas else " (y su losa)")
            self.seleccion = None
            self.modelo_cambiado(texto)
            return
        if tipo == "losa":
            nombre = self.modelo.losas[ident].nombre
            self.modelo.eliminar_losa(ident)
            self.seleccion = None
            self.modelo_cambiado(f"{nombre} eliminada")
            return
        if tipo == "carga":
            self.modelo.eliminar_carga(ident)
            texto = f"Carga {ident} eliminada"
        elif tipo == "apoyo":
            self.modelo.restringir(ident, *TIPOS["libre"])
            texto = f"Apoyo del nodo {ident} eliminado"
        elif tipo == "nodo":
            apoyo = any(self.modelo.nodos[ident].apoyo)
            conectadas = self.modelo.elementos_conectados(ident)
            n_cargas = len(self.modelo.cargas_en("nodo", ident)) + sum(
                len(self.modelo.cargas_en("barra", e)) for e in conectadas)
            barras = self.modelo.eliminar_nodo(ident)
            partes = (["su apoyo"] if apoyo else []) + ([_plural(len(barras), "barra")] if barras else []) + \
                     ([_plural(n_cargas, "carga")] if n_cargas else [])
            texto = f"Nodo {ident} eliminado"
            if partes:
                texto += " (con " + (", ".join(partes[:-1]) + " y " + partes[-1] if len(partes) > 1 else partes[0]) + ")"
        else:
            self.modelo.eliminar_elemento(ident)
            texto = f"Elemento {ident} eliminado (sus nodos quedan)"
        self.seleccion = None
        self.modelo_cambiado(texto)

    def _asignar_seccion(self, eid, sid):
        el = self.modelo.elementos.get(eid)
        if el is None or el.seccion == sid:
            return
        self.antes_de_cambiar()
        self.modelo.asignar_seccion(eid, sid)
        nombre = textos.nombre(self.modelo.secciones[sid], self.modelo) if sid is not None else "sin sección"
        self.modelo_cambiado(f"Elemento {eid}: {nombre}")

    def _editar_seccion_columna(self, eid, valores):
        """Medidas nuevas desde la pestaña Interacción: otra sección solo para esa columna. Si había
        resultados a la vista, se vuelve a analizar solo y se queda en el mismo estado (caso o
        combinación, resultado y pestaña): es la única excepción a "un cambio vuelve a Editar", porque
        la pestaña sirve para ajustar la sección mirando sus puntos Pu–Mu."""
        estado = (self.modo_resultados, self.ver_combinaciones, self.resultado_visible or self._ultimo_resultado,
                  self.accion_seccion_real.isChecked())
        self._editar_seccion(eid, valores)
        if not estado[0] or self.modo_resultados:
            return
        self._ultimo_resultado = estado[2]
        self.ver_combinaciones = estado[1]
        self.analizar()
        if self.modo_resultados:
            self._poner_seccion_real(estado[3])       # como estaba (analizar la apaga)
            self._actualizar_modo()
            self.redibujar()
            self._refrescar_paneles()

    def _editar_seccion(self, eid, valores):
        """Medidas nuevas para la sección de una barra: se usa (o crea) otra sección solo para ella."""
        if eid not in self.modelo.elementos:
            return
        material, b, h, d, barra, nx, ny, fy = valores[:8]
        acero = valores[8] if len(valores) > 8 and valores[8] in self.modelo.materiales else None
        mat = self.modelo.materiales.get(material)
        error = None
        if mat is None or mat.fc is None:
            error = "La sección necesita un material de concreto (Definir → Materiales)"
        elif not 0 < d < min(b, h) / 2:
            error = "d debe ser menor que la mitad de b y de h"
        else:
            from modelo import interaccion as puente
            from modelo.estructura import Concreto
            try:
                puente.propiedades(Concreto("rectangular", mat.fc, d, barra, b, h, nx, ny, fy=fy))
            except ValueError as e:
                error = str(e)
        if error:
            self.mensaje(error)
            self._mostrar_propiedades(self._en_propiedades)      # vuelven los valores anteriores
            return
        self.antes_de_cambiar()
        sid, nueva = cc.buscar_o_crear_seccion(self.modelo, material, b, h, d, barra, nx, ny, fy, acero)
        self.modelo.asignar_seccion(eid, sid)
        texto = f"Elemento {eid}: {textos.nombre(self.modelo.secciones[sid], self.modelo)}"
        self.modelo_cambiado(texto + (" (sección nueva)" if nueva else ""))

    # ---------- Losas: cambios desde Propiedades, Comprobaciones y el Explorador ----------
    def _cambiar_losas(self, funcion, texto):
        """Aplica funcion(modelo 3D), un cambio de una losa, con un paso de Deshacer. Se prueba antes en
        una copia: si no sirve, se avisa y nada cambia. Con un sistema de vigueta a la vista, se vuelve a
        abrir (la vigueta cambió) y, si se veían resultados, se vuelve a analizar."""
        import copy
        try:
            funcion(copy.deepcopy(self._modelo_real()))
        except (ValueError, KeyError) as e:
            self.mensaje(f"No se pudo: {e}")
            self._mostrar_propiedades(self._en_propiedades)
            return False
        sistema, resultados, combos = self.sistema, self.modo_resultados, self.ver_combinaciones
        visible = self.resultado_visible or self._ultimo_resultado
        self.salir_de_sistema(redibujar=False)
        self.antes_de_cambiar()
        funcion(self.modelo)
        self.modelo_cambiado(texto)
        if sistema is not None and sistema in [tuple(d) for d in (self.selector_sistema.itemData(i)
                                                                  for i in range(self.selector_sistema.count()))
                                               if d is not None]:
            self.abrir_sistema(sistema)
            if resultados:
                self._ultimo_resultado, self.ver_combinaciones = visible, combos
                self.analizar()
        return True

    def _editar_losa(self, lid, cambios):
        """Datos de la losa desde Propiedades: n, paño de referencia, ξ, ψ o si sostiene elementos frágiles."""
        def cambiar(m):
            losa = m.losas[lid]
            for clave, valor in cambios.items():
                setattr(losa, clave, valor)
            if "n_viguetas" in cambios or "referencia" in cambios:
                ml.actualizar_seccion(m, losa)                 # s cambia: bf también
        self._cambiar_losas(cambiar, f"{self._modelo_real().losas[lid].nombre}: datos cambiados")

    def _editar_pano(self, pid, muerta, viva):
        def cambiar(m):
            pano = m.losas[m.losa_de_pano(pid)].panos[pid]
            pano.muerta, pano.viva = muerta, viva
        self._cambiar_losas(cambiar, f"Paño {pid}: cargas cambiadas")

    def _editar_vigueta(self, lid, v):
        """La vigueta nueva desde Comprobaciones: una T con esos datos y el bf que le toca por s."""
        def cambiar(m):
            losa = m.losas[lid]
            sec = m.secciones[losa.seccion]
            geos = ml.geometrias(m, losa)
            bf = ml.ala_efectiva(geos, losa, v["bw"], v["hf"])
            if bf <= v["bw"] + 1e-6:
                raise ValueError("con esa separación no queda ala: pon menos viguetas o un alma más angosta")
            sid, _nueva = cc.buscar_o_crear_seccion_T(
                m, sec.material, v["bw"], v["h"], round(bf, 6), v["hf"], 0.0, v["barra"], v["n"], sec.concreto.fy,
                acero=sec.concreto.acero, acero_estribo=sec.concreto.acero_estribo,
                barra_sup=v["barra_sup"], n_sup=v["n_sup"], rec=v["rec"], estribo=v["estribo"],
                s_estribo=v["s_estribo"])
            losa.seccion = sid
        self._cambiar_losas(cambiar, f"Vigueta de {self._modelo_real().losas[lid].nombre} cambiada")

    def _menu_losa(self, dato, posicion):
        """Clic derecho en el Explorador sobre una losa, un paño, una franja o un caso de viva."""
        tipo, valor = dato
        menu = QMenu(self)
        en_sistema = self.sistema is not None
        if tipo == "franja":
            menu.addAction("Ver el sistema de vigueta", lambda: self.abrir_sistema(valor))
            menu.addAction("Nuevo caso de viva…", lambda: self._nuevo_caso_viva(*valor)).setEnabled(not en_sistema)
        elif tipo == "patron":
            lid, letra, i, auto = valor
            menu.addAction("Ver el sistema de vigueta", lambda: self.abrir_sistema((lid, letra)))
            accion = menu.addAction("Eliminar caso de viva", lambda: self._eliminar_caso_viva(lid, letra, i))
            accion.setEnabled(not auto and not en_sistema)
            if auto:
                accion.setToolTip("Los casos automáticos (§6.4.2) no se eliminan")
        elif tipo == "pano":
            lid = self._modelo_real().losa_de_pano(valor)
            menu.addAction("Hacerlo el paño de referencia (n viguetas)",
                           lambda: self._editar_losa(lid, {"referencia": valor})).setEnabled(not en_sistema)
            menu.addAction("Eliminar paño", lambda: (self.seleccionar(("pano", valor)), self.eliminar())
                           ).setEnabled(not en_sistema)
        elif tipo == "losa":
            menu.addAction("Eliminar losa", lambda: (self.seleccionar(("losa", valor)), self.eliminar())
                           ).setEnabled(not en_sistema)
        menu.exec(posicion)

    def _nuevo_caso_viva(self, lid, letra):
        """Un caso de viva propio para la franja: la viva en los claros que se marquen."""
        from interfaz.ventanas.casos_viva import pedir_claros
        principal = self._modelo_real()
        franja = next((f for f in self._resumenes().get(lid, {}).get("franjas", []) if f.letra == letra), None)
        if franja is None:
            return
        claros = pedir_claros(self, franja)
        if not claros:
            return
        existentes = ml.patrones(principal.losas[lid], franja)
        if any(tuple(c) == tuple(claros) for _n, c, _a in existentes):
            self.mensaje("Ese caso de viva ya existe")
            return
        nombre = f"Caso {len(existentes) + 1}"

        def cambiar(m):
            m.losas[lid].patrones.setdefault(franja.firma, []).append([nombre, list(claros)])
        self._cambiar_losas(cambiar, f"{franja.nombre}: {nombre} con viva en {ml.describir_claros(claros)}")

    def _eliminar_caso_viva(self, lid, letra, indice):
        principal = self._modelo_real()
        franja = next((f for f in self._resumenes().get(lid, {}).get("franjas", []) if f.letra == letra), None)
        if franja is None:
            return
        nombre, claros, auto = ml.patrones(principal.losas[lid], franja)[indice]
        if auto:
            return

        def cambiar(m):
            lista = m.losas[lid].patrones.get(franja.firma, [])
            lista[:] = [p for p in lista if tuple(p[1]) != tuple(claros)]
        self._cambiar_losas(cambiar, f"{franja.nombre}: {nombre} eliminado")

    def modelo_cambiado(self, texto, invalida=True):
        """Lo llaman las herramientas y los paneles después de cambiar el modelo.

        invalida=False: el cambio no toca los resultados de los casos (editar combinaciones, que se
        calculan sumando esos resultados); solo se rehacen las combinaciones."""
        self.modificado = True
        self.marcados = []
        self._cache = {}                           # lo calculado de las losas ya no vale
        if invalida:
            self._invalidar_resultados()
        else:
            self._combinados = {}
        self._actualizar_deshacer()
        self._actualizar_titulo()
        self._llenar_sistemas()
        self._llenar_casos()
        self._llenar_combinaciones()
        self._actualizar_modo()
        self.redibujar()
        self._refrescar_paneles()
        self.mensaje(texto)
        self.actualizar_indicacion()
        self._actualizar_puntero()

    def _refrescar_paneles(self):
        """Los botones del estado vigente, el Explorador, Propiedades, Diagrama y las ventanas
        abiertas, con el modelo y las unidades vigentes."""
        self._llenar_casos()
        self._llenar_combinaciones()
        self._actualizar_modo()
        caso = None if self.modo_combinaciones else self.caso_activo()
        con_losas = self.sistema is None and getattr(self.modelo, "losas", None)
        self.explorador.actualizar(
            self.modelo, caso,
            cargas_losas=cargas_de_losas(self.modelo, caso, self._cargas_losas()) if con_losas and caso else None,
            resumenes=self._resumenes() if con_losas else None)
        self.explorador.marcar(self.seleccion, *self._relacionados(self.seleccion))
        self._mostrar_propiedades(self._en_propiedades)
        self.modelo_actualizado.emit()
        if self.ventana_matriz.isVisible():
            self.ventana_matriz.refrescar(self.modelo)
        for ventana in self.diagramas:
            ventana.refrescar()

    # ---------- Mouse ----------
    def _actualizar_puntero(self):
        """Recalcula dónde caería un clic: coordenadas en la barra de estado y previsualización gris."""
        if self._mouse is None or self.cubo.contiene(*self._mouse):
            cand = Candidato()
        else:
            cand = candidato(self.vista.renderer, *self._mouse, self.modelo, self.rejilla,
                             self.accion_snap.isChecked())
        self.candidato = cand
        self.coordenadas.setText(texto_coordenadas(cand, self.herramienta.inicio()))
        habia = self.previsualizacion.visible
        if self.herramienta.usa_previsualizacion:
            self.herramienta.previsualizar(cand)
        else:
            self.previsualizacion.ocultar()
        if habia or self.previsualizacion.visible:
            self.vista.render()

    def _actualizar_resaltado(self):
        """Con Seleccionar, el nodo, el apoyo o la barra bajo el mouse se ve en el gris intermedio."""
        nuevo = None
        if (self._mouse is not None and isinstance(self.herramienta, Seleccionar)
                and not self.cubo.contiene(*self._mouse)):
            nuevo = elemento_en(self.vista.renderer, self.modelo, *self._mouse, ui.TOL_SELECCION_PX,
                                self.dibujado.cajas_apoyo, self.dibujado.cajas_nudo, self.dibujado.esquinas_pano)
        if nuevo != self.resaltado:
            self.resaltado = nuevo
            self.pintar()

    def _al_presionar(self, *_):
        self.animador.detener()                    # si la cámara estaba girando, manda el usuario
        self._pos_presion = self.vista.iren.get_event_position()

    def _al_mover(self, *_):
        if self._pos_presion is not None:          # arrastrando para rotar: no se recalcula nada
            return
        self._mouse = self.vista.iren.get_event_position()
        if self.accion_medir.isChecked():
            if not self.cubo.contiene(*self._mouse):
                self.medicion.mover(*self._mouse)
            return
        self._actualizar_resaltado()               # el cubo se resalta solo (filtra los eventos de la vista)
        self._actualizar_puntero()

    def _al_salir(self, *_):
        self._mouse = None
        self._actualizar_resaltado()
        self._actualizar_puntero()

    def _al_soltar(self, *_):
        if self._pos_presion is None:
            return
        x, y = self.vista.iren.get_event_position()
        x0, y0 = self._pos_presion
        self._pos_presion = None
        if abs(x - x0) > ui.TOL_CLIC_PX or abs(y - y0) > ui.TOL_CLIC_PX:
            return                                 # fue un arrastre para rotar, no un clic
        self._clic(x, y)

    def _clic(self, x, y):
        if self.cubo.contiene(x, y):               # clic en la zona del cubo: lo atiende el propio cubo
            return
        if self.accion_medir.isChecked():          # midiendo: el clic pone un punto de la medición
            self.medicion.clic(x, y)
            return
        self._mouse = (x, y)
        self._actualizar_puntero()
        self.herramienta.clic(x, y, self.candidato)
        self.actualizar_indicacion()
        self._actualizar_puntero()

    # ---------- Selección ----------
    def seleccionar(self, seleccion):
        """Selecciona un ("nodo", id), ("apoyo", id), ("barra", id) o ("carga", id): gris oscuro en
        3D (con lo relacionado en un gris más tenue), marcado en el explorador con todo lo
        relacionado y sus datos en Propiedades. None quita la selección."""
        self.seleccion = self._vigente(seleccion)
        self.marcados = []                         # una selección nueva quita lo marcado por una sección
        self._dibujar_ejes_locales()
        self.pintar()
        self.explorador.marcar(self.seleccion, *self._relacionados(self.seleccion))
        self._mostrar_propiedades(self.seleccion)

    # ---------- Archivo ----------
    def _actualizar_titulo(self):
        nombre = self.ruta.name if self.ruta else "Sin título"
        self.setWindowTitle(f"{ui.TITULO_VENTANA} — {nombre}{'*' if self.modificado else ''}")

    def _carpeta(self):
        return str(self.ruta.parent) if self.ruta else str(Path.home())

    def _confirmar_descartar(self):
        """True si se puede seguir: no hay cambios, se guardaron o el usuario los descarta."""
        if not self.modificado:
            return True
        respuesta = QMessageBox.question(
            self, "Cambios sin guardar", "El modelo tiene cambios sin guardar. ¿Quieres guardarlos?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if respuesta == QMessageBox.Save:
            return self.guardar()
        return respuesta == QMessageBox.Discard

    def nuevo(self):
        if self._confirmar_descartar():
            m = Modelo()
            cc.acero_por_defecto(m)                # el acero de refuerzo Grado 60 viene por defecto
            self._cargar(m, None, {})

    def abrir(self, ruta=None):
        if not self._confirmar_descartar():
            return False
        if ruta is None:
            ruta, _ = QFileDialog.getOpenFileName(self, "Abrir modelo", self._carpeta(), "Modelos (*.json)")
            if not ruta:
                return False
        try:
            modelo, vista = archivo.abrir(ruta)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Abrir", f"No se pudo abrir {Path(ruta).name}:\n\n{e}")
            return False
        self._cargar(modelo, Path(ruta), vista)
        return True

    def guardar(self):
        return self._escribir(self.ruta) if self.ruta else self.guardar_como()

    def guardar_como(self, ruta=None):
        if ruta is None:
            sugerido = str(self.ruta) if self.ruta else str(Path(self._carpeta()) / "modelo.json")
            ruta, _ = QFileDialog.getSaveFileName(self, "Guardar modelo como", sugerido, "Modelos (*.json)")
            if not ruta:
                return False
        ruta = Path(ruta)
        if ruta.suffix.lower() != ".json":
            ruta = ruta.with_name(ruta.name + ".json")
        return self._escribir(ruta)

    def _escribir(self, ruta):
        try:
            archivo.guardar(self._modelo_real(), ruta)        # el modelo 3D, aunque se vea un sistema
        except OSError as e:
            QMessageBox.warning(self, "Guardar", f"No se pudo guardar {Path(ruta).name}:\n\n{e}")
            return False
        self.ruta = Path(ruta)
        self.modificado = False
        self.historial.marcar_sin_guardar()       # solo el estado actual coincide con el archivo
        self._actualizar_titulo()
        self.mensaje(f"Guardado en {self.ruta.name}")
        return True

    def _cargar(self, modelo, ruta, vista):
        """Pone otro modelo en la ventana (Nuevo o Abrir)."""
        self.salir_de_sistema(redibujar=False)
        self.explorador.reiniciar()                # otro modelo: el explorador empieza con todo cerrado
        self._cache = {}
        self.modelo, self.ruta, self.modificado = modelo, ruta, False
        self.ver_combinaciones = False
        self._ultimo_resultado = "deformada"
        self._invalidar_resultados()
        self._llenar_casos()
        self._llenar_combinaciones()
        self.historial.vaciar()
        self._actualizar_deshacer()
        self._llenar_sistemas()
        for _, herramienta in self._herramientas:
            herramienta.reiniciar()
        self.seleccion = self.resaltado = self._en_propiedades = None
        self.ventana_matriz.close()
        for ventana in list(self.diagramas):
            ventana.close()
        self._actualizar_modo()
        self.redibujar(reiniciar_camara=True)
        self._refrescar_paneles()
        self._actualizar_titulo()
        self.actualizar_indicacion()
        self._actualizar_puntero()

    # ---------- Configuración ----------
    def abrir_configuracion(self):
        """El diálogo aplica cada cambio en el momento; aquí solo se abre."""
        DialogoConfiguracion(self).exec()

    def aplicar_configuracion(self):
        """Toma los valores vigentes de configuracion/ (lo llama el diálogo en cada cambio)."""
        aplicar_tema(QApplication.instance())
        for barra in (self.herramientas, self.barra_definir):
            barra.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        for boton in self.botones_resultado.values():
            boton.setIconSize(QSize(ui.TAMANO_ICONO, ui.TAMANO_ICONO))
        inferior = QSize(ui.TAMANO_ICONO_INFERIOR, ui.TAMANO_ICONO_INFERIOR)
        self.barra_inferior.setIconSize(inferior)
        self.boton_etiquetas.setIconSize(inferior)
        self.cubo.actualizar_colores()
        self._ajustar_esquinas()
        self.propiedades.actualizar_unidades()     # campos a medias (cargas, formularios) en las nuevas
        self.redibujar()
        self._refrescar_paneles()
        self.actualizar_indicacion()
        self._actualizar_puntero()
        for barra in (self.herramientas, self.barra_definir, self.barra_inferior):
            barra.update()                         # los íconos se vuelven a pintar con su color

    # ---------- Ventana ----------
    def _ajustar_esquinas(self):
        """Cubo arriba a la derecha y ejes abajo a la izquierda: cuadrados y con el mismo margen."""
        ancho, alto = self.vista.ren_win.GetSize()
        if ancho <= 0 or alto <= 0:
            return
        self.cubo.ajustar_tamano()
        ejes = self.vista.renderer.axes_widget
        if ejes is not None:
            ejes.SetViewport(*viewport_esquina(ancho, alto, ui.EJES_TAMANO, "abajo_izquierda"))

    def showEvent(self, evento):
        super().showEvent(evento)
        QTimer.singleShot(0, self._ajustar_y_dibujar)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if hasattr(self, "cubo"):
            QTimer.singleShot(0, self._ajustar_y_dibujar)   # después de que la vista tome su tamaño

    def _ajustar_y_dibujar(self):
        if not self._cerrando:
            self._ajustar_esquinas()
            self.vista.render()

    def closeEvent(self, evento):
        if not self._confirmar_descartar():
            evento.ignore()
            return
        self._cerrando = True
        self.animador.detener()                    # que el giro no siga con la ventana cerrándose
        for ventana in list(self.diagramas):
            ventana.close()
        self.ventana_matriz.close()
        self.propiedades.interaccion.cerrar()      # la vista 3D de la pestaña Interacción, si se creó
        self.cubo.apagar()                         # apaga el cubo antes de cerrar la vista 3D
        self.vista.close()                         # libera la ventana 3D al cerrar
        super().closeEvent(evento)
