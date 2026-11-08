"""Convierte una página de un PDF en imagen PNG para leerla: tablas, ecuaciones y el REP 2021
(que es un escaneo sin texto).

Uso:
  python ver_pagina.py <pdf> <página> <salida.png> [escala] [x0 y0 x1 y1]
    página : número de página del PDF (desde 1)
    escala : 1.45 alcanza para el REP; 2.0 para tablas pequeñas del ACI o del ASCE
    recorte: fracciones de la página (0 a 1) desde arriba a la izquierda, ej. 0 0.4 1 0.9
Guardar la salida en la scratchpad, no en el repositorio.
"""
import sys

import pypdfium2 as pdfium


def main():
    pdf_path, num, salida = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    escala = float(sys.argv[4]) if len(sys.argv) > 4 else 1.45
    img = pdfium.PdfDocument(pdf_path)[num - 1].render(scale=escala, grayscale=True).to_pil()
    if len(sys.argv) > 8:
        x0, y0, x1, y1 = (float(v) for v in sys.argv[5:9])
        w, h = img.size
        img = img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
    img.save(salida)
    print("listo:", salida, img.size)


if __name__ == "__main__":
    main()
