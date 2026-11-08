# Etapa 7: Sismo (cargas sísmicas, análisis, deriva y detallado sísmico)

**Qué cubre:**
- de los mapas a SDS y SD1, el espectro y la CDS;
- el sistema estructural (R, Ω0, Cd);
- el análisis (fuerza lateral equivalente o modal);
- la torsión, la deriva y P-Δ;
- qué capítulo del ACI 18 se aplica.

**Qué norma manda:**
- **REP 2021 cap. 5 (p. 28–32):** remite a ASCE/SEI 7-05, capítulos 11 a 23, con estas modificaciones:
  - **5.2.1, Cs mínimo:** Cs = 0.044·SDS·I ≥ 0.01. Es la Ec. 12.8-5 modificada. Para estructuras no edificio: ≥ 0.03 (Ec. 15.4-1) y ≥ 0.01 (Ec. 15.4-4).
  - **5.12, mapas propios (Anexo 3):** Ss y S1 para Sitio Clase B al 5 % de amortiguamiento, más el PGA para un periodo de retorno de 2500 años (hojas PGA-1 a PGA-36). La Gaceta solo trae las hojas 5, 6, 14 y 15 (p. 193–204); el juego completo está en la JTIA.
  - **5.13:** **TL = 10 s** en todo Panamá.
  - 5.10, sitio: cap. 20 de ASCE; 5.11, espectro de sitio: cap. 21; 5.9, interacción suelo-estructura: cap. 19 (con interacción cinemática de pilotes si hace falta).
  - 1.10 y Anexo 1: se permite el diseño por desempeño (REP DSBD 2021), que en concreto usa ACI 318-19 (Anexo 1, sección 6).
- **Concreto: ACI 318-19 cap. 18.** El REP 1.7 pide además el aseguramiento de calidad del Apéndice 11A de ASCE 7-05.

## Movimiento del suelo: ASCE 7-05 cap. 11 (p. 144–147)

1. **Ss y S1** se leen en los mapas del **REP** para el sitio (11.4.1). Los mapas 22-x de ASCE son de EE.UU. y no aplican.
2. **Clase de sitio** (11.4.2 y cap. 20). **Si no se conoce el suelo, se usa la clase D**, salvo que haya indicios de E o F.
3. **SMS = Fa·Ss y SM1 = Fv·S1** (Ec. 11.4-1 y 11.4-2). Fa y Fv vienen de las Tablas 11.4-1 y 11.4-2, interpolando:

   | Clase de sitio | Fa con Ss ≤ 0.25 / 0.5 / 0.75 / 1.0 / ≥ 1.25 | Fv con S1 ≤ 0.1 / 0.2 / 0.3 / 0.4 / ≥ 0.5 |
   |---|---|---|
   | A | 0.8 (todas) | 0.8 (todas) |
   | B | 1.0 (todas) | 1.0 (todas) |
   | C | 1.2 / 1.2 / 1.1 / 1.0 / 1.0 | 1.7 / 1.6 / 1.5 / 1.4 / 1.3 |
   | D | 1.6 / 1.4 / 1.2 / 1.1 / 1.0 | 2.4 / 2.0 / 1.8 / 1.6 / 1.5 |
   | E | 2.5 / 1.7 / 1.2 / 0.9 / 0.9 | 3.5 / 3.2 / 2.8 / 2.4 / 2.4 |
   | F | Espectro de sitio (11.4.7) | Espectro de sitio |

   Fv se confirmó en la imagen de la p. 144. Fa no salió en el recorte; son los valores estándar de ASCE 7-05 y conviene confirmarlos en la p. 144.
4. **SDS = (2/3)·SMS y SD1 = (2/3)·SM1** (Ec. 11.4-3 y 11.4-4).
5. **Espectro de diseño** (11.4.5), con T0 = 0.2·SD1/SDS y Ts = SD1/SDS:
   - Sa = SDS(0.4 + 0.6·T/T0) si T < T0;
   - Sa = SDS si T0 ≤ T ≤ Ts;
   - Sa = SD1/T si Ts < T ≤ TL;
   - Sa = SD1·TL/T² si T > TL.

   El espectro MCE es 1.5 veces el de diseño (11.4.6).
