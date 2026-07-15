# POST-COURSE HANDOFF: LLM Zoomcamp — Módulo 4
# DataTalks.Club — Evaluation and Monitoring (Alexey Grigorev)

## Contexto

Acabo de terminar el Módulo 4 del LLM Zoomcamp 2026.
Ver ROADMAP.md para el estado completo del repo.

Capas completadas hasta ahora:
- Capa 1 ✅ — Esqueleto del agente (LangGraph)
- Capa 2 ✅ — Tests y CI
- Capa 3A ✅ — Evaluadores a mano
- Capa 3B ✅ — Integración LangSmith
- Capa 4 ✅ — Outputs tipados con Pydantic
- Capa 5A ✅ — RAG en memoria (numpy + cosine similarity)
- Capa 5A.2 ✅ — Hybrid search en memoria (TF-IDF + RRF)
- Capa 5B.0/5B.1 ✅ — Infraestructura Supabase + script de ingesta
- Capa 5B.2 ✅ — `rag_search()` migrado a Postgres (pgvector + FTS + RRF real)

Capa en pausa desde 2026-07-09 (foco en M4, deadline 2026-07-13):
- Capa 5B.3 ⬜ — Postgres checkpointer (diseño cerrado 2026-07-07, sin código)
- Sesión 2 de limpieza (paso 6, tracing real, `tool_calls_used`, `max_tokens`,
  `SYSTEM_PROMPT`) ⬜ — planificada para después de 5B.3, ver ROADMAP.md

### Estado del módulo
- HW4 entregado ✓ | Notebook completa Q1–Q6 ✓ (`M4-lessons/HW4 - Juan Belbey.ipynb`)
- Videos del módulo: pendientes de repaso | Apuntes (`M4-lessons/apuntes.md`): pendientes

### Respuestas confirmadas (HW4)

| Q | Pregunta | Respuesta |
|---|---|---|
| Q1 | Promedio de input tokens generando 5 preguntas/página (3 páginas) | 1400 (1353 medido) |
| Q2 | Primer resultado de `text_search` para la pregunta 0 del ground truth | `01-agentic-rag/lessons/03-rag.md` |
| Q3 | Primer resultado de `vector_search`, misma pregunta | `01-agentic-rag/lessons/01-intro.md` |
| Q4 | Hit Rate de `text_search` sobre las 360 preguntas | 0.76 (0.758 medido) |
| Q5 | MRR de `vector_search` sobre las 360 preguntas | 0.55 (0.549 medido) |
| Q6 | Mejor `k` de RRF por MRR (probado 1/50/100/200) | 1 (0.648 medido) |

---

## Qué vi en el módulo (conceptos clave)

| Concepto | Descripción |
|---|---|
| **Ground truth generado con LLM + structured output** | Por cada página del curso se le pide a un LLM (`llm_structured` + modelo Pydantic `Questions`) que genere 5 preguntas que esa página responde. Cada pregunta queda etiquetada con el `filename` de origen. 72 páginas → 360 preguntas, sin trabajo manual. |
| **Por qué pedir wording distinto al de la página** | Las instrucciones piden explícitamente usar pocas palabras de la página y no copiar su frase. Si el ground truth reusa el vocabulario del texto fuente, la evaluación queda artificialmente fácil y favorece a keyword search de forma injusta. |
| **Hit Rate** | Fracción de preguntas donde el documento correcto aparece en algún lugar de los top-k resultados. Es binario por pregunta (¿apareció o no?); no le importa en qué posición. |
| **MRR (Mean Reciprocal Rank)** | Promedio de `1/posición` del primer acierto. Pondera la posición: acertar en el puesto 1 vale 1.0, en el puesto 5 vale 0.2. Complementa a Hit Rate porque también mide qué tan arriba aparece el acierto. |
| **Evaluación por filename, no por chunk exacto** | El chunking con overlap genera varios chunks por página, así que la relevancia se mide contra el documento de origen (`filename`), no contra el chunk puntual que generó la pregunta. Un resultado cuenta como acierto si viene del archivo correcto, aunque sea otro chunk. |
| **Tuning de `k` en RRF vía medición, no intuición** | El paper de RRF usa `k=60` como default, pero el valor óptimo depende del dataset. Se corrió `evaluate()` con distintos `k` (1, 50, 100, 200) sobre las mismas 360 preguntas y se comparó MRR directamente — mismo patrón de "cambiá un parámetro, volvé a medir" que M2. |
| **Vector search gana a veces, text search gana otras — pero solo agregado importa** | En un caso puntual, `text_search` no encontró la página correcta en el puesto 1 pero `vector_search` sí (semántica vs coincidencia léxica). Agregado sobre las 360 preguntas, sin embargo, `text_search` tuvo mejor Hit Rate (0.76) que `vector_search` (0.73) — un caso suelto no predice el comportamiento agregado, por eso se mide sobre todo el dataset. |

