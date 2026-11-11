"""Generador de la memoria de cálculo en Word (python -m scripts.memoria).

- __main__.py: arma el documento (portada, índice y capítulos), lo guarda y actualiza el índice.
- documento.py: la clase Memoria, con las piezas del documento (títulos, párrafos, ecuaciones,
  tablas, código, figuras y comprobaciones) y todo su formato.
- ecuaciones.py: LaTeX → ecuación de Word.
- word.py: lo que solo Word sabe hacer (llenar el índice, exportar a PDF).
- capitulos/: un módulo por tema, con una función capitulo(m) que escribe su contenido.

No tiene fórmulas del programa: las lee de calculo/ (para mostrar su código y para comparar sus
resultados con cálculos a mano). No cambia nada del programa.
"""