6. **Factor de importancia I** (Tabla 11.5-1, según la categoría de ocupación de la Tabla 1-1): 1.0 para I y II, **1.25 para III** y **1.5 para IV**.
7. **CDS**: se toma la más severa de las Tablas 11.6-1 (con SDS) y 11.6-2 (con SD1). Si **S1 ≥ 0.75**, la CDS es E (I a III) o F (IV).

   | | Ocupación I o II | III | IV |
   |---|---|---|---|
   | SDS < 0.167 / SD1 < 0.067 | A | A | A |
   | 0.167 ≤ SDS < 0.33 / 0.067 ≤ SD1 < 0.133 | B | B | C |
   | 0.33 ≤ SDS < 0.50 / 0.133 ≤ SD1 < 0.20 | C | C | D |
   | **SDS ≥ 0.50 / SD1 ≥ 0.20** | **D** | **D** | **D** |
8. **11.8:** en CDS C a F hace falta un **informe geotécnico**: estabilidad de taludes, licuación, asentamientos y fallas. En CDS D a F, además, los empujes sísmicos y la licuación con PGA = Ss/2.5 si no hay estudio de sitio.

## Sistema estructural, irregularidades y redundancia: ASCE 12.2 y 12.3 (p. 148–155)

- **Tabla 12.2-1 (p. 150, leída en la imagen):**

  | Sistema | R | Ω0 | Cd | Dónde se permite |
  |---|---|---|---|---|
  | **Pórtico especial de concreto (SMF)** | **8** | 3 | **5½** | Todas las CDS |
  | Pórtico intermedio de concreto (IMF) | 5 | 3 | 4½ | Solo B y C (no en D a F) |
  | Pórtico ordinario de concreto (OMF) | 3 | 3 | 2½ | Solo B |
  | Dual: SMF + muros especiales de concreto | 7 | 2½ | 5½ | Todas |
  | Dual: IMF + muros especiales de concreto | 6½ | 2½ | 5 | B y C; altura máxima 160 ft en D y 100 ft en E y F |
- **12.3.2, irregularidades:**
  - en planta (Tabla 12.3-1, p. 154): 1a torsional (δmax > 1.2·δprom), 1b torsional extrema (> 1.4·δprom), 2 esquina entrante, 3 diafragma, 4 fuera del plano, 5 sistemas no paralelos;
  - en elevación (Tabla 12.3-2): 1a piso blando (< 70 % del piso de arriba o < 80 % del promedio de los tres de arriba), 2 masa (> 150 %), 3 geometría, 4 discontinuidad en el plano, 5a/5b piso débil (< 80 % / < 65 %).
- **12.3.4, redundancia ρ:** 1.0 en CDS B y C y para deriva y P-Δ. En CDS D a F, **1.3**, salvo que se cumpla 12.3.4.2(a) o (b) (ver etapa 3).

## Análisis: ASCE 12.5 a 12.9 (p. 156–161)

- **12.5.3 y 12.5.4, direcciones:**
  - en CDS C con irregularidad tipo 5 y en CDS D a F: **100 % en una dirección + 30 % en la perpendicular**, o análisis con registros simultáneos;
  - en CDS D a F aplica a las columnas que pertenecen a dos sistemas y cuyo axial sísmico es ≥ 20 % de su resistencia axial.
- **Tabla 12.6-1, método permitido:**
  - en CDS D a F, la **fuerza lateral equivalente (FLE)** solo se permite en estructuras **regulares con T < 3.5·Ts**, en estructuras livianas, o en irregulares con T < 3.5·Ts que solo tengan ciertas irregularidades;
  - en los demás casos hace falta el **análisis modal espectral (12.9)**.
- **12.7.2, peso sísmico W:** muerta total, más:
  - ≥ 25 % de la viva en zonas de almacenamiento;
  - tabiques (reales o ≥ 10 psf = 0.48 kN/m²);
  - equipo permanente.

  En Panamá no hay nieve. Con el REP 2.1, los tabiques ya son carga muerta (0.75 kPa).
