# Programa de análisis y diseño estructural 3D

Programa en Python para analizar pórticos 3D por el método de rigidez y, por etapas, diseñar sus elementos de concreto con las normas que rigen en Panamá. El usuario lo está construyendo mientras aprende (POO, análisis matricial, normas), así que se le explica el porqué de las cosas.

## Qué ofrece hoy

| Parte | Qué hace | Dónde |
|---|---|---|
| **Cálculo (sagrado)** | Solo las fórmulas que deciden los resultados: reciben números y devuelven números. Separado del resto y protegido (ver "Cálculo sagrado" en Convenciones). No importa nada del resto del programa | `calculo/` |
| — Rigidez de la barra | Matriz de rigidez local 12×12 de barra 3D (Euler-Bernoulli), ángulos α, β y γ, rotación R = A(α)·B(β)·C(γ), transformación y `k_global_barra` | `calculo/rigidez/barra.py` |
| — Ensamble y solución | K global. `resolver(modelo, F, fef)` resuelve K·U = F con los apoyos (si todo está restringido, U = 0), da las reacciones y las fuerzas en los extremos de cada barra en ejes locales (k·u + FEF) y detecta mecanismos. La clase `Resultados` va aparte | `calculo/rigidez/ensamble.py`, `solucion.py`, `resultados.py` |
| — Cargas en barras | Fuerzas de empotramiento (FEF) en ejes locales de la carga uniforme en toda la barra, la puntual y el momento a una distancia a, en x, y o z. Salen de las funciones de forma de Hermite (cargas consistentes) | `calculo/rigidez/empotramiento.py` |
| — Diagramas N, V, M y T | N, Vy, Vz, T, My y Mz a lo largo de la barra, por equilibrio del tramo 0–x (dos puntos en cada carga puntual, para el salto). Deformada local: integra N/EA, T/GJ y M/EI con los desplazamientos de los dos extremos | `calculo/rigidez/diagramas.py` |
| — Fórmulas del concreto | E = 57 000√f'c en psi (ACI 318-19 §19.2.2.1b, PDF p. 358; en MPa ≈ 4733√f'c), ν = 0.2 (el ACI no lo da) y G = E/2.4. Rectángulo: A, Iy = b·h³/12, Iz = h·b³/12 y J de Saint-Venant (Roark, error < 0.2 %). Peso unitario γ = 150 lb/ft³ = 23.56 kN/m³ (ASCE 7-05 Tabla C3-2, PDF p. 295) | `calculo/concreto.py` |
| — Tolerancias | `TOL_LONGITUD`, `TOL_RELATIVA` y `COND_MAXIMA` (límite de inestabilidad) | `calculo/tolerancias.py` |
| — Diagramas de interacción | Columna rectangular (un eje), circular y rectangular biaxial (cualquier θ y superficie 3D). ACI 318-19 con `pint` | `calculo/interaccion/` |
| Modelo | Nodos, materiales (E, G, γ y, si es concreto, f'c), secciones (A, Iy, Iz, J y su material), barras y apoyos, con validaciones; **casos de carga** y **cargas** en nodos y en barras; modificar y eliminar (borrar un nodo o una barra borra sus cargas). Una barra puede quedar **sin material o sección** (`None`): se dibuja en un gris más claro y el análisis se niega hasta asignarlos. Una sección puede guardar su **refuerzo** (`Concreto`: forma, b × h o D, d, f'c, número de barra y nx·ny o nbarras, en unidades internas). `asignar_seccion` asigna la sección y su material a una barra | `modelo/estructura.py` |
| — Concreto | Por ahora solo concreto: materiales por f'c (con su γ) y secciones con b, h y refuerzo; las fórmulas las toma de `calculo/concreto.py`. Los viejos (sin f'c o sin refuerzo) quedan en la familia "otros". `cambiar_material` y `cambiar_seccion` cambian en su lugar (todo el modelo lo toma; una sección no puede quedar igual a otra). Nombre automático `Concreto 20x20 Nx3 Ny3 #6` (en cm); `buscar_o_crear_seccion` no duplica secciones | `modelo/concreto.py` |
| — Análisis (puente) | Prepara cada caso para el cálculo: pasa las cargas de barra (globales o locales) a ejes locales, suma el peso propio (A·γ por el factor del caso, hacia −Z global), arma F con las cargas nodales y las equivalentes (−Tᵀ·FEF) y llama a `resolver`. Da también los diagramas y la deformada de cada barra, para dibujarlos | `modelo/analisis.py` |
| — Apoyos e interacción | Tipos de apoyo (empotrado, apoyo fijo y libre) y el adaptador del refuerzo a los diagramas de interacción (de kN y m a `pint`, y sus salidas de tonf a kN) | `modelo/apoyos.py`, `modelo/interaccion.py` |
| Archivo | Guardar y abrir modelos en `.json` (texto legible, versión 2): unidades internas, contadores de IDs, casos y cargas, refuerzo y material de las secciones, y f'c y γ de los materiales; revisa la consistencia al abrir. Los de la versión 1 abren igual: la carga de cada nodo pasa al caso Muerta y el concreto toma su γ | `modelo/archivo.py` |
| Salida | Ver matrices con etiquetas de GDL e imprimir el modelo y los resultados en la consola (ya no guarda CSV) | `salida/consola.py` |
| Interfaz 3D | Ventana PySide6 + PyVista, abre **maximizada**: barras, nodos, apoyos (apoyo fijo = cono; empotrado = placa; tamaño `TAMANO_APOYO`, fracción del modelo), números de nodo y de barra, cargas, resultados y rejilla; rotar, zoom y desplazar. Separador gris notorio entre la vista y los paneles. Nodos, barras y apoyos en **gris**; con Seleccionar, **gris oscuro** al pasar el mouse y **negro** al seleccionar, con el mismo tamaño | `interfaz/ventana.py`, `interfaz/vista3d/dibujo.py` |
| — Menús | **Archivo**: Nuevo, Abrir, Guardar, Guardar como (aviso de cambios sin guardar y `*` en el título). **Editar**: Deshacer (Ctrl+Z) y Rehacer (Ctrl+Y). **Supr** (sin estar en el menú) borra lo seleccionado: un nodo con sus barras y cargas, una barra con sus cargas, o una carga. **Ver**: muestra u oculta los paneles (no se cierra al marcar, `MenuPersistente`). **Definir**: Materiales y Secciones de concreto (Combinaciones, deshabilitado: etapa 3). **Configuración** | `interfaz/ventana.py`, `interfaz/historial.py`, `interfaz/paneles/comunes.py` |
| — Definir | Materiales y Secciones **separados**, agrupados en la carpeta **Concreto** ("Otros" solo aparece si hay viejos, sin Nuevo). Están en dos **ventanas** (Definir → Materiales… y Secciones…, no modales, propiedades a la derecha) y en el **Explorador** (propiedades en el panel Propiedades). Clic muestra (una sección, con su dibujo) y otro clic lo quita; doble clic edita; **clic derecho**: Nuevo… en Concreto, Editar…, Copiar… y Eliminar (deshabilitado si está en uso) en un ítem. El material pide f'c y γ (peso propio). Editar un material o una sección aquí **cambia todo el modelo**; editar las medidas desde una barra crea otra sección solo para ella | `interfaz/ventanas/definir.py`, `interfaz/paneles/formularios.py` |
| — Barra de arriba | Íconos: **Deshacer** y **Rehacer** (en gris si no hay nada) · **Material** y **Sección** (las acciones de Definir) · **Caso** (lista: las cargas nuevas van a ese caso y se ven sus resultados) y **Analizar** (▶: resuelve todos los casos) · resultados, uno a la vez (otro clic lo apaga): **Deformada**, **Axial**, **Cortante ▾** (Vy o Vz), **Momento ▾** (My o Mz) y **Torsión**. Están en gris hasta analizar, y cualquier cambio del modelo (también deshacer o abrir) borra los resultados | `interfaz/ventana.py`, `interfaz/iconos.py` |
| — Explorador del modelo | Panel a la izquierda (se mueve de lado y se cierra con su x sin recuadro; no se desacopla). La pestaña inactiva va un poco más oscura. Arriba solo los grupos principales, cerrados, con cuadritos **+/−** unidos por líneas punteadas. Pestaña **Modelo**: Nodos (`1. (x, y, z)`), Elementos, Apoyos, **Cargas** (las del caso activo: `Nodo 3: Fx 10.00 kN, Fz -20.00 kN`, `Barra 2: uniforme -15.00 kN/m (Z global)`), Materiales y Secciones. Pestaña **Tablas**: matrices de rigidez globales (una por elemento) y diagramas de interacción (uno por sección con refuerzo). Elegir un ítem lo selecciona en 3D y lo muestra en Propiedades. Al seleccionar se abren los grupos y se marca **lo relacionado**: el mismo objeto en todas sus filas (un nodo, en Nodos y en Apoyos) y sus cargas, con el color de selección; sus barras (o los nodos de una barra, o el nodo o la barra de una carga), con un fondo más claro (`INTERFAZ_ENLAZADO`) | `interfaz/paneles/explorador.py` |
| — Propiedades | Panel a la derecha (`PanelPropiedades` dentro de un panel acoplable; la ventana Definir usa otro), vacío si no hay nada seleccionado, en unidades de pantalla, sin barra horizontal (lo que no cabe termina en "…"). Nodo: posición, apoyo (tipo y cada eje Δx…φz), cargas del caso activo, barras conectadas y, si hay análisis, desplazamientos y reacción. Material: familia, f'c, E, G, γ y quién lo usa. Sección: su dibujo, propiedades y quién la usa. Barra: nodos, L, α, β, γ, material y sección (la sección se elige de una lista, que asigna también su material; b, h, barra, Nx y Ny se editan y eso busca o crea otra sección **solo para esa barra**), sus cargas y, si hay análisis, el mínimo y el máximo de N, Vy, Vz, T, My y Mz y un **gráfico 2D** del diagrama activo (matplotlib; My si no hay ninguno). Carga: sus datos. Sección con refuerzo: b × h (o D), d, f'c, barras, As, ρ, β1 y fy, y los botones **Ver 2D** y **Ver 3D** (el diagrama se calcula solo al pedirlo, porque pesa). Con las herramientas Apoyo, Carga en nodo y Carga en barra muestra el panel de la herramienta | `interfaz/paneles/propiedades.py`, `interfaz/ventanas/interaccion.py` |
| — Matriz de rigidez | Ventana con la K global 12×12 de un elemento (sale de `k_global_barra`, sin repetir fórmulas): etiquetas de GDL con Δ y φ y los IDs de los nodos (`Δx1`, `φx1`), unidades por bloque (F/L, F y F·L) y botón **Copiar** para pegar en Excel | `interfaz/ventanas/matriz.py` |
| — Cubo de vistas | Arriba a la derecha, como el de Civil 3D: blanco plano (sin iluminación), sin letras ni aro. Gira con la cámara. Al pasar el mouse se sombrea en gris la cara, arista o esquina (la esquina completa, sus 3 parches). Clic = giro animado (~0.35 s, slerp de cuaterniones) hasta la vista desde ese lado (26 vistas), **sin encuadre**: gira alrededor del foco actual, a la misma distancia y con el mismo zoom. El cubo y los ejes (abajo a la izquierda, X en rojo) son cuadrados en píxeles, con el mismo margen a su esquina | `interfaz/vista3d/cubo.py`, `animacion.py`, `camara.py` |
| — Herramientas | Barra a la izquierda, solo íconos, una activa a la vez. **Seleccionar**, **Nodo** (un clic), **Elemento** (dos clics, no encadena; crea o reutiliza los nodos; usa el primer material y sección, o queda sin asignar), **Apoyo** (en Propiedades se elige Empotrado, Apoyo fijo o Libre y cada clic sobre un nodo lo asigna; las casillas de los ejes solo informan, para no permitir combinaciones sin sentido), **Carga en nodo** (Fx, Fy, Fz, Mx, My y Mz en ejes globales; clic sobre un nodo) y **Carga en barra** (uniforme, puntual o momento; valor; dirección global X, Y, Z o local x, y, z; y la distancia a desde el nodo i; clic sobre una barra). Las cargas van al caso activo y **suman** o **reemplazan** las que ya tenga. Cada herramienta es una clase con los mismos métodos (polimorfismo) | `interfaz/herramientas.py`, `interfaz/iconos.py` |
| — Rejilla 3D y snap | Como la de ETABS: la planta (líneas X e Y) repetida en cada nivel Z, desde el origen, con su distancia y cantidad por eje (Configuración → Rejilla). Con **Snap** (F9) el puntero se pega, en este orden, al nodo más cercano en pantalla y al cruce de la rejilla más cercano en pantalla en cualquier nivel (si empatan, el más cercano a la cámara); si no hay nada cerca o el snap está apagado, cae en el plano horizontal de la base (z del nodo más bajo). Antes de colocar se ve dónde quedará el nodo o la barra, en el mismo gris pero transparente | `interfaz/vista3d/rejilla.py`, `interfaz/vista3d/seleccion.py` (`proyectar`), `interfaz/vista3d/dibujo.py` |
| — Barra de comandos | Encima de la barra de estado. Solo se activa con **Nodo** o **Elemento**. La guía es la plantilla gris dentro del campo; lo escrito va en gris mientras no es un punto válido y en negro cuando ya lo es. Coordenadas exactas en unidades de pantalla: `x, y, z`; `x, y` sobre la base; `@dx, dy, dz` relativo. Los números escritos sobre la vista van ahí. Esc cancela | `interfaz/ventana.py`, `interfaz/vista3d/rejilla.py` |
| — Barra inferior | A la izquierda, la **posición del puntero** (solo con el mouse en el dibujo; si se pegó a un nodo, y el largo L). A la derecha: **Rejilla** (F7), **Snap** (F9), **Etiquetas** (menú que no se cierra: números de nodo, números de barra, valores de las cargas y valores de los resultados), **Sección real** (barras como cajas b × h; sin sección, como línea) y **Encuadre** (con el mismo giro del cubo) | `interfaz/ventana.py` |
| — Selección | Clic sobre un nodo o una barra con Seleccionar (los nodos tienen prioridad): queda en negro (un nodo, con su apoyo) y lo enlazado en gris oscuro (de un nodo, sus barras; de una barra, sus nodos y apoyos). Una carga elegida en el explorador pinta su nodo o su barra. Sus datos salen en Propiedades | `interfaz/vista3d/seleccion.py`, `interfaz/ventana.py` (`_relacionados`) |
| — Cargas (dibujo) | Flechas para las fuerzas, doble flecha para los momentos y una fila de flechas para la uniforme, en `colores.CARGA`, con su valor (Etiquetas). Largo: `TAMANO_CARGA`, fracción del modelo | `interfaz/vista3d/cargas.py`, `interfaz/textos.py` |
| — Resultados (dibujo) | **Deformada**: las barras curvas, con el desplazamiento mayor dibujado como `ESCALA_DEFORMADA` del modelo. **Diagramas** rellenos en su plano local (My, Vz, N y T en el x–z; Mz y Vy en el x–y), los momentos del lado de la tracción; positivo en `DIAGRAMA_POSITIVO` y negativo en `DIAGRAMA_NEGATIVO`, con borde y el valor extremo de cada barra (Etiquetas). Alto: `ESCALA_DIAGRAMA` del modelo | `interfaz/vista3d/resultados.py` |
| Configuración | Carpeta separada por tema: unidades, formato, interfaz, colores y preferencias. **Unidades como en Ftool**: unidad y decimales por magnitud. El diálogo **aplica cada cambio en el momento** y lo guarda; abajo solo **Restablecer** (izquierda) y **Cerrar** (derecha). Pestañas: Unidades, Rejilla (distancia y líneas por eje; sin plano de trabajo), Vista, Interfaz y Colores. Las preferencias se guardan aparte (`%APPDATA%\Analisis3D\preferencias.json`) y se aplican encima de la "personalización base" | `configuracion/`, `interfaz/ventanas/dialogo_configuracion.py` |
| Tema | Interfaz en blanco y negro: estilo Fusion, paleta en grises y hoja de estilo. Íconos vectoriales propios | `interfaz/tema.py`, `interfaz/iconos.py` |
| Ejemplo | Pórtico 3D de 5 nodos y 4 barras, todo de concreto: f'c = 4 ksi, viga `Concreto 30x50 Nx3 Ny2 #6` y columna `Concreto 40x40 Nx3 Ny3 #6` (refuerzo **de ejemplo**). Caso Muerta: Fx = 10 kN y Fz = −20 kN en el nodo 3, más el peso propio | `ejemplos/portico.py` |
| Pruebas | Simetría de K, traslación rígida, equilibrio, voladizo e inestabilidad; al final, la integridad del cálculo | `pruebas/verificacion.py` |
| Integridad del cálculo | Huellas SHA-256 de cada archivo de `calculo/` y resultados de referencia: un pórtico, tres barras con cargas en la barra (biempotrada, simple e inclinada; uniforme, puntual y momento, en ejes globales y locales) y puntos de los tres diagramas de interacción. Dice qué archivo cambió y si cambiaron los números | `pruebas/integridad.py`, `pruebas/referencias/` |
| Diagramas de interacción (scripts) | Dibujan con matplotlib (el biaxial, en una ventana tkinter) usando `calculo/interaccion/` | `scripts/interaccion_rectangular.py`, `scripts/interaccion_circular.py`, `scripts/interaccion_biaxial.py` |
| Combinaciones (borrador) | Imprime las combinaciones de resistencia de ASCE 7-05 (incompletas: falta Lr) | `scripts/combinaciones_asce7.py` |

