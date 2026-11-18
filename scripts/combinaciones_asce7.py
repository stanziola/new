"""Imprime las combinaciones que el programa trae cargadas: las de resistencia (ASCE 7-05 §2.3.2 y
§12.4.2.3) y las de servicio (ASCE 7-05 Apéndice C). La lista y sus factores están en
modelo/combinaciones.py, que es lo que usa el programa; aquí solo se imprimen. Desde la raíz:
python -m scripts.combinaciones_asce7
"""
import sys

from modelo.combinaciones import FORMULAS, REFERENCIA_SERVICIO, numero, resistencia, servicio

SDS = 0.5   # dato del sitio
rho = 1.3   # 1.0 en CDS B o C; 1.3 en D, E y F salvo exención

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("Resistencia (ASCE 7-05 §2.3.2 y §12.4.2.3):")
    for clave in resistencia(SDS, rho):
        print(f"  {numero(clave)}: {FORMULAS[clave]}")
    print("Servicio (ASCE 7-05 Apéndice C):")
    for clave, co in servicio().items():
        print(f"  {co.nombre}: {REFERENCIA_SERVICIO[clave]}")
