# Etapa 8: Viento

**Qué cubre:**
- velocidad de diseño;
- presión de velocidad;
- coeficientes de presión;
- cargas del sistema principal resistente al viento (SPRV / MWFRS) y sus casos de carga;
- límites de deformación por viento del REP.

**Qué norma manda:**
- **REP 2021 cap. 4 (p. 25–27):** ASCE 7-05 capítulo 6 **sin la Figura 6-1**, con velocidades propias de Panamá.
- **REP 4.2:** V se toma de la **Tabla 4.1**. Son ráfagas de 3 s a 10 m, en exposición C, para regiones **no expuestas a huracanes**:

  | Periodo de retorno | Pacífico | Atlántico |
  |---|---|---|
  | 10 años (aceleraciones de servicio) | 104.0 km/h | 121.0 km/h |
  | 20 años | 113.0 | 133.9 |
  | **50 años (cargas y deformaciones)** | **124.9 km/h = 34.7 m/s** | **150.8 km/h = 41.9 m/s** |
  | 100 años (puentes, AASHTO) | 133.9 | 163.4 |

  - Se permiten valores mayores si se justifican.
  - Las cargas del cap. 6 de ASCE 7-05 son **a nivel de servicio** (p. 26).
  - Para la respuesta en servicio de edificios de concreto o acero con T > 1 s, el amortiguamiento es **≤ 2 %**.
- **REP 4.3 (p. 27), límites de deformación por viento**, con cargas **sin mayorar** y rigidez de servicio:
  - desplazamiento en la parte superior / altura total ≤ **1/400**;
  - deriva de piso / altura del piso ≤ **1/300**;
  - aceleración máxima ≤ **0.2 m/s²**, con el viento de 10 años.
- **REP 8.4 (p. 101):** W de servicio × **1.6** en las combinaciones de ACI 318-19 (§5.3.5). Las combinaciones de ASCE 7-05 ya traen 1.6W y 0.8W.

## ASCE 7-05 cap. 6, procedimiento analítico (Método 2, 6.5, p. 53–58)

| Paso (6.5.3) | Qué es | Valor o regla |
|---|---|---|
| 1 | V y Kd | V de la tabla del REP. **Kd = 0.85** para edificios, SPRV y componentes (Tabla 6-4). Kd **solo** se usa con las combinaciones 2.3 y 2.4 (6.5.4.4). |
| 2 | Importancia I (6.5.5, Tabla 6-1) | Región no huracanada: **0.87** (cat. I), **1.00** (II), **1.15** (III y IV) |
| 3 | Exposición y Kz (6.5.6) | **B:** urbano o suburbano en ≥ 2600 ft (792 m) o 20h a barlovento (1500 ft si h ≤ 30 ft).<br>**C:** todos los demás casos.<br>**D:** terreno plano o agua en ≥ 5000 ft o 20h, y se extiende 600 ft a sotavento.<br>Se evalúan los dos sectores de 45° de cada dirección y se usa el peor; en zonas de transición, la más desfavorable.<br>Kz sale de la Tabla 6-3: Kz = 2.01·(z/zg)^(2/α), con z ≥ 15 ft; α y zg de la Tabla 6-2 (B: 7.0 y 1200 ft; C: 9.5 y 900 ft; D: 11.5 y 700 ft). |
| 4 | Topografía Kzt (6.5.7) | Kzt = (1 + K1·K2·K3)² (Fig. 6-4) en colinas o escarpes aislados que cumplen las 5 condiciones. Si no, **1.0**. |
| 5 | Ráfaga G (6.5.8) | Estructura rígida (n1 ≥ 1 Hz): **G = 0.85** o calculado (Ec. 6-4). Flexible (n1 < 1 Hz): **Gf** (Ec. 6-8), que depende de n1, del amortiguamiento (≤ 2 % según el REP) y de V. |
| 6 | Cerramiento (6.5.9) | Cerrado, parcialmente cerrado o abierto, según las aberturas. |
| 7 | Presión interna GCpi (Fig. 6-5) | Cerrado **±0.18**; parcialmente cerrado ±0.55; abierto 0. |
| 8 | Coeficientes externos Cp (Fig. 6-6) | Muro de barlovento **+0.8**. Sotavento −0.5 (L/B ≤ 1), −0.3 (L/B = 2), −0.2 (L/B ≥ 4). Muros laterales **−0.7**. Techo según θ y h/L. En edificios bajos, GCpf de la Fig. 6-10. |
| 9 | Presión de velocidad (6.5.10) | **qz = 0.00256·Kz·Kzt·Kd·V²·I** (psf, V en mph). En SI: **qz = 0.613·Kz·Kzt·Kd·V²·I** (N/m², V en m/s). |
| 10 | Presión de diseño del SPRV (6.5.12.2.1) | **p = q·G·Cp − qi·(GCpi)**, con q = qz en barlovento y q = qh en sotavento, laterales y techo. |

