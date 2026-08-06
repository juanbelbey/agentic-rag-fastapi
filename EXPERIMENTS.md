# EXPERIMENTS.md
# Historial de decisiones basadas en datos — agentic-rag-fastapi

Este archivo cuenta, en orden cronológico, cada mejora de calidad (retrieval y
generación) que se probó, midió y decidió con evidencia — no con intuición. Es
la versión "para contar" de lo que `ROADMAP.md`/`CHANGELOG.md` documentan con
todo el detalle técnico. Los números crudos de cada experimento están en
`evals/results/experiments_log.csv` (formato largo: fecha, área, experimento,
variante, métrica, valor) — pensado para alimentar un dashboard o gráfico más
adelante sin tener que releer este archivo a mano.

Convención: cada entrada dice qué se probó, qué se encontró, y qué se decidió
en base a eso. Cuando hay un hallazgo real (bug, sorpresa, dato que contradice
la hipótesis inicial), se marca explícito — es la parte más valiosa para
mostrar en una entrevista.

---

## Retrieval

### 2026-07-18 — Bug real en keyword search (hit_rate 0.008 → 0.300)

**Qué se probó:** portar hit_rate/mrr (patrón M4 de LLM Zoomcamp) a
`evals/retrieval_metrics.py` y correrlo contra las 520 preguntas reales de
`ground_truth_retrieval.json`.

**Qué se encontró:** keyword search prácticamente no funcionaba (hit_rate
0.008 — 4 de cada 500 preguntas). Causa: `plainto_tsquery` arma un AND de
todas las palabras de la pregunta; con preguntas parafraseadas de 15-20
palabras, cumplir el AND completo es casi imposible. Se agravaba porque el
corpus es bilingüe (8/11 PDFs en inglés) y la config `'simple'` no filtra
stopwords en español.

**Qué se decidió:** reescribir el armado de la query — OR a mano
(`_build_or_tsquery`) en vez de AND, más un filtro de stopwords ES/EN
(`_STOPWORDS`) para que el OR no matchee solo por palabras como "de"/"la"/"el".

**Resultado:** hit_rate 0.008 → 0.300, mrr → 0.197 (@top_k=5). El fix toca el
`_keyword_search` real que usa `rag_search()` en producción, no solo las
métricas.

### 2026-07-18 — Barrido de k de RRF (default 60 → 1)

**Qué se probó:** RRF (Reciprocal Rank Fusion) combina vector + keyword con
un parámetro `k` que amortigua diferencias de ranking. Se barrió
k=[1, 50, 60, 100, 200] contra las mismas 520 preguntas.

**Qué se encontró:** k=1 gana en hit_rate y mrr *a la vez* (sin trade-off que
resolver) — 0.3173/0.1858 contra 0.3115/0.1797 del resto. k=50/60/100/200 dan
resultados prácticamente idénticos entre sí: con `candidate_k=10`, un k mucho
mayor que el rango de posiciones aplana las diferencias de rank hasta
volverlas irrelevantes.

**Por qué importa el criterio:** se priorizó hit_rate sobre mrr a propósito —
el agente manda todo el top-k como contexto al LLM, no hay "posición #1" que
importe como en un buscador tradicional de resultados ordenados.

**Qué se decidió:** default de `rrf_k` cambiado de 60 a 1 en `rrf()`
(`src/ingestion.py`) y `_hybrid_search()` (`src/tools.py`) — cambia el
comportamiento real de producción, no solo las métricas.

### 2026-08-03 — Query rewriting: la brecha ES/EN (hit_rate hybrid +31%)

**Qué se probó:** el corpus mezcla español e inglés (8/11 PDFs en inglés);
las preguntas del golden set están en español. Se agregó
`_rewrite_query_impl()` — reescribe la query a inglés técnico con
`gpt-4o-mini` (T=0, `@lru_cache`) antes de armar el tsquery, dentro de
`_keyword_search_impl`. El vector search no lo necesita (el embedding ya es
multilingüe).

**Qué se encontró:** la reescritura no es un parche cosmético — mueve la
aguja en las dos búsquedas que dependen de ella indirectamente (keyword
standalone y hybrid, que usa keyword por dentro).

**Resultado (520 preguntas, sin re-correr el barrido de k — RRF fusiona solo
por ranking, no depende del texto de la query):**
- keyword: hit_rate 0.300 → 0.3288, mrr 0.197 → 0.2368
- hybrid (el que usa `rag_search()` real): hit_rate 0.317 → 0.4154 (**+31%**),
  mrr 0.186 → 0.2197