- **12.7.3, modelo:**
  - en 3D si hay irregularidades 1a, 1b, 4 o 5, con al menos 3 GDL dinámicos por nivel (dos traslaciones y un giro);
  - **(a) en concreto se usan secciones agrietadas**: conecta con la Tabla 6.6.3.1.1 del ACI, en la etapa 1.
- **12.8, fuerza lateral equivalente:**
  - **V = Cs·W** (12.8-1).
  - **Cs = SDS/(R/I)** (12.8-2), con dos topes: ≤ SD1/(T·(R/I)) si T ≤ TL, y ≤ SD1·TL/(T²·(R/I)) si T > TL.
  - Mínimos: **Cs ≥ 0.044·SDS·I ≥ 0.01** (REP 5.2.1); si **S1 ≥ 0.6**, además Cs ≥ 0.5·S1/(R/I).
  - **12.8.1.3:** en estructuras regulares de 5 pisos o menos con T ≤ 0.5 s se puede usar Ss = 1.5 para calcular Cs.
  - **12.8.2, periodo:** T ≤ Cu·Ta, con Cu de la Tabla 12.8-1 (1.4 si SD1 ≥ 0.4; 1.5 con 0.2; 1.6 con 0.15; 1.7 con ≤ 0.1). **Ta = Ct·hn^x**: en pórticos de concreto Ct = 0.016 (0.0466 en SI, hn en m) y x = 0.9. Alternativa: Ta = 0.1·N, para 12 pisos o menos con altura de piso ≥ 3 m.
  - **12.8.3:** Fx = Cvx·V, con Cvx = wx·hx^k/Σ(wi·hi^k). k = 1 si T ≤ 0.5 s, k = 2 si T ≥ 2.5 s, e interpolado entre ambos.
  - **12.8.4:** torsión inherente más **torsión accidental**: centro de masa desplazado ±**5 %** de la dimensión perpendicular. En CDS C a F con irregularidad 1a o 1b, se amplifica por **Ax = (δmax/(1.2·δprom))² ≤ 3.0**.
  - **12.8.6, deriva:** **δx = Cd·δxe/I**, en el centro de masa. Δ = δx − δx−1. Para la deriva se puede usar el T calculado sin el tope Cu·Ta (12.8.6.2).
  - **12.8.7, P-Δ:** **θ = Px·Δ/(Vx·hsx·Cd)**. En ASCE 7-05 la ecuación no incluye I. Si θ ≤ 0.10, se ignora. **θmax = 0.5/(β·Cd) ≤ 0.25**. Entre 0.10 y θmax, se multiplica por 1/(1 − θ). Por encima de θmax la estructura es inestable y se rediseña.
- **12.9, análisis modal:** modos suficientes para alcanzar **≥ 90 % de masa participativa** en cada dirección; combinación SRSS o CQC; si el cortante modal Vt < 0.85·V de la FLE, se escala (12.9.4; confirmar el alcance en el texto).

## Deriva admisible: ASCE 12.12 (p. 163)

**Tabla 12.12-1 (Δa), leída en la imagen:**

| Estructura | Ocupación I o II | III | IV |
|---|---|---|---|
| ≤ 4 pisos con tabiques, cielos y fachadas diseñados para la deriva (sin muros de mampostería) | 0.025·hsx | 0.020·hsx | 0.015·hsx |
| Muros de mampostería en voladizo | 0.010·hsx | 0.010·hsx | 0.010·hsx |
| Otros muros de mampostería | 0.007·hsx | 0.007·hsx | 0.007·hsx |
| **Todas las demás** | **0.020·hsx** | **0.015·hsx** | **0.010·hsx** |

- **12.12.1.1:** en pórticos de momento con CDS D a F, **Δ ≤ Δa/ρ**.
- **12.12.3:** separación entre edificios suficiente para el desplazamiento total δx.
- **12.12.4:** compatibilidad de deformaciones en CDS D a F (ver ACI 18.14).

## ACI 318-19 cap. 18 (p. 287–356): qué aplica según la CDS

