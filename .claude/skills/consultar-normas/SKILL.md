---
name: consultar-normas
description: Busca, lee y cita disposiciones del REP 2021, ASCE 7-05 y ACI 318-19 usando las notas de docs/normas/ y los PDF de docs/codigos/. Úsala siempre que haya que citar, aplicar, explicar o comprobar una cláusula, tabla, ecuación o valor de estas normas, en vez de responder de memoria.
---

# Consultar normas

## Qué norma manda (confirmado en el REP 2021)

- **REP 2021** (Res. JTIA 020-2022) rige en Panamá.
- Cargas, combinaciones, sismo y viento: **ASCE/SEI 7-05**, con las modificaciones del REP.
- Concreto: **ACI 318-19** (REP 8.1).

Resumen y mapa de páginas: `docs/normas/indice.md`.

## Orden de búsqueda

1. **Notas del proyecto:** `docs/normas/indice.md` y `docs/normas/etapaN_*.md` (una por etapa de la hoja de ruta). Tienen la cláusula, la fórmula, los límites y la página del PDF.
2. **Texto del PDF**, si hace falta la redacción exacta o algo que no está en las notas.
   - Generar los textos una vez por sesión, en la scratchpad, con los scripts de esta carpeta. Tardan unos 30 s:
     ```
     python .claude/skills/consultar-normas/extraer.py "docs/codigos/ACI 318-19.pdf" <scratchpad>/aci.txt aci
     python .claude/skills/consultar-normas/extraer.py "docs/codigos/ASCE 7-05.pdf" <scratchpad>/asce.txt asce
     ```
     El ACI genera `aci.txt` (código, la columna izquierda) y `aci_comentario.txt` (comentario R…).
   - Buscar:
     ```
     python .claude/skills/consultar-normas/buscar.py <scratchpad>/aci.txt sec 22.5.5.1
     python .claude/skills/consultar-normas/buscar.py <scratchpad>/asce.txt re "Redundancy"
     python .claude/skills/consultar-normas/buscar.py <scratchpad>/aci.txt pag 402 403
     ```
   - Los dos PDF tienen fuentes corridas −29 (`ZKHUH` = `where`). `extraer.py` las decodifica; no uses `pdftotext` directo.
   - El ASCE es un escaneo con OCR: separa números ("1 2.8" = "12.8").
   - Algunos símbolos del ACI salen como otros glifos (`Ȝ` = λ, `ȕ` = β, `Ɛ` = ℓ, `İ` = ε, `ȡ` = ρ, `ȥ` = ψ). En las tablas de combinaciones, `a, i, t, b` = D, L, W, E.
3. **Imagen de la página**, para **tablas, ecuaciones** y todo el **REP 2021**, que es un escaneo sin texto:
   ```
   python .claude/skills/consultar-normas/ver_pagina.py "docs/codigos/REP 2021.pdf" 28 <scratchpad>/rep28.png
   python .claude/skills/consultar-normas/ver_pagina.py "docs/codigos/ASCE 7-05.pdf" 150 <scratchpad>/t.png 1.6 0 0.08 1 0.8
   ```
   Después se lee el PNG con la herramienta de lectura.
   - En el cuerpo del REP, **página impresa N = página PDF N + 14**.
   - Los mapas del REP están en las p. 193–204.

## Cómo citar

`ACI 318-19 §22.5.5.1, Tabla 22.5.5.1 (PDF p. 406)` · `ASCE 7-05 §12.8.6 (PDF p. 159)` · `REP 2021 §5.2.1 (PDF p. 28)`

- Indica siempre la edición y la página del PDF.
- Si el dato viene de las notas y no se volvió a revisar en el PDF, dilo ("según docs/normas/etapa4…").
- Si no se pudo confirmar en el PDF, dilo explícitamente. **No inventes valores de tablas.**

## Cuidados

- Si el REP modifica la norma base, manda el REP:
  - Cs ≥ 0.044·SDS·I ≥ 0.01;
  - V de la Tabla 4.1 del REP;
  - tabiques como carga muerta;
  - W de servicio × 1.6;
  - TL = 10 s.
- **Erratas conocidas del REP:**
  - 5.7 y 5.8 citan una "1.11" que no existe;
  - 5.5 cita el REP-14;
  - 5.12 describe S1 como de "periodos cortos";
  - 8.3 cita los caps. 3 y 5 del ACI 318-19;
  - 8.5 dice "anexo 2" cuando es el Anexo 1.
- **No están en `docs/codigos/`:**
  - ACI 318-14 (DDM y EFM de losas);
  - ANSI/SDI C, AISI S100-2013 y AISC 360-10 (metal deck, acero);
  - ASCE 7-05 en SI.

  Si hace falta algo de ellas, avisa al usuario.
- Los PDF están en unidades inglesas. Si das el equivalente en SI, marca que es una conversión.
