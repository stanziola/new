# Etapa 5: Vigas (acero longitudinal, estribos, torsión y servicio)

**Qué cubre:**
- diseño a flexión (As) y a cortante (estribos);
- torsión;
- límites de refuerzo y detallado;
- deflexiones y fisuración;
- desarrollo y empalmes;
- requisitos sísmicos de vigas según el tipo de pórtico.

**Qué norma manda:** ACI 318-19 (REP 8.1). Mu, Vu y Tu salen de las etapas 2 y 3. El tipo de pórtico (OMF, IMF o SMF) lo fija la CDS (etapa 7).

## Límites y resistencia: ACI cap. 9 (p. 129–152)

| Cláusula | Qué dice |
|---|---|
| Tabla 9.3.1.1 (p. 131) | **Altura mínima** si la viga no soporta elementos que se dañen con deflexiones: simplemente apoyada ℓ/16; un extremo continuo ℓ/18.5; ambos continuos ℓ/21; voladizo ℓ/8. Vale para concreto normal y fy = 60 ksi; con otro fy se multiplica por (0.4 + fy/100 000). Si no cumple, se calculan las deflexiones (24.2). |
| **9.3.3.1** (p. 132) | Vigas con Pu < 0.10·f'c·Ag: **deben quedar controladas por tracción**, es decir εt ≥ εty + 0.003, con φ = 0.90. **Cambio del 318-19**: antes bastaba εt ≥ 0.004. |
| 9.4.2.1 / 9.4.3.1 | Mu y Vu se pueden tomar **en la cara del apoyo**. |
| 9.4.3.2 | Vu se puede tomar a una distancia **d** de la cara si la reacción comprime el extremo, la carga está arriba y no hay cargas concentradas en ese tramo. |
| 9.4.4 | La torsión que transmite una losa se puede suponer uniforme a lo largo de la viga. Sección crítica a d. |
| 9.5.2.1–2 | Si Pu < 0.10·f'c·Ag, Mn se calcula con 22.3 (flexión). Si no, con 22.4 (flexo-compresión, como una columna). |
| 9.5.4.1 | Si Tu < φ·Tth, la torsión se desprecia. |
| **9.6.1.2** (p. 137–138) | **As,min = mayor de 3√f'c·bw·d/fy y 200·bw·d/fy** (psi) [SI: 0.25√f'c·bw·d/fy y 1.4·bw·d/fy]. Con fy ≤ 80 ksi. En vigas T isostáticas con el ala en tracción, bw = min(bf, 2bw). |
| 9.6.1.3 | No se exige As,min si en todas las secciones As colocado ≥ 4/3 de As requerido. |
| **9.6.3.1** (p. 138) | **Av,min donde Vu > φ·λ·√f'c·bw·d**. **Cambio del 318-19**: antes era 0.5·φ·Vc. Excepciones de la Tabla 9.6.3.1, que solo lo exigen si Vu > φVc: h ≤ 10 in; vigas integradas con la losa con h ≤ el mayor de 2.5tf y 0.5bw, y h ≤ 24 in; viguetas. |
| Tabla 9.6.3.4 (p. 140) | **Av,min/s = mayor de 0.75√f'c·bw/fyt y 50·bw/fyt.** |
| 9.6.4 | Torsión mínima: (Av + 2At)/s ≥ el mayor de 0.75√f'c·bw/fyt y 50·bw/fyt. Para Aℓ,min, la expresión de 9.6.4.3. |
| **Tabla 9.7.6.2.2** (p. 149) | **Separación máxima de estribos.** Si Vs ≤ 4√f'c·bw·d: a lo largo, el menor de **d/2 y 24 in**; a lo ancho, d. Si Vs > 4√f'c·bw·d: **d/4 y 12 in** a lo largo y d/2 a lo ancho. |
| 9.7.6.3 (p. 149–150) | Torsión: **estribos cerrados** con ganchos de 135° (25.7.1.6), que se extienden (bt + d) más allá; separación ≤ el menor de **ph/8 y 12 in**. |
| 9.7.6.4 (p. 150) | Barras en compresión: estribos #3 (#4 si las barras son #11 o mayores), con s ≤ el menor de 16db, 48db del estribo y la menor dimensión. Esquinas y barra por medio apoyadas a ≤ 135°, y ninguna barra a más de 6 in. |
| 9.7.2.2–3 | Separación máxima por fisuración (24.3). Si h > 36 in, refuerzo de piel en las caras laterales. |
| 9.7.3.8 (p. 144) | Corte de barras: al menos 1/3 del refuerzo positivo entra 6 in o más en los apoyos simples, y 1/4 en los demás. Si la viga es parte del sistema lateral, ese refuerzo se ancla para desarrollar fy. |
| **9.7.7** (p. 151–152) | **Integridad estructural.** Vigas de perímetro: ≥ 1/4 del positivo y ≥ 1/6 del negativo continuos (al menos 2 barras), con estribos cerrados. Otras vigas: 1/4 del positivo continuo, o estribos cerrados. Empalmes del positivo cerca del apoyo y del negativo cerca del centro, Clase B o mecánicos. |

