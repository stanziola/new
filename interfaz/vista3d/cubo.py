"""Cubo de vistas, como el ViewCube de Civil 3D.

El cubo es blanco, plano (sin iluminación) y sin letras. Está en la esquina superior derecha y
gira junto con la cámara. Al pasar el mouse se sombrea en gris lo que está debajo. Tiene tres partes:

- **El cubo.** Con un clic, la cámara gira con una animación corta hasta mirar el modelo desde ese
  lado: desde la cara, o desde una vista intermedia si es una arista o una esquina (26 vistas).
- **El anillo de giro**, debajo del cubo (en el plano de su base), con cuatro marcas. Arrastrarlo
  gira la cámara alrededor del eje vertical (Z) que pasa por el foco, a la misma distancia y con el
  mismo zoom: el punto del anillo que se tomó sigue al mouse.
- **Las flechas**, que aparecen solo con el mouse sobre el cubo y mirando una cara de frente:
  cuatro triángulos (uno por lado) que llevan a la cara vecina y dos flechas curvas, arriba a la
  derecha, que giran la vista 90° sobre la línea de visión.
El anillo y las flechas se pueden quitar (Configuración → Interfaz, ui.CUBO_ANILLO).

Cómo funciona:
- Cada cara del cubo se divide en 3x3 parches: el del centro es la cara; los de los bordes son
  aristas; los de las puntas son esquinas. Cada parche guarda la dirección desde la que se mira
  (por ejemplo, la arista entre +X y +Z guarda (1, 0, 1)).
- El cubo y el anillo son el "marcador" de un vtkOrientationMarkerWidget, que copia la orientación
  de la cámara principal en cada render. Las flechas son dibujos 2D (vtkActor2D) en ese mismo
  recuadro: no giran.
- Para saber qué parche (o el anillo) se tocó, se usa un vtkCellPicker sobre el renderer del widget.
- Una arista está formada por 2 parches (uno en cada cara que llega a ella) y una esquina por 3.
  Todos guardan la misma dirección, así que para resaltar la esquina completa se pintan todos
  los parches con esa dirección, no solo el que está bajo el mouse.
- El cubo se atiende solo: es un QObject que filtra los eventos del mouse de la vista (mover,
  presionar, soltar, salir y cambiar de tamaño). Por eso sirve igual en la ventana principal y en
  el diagrama de interacción 3D, sin que ninguna de las dos tenga que avisarle nada. El arrastre del
  anillo se "consume" ahí: no le llega a la cámara, que si no giraría libremente.
- El giro lo hace el AnimadorCamara (interfaz/vista3d/camara.py), el mismo que usa el botón Encuadre.
"""
import math

import numpy as np
import pyvista as pv
from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingCore import (vtkActor, vtkActor2D, vtkCellPicker, vtkCoordinate, vtkPolyDataMapper,
                                         vtkPolyDataMapper2D)

from configuracion import colores
from configuracion import interfaz as ui
from interfaz.vista3d.animacion import marco_camara
from interfaz.vista3d.camara import leer_camara

# Normal de cada cara y dos ejes en su plano (u x v = normal, para que el parche mire hacia afuera)
CARAS = [
    ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    ((0, 0, -1), (0, 1, 0), (1, 0, 0)),
]

# Qué es cada celda del marcador (arreglo "parte")
PARCHE, BORDE, ANILLO, LINEA_ANILLO = 0, 1, 2, 3

# Anillo de giro, en lados del cubo (el cubo mide 1 y su media diagonal en planta, 0.71)
RADIO_ANILLO = (0.95, 1.20)        # radios interior y exterior
Z_ANILLO = -0.5                    # en el plano de la base del cubo
SEGMENTOS_ANILLO = 72
# El marcador se encuadra solo, a su esfera envolvente. Con el anillo esa esfera es el doble de
# grande (radio 1.77 en vez de 0.87) y el cubo se vería chico: el recuadro crece y el marcador se
# acerca, de modo que el cubo queda del mismo tamaño que sin anillo y el anillo llena el 80 %
FACTOR_RECUADRO = 1.7              # cuánto crece el recuadro con el anillo
ZOOM_ANILLO = 1.3                  # acercamiento del marcador dentro de su recuadro
DE_FRENTE = 0.9995                 # |coseno| desde el cual la cámara mira una cara "de frente"
SEMIVUELTA_PX = 1.0                # anillo visto de canto: arrastrar un recuadro entero gira media vuelta

