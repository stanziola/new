"""Método de rigidez para pórticos 3D (barras de Euler-Bernoulli). Parte del cálculo sagrado.

- barra.py: matriz de rigidez local 12x12, ángulos, rotación R = A·B·C, transformación y la matriz
  global de una barra.
- ensamble.py: matriz K global.
- solucion.py: K·U = F con apoyos, reacciones y fuerzas en los extremos de las barras.
- resultados.py: la clase Resultados (solo guarda datos).
"""
