"""Modelo: los datos de la estructura y su archivo .json. No es cálculo (eso está en calculo/).

- estructura.py: Modelo, Nodo, Material, Seccion (con Concreto: su refuerzo), Elemento, casos,
  cargas y combinaciones.
- concreto.py: nombres, familias y cambios de materiales y secciones de concreto.
- apoyos.py: los tipos de apoyo.
- combinaciones.py: las combinaciones predeterminadas (ASCE 7-05), con el SDS y el ρ del modelo.
- analisis.py: el puente del modelo al cálculo (cargas de cada caso, peso propio, combinaciones por
  superposición, diagramas).
- interaccion.py: el refuerzo de una sección pasado a los diagramas de interacción, y la posición y el
  diámetro de sus barras.
- archivo.py: guardar y abrir modelos en .json.
"""
from modelo.estructura import (CargaBarra, CargaNodal, Caso, Combinacion, Concreto, Elemento, Material,  # noqa: F401
                               Modelo, Nodo, Seccion)