# Flechas, en coordenadas del recuadro del cubo (de 0 a 1, con el centro en 0.5, 0.5). De frente a
# una cara, el cuadrado del cubo llega a 0.19 del centro y el anillo va de 0.32 a 0.40
TRIANGULO = (0.232, 0.050, 0.045)  # distancia del centro a la base, alto y medio ancho de la base
RADIO_GIRO = 0.440                 # radio del arco de las flechas curvas (por fuera del anillo)
GROSOR_GIRO = 0.010                # medio grosor del arco
ARCOS_GIRO = {"antihorario": (50.0, 76.0), "horario": (40.0, 14.0)}    # de dónde a dónde va cada arco (grados)
PUNTA_GIRO = (0.030, 9.0)          # medio ancho de la punta y cuántos grados de arco ocupa
RADIO_ZONA = 0.43                  # el cubo "ocupa" un círculo de este radio en su recuadro (clics)
LADOS = {"arriba": (0.0, 1.0), "abajo": (0.0, -1.0), "izquierda": (-1.0, 0.0), "derecha": (1.0, 0.0)}


def viewport_esquina(ancho, alto, tamano, esquina):
    """Viewport (x0, y0, x1, y1) de un cuadrado de lado `tamano` (fracción del alto) en una esquina.

    Cuadrado en píxeles y a MARGEN_ESQUINA_PX del borde. Lo usan el cubo (arriba a la derecha) y
    los ejes X, Y, Z (abajo a la izquierda), para que queden proporcionados.
    """
    lado = min(tamano, 0.9) * alto                     # lado en píxeles
    lado = min(lado, 0.9 * ancho)                      # y que quepa a lo ancho (paneles angostos)
    m = ui.MARGEN_ESQUINA_PX
    if esquina == "arriba_derecha":
        x0, y0 = ancho - m - lado, alto - m - lado
    else:                                              # abajo a la izquierda
        x0, y0 = m, m
    return (max(x0, 0) / ancho, max(y0, 0) / alto, min(x0 + lado, ancho) / ancho, min(y0 + lado, alto) / alto)


def _rgb(color, n):
    return np.tile(np.array(colores.rgb(color), dtype=np.uint8), (n, 1))


def _parches():
    """Superficie del cubo (lado 1) con 9 parches por cara y la dirección de vista de cada uno."""
    f = ui.CUBO_FRANJA
    cortes = [-0.5, -0.5 + f, 0.5 - f, 0.5]
    signo = [-1, 0, 1]                      # parche izquierdo/abajo, centro, derecho/arriba
    puntos, caras, direcciones = [], [], []
    for n, u, v in CARAS:
        n, u, v = (np.array(a, dtype=float) for a in (n, u, v))
        for i in range(3):
            for j in range(3):
                esquinas = [(cortes[i], cortes[j]), (cortes[i + 1], cortes[j]),
                            (cortes[i + 1], cortes[j + 1]), (cortes[i], cortes[j + 1])]
                k = len(puntos)
                puntos += [0.5 * n + a * u + b * v for a, b in esquinas]
                caras += [4, k, k + 1, k + 2, k + 3]
                direcciones.append(n + signo[i] * u + signo[j] * v)
    malla = pv.PolyData(np.array(puntos), faces=np.array(caras))
    malla.cell_data["direccion"] = np.array(direcciones)
    malla.cell_data["parte"] = np.full(malla.n_cells, PARCHE)
    malla.cell_data["color"] = _rgb(colores.CUBO_CARA, malla.n_cells)
    return malla


