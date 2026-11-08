# Etapa 3: Combinaciones de carga

**Qué cubre:** con qué combinaciones se obtienen las fuerzas mayoradas (Pu, Mu, Vu, Tu) para diseñar, y cómo encajan ACI 318-19, ASCE 7-05 y el REP.

**Qué norma manda:**
- **REP 1.4.1 (p. 16):** "Las estructuras se diseñarán para resistir las combinaciones de carga del Capítulo 2 de ASCE/SEI 7-05." Lo repite en 9.4 (p. 103) para el acero.
- **REP 8.4 (p. 101):** "La carga de viento W… es a nivel de servicio. Para utilizarla con las combinaciones… 5.3 del ACI 318-19… deben multiplicarse por 1.6 (ACI 318-19 §5.3.5)."
- **REP 4.2 (p. 26):** "Las cargas de viento calculadas con el capítulo 6 del ASCE 7-05 son a nivel de servicio."

## ASCE 7-05 2.3.2: combinaciones de resistencia (p. 34, leídas en la imagen de la página)

| # | Combinación |
|---|---|
| 1 | 1.4(D + F) |
| 2 | 1.2(D + F + T) + 1.6(L + H) + 0.5(Lr o S o R) |
| 3 | 1.2D + 1.6(Lr o S o R) + (L o 0.8W) |
| 4 | 1.2D + 1.6W + L + 0.5(Lr o S o R) |
| 5 | 1.2D + 1.0E + L + 0.2S |
| 6 | 0.9D + 1.6W + 1.6H |
| 7 | 0.9D + 1.0E + 1.6H |

**Excepciones:**
1. El factor de L en 3, 4 y 5 puede ser **0.5** si Lo ≤ 100 psf, salvo en garajes y zonas de reunión pública.
2. El factor de H es 0 en 6 y 7 si H se opone a W o a E.
3. Nota de 2.3.2: hay que investigar el efecto de **una o más cargas que no actúan**. W y E no se combinan entre sí.
4. 2.1: se usa resistencia (2.3) **o** esfuerzos admisibles (2.4), una sola de las dos por material.

## ASCE 7-05 12.4: efecto sísmico E (p. 155–156)

- **E = Eh + Ev** en la combinación 5 y **E = Eh − Ev** en la 7 (Ec. 12.4-1 y 12.4-2).
- **Eh = ρ·QE** (Ec. 12.4-3). QE es el efecto de las fuerzas sísmicas horizontales (V o Fp). Donde lo pidan 12.5.3 y 12.5.4, se aplica en dos direcciones ortogonales a la vez.
- **Ev = 0.2·SDS·D** (Ec. 12.4-4). Vale 0 si SDS ≤ 0.125, o en la Ec. 12.4-2 para la interfaz suelo-cimiento.
- **Combinaciones sísmicas de resistencia (12.4.2.3):**
  - 5. (1.2 + 0.2·SDS)·D + ρ·QE + L + 0.2S
  - 7. (0.9 − 0.2·SDS)·D + ρ·QE + 1.6H
  - El factor de L en la 5 puede ser 0.5 con Lo ≤ 100 psf, salvo garajes y zonas de reunión.
  - En esfuerzos admisibles: 5. (1.0 + 0.14·SDS)·D + H + F + 0.7·ρ·QE.
- **Sobrerresistencia (12.4.3):** Em = Ω0·QE ± 0.2·SDS·D. Se usa solo donde la norma lo exige, por ejemplo en columnas bajo elementos discontinuos (12.3.3.3) y en colectores.
- **Redundancia ρ (12.3.4, p. 154–155):**
  - ρ = 1.0 en CDS B y C, para deriva y P-Δ, en no estructurales y en elementos diseñados con Ω0.
  - En CDS D a F, **ρ = 1.3**, salvo que se cumpla una de estas dos:
    - (a) cada piso que toma más del 35 % del cortante basal cumple la Tabla 12.3-3. En pórticos de momento: perder los dos extremos de una viga no baja la resistencia del piso más de 33 % ni crea una irregularidad torsional extrema;
    - (b) estructura regular en planta con al menos 2 vanos de pórtico perimetral por lado y dirección.