### Qué implementé en la notebook (HW4)

- Generación de preguntas con `llm_structured` + modelo Pydantic `Questions`, para 3 páginas (Q1) — tokens medidos desde `response.usage`
- Carga del ground truth completo (360 preguntas, 72 páginas) desde CSV
- Reconstrucción de `text_search` (`minsearch.Index`) y `vector_search` (`minsearch.VectorSearch`) sobre los mismos 295 chunks de HW2
- `rrf()` + `hybrid_search()` reutilizados de HW2
- `compute_relevance`, `hit_rate`, `mrr`, `evaluate` — el framework de medición completo, aplicable a cualquier función de búsqueda con la firma `(query, num_results)`
- Barrido de `k` en `hybrid_search` (1, 50, 100, 200) comparando MRR

---

## Auditoría contra el repo real (no asumido, verificado leyendo el código)

Antes de proponer nada, reviso el estado real de `evals/golden_set.json`,
`evals/evaluators.py`, `evals/run_evals.py`, `src/ingestion.py` y `src/tools.py`
para responder con evidencia, no con suposiciones:

**1. ¿El repo flagship tiene ya algún dataset de evaluación de retrieval?**
No. `evals/golden_set.json` tiene 20 preguntas escritas a mano por Juan, con
`expected_answer` y `category` — evalúa la *respuesta final* del agente
(`relevance_evaluator`, LLM-as-judge), no si `rag_search()` recuperó el chunk
correcto. No hay ningún campo tipo `filename`/`source` esperado por pregunta
que permita medir Hit Rate o MRR contra el corpus real de `docs/`. El patrón
de M4 (LLM + structured output generando preguntas etiquetadas por documento
fuente) no existe todavía en el repo — habría que construirlo desde cero.

**2. ¿`evals/evaluators.py` mide algo parecido a Hit Rate o MRR?**
No. Los tres evaluadores existentes (`relevance`, `citation`, `convergence`)
son todos a nivel de *respuesta del agente completo* — ninguno mide la calidad
del retrieval en aislado (¿el chunk correcto estuvo entre los top-k que
`rag_search()` devolvió?). Es una capa de medición distinta y complementaria
a la de M4, no una que ya esté cubierta.

**3. ¿El `k=60` de RRF en el repo se probó alguna vez, o quedó en el default?**
Quedó en el default sin medir. `src/ingestion.py:104` (`rrf(..., k: int = 60)`)
usa el valor del paper original, heredado tal cual desde 5A.2 (2026-07-01) y
reutilizado sin cambios en `_hybrid_search()` de `src/tools.py` (5B.2,
2026-07-04). M4 muestra en el propio corpus del curso que el óptimo puede
estar lejos del default (`k=1` ganó por MRR en la notebook) — nunca se corrió
ese mismo experimento contra el corpus de `docs/langgraph-intro.txt`.

