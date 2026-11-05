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

TOL_LONGITUD = 1e-9
TOL_RELATIVA = 1e-9