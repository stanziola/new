import numpy as np
import pandas as pd
from configuracion import GDL

def etiquetas_gdl(nodos):
    return [f"{g}{n}" for n in nodos for g in GDL]

def ver(M, nodos=None, archivo=None):
    """Muestra una matriz con etiquetas. Si se da 'archivo', la guarda en CSV (para Excel)."""
    if nodos is None:
        nodos = range(M.shape[0] // 6)
    if len(nodos) * 6 != M.shape[0]:
        raise ValueError(f"La matriz es {M.shape[0]}x{M.shape[0]}, "
                         f"pero se dieron {len(nodos)} nodos ({len(nodos)*6} GDL)")

    M = np.where(np.abs(M) < 1e-9 * np.abs(M).max(), 0.0, M)   # borra ruido de redondeo
    et = etiquetas_gdl(nodos)
    df = pd.DataFrame(M, index=et, columns=et)

    if archivo:
        df.to_csv(archivo, sep=";", decimal=",")   # formato de Excel en español
        print(f"Matriz guardada en {archivo}")
    else:
        print(df)