## Cómo ejecutar (desde la raíz)

- `python main.py`: abre la interfaz con el pórtico de ejemplo. Escríbelo en una terminal aparte: el botón ▷ de VS Code escribe en la terminal donde está Claude.
- `python -m pruebas.verificacion`: corre las comprobaciones y, al final, la integridad del cálculo.
- `python -m pruebas.integridad`: revisa solo el cálculo sagrado. Con `--aprobar` acepta el estado actual, **después** de revisar el cambio.
- `python -m scripts.interaccion_biaxial`: diagrama de interacción biaxial con ventana. `scripts.interaccion_rectangular` y `scripts.interaccion_circular` muestran el gráfico directamente, y `scripts.combinaciones_asce7` imprime las combinaciones. Van con `-m` desde la raíz, para que encuentren `calculo/`.

**Dependencias:** `pip install -r requirements.txt` (matplotlib, numpy, pandas, pint, PySide6, pyvista, pyvistaqt).

## Estructura

```
calculo/        SAGRADO: solo fórmulas (entran números, salen números). No importa nada del resto
  rigidez/        barra (k local, ángulos, R y T), ensamble (K), solucion (K·U = F, reacciones y fuerzas),
                  resultados (la clase), empotramiento (FEF) y diagramas (N, V, M, T y deformada)
  interaccion/    diagramas de interacción ACI 318-19 (comun, rectangular, circular y biaxial)
  concreto.py     E, G, A, I, J y γ del concreto
  tolerancias.py
modelo/         las clases y su manejo: estructura (Modelo, nodos, materiales, secciones, barras, casos
                y cargas), concreto (nombres, familias, buscar y cambiar), apoyos (tipos), interaccion
                (refuerzo → pint), analisis (puente del modelo al cálculo, por caso) y archivo (.json)
configuracion/  unidades, formato, interfaz, colores y preferencias (ver su __init__.py)
interfaz/       ventana, tema, íconos, herramientas, historial (deshacer) y textos (de las cargas)
  vista3d/        dibujo, cargas, resultados, cubo, cámara, animación, selección y rejilla (snap)
  paneles/        explorador, propiedades, formularios y comunes (ArbolLimpio, TituloPanel, MenuPersistente)
  ventanas/       Definir, configuración, matriz K e interacción (Ver 2D y Ver 3D)
salida/         impresión en consola
scripts/        programas sueltos: diagramas de interacción y combinaciones (python -m scripts.…)
ejemplos/       modelos de prueba
pruebas/        comprobaciones automáticas, integridad del cálculo y sus referencias
docs/codigos/   PDF de ACI 318-19, ASCE 7-05 y REP 2021
docs/normas/    notas de normas por etapa (cláusula, fórmula y página del PDF) + índice
docs/plan_de_estudio.md   hoja de ruta, plan de estudio, verificaciones y hallazgos
.claude/settings.json     hace que Claude Code pida permiso antes de editar calculo/
.claude/skills/ revisar-pedido, verificar-calculos, consultar-normas (con scripts para leer los PDF)
main.py                   punto de entrada (carga las preferencias, el tema y la ventana)
```