## Resistencia de la sección

- **22.2 y 22.3:** εcu = 0.003, bloque 0.85·f'c·β1·c y compatibilidad (ver etapa 1).
  - Viga simplemente reforzada: a = As·fy/(0.85·f'c·b) y Mn = As·fy·(d − a/2).
  - Se verifica εt para obtener φ (Tabla 21.2.2).
- **Cortante, 22.5 (ver etapa 4):** Vc según la Tabla 22.5.5.1, Vs = Av·fyt·d/s, φ = 0.75 y Vu ≤ φ(Vc + 8√f'c·bw·d).
- **Torsión, 22.7 (p. 422–430):**
  - **Torsión de equilibrio** (22.7.3.1): se diseña para Tu.
  - **Torsión de compatibilidad** (22.7.3.2): Tu se puede reducir a φ·Tcr, redistribuyendo a los miembros vecinos.
  - Tth está en la Tabla 22.7.4.1. Para sección maciza sin axial, Tth = λ√f'c·Acp²/pcp, y Tcr = 4·Tth.
  - Tn = 2·Ao·At·fyt·cotθ/s, con θ = 45° y Ao = 0.85·Aoh. Aℓ = (At/s)·ph·(fyt/fy)·cot²θ.
  - Límite de la sección: √[(Vu/(bw·d))² + (Tu·ph/(1.7·Aoh²))²] ≤ φ[Vc/(bw·d) + 8√f'c].

## Servicio: ACI cap. 24 (p. 457–463)

- **Tabla 24.2.2, deflexiones máximas:**
  - techos planos que no soportan elementos frágiles: ℓ/180, inmediata por Lr;
  - pisos: **ℓ/360**, inmediata por L;
  - con elementos que se pueden dañar: ℓ/480, la parte que ocurre después de colocarlos;
  - con elementos que no se dañan: ℓ/240.

  Los valores numéricos de la tabla no salieron en el texto extraído; son los usuales del ACI.
- **Tabla 24.2.3.5, inercia efectiva (fórmula nueva del 318-19):**
  - Ie = Ig si Ma ≤ (2/3)·Mcr;
  - si no, **Ie = Icr / [1 − ((2/3)·Mcr/Ma)²·(1 − Icr/Ig)]**;
  - Mcr = fr·Ig/yt;
  - en tramos continuos se toma el promedio de las secciones críticas, y en voladizos el valor en el apoyo.
- **24.2.4, deflexión diferida:** λΔ = ξ/(1 + 50ρ'). ξ = 1.0 (3 meses), 1.2 (6), 1.4 (12) y 2.0 (5 años o más).
- **Tabla 24.3.2, fisuración:** s ≤ el menor de 15(40 000/fs) − 2.5·cc y 12(40 000/fs), con fs en psi. Se permite fs = (2/3)·fy.

## Desarrollo y empalmes: ACI cap. 25 (p. 469–495)

- **25.2:** separación libre mínima entre barras de una capa ≥ el mayor de 1 in, db y (4/3)·dagg. Entre capas, ≥ 1 in.
- **Tabla 25.4.2.3, ld simplificado:** separación ≥ db, recubrimiento ≥ db y estribos mínimos (o separación ≥ 2db):
  - ld = fy·ψt·ψe·ψg/(**25**·λ√f'c)·db para #6 y menores;
  - /(**20**·λ√f'c) para #7 y mayores;
  - en los demás casos, 1.5 veces esos valores;
  - **ld ≥ 12 in**.
- **25.4.2.4, ld detallado:** 3·fy·ψt·ψe·ψs·ψg/(40·λ√f'c·(cb + Ktr)/db)·db, con (cb + Ktr)/db ≤ 2.5 y Ktr = 40·Atr/(s·n).
- **Tabla 25.4.2.5, factores:**
  - ψt = 1.3 si hay más de 12 in de concreto fresco debajo; ψe = 1.5 o 1.2 si es epóxica; ψtψe ≤ 1.7;
  - ψs = 0.8 para #6 y menores;
  - **ψg = 1.0 (Gr 40/60), 1.15 (Gr 80) o 1.3 (Gr 100)**, nuevo en el 318-19;
  - λ = 0.75 en concreto liviano.
- **25.4.3.1, gancho:** ldh = el mayor de (fy·ψe·ψr·ψo·ψc/(55·λ√f'c))·db^1.5, 8db y 6 in. Fórmula nueva del 318-19.
- **25.5.2, traslapes en tracción:** Clase A = 1.0·ld; Clase B = 1.3·ld; ≥ 12 in.

## Requisitos sísmicos de vigas según el tipo de pórtico

| | Ordinario, OMF (18.3.2) | Intermedio, IMF (18.4.2, p. 294–295) | **Especial, SMF (18.6, p. 302–306)** |
|---|---|---|---|
| Longitudinal | ≥ 2 barras continuas arriba y abajo; el continuo inferior ≥ 1/4 del máximo inferior, anclado para fy | Igual que OMF, más M+ en la cara ≥ 1/3 M−, y M+ y M− en cualquier sección ≥ 1/5 del máximo | ≥ 2 barras continuas; As ≥ As,min arriba y abajo; **ρ ≤ 0.025** (Gr 60) o 0.02 (Gr 80); **M+ en la cara ≥ 1/2 M−**; en cualquier sección ≥ 1/4 del máximo |
| Cortante | — | φVn ≥ el menor entre el cortante por Mn en los extremos más gravedad y el de las combinaciones con **2E** | **Ve por Mpr** (1.25fy, φ = 1) de signos opuestos en las caras, más wu = (1.2 + 0.2SDS)D + 1.0L + 0.2S. **Vc = 0** en 2h si el cortante sísmico ≥ ½ del total y Pu < Ag·f'c/20 |
| Aros | En 2h desde la cara: primer aro ≤ 2 in; s ≤ el menor de d/4, 8db, 24db del aro y 12 in. En el resto, s ≤ d/2 | Igual que IMF (esa columna) | En 2h desde las caras y junto a rótulas: primer aro ≤ 2 in; **s ≤ el menor de d/4, 6 in, 6db (Gr 60) y 5db (Gr 80)**. Barras apoyadas cada 14 in o menos. En el resto, estribos con gancho sísmico a ≤ d/2 |
| Geometría | — | — | ln ≥ 4d; bw ≥ el menor de 0.3h y 10 in; la viga no sobresale de la columna más que el menor de c2 y 0.75·c1 a cada lado |
| Empalmes | — | — | No en los nudos, no a menos de 2h de la cara ni de las rótulas, y con aros a ≤ el menor de d/4 y 4 in |

(La columna del ordinario corresponde a 18.3.2. Los aros a 2h de la cara son del intermedio, 18.4.2.4–5.)

## Diferencias o contradicciones encontradas

1. **Cambios del 318-19 que conviene no confundir con el 318-14:**
   - vigas controladas por tracción (antes εt ≥ 0.004);
   - Av,min desde Vu > φλ√f'c·bw·d (antes 0.5φVc);
   - Vc con ρw^(1/3) y factor de tamaño λs;
   - Ie de Bischoff;
   - factor ψg y ldh con db^1.5.
2. Diseñar vigas **requiere la etapa 2** (cargas en barras y diagramas). Hoy el programa solo da fuerzas en los extremos con cargas nodales.
3. En SMF el **cortante de diseño no sale del análisis**, sino de Mpr. Hay que calcular Mn y Mpr de la sección con el acero real.

## Para el programa (qué implementar y cómo verificarlo)

- **Flexión:** dado Mu, calcular As requerido (con As,min), revisar εt y φ, elegir barras y revisar la separación (25.2 y 24.3). Opcionalmente, acero en compresión y vigas T (ancho de ala de 6.3.2).
- **Cortante:** Vc según la Tabla 22.5.5.1, Vs, s requerido, y comparar con s máximo, Av,min y el límite de la sección. En SMF, Ve por Mpr.
- **Torsión:** Tth, Tcr, At/s, Aℓ y el límite combinado con cortante.
- **Servicio:** altura mínima (Tabla 9.3.1.1) o deflexión con Ie y λΔ.
- **Detallado:** ld y ldh (Tablas 25.4.2.3 y 25.4.2.5), corte de barras e integridad estructural.
- **Verificaciones:**
  - viga 30×50 con f'c = 4 ksi y fy = 60 ksi, calculada a mano: a, Mn y εt;
  - ejemplos de Wight & MacGregor 8.ª ed. o McCormac & Brown 11.ª ed. (ACI 318-19);
  - casos borde: Vu justo en φλ√f'c·bw·d y en Vs = 4√f'c·bw·d, para el cambio de s máximo.
