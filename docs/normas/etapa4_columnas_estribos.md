# Etapa 4: Columnas (flexo-compresión, esbeltez, cortante y estribos)

**Qué cubre:**
- resistencia a flexo-compresión (lo que ya hacen los diagramas de interacción);
- límites de refuerzo y factores φ;
- esbeltez;
- cortante;
- **verificación de estribos**, tanto los no sísmicos (cap. 10 y 25.7) como los sísmicos según el tipo de pórtico (18.3, 18.4 y 18.7).

**Qué norma manda:**
- ACI 318-19 (REP 8.1). Las fuerzas Pu, Mu y Vu salen de las combinaciones de ASCE 7-05 (etapa 3).
- El tipo de pórtico (ordinario, intermedio o especial) lo fija la CDS (ASCE 7-05 Tabla 12.2-1, etapa 7). En la ciudad de Panamá lo usual es **CDS D**, que exige **pórtico especial**.

## Diseño general: ACI cap. 10 (p. 157–165)

| Cláusula | Qué dice |
|---|---|
| 10.3.1.1 | Una columna cuadrada u octogonal se puede diseñar como circular, con diámetro igual a su menor dimensión. |
| 10.3.1.2 | Si la columna es más grande de lo necesario, se puede usar un área efectiva reducida, no menor que la mitad. **No aplica en pórticos especiales.** |
| 10.4.2.1 | Pu y Mu se toman **simultáneos**, de la misma combinación. |
| 10.5.1.1 | φPn ≥ Pu, φMn ≥ Mu, φVn ≥ Vu y φTn ≥ Tu, considerando la interacción. |
| 10.6.1.1 (p. 160) | **0.01Ag ≤ Ast ≤ 0.08Ag**. En pórticos especiales el máximo es **0.06Ag** (18.7.4.1). |
| 10.6.2 | Donde Vu > 0.5·φ·Vc: Av,min = mayor de 0.75√f'c·bw·s/fyt y 50·bw·s/fyt (psi). |
| 10.7.3.1 (p. 161) | Mínimo de barras: **3** con estribos triangulares, **4** con estribos rectangulares o circulares y **6** con espiral (o con aros circulares en pórtico especial). |
| 10.7.6.2 (p. 164) | **Primer estribo a ≤ s/2** sobre la zapata o la losa; **último a ≤ s/2** bajo el refuerzo de la losa; ≤ 3 in bajo la viga más baja si llegan vigas por los 4 lados. |
| 10.7.6.1.5 | Si hay pernos de anclaje arriba: al menos 2 estribos #4 o 3 #3 en las 5 in superiores. |
| Tabla 10.7.6.5.2 (p. 165) | Separación máxima del refuerzo por cortante: **d/2 y 24 in** si Vs ≤ 4√f'c·bw·d; **d/4 y 12 in** si es mayor. Los valores en pulgadas no salieron en el texto extraído; son los mismos de la Tabla 9.7.6.2.2 de vigas. |

## Estribos y espirales: ACI 25.7 (p. 496–505)

- **25.7.2.1 Separación de estribos:**
  - libre ≥ (4/3)·dagg;
  - centro a centro **≤ el menor de 16·db longitudinal, 48·db del estribo y la menor dimensión** de la columna.
- **25.7.2.2 Diámetro:** **#3** si las barras son #10 o menores; **#4** si son #11, #14, #18 o paquetes.
- **25.7.2.3 Arreglo:**
  - (a) **cada esquina y barra por medio** apoyada en una esquina de estribo de **≤ 135°**;
  - (b) **ninguna barra sin apoyo a más de 6 in libres** de una barra apoyada.
- **25.7.2.3.1:** anclaje con ganchos estándar (25.3.2).
- **25.7.2.4:** estribos circulares con traslape ≥ 6 in, ganchos y traslapes alternados.
- **25.7.3 Espirales:**
  - paso libre entre max(1 in, 4/3·dagg) y 3 in;
  - diámetro ≥ 3/8 in;
  - **ρs ≥ 0.45(Ag/Ach − 1)·f'c/fyt**, con fyt ≤ 100 ksi;
  - anclaje con 1.5 vueltas extra.

## Resistencia de la sección

