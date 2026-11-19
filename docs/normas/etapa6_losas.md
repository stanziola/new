# Etapa 6: Losas (una y dos direcciones, viguetas y metal deck)

**Qué cubre:** espesores mínimos, refuerzo mínimo y separaciones, análisis de losas en dos direcciones, punzonamiento, sistemas de viguetas (nervadas) y losas sobre lámina de acero (metal deck).

**Qué norma manda:**
- Concreto: ACI 318-19 (REP 8.1).
- **Metal deck:** la lámina es acero formado en frío, que el REP 9.2 manda diseñar con **AISI S100-2013**. La losa **compuesta** no la cubre el ACI (1.4.10); la norma de práctica es **ANSI/SDI C** (Steel Deck Institute). Las vigas compuestas se diseñan con **AISC 360-10**, capítulo I (REP 9.1). **Ninguna de estas tres normas está en `docs/codigos/`.**

## Losas en una dirección: ACI cap. 7 (p. 91–100)

| Cláusula | Qué dice |
|---|---|
| 7.1.1 | Abarca losas macizas, losas sobre metal deck **no compuesto** (la lámina solo como encofrado, 1.4.5), losas compuestas de concreto y alveolares pretensadas. |
| Tabla 7.3.1.1 (p. 92) | **Espesor mínimo** (concreto normal, fy = 60 ksi): simplemente apoyada **ℓ/20**; un extremo continuo **ℓ/24**; ambos continuos **ℓ/28**; voladizo **ℓ/10**. Con otro fy se multiplica por (0.4 + fy/100 000). Si no cumple, se calculan deflexiones (24.2). |
| 7.3.3.1 | Debe quedar **controlada por tracción**. |
| 7.4.2–7.4.3 | Mu en la cara del apoyo; Vu a una distancia d (mismas condiciones que en vigas). |
| 7.5.2.3 | Si la losa trabaja como ala de una viga T con el refuerzo principal paralelo a la viga, hace falta refuerzo superior perpendicular, diseñado como voladizo. |
| **7.6.1.1** (p. 94) | **As,min = 0.0018·Ag**. |
| 7.6.3.1 | Av,min solo donde Vu > φ·Vc. |
| 7.6.4 / 24.4 | Refuerzo de **retracción y temperatura**: 0.0018·Ag, en la dirección perpendicular. |
| **7.7.2.3** (p. 97) | Separación máxima del refuerzo de flexión: el menor de **3h y 18 in**. |

Para analizar losas continuas sirve el método simplificado de 6.5 (Tabla 6.5.2, ver etapa 2), si se cumplen sus condiciones.

## Losas en dos direcciones: ACI cap. 8 (p. 101–128)

- **8.3.1.1 (p. 103)**, losas **sin vigas interiores** y relación de luces ≤ 2. Espesor mínimo de la Tabla 8.3.1.1, con fy = 60 ksi:

  | | Paneles exteriores sin viga de borde | Paneles exteriores con viga de borde | Paneles interiores |
  |---|---|---|---|
  | Sin ábacos | **ℓn/30** | ℓn/33 | ℓn/33 |
  | Con ábacos | ℓn/33 | ℓn/36 | ℓn/36 |

  Además, **h ≥ 5 in** sin ábacos y **4 in** con ábacos. La fila "con ábacos" no salió en el texto extraído; son los valores usuales del ACI.
- **Tabla 8.3.1.2**, losas **con vigas** en los cuatro lados:
  - αfm ≤ 0.2: aplica 8.3.1.1;
  - 0.2 < αfm ≤ 2.0: h ≥ el mayor de ℓn(0.8 + fy/200 000)/(36 + 5β(αfm − 0.2)) y 5 in;
  - αfm > 2.0: h ≥ el mayor de ℓn(0.8 + fy/200 000)/(36 + 9β) y 3.5 in;
  - en bordes discontinuos: viga de borde con αf ≥ 0.80, o +10 % de espesor (8.3.1.2.1).
- **8.6.1.1 (p. 112):** As,min = 0.0018·Ag cerca de la cara en tracción, en cada dirección.
- **8.7.2.2 (p. 116):** separación máxima: el menor de **2h y 18 in** en secciones críticas, y de 3h y 18 in en el resto.
- **Análisis para gravedad, R6.2.4.1 (comentario p. 70):** los métodos **directo (DDM) y del pórtico equivalente (EFM) se eliminaron del ACI 318-19**. Se pueden seguir usando como estaban en el **ACI 318-14** (8.10 y 8.11). El 318-19 también permite análisis elástico lineal (6.6) y elementos finitos (6.9). La franja de columna se define en 8.4.1.5.
- **Punzonamiento, 22.6 (p. 413–421):**
  - sección crítica a **d/2** de la cara de la columna (22.6.4.1);
  - **Tabla 22.6.5.2:** vc = el menor de **4·λs·λ√f'c**, (2 + 4/β)·λs·λ√f'c y (2 + αs·d/bo)·λs·λ√f'c;
  - λs = √(2/(1 + d/10)) ≤ 1 es el **factor de tamaño, nuevo en el 318-19 también para losas**;
  - αs = 40 en columnas interiores, 30 en borde y 20 en esquina; β es la relación de lados de la columna.
