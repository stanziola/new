"""Imprime las combinaciones de resistencia que el programa trae cargadas (ASCE 7-05 §2.3.2 y
§12.4.2.3). La lista y sus factores están en modelo/combinaciones.py, que es lo que usa el
programa; aquí solo se imprimen. Desde la raíz:  python -m scripts.combinaciones_asce7
"""
import sys

from modelo.combinaciones import FORMULAS, MUERTA, numero, predeterminadas

SDS = 0.5   # dato del sitio
rho = 1.3   # 1.0 en CDS B o C; 1.3 en D, E y F salvo exención

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for clave in predeterminadas(SDS, rho):
        if clave != MUERTA:
            print(f"{numero(clave)}: {FORMULAS[clave]}")
