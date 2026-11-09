# Etapa 2: Cargas en barras y diagramas de fuerzas internas

**Qué cubre:** qué cargas de gravedad se aplican (muerta, viva, tabiques, impacto), cómo se distribuyen (área tributaria, carga parcial, alternancia de la viva), qué métodos de análisis permite el ACI y qué le falta al programa: cargas sobre barras y diagramas N, V, T y M.

**Qué norma manda:**
- REP 2021 2.1–2.2 (p. 23): muerta según ASCE 7-05 cap. 3 y viva según el cap. 4 (incluye la Tabla 4-1 y las reducciones 4.8 y 4.9).
- REP 1.4.7 (p. 17): cargas durante la construcción según SEI/ASCE 37-02.
- El análisis se rige por ACI 318-19 cap. 6.

## REP 2021: lo que cambia

- **Tabiques (REP 2.1, p. 23):** "carga mínima para paredes de **0.75 kPa** si la carga viva es menor de **4 kPa**", clasificada como **carga muerta** dentro de 2.1. Además pide cargar las paredes según su ubicación real en planta y cuidar las concentraciones de paredes.

## ASCE 7-05: cargas (p. 36–42)

| Sección | Qué dice |
|---|---|
| 3.1 (p. 36) | Muerta = peso real de todos los materiales y del equipo fijo (tuberías, ductos, HVAC). |
| 4.2.1 (p. 38) | Viva = la máxima esperada, nunca menor que la de la Tabla 4-1 (p. 41–42). |
| 4.2.2 (p. 38) | Tabiques: **carga viva** de al menos 15 psf [0.72 kN/m²] en oficinas y edificios con tabiques movibles. No se exige si la viva pasa de 80 psf [3.83 kN/m²]. |
| 4.3 (p. 38) | Se diseña para la viva uniforme **o** para la concentrada de la Tabla 4-1, la que produzca mayor efecto. La concentrada actúa sobre 2.5 ft × 2.5 ft (762 mm; 0.58 m²). |
| 4.6 (p. 39) | **Carga parcial:** la viva (ya reducida) aplicada solo en una parte de la estructura, si eso es más desfavorable. |
| 4.7 (p. 39) | Impacto: ascensores +100 %. Maquinaria de ascensor +100 %; maquinaria liviana +20 %; maquinaria alternativa +50 %; colgantes de pisos o balcones +33 %. |
| 4.8 (p. 39) | Reducción de viva. Aplica si KLL·AT ≥ 400 ft² [37.16 m²]:<br>• L = Lo(0.25 + 15/√(KLL·AT)) [en SI con 4.57];<br>• mínimos: L ≥ 0.50Lo (un piso) y L ≥ 0.40Lo (dos o más pisos);<br>• 4.8.2: viva > 100 psf no se reduce, salvo −20 % en miembros que soportan 2 o más pisos;<br>• 4.8.3: garajes de autos, igual que 4.8.2;<br>• 4.8.4: zonas de reunión pública con ≤ 100 psf no se reducen;<br>• 4.8.5: en losas en una dirección, AT ≤ luz × 1.5·luz;<br>• KLL en la Tabla 4-2 (p. 42). |
| 4.9 (p. 39–40) | Reducción de viva de techo:<br>• Lr = Lo·R1·R2, con 12 ≤ Lr ≤ 20 psf [0.58–0.96 kN/m²];<br>• R1 = 1 si At ≤ 200 ft² [18.58 m²]; 1.2 − 0.001·At [SI: 1.2 − 0.011·At]; 0.6 si At ≥ 600 ft² [55.74 m²];<br>• R2 = 1 si F ≤ 4; 1.2 − 0.05F; 0.6 si F ≥ 12;<br>• F = pulgadas de subida por pie [SI: 0.12 × pendiente en %]; en arcos y domos, F = 32·(flecha/luz);<br>• 4.9.2: techos con uso (jardines, reunión) se reducen por 4.8. |

## ACI 318-19: análisis (p. 69–87)