| CDS | Qué cumplir (18.2.1) |
|---|---|
| A | El capítulo 18 no aplica |
| B | 18.2.2 (análisis), más pórtico ordinario (18.3) |
| C | 18.2.2, 18.2.3 y 18.13 (cimentaciones), más pórtico intermedio (18.4) |
| **D, E, F** | 18.2.2 a 18.2.8, 18.12 (diafragmas), 18.13 (cimentaciones), **18.14 (miembros que no son parte del sistema sísmico)**, más pórtico especial (18.6 a 18.8) |

- **Pórtico especial:**
  - **vigas (18.6)** y **columnas (18.7)**: ver etapas 5 y 4;
  - **nudos (18.8):**
    - profundidad del nudo ≥ el mayor de 20·db/λ (Gr 60), 26·db (Gr 80) y h/2 de la viga;
    - Vu del nudo con 1.25·fy en las barras de las vigas;
    - **Vn = 20 / 15 / 12·λ√f'c·Aj** según cuántas caras confinan las vigas, con columna continua (Tabla 18.8.4.3, p. 315; confirmar los valores con columna discontinua);
    - **φ = 0.85** en nudos (21.2.4.4);
    - gancho en el nudo: **ldh = fy·db/(65·λ√f'c)** ≥ el mayor de 8db y 6 in (18.8.5.1).
- **φ por cortante = 0.60** en miembros diseñados para E cuya Vn sea menor que el cortante asociado a su Mn (21.2.4.1). Por eso en SMF el cortante se diseña con Mpr.
- **Requisitos generales en CDS D:** f'c ≥ 3000 psi (Tabla 19.2.1.1); barras A706 o A615 Gr 60 que cumplan 20.2.2.5(b).

## Diferencias o contradicciones encontradas

1. **Hoja de ruta:** la deriva (antes etapa 4) es parte del sismo: necesita Cd, I y ρ, y las fuerzas de 12.8. Con viento hay otro criterio, el del REP 4.3 (etapa 8). **Ya se reordenó.**
2. **Inconsistencias dentro del REP:**
   - 5.7 y 5.8 citan una "sección 1.11 del REP-21" que **no existe** en el índice;
   - 5.5 cita el "5.2.1 del REP-14";
   - 5.12 dice "S1… para periodos cortos", cuando S1 es el periodo de 1 s.

   Son erratas, pero conviene saberlo antes de citar esas secciones.
3. **`combinacionescarga.py`** tiene `SDS = 0.5` y `rho = 1.3` fijos. Deberían salir de este cálculo: SDS a partir de Ss, clase de sitio y Fa; ρ según 12.3.4.
4. En la ciudad de Panamá, con Ss y S1 altos cerca de las fallas (hoja 14) y suelo D por defecto, lo esperable es **CDS D**. Eso obliga a pórtico especial (R = 8, Cd = 5.5) y al detallado de 18.6 a 18.8 en las etapas 4 y 5.

## Para el programa (qué implementar y cómo verificarlo)

- **Datos del sitio:** Ss, S1 (de los mapas del REP), clase de sitio, categoría de ocupación y TL = 10 s. Con eso: Fa, Fv, SMS, SM1, SDS, SD1, I, CDS, el espectro y su gráfico.
- **Sistema:** R, Ω0 y Cd según la Tabla 12.2-1, con validación de si está permitido para esa CDS.
- **Masas y peso W** por nivel, a partir de las cargas D (etapa 2) más el porcentaje de viva aplicable.
- **FLE:**
  - Ta, T del análisis y T ≤ Cu·Ta;
  - Cs con los topes y el mínimo del REP;
  - V, Fx y la torsión accidental (±5 %).
- **Modal (más adelante):** matriz de masas, eigenvalores con `scipy.linalg.eigh`, participación de masa ≥ 90 %, CQC y escalado.
- **Deriva y P-Δ:** δxe del análisis con secciones agrietadas → δx = Cd·δxe/I → Δ comparada con Δa/ρ. Luego θ y θmax.
- **Verificaciones:**
  - un ejemplo de **FEMA 451** (NEHRP Recommended Provisions: Design Examples, 2006), que usa ASCE 7-05;
  - un cálculo a mano de V para un edificio de 3 pisos;
  - continuidad del espectro en T0, Ts y TL.
