SDS = 0.5   # dato del sitio
rho = 1.3   # 1.0 en CDS B o C; 1.3 en D, E y F salvo exención

combos = [
    (1, "1.4D",         {"D": 1.4}),
    (2, "1.2D+1.6L",    {"D": 1.2, "L": 1.6}),
    (3, "1.2D+0.8W",    {"D": 1.2, "W": 0.8}),
    (3, "1.2D-0.8W",    {"D": 1.2, "W": -0.8}),
    (4, "1.2D+1.6W+L",  {"D": 1.2, "W": 1.6, "L": 1.0}),
    (4, "1.2D-1.6W+L",  {"D": 1.2, "W": -1.6, "L": 1.0}),
    (5, "(1.2+0.2SDS)D+ρE+L", {"D": round(1.2 + 0.2 * SDS, 4), "E": rho, "L": 1.0}),
    (5, "(1.2+0.2SDS)D-ρE+L", {"D": round(1.2 + 0.2 * SDS, 4), "E": -rho, "L": 1.0}),
    (6, "0.9D+1.6W",    {"D": 0.9, "W": 1.6}),
    (6, "0.9D-1.6W",    {"D": 0.9, "W": -1.6}),
    (7, "(0.9-0.2SDS)D+ρE", {"D": round(0.9 - 0.2 * SDS, 4), "E": rho}),
    (7, "(0.9-0.2SDS)D-ρE", {"D": round(0.9 - 0.2 * SDS, 4), "E": -rho}),
]

for num, nombre, factores in combos:
    print(f"{num}: {nombre}")
