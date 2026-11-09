"""La clase con los resultados de un análisis (separada de las fórmulas)."""
from dataclasses import dataclass

import numpy as np


@dataclass
class Resultados:
    ids: list                # IDs de nodo en el orden de K
    K: np.ndarray            # matriz de rigidez global
    F: np.ndarray            # vector de cargas
    U: np.ndarray            # vector de desplazamientos
    R: np.ndarray            # vector de reacciones (0 en GDL libres)
    desplazamientos: dict    # id nodo -> [Dx, Dy, Dz, Phix, Phiy, Phiz]
    reacciones: dict         # id nodo con apoyo -> [Fx, Fy, Fz, Mx, My, Mz]
    fuerzas: dict            # id elemento -> 12 fuerzas en ejes locales