## ACI 318-19 5.3 (p. 64–67)

- **Tabla 5.3.1:**
  - (a) 1.4D
  - (b) 1.2D + 1.6L + 0.5(Lr o S o R)
  - (c) 1.2D + 1.6(Lr o S o R) + (1.0L o 0.5W)
  - (d) 1.2D + 1.0W + 1.0L + 0.5(Lr o S o R)
  - (e) 1.2D + 1.0E + 1.0L + 0.2S
  - (f) 0.9D + 1.0W
  - (g) 0.9D + 1.0E
- **5.3.3:** el factor de L en (c), (d) y (e) puede ser 0.5, salvo en garajes, reunión pública o L > 100 psf.
- **5.3.4:** L incluye cargas concentradas, vehiculares, de grúas, barandas, impacto y vibración.
- **5.3.5:** si W es de servicio, se usa **1.6W** en lugar de 1.0W en (d) y (f), y **0.8W** en lugar de 0.5W en (c).
- **5.3.6 a 5.3.8:**
  - T (cambio de volumen y asentamiento): factor ≥ 1.0.
  - F (fluidos): 1.4 / 1.2 / 0.9.
  - H (empuje de tierras): 1.6 si se suma; 0.9 si se opone y es permanente; no se incluye si se opone y no es permanente.
- **5.2.2 y 5.2.3:** las cargas, la CDS y la reducción de viva se toman del reglamento general, que en Panamá es el REP → ASCE 7-05.

## Diferencias o contradicciones encontradas

1. **No hay contradicción ACI–ASCE–REP:** con viento a nivel de servicio (REP 4.2), las combinaciones de ACI 5.3 con el 5.3.5 dan lo mismo que ASCE 7-05 2.3.2: 1.6W en lugar de 1.0W y 0.8W en lugar de 0.5W. **Error típico:** usar 1.0W de ACI 318-19 con el viento del REP, que da un 37.5 % menos de viento.
2. **`combinacionescarga.py`:**
   - **falta Lr**: la 2 lleva +0.5Lr; la 3 es 1.2D + 1.6Lr + (L o 0.8W), así que faltan los casos 1.2D + 1.6Lr + L y 1.2D + 1.6Lr ± 0.8W; la 4 lleva +0.5Lr;
   - S y R son 0 en Panamá (no nieva). R es la lluvia acumulada en el techo (cap. 8 de ASCE), que el REP 3.3 sí exige;
   - no aplica la opción 0.5L de la excepción 1;
   - SDS y ρ están fijos en el código. Deberían venir de la etapa de sismo;
   - E y W deberían considerarse en **X e Y y con los dos signos**, y en sismo también con la torsión accidental (etapa 7).
3. **Unidades de E:** el E de ASCE 7-05 ya está a nivel de resistencia (factor 1.0). No se multiplica.

## Para el programa (qué implementar y cómo verificarlo)

- **Casos de carga con nombre** (D, L, Lr, R, W±x, W±y, E±x, E±y, H…). Las combinaciones son **factores × casos**; como el análisis es lineal, el resultado es la suma de los resultados de cada caso.
- **Generador de combinaciones** según ASCE 7-05 2.3.2 y 12.4.2.3, con:
  - SDS y ρ como datos;
  - la opción 0.5L con sus exclusiones;
  - los signos ± de W y E.
- **Envolventes:** máximo y mínimo de cada esfuerzo, y qué combinación los produce.
- **Verificaciones:**
  - Una barra con D = 10 y L = 5 → la combinación 2 da 20; la 1 da 14.
  - Con W de servicio = 10: la 4 debe dar 1.2D + 16 (no 1.2D + 10).
  - Con SDS = 0.5: las combinaciones 5 y 7 dan 1.3D + ρQE + L y 0.8D + ρQE.
