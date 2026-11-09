"""Configuración del programa, separada por tema. Solo presentación: nada de aquí cambia resultados.

| Archivo          | Qué tiene                                                               |
|------------------|-------------------------------------------------------------------------|
| unidades.py      | unidades internas (kN, m), unidad de pantalla de cada magnitud (Ftool),  |
|                  | con las dimensiones de sección aparte, y magnitudes derivadas (F/L³)     |
| formato.py       | decimales de cada magnitud, tablas de consola y nombres de GDL y fuerzas |
| interfaz.py      | tamaños, rejilla, cubo y ejes, animación y constantes del mouse          |
| colores.py       | colores de la interfaz (solo grises) y del dibujo 3D                     |
| preferencias.py  | lo que el usuario cambia en Configuración, guardado aparte en un JSON    |

Los valores de estos archivos son la "personalización base" del programa. Lo que el usuario
cambia desde Configuración se guarda aparte (preferencias.py) y se aplica encima al abrir.
Las tolerancias del cálculo NO están aquí: son parte del cálculo sagrado (calculo/tolerancias.py).
"""
