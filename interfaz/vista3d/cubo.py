"""Cubo de vistas, como el ViewCube de Civil 3D.

El cubo es blanco, plano (sin iluminación) y sin letras. Está en la esquina superior derecha y
gira junto con la cámara. Al pasar el mouse se sombrea en gris la cara, arista o esquina que está
debajo. Con un clic, la cámara gira con una animación corta hasta mirar el modelo desde ese lado:
desde la cara, o desde una vista intermedia si es una arista o una esquina (26 vistas en total).

Cómo funciona:
- Cada cara del cubo se divide en 3x3 parches: el del centro es la cara; los de los bordes son
  aristas; los de las puntas son esquinas. Cada parche guarda la dirección desde la que se mira
  (por ejemplo, la arista entre +X y +Z guarda (1, 0, 1)).
- El cubo es el "marcador" de un vtkOrientationMarkerWidget, que copia la orientación de la
  cámara principal en cada render.
- Para saber qué parche se tocó, se usa un vtkCellPicker sobre el renderer del widget.
- Una arista está formada por 2 parches (uno en cada cara que llega a ella) y una esquina por 3.
  Todos guardan la misma dirección, así que para resaltar la esquina completa se pintan todos
  los parches con esa dirección, no solo el que está bajo el mouse.
- El giro lo hace el AnimadorCamara (interfaz/camara.py), el mismo que usa el botón Encuadre.
"""
import numpy as np
import pyvista as pv
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingCore import vtkActor, vtkCellPicker, vtkPolyDataMapper

from configuracion import colores
from configuracion import interfaz as ui

# Normal de cada cara y dos ejes en su plano (u x v = normal, para que el parche mire hacia afuera)
CARAS = [
    ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    ((0, 0, -1), (0, 1, 0), (1, 0, 0)),
]


def viewport_esquina(ancho, alto, tamano, esquina):
    """Viewport (x0, y0, x1, y1) de un cuadrado de lado `tamano` (fracción del alto) en una esquina.

    Cuadrado en píxeles y a MARGEN_ESQUINA_PX del borde. Lo usan el cubo (arriba a la derecha) y
    los ejes X, Y, Z (abajo a la izquierda), para que queden proporcionados.
    """
    lado = min(tamano, 0.9) * alto                     # lado en píxeles
    m = ui.MARGEN_ESQUINA_PX
    if esquina == "arriba_derecha":
        x0, y0 = ancho - m - lado, alto - m - lado
    else:                                              # abajo a la izquierda
        x0, y0 = m, m
    return (max(x0, 0) / ancho, max(y0, 0) / alto, min(x0 + lado, ancho) / ancho, min(y0 + lado, alto) / alto)


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
    malla.cell_data["color"] = np.tile(np.array(colores.rgb(colores.CUBO_CARA), dtype=np.uint8),
                                       (malla.n_cells, 1))
    return malla


def _borde():
    """Líneas de las aristas del cubo (solo decoración: su dirección es 0 y no se pueden elegir)."""
    borde = pv.Box(bounds=(-0.5, 0.5, -0.5, 0.5, -0.5, 0.5)).extract_all_edges()
    borde.cell_data["direccion"] = np.zeros((borde.n_cells, 3))
    borde.cell_data["color"] = np.tile(np.array(colores.rgb(colores.CUBO_BORDE), dtype=np.uint8),
                                       (borde.n_cells, 1))
    return borde


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