## Convenciones (no cambiarlas sin decidirlo con el usuario)

- **Cálculo sagrado (`calculo/`):**
  - ahí están solo las fórmulas que deciden los resultados: rigidez (barra, ensamble, solución, empotramiento y diagramas a lo largo de la barra), concreto (E, G, A, I, J y γ), tolerancias y diagramas de interacción. No importa nada de `modelo/`, `configuracion/` ni `interfaz/`: recibe datos y devuelve números;
  - **no se cambia sin un pedido explícito del usuario que nombre `calculo/`**. Si otro cambio lo necesita, se para y se pregunta;
  - Claude Code pide permiso antes de editar cualquier archivo de ahí (`.claude/settings.json`: `"ask": ["Edit(calculo/**)"]`);
  - después de un cambio: `python -m pruebas.integridad`. Si cambian los resultados de referencia, cambió el cálculo: se justifica (skill `verificar-calculos`) y, ya revisado, `python -m pruebas.integridad --aprobar`;
  - los commits que lo cambian empiezan con **"CALCULO:"**;
  - lo que adapta los datos del modelo al cálculo vive afuera: `modelo/analisis.py` arma F y las FEF de cada caso, y `modelo/interaccion.py` pasa el refuerzo (en kN y m) a las cantidades `pint` de los diagramas, y sus salidas de tonf a kN. Las clases (`Modelo`, `Caso`, `CargaBarra`…) viven en `modelo/`; el cálculo no las importa: lee los atributos del modelo que recibe (como `ensamblar_k`) o recibe tuplas y números (como `empotramiento` e `internas`).
