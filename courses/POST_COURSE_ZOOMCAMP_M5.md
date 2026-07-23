# POST-COURSE HANDOFF: LLM Zoomcamp — Módulo 5
# DataTalks.Club — Monitoring (Alexey Grigorev)

> Nota: el módulo enseña monitoring "a mano" (dataclass + Postgres + Streamlit + Grafana), pero
> el homework pide explícitamente resolverlo con **OpenTelemetry** en cambio — instrumentación
> estándar de industria, la misma base que usan Logfire, Langfuse, Arize Phoenix. Por eso esta
> sección traspasa conceptos de OTel, no el stack Postgres/Streamlit/Grafana de las lecciones.

## Contexto

Acabo de terminar el Módulo 5 del LLM Zoomcamp 2026.
Ver ROADMAP.md para el estado completo del repo.

Capas completadas hasta ahora:
- Capa 1 ✅ — Esqueleto del agente (LangGraph)
- Capa 2 ✅ — Tests y CI
- Capa 3A ✅ — Evaluadores a mano
- Capa 3B ✅ — Integración LangSmith (solo en `evals/`, tracing de runtime sigue sin prender — ver auditoría abajo)
- Capa 4 ✅ — Outputs tipados con Pydantic
- Capa 5A ✅ — RAG en memoria (numpy + cosine similarity)
- Capa 5A.2 ✅ — Hybrid search en memoria (TF-IDF + RRF)
- Capa 5B.0/5B.1 ✅ — Infraestructura Supabase + script de ingesta
- Capa 5B.2 ✅ — `rag_search()` migrado a Postgres (pgvector + FTS + RRF real)
- Capa 5B.4 ✅ — Corpus real (11 PDFs instrumentación de campo) + evals de retrieval de M4
  (hit_rate/mrr, barrido de k de RRF, default RRF actualizado a k=1) — completa 6/6, 2026-07-18

Capa en pausa, ahora desbloqueada (HW5 entregado):
- Capa 5B.3 ⬜ — Postgres checkpointer (diseño cerrado 2026-07-07, sin código; pausada desde
  2026-07-09 hasta que se entregara el HW de M5 — ya se entregó, es la siguiente en la cola)
- Sesión 2 de limpieza (paso 6 dead code, tracing real, `tool_calls_used`, `max_tokens`) ⬜ —
  ver auditoría abajo, ahora con una pieza nueva: el patrón de spans/atributos de M5 encaja en
  el mismo trabajo de "prender tracing real"

### Estado del módulo
- HW5 entregado ✓ (resuelto de punta a punta corriendo código real contra OpenAI, excepción
  puntual — no es el flujo normal de trabajo del repo)
- Notebook completa Q1–Q6 ✓ (`M5-lessons/HW5 - Juan Belbey.ipynb`)
- Videos del módulo: vistos ✓ | Apuntes (`M5-lessons/apuntes.md`): completos ✓ | Repaso activo Q1–Q6: hecho ✓

### Respuestas confirmadas (HW5)

| Q | Pregunta | Respuesta |
|---|---|---|
| Q1 | Cantidad de spans que produce un trace (`rag` → `search`, `llm`) | 3 |
| Q2 | Input tokens de una query corta (contexto de 5 docs incluido) | 7000 (7111 medido) |
| Q3 | Duración típica del span `llm` | 500-2000ms (1053-1616ms medido) |
| Q4 | Nombres de span en la tabla SQLite tras instrumentar | `rag`, `search`, `llm` |
| Q5 | Span que más tiempo total consume (excluyendo `rag`) | `llm` (>99% del tiempo) |
| Q6 | Variación de input tokens en 4 corridas de la misma query | 0% — idénticos (7111 las 4 veces) |

---

## Qué vi en el módulo (conceptos clave)

