"""Tipos de apoyo que se pueden asignar desde la interfaz.

Solo combinaciones con sentido estructural (por ahora dos, más "libre" para quitar un apoyo):
- empotrado: restringe los 6 GDL (3 desplazamientos y 3 giros);
- apoyo fijo: restringe los 3 desplazamientos y deja girar (lo que en 2D se llama articulado).
El orden de cada lista es el de los GDL: Dx, Dy, Dz, φx, φy, φz.
"""
TIPOS = {
    "empotrado": [True] * 6,
    "fijo": [True, True, True, False, False, False],
    "libre": [False] * 6,
}
NOMBRES = {"empotrado": "Empotrado", "fijo": "Apoyo fijo", "libre": "Libre"}


def tipo_de(apoyo):
    """"empotrado", "fijo", "libre" u "otro" (una combinación que la interfaz no asigna)."""
    for tipo, restricciones in TIPOS.items():
        if list(apoyo) == restricciones:
            return tipo
    return "otro"


def describir(apoyo):
    """Texto corto para el explorador y Propiedades."""
    return NOMBRES.get(tipo_de(apoyo), "otro").lower()
