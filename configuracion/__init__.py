"""Configuración del programa, separada por tema.

| Archivo          | Qué tiene                                                               |
|------------------|-------------------------------------------------------------------------|
| calculo.py       | tolerancias numéricas del análisis                                      |
| unidades.py      | unidades internas (kN, m), unidades de pantalla y conversiones          |
| formato.py       | decimales, formato de tablas de consola y nombres de GDL y fuerzas      |
| interfaz.py      | tamaños, tiempos, tolerancias del mouse, atajos, rejilla, snap y cubo   |
| colores.py       | colores de la interfaz (solo grises) y del dibujo 3D                    |
| preferencias.py  | lo que el usuario cambia en Configuración, guardado aparte en un JSON   |

Los valores de estos archivos son la "personalización base" del programa. Lo que el usuario
cambia desde Configuración se guarda aparte (preferencias.py) y se aplica encima al abrir.
"""
