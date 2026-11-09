"""Tolerancias numéricas del análisis (en unidades internas: kN y m)."""
TOL_LONGITUD = 1e-9     # dos puntos más cerca que esto (m) son el mismo punto
TOL_RELATIVA = 1e-9     # tolerancia relativa para decidir hacia dónde apunta una barra
COND_MAXIMA = 1e12      # si cond(Kll) pasa de esto, la estructura es inestable (mecanismo)
