"""Preferencias del usuario: lo que cambia en Configuración, guardado aparte de los valores base.

Cómo funciona:
- Los valores base están en los módulos de esta carpeta (colores.py, interfaz.py...).
- Lo que el usuario cambia se guarda en un JSON propio, fuera del proyecto
  (%APPDATA%/Analisis3D/preferencias.json), y al abrir el programa se aplica encima con setattr.
- El código siempre lee el valor en el momento (colores.ELEMENTO, ui.TAMANO_ICONO...), así que ve
  el valor vigente sin hacer nada más.
- Para que algo sea configurable basta agregar una línea a PARAMETROS: el diálogo se arma solo.
- Los valores con unidades (magnitud) se guardan en unidades internas y el diálogo los muestra en
  las de pantalla.
"""
import json
import os
import re
import warnings
from dataclasses import dataclass
from pathlib import Path

from configuracion import colores, formato, interfaz, unidades

ARCHIVO = Path(os.environ.get("APPDATA") or Path.home()) / "Analisis3D" / "preferencias.json"


@dataclass(frozen=True)
class Parametro:
    modulo: object          # módulo donde vive el valor base
    nombre: str             # nombre de la constante en ese módulo
    etiqueta: str           # texto en el diálogo
    tipo: str               # "entero", "real", "bool", "color", "opcion" o "atajo"
    grupo: str              # pestaña del diálogo
    minimo: float = 0
    maximo: float = 1e9
    opciones: tuple = ()    # para "opcion"
    magnitud: str = None    # si tiene unidades ("longitud"...): en el diálogo se convierte
    decimales: int = 2      # para "real"

    @property
    def clave(self):
        """Nombre en el JSON, por ejemplo "colores.ELEMENTO"."""
        return f"{self.modulo.__name__.rsplit('.', 1)[-1]}.{self.nombre}"

    def valor(self):
        return getattr(self.modulo, self.nombre)

    def poner(self, valor):
        setattr(self.modulo, self.nombre, valor)


P = Parametro
PARAMETROS = [
    # ---------- Unidades (como en Ftool: unidad y decimales por magnitud) ----------
    *[p for m in unidades.UNIDADES for p in (
        P(unidades, m.upper(), unidades.NOMBRES[m], "opcion", "Unidades", opciones=tuple(unidades.UNIDADES[m])),
        P(formato, f"DECIMALES_{m.upper()}", f"Decimales de {unidades.NOMBRES[m].lower()}", "entero",
          "Unidades", 0, 8))],
    # ---------- Rejilla ----------
    *[P(interfaz, f"REJILLA_DISTANCIA_{eje}", f"Distancia entre líneas en {eje}", "real", "Rejilla",
        0.001, 1e6, magnitud="longitud", decimales=3) for eje in "XYZ"],
    P(interfaz, "REJILLA_LINEAS_X", "Líneas en X", "entero", "Rejilla", 2, 201),
    P(interfaz, "REJILLA_LINEAS_Y", "Líneas en Y", "entero", "Rejilla", 2, 201),
    P(interfaz, "REJILLA_LINEAS_Z", "Niveles en Z", "entero", "Rejilla", 1, 201),
    # ---------- Vista ----------
    P(interfaz, "GROSOR_BARRA", "Grosor de los elementos (píxeles)", "entero", "Vista", 1, 20),
    P(interfaz, "TAMANO_NODO", "Tamaño de los nodos (píxeles)", "entero", "Vista", 1, 50),
    P(interfaz, "TAMANO_APOYO", "Tamaño de los apoyos (fracción del modelo)", "real", "Vista", 0.01, 0.3),
    P(interfaz, "TAMANO_CARGA", "Tamaño de las cargas (fracción del modelo)", "real", "Vista", 0.01, 0.5),
    P(interfaz, "ESCALA_DEFORMADA", "Escala de la deformada (fracción del modelo)", "real", "Vista", 0.005, 0.5),
    P(interfaz, "ESCALA_DIAGRAMA", "Escala de los diagramas (fracción del modelo)", "real", "Vista", 0.01, 0.5),
    # ---------- Interfaz ----------
    P(interfaz, "TAMANO_ICONO", "Íconos de las barras izquierda y Definir (píxeles)", "entero", "Interfaz", 12, 64),
    P(interfaz, "TAMANO_ICONO_INFERIOR", "Íconos de la barra inferior (píxeles)", "entero", "Interfaz", 12, 64),
    P(interfaz, "CUBO_TAMANO", "Tamaño del cubo (fracción del alto de la vista)", "real", "Interfaz", 0.08, 0.5),
    P(interfaz, "EJES_TAMANO", "Tamaño de los ejes (fracción del alto de la vista)", "real", "Interfaz", 0.06, 0.4),
    P(interfaz, "ANIM_CAMARA_DURACION_MS", "Duración del giro de la cámara (ms)", "entero", "Interfaz", 0, 3000),
    P(interfaz, "HISTORIAL_MAXIMO", "Pasos para deshacer", "entero", "Interfaz", 1, 500),
    # ---------- Colores del dibujo ----------
    P(colores, "ELEMENTO", "Nodos, elementos y apoyos", "color", "Colores"),
    P(colores, "RESALTADO", "Al pasar el mouse", "color", "Colores"),
    P(colores, "SELECCIONADO", "Seleccionado", "color", "Colores"),
    P(colores, "SIN_ASIGNAR", "Elementos sin material o sección", "color", "Colores"),
    P(colores, "ETIQUETA", "Etiquetas", "color", "Colores"),
    P(colores, "CARGA", "Cargas", "color", "Colores"),
    P(colores, "DEFORMADA", "Deformada", "color", "Colores"),
    P(colores, "DIAGRAMA_POSITIVO", "Diagramas: positivo", "color", "Colores"),
    P(colores, "DIAGRAMA_NEGATIVO", "Diagramas: negativo", "color", "Colores"),
    P(colores, "REJILLA", "Rejilla", "color", "Colores"),
    P(colores, "FONDO_VISTA", "Fondo de la vista", "color", "Colores"),
    P(colores, "CUBO_CARA", "Cubo: caras", "color", "Colores"),
    P(colores, "CUBO_RESALTADO", "Cubo: resaltado", "color", "Colores"),
    P(colores, "CUBO_BORDE", "Cubo: bordes", "color", "Colores"),
    # ---------- Colores de la interfaz (grises) ----------
    P(colores, "INTERFAZ_FONDO", "Interfaz: fondo", "color", "Colores"),
    P(colores, "INTERFAZ_TEXTO", "Interfaz: texto", "color", "Colores"),
    P(colores, "INTERFAZ_BORDE", "Interfaz: líneas divisorias", "color", "Colores"),
    P(colores, "INTERFAZ_HOVER", "Interfaz: botón bajo el mouse", "color", "Colores"),
    P(colores, "INTERFAZ_ACTIVO", "Interfaz: botón activo", "color", "Colores"),
    P(colores, "INTERFAZ_ACTIVO_BORDE", "Interfaz: borde del botón activo", "color", "Colores"),
    P(colores, "INTERFAZ_PESTANA_INACTIVA", "Interfaz: pestaña inactiva", "color", "Colores"),
    P(colores, "INTERFAZ_SELECCION", "Interfaz: fila seleccionada", "color", "Colores"),
    P(colores, "INTERFAZ_ENLAZADO", "Interfaz: filas relacionadas", "color", "Colores"),
    P(colores, "ICONO", "Íconos", "color", "Colores"),
]

