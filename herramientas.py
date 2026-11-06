import pandas as pd
from configuracion import GDL

def etiquetas_gdl(nodos):
    return [f"{g}{n}" for n in nodos for g in GDL]

def ver(M, nodos=None):
    if nodos is None:
        nodos = range(M.shape[0] // 6)
    if len(nodos) * 6 != M.shape[0]:
        raise ValueError(f"La matriz es {M.shape[0]}x{M.shape[0]}, "
                         f"pero se dieron {len(nodos)} nodos ({len(nodos)*6} GDL)")
    et = etiquetas_gdl(nodos)
    print(pd.DataFrame(M, index=et, columns=et))