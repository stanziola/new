---
name: verificar-calculos
description: Verifica fórmulas, cálculos y resultados numéricos del programa de análisis y diseño estructural (análisis matricial, diagramas de interacción, diseño ACI 318-19, cargas ASCE 7-05 y REP 2021). Úsala siempre que se escriba, revise o explique un cálculo, una fórmula, un resultado o un módulo de cálculo de este proyecto, y antes de afirmar que algo "da bien".
---

# Verificar cálculos

El REP 2021 1.8.2 (p. 20–21) exige usar solo programas cuya validez esté verificada y **verificar los resultados con programas independientes o con métodos aproximados**. Esta skill es la forma de hacerlo en el proyecto.

## Procedimiento (en este orden)

1. **Fuente.** Identifica la norma, la edición, la cláusula, la ecuación o tabla y la página del PDF.
   - Usa la skill `consultar-normas`. **No cites de memoria.**
   - Comprueba que la edición sea la que aplica: **REP 2021 → ASCE 7-05 y ACI 318-19**. Si el REP modifica algo, manda el REP.
   - Ojo con las fórmulas de otras ediciones (318-14, ASCE 7-10/16), que cambiaron:
     - Vc con ρw^(1/3);
     - Av,min desde φλ√f'c·bw·d;
     - Ie de Bischoff;
     - ψg;
     - vigas controladas por tracción;
     - viento de servicio (×1.6) frente a viento de resistencia (×1.0).
2. **Unidades.** Haz el análisis dimensional de cada término.
   - El ACI de `docs/codigos/` está en psi e in; las constantes con raíces (√f'c) **no son adimensionales**: 57 000√f'c solo vale en psi y 4700√f'c en MPa.
   - El análisis del programa usa kN y m. Los `iteracion*.py` usan `pint` con in, ksi y tonf.
   - Comprueba todas las conversiones (1 ksi = 6.895 MPa, 1 in = 25.4 mm, 1 kip = 4.448 kN, 1 tonf = 9.807 kN).
3. **Rango de validez.** ¿Se cumplen las condiciones de la fórmula? Por ejemplo:
   - el método 6.5 exige L ≤ 3D y tramos parecidos;
   - KLL·AT ≥ 37.16 m²;
   - f'c ≥ 2500 psi;
   - fy ≤ 80 ksi;
   - SDS ≤ 0.125 para Ev = 0.

   Revisa también los mínimos y máximos (cuantías, separaciones) y las excepciones.
4. **Coherencia entre normas.** Combinaciones de ASCE 7-05 con resistencias ACI 318-19:
   - W del REP es de servicio → 1.6W;
   - E de ASCE ya es de resistencia → 1.0E;
   - ρ y SDS deben salir del sismo;
   - el tipo de pórtico (OMF, IMF o SMF) cambia los estribos, el cortante y la cuantía.
5. **Comprobación independiente**, al menos una:
   - un cálculo a mano con números redondos;
   - una solución cerrada (viga simple wL²/8, voladizo PL³/3EI, biempotrada wL²/12);
   - un segundo método (por ejemplo el método de coeficientes de ACI 6.5 contra el análisis matricial);
   - un ejemplo resuelto de un libro;
   - otro programa (Ftool, PyNite, spColumn).

   Para el análisis matricial:
   - K simétrica;
   - traslaciones y **rotaciones** rígidas que no generan fuerzas;
   - equilibrio global de fuerzas y momentos;
   - equilibrio de cada barra;
   - simetría del resultado en estructuras simétricas.
6. **Casos borde.** Valores en los límites de cada tramo de una fórmula por tramos (continuidad o saltos que la norma sí tiene), ceros, signos negativos, f'c justo en el límite de β1, y Pu = 0.3·Ag·f'c.
7. **Pruebas automáticas.** Corre `python -m pruebas.verificacion` desde la raíz y propón nuevas comprobaciones para `pruebas/`.
   - **No las agregues ni edites código sin que el usuario lo pida.**
   - Para probar algo puntual sin tocar el proyecto, usa un script en la scratchpad que importe el módulo, con `sys.path` apuntando a la raíz.

## Cómo informar

Una tabla corta, y después la propuesta de corrección (sin aplicarla):

| Qué se revisó | Resultado | Evidencia |
|---|---|---|
| Ec. 22.4.2.2 (ACI 318-19, p. 402) | ✓ | Po a mano = 1 234 kN; programa = 1 234 kN |
| Unidades de `phipnmn` | ✗ | mezcla kip e in con tonf sin convertir el brazo |

Si algo no se pudo verificar, dilo explícitamente. No afirmes que está bien.

## Comprobaciones ya conocidas del proyecto

- `pruebas/verificacion.py`: simetría de K, traslación rígida, equilibrio, voladizo e inestable.
- Hallazgos pendientes, en `docs/plan_de_estudio.md` → "Hallazgos de la revisión".