- **Unidades:**
  - el modelo guarda **todo en kN y m (unidades internas)**: E y G en kN/m², A en m², I en m⁴;
  - la interfaz muestra y recibe en **unidades de pantalla por magnitud, como en Ftool**. Cada magnitud (longitud, área, inercia, fuerza, momento, carga distribuida y esfuerzo) tiene su unidad (`unidades.LONGITUD`…) y sus decimales (`formato.DECIMALES_LONGITUD`…). Se convierte con `configuracion/unidades.py` (`a_interna`, `a_pantalla`, `simbolo`) y se escribe con `formato.cantidad`. Cambiar de unidades no toca los datos;
  - las matrices de rigidez mezclan magnitudes: cada bloque se convierte con `unidades.compuesta(a, b)`, que da F^a·L^b con las unidades elegidas (F/L, F o F·L);
  - **tonf es la tonelada métrica** (9.80665 kN). En `pint`, `ton_force` es la tonelada corta (8.896 kN): no usarla;
  - los diagramas de interacción (`calculo/interaccion/`) usan `pint`: reciben cantidades con unidades (los scripts dan cm, ksi y número de barra) y devuelven `tonne_force = 1000 kgf` y tonf·m.
- **Orientación de barras:**
  - R = A(α)·B(β)·C(γ), estilo Mathcad;
  - γ = atan2(dy, dx);
  - β = −atan2(dz, √(dx² + dy²)), negativo por el signo de la matriz B;
  - α es el giro de la sección, que el usuario da **en grados**; se guarda en grados y se pasa a radianes en el ensamble.
