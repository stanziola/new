"""CÁLCULO ESTRUCTURAL — SAGRADO.

Aquí está solo el cálculo estructural: lo que decide los resultados.
- elemento.py: matriz de rigidez local 12x12, ángulos, rotación R = A·B·C y transformación.
- ensamble.py: matriz K global y vector F.
- analisis.py: solución de K·U = F, reacciones y fuerzas en los extremos de las barras.
- tolerancias.py: tolerancias numéricas y el límite de inestabilidad.
- interaccion/: diagramas de interacción de columnas (ACI 318-19).

Reglas:
- No se cambia sin un pedido explícito del usuario que nombre esta carpeta.
- Claude Code pide permiso antes de editar cualquier archivo de aquí (.claude/settings.json).
- `python -m pruebas.integridad` compara las huellas de estos archivos con las aprobadas y
  recalcula resultados de referencia. Si algo cambió, lo dice.
- Después de revisar y aprobar un cambio: `python -m pruebas.integridad --aprobar`.
- Los commits que cambian esta carpeta empiezan con "CALCULO:".

Nada de aquí depende de la interfaz ni de la configuración de pantalla.
"""