- **18.4.5 (p. 298):** si una losa sin vigas forma parte del sistema sísmico (pórtico intermedio), hay requisitos de refuerzo en la franja de columna.

## Viguetas (losas nervadas): ACI 9.8 (una dirección, p. 153) y 8.8 (dos direcciones, p. 127)

| Requisito (9.8.1.x / 8.8.1.x) | Valor |
|---|---|
| Ancho de nervio | ≥ **4 in** en cualquier punto |
| Altura del nervio | ≤ **3.5 ×** el ancho mínimo del nervio |
| Separación libre entre nervios | ≤ **30 in** |
| Cortante | Vc se puede tomar como **1.1 ×** el de 22.5 |
| Integridad | Al menos **una barra inferior** continua en cada nervio, o empalmada Clase B o con empalme mecánico |
| Refuerzo perpendicular a los nervios | Por flexión de la losa, con el mínimo de retracción y temperatura |
| Si no cumple los límites | Se diseña como losa y vigas por separado (9.8.1.8 / 8.8.1.8) |
| Rellenos permanentes de arcilla o concreto (9.8.2.1) | Losa sobre el relleno ≥ el mayor de 1/12 de la distancia libre entre nervios y 1.5 in. Para cortante y momento negativo se pueden contar las paredes verticales del relleno. |
| **Encofrado removible u otros rellenos (9.8.3.1, p. 154)** | **Losa ≥ el mayor de 1/12 de la distancia libre entre nervios y 2 in** (la de las viguetas coladas en sitio) |

Confirmado en el PDF (noviembre de 2026, p. 153–154): 9.8.1.2 a 9.8.1.8, 9.8.2.1 y 9.8.3.1. "Overall depth of ribs" (9.8.1.3) no está definida: el programa usa la altura del nervio bajo la losa, h − hf, como el SMath del usuario.

### Lo que usa el programa para la vigueta (confirmado en el PDF)

