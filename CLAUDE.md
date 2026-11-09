# Programa de análisis y diseño estructural 3D

Programa en Python para analizar pórticos 3D por el método de rigidez y, por etapas, diseñar sus elementos de concreto con las normas que rigen en Panamá. El usuario lo está construyendo mientras aprende (POO, análisis matricial, normas), así que se le explica el porqué de las cosas.

## Qué ofrece hoy

| Parte | Qué hace | Dónde |
|---|---|---|
| Modelo | Nodos, materiales (E, G), secciones (A, Iy, Iz, J) y barras, con validaciones; apoyos y cargas **nodales**; modificar y eliminar | `calculo/modelo.py` |
| Elemento | Matriz de rigidez local 12×12 de barra 3D (Euler-Bernoulli), ángulos α, β y γ, rotación R = A(α)·B(β)·C(γ) y transformación | `calculo/elemento.py` |
| Ensamble y análisis | K global, vector F, solución K·U = F con apoyos, reacciones, fuerzas en los extremos de cada barra (ejes locales) y detección de mecanismo | `calculo/ensamble.py`, `calculo/analisis.py` |
| Salida | Ver matrices con etiquetas de GDL (o guardarlas en CSV para Excel) e imprimir el modelo y los resultados | `salida/consola.py` |
| Interfaz 3D | Ventana PySide6 + PyVista: barras, nodos, apoyos, números de nodo y rejilla de piso; rotar, zoom y desplazar | `interfaz/ventana.py`, `interfaz/dibujo.py` |
| — Cubo de vistas | Arriba a la derecha, como el de Civil 3D: blanco plano (sin iluminación), sin letras ni aro. Gira con la cámara. Al pasar el mouse se sombrea en gris la cara, arista o esquina (la esquina completa, sus 3 parches). Clic = giro animado (~0.35 s, slerp de cuaterniones) hasta la vista desde ese lado (26 vistas) | `interfaz/cubo_vistas.py`, `interfaz/animacion.py`, `interfaz/camara.py` |
| — Panel de herramientas | Barra a la izquierda, solo íconos. **Seleccionar** (flecha de contorno) es la herramienta por defecto | `interfaz/ventana.py`, `interfaz/iconos.py` |
| — Barra inferior | A la derecha de la barra de estado. **Rejilla** (F7): rejilla de piso con paso 1-2-5 automático, que no cuenta para el encuadre. **Snap** (F9): deshabilitado hasta que exista la herramienta de dibujo. **Etiquetas**: números de nodo. **Encuadre**: ajusta la vista al modelo con el mismo giro del cubo | `interfaz/ventana.py`, `interfaz/dibujo.py` |
| — Selección | Clic sobre un nodo o una barra: se resalta en naranja y sus datos salen en la barra de estado. Clic en el vacío deselecciona. Arrastrar rota | `interfaz/seleccion.py` |
| Estilo y tema | Colores, tamaños, tolerancias y la "personalización base" (valores por defecto que el usuario podrá cambiar más adelante). Tema en blanco y negro: estilo Fusion, paleta en grises y hoja de estilo. Íconos vectoriales propios | `interfaz/estilo.py`, `interfaz/tema.py`, `interfaz/iconos.py` |
| Ejemplo | Pórtico 3D de 5 nodos y 4 barras | `ejemplos/portico.py` |
| Pruebas | Simetría de K, traslación rígida, equilibrio, voladizo e inestabilidad | `pruebas/verificacion.py` |
| Diagramas de interacción | Columna rectangular 2D, circular 2D y rectangular biaxial 3D (con ventana tkinter). Usan ACI 318-19 y `pint`. Son scripts sueltos: todavía no están conectados al modelo | `iteracion2drect.py`, `iteracion2dcir.py`, `iteracion3drect.py` |
| Combinaciones (borrador) | Imprime las combinaciones de resistencia de ASCE 7-05 (incompletas: falta Lr) | `combinacionescarga.py` |

## Cómo ejecutar (desde la raíz)

- `python main.py`: abre la interfaz con el pórtico de ejemplo.
- `python -m pruebas.verificacion`: corre las comprobaciones. Escribe `K_global.csv`, que git ignora.
- `python iteracion3drect.py`: diagrama de interacción biaxial con ventana. Los otros dos `iteracion*.py` muestran el gráfico directamente.

**Dependencias:** las de `requirements.txt` (numpy, pandas, PySide6, pyvista, pyvistaqt). Los `iteracion*.py` además usan **`pint` y `matplotlib`, que no están en `requirements.txt`**.

## Estructura

