# Programa de análisis y diseño estructural 3D

Programa en Python para analizar pórticos 3D por el método de rigidez y, por etapas, diseñar sus elementos de concreto con las normas que rigen en Panamá. El usuario lo está construyendo mientras aprende (POO, análisis matricial, normas), así que se le explica el porqué de las cosas.

## Qué ofrece hoy

| Parte | Qué hace | Dónde |
|---|---|---|
| **Cálculo (sagrado)** | Todo lo que decide los resultados, separado del resto y protegido (ver "Cálculo sagrado" en Convenciones). No importa nada del resto del programa | `calculo/` |
| — Elemento | Matriz de rigidez local 12×12 de barra 3D (Euler-Bernoulli), ángulos α, β y γ, rotación R = A(α)·B(β)·C(γ), transformación y `k_global_barra` | `calculo/elemento.py` |
| — Ensamble y análisis | K global, vector F, solución K·U = F con apoyos, reacciones, fuerzas en los extremos de cada barra (ejes locales) y detección de mecanismo | `calculo/ensamble.py`, `calculo/analisis.py` |
| — Tolerancias | `TOL_LONGITUD`, `TOL_RELATIVA` y `COND_MAXIMA` (límite de inestabilidad) | `calculo/tolerancias.py` |
| — Diagramas de interacción | Columna rectangular (un eje), circular y rectangular biaxial (cualquier θ y superficie 3D). ACI 318-19 con `pint` | `calculo/interaccion/` |
| Modelo | Nodos, materiales (E, G y, si es concreto, f'c), secciones (A, Iy, Iz, J y su material) y barras, con validaciones; apoyos y cargas **nodales**; modificar y eliminar. Una barra puede quedar **sin material o sección** (`None`): se dibuja en un gris más claro y el análisis se niega hasta asignarlos. Una sección puede guardar su **refuerzo** (`Concreto`: forma, b × h o D, d, f'c, número de barra y nx·ny o nbarras, en unidades internas). `asignar_seccion` asigna la sección y su material a una barra | `modelo/estructura.py` |
| Concreto | E = 57 000√f'c en psi (ACI 318-19 §19.2.2.1b, PDF p. 358; en MPa ≈ 4733√f'c), ν = 0.2 (el ACI no lo da) y G = E/2.4. Rectángulo: A, Iy = b·h³/12, Iz = h·b³/12 y J de Saint-Venant (Roark, error < 0.2 %). Nombre automático `Concreto 20x20 Nx3 Ny3 #6` (en cm); `buscar_o_crear_seccion` no duplica secciones | `modelo/concreto.py` |
| Archivo | Guardar y abrir modelos en `.json` (texto legible): unidades internas, contadores de IDs, plano de la rejilla, refuerzo y material de las secciones y f'c de los materiales; revisa la consistencia al abrir. Los archivos anteriores abren igual | `modelo/archivo.py` |
| Salida | Ver matrices con etiquetas de GDL (o guardarlas en CSV para Excel) e imprimir el modelo y los resultados | `salida/consola.py` |
| Interfaz 3D | Ventana PySide6 + PyVista, abre **maximizada**: barras, nodos, apoyos (apoyo fijo = cono; empotrado = placa; tamaño `TAMANO_APOYO`, fracción del modelo), números de nodo y rejilla; rotar, zoom y desplazar. Separador gris notorio entre la vista y los paneles. Nodos, barras y apoyos en **gris**; con Seleccionar, **gris oscuro** al pasar el mouse y **negro** al seleccionar, con el mismo tamaño | `interfaz/ventana.py`, `interfaz/dibujo.py` |
| — Menús | **Archivo**: Nuevo, Abrir, Guardar, Guardar como (aviso de cambios sin guardar y `*` en el título). **Editar**: Deshacer (Ctrl+Z), Rehacer (Ctrl+Y) y Eliminar (Supr: un nodo con sus barras, o una barra). **Ver**: muestra u oculta los paneles. **Definir**: Materiales y Secciones de concreto (Combinaciones, deshabilitado: etapa 3). **Configuración** | `interfaz/ventana.py`, `interfaz/historial.py` |
| — Definir | Materiales: f'c, nombre propuesto (`Concreto f'c 28 MPa`), E y G calculados; no se editan (las secciones copiaron su f'c). Secciones rectangulares: material, b, h, d, barra, Nx y Ny, con nombre y propiedades calculadas y una **previsualización** a escala con las barras. Guardar cambios en una sección en uso crea otra | `interfaz/definir.py` |
| — Barra de arriba | Íconos: **Deshacer** y **Rehacer** (en gris si no hay nada) y, separados, **Material** y **Sección** (las acciones de Definir) | `interfaz/ventana.py`, `interfaz/iconos.py` |
| — Explorador del modelo | Panel a la izquierda (se mueve de lado y se cierra; no se desacopla). Arriba solo los grupos principales, cerrados, con cuadritos **+/−** unidos por líneas punteadas. Pestaña **Modelo**: Nodos, Elementos y Apoyos (`1. (x, y, z)`). Pestaña **Tablas**: matrices de rigidez globales (una por elemento) y diagramas de interacción (uno por sección con refuerzo). Elegir un ítem lo selecciona en 3D y lo muestra en Propiedades; seleccionar en 3D lo marca en el árbol | `interfaz/explorador.py` |
| — Propiedades | Panel a la derecha, en unidades de pantalla, sin barra horizontal (lo que no cabe termina en "…"). Nodo: posición, apoyo (tipo y cada eje Dx…φz), cargas y barras conectadas. Barra: nodos, L, α, β, γ, material y sección: la sección se elige de una lista (asigna también su material) y b, h, barra, Nx y Ny se editan; editar busca o crea otra sección **solo para esa barra**. Sección con refuerzo: b × h (o D), d, f'c, barras, As, ρ, β1 y fy, y los botones **Ver 2D** y **Ver 3D** (el diagrama se calcula solo al pedirlo, porque pesa) | `interfaz/propiedades.py`, `interfaz/diagramas.py`, `interfaz/concreto.py` |
| — Matriz de rigidez | Ventana con la K global 12×12 de un elemento (sale de `k_global_barra`, sin repetir fórmulas): etiquetas de GDL con φ y los IDs de los nodos (`φx1`), unidades por bloque (F/L, F y F·L) y botón **Copiar** para pegar en Excel | `interfaz/tablas.py` |
| — Cubo de vistas | Arriba a la derecha, como el de Civil 3D: blanco plano (sin iluminación), sin letras ni aro. Gira con la cámara. Al pasar el mouse se sombrea en gris la cara, arista o esquina (la esquina completa, sus 3 parches). Clic = giro animado (~0.35 s, slerp de cuaterniones) hasta la vista desde ese lado (26 vistas). El cubo y los ejes (abajo a la izquierda, X en rojo) son cuadrados en píxeles, con el mismo margen a su esquina | `interfaz/cubo_vistas.py`, `interfaz/animacion.py`, `interfaz/camara.py` |
| — Herramientas | Barra a la izquierda, solo íconos, una activa a la vez. **Seleccionar**, **Nodo** (un clic), **Elemento** (dos clics, no encadena; crea o reutiliza los nodos; usa el primer material y sección, o queda sin asignar) y **Apoyo** (en Propiedades se elige Empotrado, Apoyo fijo o Libre y cada clic sobre un nodo lo asigna; las casillas de los ejes solo informan, para no permitir combinaciones sin sentido). Cada herramienta es una clase con los mismos métodos (polimorfismo) | `interfaz/herramientas.py`, `interfaz/iconos.py` |
| — Plano de trabajo y snap | La rejilla está en un plano **XY, XZ o YZ** a una coordenada (Configuración). Empieza en el origen, con N líneas por eje separadas una distancia d. El puntero cae en ese plano. Con **Snap** (F9) se pega a nodos (en pantalla) y a las intersecciones de la rejilla (solo dentro de ella); antes de colocar se ve dónde quedará el nodo o la barra, en el mismo gris pero transparente | `interfaz/plano_trabajo.py`, `interfaz/dibujo.py` |
| — Barra de comandos | Encima de la barra de estado. Solo se activa con **Nodo** o **Elemento**. La guía es la plantilla gris dentro del campo; lo escrito va en gris mientras no es un punto válido y en negro cuando ya lo es. Coordenadas exactas en unidades de pantalla: `x, y, z`; `u, v` en el plano de la rejilla; `@dx, dy, dz` relativo. Los números escritos sobre la vista van ahí. Esc cancela | `interfaz/ventana.py`, `interfaz/plano_trabajo.py` |
| — Barra inferior | A la izquierda, la **posición del puntero** (si se pegó a un nodo, y el largo L). A la derecha: **Rejilla** (F7), **Snap** (F9), **Etiquetas**, **Sección real** (barras como cajas b × h; sin sección, como línea) y **Encuadre** (con el mismo giro del cubo) | `interfaz/ventana.py` |
| — Selección | Clic sobre un nodo o una barra con Seleccionar (los nodos tienen prioridad). Sus datos salen en Propiedades | `interfaz/seleccion.py` |
| Configuración | Carpeta separada por tema: unidades, formato, interfaz, colores y preferencias. **Unidades como en Ftool**: unidad y decimales por magnitud. El diálogo **aplica cada cambio en el momento** y lo guarda; abajo solo **Restablecer** (izquierda) y **Salir** (derecha). Pestañas: Unidades, Rejilla, Vista, Interfaz y Colores. Las preferencias se guardan aparte (`%APPDATA%\Analisis3D\preferencias.json`) y se aplican encima de la "personalización base" | `configuracion/`, `interfaz/dialogo_configuracion.py` |
| Tema | Interfaz en blanco y negro: estilo Fusion, paleta en grises y hoja de estilo. Íconos vectoriales propios | `interfaz/tema.py`, `interfaz/iconos.py` |
| Ejemplo | Pórtico 3D de 5 nodos y 4 barras. La sección "Col 40x40" lleva un refuerzo **de ejemplo** (8 #6, f'c = 4 ksi) | `ejemplos/portico.py` |
| Pruebas | Simetría de K, traslación rígida, equilibrio, voladizo e inestabilidad; al final, la integridad del cálculo | `pruebas/verificacion.py` |
| Integridad del cálculo | Huellas SHA-256 de cada archivo de `calculo/` y resultados de referencia (un pórtico y puntos de los tres diagramas). Dice qué archivo cambió y si cambiaron los números | `pruebas/integridad.py`, `pruebas/referencias/` |
| Diagramas (scripts) | Dibujan con matplotlib (el biaxial, en una ventana tkinter) usando `calculo/interaccion/`. Se ven y se usan igual que antes | `iteracion2drect.py`, `iteracion2dcir.py`, `iteracion3drect.py` |
| Combinaciones (borrador) | Imprime las combinaciones de resistencia de ASCE 7-05 (incompletas: falta Lr) | `combinacionescarga.py` |

## Cómo ejecutar (desde la raíz)

- `python main.py`: abre la interfaz con el pórtico de ejemplo. Escríbelo en una terminal aparte: el botón ▷ de VS Code escribe en la terminal donde está Claude.
- `python -m pruebas.verificacion`: corre las comprobaciones y, al final, la integridad del cálculo. Escribe `K_global.csv`, que git ignora.
- `python -m pruebas.integridad`: revisa solo el cálculo sagrado. Con `--aprobar` acepta el estado actual, **después** de revisar el cambio.
- `python iteracion3drect.py`: diagrama de interacción biaxial con ventana. Los otros dos `iteracion*.py` muestran el gráfico directamente.

**Dependencias:** `pip install -r requirements.txt` (matplotlib, numpy, pandas, pint, PySide6, pyvista, pyvistaqt).

## Estructura

```
calculo/        SAGRADO: elemento, ensamble, análisis, tolerancias e interaccion/ (diagramas
                ACI 318-19). No importa nada del resto del programa
