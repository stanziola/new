"""Nuevo caso de viva de una franja de losa: en qué claros va la viva.

Los automáticos (ACI 318-19 §6.4.2, PDF p. 75: todos, los impares, los pares y cada par de vecinos) ya
están; aquí se agrega otro, por ejemplo el que pidió el profesor o uno para una revisión particular.
Se guarda con la losa (por los claros de la franja) y entra en las envolventes de diseño y de servicio.
"""
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from configuracion import formato


def pedir_claros(parent, franja):
    """Abre el diálogo y devuelve los claros elegidos (1, 2…), o None si se canceló o no se marcó ninguno."""
    dialogo = QDialog(parent)
    dialogo.setWindowTitle(f"Nuevo caso de viva — {franja.nombre}")
    diseno = QVBoxLayout(dialogo)
    diseno.addWidget(QLabel("¿En qué claros va la viva? (la muerta va siempre en todos)"))
    casillas = []
    for k, (claro, viva) in enumerate(zip(franja.claros, franja.viva), start=1):
        casilla = QCheckBox(f"Claro {k}: {formato.cantidad(claro, 'longitud')}, viva "
                            f"{formato.cantidad(viva, 'carga_area')}")
        casillas.append(casilla)
        diseno.addWidget(casilla)
    botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    botones.button(QDialogButtonBox.Ok).setText("Agregar")
    botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
    botones.accepted.connect(dialogo.accept)
    botones.rejected.connect(dialogo.reject)
    diseno.addWidget(botones)
    if dialogo.exec() != QDialog.Accepted:
        return None
    claros = tuple(k for k, casilla in enumerate(casillas, start=1) if casilla.isChecked())
    return claros or None