**4. ¿Cuál es el corpus real y qué tan grande es?**
Chico: hoy `docs/` tiene un solo archivo (`langgraph-intro.txt`), ingerido en
16 chunks (ver CHANGELOG 2026-07-01). Es significativamente menor que las 72
páginas / 295 chunks del corpus de M4. Con un corpus tan chico, generar 5
preguntas por chunk (no por documento, ya que hay un solo documento) daría un
ground truth utilizable, pero su valor como *gate de regresión* crece en
proporción al corpus — hoy el retorno de construirlo es bajo. Vale más esperar
a que el soporte de PDFs reales (pendiente, ver ROADMAP "POSPUESTO") amplíe
`docs/` antes de invertir en esto.

---

## Decisiones tomadas en este handoff

| Decisión | Elección | Razón |
|---|---|---|
| Framework `evaluate()` / `hit_rate` / `mrr` de M4 | Adoptar cuando el corpus lo justifique | Portable tal cual: está parametrizado por función de búsqueda (`text_search`/`vector_search`/`hybrid_search`), no por implementación puntual. No se construye ahora porque `docs/` tiene un solo documento — bajo retorno todavía. |
| Ground truth generado con LLM (structured output) | Adoptar en el mismo momento que lo anterior | Mismo patrón usado en HW4: reutilizable para cualquier corpus nuevo que se agregue, sin trabajo manual de escritura de preguntas. |
| Medir `k` de RRF contra el corpus real | Posponer junto con lo anterior | Medir `k` sin un ground truth de verdad (Hit Rate/MRR) sería eyeballear resultados sueltos — exactamente lo que M4 enseña a no hacer. Requiere el framework de evaluación primero. |
| Prioridad relativa a 5B.3 y a la Sesión 2 de limpieza | Los patrones de M4 esperan | Nada de esto bloquea Capa 5B.3 (Postgres checkpointer) ni la Sesión 2 ya planificada en ROADMAP. Se hacen los pasos ya en cola primero; los patrones de M4 quedan anotados para cuando el corpus crezca (soporte de PDFs reales). |

---

## Candidatos para cuando el corpus crezca (no ahora)

1. **Generar ground truth con LLM + structured output** sobre el corpus real
   de `docs/`, siguiendo el patrón de HW4 (`Questions` Pydantic model, 5
   preguntas por chunk/documento, etiquetadas por `source`).
2. **Portar `hit_rate` / `mrr` / `evaluate()`** a `evals/` (por ejemplo
   `evals/retrieval_metrics.py`), parametrizado para aceptar `_vector_search`,
   `_keyword_search` y `_hybrid_search` de `src/tools.py` tal como están.
3. **Correr el barrido de `k`** de RRF (1/50/100/200 o similar) contra ese
   ground truth real, y decidir con datos si el `k=60` default de
   `src/ingestion.py:104` se queda o se ajusta.
4. **Usar Hit Rate/MRR como gate de regresión** antes de tocar embeddings,
   chunking o boosts de campo — reemplaza el eyeballeo manual de resultados
   sueltos que es la práctica actual.

Ninguno de estos se implementa todavía — quedan para decidir con Juan cuándo
el corpus de `docs/` deje de ser un solo archivo (ligado al pendiente de
soporte de PDFs reales en `scripts/ingest.py`, ya anotado en ROADMAP).

---

## Restricciones heredadas (sin cambio)

- `gpt-4o-mini` como modelo por defecto
- No usar Pinecone/Weaviate: el stack es Supabase/pgvector + LangGraph
- LangSmith debe seguir degradándose silenciosamente si no hay `LANGCHAIN_API_KEY`
- El repo debe poder correrse localmente en cualquier momento con `uvicorn src.main:app --reload`
- No saltar de Capa 5B.3 ni de la Sesión 2 de limpieza para adoptar los
  candidatos de M4 antes de tiempo — quedan pospuestos hasta que el corpus lo justifique

---

*Próximo módulo: M5 — se agrega una sección nueva cuando esté completo.*
