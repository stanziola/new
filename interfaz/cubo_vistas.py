"""Cubo de vistas, como el ViewCube de Civil 3D.

El cubo está en la esquina superior derecha y gira junto con la cámara. Con un clic sobre una
cara se mira el modelo desde esa cara; sobre una arista o una esquina, desde una vista
intermedia (26 vistas en total).

Cómo funciona:
- Cada cara del cubo se divide en 3x3 parches: el del centro es la cara; los de los bordes son
  aristas; los de las puntas son esquinas. Cada parche guarda la dirección desde la que se mira
  (por ejemplo, la arista entre +X y +Z guarda (1, 0, 1)).
- El cubo es el "marcador" de un vtkOrientationMarkerWidget, que copia la orientación de la
  cámara principal en cada render.
- Para saber qué parche se tocó, se usa un vtkCellPicker sobre el renderer del widget.
"""
import numpy as np
import pyvista as pv
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingCore import vtkActor, vtkCellPicker, vtkPolyDataMapper

from interfaz import estilo as es

# Normal de cada cara y dos ejes en su plano (u x v = normal, para que el parche mire hacia afuera)
CARAS = [
    ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    ((0, 0, -1), (0, 1, 0), (1, 0, 0)),
]


def _parches():
    """Superficie del cubo (lado 1) con 9 parches por cara y la dirección de vista de cada uno."""
    f = es.CUBO_FRANJA
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
    malla.cell_data["color"] = np.tile(np.array(es.CUBO_COLOR_CARA, dtype=np.uint8), (malla.n_cells, 1))
    return malla


def _letras():
    """Texto de cada cara ("+X", "-Z"...), derecho al mirar la cara desde afuera.

    Las caras laterales tienen +Z hacia arriba. La de arriba se orienta para leerse derecha en la
    vista isométrica inicial (cámara desde +X +Y +Z), como en el cubo de Civil 3D.
    """
    partes = []
    for n, _, _ in CARAS:
        n = np.array(n, dtype=float)
        if n[2] > 0.5:                      # cara superior
            arriba = np.array([-1.0, -1.0, 0.0]) / np.sqrt(2)
        elif n[2] < -0.5:                   # cara inferior
            arriba = np.array([0.0, 1.0, 0.0])
        else:                               # caras laterales
            arriba = np.array([0.0, 0.0, 1.0])
        derecha = np.cross(arriba, n)       # hacia la derecha de quien mira la cara
        texto = pv.Text3D(es.CUBO_LETRAS[tuple(int(c) for c in n)], depth=0.02)
        xmin, xmax, ymin, ymax, _, _ = texto.bounds
        p = (texto.points - [(xmin + xmax) / 2, (ymin + ymax) / 2, 0]) * (0.32 / (ymax - ymin))
        rot = np.column_stack([derecha, arriba, n])     # ejes del texto -> ejes del mundo
        texto.points = p @ rot.T + 0.515 * n
        texto.cell_data["direccion"] = np.tile(n, (texto.n_cells, 1))   # clic en la letra = clic en la cara
        texto.cell_data["color"] = np.tile(np.array(es.CUBO_COLOR_LETRA, dtype=np.uint8), (texto.n_cells, 1))
        partes.append(texto)
    return pv.merge(partes)


def _borde_y_anillo():
    """Aristas del cubo y anillo inferior (solo decoración: su dirección es 0 y no se pueden elegir)."""
    borde = pv.Box(bounds=(-0.5, 0.5, -0.5, 0.5, -0.5, 0.5)).extract_all_edges()
    anillo = pv.Disc(center=(0, 0, -0.55), inner=0.78, outer=0.92, normal=(0, 0, 1), c_res=48)
    for malla, color in ((borde, es.CUBO_COLOR_BORDE), (anillo, es.CUBO_COLOR_ANILLO)):
        malla.cell_data["direccion"] = np.zeros((malla.n_cells, 3))
        malla.cell_data["color"] = np.tile(np.array(color, dtype=np.uint8), (malla.n_cells, 1))
    return pv.merge([borde, anillo])


class CuboVistas:
    def __init__(self, vista):
        self.vista = vista
        self.malla = pv.merge([_parches(), _letras(), _borde_y_anillo()])

        mapper = vtkPolyDataMapper()
        mapper.SetInputData(self.malla)
        mapper.SetScalarModeToUseCellFieldData()   # color por celda, tomado del arreglo "color"
        mapper.SelectColorArray("color")
        mapper.SetColorModeToDirectScalars()
        actor = vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetLineWidth(2)
        prop.SetAmbient(0.6)                    # más luz ambiente: colores claros como en Civil 3D
        prop.SetDiffuse(0.5)
        prop.SetSpecular(0.0)

        self.widget = vtkOrientationMarkerWidget()
        self.widget.SetOrientationMarker(actor)
        self.widget.SetInteractor(vista.iren.interactor)
        self.widget.SetDefaultRenderer(vista.renderer)  # copia la cámara de la vista principal
        self.widget.SetViewport(*es.CUBO_VIEWPORT)
        self.widget.SetEnabled(1)
        self.widget.InteractiveOff()            # el cubo no se arrastra ni cambia de tamaño
        self.picker = vtkCellPicker()
        self.picker.SetTolerance(0.0005)

    def contiene(self, x, y):
        """True si el punto (x, y), en píxeles de la vista, cae dentro de la zona del cubo."""
        ancho, alto = self.vista.ren_win.GetSize()
        x0, y0, x1, y1 = self.widget.GetViewport()
        return x0 * ancho <= x <= x1 * ancho and y0 * alto <= y <= y1 * alto

    def clic(self, x, y):
        """Si el clic cae sobre el cubo, orienta la cámara desde ese lado y devuelve True."""
        if not self.contiene(x, y):
            return False
        if not self.picker.Pick(x, y, 0, self.widget.GetRenderer()):
            return False
        celda = self.picker.GetCellId()
        if celda < 0:
            return False
        d = np.array(self.malla.cell_data["direccion"][celda], dtype=float)
        if not d.any():                         # borde o anillo: no cambia la vista
            return False
        d /= np.linalg.norm(d)
        arriba = (0, 1, 0) if abs(d[2]) > 0.99 else (0, 0, 1)   # vista superior o inferior: +Y arriba
        self.vista.view_vector(d, viewup=arriba)
        return True

    def apagar(self):
        """Desactiva el widget (se llama antes de cerrar la ventana)."""
        self.widget.SetEnabled(0)
