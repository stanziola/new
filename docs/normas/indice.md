# Índice de normas: ACI 318-19, ASCE 7-05 y REP 2021

Los PDF están en `codigos/`. Todas las páginas de este índice son **páginas del PDF** (las que muestra el visor), no las impresas en el documento.
Las notas por tema están en los archivos `etapaN_*.md` de esta carpeta.

## 1. Qué norma manda

| Tema | Norma que aplica en Panamá | Dónde lo dice el REP 2021 |
|---|---|---|
| Todo el diseño estructural | **REP 2021** (Res. JTIA 020-2022, Gaceta Oficial 29594-A del 5/8/2022; vigente desde el 30/4/2023) | Res. p. 1–2 |
| Requisitos generales, categorías de ocupación | ASCE/SEI 7-05 cap. 1 (excepto 1.8, OSHA) | REP 1.3, p. 15 |
| Cargas y su base | "de manera particular al **ASCE/SEI 7-05**" | Introducción, p. 5 |
| Combinaciones de carga | ASCE 7-05 cap. 2 | REP 1.4.1, p. 16; 9.4, p. 103 |
| Cargas muertas y vivas | ASCE 7-05 cap. 3 y 4 (+ tabiques del REP 2.1) | REP 2.1–2.2, p. 23 |
| Viento | ASCE 7-05 cap. 6, **sin** la Fig. 6-1: velocidades de la Tabla 4.1 del REP | REP 4, p. 25–27 |
| Sismo | ASCE 7-05 cap. 11–23 + cortante basal mínimo del REP + mapas del REP | REP 5, p. 28–32 |
| Concreto | **ACI 318-19** | REP 8.1, p. 100 |
| Acero | AISC 360-10, AISC 341-10, AISC 358-10, AWS D1.1:2020 | REP 9.1, p. 102 |
| Acero formado en frío (incluye lámina de metal deck) | AISI S100-2013 | REP 9.2, p. 103 |
| Fuego | ASCE/SEI 29-05 | REP 8.2 y 9.3 |
| Cargas durante la construcción | SEI/ASCE 37-02 | REP 1.4.7, p. 17 |

**Regla:** el REP manda donde modifica a la norma base. Por ejemplo, viento a nivel de servicio por 1.6 (REP 8.4 → ACI 5.3.5), Cs mínimo (REP 5.2.1) y tabiques como carga muerta (REP 2.1).

**Conclusión del estudio:** la combinación ACI 318-19 + ASCE 7-05 que usa el proyecto **es la correcta** para el REP 2021.

## 2. Cómo buscar en cada PDF

- **ACI 318-19** (628 p.) y **ASCE 7-05** (419 p.) tienen texto, pero muchas fuentes están "corridas" −29 posiciones y salen ilegibles: `ZKHUH` = `where`. El ASCE además es un escaneo con OCR ("1 2.8" = "12.8"). Para extraerlos legibles se usan los scripts de la skill `consultar-normas` (`.claude/skills/consultar-normas/`).
- En el ACI, la columna izquierda de cada página es el **código** y la derecha el **comentario** (secciones R…).
- **REP 2021** (204 p.) es un escaneo de la Gaceta sin texto. Para leerlo, se convierte la página a imagen (`pypdfium2`) y se lee la imagen. En el cuerpo del reglamento, **página impresa N = página PDF N + 14**.

## 3. Mapa del REP 2021

| Parte | Páginas PDF |
|---|---|
| Resolución JTIA 020-2022 | 1–2 |
| Portada, comité, introducción (novedades respecto al REP 2014) | 3–6 |
| Índice | 7–14 |
| Cap. 1 Requisitos generales | 15–22 |
| — 1.4 Cargas de diseño (combinaciones, gravedad, agua, viento, sismo, suelo, construcción) | 16–17 |
| — 1.5 Diseño estructural (qué norma por material) | 17–18 |
| — 1.6.4 Paredes y fachadas; 1.6.5 no estructurales (ASCE 7-05 cap. 13); 1.7 calidad (Apéndice 11A) | 19 |
| — **1.8 Análisis y diseño mediante computadoras** | 20–21 |
| — 1.10 Diseño basado en desempeño | 22 |
| Cap. 2 Cargas de gravedad | 23 |
| Cap. 3 Presión hidrostática, inundación y lluvia | 24 |
| Cap. 4 Viento (Tabla 4.1, límites de deformación) | 25–27 |
| Cap. 5 Sismo (5.2.1 Cs mínimo; 5.12 mapas; 5.13 TL) | 28–32 |
| Cap. 6 Geotecnia | 33–64 |
| Cap. 7 Vivienda unifamiliar | 65–99 |
| Cap. 8 Concreto estructural | 100–101 |
| Cap. 9 Acero | 102–103 |
| Cap. 10 Madera / 11 Mampostería / 12 Aluminio / 13 Compuestos | 104–111 |
| Cap. 14 Infraestructura / 15 Remodelación | 112–124 |
| Anexos (lista) | 125 |
| Anexo 1: Diseño sísmico basado en desempeño (DSBD) | 126–145 |
| Anexo 2: Manual de diseño de puentes | 146–192 |
| Anexo 3: Mapas S1 (hojas 5, 6, 14, 15) | 193–196 |
| Anexo 3: Mapas Ss (hojas 5, 6, 14, 15) | 197–200 |
| Anexo 3: Mapas PGA (hojas 5, 6, 14, 15) | 201–204 |

