"""Busca en un texto extraído con extraer.py (marcas '===== p. N =====') y dice en qué página está.

Uso:
  python buscar.py <archivo.txt> sec 12.8.6 22.5.5.1     -> páginas donde empieza cada sección
  python buscar.py <archivo.txt> re "<regex>" [max]       -> páginas y líneas que coinciden
  python buscar.py <archivo.txt> pag 150 [152]            -> imprime esas páginas
Los números de sección toleran los espacios que mete el OCR del ASCE ("1 2. 8.6").
"""
import re
import sys


def paginas(archivo):
    txt = open(archivo, encoding="utf-8").read()
    partes = re.split(r"\n===== p\. (\d+) =====\n", txt)
    return [(int(partes[k]), partes[k + 1]) for k in range(1, len(partes), 2)]


def patron_seccion(sec):
    piezas = [r"\s?".join(re.escape(d) for d in parte) for parte in sec.split(".")]
    return re.compile(r"(?m)^\s*" + r"\s?\.\s?".join(piezas) + r"(?![\d])\s*\.?\s+[A-Z(]")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    archivo, modo, *args = sys.argv[1:]
    pags = paginas(archivo)
    if modo == "sec":
        for sec in args:
            pat = patron_seccion(sec)
            hits = [p for p, t in pags if p > 25 and pat.search(t)]
            print(f"{sec:10s} -> {hits[:6]}")
    elif modo == "re":
        pat = re.compile(args[0])
        maximo = int(args[1]) if len(args) > 1 else 40
        n = 0
        for p, t in pags:
            for linea in t.splitlines():
                if pat.search(linea):
                    print(f"p. {p}: {linea.strip()[:150]}")
                    n += 1
                    if n >= maximo:
                        return
    elif modo == "pag":
        a = int(args[0])
        b = int(args[1]) if len(args) > 1 else a
        for p, t in pags:
            if a <= p <= b:
                print(f"===== p. {p} =====\n{t}")


if __name__ == "__main__":
    main()