```
calculo/        modelo, elemento, ensamble, análisis (no depende de la interfaz)
interfaz/       ventana PySide6 + PyVista, cubo de vistas, animación de cámara, selección, íconos, tema y estilo
salida/         impresión en consola y CSV
ejemplos/       modelos de prueba
pruebas/        comprobaciones automáticas
docs/codigos/   PDF de ACI 318-19, ASCE 7-05 y REP 2021
docs/normas/    notas de normas por etapa (cláusula, fórmula y página del PDF) + índice
docs/plan_de_estudio.md   hoja de ruta, plan de estudio, verificaciones y hallazgos
.claude/skills/ revisar-pedido, verificar-calculos, consultar-normas (con scripts para leer los PDF)
configuracion.py          configurar() (salida en UTF-8 y formato de numpy y pandas), tolerancias y etiquetas
main.py                   punto de entrada
```

## Convenciones (no cambiarlas sin decidirlo con el usuario)

- **Unidades:** el análisis no fija unidades, solo hace falta que sean coherentes. El ejemplo usa **kN y m** (E y G en kN/m²). Los diagramas de interacción usan `pint`: entrada en cm, ksi y número de barra; salida en tonf y tonf·m.
- **Orientación de barras:**
  - R = A(α)·B(β)·C(γ), estilo Mathcad;
  - γ = atan2(dy, dx);
  - β = −atan2(dz, √(dx² + dy²)), negativo por el signo de la matriz B;
  - α es el giro de la sección, que el usuario da **en grados**; se guarda en grados y se pasa a radianes en el ensamble.
- **Orden de los nodos de una barra** (`Modelo._ordenar`): de abajo hacia arriba; si es horizontal, hacia +x; si no, hacia +y. Se reordena al mover un nodo.
- **IDs:** empiezan en 1 y **no se reutilizan** (`_sig_id`).
- **GDL por nodo:** [Dx, Dy, Dz, Phix, Phiy, Phiz]. **Cargas:** [Fx, Fy, Fz, Mx, My, Mz]. **Fuerzas locales:** [N, Vy, Vz, T, My, Mz] del nodo i y luego del j.
- **Signos:** fuerzas que los nodos ejercen sobre la barra. El orden en K es el orden de creación de los nodos.
- **Tolerancias:** en `configuracion.py`. **Estilo:** en `interfaz/estilo.py`.
- **Interfaz:**
  - un clic es presionar y soltar con menos de `TOL_CLIC_PX` de movimiento;
  - en la selección, los nodos tienen prioridad sobre las barras (tolerancia `TOL_SELECCION_PX`);
  - el cubo usa su propio `vtkOrientationMarkerWidget`, porque `add_orientation_widget` de PyVista borraría los ejes de `add_axes`;
  - **colores:** la interfaz (íconos, barras, botones) va solo en blanco, negro y grises; el dibujo 3D puede tener color;
  - **íconos propios** en `iconos.py`: línea negra de 1.5 en una cuadrícula de 24×24, sin relleno; deshabilitados en gris;
  - lo que está activo se sombrea en gris; una acción (como Encuadre) no queda activa;
  - **organización:** a la izquierda, las herramientas que cambian lo que hace el clic (una activa a la vez); abajo a la derecha, cómo se ve el modelo y Encuadre. Solo íconos con tooltip mientras el símbolo sea claro;
  - **atajos** como en Civil 3D: F7 rejilla, F9 snap;
  - la cámara la mueve un solo `AnimadorCamara` (cubo y Encuadre): un giro nuevo reemplaza al anterior.

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
- La inestabilidad se detecta con cond(Kll) > 1e12, un criterio que depende de las unidades.
- Los diagramas de interacción son scripts aparte. Los hallazgos pendientes de revisión (β1, columna con espiral, barras #14/#18, cuantía en pórtico especial) están en `docs/plan_de_estudio.md`.

## Cómo trabajar en este proyecto (instrucciones para Claude)

- Responder en **español**.
- **Al empezar cada pedido, usar la skill `revisar-pedido`.** El usuario quiere que en todo lo que diga se busquen contradicciones (con las normas, con el código y sus convenciones, con la hoja de ruta) y formas mejores de hacerlo. La respuesta va breve, al inicio.
- Todo cálculo, fórmula o resultado: skill **`verificar-calculos`**. Toda cita de norma: skill **`consultar-normas`**. Nunca citar de memoria sin comprobar.
- **No escribir ni modificar código sin un pedido explícito.** Frases como "vamos con…" significan conversar. Ante la duda, preguntar.
- **Al agregar botones o funciones**, sugerir:
  - dónde van (organización);
  - si llevan ícono, palabra o ambos;
  - qué parámetros conviene que el usuario configure. Los valores base quedan en `estilo.py` ("personalización base") o en `configuracion.py`; más adelante irán a un botón de Configuración.
- **Commits:** no ejecutarlos. Dar el comando listo para pegar en PowerShell, en una línea:

  `git add .` y luego `git commit -m "Asunto" -m "- punto 1`n- punto 2"`

  No usar comillas dobles ni backticks dentro del texto del mensaje.
- Explicar el porqué con ejemplos. El usuario estudia POO y análisis estructural mientras construye el programa.