| Tema | Cláusula (página del PDF) |
|---|---|
| Ancho efectivo: a cada lado el menor de 8h, sw/2 y ℓn/8; de un lado, 6h, sw/2 y ℓn/12 | Tabla 6.3.2.1 (p. 75) |
| Patrón de viva: M+ con L en el claro y los alternos; M− con L en los dos vecinos | §6.4.2 (p. 75) |
| Mu y Vu en la cara de un apoyo monolítico; Vu a d solo si se cumplen (a) a (c) | §9.4.2.1, §9.4.3.1 y §9.4.3.2 (p. 132–133) |
| Una viga que llega a otra (apoyo que no comprime el extremo): sección crítica en la cara | figura R9.4.3.2(e) (comentario, p. 134) |
| Altura mínima ℓ/16, ℓ/18.5, ℓ/21 y ℓ/8 (con ℓ, no ℓn), solo si no sostiene elementos que se dañen | §9.3.1.1 y Tabla 9.3.1.1 (p. 130–131) |
| Controlada por tracción: εt ≥ εty + 0.003 | §9.3.3.1 (p. 132) y Tabla 21.2.2 (p. 395) |
| As,min = máx(3√f'c/fy, 200/fy)·bw·d; no hace falta con As ≥ 4/3 del requerido | §9.6.1.2 (p. 137) y §9.6.1.3 (p. 138) |
| Viguetas: Av,min no hace falta si Vu ≤ φVc | Tabla 9.6.3.1 (p. 138) |
| Vc: (a) 2λ√f'c·bw·d con Av ≥ Av,min; (c) 8λsλρw^(1/3)√f'c·bw·d sin él; λs = √(2/(1 + d/10)) ≤ 1; Vc ≤ 5λ√f'c·bw·d | Tabla 22.5.5.1 (p. 406) y §22.5.5.1.1 a .3 (p. 407) |
| Av,min/s = máx(0.75√f'c, 50)·bw/fyt; Vs = Av·fyt·d/s; Vu ≤ φ(Vc + 8√f'c·bw·d) | Tabla 9.6.3.4 (p. 140), Ec. 22.5.8.5.3 (p. 412) y §22.5.1.2 (p. 404) |
| Viguetas: Vc × 1.1; φ = 0.75 en cortante | §9.8.1.5 (p. 153) y Tabla 21.2.1(b) (p. 393) |
| fr = 7.5λ√f'c; Mcr = fr·Ig/yt; Ie de la Tabla 24.2.3.5 (con Ma del nivel de carga) | §19.2.3.1 (p. 358), §24.2.3.5 a .7 (p. 459) |
| λΔ = ξ/(1 + 50ρ'); ξ = 1.0, 1.2, 1.4 y 2.0 (3, 6, 12 y 60 meses) | §24.2.4.1.1 a .3 (p. 460) |
| Límites: ℓ/360 (pisos, L inmediata); ℓ/480 (sostiene elementos que se dañan) o ℓ/240 (que no), para lo que ocurre después de colocarlos (lo diferido de lo sostenido + la L inmediata adicional) | Tabla 24.2.2 (p. 458) |
| Apoyo exterior monolítico con viga de borde: Mu = wu·ℓn²/24 (método aproximado) | Tabla 6.5.2 (p. 76) |

## Metal deck

- **ACI 1.4.5 (p. 12):** el ACI **sí** aplica a losas sobre metal deck **no compuesto**: la lámina es solo encofrado y la losa se diseña como concreto reforzado.
- **ACI 1.4.10 (p. 13):** el ACI **no** aplica a losas **compuestas** sobre metal deck, salvo al concreto y a las partes diseñadas como concreto reforzado (por ejemplo, el refuerzo negativo sobre los apoyos). R1.4.10 remite a la norma **SDI C**, "Standard for Composite Steel Floor Deck-Slabs".
- En Panamá: la lámina como miembro de acero formado en frío va con **AISI S100-2013** (REP 9.2); la viga de acero compuesta con conectores, con **AISC 360-10**, capítulo I (REP 9.1).
- Datos del fabricante: tablas de carga admisible de la lámina (sin apuntalar y compuesta), propiedades de la sección y luces sin apuntalar.

## Diferencias o contradicciones encontradas

1. **DDM y EFM:** no están en el ACI 318-19. Si se quieren usar para losas en dos direcciones, hace falta el ACI 318-14 o un libro.
2. **Metal deck compuesto:** no lo cubren las normas de `docs/codigos/`. Hacen falta SDI C, AISI S100-2013 y AISC 360-10 (las dos últimas las cita el REP), además del catálogo del fabricante.
3. **"Viguetas":** si se refiere a viguetas **pretensadas prefabricadas con bloques** (vigueta y bovedilla), son sistemas de fabricante: llevan las disposiciones de concreto pretensado del ACI más las tablas del fabricante. El REP 7.5 trata la aprobación de sistemas alternativos (en el capítulo de vivienda). Respondido (noviembre de 2026): el usuario usa viguetas **nervadas coladas en sitio**, en una dirección (§9.8).
4. **Vc de viguetas sin estribos** (noviembre de 2026): con el ACI 318-19, sin Av,min, Vc es la ecuación (c) de la Tabla 22.5.5.1, con el factor de tamaño λs y ρw^(1/3). En la vigueta de la tarea (1 #6, d = 41 cm) da unas 0.58 veces el clásico 2√f'c·bw·d. El ×1.1 de §9.8.1.5 se aplica a cualquiera de las dos.

## Para el programa (qué implementar y cómo verificarlo)

- **Losa en una dirección:** espesor mínimo, momentos (6.5 o análisis), As, separaciones, As,min y retracción y temperatura. Se verifica como una viga de 1 m (o 12 in) de ancho.
- **Losa en dos direcciones:** espesor mínimo (8.3.1.1 y 8.3.1.2), punzonamiento (22.6) y método de análisis (DDM del 318-14 o modelo de elementos o franjas).
- **Viguetas:** límites de 9.8.1, la vigueta como viga T (ancho de ala, 6.3.2) y Vc × 1.1. **Hecho** (noviembre de 2026): `calculo/diseno/viga.py`, `modelo/losas.py` y `modelo/diseno_vigueta.py`.
- **Carga de la losa a las vigas** (áreas tributarias) para el modelo 3D. Conecta con la etapa 2.
- **Verificaciones:**
  - losa de 4 m con ambos extremos continuos: h ≥ 4000/28 = 143 mm;
  - punzonamiento en una columna interior de 40×40 con d = 0.15 m: bo = 4(400 + 150) = 2200 mm, y comparar las tres expresiones de vc;
  - nervios: 4 in de ancho, ≤ 14 in de altura y ≤ 30 in de separación libre.
