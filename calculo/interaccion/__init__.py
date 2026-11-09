"""Diagramas de interacción de columnas de concreto (ACI 318-19). Parte del cálculo sagrado.

- comun.py: barras, β1, fy, cuantía y propiedades de la sección rectangular.
- rectangular.py: flexión en un eje (antes en iteracion2drect.py).
- circular.py: columna circular (antes en iteracion2dcir.py).
- biaxial.py: rectangular con flexión en cualquier dirección θ (antes en iteracion3drect.py).

Las funciones se movieron sin cambios desde los scripts iteracion*.py, que ahora solo dibujan.
Entradas con pint; salidas en tonne_force (tonelada métrica = 1000 kgf) y tonne_force·m.
"""