def _borde():
    """Líneas de las aristas del cubo (solo decoración: su dirección es 0 y no se pueden elegir)."""
    borde = pv.Box(bounds=(-0.5, 0.5, -0.5, 0.5, -0.5, 0.5)).extract_all_edges()
    borde.cell_data["direccion"] = np.zeros((borde.n_cells, 3))
    borde.cell_data["parte"] = np.full(borde.n_cells, BORDE)
    borde.cell_data["color"] = _rgb(colores.CUBO_BORDE, borde.n_cells)
    return borde


def _anillo():
    """El anillo de giro: una corona plana bajo el cubo, sus dos bordes y cuatro marcas (cada 90°).
    Las marcas dejan ver que el anillo gira: una corona lisa girando sobre su eje se vería quieta."""
    interior, exterior = RADIO_ANILLO
    n = SEGMENTOS_ANILLO
    angulos = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    circulo = np.column_stack([np.cos(angulos), np.sin(angulos), np.zeros(n)])
    puntos = np.vstack([interior * circulo, exterior * circulo]) + [0.0, 0.0, Z_ANILLO]
    caras = []
    for i in range(n):
        j = (i + 1) % n
        caras += [4, i, j, n + j, n + i]
    corona = pv.PolyData(puntos, faces=np.array(caras))
    corona.cell_data["direccion"] = np.zeros((corona.n_cells, 3))
    corona.cell_data["parte"] = np.full(corona.n_cells, ANILLO)
    corona.cell_data["color"] = _rgb(colores.CUBO_CARA, corona.n_cells)
    lineas = []
    for base in (0, n):                                 # los dos círculos, cerrados
        lineas += [n + 1, *range(base, base + n), base]
    for i in range(0, n, n // 4):                       # las cuatro marcas, de un borde al otro
        lineas += [2, i, n + i]
    bordes = pv.PolyData(puntos, lines=np.array(lineas))
    bordes.cell_data["direccion"] = np.zeros((bordes.n_cells, 3))
    bordes.cell_data["parte"] = np.full(bordes.n_cells, LINEA_ANILLO)
    bordes.cell_data["color"] = _rgb(colores.CUBO_BORDE, bordes.n_cells)
    return [corona, bordes]


def _actor(malla):
    """Actor del cubo: color por celda y sin iluminación (cada cara se ve con su color exacto)."""
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(malla)
    mapper.SetScalarModeToUseCellFieldData()   # color por celda, tomado del arreglo "color"
    mapper.SelectColorArray("color")
    mapper.SetColorModeToDirectScalars()
    actor = vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetLineWidth(2)
    # Sin luz, VTK pinta (ambiente + difusa) x color: con 0 + 1 queda el color tal cual,
    # sin importar el ángulo desde el que se mire la cara.
    prop.LightingOff()
    prop.SetAmbient(0.0)
    prop.SetDiffuse(1.0)
    prop.SetSpecular(0.0)
    return actor


def _actor_2d(puntos):
    """Polígono relleno dibujado en el recuadro del cubo, con sus puntos (x, y) de 0 a 1 en él."""
    puntos = np.asarray(puntos, dtype=float)
    malla = pv.PolyData(np.column_stack([puntos, np.zeros(len(puntos))]),
                        faces=np.array([len(puntos), *range(len(puntos))]))
    mapper = vtkPolyDataMapper2D()
    mapper.SetInputData(malla.triangulate())             # los arcos no son convexos: en triángulos
    coordenada = vtkCoordinate()
    coordenada.SetCoordinateSystemToNormalizedViewport()
    mapper.SetTransformCoordinate(coordenada)
    actor = vtkActor2D()
    actor.SetMapper(mapper)
    actor.SetVisibility(False)
    return actor


def _triangulo(lado):
    """Triángulo que apunta hacia afuera en el lado dado del cubo (arriba, abajo, izquierda o derecha)."""
    u = np.array(LADOS[lado])
    p = np.array([-u[1], u[0]])                          # perpendicular: a lo largo de la base
    base, alto, medio = TRIANGULO
    centro = np.array([0.5, 0.5])
    return [centro + u * base - p * medio, centro + u * base + p * medio, centro + u * (base + alto)]


def _flecha_curva(sentido):
    """Flecha curva (un arco con punta) alrededor del centro: gira la vista 90° en ese sentido."""
    inicio, fin = ARCOS_GIRO[sentido]
    medio_ancho, grados_punta = PUNTA_GIRO
    signo = 1.0 if fin > inicio else -1.0
    cuello = fin - signo * grados_punta                  # donde termina el arco y empieza la punta
    angulos = np.radians(np.linspace(inicio, cuello, 10))
    centro = np.array([0.5, 0.5])

    def punto(radio, a):
        return centro + radio * np.array([math.cos(a), math.sin(a)])

    afuera = [punto(RADIO_GIRO + GROSOR_GIRO, a) for a in angulos]
    adentro = [punto(RADIO_GIRO - GROSOR_GIRO, a) for a in angulos[::-1]]
    a_cuello, a_fin = math.radians(cuello), math.radians(fin)
    punta = [punto(RADIO_GIRO + medio_ancho, a_cuello), punto(RADIO_GIRO, a_fin),
             punto(RADIO_GIRO - medio_ancho, a_cuello)]
    return afuera + punta + adentro


def _eje(v):
    """El eje (±X, ±Y o ±Z) más cercano al vector v."""
    v = np.asarray(v, dtype=float)
    eje = np.zeros(3)
    i = int(np.argmax(np.abs(v)))
    eje[i] = 1.0 if v[i] >= 0 else -1.0
    return eje


class CuboVistas(QObject):
    def __init__(self, vista, animador):
        super().__init__(vista)                 # la vista es su "padre" en Qt: se libera junto con ella
        self.vista = vista
        self.animador = animador                # AnimadorCamara compartido con Encuadre
        self._resaltado = None                  # lo resaltado ahora: ("vista", d), ("anillo",), ("flecha", n) o None
        self._ultimo_mouse = (-1, -1)           # para actualizar el gris al terminar un giro
        self._presion = None                    # (x, y, sobre qué) al presionar sobre el cubo o una flecha
        self._arrastre = None                   # arrastrando el anillo: {"azimut": ..., "x": ...}
        self._con_anillo = None                 # cómo se armó el marcador (con o sin anillo y flechas)
        self._flechas = {}                      # nombre -> vtkActor2D (4 triángulos y 2 flechas curvas)

        self.widget = vtkOrientationMarkerWidget()
        self.widget.SetInteractor(vista.iren.interactor)
        self.widget.SetDefaultRenderer(vista.renderer)  # copia la cámara de la vista principal
        self._armar()
        self.picker = vtkCellPicker()
        self.picker.SetTolerance(0.0005)

        # Al terminar cualquier giro (del cubo o de Encuadre), el gris se pone al día
        self.animador.terminada.connect(self._al_terminar_giro)
        vista.installEventFilter(self)          # el cubo atiende sus propios eventos del mouse

    # ---------- Armado ----------
    def _armar(self):
        """Arma el marcador (cubo y, si está activo, el anillo) y las flechas, con los colores vigentes."""
        self._con_anillo = bool(ui.CUBO_ANILLO)
        partes = [_parches(), _borde()] + (_anillo() if self._con_anillo else [])
        self.malla = pv.merge(partes)
        self._colores_base = np.array(self.malla.cell_data["color"])    # copia, para quitar el gris
        self._direcciones = np.array(self.malla.cell_data["direccion"], dtype=float)
        self._parte = np.array(self.malla.cell_data["parte"])
        self._resaltado = None
        activo = bool(self.widget.GetEnabled())
        if activo:
            for actor in self._flechas.values():
                self.widget.GetRenderer().RemoveViewProp(actor)
            self.widget.SetEnabled(0)
        self.widget.SetOrientationMarker(_actor(self.malla))
        self.widget.SetEnabled(1)
        self.widget.InteractiveOff()            # el cubo no se arrastra ni cambia de tamaño
        self._flechas = {}
        if self._con_anillo:
            formas = {lado: _triangulo(lado) for lado in LADOS}
            formas.update({sentido: _flecha_curva(sentido) for sentido in ARCOS_GIRO})
            for nombre, puntos in formas.items():
                actor = _actor_2d(puntos)
                self.widget.GetRenderer().AddViewProp(actor)
                self._flechas[nombre] = actor
            self._zonas = {nombre: np.asarray(puntos) for nombre, puntos in formas.items()}
        self._pintar_flechas()
        self.ajustar_tamano()

    def ajustar_tamano(self):
        """Cubo cuadrado con lado CUBO_TAMANO (fracción del alto de la vista), arriba a la derecha,
        separado MARGEN_ESQUINA_PX de la esquina. Con el anillo, el recuadro crece (y el marcador se
        acerca) para que quepan el anillo y las flechas sin achicar el cubo.

        Se llama al crear el cubo, al cambiar el tamaño de la vista y al cambiar Configuración.
        """
        ancho, alto = self.vista.ren_win.GetSize()
        if ancho <= 0 or alto <= 0:
            return
        lado = ui.CUBO_TAMANO * (FACTOR_RECUADRO if self._con_anillo else 1.0)
        self.widget.SetViewport(*viewport_esquina(ancho, alto, lado, "arriba_derecha"))
        self.widget.SetZoom(ZOOM_ANILLO if self._con_anillo else 1.0)

    def actualizar_colores(self):
        """Toma los colores vigentes del cubo y si lleva anillo (después de cambiarlos en Configuración)."""
        if bool(ui.CUBO_ANILLO) != self._con_anillo:
            self._armar()                       # con o sin anillo: el marcador es otro
            return
        base = np.empty((len(self._parte), 3), dtype=np.uint8)
        base[:] = colores.rgb(colores.CUBO_CARA)
        base[(self._parte == BORDE) | (self._parte == LINEA_ANILLO)] = colores.rgb(colores.CUBO_BORDE)
        self._colores_base = base
        self._resaltado = None
        self.malla.cell_data["color"] = base.copy()
        self._pintar_flechas()

    # ---------- Dónde está el mouse ----------
    def _recuadro(self):
        """(x0, y0, ancho, alto) del recuadro del cubo, en píxeles de la vista."""
        ancho, alto = self.vista.ren_win.GetSize()
        x0, y0, x1, y1 = self.widget.GetViewport()
        return x0 * ancho, y0 * alto, (x1 - x0) * ancho, (y1 - y0) * alto

    def _en_recuadro(self, x, y):
        """True si el punto (x, y), en píxeles de la vista, cae dentro del recuadro del cubo."""
        x0, y0, ancho, alto = self._recuadro()
        return x0 <= x <= x0 + ancho and y0 <= y <= y0 + alto

    def contiene(self, x, y):
        """True si el punto (x, y), en píxeles de la vista, cae en la zona que ocupa el cubo: ahí los
        clics son del cubo y no de las herramientas. Sin anillo es todo el recuadro; con anillo, el
        círculo del anillo y las flechas que estén a la vista (las esquinas del recuadro quedan
        libres para el modelo)."""
        if not self._en_recuadro(x, y):
            return False
        if not self._con_anillo:
            return True
        x0, y0, ancho, alto = self._recuadro()
        if math.hypot((x - x0) / ancho - 0.5, (y - y0) / alto - 0.5) <= RADIO_ZONA:
            return True
        return self._flecha_en(x, y) is not None

    def _de_frente(self):
        """True si la cámara mira una cara del cubo de frente (ahí aparecen las flechas)."""
        return float(np.max(np.abs(self._marco()[:, 2]))) > DE_FRENTE

    def _marco(self):
        """Ejes de la cámara escritos en globales: columnas [derecha, arriba, atrás]."""
        return marco_camara(*leer_camara(self.vista.renderer.GetActiveCamera()))

    def _flecha_en(self, x, y):
        """Nombre de la flecha que está en (x, y), o None. Solo cuentan si están a la vista."""
        if not self._flechas or not self._flechas["arriba"].GetVisibility():
            return None
        x0, y0, ancho, alto = self._recuadro()
        if ancho <= 0 or alto <= 0:
            return None
        p = np.array([(x - x0) / ancho, (y - y0) / alto])
        holgura = 0.02                                   # las flechas son chicas: se agarran con margen
        for nombre, puntos in self._zonas.items():
            minimo, maximo = puntos.min(axis=0) - holgura, puntos.max(axis=0) + holgura
            if np.all(p >= minimo) and np.all(p <= maximo):
                return nombre
        return None

    def _objetivo_en(self, x, y):
        """Qué hay en (x, y): ("flecha", nombre), ("anillo",), ("vista", dirección) o None."""
        if not self._en_recuadro(x, y):
            return None
        flecha = self._flecha_en(x, y)
        if flecha is not None:
            return ("flecha", flecha)
        if not self.picker.Pick(x, y, 0, self.widget.GetRenderer()):
            return None
        celda = self.picker.GetCellId()
        if celda < 0:
            return None
        parte = self._parte[celda]
        if parte in (ANILLO, LINEA_ANILLO):
            return ("anillo",)
        if parte != PARCHE:                     # línea del borde: no es una vista
            return None
        return ("vista", tuple(float(v) for v in self._direcciones[celda]))

    # ---------- Resaltado ----------
    def resaltar(self, x, y):
        """Sombrea en gris lo que está bajo el mouse (cara, arista, esquina, anillo o flecha) y
        muestra u oculta las flechas; fuera del cubo, quita el gris."""
        self._ultimo_mouse = (x, y)
        if self.animador.activa() or self._arrastre is not None:
            return                              # mientras gira, sigue en gris lo elegido
        cambio = self._mostrar_flechas(self._en_recuadro(x, y) and self._de_frente())
        objetivo = self._objetivo_en(x, y)
        if objetivo == self._resaltado and not cambio:
            return                              # no cambió: no se recolorea ni se vuelve a dibujar
        self._resaltado = objetivo
        self._pintar()
        self.vista.render()

    def _pintar(self):
        """Colores del marcador y de las flechas según lo resaltado."""
        nuevos = self._colores_base.copy()
        tipo = self._resaltado[0] if self._resaltado else None
        if tipo == "vista":
            nuevos[np.all(self._direcciones == np.array(self._resaltado[1]), axis=1)
                   & (self._parte == PARCHE)] = colores.rgb(colores.CUBO_RESALTADO)
        elif tipo == "anillo":
            nuevos[self._parte == ANILLO] = colores.rgb(colores.CUBO_RESALTADO)
        self.malla.cell_data["color"] = nuevos
        self._pintar_flechas()

    def _pintar_flechas(self):
        """Las flechas, en gris claro; la que está bajo el mouse, en el gris del borde."""
        elegida = self._resaltado[1] if self._resaltado and self._resaltado[0] == "flecha" else None
        for nombre, actor in self._flechas.items():
            color = colores.CUBO_BORDE if nombre == elegida else colores.CUBO_RESALTADO
            actor.GetProperty().SetColor(*(c / 255.0 for c in colores.rgb(color)))

    def _mostrar_flechas(self, visibles):
        """Muestra u oculta las flechas. Devuelve True si cambió algo (hay que volver a dibujar)."""
        cambio = False
        for actor in self._flechas.values():
            if bool(actor.GetVisibility()) != bool(visibles):
                actor.SetVisibility(bool(visibles))
                cambio = True
        return cambio

    def quitar_resaltado(self):
        """Vuelve el cubo a blanco (por ejemplo, cuando el mouse sale de la ventana)."""
        self.resaltar(-1, -1)                   # (-1, -1) está fuera del cubo

    def _al_terminar_giro(self):
        """La cámara terminó de girar: resalta lo que ahora está bajo el mouse."""
        self.resaltar(*self._ultimo_mouse)

    # ---------- Clic ----------
    def clic(self, x, y):
        """Si el clic cae sobre el cubo o una flecha, gira la cámara y devuelve True."""
        objetivo = self._objetivo_en(x, y)
        if objetivo is None or objetivo[0] == "anillo":
            return False
        if objetivo[0] == "flecha":
            self._usar_flecha(objetivo[1])
            return True
        d = np.array(objetivo[1])
        d /= np.linalg.norm(d)
        arriba = (0, 1, 0) if abs(d[2]) > 0.99 else (0, 0, 1)   # vista superior o inferior: +Y arriba
        self.animador.animar(lambda: self._mirar_desde(d, arriba))
        return True

    def _usar_flecha(self, nombre):
        """Un triángulo lleva a la cara vecina de ese lado; una flecha curva gira la vista 90°."""
        derecha, arriba, atras = self._marco().T
        if nombre in ARCOS_GIRO:
            # Girar la vista en sentido horario: lo que apuntaba hacia arriba pasa a apuntar a la
            # derecha, así que el nuevo "arriba" es lo que apuntaba a la izquierda
            nuevo = -derecha if nombre == "horario" else derecha
            camara = self.vista.renderer.GetActiveCamera()
            self.animador.animar(lambda: camara.SetViewUp(*nuevo))
            return
        derecha, arriba, atras = _eje(derecha), _eje(arriba), _eje(atras)
        # La cámara pasa al lado elegido girando 90°. Hacia arriba o hacia abajo, lo que quedaba al
        # frente (o atrás) pasa a ser el nuevo "arriba": así el giro es continuo
        destino = {"derecha": (derecha, arriba), "izquierda": (-derecha, arriba),
                   "arriba": (arriba, -atras), "abajo": (-arriba, atras)}[nombre]
        self.animador.animar(lambda: self._mirar_desde(*destino))

    def _mirar_desde(self, d, arriba):
        """Pone la cámara mirando desde la dirección d, sin encuadre: gira alrededor del mismo foco y a
        la misma distancia (y con el mismo zoom), así el modelo queda donde el usuario lo dejó.
        (view_vector de pyvista hace además un encuadre, que el usuario no quiere al usar el cubo.)"""
        d = np.asarray(d, dtype=float)
        d = d / np.linalg.norm(d)
        if abs(float(np.dot(d, arriba))) > 0.99:                # "arriba" paralelo a la vista: no sirve
            arriba = (0, 1, 0) if abs(d[2]) > 0.99 else (0, 0, 1)
        camara = self.vista.renderer.GetActiveCamera()
        foco = np.array(camara.GetFocalPoint())
        distancia = camara.GetDistance()
        camara.SetPosition(*(foco + d * distancia))
        camara.SetViewUp(*arriba)

    # ---------- Anillo ----------
    def _azimut(self, x, y):
        """Ángulo alrededor de Z (rad) del punto del plano del anillo que está bajo el mouse, o None
        si el anillo se ve casi de canto (el rayo del mouse va casi paralelo a su plano)."""
        renderer = self.widget.GetRenderer()
        extremos = []
        for profundidad in (0.0, 1.0):
            renderer.SetDisplayPoint(x, y, profundidad)
            renderer.DisplayToWorld()
            px, py, pz, w = renderer.GetWorldPoint()
            if abs(w) < 1e-12:
                return None
            extremos.append(np.array([px, py, pz]) / w)
        cerca, lejos = extremos
        rayo = lejos - cerca
        largo = float(np.linalg.norm(rayo))
        if largo < 1e-12 or abs(rayo[2]) < 0.2 * largo:
            return None
        punto = cerca + (Z_ANILLO - cerca[2]) / rayo[2] * rayo
        if math.hypot(punto[0], punto[1]) < 0.05:               # justo sobre el eje: sin dirección
            return None
        return math.atan2(punto[1], punto[0])

    def _girar_anillo(self, x, y):
        """Arrastre del anillo: gira la cámara alrededor de Z para que el punto que se tomó siga bajo
        el mouse. Si el anillo se ve de canto, se usa lo que el mouse se movió a lo ancho."""
        azimut = self._azimut(x, y)
        tomado = self._arrastre["azimut"]
        if azimut is not None and tomado is not None:
            # Girar la cámara un ángulo α alrededor de Z hace que el punto de azimut φ se vea donde
            # antes estaba el de φ − α. Para que el punto tomado quede bajo el mouse: α = tomado − azimut
            alfa = tomado - azimut
        elif azimut is None:
            # De canto: el lado cercano del anillo sigue al mouse. Moverlo a la derecha es girar el
            # modelo en sentido antihorario (visto desde arriba), o sea la cámara en horario
            ancho = self._recuadro()[2] or 1.0
            alfa = -(x - self._arrastre["x"]) / (ancho * SEMIVUELTA_PX) * math.pi
            self._arrastre["azimut"] = None
        else:
            alfa = 0.0
            self._arrastre["azimut"] = azimut                   # se vuelve a tomar el anillo aquí
        self._arrastre["x"] = x
        alfa = (alfa + math.pi) % (2.0 * math.pi) - math.pi     # el camino corto
        if abs(alfa) < 1e-9:
            return
        camara = self.vista.renderer.GetActiveCamera()
        posicion, foco, arriba = leer_camara(camara)
        c, s = math.cos(alfa), math.sin(alfa)
        giro = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        camara.SetPosition(*(foco + giro @ (posicion - foco)))
        camara.SetViewUp(*(giro @ arriba))
        self.vista.renderer.ResetCameraClippingRange()
        self.vista.render()

    # ---------- Eventos del mouse sobre la vista ----------
    def _pixeles(self, evento):
        """Posición del evento en píxeles de VTK: el eje y hacia arriba y en píxeles del dispositivo
        (la misma conversión que hace pyvistaqt antes de pasarle el evento a VTK)."""
        escala = self.vista.devicePixelRatioF()
        p = evento.position()
        return round(p.x() * escala), round((self.vista.height() - p.y() - 1) * escala)

    def eventFilter(self, objeto, evento):
        if objeto is not self.vista:
            return False
        tipo = evento.type()
        if tipo == QEvent.MouseMove:
            x, y = self._pixeles(evento)
            if self._arrastre is not None:
                self._girar_anillo(x, y)
                return True                     # el arrastre del anillo no le llega a la cámara
            if evento.buttons() == Qt.NoButton:
                self.resaltar(x, y)
        elif tipo == QEvent.MouseButtonPress and evento.button() == Qt.LeftButton:
            x, y = self._pixeles(evento)
            objetivo = self._objetivo_en(x, y)
            if objetivo == ("anillo",):
                self.animador.detener()
                self._arrastre = {"azimut": self._azimut(x, y), "x": x}
                return True
            self._presion = (x, y, objetivo) if objetivo is not None else None
        elif tipo == QEvent.MouseButtonRelease and evento.button() == Qt.LeftButton:
            x, y = self._pixeles(evento)
            if self._arrastre is not None:
                self._arrastre = None
                self.resaltar(x, y)
                return True
            presion, self._presion = self._presion, None
            if presion is not None and (abs(x - presion[0]) <= ui.TOL_CLIC_PX
                                        and abs(y - presion[1]) <= ui.TOL_CLIC_PX):
                self.clic(x, y)                 # presionar y soltar en el mismo lugar: un clic
        elif tipo == QEvent.Leave:
            if self._arrastre is None:
                self.quitar_resaltado()
        elif tipo == QEvent.Resize:
            QTimer.singleShot(0, self.ajustar_tamano)   # después de que la vista tome su tamaño
        return False

    def apagar(self):
        """Desactiva el widget (se llama antes de cerrar la ventana)."""
        self.vista.removeEventFilter(self)
        self.widget.SetEnabled(0)
