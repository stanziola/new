"""Textos cortos para mostrar cargas, resultados y nombres, en las unidades de pantalla."""
from configuracion import formato, unidades
from configuracion.formato import FUERZAS
from modelo import concreto as cc
from modelo.estructura import CargaNodal, Material

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


# ---------------------------------------------------------------- Nombres de materiales y secciones
# El modelo (y el .json) guarda un nombre "canónico" que no depende de las unidades:
# "Concreto f'c 27.6 MPa" y "Concreto 30x50 Nx3 Ny2 #6" (en cm), de modelo/concreto.py.
# En pantalla, los nombres automáticos se vuelven a escribir con las unidades vigentes. Los nombres
# que escribió el usuario (y los de la familia "otros") se muestran tal cual.
def fc_corto(fc):
    """"f'c 4 ksi" en la unidad de esfuerzo vigente."""
    return f"f'c {formato.compacto(fc, 'esfuerzo')} {unidades.simbolo('esfuerzo')}"


def nombre_concreto(fc):
    """Nombre automático de un material de concreto: "Concreto f'c 28 MPa" (o 4 ksi...)."""
    return f"Concreto {fc_corto(fc)}"


def nombre_rectangular(b, h, nx, ny, barra):
    """Nombre automático de una sección rectangular, en la unidad de sección: "Concreto 30x50 Nx3 Ny2 #6"."""
    return f"Concreto {formato.compacto(b, 'seccion')}x{formato.compacto(h, 'seccion')} Nx{nx} Ny{ny} #{barra}"


def _automatico(sec):
    """True si la sección tiene el nombre automático (el canónico, en cm)."""
    c = sec.concreto
    return (c is not None and c.forma == "rectangular"
            and sec.nombre == cc.nombre_seccion(c.b, c.h, c.nx, c.ny, c.barra))


def nombre(obj, modelo=None):
    """Nombre para mostrar de un material o una sección, en las unidades vigentes.

    Con el modelo, si otra sección tiene las mismas medidas y refuerzo pero otro concreto, se agrega
    su f'c para distinguirlas: "Concreto 30x50 Nx3 Ny2 #6 (f'c 35 MPa)"."""
    if obj is None:
        return ""
    if isinstance(obj, Material):
        if obj.fc is not None and obj.nombre == cc.nombre_material(obj.fc):
            return nombre_concreto(obj.fc)
        return obj.nombre
    if not _automatico(obj):
        return obj.nombre
    c = obj.concreto
    texto = nombre_rectangular(c.b, c.h, c.nx, c.ny, c.barra)
    if modelo is not None:
        gemelas = [s for s in modelo.secciones.values()
                   if s is not obj and s.nombre == obj.nombre and s.material != obj.material]
        mat = modelo.materiales.get(obj.material)
        if gemelas and mat is not None:
            texto += f" ({fc_corto(mat.fc) if mat.fc is not None else mat.nombre})"
    return texto