La Gaceta solo trae 4 de las 36 hojas de mapas. El juego completo está en la JTIA (REP 5.12). La hoja 14 llega al oeste de la ciudad de Panamá (Ancón, Bella Vista, San Francisco).

## 4. Mapa del ACI 318-19 (secciones que usa la hoja de ruta)

| Capítulo / sección | p. PDF |
|---|---|
| 2.2 Notación / 2.3 Terminología | 17 / 33 |
| 4 Requisitos del sistema estructural | 53 |
| **5.3 Factores de carga y combinaciones** | 64 |
| **6 Análisis estructural**: 6.3 hipótesis de modelo, 6.4 disposición de carga viva, 6.6 análisis lineal de 1.er orden, 6.7 de 2.º orden | 69, 74, 75, 77, 86 |
| 7 Losas en una dirección | 91 |
| 8 Losas en dos direcciones (8.8 nervadas en dos direcciones) | 101 (127) |
| **9 Vigas**: 9.3 límites, 9.5 resistencia, 9.6 límites de refuerzo, 9.7 detallado, 9.8 viguetas en una dirección | 129, 130, 135, 137, 141, 153 |
| **10 Columnas**: 10.6 límites de refuerzo, 10.7 detallado (estribos) | 157, 160, 160 |
| 15 Nudos viga-columna | 213 |
| **18 Estructuras sismorresistentes**: 18.3 pórticos ordinarios, 18.4 intermedios, 18.6–18.8 vigas, columnas y nudos especiales | 287, 293, 294, 301–316 |
| **19.2 Propiedades de diseño del concreto** | 357 |
| **20.2 Barras de refuerzo** | 373 |
| **21.2 Factores φ** | 393 |
| **22 Resistencia de secciones**: 22.2 hipótesis, 22.3 flexión, 22.4 axial y flexo-compresión, 22.5 cortante, 22.6 punzonamiento, 22.7 torsión | 399, 399, 401, 402, 403, 413, 422 |
| 24 Servicio (24.2 deflexiones, 24.3 fisuración, 24.4 retracción y temperatura) | 457 |
| 25 Detallado (25.2 separación, 25.3 ganchos, 25.4 desarrollo, 25.5 empalmes, **25.7 refuerzo transversal**) | 469, 471, 473, 490, 496 |

El índice completo del ACI (247 marcadores) se puede regenerar con los scripts de la skill `consultar-normas`.

## 5. Mapa del ASCE 7-05

| Capítulo / sección | p. PDF |
|---|---|
| 1 General (1.5 categoría de ocupación, Tabla 1-1) | 30–33 |
| **2 Combinaciones** (2.3 resistencia, 2.4 esfuerzos admisibles) | 34–35 |
| 3 Carga muerta | 36 |
| **4 Carga viva** (4.2.2 tabiques p. 38; Tabla 4-1 p. 41–42; Tabla 4-2 KLL p. 42) | 38–43 |
| 5 Inundación | 44 |
| **6 Viento** (6.4 método simplificado p. 52; 6.5 analítico p. 54–57) | 50–109 |
| 7 Nieve (no aplica en Panamá) | 110 |
| **11 Criterios sísmicos** (11.4 aceleraciones, 11.5 importancia, 11.6 CDS) | 138–147 |
| **12 Sismo en edificios** (Tabla 12.2-1 R, Cd, Ω0 p. 149–151; 12.3.4 ρ p. 154; 12.4 efectos y combinaciones p. 155; **12.8 fuerza lateral equivalente** p. 158–160; **12.12 deriva**, Tabla 12.12-1 p. 163) | 148–171 |
| 13 Componentes no estructurales | 172 |
| 20–23 Clasificación de sitio, espectros específicos y mapas de EE.UU. (los mapas no aplican: se usan los del REP) | ~236–260 |
| Comentario (C2.3 p. 284, C4 p. ~298, C6 p. ~310) | ~280–419 |