**Qué se decidió:** query rewriting queda en producción, gateado por
`LANGCHAIN_API_KEY` igual que el resto de la instrumentación opt-in.

### 2026-08-06 — `top_k` de producción (3 → 5)

**Qué se encontró revisando resultados de RAGAS:** `rag_search()` en
producción usaba `top_k=3`, pero las métricas de hit_rate/mrr de arriba se
midieron con `top_k=5` — producción recuperaba *menos* contexto que el
retrieval ya de por sí limitado que se estaba midiendo. Tres preguntas del
golden set (`g002`, `g016`, `g029`) llegaron a `context_precision` **y**
`context_recall` en 0.0 — ninguno de los 3 chunks recuperados era relevante.

**Qué se decidió:** subir el default a `top_k=5` para alinear producción con
lo medido. Ver sección RAGAS abajo para el resultado.

---

## Generación (prompt, modelo, temperatura)

### 2026-07-27 — Primera corrida sobre el corpus real

Primera vez que el LLM-as-judge (`relevance_evaluator`/`accuracy_evaluator`)
corrió sobre las 48 preguntas del golden set de instrumentación (reemplazó al
golden set viejo de LangGraph docs). Resultado: relevancia 4.44/5, accuracy
3.88/5, 85% de respuestas con cita, 4.08 pasos promedio. Quedó un hallazgo sin
investigar: 5/48 preguntas respondibles con el manual terminaban en
`create_ticket` en vez de una respuesta directa — es la semilla del
experimento de prompt de abajo.

### 2026-08-01 — Comparación prompt × modelo (48 casos, luego 56)

**Qué se probó:** 4 combinaciones aisladas (metodología: un solo cambio de
variable por corrida) — prompt baseline vs. uno nuevo (`direct_answer`, que
prioriza responder directo con `rag_search` antes que escalar) × `gpt-4o-mini`
vs. `gpt-4.1-nano`.

**Primera corrida (48 casos, solo preguntas contestables):**

| Variante | Relevancia | Accuracy | Citas | Tickets |
|---|---|---|---|---|
| baseline_mini (producción) | 4.40/5 | 3.60/5 | 81% | 9/48 |
| baseline_nano | 4.90/5 | 4.27/5 | 92% | 0/48 |
| direct_answer_mini | 4.62/5 | 3.94/5 | 94% | 2/48 |
| direct_answer_nano | 4.75/5 | 4.08/5 | 94% | 0/48 |

`gpt-4.1-nano` medía mejor en las 4 dimensiones y ~30% más barato — decisión
obvia, en apariencia.

**El freno:** Juan objetó el criterio — "si me quedo con el modelo que mide
peor solo porque ya lo probamos, no es un criterio, es sesgo". Se extendió el
golden set con 8 casos de escalamiento reales (preguntas que el corpus NO
cubre — el agente debe escalar con `create_ticket`, no inventar) y se
re-corrió con las 56 preguntas + `tool_call_evaluator` nuevo (code-based, no
LLM-judge: mide si escaló o no, no compara texto).

**Segunda corrida (56 casos, con escalamiento):**

| Variante | Relevancia | Accuracy | Citas | Tool-call (escalamiento) |
|---|---|---|---|---|
| baseline_mini | 4.43/5 | 3.69/5 | 77% | 8/8 (100%) |
| baseline_nano | 4.68/5 | 4.12/5 | 84% | 7/8 (88%) |
| **direct_answer_mini** | **4.77/5** | **4.17/5** | 84% | **8/8 (100%)** |
| direct_answer_nano | 4.80/5 | 4.23/5 | 88% | 6/8 (75%) |

**Hallazgo que decidió todo:** nano falló los *mismos* 2 casos de
escalamiento en ambas variantes de prompt — no era ruido, era sistemático
(un transmisor Yokogawa fuera del corpus, un caudalímetro de marca genérica).
En vez de escalar, inventó datos citando "la documentación consultada" para
equipos que el corpus no cubre — justo lo que el `SYSTEM_PROMPT` prohíbe.
`gpt-4o-mini` no falló ni un caso.

**Decisión final: `direct_answer_mini`.** No por costumbre — ventaja medible
y reproducible en la dimensión de mayor riesgo del dominio (no inventar en
zona gris).

### 2026-08-01 — Barrido de temperatura

**La pregunta de Juan, ya con el modelo elegido:** "¿no deberíamos fijar la
temperatura para que invente menos?" — válida: nunca se había fijado
(corría al default implícito de OpenAI, 1.0).