- **Orden de los nodos de una barra** (`Modelo._ordenar`): de abajo hacia arriba; si es horizontal, hacia +x; si no, hacia +y. Se reordena al mover un nodo.
- **IDs:** empiezan en 1 y **no se reutilizan** (`_sig_id`). El archivo `.json` guarda los contadores para que esto siga valiendo al reabrir. Deshacer devuelve también los contadores: un objeto deshecho nunca existió.
- **Ejes de la sección:** b va en el eje local y y h en el local z (Iy = b·h³/12, la de flexión en el plano x-z). En una viga con α = 0, z local es el vertical global, así que h queda vertical.
- **Deshacer:** todo lo que cambia el modelo llama antes a `ventana.antes_de_cambiar()` (guarda una copia completa); después, `ventana.modelo_cambiado(texto)`. Máximo `HISTORIAL_MAXIMO` pasos (Configuración → Interfaz).
- **GDL por nodo:** [Dx, Dy, Dz, Phix, Phiy, Phiz] (en pantalla, `formato.GDL_PANTALLA`: Δx, Δy, Δz, φx, φy, φz; la consola sigue con Dx y Phix). **Cargas:** [Fx, Fy, Fz, Mx, My, Mz]. **Fuerzas locales:** [N, Vy, Vz, T, My, Mz] del nodo i y luego del j.
- **Signos:** fuerzas que los nodos ejercen sobre la barra. El orden en K es el orden de creación de los nodos.
- **Casos y cargas:**
  - `Modelo.casos`: por ahora solo **1: Muerta** (tipo D, peso propio ×1). La viva llegará con las losas (etapa 6); las combinaciones, en la etapa 3;
  - `Modelo.cargas` {id: carga}, cada una con su caso. `CargaNodal`: [Fx, Fy, Fz, Mx, My, Mz] en ejes globales. `CargaBarra`: tipo `"uniforme"` (en toda la barra, kN/m), `"puntual"` (kN) o `"momento"` (kN·m); dirección `"X"`, `"Y"`, `"Z"` (global) o `"x"`, `"y"`, `"z"` (local); `a`, distancia desde el nodo i (m);
  - **peso propio:** A·γ·(factor del caso), hacia −Z global, con la longitud entre nodos. γ es del material (kN/m³);
  - **cálculo:** FEF en ejes locales (lo que los nodos ejercen sobre la barra empotrada) → cargas equivalentes −Tᵀ·FEF → fuerzas en los extremos k·u + FEF;
  - **signos de los diagramas** (los de las vigas de los libros, en ejes locales): N > 0 es tracción; Mz > 0 tracciona la fibra de −y y My > 0 la de −z (en una viga con α = 0, My > 0 es el momento positivo, que tracciona abajo); dMz/dx = Vy y dMy/dx = Vz; T es el momento alrededor de x en la cara positiva. Los momentos se dibujan del lado de la tracción;
  - cualquier cambio del modelo borra los resultados (`ventana._invalidar_resultados`): hay que volver a analizar.
