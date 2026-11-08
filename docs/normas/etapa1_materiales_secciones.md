# Etapa 1: Materiales y secciones

**Qué cubre:**
- propiedades de diseño del concreto y del acero de refuerzo;
- propiedades de sección para el análisis: Ig, inercias agrietadas, A, J;
- hipótesis de resistencia de secciones (bloque rectangular), que ya usan los diagramas de interacción.

**Qué norma manda:**
- El REP 2021 8.1 (p. 100) remite a **ACI 318-19**. El REP no modifica las propiedades de los materiales.
- El REP 8.3 pide control de calidad por un laboratorio independiente certificado, con atención especial a concretos de 35 MPa (5000 psi) o más en columnas y muros.

> El ACI de `codigos/` está en **unidades inglesas** (psi, in). Entre corchetes va el equivalente SI usual del ACI 318-19M, para comparar.

## Concreto: ACI 19.2 (p. 357–359)

| Cláusula | Qué dice |
|---|---|
| Tabla 19.2.1.1 (p. 357) | f'c mínimo: **general 2500 psi** [17 MPa]. **Pórticos especiales** y muros especiales con barras Grado 60/80: **3000 psi** [21 MPa]. Cimentaciones en CDS D–F: 3000 psi. Pilotes perforados: 4000 psi. Muros especiales con Grado 100: 5000 psi. |
| 19.2.1.1(d) | Concreto liviano en pórticos o muros especiales: f'c ≤ 5000 psi, salvo ensayos. |
| 19.2.1.3 | f'c a 28 días, salvo que los planos indiquen otra edad. |
| 19.2.2.1 (p. 358) | Ec = wc^1.5 · 33 · √f'c (psi), con wc entre 90 y 160 lb/ft³. Para concreto de peso normal: **Ec = 57 000 √f'c** (psi) [**4700 √f'c** MPa]. |
| 19.2.3.1 | Módulo de rotura fr = 7.5 λ √f'c (psi) [0.62 λ √f'c MPa]. |
| 19.2.4 (p. 359) | λ = 1.0 en concreto de peso normal; 0.75 a 0.85 en liviano. |

ν y G **no están en el código**; el ACI remite a ensayos ASTM C469. En la práctica se usa ν = 0.2 y G = Ec / (2(1 + ν)) ≈ 0.42 Ec, que es mecánica de materiales, no norma.

## Acero de refuerzo: ACI 20.2 (p. 373–378)

| Cláusula | Qué dice |
|---|---|
| 20.2.1.3 | Barras corrugadas ASTM A615 (acero al carbono) o A706 (baja aleación, soldable). **No se permiten barras mayores que la No. 18.** |
| 20.2.2.1 | Curva elastoplástica: fs = Es·εs hasta fy y, después, fs = fy. |
| 20.2.2.2 (p. 376) | **Es = 29 000 000 psi** [200 000 MPa]. |
| Tabla 20.2.2.4(a) (p. 378) | fy máximo para diseño:<br>• flexión y axial: 80 ksi en pórticos especiales, 100 ksi en los demás casos;<br>• **estribos y aros por cortante: 60 ksi** [420 MPa] (80 ksi solo en malla electrosoldada corrugada);<br>• espirales por cortante: 60 ksi;<br>• torsión: 60 ksi;<br>• confinamiento y soporte lateral de barras: 100 ksi (80 ksi fuera de los sistemas sísmicos especiales). |
| Nota [2] de la tabla | En sistemas sísmicos especiales se usa A706. Se permite A615 Grado 60 si cumple 20.2.2.5(b). |
| 22.4.2.1 | En el cálculo de Po, fy ≤ 80 000 psi. |

## Propiedades de sección para el análisis: ACI 6.3 y 6.6.3 (p. 74–80)

- **6.3.1.1:** las rigideces relativas deben salir de supuestos razonables y coherentes en todo el análisis.
- **R6.3.1.1** (comentario, p. 74):
  - EcI y GJ deberían reflejar el agrietamiento.
  - En **torsión de equilibrio** la rigidez torsional se incluye.
  - En **torsión de compatibilidad** suele no incluirse, porque la rigidez torsional agrietada es pequeña.
  - En pórticos arriostrados es común usar 0.5Ig en vigas e Ig en columnas.
- **Tabla 6.3.2.1:** ancho efectivo del ala de vigas T.
  - A cada lado del alma: el menor de 8h, sw/2 y ln/8.
  - A un solo lado: el menor de 6h, sw/2 y ln/12.
  - Viga T aislada: ala de espesor ≥ 0.5bw y ancho ≤ 4bw.