modelo/         datos del modelo (estructura.py), concreto.py (E, G, A, I, J y nombres) y archivo .json
configuracion/  unidades, formato, interfaz, colores y preferencias (ver su __init__.py)
interfaz/       ventana, explorador, propiedades, definir, historial (deshacer), tablas (matriz K), diagramas,
                apoyos (tipos), concreto (adaptador
                del refuerzo al cálculo), herramientas, plano de trabajo, diálogo de configuración,
                cubo de vistas, animación de cámara, selección, dibujo, íconos y tema
salida/         impresión en consola y CSV
ejemplos/       modelos de prueba
pruebas/        comprobaciones automáticas, integridad del cálculo y sus referencias
docs/codigos/   PDF de ACI 318-19, ASCE 7-05 y REP 2021
docs/normas/    notas de normas por etapa (cláusula, fórmula y página del PDF) + índice
docs/plan_de_estudio.md   hoja de ruta, plan de estudio, verificaciones y hallazgos
.claude/settings.json     hace que Claude Code pida permiso antes de editar calculo/
.claude/skills/ revisar-pedido, verificar-calculos, consultar-normas (con scripts para leer los PDF)
main.py                   punto de entrada (carga las preferencias, el tema y la ventana)
iteracion*.py             gráficos de los diagramas de interacción (usan calculo/interaccion/)
```

## Convenciones (no cambiarlas sin decidirlo con el usuario)

- **Cálculo sagrado (`calculo/`):**
  - ahí está solo lo que decide los resultados: rigidez, ensamble, análisis, tolerancias y diagramas de interacción. No importa nada de `modelo/`, `configuracion/` ni `interfaz/`: recibe datos y devuelve números;
  - **no se cambia sin un pedido explícito del usuario que nombre `calculo/`**. Si otro cambio lo necesita, se para y se pregunta;
  - Claude Code pide permiso antes de editar cualquier archivo de ahí (`.claude/settings.json`: `"ask": ["Edit(calculo/**)"]`);
  - después de un cambio: `python -m pruebas.integridad`. Si cambian los resultados de referencia, cambió el cálculo: se justifica (skill `verificar-calculos`) y, ya revisado, `python -m pruebas.integridad --aprobar`;
  - los commits que lo cambian empiezan con **"CALCULO:"**;
  - lo que adapta los datos del modelo al cálculo vive afuera. Por ejemplo, `interfaz/concreto.py` pasa el refuerzo (en kN y m) a las cantidades `pint` de los diagramas, y sus salidas de tonf a kN.
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
- **GDL por nodo:** [Dx, Dy, Dz, Phix, Phiy, Phiz] (en pantalla, `formato.GDL_PANTALLA`: φx, φy, φz; la consola y el CSV siguen con Phix). **Cargas:** [Fx, Fy, Fz, Mx, My, Mz]. **Fuerzas locales:** [N, Vy, Vz, T, My, Mz] del nodo i y luego del j.
- **Signos:** fuerzas que los nodos ejercen sobre la barra. El orden en K es el orden de creación de los nodos.
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
  - **colores:** la interfaz (íconos, barras, botones) va solo en blanco, negro y grises; el dibujo 3D puede tener color (por ahora, el eje X en rojo);
  - **colores de la vista:** nodos, barras y apoyos en `colores.ELEMENTO` (gris); al pasar el mouse con Seleccionar, `RESALTADO` (gris oscuro); lo seleccionado, `SELECCIONADO` (negro); sin material o sección, `SIN_ASIGNAR` (gris más claro). Se cambia el color de cada celda (escalares RGB en actores VTK armados a mano en `dibujo._agregar`, porque `add_mesh` copia la malla) y no se dibuja nada encima: así no cambia el tamaño ni parpadea. La previsualización usa el mismo gris con `OPACIDAD_PREVISUALIZACION`;
  - **apoyos** (`interfaz/apoyos.py`): solo empotrado (6 restringidos), apoyo fijo (Dx, Dy, Dz) y libre. Z es la vertical: el cono y la placa van debajo del nodo;
  - **íconos propios** en `iconos.py`: línea negra de 1.5 en una cuadrícula de 24×24, sin relleno; deshabilitados en gris;
  - lo que está activo se sombrea en gris; una acción (como Encuadre) no queda activa;
  - **organización:**
    - arriba, menús con palabras (son categorías): Archivo · Ver · Definir · Configuración; debajo, la barra Definir con íconos;
    - a la izquierda, las herramientas que cambian lo que hace el clic (una activa a la vez) y el Explorador del modelo;
    - a la derecha, Propiedades;
    - los paneles se pueden mover de lado y cerrar (no se desacoplan); se vuelven a abrir desde **Ver**;
    - los árboles usan "+"/"−" con líneas punteadas (`tema.EstiloArbol`, una capa sobre Fusion);
    - abajo, la barra de comandos y, en la barra de estado, la posición del puntero y, a la derecha, cómo se ve el modelo y Encuadre;
    - solo íconos con tooltip mientras el símbolo sea claro;
  - **atajos** como en Civil 3D: F7 rejilla, F9 snap;
  - la cámara la mueve un solo `AnimadorCamara` (cubo y Encuadre): un giro nuevo reemplaza al anterior;
  - lo que pesa, como los diagramas de interacción, se calcula solo cuando el usuario lo pide (Ver 2D y Ver 3D).

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

## Limitaciones actuales del programa (REP 1.8.2 pide conocerlas y documentarlas)

- Análisis elástico lineal de **primer orden**: sin P-Δ.
- **Solo cargas en los nodos**: sin cargas en barras ni diagramas a lo largo de la barra.
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