| Concepto | Descripción |
|---|---|
| **Trace / Span / Attributes** | Span = operación con nombre + start/end time + atributos (`set_attribute`). Trace = árbol de spans de una request completa (acá: una llamada a `rag()`). |
| **Processor vs Exporter (separación deliberada)** | Processor decide *cuándo/cómo* entregar (`SimpleSpanProcessor` = síncrono; `BatchSpanProcessor` = en lotes). Exporter decide *a dónde* (consola, SQLite, collector remoto). Separados a propósito: un mismo `provider` acepta varios processors en paralelo → fan-out a múltiples destinos sin que el código que genera spans sepa nada de destinos. |
| **Anidamiento automático de spans** | OTel mantiene un stack de "span actual" (`current span`) en background. Cualquier span que se abre mientras otro sigue activo queda registrado como su hijo automáticamente — no se declara la jerarquía a mano. |
| **Instrumentación vía `super()`** | Patrón: subclase (`RAGTraced(RAGBase)`) overridea cada método, abre un span, y delega la lógica real a `super().metodo(...)`. La instrumentación envuelve el comportamiento heredado sin duplicarlo — si `RAGBase` cambia, `RAGTraced` hereda el cambio sin tocar nada. |
| **`set_tracer_provider` es de una sola vez por proceso** | Llamarlo dos veces con providers distintos se ignora en silencio. "Agregar" un exporter nuevo en la práctica es `provider.add_span_processor(...)` sobre el provider existente, no crear un provider nuevo. |
| **Exporter custom (SQLite)** | Clase que extiende `SpanExporter` con `export(spans)`, `shutdown()`, `force_flush()`. `export()` recibe una lista de `ReadableSpan` y decide cómo persistirlos — acá, un INSERT por span con nombre, timestamps y atributos (tokens, costo). |
| **Determinismo: `search` vs `llm`** | `search` (minsearch, en memoria) es una función pura → mismos `input_tokens` siempre para la misma query. `llm.generate` tiene sampling → `output_tokens` varía entre corridas. Frontera exacta de dónde entra el azar en el pipeline; útil para diagnosticar dashboards de estabilidad. |

### Qué implementé en la notebook (HW5)

- `RAGTraced(RAGBase)`: subclase que envuelve `search()`, `llm()`, `rag()` cada uno en su propio span, delegando la lógica real vía `super()`
- `ConsoleSpanExporter` para ver los spans crudos impresos en consola (Q1–Q3)
- Atributos de tokens (`input_tokens`, `output_tokens`) y costo en el span `llm`, leídos de `response.usage`
- `SQLiteSpanExporter(SpanExporter)` custom: persiste cada span en una tabla `spans` (nombre, timestamps, tokens, costo)
- Dos `SpanProcessor` sobre el mismo `provider` (consola + SQLite en paralelo)
- Queries SQL/pandas sobre `traces.db`: suma de duración por `name` excluyendo `rag` (Q5), comparación de `input_tokens` entre 4 corridas de la misma query (Q6)
- Dependencias agregadas a `pyproject.toml`: `opentelemetry-api`, `opentelemetry-sdk`

---

## Auditoría contra el repo real (no asumido, verificado leyendo el código)

Antes de proponer nada, reviso el estado real de `src/graph.py`, `src/main.py`, `src/tools.py`
y `src/schemas.py` para responder con evidencia, no con suposiciones:

**1. ¿El runtime real (`/chat`) ya tiene algún tipo de tracing prendido?**
No. `grep` de `LANGCHAIN_TRACING_V2`/`LANGCHAIN_PROJECT` en `src/` no devuelve nada — LangSmith
(Capa 3B) sigue integrado únicamente en `evals/evaluators.py` (`@traceable`) y
`evals/run_evals.py`. Este gap ya estaba confirmado en el handoff de M3 y sigue sin resolverse:
sigue anotado en Sesión 2 del ROADMAP, todavía no atacado.

**2. ¿Ya hay algún lugar donde correría un collector (Jaeger/Tempo) en la infra del repo?**
No, y no hace falta todavía. El repo corre local (`uvicorn --reload`) o en Render/Fly.io (H1) —
no hay infra de observabilidad propia desplegada en ningún lado. Meter un collector real hoy
sería infraestructura sin usuario que la necesite.

**3. ¿Tokens y costo ya se trackean en algún lado del repo?**
No. `ChatResponse` (Capa 4, `src/schemas.py`) no tiene campo de tokens ni costo, y
`create_ticket()` solo hace `print()`. Es terreno limpio — el patrón de M5 (tokens/costo como
atributos de span, no como logs sueltos) aplica directo el día que se prenda tracing real, sin
nada que migrar antes.

**4. ¿El repo tiene más de un paso interno por request donde valga la pena planear nombres de span?**
Sí — más que el `rag → search/llm` simple del homework. Un request a `/chat` pasa por
`agent_node` → posible `rag_search()` (que a su vez hace `_vector_search` + `_keyword_search` +
fetch de contenido) → posible `create_ticket()` → vuelta al LLM. Si se instrumenta, vale la pena
nombrar los spans desde el diseño (`agent.rag_search`, `agent.rag_search.vector`,
`agent.rag_search.keyword`, `agent.create_ticket`) en vez de improvisar sobre la marcha.