- **22.4.2.1–2 (p. 402):** Pn ≤ Pn,max (Tabla 22.4.2.1).
  - Con **estribos**: **0.80·Po**.
  - Con **espiral**: **0.85·Po**.
  - **Po = 0.85·f'c·(Ag − Ast) + fy·Ast**, con fy ≤ 80 ksi.
- **21.2.1 (p. 393):** φ = 0.65–0.90 en flexo-compresión (21.2.2); **0.75 en cortante y en torsión**; 0.65 en aplastamiento.
- **Tabla 21.2.2 (p. 395), con εty = fy/Es** (en Grado 60 se permite 0.002, 21.2.2.1):
  - εt ≤ εty: **0.65** con estribos y **0.75** con espiral (controla la compresión);
  - εt ≥ εty + 0.003: **0.90** (controla la tracción);
  - entre ambos: 0.65 + 0.25(εt − εty)/0.003 con estribos, o 0.75 + 0.15(εt − εty)/0.003 con espiral.
- **Cortante, 22.5 (p. 403–412):**
  - **Vn = Vc + Vs**. Límite de la sección: **Vu ≤ φ(Vc + 8√f'c·bw·d)**.
  - **Vc (Tabla 22.5.5.1):**
    - con Av ≥ Av,min: [2λ√f'c + Nu/(6Ag)]·bw·d, o [8λ(ρw)^(1/3)√f'c + Nu/(6Ag)]·bw·d;
    - con Av < Av,min: [8·λs·λ(ρw)^(1/3)√f'c + Nu/(6Ag)]·bw·d, con λs = √(2/(1 + d/10)) ≤ 1 (d en pulgadas);
    - Nu es positiva en compresión y Nu/(6Ag) ≤ 0.05·f'c;
    - Vc ≥ 0 y **Vc ≤ 5λ√f'c·bw·d**;
    - √f'c ≤ 100 psi (22.5.3.1).
  - **Sección circular (22.5.2.2):** d = 0.8·D y bw = D.
  - **Vs = Av·fyt·d/s** (22.5.8.5.3), con fyt ≤ 60 ksi (Tabla 20.2.2.4(a)).
  - **Cortante biaxial (22.5.1.10–11):** se puede ignorar la interacción si vu,x/φvn,x ≤ 0.5 o vu,y/φvn,y ≤ 0.5. Si no, la suma de ambas relaciones debe ser **≤ 1.5**. En 3D esto importa.

## Esbeltez: ACI 6.2.5 y 6.6.4 (p. 70–84)

- **Despreciable si** k·lu/r ≤ 22 (no arriostrado), o k·lu/r ≤ 34 + 12·M1/M2 y ≤ 40 (arriostrado). r = 0.30h (rectangular) o 0.25D (circular).
- **Se considera no desplazable** si el 2.º orden aumenta los momentos ≤ 5 %, o si Q = ΣPu·Δo/(Vus·lc) ≤ 0.05.
- **Pc y rigidez efectiva:**
  - Pc = π²(EI)eff/(k·lu)²;
  - (EI)eff = 0.4·Ec·Ig/(1+βdns), o (0.2·Ec·Ig + Es·Ise)/(1+βdns), o Ec·I/(1+βdns);
  - k = 1.0 se permite en no desplazables; en desplazables k ≥ 1.0.
- **No desplazable:**
  - Mc = δ·M2, con δ = Cm/(1 − Pu/(0.75·Pc)) ≥ 1;
  - Cm = 0.6 − 0.4·M1/M2 (1.0 si hay cargas transversales);
  - **M2,min = Pu(0.6 + 0.03h)** (in), por eje.
- **Desplazable:**
  - M = Mns + δs·Ms, con δs = 1/(1−Q) o 1/(1 − ΣPu/(0.75·ΣPc));
  - si δs > 1.5, solo se permite la segunda fórmula o un análisis de 2.º orden;
  - las vigas se diseñan para los momentos magnificados de las columnas (6.6.4.6.3).
- **Tope:** Mu de 2.º orden ≤ 1.4 × Mu de 1.er orden (6.2.5.3).

## Requisitos sísmicos según el tipo de pórtico

| | Ordinario, OMF (18.3, p. 293) | Intermedio, IMF (18.4.3, p. 295–296) | **Especial, SMF (18.7, p. 307–312)** |
|---|---|---|---|
| Cortante de diseño | Si lu ≤ 5c1: φVn ≥ el menor entre el cortante por Mn (el mayor) y el de las combinaciones con Ω0·E | φVn ≥ el menor entre el cortante por Mn en los extremos y el de las combinaciones con Ω0·E | **Ve por Mpr** (1.25fy, φ = 1) en los extremos, con el rango de Pu. Ve ≥ el del análisis. **Vc = 0 en lo** si el cortante sísmico ≥ ½ del total y Pu < Ag·f'c/20 |
| Zona confinada lo | — | ≥ el mayor de lu/6, la dimensión mayor y 18 in | **≥ el mayor de h, lu/6 y 18 in** |
| Separación en lo | — | so ≤ el menor de 8db (Gr 60), 8 in y bmín/2. **Primer aro a ≤ so/2** | **s ≤ el menor de bmín/4, 6db (Gr 60) o 5db (Gr 80) y so = 4 + (14 − hx)/3**, con 4 ≤ so ≤ 6 in |
| Cantidad de refuerzo transversal | — | — | **Ash/(s·bc) ≥ mayor de 0.3(Ag/Ach − 1)·f'c/fyt y 0.09·f'c/fyt**. Si Pu > 0.3·Ag·f'c o f'c > 10 ksi, también 0.2·kf·kn·Pu/(fyt·Ach), con kf = f'c/25 000 + 0.6 ≥ 1 y kn = nl/(nl − 2). Con espiral: ρs ≥ mayor de 0.45(Ag/Ach − 1)·f'c/fyt y 0.12·f'c/fyt |
| Arreglo | — | — | hx ≤ 14 in. Si Pu > 0.3·Ag·f'c: cada barra apoyada y hx ≤ 8 in |
| Fuera de lo | 10.7.6.5.2 | 10.7.6.5.2 | s ≤ el menor de 6 in, 6db (Gr 60) y 5db (Gr 80) |
| Otros | — | — | Dimensión mínima ≥ 12 in y relación de lados ≥ 0.4. **ΣMnc ≥ (6/5)·ΣMnb**. 0.01 ≤ ρ ≤ 0.06. Traslapes solo en la mitad central |

## Diferencias o contradicciones encontradas

1. **Columna circular** (`calculo/interaccion/circular.py`): usa φ = 0.65 y 0.80·Po, que son los valores de estribos. Si lleva **espiral**, corresponden 0.75, 0.75 + 0.15(…) y 0.85·Po. Hay que elegir el tipo de refuerzo transversal.
2. **Cuantía 1 %–8 %** (`mostrar_propiedades`): en **pórticos especiales el máximo es 6 %** (18.7.4.1). Conviene que el límite dependa del tipo de pórtico.
3. **"Verificar estribos" depende del tipo de pórtico.** En CDS D (lo usual en la ciudad de Panamá) mandan los requisitos de 18.7, no solo los de 25.7.2. Además, el cortante de diseño sale de **Mpr**, que se calcula con el diagrama de interacción (con 1.25fy y φ = 1). Los diagramas que ya existen sirven para obtener Mn y Mpr.
4. **Cortante biaxial:** en un programa 3D hay que revisar el 22.5.1.11, y no cada dirección por separado.

## Para el programa (qué implementar y cómo verificarlo)

- **Entrada:** sección, barras longitudinales, estribos (diámetro, ramas en x e y, separación en lo y fuera de lo), tipo de pórtico, f'c, fy y fyt.
- **Revisiones de 25.7.2 y 10.7.6:**
  - separación máxima;
  - diámetro mínimo;
  - barras apoyadas cada 6 in;
  - posición del primer y del último estribo.
- **Revisiones sísmicas de 18.4.3 y 18.7.5:** lo, so, Ash y hx.
- **Cortante:** Vc según la Tabla 22.5.5.1 (con Nu), Vs, Vu ≤ φVn, límite de la sección e interacción biaxial. En SMF, Ve por Mpr con el diagrama de interacción.
- **Verificaciones:**
  - un ejemplo resuelto de un texto con ACI 318-19 (por ejemplo, Wight & MacGregor, 8.ª ed., o McCormac & Brown, 11.ª ed., capítulo de columnas);
  - casos borde: Pu = 0.3·Ag·f'c justo en el límite, y db #10/#11 para el cambio de diámetro mínimo.
