"""Genera la memoria de cálculo en Word. Desde la raíz del proyecto:

    python -m scripts.memoria            docs/memoria/Memoria de cálculo.docx
    python -m scripts.memoria --pdf      además, el PDF al lado
    python -m scripts.memoria --salida otra/ruta.docx

El documento no se edita a mano: se vuelve a generar. Para agregar un tema se escribe un módulo en
scripts/memoria/capitulos/ con una función capitulo(m) y se suma a CAPITULOS, aquí abajo.
Hay que cerrar el documento en Word antes de generarlo (Word no deja escribir un archivo abierto).
"""
import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.memoria import word                                            # noqa: E402
from scripts.memoria.capitulos import interaccion, presentacion, rigidez    # noqa: E402
from scripts.memoria.documento import Memoria, pedir_actualizacion_al_abrir  # noqa: E402

SALIDA = RAIZ / "docs" / "memoria" / "Memoria de cálculo.docx"
CAPITULOS = [presentacion.capitulo, rigidez.capitulo, interaccion.capitulo]    # en el orden del documento
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")
AUTOR = "Luis Stanziola"


def _git(*argumentos):
    """Salida de un comando de git, o None si no hay git o no es un repositorio."""
    try:
        r = subprocess.run(["git", *argumentos], cwd=RAIZ, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return r.stdout.strip()


def version():
    """De qué versión del programa es el documento: el commit de git y si hay cambios sin confirmar."""
    commit = _git("rev-parse", "--short", "HEAD")
    if commit is None:
        return "sin control de versiones"
    return f"commit {commit}" + (" más cambios sin confirmar" if _git("status", "--porcelain") else "")


def generar(salida=SALIDA, pdf=False, imprimir=print):
    """Arma el documento y lo guarda. Devuelve True si lo pudo guardar."""
    hoy = date.today()
    m = Memoria()
    m.portada("Memoria de cálculo",
              ["Fórmulas y programación", "Programa de análisis y diseño estructural 3D"],
              AUTOR,
              ["Normas: REP 2021 · ASCE/SEI 7-05 · ACI 318-19",
               f"Generado el {hoy.day} de {MESES[hoy.month - 1]} de {hoy.year} · versión del programa: {version()}"])
    m.indice()
    for capitulo in CAPITULOS:
        capitulo(m)
    try:
        ruta = m.guardar(salida)
    except PermissionError:
        imprimir(f"No se pudo escribir {salida}: ciérralo en Word y vuelve a generar.")
        return False
    imprimir(f"Documento: {ruta}")
    problema = word.actualizar(ruta, pdf=ruta.with_suffix(".pdf") if pdf else None)
    if problema is None:
        imprimir("Índice actualizado con Word" + (f"; PDF: {ruta.with_suffix('.pdf')}" if pdf else ""))
    else:
        pedir_actualizacion_al_abrir(ruta)
        imprimir(f"Aviso: {problema}. El índice se actualizará al abrir el documento en Word (di que sí).")
    return True


def main(argv=None):
    opciones = argparse.ArgumentParser(description="Genera la memoria de cálculo en Word.")
    opciones.add_argument("--salida", type=Path, default=SALIDA, help="ruta del .docx")
    opciones.add_argument("--pdf", action="store_true", help="exportar también a PDF (necesita Word)")
    argumentos = opciones.parse_args(argv)
    return 0 if generar(argumentos.salida, argumentos.pdf) else 1


if __name__ == "__main__":
    sys.exit(main())
