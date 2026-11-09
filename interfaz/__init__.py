"""Interfaz gráfica (PySide6 + PyVista). Solo muestra y recibe: no hace cálculos de ingeniería.

- ventana.py: la ventana principal, que une todo.
- tema.py, iconos.py: aspecto (grises) e íconos propios.
- herramientas.py: lo que hace un clic (Seleccionar, Nodo, Elemento, Asignar sección, Apoyo, cargas...).
- historial.py: Deshacer y Rehacer.
- textos.py: textos de cargas y resultados, y los nombres de materiales y secciones en las unidades vigentes.
- vista3d/: el dibujo 3D, el cubo de vistas, la cámara, la rejilla y la selección.
- paneles/: el Explorador, Propiedades (con la pestaña Interacción), el panel Diagrama y sus piezas
  (formularios, árboles, título, CampoNumero).
- ventanas/: ventanas aparte (Configuración, Materiales y Secciones, Casos y Combinaciones, matriz K,
  diagramas de interacción).
"""
