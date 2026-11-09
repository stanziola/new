import numpy as np
import pandas as pd
from configuracion.formato import GDL, FUERZAS, FUERZAS_LOCALES


def etiquetas_gdl(nodos):
    return [f"{g}{n}" for n in nodos for g in GDL]


def ver(M, nodos=None):
    """Muestra una matriz con etiquetas en la consola."""
    if nodos is None:
        nodos = range(M.shape[0] // 6)
    if len(nodos) * 6 != M.shape[0]:
        raise ValueError(f"La matriz es {M.shape[0]}x{M.shape[0]}, "
                         f"pero se dieron {len(nodos)} nodos ({len(nodos)*6} GDL)")

    M = np.where(np.abs(M) < 1e-9 * np.abs(M).max(), 0.0, M)   # borra ruido de redondeo
    et = etiquetas_gdl(nodos)
    df = pd.DataFrame(M, index=et, columns=et)

    print(df)


def mostrar(m, titulo):
    """Imprime los datos del modelo."""
    print(f"\n===== {titulo} =====")
    print("Materiales:")
    for mid, mat in m.materiales.items():
        print(f"  {mid}: {mat.nombre}  E={mat.e:.3e}  G={mat.g:.3e}")
    print("Secciones:")
    for sid, s in m.secciones.items():
        print(f"  {sid}: {s.nombre}  A={s.a}  Iy={s.iy}  Iz={s.iz}  J={s.j}")
    print("Nodos:")
    for nid, n in m.nodos.items():
        extra = f"  apoyo={n.apoyo}" if any(n.apoyo) else ""
        print(f"  {nid}: {n.coords}{extra}")
    print("Cargas:")
    for cid, c in m.cargas.items():
        print(f"  {cid}: caso {c.caso}  {c}")
    print("Elementos:")
    for eid, el in m.elementos.items():
        mat = "sin asignar" if el.material is None else el.material
        sec = "sin asignar" if el.seccion is None else el.seccion
        print(f"  {eid}: {el.ni} -> {el.nj}  mat={mat}  sec={sec}  alfa={el.alfa}°")


def mostrar_resultados(m, res):
    """Imprime desplazamientos, reacciones y fuerzas en extremos de barras."""
    print("\n===== DESPLAZAMIENTOS =====")
    print(pd.DataFrame(res.desplazamientos, index=GDL).T)

    print("\n===== REACCIONES =====")
    print(pd.DataFrame(res.reacciones, index=FUERZAS).T)

    print("\n===== FUERZAS EN EXTREMOS DE BARRAS (ejes locales) =====")
    filas, etiquetas = [], []
    for eid, f in res.fuerzas.items():
        el = m.elementos[eid]
        filas += [f[:6], f[6:]]
        etiquetas += [f"Barra {eid} nodo {el.ni}", f"Barra {eid} nodo {el.nj}"]
    print(pd.DataFrame(filas, index=etiquetas, columns=FUERZAS_LOCALES))