| Sección | Qué dice |
|---|---|
| 6.2.2 (p. 69) | Hay que obtener los efectos máximos **considerando la disposición de la carga viva** (6.4). |
| 6.2.3 | Métodos permitidos: (a) simplificado 6.5; (b) **elástico lineal de 1.er orden 6.6**, que es lo que hace el programa; (c) elástico de 2.º orden 6.7; (d) inelástico 6.8; (e) elementos finitos 6.9. |
| 6.2.5.1 (p. 70) | Se puede despreciar la esbeltez si:<br>• pórtico no arriostrado: k·lu/r ≤ 22;<br>• arriostrado: k·lu/r ≤ 34 + 12(M1/M2) y ≤ 40, con M1/M2 negativo en curvatura simple.<br>Un piso se considera arriostrado si el arriostramiento tiene al menos 12 veces la rigidez lateral bruta de sus columnas. |
| 6.2.5.2 (p. 71) | r = √(Ig/Ag), o 0.30·h en columnas rectangulares y 0.25·D en circulares. |
| 6.2.5.3 (p. 72) | Si la esbeltez cuenta, se diseña con efectos de 2.º orden (6.6.4, 6.7 o 6.8). **Mu de 2.º orden ≤ 1.4·Mu de 1.er orden.** |
| 6.3.1.2 (p. 74) | Para gravedad se permite un submodelo: el nivel en estudio más las columnas de arriba y de abajo, con sus extremos lejanos empotrados. |
| 6.4.1–6.4.2 (p. 75) | La viva puede ir solo en el nivel en estudio. Vigas y losas en una dirección:<br>• +Mu máximo con L mayorada en el tramo y en tramos alternos;<br>• −Mu máximo en un apoyo con L solo en los tramos adyacentes. |
| 6.4.3 (p. 75–76) | Losas en dos direcciones:<br>• si se conoce la disposición, se analiza esa;<br>• si L ≤ 0.75D o todos los paneles se cargan juntos, todos cargados;<br>• si no, 75 % de L mayorada en tableros alternos (positivo) o adyacentes (negativo), y nunca menos que con todo cargado. |
| 6.5 (p. 76–77) | **Método simplificado.** Condiciones: miembros prismáticos, carga uniforme, L ≤ 3D, al menos dos tramos, y tramos adyacentes que no difieran más de 20 %.<br>Tabla 6.5.2 (Mu = wu·ln²/coef.):<br>• positivo: 14 en tramo extremo con extremo monolítico; 11 si no está restringido; 16 en tramos interiores;<br>• negativo: 24 con viga de borde y 16 con columna en el apoyo exterior; 9 (dos tramos) o 10 (más tramos) en el primer apoyo interior; 11 en los demás; 12 con la condición (a) o (b);<br>• para negativos, ln es el promedio de las luces libres adyacentes.<br>Tabla 6.5.4: Vu = 1.15·wu·ln/2 en la cara exterior del primer apoyo interior y wu·ln/2 en los demás. Estos momentos no se redistribuyen (6.5.3). |
| 6.6.2.1 | El momento del nivel se reparte entre las columnas de arriba y de abajo según su rigidez. |
| 6.6.2.3 (p. 77–78) | Se permite: (a) losas macizas o viguetas con luz libre ≤ 10 ft como vigas continuas sobre apoyos puntuales; (b) **zonas de nudo rígidas**. |
| 6.6.5 (p. 84–85) | **Redistribución** en miembros continuos: requiere εt ≥ 0.0075 en la sección y como máximo el menor de 1000·εt % y 20 %. Se mantiene el equilibrio, y los cortantes salen por estática. |
| 6.7 (p. 86–87) | 2.º orden elástico: considera la carga axial, el agrietamiento (propiedades de 6.7.2) y la duración de la carga. |

## Diferencias o contradicciones encontradas

1. **Tabiques:** el REP 2.1 los pone como **carga muerta** de 0.75 kPa si la viva es menor de 4 kPa. ASCE 7-05 4.2.2 los pone como **viva** de 0.72 kPa si la viva es de 80 psf (3.83 kPa) o menos. Manda el REP: van en D (factor 1.2 en lugar de 1.6).
2. **El programa solo acepta cargas en los nodos.** Sin cargas en barras no hay momentos de tramo ni diagramas, y no se pueden diseñar vigas. Esta etapa es requisito de las etapas 4 y 5.
3. La alternancia de la viva (ACI 6.4 y ASCE 4.6) obliga a analizar **varias disposiciones** de L, no solo L en todo el piso.

## Para el programa (qué implementar y cómo verificarlo)

- **Cargas en barras:** uniforme (ejes globales o locales), puntual a una distancia a y, si se quiere, trapezoidal. Además, el peso propio (A · γ): γ del concreto reforzado = 150 lb/ft³ ≈ 23.56 kN/m³ (ASCE 7-05 Tabla C3-2, PDF p. 295, revisado en el PDF). El programa ya lo usa como valor por defecto del concreto.
- **Pasos del cálculo:**
  1. Fuerzas de empotramiento en ejes locales.
  2. Transformarlas a ejes globales (Tᵀ).
  3. Cargas nodales equivalentes = −FEF.
  4. Después de resolver: fuerzas en los extremos = k·u + FEF.

  Hay que respetar la convención del programa: fuerzas que los nodos ejercen sobre la barra.
- **Diagramas a lo largo de x:** N, Vy, Vz, T, My y Mz, a partir de las fuerzas en los extremos y de las cargas del tramo, incluyendo el valor máximo y su posición.
- **Casos de carga** separados (D, L, Lr, W, E…), para combinarlos en la etapa 3.
- **Verificaciones:**
  - Viga simple con w: M = wL²/8 y V = wL/2.
  - Biempotrada: −wL²/12 en los extremos y +wL²/24 al centro.
  - Apoyada-empotrada: −wL²/8.
  - Carga puntual centrada en una biempotrada: PL/8.
  - Equilibrio de cada barra: Σ fuerzas en extremos + Σ cargas = 0.
  - Una viga continua de tramos iguales comparada con los coeficientes de la Tabla 6.5.2. Es solo un orden de magnitud: el REP 1.8.2.6 pide justamente verificar con métodos aproximados.