- **Tabla 6.6.3.1.1(a) (p. 78), análisis con cargas mayoradas:**

  | Miembro | I | Área axial | Área de cortante |
  |---|---|---|---|
  | Columnas | **0.70 Ig** | 1.0 Ag | bw·h |
  | Muros no agrietados / agrietados | 0.70 Ig / 0.35 Ig | 1.0 Ag | bw·h |
  | Vigas | **0.35 Ig** | 1.0 Ag | bw·h |
  | Losas y placas planas | 0.25 Ig | 1.0 Ag | bw·h |

  Si hay cargas laterales sostenidas, I de columnas y muros se divide por (1 + βds).
- **Tabla 6.6.3.1.1(b) (p. 79), alternativa:**
  - Columnas y muros: I = (0.80 + 25·Ast/Ag)(1 − Mu/(Pu·h) − 0.5·Pu/Po)·Ig, entre 0.35Ig y 0.875Ig.
  - Vigas y losas: I = (0.10 + 25ρ)(1.2 − 0.2·bw/d)·Ig, entre 0.25Ig y 0.5Ig.
- **6.6.3.1.2:** para cargas laterales mayoradas se permite **I = 0.5 Ig en todos los miembros**.
- **6.6.3.2.2 (p. 80):** para deflexiones laterales inmediatas en servicio se usa **1.4 × I de 6.6.3.1**, sin pasar de Ig. Aplica a la deriva por viento del REP 4.3.
- **6.6.2.3(b):** se permite suponer rígidas las zonas de nudo.
- **6.6.4.2:** las dimensiones del modelo deben estar dentro del 10 % de las de planos; si no, se repite el análisis.

## Hipótesis de resistencia: ACI 22.2 (p. 399–401)

- **Equilibrio y compatibilidad**, con deformaciones proporcionales a la distancia al eje neutro (22.2.1).
- **εcu = 0.003** en la fibra extrema comprimida (22.2.2.1). La tracción del concreto se desprecia (22.2.2.2).
- **Bloque rectangular**: 0.85 f'c uniforme sobre una profundidad a = β1·c (22.2.2.4.1).
- **β1** (Tabla 22.2.2.4.3, p. 401):
  - 0.85 si 2500 ≤ f'c ≤ 4000 psi;
  - 0.85 − 0.05(f'c − 4000)/1000 si 4000 < f'c < 8000 psi;
  - 0.65 si f'c ≥ 8000 psi.

  [SI: 0.85 hasta 28 MPa; 0.85 − 0.05(f'c − 28)/7; 0.65 desde 55 MPa.]

## Diferencias o contradicciones encontradas

1. **`beta1()`** (en los tres `iteracion*.py`) lanza error si f'c ≤ 2.5 ksi. La Tabla 22.2.2.4.3 incluye f'c = 2500 psi, así que la condición correcta es `fc < 2.5`.
2. **`fy(n)`** asigna 40 ksi a las barras #3. Solo es válido si se especifica Grado 40. En sistemas sísmicos especiales hace falta A706, o A615 Grado 60 que cumpla 20.2.2.5(b).
3. **`DIAM_ESPECIAL`** cubre #9 a #11. Para #14 y #18, n/8 da 1.75 in y 2.25 in, pero los diámetros reales son **1.693 in y 2.257 in**.
4. **Unidades:** el análisis trabaja en kN, m y kPa; los diagramas en pulgadas, ksi y kip, con salida en tonf. Conviene una sola política: SI por dentro y pint en la entrada y la salida.
5. **`ejemplos/portico.py`:** E = 25e6 kN/m² equivale a f'c ≈ 4000 psi (57 000·√4000 = 3.6e6 psi = 24.9 GPa) ✓, y G ≈ E/2.4 ✓. Pero las secciones usan **Ig sin reducir**: para análisis con cargas mayoradas el ACI pide 0.70Ig en columnas y 0.35Ig en vigas.

## Para el programa (qué implementar y cómo verificarlo)

- **Material de concreto:** f'c (o E directo), wc y ν → Ec según 19.2.2.1 y G = Ec/(2(1+ν)).
- **Material de acero:** fy, Es = 29 000 ksi, grado (A615 o A706).
- **Sección:** rectangular, circular y T, con A, Iy, Iz y J.
  - J de un rectángulo, por la fórmula de Saint-Venant aproximada: J ≈ [1/3 − 0.21·(b/h)·(1 − b⁴/(12h⁴))]·h·b³, con b ≤ h.
  - Modificadores de inercia por tipo de miembro según la Tabla 6.6.3.1.1(a), con opción 0.5Ig para cargas laterales y 1.4× para servicio.
  - Modificador de J para torsión de compatibilidad.
- **Verificaciones:**
  - Ec(4000 psi) = 3 605 000 psi.
  - β1 en los bordes: 2500 → 0.85; 4000 → 0.85; 5000 → 0.80; 8000 → 0.65. Además, continuidad en 4000 y en 8000.
  - Viga 30×50: Iy = 3.125e-3 m⁴ y J = 2.82e-3 m⁴, que coinciden con el ejemplo ✓.
  - Columna 40×40: I = 2.133e-3 m⁴ y J = 3.60e-3 m⁴ ✓.
