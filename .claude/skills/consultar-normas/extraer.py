"""Extrae el texto legible de ACI 318-19 o ASCE 7-05 (docs/codigos/*.pdf).

Los dos PDF usan fuentes "corridas": muchos caracteres salen desplazados -29 posiciones
(por ejemplo 'ZKHUH' en lugar de 'where'). Este script detecta esas fuentes por objeto de
fuente y las decodifica, descarta la marca de agua y separa las dos columnas de cada página.

Uso (desde la raíz del proyecto; la salida conviene dejarla en la scratchpad, no en el repo):
  python extraer.py "docs/codigos/ACI 318-19.pdf" <salida.txt> aci
      -> <salida.txt> con la columna izquierda (CÓDIGO) y <salida>_comentario.txt (COMENTARIO)
  python extraer.py "docs/codigos/ASCE 7-05.pdf" <salida.txt> asce
      -> columna izquierda y luego derecha de cada página

Cada página queda marcada con  ===== p. N =====  (N = página del PDF, desde 1).
El REP 2021 es un escaneo sin texto: para leerlo usar ver_pagina.py.
"""
import collections
import ctypes
import re
import sys

import pypdfium2 as pdfium
import pypdfium2.raw as raw

# Glifos especiales dentro de las fuentes corridas (ligaduras, comillas, símbolos)
ESPECIALES = {'¿': 'fi', '൵': 'ff', 'ৼ': 'ff', 'À': 'fl', '൶': 'ffi', '²': '—', '³': '“',
              '´': '”', 'ƍ': "'", 'ࢥ': 'φ', '±': '−'}
BASURA = re.compile(r"American Concrete Institute – Copyrighted|Copyrighted material licensed|"
                    r"^ACI 318-19: BUILDING CODE REQUIREMENTS|^CODE$|^COMMENTARY$|^\d{1,3}$")


def es_corrida(us):
    """Una fuente está corrida si casi no tiene minúsculas y casi todo cae en el rango desplazado."""
    us = [u for u in us if u not in (9, 10, 13, 32)]
    if len(us) < 2:
        return False
    minus = sum(97 <= u <= 122 for u in us)
    deco = sum((0x44 <= u <= 0x5D) or u == 3 for u in us)
    return minus <= 0.1 * len(us) and deco >= 0.5 * len(us)


def caracteres(pdf, i):
    """Caracteres de la página i como (texto, x0, x1, línea base, tamaño), ya decodificados."""
    pg = pdf[i]
    w, _ = pg.get_size()
    tp = pg.get_textpage()
    n = raw.FPDFText_CountChars(tp.raw)
    buf = ctypes.create_string_buffer(256)
    fl = ctypes.c_int()
    l, r, b, t, ox, oy = (ctypes.c_double() for _ in range(6))
    datos = []
    for k in range(n):
        u = raw.FPDFText_GetUnicode(tp.raw, k)
        if u in (10, 13, 0xFFFE):
            continue
        obj = raw.FPDFText_GetTextObject(tp.raw, k)
        h = ctypes.cast(raw.FPDFTextObj_GetFont(obj), ctypes.c_void_p).value if obj else None
        raw.FPDFText_GetFontInfo(tp.raw, k, buf, 256, ctypes.byref(fl))
        if b"Unifont" in buf.value:            # marca de agua
            continue
        raw.FPDFText_GetCharBox(tp.raw, k, ctypes.byref(l), ctypes.byref(r), ctypes.byref(b), ctypes.byref(t))
        raw.FPDFText_GetCharOrigin(tp.raw, k, ctypes.byref(ox), ctypes.byref(oy))
        tam = raw.FPDFText_GetFontSize(tp.raw, k)
        datos.append([u, h, l.value, r.value, oy.value, tam])

    por_fuente = collections.defaultdict(list)
    for d in datos:
        por_fuente[d[1]].append(d[0])
    corridas = {h for h, us in por_fuente.items() if h and es_corrida(us)}

    salida = []
    for u, h, x0, x1, base, tam in datos:
        c = chr(u)
        if h in corridas:
            c = ESPECIALES.get(c, chr(u + 29) if (u < 0x80 and u != 32) else c)
        if c.strip() == "" and c != " ":
            continue
        salida.append((c, x0, x1, base, tam))
    return salida, w


def lineas(chars):
    """Agrupa caracteres en líneas por línea base y los ordena por x."""
    chars = sorted(chars, key=lambda c: -c[3])
    grupos = []
    for c in chars:
        if grupos and abs(grupos[-1][0] - c[3]) < 3.6:
            grupos[-1][1].append(c)
        else:
            grupos.append([c[3], [c]])
    res = []
    for yc, cs in grupos:
        cs.sort(key=lambda c: c[1])
        txt, prev = "", None
        for c in cs:
            if prev is not None and c[0] != " " and not txt.endswith(" "):
                if c[1] - prev[2] > 0.33 * max(prev[4], 4.0):
                    txt += " "
            if not (c[0] == " " and txt.endswith(" ")):
                txt += c[0]
            prev = c
        txt = re.sub(r" {2,}", " ", txt).strip()
        if txt and not BASURA.search(txt):
            res.append((yc, txt))
    return res


def pagina(pdf, i):
    """Devuelve (líneas de la columna izquierda, líneas de la columna derecha)."""
    chars, w = caracteres(pdf, i)
    izq = [c for c in chars if (c[1] + c[2]) / 2 < w / 2]
    der = [c for c in chars if (c[1] + c[2]) / 2 >= w / 2]
    return lineas(izq), lineas(der)


def main():
    pdf_path, salida = sys.argv[1], sys.argv[2]
    modo = sys.argv[3] if len(sys.argv) > 3 else "asce"
    pdf = pdfium.PdfDocument(pdf_path)
    if modo == "aci":
        with open(salida, "w", encoding="utf-8") as fc, \
             open(salida.replace(".txt", "_comentario.txt"), "w", encoding="utf-8") as fr:
            for i in range(len(pdf)):
                izq, der = pagina(pdf, i)
                fc.write(f"\n===== p. {i + 1} =====\n" + "\n".join(t for _, t in izq) + "\n")
                fr.write(f"\n===== p. {i + 1} =====\n" + "\n".join(t for _, t in der) + "\n")
    else:
        with open(salida, "w", encoding="utf-8") as f:
            for i in range(len(pdf)):
                izq, der = pagina(pdf, i)
                f.write(f"\n===== p. {i + 1} =====\n" + "\n".join(t for _, t in izq)
                        + "\n" + "\n".join(t for _, t in der) + "\n")
    print("listo:", salida, len(pdf), "páginas")


if __name__ == "__main__":
    main()
