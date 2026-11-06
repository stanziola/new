def configurar():
    import sys
    import numpy as np
    import pandas as pd

    sys.stdout.reconfigure(encoding="utf-8")

    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 250)
    pd.set_option("display.float_format", "{:.3e}".format)

    np.set_printoptions(precision=3, suppress=True, linewidth=250)

# Tolerancias
TOL_LONGITUD = 1e-9
TOL_RELATIVA = 1e-9

# Etiquetas para mostrar resultados
GDL = ["Dx", "Dy", "Dz", "Phix", "Phiy", "Phiz"]       # desplazamientos
FUERZAS = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]         # ejes globales (cargas, reacciones)
FUERZAS_LOCALES = ["N", "Vy", "Vz", "T", "My", "Mz"]   # ejes locales de barra