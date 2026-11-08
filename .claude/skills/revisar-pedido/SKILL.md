---
name: revisar-pedido
description: Revisa cada pedido, idea o afirmación del usuario en este proyecto estructural buscando contradicciones (con REP 2021, ASCE 7-05 y ACI 318-19, con el código existente y sus convenciones, con la hoja de ruta y con decisiones anteriores) y formas mejores o más simples de hacerlo. Úsala al inicio de cada pedido del usuario, antes de planear, responder o implementar.
---

# Revisar el pedido

El usuario pidió explícitamente que, **cada vez que diga algo**, se busquen **contradicciones** y **mejores formas** de hacer lo que hace. Está aprendiendo, y esto es parte de su estudio.

## Qué revisar

1. **Normas y ediciones.**
   - ¿Lo pedido cumple el REP 2021, ASCE 7-05 o ACI 318-19, según corresponda?
   - ¿Mezcla ediciones? Por ejemplo, una fórmula del ACI 318-14 o del ASCE 7-10/16, o viento de resistencia con las combinaciones de 1.6W.
   - ¿Llama a una norma por otro nombre? Por ejemplo, dice "ACI" cuando la sección es del ASCE.

   Para confirmar, usa la skill `consultar-normas`.
2. **El código y sus convenciones** (ver `CLAUDE.md`):
   - unidades: el análisis en kN y m; los diagramas en in y ksi con pint;
   - ángulos α, β y γ;
   - orden de los nodos de una barra (de abajo hacia arriba, hacia +x o hacia +y);
   - IDs desde 1 que no se reutilizan;
   - orden de los GDL y de las fuerzas locales;
   - signos (fuerzas que los nodos ejercen sobre la barra).

   ¿Lo pedido choca con algo que ya existe o lo duplica?
3. **La hoja de ruta** (`docs/plan_de_estudio.md`): ¿lo pedido necesita algo de una etapa que todavía no está? Por ejemplo, diseñar vigas sin cargas en barras ni combinaciones, o calcular la deriva sin cargas laterales.
4. **Decisiones anteriores:** lo que dicen `CLAUDE.md`, el plan, las notas de normas y la memoria. Si el pedido cambia una decisión, avisa cuál.
5. **Hallazgos pendientes:** si lo pedido toca un hallazgo de `docs/plan_de_estudio.md` (por ejemplo, el β1 con 2.5 ksi o la φ de espiral), recuérdalo.

## Mejores formas

- ¿Hay una forma más simple, más estándar o más fácil de verificar?
- ¿Una librería ya lo hace (numpy, scipy, pyvista, pint)?
- ¿Hay una práctica de ingeniería mejor (diseño por capacidad en SMF, envolventes, secciones agrietadas)?
- ¿Conviene una prueba antes de implementar?
- Propón la alternativa con su ventaja concreta, sin imponerla.

## Cómo responder

- Al inicio, una lista **corta** con tres apartados (solo lo que aplique):
  - **Contradicciones:** qué choca, con qué y dónde (cláusula y página, o archivo y línea).
  - **Mejoras:** la alternativa y por qué.
  - **Preguntas:** solo las que cambian lo que se va a hacer.
- Si no hay nada relevante, **no rellenes**: una línea, o nada.
- Después sigue con lo que el usuario decida. **No escribas ni modifiques código sin que lo pida explícitamente.** Ante frases ambiguas ("vamos con…"), pregunta.
- No bloquees pedidos triviales con revisiones largas.
