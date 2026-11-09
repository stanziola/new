"""Deshacer y rehacer: copias del modelo antes de cada cambio.

La forma más simple y segura: antes de cambiar el modelo se guarda una copia completa
(copy.deepcopy). Deshacer cambia el modelo actual por la última copia; lo que se deshizo pasa a la
pila de rehacer. Un cambio nuevo vacía la pila de rehacer (esa "rama" ya no existe).
Las copias incluyen los contadores de IDs: un objeto deshecho nunca existió, así que su ID puede
volver a usarse.
Para modelos chicos y medianos cada copia ocupa poco; el máximo de pasos es configurable.
"""
import copy

from configuracion import interfaz as ui


class Historial:
    def __init__(self):
        self.atras = []            # copias para deshacer (la última es la más reciente)
        self.adelante = []         # copias para rehacer

    def guardar(self, modelo, guardado):
        """Antes de un cambio: copia del modelo y si ese estado estaba guardado en el archivo."""
        self.atras.append((copy.deepcopy(modelo), guardado))
        del self.atras[:-max(1, ui.HISTORIAL_MAXIMO)]
        self.adelante.clear()

    def puede_deshacer(self):
        return bool(self.atras)

    def puede_rehacer(self):
        return bool(self.adelante)

    def deshacer(self, modelo, guardado):
        """Devuelve (modelo anterior, estaba guardado) y guarda el actual para rehacer."""
        self.adelante.append((copy.deepcopy(modelo), guardado))
        return self.atras.pop()

    def rehacer(self, modelo, guardado):
        self.atras.append((copy.deepcopy(modelo), guardado))
        return self.adelante.pop()

    def marcar_sin_guardar(self):
        """Después de guardar: ninguna copia del historial coincide ya con el archivo."""
        self.atras = [(m, False) for m, _ in self.atras]
        self.adelante = [(m, False) for m, _ in self.adelante]

    def vaciar(self):
        self.atras.clear()
        self.adelante.clear()