**5. ¿LangSmith se está quedando corto como para justificar migrar a OTel?**
No hay señal concreta de eso hoy — discutido con Juan en la sesión (2026-07-22), ver ROADMAP
POSPUESTO. LangSmith sigue siendo la elección correcta para este stack (estándar de industria
para LangGraph, ya integrado con `evaluators.py`); una migración a OTel puro solo se justificaría
si el agente creciera con pasos no-LangChain que LangSmith no puede trazar, o si el volumen de
trazas superara el tier gratuito (5.000/mes).

---

## Decisiones tomadas en este handoff

| Decisión | Elección | Razón |
|---|---|---|
| Patrón de spans/atributos de M5 (subclase + `super()`, tokens/costo como atributos) | **Adoptar, dentro de LangSmith** | LangSmith ya soporta atributos custom por span (`@traceable` con metadata). No hace falta el mecanismo OTel crudo del homework para lograr el mismo resultado en este repo — se aplica el *concepto*, no el código de la notebook. |
| `SQLiteSpanExporter` / collector OTel propio | No adoptar ahora | Segunda vía de tracing en paralelo a LangSmith sin necesidad real (auditoría punto 2). Redundante mientras LangSmith cubra el caso. |
| Migrar de LangSmith a OpenTelemetry puro | Posponer (condicional) | Sin señal concreta de que LangSmith se quede corto (auditoría punto 5). Anotado en ROADMAP POSPUESTO con las dos condiciones que lo activarían. |
| Prender tracing real del agente (`LANGCHAIN_TRACING_V2` en runtime) | **Adoptar — ya estaba en cola, confirma prioridad** | Gap confirmado desde M3 (2026-07-06), sigue sin resolver. Momento natural para sumar tokens/costo como atributos del mismo span, ya que se toca el mismo código. |
| LLM-as-judge sobre el corpus nuevo (520 preguntas de `ground_truth_retrieval.json`) | Pendiente aparte, no bloquea nada de acá | No es tema de M5 — detectado al revisar qué evals de generación faltaban (2026-07-22). Ya anotado en ROADMAP POSPUESTO por separado. |

---

## Candidatos para la próxima sesión (orden sugerido)

1. **Capa 5B.3** (Postgres checkpointer) — siguiente en la cola del plan de cierre de Capa 5B,
   diseño ya cerrado (ROADMAP, 4 pasos), desbloqueada ahora que se entregó HW5.
2. **Sesión 2 de limpieza**, con una pieza nueva sumada por este módulo:
   - Prender tracing real (`LANGCHAIN_TRACING_V2`/`LANGCHAIN_PROJECT` para `/chat`, no solo evals)
   - Al mismo tiempo: nombrar spans por paso interno (rag_search, vector/keyword, create_ticket)
     y sumar tokens/costo como atributos — patrón de M5, aplicado vía LangSmith
   - Poblar `ChatResponse.tool_calls_used` (deuda técnica desde Capa 5A)
   - `max_tokens` explícito en `get_bound_llm()` (aprendizaje de M3)
   - Sacar dead code de `build_index()`/`InMemoryIndex` (paso 6, ya no lo usa `rag_search()` desde 5B.2)
3. **LLM-as-judge sobre el corpus nuevo** — aparte, cuando convenga (no depende de 1 ni 2).

Ninguno de estos se implementa todavía en esta sesión — quedan para decidir con Juan cuál se
ataca primero, uno por vez, con explicación antes de código.

---

## Restricciones heredadas (sin cambio)

- `gpt-4o-mini` como modelo por defecto
- No usar Pinecone/Weaviate: el stack es Supabase/pgvector + LangGraph
- LangSmith sigue siendo el tracing elegido para este repo — no migrar a OTel sin una de las dos
  condiciones anotadas en ROADMAP POSPUESTO
- LangSmith debe seguir degradándose silenciosamente si no hay `LANGCHAIN_API_KEY`
- El repo debe poder correrse localmente en cualquier momento con `uvicorn src.main:app --reload`
- No saltar Capa 5B.3 ni la Sesión 2 para adoptar patrones de M5 antes de tiempo

---

*Próximo módulo: M6 — se agrega una sección nueva cuando esté completo.*
