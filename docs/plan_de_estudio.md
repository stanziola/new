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
- **Casos de carga:** Peso propio (automático: A·γ de cada barra) y Carga muerta adicional, fijos, y los que agregue el usuario (Muerta, Viva, Viento o Sismo). **Combinaciones**: las 12 de ASCE 7-05 ya cargadas (con SDS y ρ a mano) y las propias, por tipo de caso; solo para ver resultados (superposición).
- **Materiales y secciones de concreto** (`calculo/concreto.py`, `modelo/concreto.py`): E, G, A, I, J y γ, con su refuerzo.
- **Interfaz 3D** (`interfaz/`, PySide6 y PyVista): dibujo, explorador, propiedades, herramientas (nodo, elemento, asignar sección, apoyo y cargas) y tres estados: editar, resultados de un caso y resultados de una combinación (deformada, diagramas y reacciones en 3D, y lo mismo para una barra en el panel Diagrama, con un corte que se desliza: los desplazamientos en ejes globales, total o por componente, y las fuerzas internas en los ejes locales, que se dibujan sobre la barra seleccionada). Con la sección real, los nudos se rellenan con un bloque de concreto y el concreto se puede ver transparente, con el acero de columnas y vigas (esquemático).
- **Diagramas de interacción de columnas** (`calculo/interaccion/`): rectangular, circular y biaxial. Se ven desde Propiedades (Ver 2D y Ver 3D, y la pestaña Interacción de una columna) y con los scripts de `scripts/`.
- **Comprobaciones automáticas** (`pruebas/verificacion.py`) e **integridad del cálculo** (`pruebas/integridad.py`).
- **Memoria de cálculo en Word** (`python -m scripts.memoria` → `docs/memoria/Memoria de cálculo.docx`): fórmulas con su cita y el código de las funciones clave. Por ahora, la matriz de rigidez y su transformación y los diagramas de interacción. Faltan los demás temas que el programa ya calcula: ensamble y solución, fuerzas de empotramiento, diagramas N, V, M y T, propiedades del concreto, peso propio y combinaciones.
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
  - **falta:**
    - cargas parciales y trapezoidales;
    - la viga continua contra la Tabla 6.5.2;
    - un pórtico comparado con Ftool o PyNite;
    - la viva de las losas (cargas de área, etapa 6). Los casos de viva, viento y sismo ya se pueden definir y cargar a mano (noviembre de 2026).

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
- **Listo cuando:** `scripts/combinaciones_asce7.py` queda reemplazado por un módulo con pruebas, que incluye Lr, 0.5L y las dos direcciones.
- **Avance (noviembre de 2026), una parte:**
  - **hecho:**
    - el peso propio en su propio caso, automático, y la carga muerta adicional aparte: la muerta total (D) es su suma;
    - casos que agrega el usuario (Definir → Casos de carga), de tipo Muerta (D), Viva (L), Viento (W) o Sismo (E);
    - las 12 combinaciones de ASCE 7-05 §2.3.2 y §12.4.2.3 para D, L, W y E, ya cargadas (`modelo/combinaciones.py`), con SDS y ρ como datos del modelo (por ahora escritos a mano) y los dos signos de W y E;
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
  - **falta:** Lr y R (el 0.5Lr de la 2 y la 4 y el 1.6Lr de la 3) y "1.2D + L" de la 3; la opción de 0.5L; W y E en X y en Y, con la torsión accidental; SDS y ρ calculados (etapa 7) en vez de escritos a mano; Ev = 0 si SDS ≤ 0.125; las envolventes y su uso en el diseño. Y decidir si las combinaciones pasan a `calculo/` cuando se usen para diseñar.

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
- ~~**Corregir antes** (hallazgos)~~: corregidos en noviembre de 2026 (β1 con 2.5 ksi, barras #14 y #18, fy como dato, aros o espiral en la circular y aviso de cuantía con el tipo de pórtico). Ver "Hallazgos".
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
5. ~~**Columna circular:** usa φ y 0.80·Po de columna con estribos~~. Resuelto (noviembre de 2026): usa los valores de espiral, φ = 0.75 y 0.75 + 0.15(εt − εty)/0.003 (ACI 318-19 Tabla 21.2.2 (a) y (c), PDF p. 395) y Pn,max = 0.85·Po (Tabla 22.4.2.1 (b), PDF p. 402). Después (noviembre de 2026) se puede elegir: `Concreto.confinamiento` = "aros" (por defecto: 0.65 y 0.80·Po) o "espiral". Falta elegirlo en la interfaz cuando se definan circulares.
6. ~~**Cuantía máxima de 8 %**~~. Resuelto (noviembre de 2026): aviso de 1–8 % (§10.6.1.1) o 1–6 % con la casilla Pórtico especial (§18.7.4.1); solo avisa, no impide.
7. **Combinaciones:**
   - les falta Lr;
   - no aplican la opción 0.5L;
   - ~~SDS y ρ están fijos en el código~~: ya son datos del modelo, escritos a mano en Definir → Combinaciones; falta que salgan de la etapa de sismo;
   - no consideran X e Y ni la torsión accidental.
8. **Análisis:**
   - ~~solo cargas nodales~~: ya hay cargas en barras y peso propio; faltan las parciales y trapezoidales;
   - sin liberaciones (articulaciones) en los extremos de barra;
   - sin brazos rígidos;
   - sin modificadores de inercia agrietada;
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
13. **Dirección por defecto del diagrama 2D** (interfaz): θ = 0° es compresión hacia +b, es decir, flexión en la dirección de b. La flexión "de un eje" de `rectangular.py` (en la dirección de h) corresponde a θ = 90°. En una sección cuadrada da igual; en una rectangular conviene decidir cuál se muestra primero y decirlo en la pantalla.

## Preguntas abiertas

1. **Unidades del programa:** ¿todo en SI (kN, m, MPa) por dentro, con conversión solo en la entrada y la salida?
2. **Viguetas:** ¿se trata de losas nervadas coladas en sitio o de viguetas pretensadas prefabricadas con bloques (sistemas de fabricante)?
3. **Metal deck:** ¿losa compuesta o la lámina solo como encofrado? ¿Las vigas de apoyo son de acero (AISC 360-10)? Hacen falta SDI C, AISI S100 y AISC 360 en `docs/codigos/`.
4. **Sistema estructural objetivo:** ¿solo pórticos especiales de concreto, o también muros y sistemas duales?
5. **Análisis sísmico:** ¿basta con la FLE al principio, o se quiere el modal desde el inicio?
6. **Cimentaciones:** no están en la hoja de ruta. ¿Se agregan después (ACI 13 y REP 6)?