class CuboVistas:
    def __init__(self, vista, animador):
        self.vista = vista
        self.animador = animador                # AnimadorCamara compartido con Encuadre
        self.malla = pv.merge([_parches(), _borde()])
        self._colores_base = np.array(self.malla.cell_data["color"])    # copia, para quitar el gris
        self._direcciones = np.array(self.malla.cell_data["direccion"], dtype=float)
        self._resaltado = None                  # dirección resaltada ahora (None = nada)
        self._ultimo_mouse = (-1, -1)           # para actualizar el gris al terminar un giro

        self.widget = vtkOrientationMarkerWidget()
        self.widget.SetOrientationMarker(_actor(self.malla))
        self.widget.SetInteractor(vista.iren.interactor)
        self.widget.SetDefaultRenderer(vista.renderer)  # copia la cámara de la vista principal
        self.widget.SetEnabled(1)
        self.widget.InteractiveOff()            # el cubo no se arrastra ni cambia de tamaño
        self.ajustar_tamano()
        self.picker = vtkCellPicker()
        self.picker.SetTolerance(0.0005)

        # Al terminar cualquier giro (del cubo o de Encuadre), el gris se pone al día
        self.animador.terminada.connect(self._al_terminar_giro)

    def ajustar_tamano(self):
        """Cubo cuadrado con lado CUBO_TAMANO (fracción del alto de la vista), arriba a la derecha,
        separado MARGEN_ESQUINA_PX de la esquina.

        Se llama al crear el cubo, al cambiar el tamaño de la ventana y al cambiar Configuración.
        """
        ancho, alto = self.vista.ren_win.GetSize()
        if ancho <= 0 or alto <= 0:
            return
        self.widget.SetViewport(*viewport_esquina(ancho, alto, ui.CUBO_TAMANO, "arriba_derecha"))

    def actualizar_colores(self):
        """Toma los colores vigentes del cubo (después de cambiarlos en Configuración)."""
        es_borde = ~self._direcciones.any(axis=1)        # las líneas del borde tienen dirección 0
        base = np.empty((len(self._direcciones), 3), dtype=np.uint8)
        base[:] = colores.rgb(colores.CUBO_CARA)
        base[es_borde] = colores.rgb(colores.CUBO_BORDE)
        self._colores_base = base
        self._resaltado = None
        self.malla.cell_data["color"] = base.copy()

    def contiene(self, x, y):
        """True si el punto (x, y), en píxeles de la vista, cae dentro de la zona del cubo."""
        ancho, alto = self.vista.ren_win.GetSize()
        x0, y0, x1, y1 = self.widget.GetViewport()
        return x0 * ancho <= x <= x1 * ancho and y0 * alto <= y <= y1 * alto

    def _direccion_en(self, x, y):
        """Dirección de vista (sin normalizar) de la cara, arista o esquina en (x, y), o None."""
        if not self.contiene(x, y):
            return None
        if not self.picker.Pick(x, y, 0, self.widget.GetRenderer()):
            return None
        celda = self.picker.GetCellId()
        if celda < 0:
            return None
        d = self._direcciones[celda]
        if not d.any():                         # línea del borde: no es una vista
            return None
        return d.copy()

    # ---------- Resaltado ----------
    def resaltar(self, x, y):
        """Sombrea en gris la cara, arista o esquina bajo el mouse; fuera del cubo, quita el gris."""
        self._ultimo_mouse = (x, y)
        if self.animador.activa():
            return                              # mientras gira, sigue en gris la vista elegida
        d = self._direccion_en(x, y)
        if (d is None and self._resaltado is None) or (
                d is not None and self._resaltado is not None and np.array_equal(d, self._resaltado)):
            return                              # no cambió: no se recolorea ni se vuelve a dibujar
        self._resaltado = d
        nuevos = self._colores_base.copy()
        if d is not None:
            nuevos[np.all(self._direcciones == d, axis=1)] = colores.rgb(colores.CUBO_RESALTADO)
        self.malla.cell_data["color"] = nuevos
        self.vista.render()

    def quitar_resaltado(self):
        """Vuelve el cubo a blanco (por ejemplo, cuando el mouse sale de la ventana)."""
        self.resaltar(-1, -1)                   # (-1, -1) está fuera del cubo

    def _al_terminar_giro(self):
        """La cámara terminó de girar: resalta lo que ahora está bajo el mouse."""
        self.resaltar(*self._ultimo_mouse)

    # ---------- Clic ----------
    def clic(self, x, y):
        """Si el clic cae sobre el cubo, gira la cámara hasta mirar desde ese lado y devuelve True."""
        d = self._direccion_en(x, y)
        if d is None:
            return False
        d /= np.linalg.norm(d)
        arriba = (0, 1, 0) if abs(d[2]) > 0.99 else (0, 0, 1)   # vista superior o inferior: +Y arriba
        self.animador.animar(lambda: self._mirar_desde(d, arriba))
        return True

    def _mirar_desde(self, d, arriba):
        """Pone la cámara mirando desde la dirección d, sin encuadre: gira alrededor del mismo foco y a
        la misma distancia (y con el mismo zoom), así el modelo queda donde el usuario lo dejó.
        (view_vector de pyvista hace además un encuadre, que el usuario no quiere al usar el cubo.)"""
        camara = self.vista.renderer.GetActiveCamera()
        foco = np.array(camara.GetFocalPoint())
        distancia = camara.GetDistance()
        camara.SetPosition(*(foco + np.asarray(d) * distancia))
        camara.SetViewUp(*arriba)

    def apagar(self):
        """Desactiva el widget (se llama antes de cerrar la ventana)."""
        self.widget.SetEnabled(0)
