"""Textos cortos para mostrar cargas y resultados, en las unidades de pantalla."""
from configuracion import formato
from configuracion.formato import FUERZAS
from modelo.estructura import CargaNodal

UNIDAD_CARGA = {"uniforme": "carga_lineal", "puntual": "fuerza", "momento": "momento"}
DIRECCION = {"X": "X global", "Y": "Y global", "Z": "Z global", "x": "x local", "y": "y local", "z": "z local"}


def texto_carga(c):
    """"Fx 10.00 kN, Fz -20.00 kN" o "uniforme -15.00 kN/m (Z global)"."""
    if isinstance(c, CargaNodal):
        partes = [f"{nombre} {formato.cantidad(v, 'fuerza' if nombre[0] == 'F' else 'momento')}"
                  for nombre, v in zip(FUERZAS, c.fuerzas) if v]
        return ", ".join(partes) or "sin valores"
    texto = f"{c.tipo} {formato.cantidad(c.valor, UNIDAD_CARGA[c.tipo])} ({DIRECCION[c.direccion]})"
    if c.tipo != "uniforme":
        texto += f" a {formato.cantidad(c.a, 'longitud')}"
    return texto


def donde(c):
    """"Nodo 3" o "Barra 2"."""
    return f"Nodo {c.nodo}" if isinstance(c, CargaNodal) else f"Barra {c.barra}"


def valor_corto(valor, componente):
    """Valor de un diagrama con su unidad (N y V en fuerza; T y M en momento)."""
    return formato.cantidad(valor, "fuerza" if componente in ("N", "Vy", "Vz") else "momento")
