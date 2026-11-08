# Plan de estudio y verificaciones

Este plan acompaña al programa de análisis y diseño estructural. Cada etapa dice qué se agrega al programa, qué estudiar (normas, teoría y Python), cómo verificar y cuándo se considera terminada.

Las notas de normas, con cláusula y página, están en [`docs/normas/`](normas/indice.md).

**Normas que aplican en Panamá** (confirmado en el REP 2021):
- **REP 2021** manda;
- cargas, sismo y viento por **ASCE/SEI 7-05** con los cambios del REP;
- concreto por **ACI 318-19**.

## Estado actual (lo que ya hace el programa)

- **Análisis matricial de pórticos 3D** (`calculo/`):
  - barras de 12 GDL;
  - transformación por ángulos α, β y γ;
  - ensamble de K y solución de K·U = F;
  - reacciones y fuerzas en los extremos de cada barra (ejes locales).

  Solo acepta **cargas en los nodos**.
- **Interfaz 3D** (`interfaz/`, PySide6 y PyVista): muestra barras, nodos, apoyos y números de nodo; incluye el cubo de vistas y la selección.
- **Diagramas de interacción de columnas** (scripts sueltos):
  - rectangular 2D (`iteracion2drect.py`);
  - circular 2D (`iteracion2dcir.py`);
  - rectangular biaxial 3D con ventana tkinter (`iteracion3drect.py`).
- **Comprobaciones automáticas** (`pruebas/verificacion.py`).
- Borrador de combinaciones (`combinacionescarga.py`).

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
- **Listo cuando:** `combinacionescarga.py` queda reemplazado por un módulo con pruebas, que incluye Lr, 0.5L y las dos direcciones.

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
  - refactorizar `iteracion*.py` en un paquete `diseno/` con funciones puras y pruebas;
  - separar el cálculo de la ventana (hoy están mezclados en `iteracion3drect.py`).
- **Verificaciones:**
  - ejemplo resuelto de un libro con ACI 318-19 (diagrama y estribos);
  - casos borde: Pu = 0.3·Ag·f'c y el paso de barra #10 a #11 (cambio de diámetro mínimo del estribo);
  - diagrama de interacción contra **spColumn** o un ejemplo publicado.
- **Corregir antes** (hallazgos):
  - `beta1` con f'c = 2.5 ksi;
  - φ y Pn,max de la columna circular con espiral;
  - diámetros de las barras #14 y #18;
  - límite de cuantía de 6 % en pórtico especial.
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
  - metal deck compuesto: **ANSI/SDI C**, AISI S100-2013 y AISC 360-10, que **no están en `codigos/`**.
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
- detección de estructura inestable.

**Propuestas:**
1. **Rotación rígida:** u = θ × r en todos los nodos, con φ = θ → K·u = 0. Completa la prueba de cuerpo rígido.
2. **Pórtico plano** contra un ejemplo de libro y contra Ftool.
3. **Pórtico 3D** contra **PyNite** (Python, gratuito), comparando desplazamientos y reacciones.
4. **Casos con solución cerrada** de cada etapa (los listados arriba).
5. **Diagramas de interacción** contra un ejemplo publicado.
6. **Unidades:** la misma estructura en m y kN y en mm y N debe dar resultados equivalentes.
7. Mantener una **tabla de limitaciones** del programa en `CLAUDE.md`, como pide el REP 1.8.2.

## Hallazgos de la revisión (pendientes de decidir; no se tocaron)

1. **Unidades mezcladas:** el análisis trabaja en kN y m; los diagramas en pulgadas y ksi, con salida en tonf. Se sugiere SI por dentro y `pint` en la entrada y la salida.
2. **`requirements.txt`** no incluye `pint` ni `matplotlib`, que usan los `iteracion*.py`.
3. **`beta1`:** rechaza f'c = 2.5 ksi, que el ACI permite (Tabla 22.2.2.4.3).
4. **Barras #14 y #18:** sus diámetros salen mal con n/8 (son 1.693 in y 2.257 in).
5. **Columna circular:** usa φ y 0.80·Po de columna con estribos. Con espiral son 0.75 y 0.85·Po.
6. **Cuantía máxima de 8 %:** en pórtico especial es 6 %.
7. **Combinaciones:**
   - les falta Lr;
   - no aplican la opción 0.5L;
   - SDS y ρ están fijos en el código;
   - no consideran X e Y ni la torsión accidental.
8. **Análisis:**
   - solo cargas nodales;
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

## Preguntas abiertas

1. **Unidades del programa:** ¿todo en SI (kN, m, MPa) por dentro, con conversión solo en la entrada y la salida?
2. **Viguetas:** ¿se trata de losas nervadas coladas en sitio o de viguetas pretensadas prefabricadas con bloques (sistemas de fabricante)?
3. **Metal deck:** ¿losa compuesta o la lámina solo como encofrado? ¿Las vigas de apoyo son de acero (AISC 360-10)? Hacen falta SDI C, AISI S100 y AISC 360 en `codigos/`.
4. **Sistema estructural objetivo:** ¿solo pórticos especiales de concreto, o también muros y sistemas duales?
5. **Análisis sísmico:** ¿basta con la FLE al principio, o se quiere el modal desde el inicio?
6. **Cimentaciones:** no están en la hoja de ruta. ¿Se agregan después (ACI 13 y REP 6)?
