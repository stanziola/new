"""Medir: la distancia entre dos puntos del modelo, con snap automático (barra de arriba, a la derecha).

Se activa con su botón y sirve en los tres estados (editando, con resultados de un caso o de una
combinación) y en los sistemas de vigueta: no cambia el modelo ni entra en Deshacer. Dos clics: el
primer punto y el segundo; un tercer clic empieza otra medición; Esc la borra (y otro Esc apaga Medir).

Snap automático: el puntero se pega, en este orden de prioridad, a lo que esté a menos de TOL_PX en
la pantalla:
1. un nodo;
2. un vértice del concreto dibujado (las cajas de vigas y columnas, los bloques de los nudos y la losa);
3. el punto medio de una arista de ese concreto;
4. con el primer punto ya puesto, el pie de la perpendicular desde él a una arista del concreto o al eje
   de una barra: con el primer punto en la cara de una viga, da la distancia libre hasta la otra viga;
5. un punto sobre el eje de una barra;
6. un cruce de la rejilla.
Si no hay nada cerca, cae en el plano de la base (como el snap de Nodo y Elemento).
Lo medido se ve como una cota (colores.MEDICION) con su texto y, en la barra de estado,
"L = … · Δx · Δy · Δz" en las unidades de pantalla.
"""
from dataclasses import dataclass

import numpy as np
import pyvista as pv

from configuracion import colores, formato
from configuracion import interfaz as ui
from interfaz.vista3d.rejilla import base_del_modelo, cruce_cercano, punto_en_base
from interfaz.vista3d.seleccion import a_pantalla, proyectar

TOL_PX = 12                            # distancia en pantalla para pegarse (constante interna, como el snap)
NOMBRES = {"nodo": "nodo", "vertice": "vértice", "medio": "punto medio", "perpendicular": "perpendicular",
           "eje": "en el eje", "rejilla": "rejilla", "libre": "libre"}


@dataclass
class Punto:
    punto: np.ndarray
    tipo: str                          # una clave de NOMBRES


def _aristas(malla):
    """Aristas únicas de una malla de polígonos: arreglo (n, 2, 3) con sus extremos."""
    if malla is None or malla.n_cells == 0:
        return np.zeros((0, 2, 3))
    pares = set()
    caras = malla.faces
    i = 0
    while i < len(caras):
        n = caras[i]
        ids = caras[i + 1:i + 1 + n]
        for a, b in zip(ids, np.roll(ids, -1)):
            pares.add((min(a, b), max(a, b)))
        i += n + 1
    puntos = np.asarray(malla.points, dtype=float)
    return np.array([[puntos[a], puntos[b]] for a, b in pares]) if pares else np.zeros((0, 2, 3))


