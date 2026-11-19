# Plan de estudio y verificaciones

Este plan acompaña al programa de análisis y diseño estructural. Cada etapa dice qué se agrega al programa, qué estudiar (normas, teoría y Python), cómo verificar y cuándo se considera terminada.

Las notas de normas, con cláusula y página, están en [`docs/normas/`](normas/indice.md).

**Normas que aplican en Panamá** (confirmado en el REP 2021):
- **REP 2021** manda;
- cargas, sismo y viento por **ASCE/SEI 7-05** con los cambios del REP;
- concreto por **ACI 318-19**.

## Estado actual (lo que ya hace el programa)

- **Análisis matricial de pórticos 3D** (`calculo/rigidez/`):
  - barras de 12 GDL;
  - transformación por ángulos α, β y γ;
  - ensamble de K y solución de K·U = F;
  - reacciones y fuerzas en los extremos de cada barra (ejes locales);
  - cargas en los nodos y en las barras (uniforme, puntual y momento), con sus fuerzas de empotramiento, y peso propio;
  - diagramas N, V, M y T y la deformada a lo largo de cada barra.
- **Casos de carga:** Peso propio (automático: A·γ de cada barra) y Carga muerta adicional, fijos, y los que agregue el usuario (Muerta, Viva, Viva de techo, Viento o Sismo). **Combinaciones**: las 13 de ASCE 7-05 ya cargadas (con Lr y su 0.5Lr de acompañamiento, sin la opción de 0.5L; SDS y ρ a mano), las propias, por tipo de caso, y la envolvente; solo para ver resultados (superposición).
- **Materiales y secciones de concreto** (`calculo/concreto.py`, `modelo/concreto.py`): E, G, A, I, J y γ, con su refuerzo.
- **Interfaz 3D** (`interfaz/`, PySide6 y PyVista): dibujo, explorador, propiedades, herramientas (nodo, elemento, asignar sección, apoyo y cargas) y tres estados: editar, resultados de un caso y resultados de una combinación (deformada, diagramas y reacciones en 3D, y lo mismo para una barra en el panel Diagrama, con un corte que se desliza: los desplazamientos en ejes globales, total o por componente, y las fuerzas internas en los ejes locales, que se dibujan sobre la barra seleccionada). Con la sección real, los nudos se rellenan con un bloque de concreto y el concreto se puede ver transparente, con el acero de columnas y vigas (esquemático).
- **Diagramas de interacción de columnas** (`calculo/interaccion/`): rectangular, circular y biaxial. Se ven desde Propiedades (Ver 2D y Ver 3D, y la pestaña Interacción de una columna) y con los scripts de `scripts/`. El 2D es el corte en la dirección del momento, con un deslizador; con resultados, los puntos Pu–Mu de las 13 combinaciones y un aviso si alguno queda fuera.
- **Losas de viguetas** (`modelo/losas.py`, `modelo/diseno_vigueta.py`, `calculo/diseno/viga.py`): paños entre vigas (también en L), franjas (sistemas de vigueta) con sus casos de viva, carga a las vigas por las reacciones de la vigueta, diseño de la vigueta (flexión, cortante, Ie y deflexiones) y la pestaña Comprobaciones, con la vigueta editable.
- **Comprobaciones automáticas** (`pruebas/verificacion.py`) e **integridad del cálculo** (`pruebas/integridad.py`).
- **Memoria de cálculo en Word** (`python -m scripts.memoria` → `docs/memoria/Memoria de cálculo.docx`): fórmulas con su cita y el código de las funciones clave. Por ahora, la matriz de rigidez y su transformación, los diagramas de interacción y la vigueta T. Faltan los demás temas que el programa ya calcula: ensamble y solución, fuerzas de empotramiento, diagramas N, V, M y T, propiedades del concreto, peso propio y combinaciones.
- Combinaciones predeterminadas en `modelo/combinaciones.py` (`scripts/combinaciones_asce7.py` las imprime).

## Hoja de ruta (orden acordado)

| # | Etapa | Depende de | Notas de normas |
|---|---|---|---|
| 1 | Materiales y secciones | — | [etapa1](normas/etapa1_materiales_secciones.md) |
| 2 | Cargas en barras y diagramas N, V, M y T | 1 | [etapa2](normas/etapa2_cargas_en_barras.md) |
| 3 | Combinaciones de carga | 2 | [etapa3](normas/etapa3_combinaciones.md) |
| 4 | Columnas: estribos (y cortante, esbeltez) | 1, 3 y los diagramas de interacción | [etapa4](normas/etapa4_columnas_estribos.md) |
| 5 | Vigas: acero longitudinal y estribos | 1, 2, 3 | [etapa5](normas/etapa5_vigas.md) |
| 6 | Losas: una y dos direcciones, viguetas, metal deck | 2, 5 | [etapa6](normas/etapa6_losas.md) |
| 7 | Sismo, con deriva | 1–3 (y 4–5 para el detallado especial) | [etapa7](normas/etapa7_sismo.md) |
| 8 | Viento, con deriva de servicio | 1–3 | [etapa8](normas/etapa8_viento.md) |