- **Configuración:** todo valor ajustable de presentación vive en `configuracion/`. Las tolerancias del cálculo no: están en `calculo/tolerancias.py`.
  - Lo que el usuario puede cambiar se lee en el momento (`colores.ELEMENTO`, `ui.TAMANO_ICONO`), nunca con `from ... import CONSTANTE`; si no, no vería sus cambios. Las constantes fijas (tolerancias, nombres de GDL) sí se pueden importar.
  - Para hacer algo configurable se agrega una línea a `preferencias.PARAMETROS` y el diálogo se arma solo.
  - Los valores con unidades (`magnitud`) se guardan en internas.
  - El diálogo aplica cada cambio en el momento y lo guarda. Espera `RETARDO_CONFIGURACION_MS` para no redibujar con cada tecla: si se escribe "125", redibuja una vez y no tres.
  - Quedan fuera del diálogo, como constantes internas: los atajos (F7 y F9), las distancias de selección, de snap y de clic, y los tamaños de apoyo, letra y previsualización.
- **Interfaz:**
  - un clic es presionar y soltar con menos de `TOL_CLIC_PX` de movimiento;
  - en la selección, los nodos tienen prioridad sobre las barras (tolerancia `TOL_SELECCION_PX`);
  - el cubo usa su propio `vtkOrientationMarkerWidget`, porque `add_orientation_widget` de PyVista borraría los ejes de `add_axes`. El cubo y los ejes van en viewports cuadrados en píxeles, con `MARGEN_ESQUINA_PX` a su esquina, y se recalculan al cambiar el tamaño de la ventana;
  - **colores:** la interfaz (íconos, barras, botones) va solo en blanco, negro y grises; el dibujo 3D puede tener color (el eje X en rojo, las cargas, la deformada y los diagramas);
  - **colores de la vista:** nodos, barras y apoyos en `colores.ELEMENTO` (gris); al pasar el mouse con Seleccionar, `RESALTADO` (gris oscuro); lo seleccionado, `SELECCIONADO` (negro); sin material o sección, `SIN_ASIGNAR` (gris más claro). Se cambia el color de cada celda (escalares RGB en actores VTK armados a mano en `dibujo._agregar`, porque `add_mesh` copia la malla) y no se dibuja nada encima: así no cambia el tamaño ni parpadea. La previsualización usa el mismo gris con `OPACIDAD_PREVISUALIZACION`;
  - **lo relacionado** con lo seleccionado (`ventana._relacionados`): de un nodo, su apoyo, sus cargas y sus barras; de una barra, sus nodos, sus apoyos y sus cargas; de una carga, su nodo o su barra. En 3D va en gris oscuro; en el explorador, las cargas con el color de selección y lo demás con `INTERFAZ_ENLAZADO`;
  - **apoyos** (`modelo/apoyos.py`): solo empotrado (6 restringidos), apoyo fijo (Dx, Dy, Dz) y libre. Z es la vertical: el cono y la placa van debajo del nodo;
  - **íconos propios** en `iconos.py`: línea negra de 1.5 en una cuadrícula de 24×24, sin relleno; deshabilitados en gris;
  - lo que está activo se sombrea en gris; una acción (como Encuadre) no queda activa;
  - **organización:**
    - arriba, menús con palabras (son categorías): Archivo · Editar · Ver · Definir · Configuración; debajo, la barra con íconos: Deshacer y Rehacer · Material y Sección · Caso y Analizar · resultados;
    - a la izquierda, las herramientas que cambian lo que hace el clic (una activa a la vez) y el Explorador del modelo;
    - a la derecha, Propiedades;
    - los paneles se pueden mover de lado y cerrar (no se desacoplan); se vuelven a abrir desde **Ver**;
    - los árboles usan "+"/"−" con líneas punteadas (`tema.EstiloArbol`, una capa sobre Fusion); la fila elegida, en `INTERFAZ_SELECCION`;
    - los árboles del explorador y de Definir son `paneles/comunes.ArbolLimpio`: no toman el foco (si no, Qt deja la primera fila marcada sola), otro clic sobre lo elegido o un clic en el vacío lo deselecciona, y las carpetas se abren con un clic y no se eligen. Propiedades no selecciona filas;
    - los paneles tienen barra de título propia (`paneles/comunes.TituloPanel`): la x sola, sombreada al pasar el mouse;
    - las acciones sobre materiales y secciones van con palabras en el menú de clic derecho (son verbos, no herramientas);
    - abajo, la barra de comandos y, en la barra de estado, la posición del puntero y, a la derecha, cómo se ve el modelo y Encuadre;
    - solo íconos con tooltip mientras el símbolo sea claro;
  - **atajos** como en Civil 3D: F7 rejilla, F9 snap;
  - la cámara la mueve un solo `AnimadorCamara` (cubo y Encuadre): un giro nuevo reemplaza al anterior. El cubo no encuadra: gira alrededor del foco actual, a la misma distancia y con el mismo zoom;
  - lo que pesa se calcula solo cuando el usuario lo pide: los diagramas de interacción (Ver 2D y Ver 3D) y el análisis (Analizar).

