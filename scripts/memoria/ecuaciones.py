"""Ecuaciones de Word a partir de LaTeX.

Las fórmulas de la memoria se escriben en LaTeX, la forma usual de escribir matemáticas como texto:
    r"C_c = 0.85 f'_c \\, a \\, b"          _ subíndice, ^ superíndice
    r"\\frac{E A}{L}"                       fracción
    r"\\sqrt{dx^2 + dy^2}"                  raíz
    r"\\begin{bmatrix} a & b \\\\ c & d \\end{bmatrix}"   matriz (& separa columnas; \\\\, filas)
y aquí se convierten en ecuaciones de Word de verdad (se pueden editar con su editor de ecuaciones):

    LaTeX → MathML (librería latex2mathml) → OMML, el formato de Word,
            con la hoja de transformación MML2OMML.XSL que instala Microsoft Office.

Si Office no está instalado (o está en otra carpeta), la variable de entorno MML2OMML puede dar la
ruta de ese archivo.
"""
import os
from functools import lru_cache
from pathlib import Path

from latex2mathml.converter import convert
from lxml import etree

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NOMBRE_XSL = "MML2OMML.XSL"


@lru_cache(maxsize=1)
def ruta_xsl():
    """Dónde está MML2OMML.XSL: la variable MML2OMML o la carpeta de Microsoft Office."""
    indicada = os.environ.get("MML2OMML")
    if indicada and Path(indicada).is_file():
        return Path(indicada)
    carpetas = [Path(base) / "Microsoft Office" for base in
                (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramW6432"))
                if base]
    for carpeta in carpetas:                       # primero, donde suele estar
        for sub in ("root/Office16", "Office16", "root/Office15", "Office15"):
            if (carpeta / sub / NOMBRE_XSL).is_file():
                return carpeta / sub / NOMBRE_XSL
    for carpeta in carpetas:                       # si no, se busca en toda la carpeta de Office
        if carpeta.is_dir():
            for ruta in carpeta.rglob(NOMBRE_XSL):
                return ruta
    raise FileNotFoundError(
        f"No se encontró {NOMBRE_XSL} (lo instala Microsoft Office). Las ecuaciones de Word se arman con ese "
        "archivo: instala Office o pon su ruta en la variable de entorno MML2OMML.")


@lru_cache(maxsize=1)
def _transformacion():
    return etree.XSLT(etree.parse(str(ruta_xsl())))


# Ajustes antes de convertir (lo que la hoja de Office no maneja bien tal cual):
# - una matriz entre corchetes se escribe con \left[ … \right], para que Word estire los corchetes;
# - los espacios de LaTeX (\quad, \;) se pierden en la conversión: se cambian por espacios de texto.
AJUSTES = (("\\begin{bmatrix}", "\\left[\\begin{matrix}"), ("\\end{bmatrix}", "\\end{matrix}\\right]"),
           ("\\begin{pmatrix}", "\\left(\\begin{matrix}"), ("\\end{pmatrix}", "\\end{matrix}\\right)"),
           ("\\qquad", "\\text{        }"), ("\\quad", "\\text{    }"), ("\\;", "\\text{ }"))


def omml(latex):
    """La ecuación de Word (elemento <m:oMath>) de una fórmula en LaTeX."""
    for escrito, equivalente in AJUSTES:
        latex = latex.replace(escrito, equivalente)
    try:
        mathml = etree.fromstring(convert(latex).encode("utf-8"))
    except Exception as e:                          # la fórmula está mal escrita
        raise ValueError(f"No se pudo leer la fórmula {latex!r}: {e}") from e
    return _transformacion()(mathml).getroot()


def omml_centrada(latex):
    """La ecuación en su propio renglón, centrada (elemento <m:oMathPara>)."""
    parrafo = etree.Element(f"{{{M}}}oMathPara", nsmap={"m": M})
    parrafo.append(omml(latex))
    return parrafo