_BASE = {p.clave: p.valor() for p in PARAMETROS}     # valores base, tomados al importar
_POR_CLAVE = {p.clave: p for p in PARAMETROS}


def base(parametro):
    """Valor base (el del código) de un parámetro."""
    return _BASE[parametro.clave]


def _valido(p, v):
    """True si v tiene el tipo y el rango que le corresponden al parámetro p."""
    numero = isinstance(v, (int, float)) and not isinstance(v, bool)
    if p.tipo == "bool":
        return isinstance(v, bool)
    if p.tipo == "entero":
        return numero and float(v).is_integer() and p.minimo <= v <= p.maximo
    if p.tipo == "real":
        return numero and p.minimo <= v <= p.maximo
    if p.tipo == "opcion":
        return v in p.opciones
    if p.tipo == "color":
        return isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v) is not None
    if p.tipo == "atajo":
        return isinstance(v, str)
    return False


def cargar(archivo=None):
    """Aplica las preferencias guardadas encima de los valores base. Devuelve cuántas aplicó.

    Un archivo dañado o un valor que no corresponde se ignoran con un aviso: nunca impiden abrir.
    """
    archivo = Path(archivo or ARCHIVO)
    if not archivo.exists():
        return 0
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        if not isinstance(datos, dict):
            raise ValueError("no es un diccionario")
    except (OSError, ValueError) as e:
        warnings.warn(f"No se pudieron leer las preferencias ({archivo}): {e}. Se usan los valores base.")
        return 0
    aplicadas = 0
    for clave, v in datos.items():
        p = _POR_CLAVE.get(clave)
        if p is None or not _valido(p, v):
            warnings.warn(f"Preferencia ignorada: {clave} = {v!r}")
            continue
        p.poner(float(v) if p.tipo == "real" else int(v) if p.tipo == "entero" else v)
        aplicadas += 1
    return aplicadas


def guardar(archivo=None):
    """Guarda solo lo que difiere de los valores base. Devuelve lo guardado."""
    archivo = Path(archivo or ARCHIVO)
    cambios = {p.clave: p.valor() for p in PARAMETROS if p.valor() != _BASE[p.clave]}
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(json.dumps(cambios, indent=2, ensure_ascii=False), encoding="utf-8")
    return cambios


def restablecer():
    """Vuelve todos los parámetros a sus valores base (no borra el archivo: eso lo hace guardar)."""
    for p in PARAMETROS:
        p.poner(_BASE[p.clave])