**Por qué se reordenó:**
- El diseño de estribos y vigas necesita fuerzas **mayoradas** (etapa 3) y **momentos en el tramo** (etapa 2), que el programa todavía no calcula.
- La **deriva** necesita cargas laterales y los factores Cd, I y ρ del sismo. Además hay dos criterios distintos: sismo (ASCE 12.12) y viento (REP 4.3).
- En la ciudad de Panamá lo usual es **CDS D**, que exige **pórtico especial** (ACI 18.6 a 18.8). Conviene diseñar estribos y vigas (etapas 4 y 5) con el tipo de pórtico como dato desde el principio, para no rehacerlos en la etapa 7.

---

## Etapa 1: Materiales y secciones

- **Objetivo:** materiales de concreto y acero con sus propiedades calculadas. Secciones rectangular, circular y T con A, Iy, Iz y J, más los modificadores de inercia del ACI según el tipo de miembro. Todo editable desde la interfaz.
- **Normas:**
  - ACI 19.2 (Ec, fr, f'c mínimo), 20.2 (Es, fy máximo);
  - 6.3.2 (ancho de ala de vigas T);
  - **Tabla 6.6.3.1.1** (0.70Ig en columnas, 0.35Ig en vigas; 0.5Ig para cargas laterales; ×1.4 para servicio);
  - 22.2 (bloque rectangular, β1).
- **Teoría:**
  - propiedades geométricas (Steiner);
  - constante de torsión de Saint-Venant para rectángulos;
  - qué es la rigidez agrietada y por qué cambia las fuerzas en estructuras hiperestáticas.
  - Libro: Wight y MacGregor, *Reinforced Concrete* (8.ª ed., ACI 318-19), caps. 2–3.
- **Python y POO:**
  - `dataclass` con validación en `__post_init__`;
  - `@property` para las propiedades calculadas;
  - `@classmethod` como constructores (`Material.concreto(fc_mpa)`);
  - unidades con `pint` en la entrada y la salida, y SI por dentro;
  - formularios en PySide6 (`QDialog`, `QFormLayout`, `QTableWidget`).
- **Verificaciones:**
  - Ec(4000 psi) = 3 605 000 psi;
  - β1 en 2500, 4000, 5000 y 8000 psi;
  - J de 30×50 = 2.82e-3 m⁴;
  - I agrietada de una viga = 0.35Ig, y comprobar que el análisis la usa.
- **Listo cuando:** se pueden crear, editar y borrar materiales y secciones desde la interfaz, el análisis usa las propiedades modificadas y hay pruebas automáticas para lo anterior.
- **Hecho (noviembre de 2026): inercia agrietada.**
  - `calculo/concreto.factor_inercia`: 0.70 en columnas y 0.35 en vigas, fijos (Tabla 6.6.3.1.1(a), confirmada en la imagen de la PDF p. 78).
  - `modelo/analisis.py` resuelve cada caso dos veces:
    - el de **resistencia**, con esos factores en las barras de concreto, da las fuerzas, las reacciones y los puntos Pu–Mu;
    - el de **Ig** da la deformada y los desplazamientos. Ig para la deformada es decisión del usuario, por ahora.
  - Verificado en `pruebas/verificacion.py`:
    - voladizo a mano (Δ/0.70 y el mismo momento);
    - pórtico igual a un modelo armado a mano con las inercias ya reducidas;
    - el momento de un pórtico hiperestático cambia (5.47 contra 7.30 kN·m en la base);
    - sin concreto, un solo análisis.
  - Falta: la rigidez de servicio (1.4×, para la deriva por viento) e Ie (etapa 5).

  Alcance, como se acordó:
  - la Tabla 6.6.3.1.1(a) (PDF p. 78) es para el análisis con **cargas mayoradas**, es decir, para obtener las fuerzas de diseño;
  - las deformaciones no salen de esa tabla:
    - las laterales inmediatas de servicio (la deriva por viento del REP 4.3) usan **1.4 × esas inercias, sin pasar de Ig** (§6.6.3.2.2, PDF p. 80);
    - la flecha de vigas por gravedad usa **Ie** (§24.2, etapa 5);
    - la deriva sísmica usa secciones agrietadas (ASCE 7-05 §12.7.3(a)) y luego δx = Cd·δxe/I (etapa 7);
  - por eso el programa necesitará dos rigideces, una de resistencia y otra de servicio. Hoy la segunda es Ig.

## Etapa 2: Cargas en barras y diagramas

- **Objetivo:**
  - cargas uniformes y puntuales en barras, además del peso propio;
  - fuerzas de empotramiento, cargas nodales equivalentes y fuerzas finales en los extremos;
  - diagramas N, V, M y T a lo largo de cada barra;
  - casos de carga separados (D, L, Lr…).
- **Normas:**
  - ASCE 7-05 cap. 3 y 4: Tabla 4-1, tabiques, carga parcial 4.6, reducción 4.8 y 4.9;
  - **REP 2.1: tabiques como carga muerta, 0.75 kPa**;
  - ACI 6.4 (alternancia de la viva), 6.5 (coeficientes, útiles para verificar) y 6.6.
- **Teoría:**
  - fuerzas de empotramiento en barras 3D;
  - superposición;
  - relación w → V → M (dV/dx = −w, dM/dx = V);
  - convención de signos en ejes locales.
  - Libros: Kassimali, *Matrix Analysis of Structures*, cap. de cargas en miembros; McGuire, Gallagher y Ziemian, *Matrix Structural Analysis* (2.ª ed., gratuito en línea).
- **Python:**
  - clases de carga (`CargaUniforme`, `CargaPuntual`) con un método común, que es un ejemplo de polimorfismo;
  - `numpy` vectorizado para evaluar los diagramas;
  - gráficos en PyVista o `matplotlib`.
- **Verificaciones:**
  - viga simple wL²/8;
  - biempotrada wL²/12 y wL²/24;
  - apoyada-empotrada wL²/8;
  - puntual PL/8;
  - equilibrio de cada barra;
  - viga continua contra la Tabla 6.5.2;
  - un pórtico comparado con **Ftool** (2D, gratuito) o **PyNite** (3D, Python).
- **Listo cuando:** los diagramas coinciden con los casos de libro y el equilibrio cierra en cada barra y en los apoyos.
- **Avance (noviembre de 2026):**
  - **hecho:**
    - cargas en nodos y en barras (uniforme en toda la barra, puntual y momento a una distancia a; en ejes globales o locales);
    - peso propio con γ = 150 lb/ft³ = 23.56 kN/m³ (ASCE 7-05 Tabla C3-2, PDF p. 295) y el caso Muerta;
    - FEF con las funciones de forma de Hermite;
    - diagramas N, V, M y T y la deformada, en 3D y en Propiedades.
  - **diseño:** una sola clase `CargaBarra` con un `tipo`, en vez de una clase por tipo. Las fórmulas tienen que vivir en `calculo/` (sagrado), que no conoce las clases del modelo; ahí se eligen por tipo.
  - **verificado** (con `verificar-calculos`, en un script aparte):
    - viga simple: wL²/8, wL/2 y 5wL⁴/384EI;
    - biempotrada: wL²/12 y wL²/24;
    - apoyada-empotrada: wL²/8;
    - puntual al centro: PL/8;
    - puntual y momento a una distancia a, contra la misma barra partida por un nodo en a (otro método; diferencia 5e-14, también en una barra inclinada con α = 30°);
    - equilibrio global de un pórtico con cargas en barras;
    - peso propio: ΣRz = ΣA·γ·L;
    - dMz/dx = Vy y dMy/dx = Vz;
    - la deformada en los extremos coincide con los desplazamientos de los nodos.

    Las vigas de referencia quedaron en `pruebas/integridad.py`.
  - **hecho** (noviembre de 2026): cargas parciales y trapezoidales (`calculo/rigidez/empotramiento.py` y `diagramas.py`, con Gauss exacto), contra la triangular biempotrada, la viga simple con triangular, 20 000 puntuales y la uniforme; la viva de las losas va al caso fijo Carga viva;
  - **falta:**
    - la viga continua contra la Tabla 6.5.2;
    - un pórtico comparado con Ftool o PyNite. Los casos de viva, viento y sismo ya se pueden definir y cargar a mano (noviembre de 2026).

## Etapa 3: Combinaciones de carga

- **Objetivo:**
  - generador de combinaciones de ASCE 7-05 2.3.2 y 12.4.2.3;
  - opción 0.5L con sus exclusiones;
  - ± para W y E en X e Y;
  - envolventes con la combinación que manda.
- **Normas:**
  - ASCE 2.3.2 y 12.4 (E = ρQE ± 0.2·SDS·D);
  - ACI 5.3 con **5.3.5 (1.6W)**;
  - REP 1.4.1 y 8.4.
- **Teoría:** estados límite, factores de carga y por qué el viento del REP va × 1.6.
- **Python:** diccionarios de factores; superposición lineal de resultados; `numpy.max` y `argmax` para las envolventes.
- **Verificaciones:**
  - con D = 10 y L = 5: la combinación 2 da 20;
  - con W de servicio = 10: la combinación 4 da 1.2D + 16;
  - con SDS = 0.5: 1.3D + ρQE + L y 0.8D + ρQE;
  - la envolvente coincide con el máximo calculado a mano.
- **Listo cuando:** `scripts/combinaciones_asce7.py` queda reemplazado por un módulo con pruebas, que incluye Lr y las dos direcciones. La opción de 0.5L **no** entra (decisión del usuario: no reducir cargas); el 0.5Lr de las combinaciones 2 y 4 sí, porque es el factor de acompañamiento que exige §2.3.2 y no una reducción.
- **Avance (noviembre de 2026), una parte:**
  - **hecho:**
    - el peso propio en su propio caso, automático, y la carga muerta adicional aparte: la muerta total (D) es su suma;
    - casos que agrega el usuario (Definir → Casos de carga), de tipo Muerta (D), Viva (L), Viva de techo (Lr), Viento (W) o Sismo (E);
    - las 13 combinaciones de ASCE 7-05 §2.3.2 y §12.4.2.3 para D, L, Lr, W y E (Lr agregada en noviembre de 2026; L siempre completa, sin la opción de 0.5L), ya cargadas (`modelo/combinaciones.py`), con SDS y ρ como datos del modelo (por ahora escritos a mano) y los dos signos de W y E;
    - combinaciones propias, con un factor por tipo de caso (Definir → Combinaciones de carga) y nombre automático ("1.2D + 1.6L");
    - resultados por **superposición** (`modelo/analisis.combinar`), sin volver a resolver;
    - tres estados en la interfaz: editar, resultados de un caso y resultados de una combinación (Σ); con resultados a la vista no se edita;
    - archivo `.json` versión 4 (combinaciones propias por tipo, SDS y ρ); los anteriores abren con la misma muerta total.
  - **verificado** (con `verificar-calculos`, y en `pruebas/verificacion.py`):
    - combinaciones leídas en la norma: las siete de §2.3.2 en la imagen de la página (PDF p. 34) y las sísmicas de §12.4.2.3 en el texto (PDF p. 156); 1.6W en REP §8.4 (PDF p. 101);
    - con SDS = 0.5 y ρ = 1.3: la 5 da 1.3D + 1.3E + L y la 7, 0.8D + 1.3E;
    - 1.2D + 1.6L y 1.2D − 1.6W + L por superposición (el factor de D en los dos casos tipo D) = un análisis con todas las cargas multiplicadas (U, R y diagramas de todas las barras);
    - peso propio: ΣRz = ΣA·γ·L; y Carga muerta (D) = peso propio + carga muerta adicional;
    - viga simple con D = 10 y L = 5 kN/m y un viento de 10 kN al centro: 1.2D + 1.6L da wL²/8 = 90 kN·m y wL/2 = 60 kN; 1.4D, 63 kN·m y 42 kN; 1.2D + 1.6W + L, 100.5 kN·m y 59 kN.
  - **hecho después (noviembre de 2026):** Lr (viva de techo) con el 0.5Lr de la 2 y la 4 y la 3 completa (1.2D + 1.6Lr + L y ±0.8W), verificado a mano en una viga simple. La opción de 0.5L **no se usa**, por decisión del usuario (no reducir cargas).
  - **envolventes (noviembre de 2026):** opción "Envolvente" en la lista Combinación: máximo y mínimo de N, V, M y T entre las 13 de la norma, con la combinación que da cada uno; sin deformada ni reacciones. Verificado en la viga simple: máx al centro 109.5 kN·m (1.2D + 1.6W + L + 0.5Lr) y mín 16.5 kN·m (0.9D − 1.6W), a mano; y ninguna combinación se sale de la envolvente en ningún punto.
  - **falta:** R y S (no aplican en Panamá); W y E en X y en Y, con la torsión accidental; SDS y ρ calculados (etapa 7) en vez de escritos a mano; Ev = 0 si SDS ≤ 0.125; el uso de la envolvente en el diseño (etapas 4 y 5). Y decidir si las combinaciones pasan a `calculo/` cuando se usen para diseñar.
  - **Ojo en el diseño de columnas:** la envolvente junta el máximo de P y el de M por separado, que pueden salir de combinaciones distintas, así que ese par no existe. Una columna se revisa con el par (Pu, Mu) simultáneo de cada combinación (ACI 318-19 §10.4.2.1, PDF p. 158), como ya hace la pestaña Interacción. En vigas, la envolvente de M y V sí sirve.

## Etapa 4: Columnas (estribos, cortante, esbeltez)

- **Objetivo:**
  - verificar estribos: separación, diámetro, barras apoyadas cada 6 in, posición del primero y del último, y zona confinada;
  - verificar el cortante: Vc con Nu, Vs e interacción biaxial;
  - esbeltez por magnificación de momentos;
  - integrar los **diagramas de interacción** que ya existen como módulo del programa.
- **Normas:**
  - ACI 10, 25.7.2–25.7.4, 22.4, 22.5, 21.2 y 6.6.4;
  - **ACI 18.4.3 (IMF) y 18.7 (SMF)**: lo, so, Ash y Ve por Mpr.
- **Teoría:**
  - confinamiento del concreto;
  - por qué el cortante sísmico sale de Mpr (diseño por capacidad);
  - efectos P-δ.
  - Libros: Wight y MacGregor, caps. 11–12 y 19; *NEHRP Seismic Design Technical Brief No. 1* (pórticos especiales de concreto, NIST).
- **Python:**
  - ya hecho: las fórmulas están en `calculo/interaccion/` (funciones puras, con referencias en la integridad) y las ventanas aparte (`scripts/` e `interfaz/ventanas/interaccion.py`);
  - falta un paquete de diseño (`diseno/`) que las use, con pruebas.
- **Verificaciones:**
  - ejemplo resuelto de un libro con ACI 318-19 (diagrama y estribos);
  - casos borde: Pu = 0.3·Ag·f'c y el paso de barra #10 a #11 (cambio de diámetro mínimo del estribo);
  - diagrama de interacción contra **spColumn** o un ejemplo publicado.
- ~~**Corregir antes** (hallazgos)~~: corregidos en noviembre de 2026 (β1 con 2.5 ksi, barras #14 y #18, fy como dato, la circular con aros y aviso de cuantía con el tipo de pórtico). Ver "Hallazgos".
- **Listo cuando:** dada una columna y sus fuerzas, el programa dice qué cumple, qué no, y por qué (con la cláusula).

## Etapa 5: Vigas (acero longitudinal y estribos)

- **Objetivo:**
  - As requerido y su verificación (As,min, εt, separaciones);
  - estribos por cortante, y por torsión si aplica;
  - deflexiones (Ie, λΔ) y fisuración;
  - longitudes de desarrollo;
  - requisitos de 18.6 si el pórtico es especial.
- **Normas:** ACI 9, 22.2–22.3, 22.5, 22.7, 24, 25 y 18.6.

  Ojo con los **cambios del 318-19**:
  - viga controlada por tracción;
  - Av,min desde φλ√f'c·bw·d;
  - Vc con ρw^(1/3);
  - nueva fórmula de Ie;
  - factor ψg.
- **Teoría:** flexión (bloque de Whitney), cortante (mecanismo de bielas), torsión (tubo de pared delgada), deflexiones a largo plazo.
- **Python:** algoritmos de elección de barras (búsqueda en una tabla de barras) y reportes de memoria de cálculo.
- **Verificaciones:**
  - viga 30×50 calculada a mano;
  - ejemplos de McCormac y Brown (11.ª ed.) o de Wight;
  - casos borde en los límites de s máximo.
- **Listo cuando:** diseña y verifica una viga continua del modelo con las fuerzas de las etapas 2 y 3.

## Etapa 6: Losas

- **Objetivo:**
  - losa en una dirección;
  - losa en dos direcciones: espesor mínimo, punzonamiento y método de análisis;
  - viguetas (nervadas);
  - metal deck;
  - reparto de la carga de losa a las vigas.
- **Normas:**
  - ACI 7, 8, 9.8, 8.8 y 22.6;
  - **DDM y EFM no están en el ACI 318-19**: hace falta el ACI 318-14 o un libro;
  - metal deck compuesto: **ANSI/SDI C**, AISI S100-2013 y AISC 360-10, que **no están en `docs/codigos/`**.
- **Teoría:** líneas de fluencia (opcional), método directo, áreas tributarias, comportamiento compuesto.
- **Verificaciones:**
  - h mínimo para ℓ = 4 m (143 mm con ambos extremos continuos);
  - punzonamiento de una columna interior;
  - límites de nervios (4 in, 3.5×, 30 in);
  - tablas del fabricante del metal deck.
- **Avance (noviembre de 2026, adelantada a pedido del usuario):** las **viguetas** en lo principal (ver "Noviembre de 2026: losas de viguetas", al final). Faltan la losa maciza en una y dos direcciones, el punzonamiento, el metal deck y el refuerzo de temperatura de la losa de las viguetas.
- **Preguntas abiertas:** ver al final.

## Etapa 7: Sismo (con deriva)

- **Objetivo:**
  - datos de sitio → espectro y CDS;
  - sistema (R, Ω0, Cd);
  - masas y W;
  - fuerza lateral equivalente (V, Fx, torsión accidental);
  - deriva (δx = Cd·δxe/I contra Δa/ρ) y P-Δ;
  - más adelante, análisis modal.
- **Normas:**
  - ASCE 7-05 cap. 11 y 12;
  - **REP 5**: Cs ≥ 0.044·SDS·I ≥ 0.01, mapas del Anexo 3 y TL = 10 s;
  - ACI 18 (qué aplica según la CDS).
- **Teoría:** dinámica de un grado de libertad y de varios, espectros de respuesta, ductilidad y factor R, irregularidades.
  - Libros: Chopra, *Dynamics of Structures*; **FEMA 451** (ejemplos de diseño con ASCE 7-05).
- **Python:** matriz de masas; `scipy.linalg.eigh(K, M)` para modos y periodos; CQC.
- **Verificaciones:**
  - un ejemplo de FEMA 451;
  - continuidad del espectro;
  - T del análisis contra Cu·Ta;
  - suma de las Fx = V;
  - deriva de un pórtico simple contra un cálculo a mano.
- **Listo cuando:** de los datos del sitio salen los casos E±x y E±y, con torsión, que entran a las combinaciones, y la deriva queda verificada.

## Etapa 8: Viento (con deriva de servicio)

- **Objetivo:**
  - presiones y fuerzas por nivel del SPRV (procedimiento analítico) en X e Y, con los 4 casos de la Fig. 6-9;
  - verificación de H/400, h/300 y 0.2 m/s².
- **Normas:**
  - ASCE 7-05 cap. 6;
  - **REP 4**: Tabla 4.1, 50 años para cargas y 10 para aceleraciones, viento de servicio;
  - ACI 6.6.3.2.2 (rigidez de servicio).
- **Teoría:** perfil de velocidad, factor de ráfaga, presiones interna y externa.
  - Libro: Mehta y Coulbourne, *Guide to the Wind Load Provisions of ASCE 7-05*.
- **Verificaciones:**
  - qz a mano (z = 10 m, exposición C, V = 34.7 m/s → ≈ 627 N/m²);
  - un ejemplo de la guía de Mehta;
  - el mínimo de 0.48 kN/m².
- **Listo cuando:** salen los casos W±x y W±y con torsión y la deriva de servicio está verificada.

---

## Verificaciones del programa (lo que exige el REP 1.8)

El **REP 1.8.2** (p. 20–21) pide:
- usar solo programas cuyo funcionamiento y limitaciones se conozcan;
- basarse en programas cuya validez esté verificada;
- documentar los métodos y las limitaciones;
- **verificar los resultados con programas independientes o con métodos aproximados**.

El **REP 1.8.3** pide que la memoria incluya cálculos a mano y los datos de entrada y salida.

**Ya existen** (`python -m pruebas.verificacion`):
- K simétrica;
- traslación rígida en X, Y y Z sin fuerzas;
- equilibrio global de fuerzas y momentos;
- voladizo con P·L³/(3EI), reacción y momento;
- detección de estructura inestable;
- integridad del cálculo: huellas de `calculo/` y resultados de referencia (pórtico, vigas con cargas en la barra y diagramas de interacción).

**Hechas una vez a mano (noviembre de 2026)**, al escribir la memoria de cálculo. Salieron de ella por pedido del usuario: la memoria queda solo con fórmulas y código. Conviene pasarlas a `pruebas/verificacion.py`:
- los 144 términos de la matriz local contra `k_local`, y sus coeficientes a mano (EA/L, GJ/L, 12EI/L³…);
- ángulos y rotación de una barra inclinada con α = 30°: L, γ, β, R ortogonal y det R = 1; ejes locales de una viga en X, una en Y y una columna;
- cuerpo rígido de **una barra** en ejes globales: tres traslaciones y **tres giros** (K·u = 0);
- voladizo acostado y de pie: P·L³/3EI y P·L²/2EI;
- diagrama de interacción de la columna del ejemplo: propiedades, Po y su techo de diseño, el punto balanceado fila por fila, el punto en que φ llega a 0.90 y la biaxial con θ = 90° igual a la de un eje; columna circular con a = R (medio círculo), Po y su techo.

**Propuestas:**
1. **Rotación rígida:** u = θ × r en todos los nodos, con φ = θ → K·u = 0. Completa la prueba de cuerpo rígido. (Comprobada a mano para una barra; falta para la K ensamblada de un pórtico, en `pruebas/verificacion.py`.)
2. **Pórtico plano** contra un ejemplo de libro y contra Ftool.
3. **Pórtico 3D** contra **PyNite** (Python, gratuito), comparando desplazamientos y reacciones.
4. **Casos con solución cerrada** de cada etapa (los listados arriba).
5. **Diagramas de interacción** contra un ejemplo publicado.
6. **Unidades:** la misma estructura en m y kN y en mm y N debe dar resultados equivalentes.
7. Mantener una **tabla de limitaciones** del programa en `CLAUDE.md`, como pide el REP 1.8.2.

## Hallazgos de la revisión

1. **Unidades mezcladas:** el análisis trabaja en kN y m; los diagramas en pulgadas y ksi, con salida en tonf. Se sugiere SI por dentro y `pint` en la entrada y la salida.
2. ~~**`requirements.txt`** no incluye `pint` ni `matplotlib`~~. Resuelto: ya los incluye.
3. ~~**`beta1`:** rechaza f'c = 2.5 ksi~~. Resuelto (noviembre de 2026): acepta 2.5 ksi (Tabla 22.2.2.4.3, PDF p. 401).
4. ~~**Barras #14 y #18**~~. Resuelto (noviembre de 2026): 1.693 y 2.257 in (Apéndice B, PDF p. 583).
5. ~~**Columna circular**~~. Resuelto (noviembre de 2026): siempre con aros, φ = 0.65 y 0.65 + 0.25(εt − εty)/0.003 (ACI 318-19 Tabla 21.2.2 (b) y (d), PDF p. 395) y Pn,max = 0.80·Po (Tabla 22.4.2.1 (a), PDF p. 402). La espiral (0.75 y 0.85·Po) se quitó a pedido del usuario: con una columna con espiral queda del lado seguro.
6. ~~**Cuantía máxima de 8 %**~~. Resuelto (noviembre de 2026): aviso de 1–8 % (§10.6.1.1) o 1–6 % con la casilla Pórtico especial (§18.7.4.1); solo avisa, no impide.
7. **Combinaciones:**
   - ~~les falta Lr~~: resuelto (noviembre de 2026), con el 0.5Lr de acompañamiento de la 2 y la 4, que exige §2.3.2;
   - la opción 0.5L no se usa: no es un error, es una decisión del usuario (no reducir cargas);
   - ~~SDS y ρ están fijos en el código~~: ya son datos del modelo, escritos a mano en Definir → Combinaciones; falta que salgan de la etapa de sismo;
   - no consideran X e Y ni la torsión accidental.
8. **Análisis:**
   - ~~solo cargas nodales~~: ya hay cargas en barras y peso propio; ~~faltan las parciales y trapezoidales~~: hechas (noviembre de 2026);
   - ~~los estribos de la vigueta usaban el fy de la sección sin tope~~: resuelto (noviembre de 2026): fyt sale del acero de los estribos y en cortante se toma como máximo 60 ksi (Tabla 20.2.2.4(a), PDF p. 378);
   - sin liberaciones (articulaciones) en los extremos de barra;
   - sin brazos rígidos;
   - ~~sin modificadores de inercia agrietada~~: hechos en el análisis de resistencia (ver la etapa 1); la deformada sigue con Ig;
   - la detección de inestabilidad usa cond(K) > 1e12, que depende de las unidades.
9. **Inconsistencias del propio REP 2021:**
   - 5.7 y 5.8 citan una sección 1.11 que no existe;
   - 5.5 cita el REP-14;
   - 5.12 llama a S1 de "periodos cortos";
   - 8.3 cita los capítulos 3 y 5 del ACI 318-19 (en esa edición corresponde a los caps. 19, 20 y 26);
   - 8.5 dice "anexo 2" para desempeño, cuando es el Anexo 1.
10. **Diferencia REP–ASCE en tabiques:** el REP los trata como carga muerta (0.75 kPa si L < 4 kPa); ASCE como viva (0.72 kPa si L ≤ 3.83 kPa). Manda el REP.
11. ~~**`fy` según la barra**~~. Resuelto (noviembre de 2026): fy es un dato de la sección (`Concreto.fy`, 60 ksi por defecto), que se escribe en el formulario de la sección.
12. **Área de la barra:** se calcula como π·db²/4 y no con el área nominal del ACI 318-19, Apéndice B (PDF p. 583). La diferencia es menor de 1 % (#6: 0.4418 contra 0.44 in²).
13. ~~**Dirección por defecto del diagrama 2D**~~. Resuelto (noviembre de 2026): el 2D abre en 90°, flexión hacia h, como la flexión "de un eje" de `rectangular.py`. La dirección es la del momento y el deslizador la muestra al lado ("90°").

## Preguntas abiertas

1. **Unidades del programa:** ¿todo en SI (kN, m, MPa) por dentro, con conversión solo en la entrada y la salida?
2. ~~**Viguetas:** ¿losas nervadas coladas en sitio o viguetas pretensadas prefabricadas?~~ Respondida (noviembre de 2026): nervadas coladas en sitio, en una dirección (ACI 318-19 §9.8), las de la tarea del usuario.
3. **Metal deck:** ¿losa compuesta o la lámina solo como encofrado? ¿Las vigas de apoyo son de acero (AISC 360-10)? Hacen falta SDI C, AISI S100 y AISC 360 en `docs/codigos/`.
4. **Sistema estructural objetivo:** ¿solo pórticos especiales de concreto, o también muros y sistemas duales?
5. **Análisis sísmico:** ¿basta con la FLE al principio, o se quiere el modal desde el inicio?
6. **Cimentaciones:** no están en la hoja de ruta. ¿Se agregan después (ACI 13 y REP 6)?

### Noviembre de 2026: diagrama de interacción y puntos Pu–Mu

- **Corregido (error del cambio de fy como dato):** εy = fy/Es no reducía unidades; con fy en kN/m² (como lo manda la interfaz) daba 14.27 en vez de 0.00207 y el diagrama quedaba inservible. Ahora `.to("dimensionless")`, con prueba por el camino de la interfaz y una referencia de integridad en kN/m².
- **Hecho (etapa 4, primer paso):** puntos Pu–Mu de la columna en la pestaña Interacción, con resultados a la vista: las combinaciones aplicables (`modelo/combinaciones.aplicables`), los dos extremos (`modelo/analisis.demandas_columna`), tabla, 2D en la dirección del momento del punto elegido (`calculo/interaccion/biaxial.curva_direccion`, verificada contra un barrido denso de θ: < 0.4 %) y 3D en VTK. ACI 318-19 §10.4.2.1 (PDF p. 158) y §6.6.4.5.3 (PDF p. 82).
- **Falta:** relación demanda/capacidad y esbeltez (δ, Cm, M2,mín).
- ~~**Hallazgo: el 2D con θ intermedio**~~. Resuelto (noviembre de 2026). El diagrama 2D con θ intermedio (`biaxial.curva`) graficaba la componente del momento sobre θ, con el eje neutro perpendicular a θ; no es la resistencia para un momento resultante en esa dirección. A igual φPn, contra el corte real: 40×40, hasta 2 %; 30×60, hasta +46 % (a 45°, +34 a +40 %); 25×80, hasta +87 %, del lado inseguro. Ahora el 2D es siempre el corte en la dirección del momento (`curva_direccion`), elegida con un deslizador de 0° a 90° que abre en 90°; `calculo/` no cambió. La prueba "30x60 a 45°" de la verificación lo deja escrito.
- **Hecho (noviembre de 2026):**
  - los puntos Pu–Mu salen de las **13 combinaciones**, aunque falte una carga, que vale cero (decisión del usuario; también 1.2D ± 0.8W sin Lr);
  - un **aviso en rojo**, en 2D y en 3D, dice qué puntos quedan fuera del diagrama de diseño. Cada uno se revisa contra la curva de su dirección (a 1°) con `modelo/interaccion.dentro_del_diagrama`. Como φPn nunca baja a lo largo de la curva (comprobado en varias secciones y direcciones), un punto está dentro si Pu está entre la tracción y el techo y Mu ≤ φMn a esa altura;
  - el aviso es para la pantalla; la relación demanda/capacidad del diseño sigue pendiente (etapa 4).

### Noviembre de 2026: losas de viguetas

- **Hecho:**
  - `calculo/diseno/viga.py` (sagrado, autorizado): flexión de la T (también con el bloque en el alma), As,min, As requerido, Mcr, Icr, Ie, λΔ, Vc de la Tabla 22.5.5.1 con λs, Av,min, Vs, ancho efectivo, límites de §9.8, h mínima y wu·ℓn²/24. Reproduce **todos** los números de la hoja de SMath del usuario (yb, Ig, fr, Mcr, d, c, εt, φMn+ y φMn−, Icr e Ie);
  - la sección T con acero arriba, recubrimiento y estribos (archivo v6);
  - las losas (archivo v7): paños entre vigas, franjas, casos de viva automáticos y propios, carga a las vigas (comprobado: lo que llega a las vigas es q × área en cada caso), sistemas de vigueta en la lista Sistema, diseño con las envolventes de todas las franjas y la pestaña Comprobaciones;
  - Medir (con snap a vértices, puntos medios y la perpendicular), la lista Combinación en dos columnas con la envolvente de servicio, el panel Diagrama abierto al iniciar y la transparencia sin saltos (depth peeling).
- **Hallazgos de la hoja de SMath** (se corrigen en el programa; la hoja es del usuario y no se toca):
  1. **Ma es por nivel de carga** (Tabla 24.2.3.5, p. 459): un Ie con Ma(D) para Δ(D) y otro con Ma(D + L) para Δ(D + L). Con un solo Ma, el mayor, ΔL = Δ(D+L) − Δ(D) sale menor que la del ACI.
  2. **ℓ/480, no ℓ/240**, si la losa sostiene tabiques que se dañan (Tabla 24.2.2, p. 458); la hoja tiene 300 kgf/m² de paredes. Y falta el ℓ/360 de la viva inmediata, y la ΔL en la suma de lo diferido.
  3. **Tabla 9.3.1.1** (p. 130–131): usa ℓ, no ℓn, y solo exime de calcular la deflexión si la viga no sostiene elementos que se dañen.
  4. **Faltaba**: la sección **controlada por tracción** (§9.3.3.1, p. 132) y el **cortante**. Sin estribos, Vc es la ecuación (c) de la Tabla 22.5.5.1 (p. 406), con λs y ρw^(1/3): en la vigueta de la tarea da unas 0.58 veces el 2√f'c·bw·d. Con estribos que cumplan Av,min vale la (a) más Vs. En viguetas, Av,min no hace falta si Vu ≤ φVc (Tabla 9.6.3.1, p. 138).
  5. **Vu en la cara**, no a d: la vigueta llega al costado de la viga (figura R9.4.3.2(e), p. 134).
  6. **Apoyo exterior**: el modelo con apoyos simples da M− = 0, pero una vigueta monolítica con su viga de borde tiene wu·ℓn²/24 (Tabla 6.5.2, p. 76): se revisa como recomendada.
  7. **Peso propio**: h_eq = A/bf solo vale si bf = s; con bf < s, la losa entre alas también pesa.
- **Con el ejemplo de la tarea** (`ejemplos/losa_viguetas.py`, 15 viguetas en el salón: s = 48.7 cm): Mu+ = 42.64, Mu− = 56.76 kN·m y Vu = 41.90 kN, todos en el pasillo (franja B); la flexión cumple con 1 #6 abajo y 2 #5 arriba. Con ψ = 0.5 la deflexión diferida no cumple ℓ/480 en los claros extremos (31.7 mm contra 15.7 mm en el pasillo).
- **Falta:** el refuerzo de temperatura de la losa (§9.8.1.7 y 24.4), la vigueta de borde sin viga lateral como L, el corte de barras diseñado, la redistribución (§6.6.5) y los patrones de viva de las vigas del 3D (etapa 5).

### Noviembre de 2026: el acero estructural salió del programa

- Las secciones de acero (tubo circular y perfil I) y el marco de Ftool de una tarea de la universidad se agregaron y luego **se quitaron** a pedido del usuario: el programa es solo de concreto armado.
- Quedaron en una copia aparte con su historial: `C:\Users\luisa\OneDrive\Desktop\utp`.
- Un archivo viejo con acero se abre con esas secciones y materiales en "Otros", con las mismas propiedades. Comprobado: el marco guardado desde `utp` da la misma suma de reacciones.
- Con el marco se fue su prueba contra un pórtico plano independiente (`_portico_2d`). Una igual con un pórtico de concreto sigue en las propuestas de verificación (punto 2).