| Temp | Accuracy | Estabilidad (spread) |
|---|---|---|
| 0.0 | 4.00/5 | 0.04 |
| **0.3** | **4.07/5** | **0.10** |
| 0.6 | 4.12/5 | 0.05 |
| 1.0 (default anterior) | 4.03/5 | **0.18** |

**Qué se encontró:** la aparente tendencia "más temperatura = más accuracy"
no se sostiene con comparación pareada — es ruido del LLM-judge sobre 48
preguntas, no una relación causal. Lo único que sí es señal limpia: **T=1.0
es la más inestable de las cuatro**, confirmando la sospecha de que no
fijarla agregaba ruido innecesario.

**Decisión final: `temperature=0.3`** — punto medio entre estabilidad
(spread 0.10, muy por debajo del 0.18 de referencia) y tasa de citas (86%
vs. 78% a T=0.0).

### 2026-08-05 / 2026-08-06 — RAGAS: faithfulness, answer relevancy, context precision/recall

**Qué se probó:** 4 métricas de RAGAS sobre los 48 casos con `expected_answer`
del golden set, con `direct_answer_mini` + T=0.3 ya en producción. `contexts`
tomados de lo que el agente realmente vio (la tool call real a `rag_search`
en la traza), no de una llamada aparte — juzga contra la realidad, no contra
un retrieval hipotético.

**Bugs reales encontrados corriendo el script de punta a punta** (no solo
leyendo la API de RAGAS): el `.score()` sync exige cliente `AsyncOpenAI`, no
`OpenAI`; sin `max_tokens` explícito la salida estructurada de `faithfulness`
se truncaba; el primer `try/except` no cubría el `invoke_agent()` completo y
una corrida se perdió entera por un error transitorio de Postgres a mitad de
una tool call.

**Resultado con `top_k=3` (2026-08-05):** faithfulness 0.783, answer_relevancy
0.708, context_precision 0.571, context_recall 0.679 (46/48 puntuados — 2
casos sin contexts recuperados).

**Lectura:** faithfulness/answer_relevancy (generación) están razonablemente
bien; context_precision/context_recall (retrieval) son las dos métricas
flojas — el LLM responde bien con lo que le dan, el problema es lo que le
dan. Coincide con el hit_rate hybrid ya conocido (0.317-0.415 según la
versión), y con 3 casos (`g002`, `g016`, `g029`) donde ninguno de los 3 chunks
recuperados era relevante.

**Resultado con `top_k=5` (2026-08-06):** faithfulness 0.776, answer_relevancy
0.718, context_precision 0.563, context_recall **0.773** (46/48 puntuados).

| Métrica | top_k=3 | top_k=5 | Δ |
|---|---|---|---|
| faithfulness | 0.783 | 0.776 | -0.007 |
| answer_relevancy | 0.708 | 0.718 | +0.010 |
| context_precision | 0.571 | 0.563 | -0.008 |
| context_recall | 0.679 | **0.773** | **+0.094** |

**Lectura:** el trade-off es el esperable — más contexto recuperado sube la
probabilidad de incluir el chunk correcto (`context_recall` +0.094, ~14%
relativo, la mejora real del experimento) a costa de diluir un poco la
proporción de chunks relevantes sobre el total (`context_precision` -0.008,
dentro de ruido). `faithfulness`/`answer_relevancy` se mantienen
prácticamente planas — el LLM no se confunde por tener 2 chunks más, ni gana
ni pierde ahí. Como `context_recall` era la métrica más floja de las cuatro y
la ganancia es clara mientras que la pérdida en precision es ruido, el cambio
queda como mejora neta. **Decisión: `top_k=5` default en producción.** El
techo real de retrieval sigue estando en `context_precision`/hit_rate — para
subirlo de verdad hace falta reranking, no otro ajuste de `top_k`.

---

## Próximos experimentos candidatos (no ejecutados todavía)

- Reranking (cross-encoder sobre el pool de `candidate_k=10` antes de cortar
  a `top_k`) — ataca la causa de fondo de `context_precision` bajo (RRF
  fusiona por ranking, no por relevancia semántica fina). Más impacto que
  subir `top_k`, pero es un componente nuevo (latencia + costo).
- Revisar granularidad de chunking (`CHUNK_SIZE=1000`/`CHUNK_STEP=800`) —
  chunks grandes pueden diluir la precisión del embedding.
- Sweep de `gpt-4.1-nano` a temperatura baja (0.0/0.3) — anotado en
  `ROADMAP.md`, curiosidad de si su falla de escalamiento es de muestreo o de
  conocimiento del modelo. No cambia la decisión ya tomada salvo resultado
  sorprendente.