- **Mínimos (6.1.4):** SPRV ≥ **10 psf (0.48 kN/m²)** por el área proyectada; componentes y revestimientos ≥ 10 psf netos.
- **Casos de carga (6.5.12.3, Fig. 6-9):**
  - (1) presión completa en cada dirección;
  - (2) 75 % con excentricidad de ±15 % del ancho, que genera torsión;
  - (3) 75 % en las dos direcciones a la vez;
  - (4) 56.3 % en las dos direcciones con excentricidad.

  Los porcentajes de la figura no salieron en el texto extraído; son los usuales de ASCE 7-05 y conviene confirmarlos en la figura (p. ~79).
- **Método 1 simplificado (6.4):** solo para edificios regulares, cerrados, con h ≤ 60 ft y otras condiciones.
- **Túnel de viento (6.6):** para formas o respuestas especiales.

## Diferencias o contradicciones encontradas

1. La **Figura 6-1** (mapa de EE.UU.) **no aplica**: V sale de la Tabla 4.1 del REP. Para cargas y deformaciones se usa la de **50 años**, y para aceleraciones la de 10 años.
2. **Dos criterios de deriva distintos:**
   - por **viento**: h/300 en servicio (REP 4.3.2);
   - por **sismo**: Δa de la Tabla 12.12-1 con fuerzas de resistencia × Cd/I (etapa 7).

   El programa debe calcular las dos.
3. **Rigidez para las deformaciones por viento:** servicio, es decir 1.4 × las inercias agrietadas de la Tabla 6.6.3.1.1, sin pasar de Ig (ACI 6.6.3.2.2). Es distinta de la del análisis por resistencia.

## Para el programa (qué implementar y cómo verificarlo)

- **Datos:** región (Pacífico o Atlántico), periodo de retorno, exposición por dirección, Kzt, categoría y dimensiones del edificio (B, L, h por nivel).
- **Cálculo:**
  - Kz(z) y qz por nivel;
  - G (rígido, o flexible con n1 del análisis modal);
  - Cp de barlovento, sotavento y laterales;
  - presión por nivel → fuerzas por piso en X e Y;
  - los 4 casos de la Fig. 6-9, con torsión.
- **Salida:** casos W±x, W±y y los casos con torsión, para las combinaciones (etapa 3).
- **Servicio:**
  - deriva h/300 y desplazamiento H/400 con cargas sin mayorar y rigidez de servicio;
  - aceleración ≤ 0.2 m/s² con el viento de 10 años. Esto requiere un modelo dinámico; fórmulas en el comentario C6 de ASCE 7-05 o en la literatura.
- **Verificaciones:**
  - qz a mano: z = 10 m, exposición C (Kz = 1.00), Kzt = 1, Kd = 0.85, I = 1, V = 34.7 m/s → qz = 0.613 × 0.85 × 34.7² ≈ **627 N/m²**;
  - un ejemplo de la *Guide to the Use of the Wind Load Provisions of ASCE 7-05* (Mehta y Coulbourne).