## Normas

- **REP 2021** (Panamá) manda. Para cargas, combinaciones, sismo y viento remite a **ASCE/SEI 7-05** con modificaciones; para concreto, a **ACI 318-19**. Está confirmado en el propio REP: Introducción, 1.3, 1.4.1 y 8.1.
- Las notas por tema están en `docs/normas/` (índice y etapas 1 a 8). Para citar o comprobar algo de las normas se usa la skill `consultar-normas`.
- Lo que más se olvida:
  - **viento del REP a nivel de servicio → 1.6W** en las combinaciones (REP 8.4, ACI 5.3.5);
  - **Cs ≥ 0.044·SDS·I ≥ 0.01** (REP 5.2.1);
  - **TL = 10 s** (REP 5.13);
  - **tabiques como carga muerta, 0.75 kPa** (REP 2.1).

## Hoja de ruta (orden acordado)

1. Materiales y secciones
2. Cargas en barras y diagramas N, V, M y T
3. Combinaciones de carga
4. Columnas: estribos, cortante y esbeltez (usando los diagramas de interacción)
5. Vigas: acero longitudinal y estribos
6. Losas: una y dos direcciones, viguetas, metal deck
7. Sismo, con deriva
8. Viento, con deriva de servicio

El detalle (qué estudiar, cómo verificar y cuándo se considera terminada cada etapa) está en `docs/plan_de_estudio.md`.