class Medicion:
    """El estado de una medición: los puntos elegidos, lo que se dibuja y los candidatos del snap."""

    def __init__(self, ventana):
        self.ventana = ventana
        self.puntos = []                  # 0, 1 o 2 Punto
        self.actores = {}
        self._candidatos = None           # (clave del dibujo, vértices, medios, aristas)

    # ---------- Candidatos del snap ----------
    def _preparar(self):
        """Vértices, puntos medios y aristas del concreto dibujado (se guardan hasta que se redibuje)."""
        d = self.ventana.dibujado
        if self._candidatos is not None and self._candidatos[0] is d:
            return self._candidatos
        aristas = [_aristas(d.mallas.get(nombre)) for nombre in ("solidos", "losas")]
        aristas = np.concatenate([a for a in aristas if len(a)]) if any(len(a) for a in aristas) else np.zeros((0, 2, 3))
        vertices = np.unique(aristas.reshape(-1, 3).round(9), axis=0) if len(aristas) else np.zeros((0, 3))
        medios = aristas.mean(axis=1) if len(aristas) else np.zeros((0, 3))
        self._candidatos = (d, vertices, medios, aristas)
        return self._candidatos

    def _segmentos_ejes(self):
        m = self.ventana.modelo
        return np.array([[m.nodos[el.ni].coords, m.nodos[el.nj].coords] for el in m.elementos.values()],
                        dtype=float).reshape(-1, 2, 3)

    @staticmethod
    def _mas_cercano(renderer, puntos, x, y):
        """(distancia en px, índice) del punto más cercano en pantalla, o (inf, None)."""
        if len(puntos) == 0:
            return np.inf, None
        xy, _p, delante = proyectar(renderer, puntos)
        dist = np.where(delante, np.linalg.norm(xy - np.array([x, y]), axis=1), np.inf)
        i = int(np.argmin(dist))
        return float(dist[i]), i

    def _pie(self, origen, segmentos):
        """El pie de la perpendicular desde origen a cada segmento (recortado al segmento)."""
        a, b = segmentos[:, 0], segmentos[:, 1]
        ab = b - a
        largo2 = np.einsum("ij,ij->i", ab, ab)
        t = np.where(largo2 > 0, np.einsum("ij,ij->i", origen - a, ab) / np.where(largo2 > 0, largo2, 1), 0.0)
        return a + np.clip(t, 0.0, 1.0)[:, None] * ab

    def snap(self, x, y):
        """El Punto donde caería un clic en (x, y) de la pantalla."""
        v = self.ventana
        r = v.vista.renderer
        m = v.modelo
        nodos = np.array([n.coords for n in m.nodos.values()], dtype=float).reshape(-1, 3)
        _d, vertices, medios, aristas = self._preparar()
        for tipo, puntos in (("nodo", nodos), ("vertice", vertices), ("medio", medios)):
            dist, i = self._mas_cercano(r, puntos, x, y)
            if dist <= TOL_PX:
                return Punto(np.array(puntos[i], dtype=float), tipo)
        ejes = self._segmentos_ejes()
        if self.puntos and len(self.puntos) == 1:
            segmentos = np.concatenate([s for s in (aristas, ejes) if len(s)]) if (len(aristas) or len(ejes)) else []
            if len(segmentos):
                pies = self._pie(self.puntos[0].punto, segmentos)
                dist, i = self._mas_cercano(r, pies, x, y)
                if dist <= TOL_PX:
                    return Punto(pies[i], "perpendicular")
        if len(ejes):
            clic = np.array([x, y], dtype=float)
            mejor = None
            for a, b in ejes:
                pa, pb = a_pantalla(r, a), a_pantalla(r, b)
                ab = pb - pa
                largo2 = ab @ ab
                t = 0.0 if largo2 == 0 else float(np.clip((clic - pa) @ ab / largo2, 0.0, 1.0))
                dist = float(np.linalg.norm(clic - (pa + t * ab)))
                if dist <= TOL_PX and (mejor is None or dist < mejor[0]):
                    mejor = (dist, a + t * (b - a))
            if mejor is not None:
                return Punto(np.asarray(mejor[1], dtype=float), "eje")
        if v.rejilla is not None and v.accion_snap.isChecked():
            cruce = cruce_cercano(r, x, y, v.rejilla, ui.TOL_SNAP_PX)
            if cruce is not None:
                return Punto(np.asarray(cruce, dtype=float), "rejilla")
        libre = punto_en_base(r, x, y, base_del_modelo(m))
        return Punto(np.asarray(libre, dtype=float), "libre") if libre is not None else None

    # ---------- Lo que hace el usuario ----------
    def mover(self, x, y):
        """El mouse se movió: la marca del snap y, con el primer punto puesto, la cota provisional."""
        p = self.snap(x, y)
        self._dibujar(p)
        return p

    def clic(self, x, y):
        p = self.snap(x, y)
        if p is None:
            return
        if len(self.puntos) >= 2:
            self.puntos = []
        self.puntos.append(p)
        self._dibujar(None)
        if len(self.puntos) == 2:
            self.ventana.coordenadas.setText(f"Medido: {self.texto()}")
            self.ventana.mensaje(self.texto())
        else:
            self.ventana.mensaje(f"Primer punto ({NOMBRES[p.tipo]}): ahora el segundo")

    def cancelar(self):
        """Esc: borra la medición. Devuelve True si había algo."""
        habia = bool(self.puntos) or bool(self.actores)
        self.puntos = []
        self._quitar()
        return habia

    def texto(self, hasta=None):
        """"L = 7.300 m · Δx 7.300 · Δy 0.000 · Δz 0.000 m" entre los dos puntos (o hasta `hasta`)."""
        a = self.puntos[0].punto
        b = hasta if hasta is not None else self.puntos[1].punto
        d = b - a
        partes = [f"L = {formato.cantidad(float(np.linalg.norm(d)), 'longitud')}"]
        partes += [f"Δ{eje} {formato.cantidad(float(abs(c)), 'longitud', False)}" for eje, c in zip("xyz", d)]
        return " · ".join(partes) + f" {formato.unidades.simbolo('longitud')}"

    # ---------- Dibujo ----------
    def _quitar(self):
        for actor in self.actores.values():
            self.ventana.vista.remove_actor(actor, render=False)
        self.actores = {}
        self.ventana.vista.render()

    def _dibujar(self, cursor):
        """Las marcas de los puntos, la cota y la marca del snap bajo el cursor."""
        vista = self.ventana.vista
        for actor in self.actores.values():
            vista.remove_actor(actor, render=False)
        self.actores = {}
        tamano = self.ventana._tamano()
        radio = 0.006 * tamano
        puntos = [p.punto for p in self.puntos]
        if cursor is not None and len(self.puntos) < 2:
            puntos_cota = puntos + [cursor.punto] if self.puntos else []
        else:
            puntos_cota = puntos
        piezas = [pv.Sphere(radius=radio, center=p, theta_resolution=12, phi_resolution=12) for p in puntos]
        if cursor is not None:
            lado = 2.2 * radio                         # la marca del snap: un cubito
            piezas.append(pv.Cube(center=cursor.punto, x_length=lado, y_length=lado, z_length=lado))
        if piezas:
            malla = piezas[0].merge(piezas[1:]) if len(piezas) > 1 else piezas[0]
            self.actores["marcas"] = vista.add_mesh(malla, color=colores.MEDICION, pickable=False,
                                                    reset_camera=False, name="medicion_marcas", render=False)
        if len(puntos_cota) == 2:
            a, b = puntos_cota
            self.actores["cota"] = vista.add_mesh(pv.Line(a, b), color=colores.MEDICION, line_width=2,
                                                  pickable=False, reset_camera=False, name="medicion_cota",
                                                  render=False)
            texto = self.texto(hasta=b) if self.puntos else ""
            self.actores["texto"] = vista.add_point_labels(
                np.array([(a + b) / 2]), [texto.split(" · ")[0]], font_size=ui.TAMANO_LETRA, text_color=colores.MEDICION,
                shape=None, show_points=False, always_visible=True, name="medicion_texto", reset_camera=False)
        if cursor is not None:
            nombre = NOMBRES[cursor.tipo]
            self.ventana.coordenadas.setText(f"Medir · snap: {nombre}"
                                             + (f" · {self.texto(hasta=cursor.punto)}" if self.puntos and len(self.puntos) == 1 else ""))
        vista.render()