**Avance:** la etapa 2 está hecha en lo principal (cargas en nodos y barras, peso propio, caso Muerta, diagramas N, V, M y T y deformada, verificados contra casos de libro); falta compararla con Ftool o PyNite. El detalle, en el plan.

## Limitaciones actuales del programa (REP 1.8.2 pide conocerlas y documentarlas)

- Análisis elástico lineal de **primer orden**: sin P-Δ.
- **Cargas:** en los nodos y en las barras (uniforme en **toda** la barra, puntual y momento a una distancia a) y el peso propio. Todavía sin cargas parciales ni trapezoidales, de área (losas), de temperatura ni asentamientos.
- **Un solo caso, Muerta,** y sin combinaciones (etapa 3): los resultados son de servicio, sin mayorar.
- El peso propio usa la longitud entre nodos, así que el nudo viga–columna se cuenta en las dos barras (queda del lado seguro).
- Sin liberaciones (articulaciones en los extremos de barra) ni brazos rígidos.
- Sin deformación por cortante.
- Secciones con **inercia bruta**: todavía sin los modificadores de agrietamiento del ACI (Tabla 6.6.3.1.1).
- Sin diafragmas, masas ni análisis dinámico.
- La inestabilidad se detecta con cond(Kll) > `COND_MAXIMA` (1e12, en `calculo/tolerancias.py`), un criterio que depende de las unidades.
- Las barras sin material o sección se pueden dibujar, pero el análisis las rechaza hasta que se asignen.
- Secciones definibles: solo rectangulares de concreto (las circulares solo desde código).
- Los diagramas de interacción se ven por sección (Propiedades → Ver 2D o Ver 3D), pero todavía no se usan para diseñar. Los hallazgos pendientes de revisión (β1, columna con espiral, barras #14/#18, cuantía en pórtico especial) están en `docs/plan_de_estudio.md` y **siguen sin corregir**: corregirlos es un cambio al cálculo sagrado.

## Cómo trabajar en este proyecto (instrucciones para Claude)

- Responder en **español**.
- **Al empezar cada pedido, usar la skill `revisar-pedido`.** El usuario quiere que en todo lo que diga se busquen contradicciones (con las normas, con el código y sus convenciones, con la hoja de ruta) y formas mejores de hacerlo. La respuesta va breve, al inicio.
- Todo cálculo, fórmula o resultado: skill **`verificar-calculos`**. Toda cita de norma: skill **`consultar-normas`**. Nunca citar de memoria sin comprobar.
- **No escribir ni modificar código sin un pedido explícito.** Frases como "vamos con…" significan conversar. Ante la duda, preguntar.
- **`calculo/` es sagrado:** no tocarlo sin un pedido explícito que lo nombre (ver Convenciones). Si un cambio de otra parte lo necesita, parar y preguntar.
- **Al agregar botones o funciones**, sugerir:
  - dónde van (organización);
  - si llevan ícono, palabra o ambos;
  - qué parámetros conviene que el usuario configure. Los valores base quedan en `configuracion/` ("personalización base") y se exponen en el diálogo con una línea en `preferencias.PARAMETROS`.
- **Commits:** no ejecutarlos. Dar el comando listo para pegar en PowerShell, en una línea:

  `git add .` y luego ``git commit -m "Asunto" -m "- punto 1`n- punto 2"``

  - No usar comillas dobles ni backticks dentro del texto del mensaje.
  - Si el commit cambia `calculo/`, el asunto empieza con "CALCULO:".
  - **Nunca** agregar `Co-Authored-By` ni ninguna otra atribución a Claude.
- Explicar el porqué con ejemplos. El usuario estudia POO y análisis estructural mientras construye el programa.
