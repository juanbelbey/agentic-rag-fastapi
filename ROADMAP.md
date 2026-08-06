# ROADMAP.md
# Plan completo de especialización — AI Engineer 2026
# Juan Belbey

## Para qué existe este archivo

Este archivo es la fuente de verdad del proyecto:
qué cursos hice, qué construí con cada uno, qué viene después,
y qué capa del repo flagship corresponde a cada etapa.

Copilot nunca debe improvisar qué viene después. Todo está acá.
Para reglas de comportamiento y estilo de trabajo, ver COPILOT_STRATEGY.md.

---

## El repo flagship: agentic-rag-fastapi

Un sistema de soporte inteligente con RAG sobre PDFs de documentación
técnica (LangGraph docs), agente con LangGraph, y tickets en Postgres.

**Caso de uso:** usuario hace una pregunta → el agente busca en los docs
→ responde con citas → si hace falta, crea un ticket en la base de datos.

**Stack definitivo:**
- Python + FastAPI
- LangGraph (orquestación del agente)
- OpenAI API (gpt-4o-mini por defecto)
- LangSmith (observabilidad y evals) — integrado en Capa 3B ✅
- Supabase (Postgres + pgvector) — se incorpora en Capa 5
- GitHub Actions (CI)
- Deploy: Render/Fly.io (H1) → AWS (H2)

---

## Mapa de capas

```
CAPA 1 — Esqueleto del agente         ✅ COMPLETADA
CAPA 2 — Tests y CI                   ✅ COMPLETADA
CAPA 3 — Observabilidad y evals       ✅ COMPLETADA
  3A — Evaluadores a mano             ✅ COMPLETADA
  3B — Integración LangSmith          ✅ COMPLETADA
CAPA 4 — Outputs tipados con Pydantic ✅ COMPLETADA
CAPA 5 — RAG real con PDFs            ✅ COMPLETADA (2026-07-24)
  5A  — Índice en memoria (numpy)     ✅ COMPLETADA (2026-06-20)
  5A.2 — Hybrid search + RRF          ✅ COMPLETADA (2026-07-01)
  5B  — pgvector/Supabase + FTS       ✅ COMPLETADA (2026-07-24)
    5B.0 — Infraestructura Supabase   ✅ COMPLETADA (2026-07-01)
    5B.1 — Script de ingesta          ✅ COMPLETADA (2026-07-01)
    5B.2 — Migrar rag_search()        ✅ COMPLETADA (2026-07-04)
    5B.3 — Postgres checkpointer      ✅ COMPLETADA (2026-07-24; verificado contra
                                          Supabase real: setup() crea tablas,
                                          persistencia por thread_id confirmada)
    5B.4 — Corpus real + evals M4     ✅ COMPLETADA (2026-07-18; ver CORPUS_INSTRUMENTACION.MD)
CAPA 6 — Deploy en AWS                ← PENDIENTE (H2)
```

Nunca se salta una capa. Nunca se espera terminar todos los cursos
para empezar a construir.

---

## Estado actual del repo

```
src/
├── config.py      ✅ validación temprana de OPENAI_API_KEY
├── state.py       ✅ AgentState con TypedDict + add_messages
├── tools.py       ✅ rag_search() sobre Postgres (5B.2): _get_connection + _vector_search
│                     + _keyword_search + _hybrid_search (RRF) + fetch de content/source por id
│                     + create_ticket() con TicketInput
│                     _keyword_search reescrita en 5B.4 paso 5 (2026-07-18): config 'simple'
│                     (no 'spanish' — corpus mezcla EN/ES) + tsquery armado a mano con OR ('|')
│                     entre palabras vía _build_or_tsquery(), no plainto_tsquery (fuerza AND de
│                     todas las palabras — inviable con preguntas parafraseadas de 15-20 palabras)
│                     + _STOPWORDS (ES+EN) para que el OR no matchee solo por "de"/"la"/"el"
│                     compartidas con la pregunta. Medido contra las 520 preguntas de
│                     evals/ground_truth_retrieval.json: keyword hit_rate 0.008 → 0.300 (ver
│                     CHANGELOG 2026-07-18 para la progresión completa del debugging).
│                     [paso 6 de la Sesión 2, 2026-07-28: sacado el dead code _index/
│                     InMemoryIndex/set_index — ya no los usaba rag_search() desde 5B.2]
│                     _vector_search/_keyword_search instrumentados con @traceable
│                     (LangSmith) — spans agent.rag_search.vector/agent.rag_search.keyword,
│                     gateado por LANGCHAIN_API_KEY (mismo patrón opt-in que
│                     evals/evaluators.py). Sesión 2, tracing real completo y verificado
│                     en LangSmith (2026-07-29) — árbol de spans confirmado: ChatOpenAI
│                     trazado automático por el tracer global, rag_search con
│                     agent.rag_search.vector/agent.rag_search.keyword anidados adentro
│                     como spans hijos.
│                     [2026-08-03, punto 5 del plan de entrega] `_rewrite_query_impl()`
│                     nueva — reescribe la query a ingles tecnico antes de
│                     `_build_or_tsquery`, dentro de `_keyword_search_impl` (no en
│                     `_hybrid_search`: asi `evals/retrieval_metrics.py` mide el impacto
│                     tanto en la fila "keyword" standalone como en "hybrid", que la usa
│                     por dentro). Ataca la brecha ES/EN documentada arriba — el vector
│                     search no la necesita (embedding ya multilingue). LLM `gpt-4o-mini`
│                     `temperature=0` + `prompts/query_rewrite.txt` nuevo (traduce
│                     vocabulario tecnico, no nombres de marca/modelo). `@lru_cache(
│                     maxsize=1024)` — deterministico, evita recomputar las mismas 520
│                     preguntas en cada pasada de retrieval_metrics.py. Mismo patron
│                     `@traceable` opcional que _vector_search/_keyword_search (span
│                     `agent.rag_search.rewrite`). Validado contra las 520 preguntas de
│                     ground_truth_retrieval.json (sin re-correr el barrido de k, ya
│                     cerrado en 5B.4 — rrf() fusiona solo por ranking, no depende del
│                     texto de la query): hit_rate/mrr keyword 0.300/0.197 → 0.3288/0.2368;
│                     hybrid (el que usa rag_search() real) 0.317/0.186 → 0.4154/0.2197
│                     (+31% hit_rate) — mejora sustancial, no marginal. Pendiente de
│                     commitear.
├── graph.py       ✅ StateGraph con routing condicional — SYSTEM_PROMPT con el caso de uso real
│                     (instrumentación de campo, agua potable/saneamiento) desde 5B.4 paso 3
│                     (2026-07-15). Desde 5B.3 paso 2 (2026-07-23) exporta `graph_builder` SIN
│                     compilar (antes compilaba con MemorySaver a nivel de módulo) — cada
│                     consumidor decide su propio checkpointer llamando `.compile()`
│                     `get_bound_llm()` con `max_tokens=800` explícito (Sesión 2, 2026-07-29
│                     — aprendizaje de M3: sin techo, resúmenes largos escalan ~2.3x en tokens
│                     de output; 800 alcanza de sobra para una respuesta técnica con cita)
│                     [2026-08-01, punto 4] Refactorizado para comparar prompts/modelos sin
│                     romper nada que ya importa `graph_builder`: `SYSTEM_PROMPT` ya NO vive
│                     inline (resuelve el pendiente de POSPUESTO del 2026-07-15) — se lee con
│                     `load_prompt("system_prompt.txt")` nuevo desde `prompts/` (directorio
│                     nuevo en la raíz). `build_agent_node(system_prompt, model_name)` (closure
│                     factory) y `build_graph(system_prompt=SYSTEM_PROMPT, model_name=MODEL_NAME)`
│                     nuevos — `graph_builder = build_graph()` al final mantiene exactamente el
│                     mismo objeto/comportamiento que antes para `main.py`/`conftest.py`.
│                     [2026-08-01, noche] `temperature` explicito nuevo en `get_bound_llm()`/
│                     `build_agent_node()`/`build_graph()` (default `1.0` — el default implicito
│                     de OpenAI que ya regia sin fijarse en ningun lado, asi que no cambia
│                     comportamiento existente). Motivado por una duda real de Juan: dos corridas
│                     identicas de compare_prompts.py dieron accuracy distinta solo por la
│                     aleatoriedad del muestreo (temperatura nunca fijada). [2026-08-03]
│                     Decision final de produccion APLICADA: `TEMPERATURE = 0.3` (constante
│                     nueva, mismo patron que `MODEL_NAME`) y `SYSTEM_PROMPT = load_prompt(
│                     "system_prompt_direct_answer.txt")` (antes `system_prompt.txt`).
│                     `graph_builder = build_graph()` ya usa los defaults nuevos. Tests
│                     verificados en verde (7/7) antes de commitear. Commit `8fabcf6`.
├── main.py        ✅ FastAPI POST /chat
│                     [paso 6 de la Sesión 2, 2026-07-28: sacado build_index()/DOCS_DIR —
│                     el lifespan ya no re-embebe docs.txt con la API de OpenAI en cada
│                     arranque para nada; de paso, docs/ ya ni tiene .txt desde 5B.4 (solo
│                     pdfs/), así que el bloque tampoco encontraba qué indexar]
│                     load_dotenv() movido al principio del archivo, antes de
│                     `from src.graph import graph_builder` (2026-07-28, mismo paso de
│                     tracing): ese import dispara `import src.tools`, que evalúa
│                     `LANGCHAIN_API_KEY` a nivel de módulo — sin este orden, la
│                     instrumentación de tools.py quedaba desactivada en producción aunque
│                     la key estuviera en .env (load_settings() antes corría recién dentro
│                     de lifespan, demasiado tarde)
│                     Desde 5B.3 paso 3 (2026-07-23): el lifespan abre un `psycopg_pool.ConnectionPool`
│                     real a Postgres (autocommit=True, prepare_threshold=0 — ver nota abajo),
│                     corre `checkpointer.setup()` (idempotente, crea tablas de PostgresSaver) y
│                     recien ahi compila `graph_builder.compile(checkpointer=...)`, guardado en
│                     variable global `graph`. Pool se cierra despues del `yield`. `/chat` valida
│                     `graph is None` ademas de `settings is None`.
│                     Verificado contra Supabase real (2026-07-24): `checkpointer.setup()` crea
│                     las 4 tablas (checkpoints/checkpoint_blobs/checkpoint_writes/
│                     checkpoint_migrations) y dos `graph.invoke()` con el mismo thread_id
│                     confirman persistencia real de la conversación (script manual fuera del
│                     repo, no vive en scripts/).
│                     `ChatResponse.tool_calls_used` poblado de verdad (Sesión 2, 2026-07-29
│                     — antes siempre devolvía `[]`, deuda técnica desde Capa 5A): recorre
│                     `result["messages"]` después de `graph.invoke()` y junta los
│                     `.tool_calls[].name` de los `AIMessage` que llamaron una tool, sin
│                     duplicados.
│                     [punto 3 del plan de entrega, 2026-07-31 noche] `run_id` generado con
│                     `uuid.uuid4()` ANTES de `graph.invoke()` y pasado por `config["run_id"]`
│                     (LangSmith usa ese UUID para el trace en vez de generar el suyo),
│                     devuelto en `ChatResponse.run_id` — necesario para asociar feedback a
│                     una conversación puntual con `client.create_feedback()`. `lifespan`
│                     también crea la tabla `feedback` (idempotente, mismo patrón que
│                     `checkpointer.setup()`) sobre el mismo pool `psycopg_pool` del
│                     checkpointer — verificado contra Supabase real.
│                     [2026-08-01, cierra punto 3] Ruta `POST /feedback` nueva: valida con
│                     `FeedbackInput`, hace `INSERT` a la tabla `feedback` sobre el pool
│                     existente, y manda `client.create_feedback(run_id, key="user_score",
│                     score, comment)` a LangSmith si `langsmith_client` está seteado (mismo
│                     patrón opt-in por `LANGCHAIN_API_KEY` que `tools.py`, fail-silent con
│                     try/except si LangSmith falla). Verificado end-to-end: `POST /chat` real
│                     → `run_id` real → `POST /feedback` con ese `run_id` → confirmado en
│                     Postgres (`SELECT`) y en LangSmith (`client.list_feedback(run_ids=...)`
│                     devuelve `key="user_score"` con el score/comment correctos). Commit
│                     `2810fb4`.
├── schemas.py     ✅ ChatRequest, ChatResponse, TicketInput, RAGResult (Capa 4)
│                     [2026-07-31 noche] `ChatResponse.run_id: str` nuevo — ver detalle en
│                     main.py abajo (punto 3 del plan de entrega, feedback de usuario)
│                     [2026-08-01] `FeedbackInput` nuevo: `run_id`, `thread_id`, `score`
│                     (float 0.0-1.0, 1.0=pulgar arriba), `comment` opcional. Commit `2810fb4`.
│                     [Sesión 2, 2026-07-29] `TicketInput.category` redominado: las 4
│                     categorías genéricas de soporte de software (bug/feature/question/other,
│                     herencia de la Capa 1) reemplazadas por 4 del dominio real de
│                     instrumentación de campo (field_instrument_failure/
│                     biological_process_anomaly/pump_maintenance/undocumented_query), tomadas
│                     del borrador ya existente en CORPUS_INSTRUMENTACION.MD y traducidas a
│                     inglés para seguir la convención del resto del Literal (low/medium/high).
│                     `RAGResult.score`: sacado el `le=1.0` y corregida la descripción a "score
│                     de fusión RRF" — decía "similitud coseno" pero `rag_search()` le pasa el
│                     score de RRF (Reciprocal Rank Fusion), que no tiene el mismo techo fijo;
│                     con `rrf_k=1` el máximo daba 1.0 "por casualidad", frágil ante un cambio
│                     futuro de `rrf_k`.
└── ingestion.py   ✅ chunking (chunk_text) + embeddings OpenAI (embed_texts() batchea de a 300
                      textos por request, límite de la API de OpenAI: 300k tokens / 2048 items por
                      request, tocado 5B.4 paso 2) + rrf() (fusión RRF, Capa 5A.2 — el algoritmo
                      quedó, no depende de dónde viven los datos). InMemoryIndex/KeywordIndex/
                      build_index() (Capa 5A, búsqueda en memoria) sacados en el paso 6 de la
                      Sesión 2 (2026-07-28) — código muerto desde que rag_search() migró a
                      Postgres en 5B.2, verificado con git grep que no quedaban referencias.
                      Cliente de OpenAI (_client) se crea recién en embed_texts(), no al importar el
                      módulo (fix 2026-07-15) — antes exigía OPENAI_API_KEY solo con importar
                      src.graph/src.tools, tumbaba el job rules de CI

scripts/
└── ingest.py      ✅ ingesta manual: docs/pdfs/*.pdf → chunks → embeddings → tabla chunks en Supabase
                      (Capa 5B.1, extendido 5B.4 paso 2). _read_pdf() nuevo (pypdf, sin OCR) +
                      CHUNK_SIZE=1000/CHUNK_STEP=800 locales al script (no toca el default 500/250 de
                      src/ingestion.py:chunk_text()). Corrida real contra Supabase el 2026-07-14:
                      2451 chunks / 11 documentos insertados, verificado con SELECT COUNT(*).

docs/
└── pdfs/                 ✅ 11 PDFs de instrumentación de campo (Capa 5B.4 paso 1, 2026-07-14) —
                             5 Emerson/Rosemount, 4 Siemens/Sitrans, 2 Endress+Hauser, gitignored
                             (ver CORPUS_INSTRUMENTACION.MD)

archive/
└── langgraph-intro.txt  ✅ movido fuera de docs/ (2026-07-14, git mv) — ya no se ingesta con
                             el corpus real; scripts/ingest.py e InMemoryIndex (src/main.py) solo
                             leen docs/*.txt, docs/ ahora solo tiene pdfs/

tests/
├── conftest.py    ✅ fixtures: agent_graph, sample_responses, invoke_agent. Desde 5B.3 paso 4
│                     (2026-07-23): agent_graph importa `graph_builder` (sin compilar) y compila
│                     con `MemorySaver()` en la fixture — no depende de Postgres para correr
├── test_rules.py  ✅ 7 tests — 5 deterministas sin API; los 2 de rag_search pegan a Postgres+OpenAI
│                     reales desde 5B.2 y se saltan con pytest.skip si falta OPENAI_API_KEY/
│                     DATABASE_URL (fix 2026-07-15, mismo patrón que invoke_agent en conftest.py)
├── test_evals.py  ✅ LLM-as-judge usando evaluators.py compartido
└── reports/       ✅ pytest-html local + artefacto en CI

evals/
├── golden_set.json           ✅ (2026-07-27) 48 preguntas sobre el corpus real de instrumentación
│                                 (12 por categoría: factual/procedimental/inferencial/borde), con
│                                 expected_answer generada por LLM grounded en los chunks reales —
│                                 evals/generate_golden_set.py. Reemplaza las 20 preguntas viejas
│                                 sobre LangGraph docs (corpus que ya no existe en Supabase).
│                                 [2026-08-01, noche] +8 casos hand-crafted (g049-g056, total 56) —
│                                 categoria nueva "escalamiento", 2 por cada categoria de
│                                 TicketInput (field_instrument_failure/biological_process_anomaly/
│                                 pump_maintenance/undocumented_query). A diferencia de los 48
│                                 originales (sampleados de ground_truth_retrieval.json + expected_
│                                 answer generada por LLM), estos son escritos a mano y usan
│                                 expected_tool="create_ticket" en vez de expected_answer — no hay
│                                 texto de referencia con el que comparar, lo que importa es si el
│                                 agente decide escalar (ver tool_call_evaluator en evaluators.py).
├── generate_ground_truth.py  ✅ (5B.4 paso 4, 2026-07-17) genera ground truth de retrieval:
│                                 samplea 1 anclaje cada 20 chunks por documento (equiespaciado),
│                                 ventana de 2 chunks consecutivos por anclaje, LLM + structured
│                                 output (client.beta.chat.completions.parse, patron HW4) genera
│                                 preguntas factual/procedimental/inferencial/borde por ventana.
│                                 Script manual (python -m evals.generate_ground_truth), no lo
│                                 llama la app ni CI — mismo patron que scripts/ingest.py.
│                                 [hallazgo sin resolver: las 130 ventanas generaron exactamente
│                                 4 preguntas cada una pese a que el prompt pedia "1 a 4, solo las
│                                 categorias que el fragmento sostiene" — muestreo manual de la
│                                 primera ventana no mostro preguntas forzadas, pero no se reviso
│                                 el resto; vigilar si esto genera ruido en hit_rate/mrr del paso 5]
├── ground_truth_retrieval.json ✅ (5B.4 paso 4, 2026-07-17) salida real de generate_ground_truth.py
│                                 contra Supabase+OpenAI: 520 preguntas (factual 138, procedimental
│                                 133, inferencial 128, borde 121) sobre 130 ventanas / 11 documentos.
│                                 Cada registro: question, category, chunk_ids (lista — 1 elemento
│                                 para ventanas de 1 chunk al final de un documento, 2 en el resto),
│                                 source. Commiteado 2026-07-18 (commit 15bf4bd).
├── generate_golden_set.py   ✅ (2026-07-27) genera evals/golden_set.json nuevo: samplea 12
│                                 preguntas por categoría (48 total, seed=42 fijo) de las 520 de
│                                 ground_truth_retrieval.json, trae el contenido real de sus
│                                 chunk_ids desde Supabase, y le pide al LLM que escriba la
│                                 expected_answer grounded en ese texto — no inventa preguntas
│                                 nuevas, reusa el mapeo pregunta→chunk ya verificado en 5B.4.
│                                 Distinto de generate_ground_truth.py: aquel mide retrieval
│                                 (hit_rate/mrr), este arma la referencia para medir generación
│                                 (accuracy_evaluator, ver evaluators.py abajo). Script manual
│                                 (python -m evals.generate_golden_set), no lo llama la app ni CI.
├── retrieval_metrics.py ✅ (5B.4 pasos 5-6, 2026-07-18) compute_relevance/hit_rate/mrr/evaluate,
│                            patron de M4 portado y parametrizado para _vector_search/
│                            _keyword_search/_hybrid_search de src/tools.py. Acierto definido por
│                            chunk_ids (no filename, a diferencia de M4 — ver nota del paso 4).
│                            Script manual (python -m evals.retrieval_metrics), no lo llama la app
│                            ni CI. Corrida real contra las 520 preguntas destapó y motivo el fix
│                            de _keyword_search en src/tools.py (ver "Estado actual del repo"
│                            arriba y CHANGELOG 2026-07-18 para la progresion completa). Tambien
│                            corre el barrido de k de RRF (RRF_K_VALUES) para el paso 6.
│                            Metricas finales @top_k=5, k=1 (default nuevo, ver src/ingestion.py):
│                            vector 0.231/0.141, keyword 0.300/0.197, hybrid 0.317/0.186
│                            (hit_rate/mrr) — hybrid ahora supera a los dos individuales en ambas
│                            metricas, sin trade-off.
├── evaluators.py    ✅ relevance (LLM-judge, sin referencia — juzga la respuesta en el vacío),
│                       accuracy (LLM-judge, nuevo 2026-07-27 — compara la respuesta del agente
│                       contra expected_answer del golden set; complementario a relevance, no
│                       lo reemplaza: relevance sigue siendo el único que sirve para casos sin
│                       referencia, ej. el flujo de create_ticket en test_evals.py), citation
│                       (code), convergence (code) + @traceable para LangSmith (Capa 3B)
│                       [2026-08-01, noche] `tool_call_evaluator(trace, expected_tool)` nuevo —
│                       code-based (no LLM-judge), verifica si la tool esperada aparece en la
│                       traza. Distinto de accuracy_evaluator: no compara texto contra una
│                       referencia, verifica una decision estructural (¿escalo o no?), pensado
│                       para los casos de escalamiento nuevos de golden_set.json (ver abajo).
├── run_evals.py     ✅ corre evals, guarda resultados por fecha/hora
│                       + client.create_feedback() para LangSmith (Capa 3B). Desde 5B.3 paso 4
│                       (2026-07-23): importa `graph_builder` y compila con `MemorySaver()` a
│                       nivel de módulo (sin problema, a diferencia de Postgres no abre ninguna
│                       conexión real ni depende de credenciales) — un eval es una corrida de
│                       una sola pasada, no necesita que el checkpoint sobreviva un reinicio.
│                       Desde 2026-07-27: cada caso corre accuracy_evaluator además de
│                       relevance_evaluator, el resumen agrega avg_accuracy, y el feedback a
│                       LangSmith manda las dos keys (relevance/accuracy) en vez de solo una.
│                       [2026-08-01, punto 4] Refactorizado para reusar en comparaciones:
│                       `build_eval_graph(system_prompt, model_name)` nuevo (llama a
│                       `build_graph()` de `src/graph.py`); `invoke_agent`/`evaluate_case` ahora
│                       reciben el `graph` como parámetro en vez de un global fijo;
│                       `run_eval_pass()`/`send_feedback()` extraídos para reusarlos desde
│                       `compare_prompts.py`. `main()` (el que corre CI) sigue con el mismo
│                       comportamiento exacto de antes. **Bug real encontrado y arreglado en el
│                       camino:** `run_id` en `evaluate_case()` siempre daba `None` — intentaba
│                       leerlo de `trace.get("run_id")`, pero `AgentState` nunca tuvo ese campo
│                       (a diferencia de `main.py`, que lo genera antes del invoke). Efecto real:
│                       desde que se armó el envío de feedback a LangSmith (2026-07-27), nunca se
│                       mandó nada — `if ... run_id is None: return` cortaba siempre. Fix:
│                       `invoke_agent()` ahora genera el `run_id` ANTES de invocar (mismo patrón
│                       que `main.py`) y lo devuelve junto al trace. Verificado con
│                       `client.list_feedback(run_ids=[...])`: feedback llega de verdad ahora.
│                       [2026-08-01, noche] `evaluate_case()` ramifica segun el caso: con
│                       `expected_answer` sigue el flujo viejo (accuracy_evaluator contra
│                       referencia); con `expected_tool` usa `tool_call_evaluator` en vez de
│                       comparar texto. `build_summary()` calcula `avg_accuracy`/`tool_call_rate`
│                       por separado (ausentes del summary si no hay casos de ese tipo en la
│                       corrida). `send_feedback()` manda tambien `tool_call` a LangSmith.
│                       `build_eval_graph()` acepta `temperature` explicito (ver src/graph.py).
├── compare_prompts.py ✅ (2026-08-01, punto 4) corre 4 combinaciones prompt x modelo, aisladas
│                       de a una variable por vez: baseline/direct_answer x gpt-4o-mini/
│                       gpt-4.1-nano. Reusa `build_eval_graph`/`run_eval_pass` de `run_evals.py`.
│                       Script manual (`python -m evals.compare_prompts`), no lo llama CI.
│                       Corrida dos veces (2026-08-01): 48 casos primero, 56 casos (con los de
│                       escalamiento nuevos) despues — ver "Actualizacion (2026-08-01, noche)"
│                       mas abajo para el resultado que decide el punto 4.
├── compare_temperature.py ✅ (2026-08-01, noche) sweep de temperatura (0.0/0.3/0.6/1.0, 2
│                       corridas cada una) sobre la combinacion prompt x modelo ganadora, fijada
│                       en el script (`direct_answer` + `gpt-4o-mini`). Reusa
│                       `build_eval_graph`/`run_eval_pass`. Script manual
│                       (`python -m evals.compare_temperature`), no lo llama CI. Primera corrida
│                       en background se cortó sola a los 5/8 (status `killed`, causa
│                       desconocida — no hay nada en el codigo que explique el corte); las 3
│                       corridas faltantes se relanzaron aparte reusando las mismas funciones,
│                       sin repetir las 5 ya guardadas (cada corrida escribe su JSON apenas
│                       termina, nada se perdió).
├── cost_report.py   ✅ (2026-08-01) calcula costo/tokens reales por variante leyendo los traces
│                       de LangSmith asociados a los `run_id` guardados en cada JSON de
│                       resultados (`client.list_runs(run_ids=...)` — `read_run()` uno a uno pega
│                       el rate limit de LangSmith con 48 corridas seguidas). Script manual
│                       (`python -m evals.cost_report <json...>`), no lo llama CI.
├── ragas_eval.py    ✅ (2026-08-05, stretch #1) 4 metricas de RAGAS (`ragas.metrics.collections`:
│                       `Faithfulness`/`AnswerRelevancy`/`ContextPrecision`/`ContextRecall`) sobre
│                       los 48 casos con `expected_answer` de `golden_set.json` (quedan afuera los 8
│                       de escalamiento). `contexts` = contenido real de los chunks que devolvio la
│                       tool call a `rag_search` en la traza (`extract_contexts()`), no una llamada
│                       aparte a `_hybrid_search()` — juzga contra lo que el LLM realmente vio.
│                       Juez `gpt-4o-mini` (`llm_factory`) + `OpenAIEmbeddings` default
│                       (`text-embedding-3-small`, mismo modelo que `embed_texts()` de
│                       `src/ingestion.py`). Script manual (`python -m evals.ragas_eval`), no lo
│                       llama CI. Tres bugs reales encontrados y arreglados corriendolo de punta a
│                       punta: (1) el `.score()` sync de cada metrica llama internamente a
│                       `agenerate()`, que exige cliente async — `AsyncOpenAI`, no `OpenAI`; (2) sin
│                       `max_tokens` explicito, la salida estructurada de `faithfulness` se trunco
│                       (`instructor.v2.core.errors.IncompleteOutputException`) — fijado a 2048; (3)
│                       el primer `try/except` de `evaluate_case()` solo envolvia el scoring de
│                       RAGAS, no el `invoke_agent()` del agente — un `server closed the connection
│                       unexpectedly` real de Postgres a mitad de una tool call tiro abajo toda la
│                       corrida completa (mismo riesgo que dejo `compare_temperature.py` a medio
│                       terminar el 2026-08-01). Ampliado el `try/except` a todo el cuerpo del caso.
└── results/         ✅ JSONs organizados por YYYY-MM-DD/HH-MM-SS
                        (corridas: 2026-05-29, 05-30, 06-01, 06-03, 2026-07-27 — primera corrida
                        real contra el golden set de instrumentación nuevo: 48 casos, relevancia
                        4.44/5, accuracy 3.88/5, 85% con cita, 4.08 pasos promedio. Hallazgo sin
                        investigar: 5/48 preguntas respondibles con el manual terminaron en
                        create_ticket en vez de una respuesta directa — candidato a explicar
                        parte de la brecha relevancia/accuracy)
                        [2026-08-01] Corrida real de `compare_prompts.py` (48 casos x 4
                        variantes) + `cost_report.py`: ver detalle completo en la actualización
                        del 2026-08-01 más abajo (punto 4) — decisión de qué combinación pasa a
                        producción sigue pendiente de confirmar con Juan.
                        [2026-08-01, noche] Segunda corrida de `compare_prompts.py` (56 casos x 4
                        variantes, con los 8 de escalamiento nuevos) + sweep completo de
                        `compare_temperature.py` (4 valores x 2 corridas sobre el ganador) — 15
                        JSONs nuevos en `evals/results/2026-08-01/`. Decisión final tomada, ver
                        "Actualización (2026-08-01, noche)" más abajo.
                        [2026-08-05] Primera corrida real de `ragas_eval.py` sobre los 48 casos de
                        `golden_set.json` (`direct_answer_mini` en producción): 46/48 puntuados (2
                        sin contexts recuperados — `g026`/`g039`, `rag_search` no devolvió
                        resultados para esas preguntas, hallazgo de retrieval, no bug del script).
                        `evals/results/2026-08-05/11-46-58_ragas.json`: faithfulness 0.783,
                        answer_relevancy 0.708, context_precision 0.571, context_recall 0.679.

.github/
└── workflows/
    └── ci.yml     ✅ rules en cada push, evals solo en main (MAX_EVAL_CASES=1)
                      + LANGCHAIN_API_KEY como secret (Capa 3B). ARREGLADO 2026-07-28: job
                      evals ya no falla con RuntimeError "Falta DATABASE_URL". Se creó en
                      Supabase un rol `ci_readonly` (GRANT SELECT únicamente sobre `chunks`,
                      + policy de RLS scopeada a ese rol — la tabla tiene RLS activado sin
                      policies desde 5B.4 paso 2, así que sin la policy el SELECT hubiera
                      devuelto 0 filas en vez de error) y se agregó como secret `DATABASE_URL`
                      en GitHub Actions. Verificado con un script descartable (fuera del repo):
                      SELECT sobre chunks funciona (2451 filas), INSERT bloqueado
                      (permission denied), SELECT sobre checkpoints (tabla fuera de su
                      alcance) también bloqueado. `evals/run_evals.py` compila con
                      MemorySaver (no PostgresSaver) en CI, así que el rol nunca necesita
                      tocar las tablas del checkpointer. Las 2 preguntas hardcodeadas del
                      dominio viejo en tests/test_evals.py (reembolso, ticket de login)
                      reemplazadas por preguntas reales de instrumentación de campo (una
                      factual del golden set para el flujo de rag_search, una de escalado a
                      técnico de planta para el flujo de create_ticket). CI run #17 verde en
                      ambos jobs (commit 1945750) — único warning es la deprecación de
                      Node.js 20 en el runner de GitHub Actions, ajena a este repo.

Dockerfile          ✅ (2026-07-30) nuevo — python:3.12-slim, COPY requirements.txt +
                      pip install antes de COPY src/ (cachea la capa de dependencias),
                      EXPOSE 8000, CMD uvicorn src.main:app --host 0.0.0.0 --port 8000.
                      No copia docs/pdfs/ ni .env (secretos van por --env-file en
                      docker run). Probado 2026-07-31: docker build (~61s, sin errores) +
                      docker run --env-file .env -p 8000:8000 (conectó a Postgres real,
                      checkpointer.setup() corrió, uvicorn arriba) + POST /chat real
                      (pregunta sobre transmisor Rosemount, rag_search encontró el chunk
                      correcto, respuesta con cita de fuente, tool_calls_used poblado).
                      Container detenido y borrado al terminar. Containerization 0→1
                      en la rúbrica.
.dockerignore        ✅ (2026-07-30) nuevo — excluye .venv/, .git/, docs/, tests/,
                      .env, reports/, courses/, scripts/, *.md del contexto de build.

── PRÓXIMO PASO ──
Capa 5B.2 completa (2026-07-04). rag_search() corre 100% sobre Postgres:
1. ✅ _get_connection()
2. ✅ _vector_search(conn, query_embedding, top_k)
3. ✅ _keyword_search(conn, query, top_k)
4. ✅ _hybrid_search(conn, query, query_embedding, top_k, candidate_k=10) — pide 10
   candidatos a cada búsqueda, fusiona con rrf(), corta a top_k (mismo patrón que
   el InMemoryIndex.hybrid_search() de 5A.2).
5. ✅ rag_search() reescrito: abre conexión (try/finally para garantizar close()),
   embebe la query con embed_texts([query])[0], llama _hybrid_search(), trae
   content/source con SELECT ... WHERE id = ANY(ids), y reordena con un diccionario
   {id: (content, source)} recorriendo fused (que ya viene ordenado por RRF) —
   sin eso, Postgres devuelve las filas en su propio orden, no en el de relevancia.
   Verificado contra Supabase real (query "que es langgraph") y con los 7 tests
   de test_rules.py pasando sin cambios.

Capa 5B.3 — Postgres checkpointer (MemorySaver → PostgresSaver). Diseño cerrado
(2026-07-07), código de los 4 pasos completo (2026-07-23) — falta verificar contra
Supabase real antes de dar la capa por cerrada (ver nota abajo):
1. ✅ (2026-07-23) Instalado langgraph-checkpoint-postgres==3.1.0 (trae psycopg v3 +
   psycopg_pool, driver distinto al psycopg2 que ya usa tools.py — conviven a
   propósito, no se migra tools.py). Hallazgo en el camino: `psycopg` puro necesita
   la librería nativa `libpq` instalada en el sistema — no está en este Windows, el
   import fallaba. Se instaló `psycopg[binary]` (wheel autocontenido, mismo motivo
   por el que el proyecto ya usa `psycopg2-binary` y no `psycopg2` a secas).
2. ✅ (2026-07-23) graph.py: ya no compila el grafo a nivel de módulo (antes corría
   al importar, antes de que exista el lifespan). Ahora exporta `graph_builder` sin
   compilar — se sacó el import de MemorySaver del archivo, ya no se usa ahí.
3. ✅ (2026-07-23) main.py: el lifespan abre un `psycopg_pool.ConnectionPool` real
   (kwargs `autocommit=True` — cada operación del checkpointer se confirma sola, sin
   dejar transacciones abiertas; `prepare_threshold=0` — evita prepared statements,
   que pueden fallar si DATABASE_URL pasa por un pooler tipo pgbouncer), llama
   `checkpointer.setup()` (idempotente) y compila `graph_builder.compile(checkpointer=...)`
   ahí adentro, guardado en variable global `graph`. Pool se cierra después del `yield`.
   `/chat` valida `graph is None` además de `settings is None`.
4. ✅ (2026-07-23) tests/conftest.py y evals/run_evals.py ya no importan `graph`
   compilado (ya no existe ese nombre) — importan `graph_builder` y compilan cada
   uno con `MemorySaver()`: conftest.py dentro de la fixture `agent_graph` (lazy, por
   test), run_evals.py a nivel de módulo (sin problema — MemorySaver no abre
   conexión real ni depende de credenciales, a diferencia del Postgres de main.py).
   7 tests de test_rules.py verificados en verde con el fix.

**Verificado contra Supabase real (2026-07-24):** script manual (pool + `setup()` + dos
`graph.invoke()` con el mismo `thread_id`, fuera del repo). `setup()` creó/confirmó las
4 tablas de PostgresSaver. El segundo invoke recordó el dato dado en el primero —
persistencia real confirmada, no solo código que compila.

**Capa 5B.3 completa, 2026-07-24. Capa 5B (pgvector/Supabase + FTS) y Capa 5 (RAG real
con PDFs) quedan completas.**

Capa 5B.4 — Corpus real (instrumentación de campo) + framework de evals de M4.
PRIORIDAD ACTUAL (decidido 2026-07-13). Plan completo en CORPUS_INSTRUMENTACION.MD
(no duplicado acá) — resuelve la decisión pospuesta en el handoff de M4
(courses/POST_COURSE_ZOOMCAMP_M4.md, 2026-07-11): portar hit_rate/mrr/evaluate()
quedaba condicionado a que docs/ dejara de tener un solo archivo. El corpus nuevo
(instrumentación de campo — presión/caudal/temperatura — para agua potable y
saneamiento, 12 PDFs de Emerson/Siemens/Endress+Hauser, justificado por experiencia
real de Juan como consultor técnico en el rubro) es ese salto de volumen. Pasos
(ver detalle en CORPUS_INSTRUMENTACION.MD):
1. ✅ Descargar los PDFs del checklist a carpeta fuente gitignored (2026-07-14).
   Terminaron siendo 11, no 12: los 6 links de Rosemount originales estaban
   rotos (URLs con codificación de caracteres corrupta, HTTP 400/404
   confirmado con curl) — reemplazados por 5 documentos en inglés verificados
   HTTP 200 (Emerson no publica todas las versiones ES); el bonus ES de 3051
   y el ítem "ampliar E+H" quedaron sin bajar. Detalle completo y checklist
   marcado en CORPUS_INSTRUMENTACION.MD. Los 11 PDFs están en docs/pdfs/,
   verificados %PDF válidos, renombrados fabricante_modelo_tipo_idioma.pdf.
2. ✅ (2026-07-14) — scripts/ingest.py extendido con soporte real de PDFs:
   load_documents() ahora también lee docs/pdfs/*.pdf vía _read_pdf() nuevo
   (pypdf.PdfReader, sin OCR — páginas escaneadas sin capa de texto quedan
   vacías). Se agregaron CHUNK_SIZE=1000/CHUNK_STEP=800 (antes 500/250
   default de chunk_text()) — manuales más largos/densos que
   docs/langgraph-intro.txt, con procedimientos y tablas que no conviene
   cortar cada 500 caracteres; el default de src/ingestion.py no se tocó
   (lo comparten Capa 5A en memoria y tests/evals), el ajuste queda local a
   este script. Decisión pypdf vs pdfplumber verificada empíricamente sobre
   páginas con tablas reales (ficha Siemens P320/P420 + manual Rosemount
   2051): texto plano equivalente entre ambas, extracción estructurada de
   tablas de pdfplumber funciona en Rosemount pero falla en Siemens (no
   confiable en todo el corpus) → se descarta pdfplumber, queda pypdf==5.1.0
   en requirements.txt. Evidencia real de headers/footers repetidos por
   página (título del doc + número de página, en Siemens y Rosemount) —
   **decisión tomada: no limpiar por ahora.** Previsualización sin costo
   (chunking de 3 PDFs de muestra sin llamar a embed_texts()) mostró que el
   ruido es 2-3 líneas cortas contra chunks de 1000 caracteres, dilución
   baja; se corre tal cual y se re-evalúa con datos reales de retrieval en
   el paso 6 si hace falta, antes de invertir en un limpiador por fabricante
   (5 formatos de header/footer distintos). docs/langgraph-intro.txt movido
   a archive/ (git mv) para que la ingesta real no lo mezcle con el corpus
   nuevo. Encontrado y arreglado en el camino: embed_texts()
   (src/ingestion.py) mandaba todos los chunks en un solo request — con
   2451 chunks (~626k tokens) supera el límite de la API de OpenAI (300k
   tokens / 2048 items por request); ahora batchea de a 300. **Corrida real
   contra Supabase (2026-07-14):** TRUNCATE + 2451 chunks insertados desde
   los 11 PDFs, verificado con SELECT COUNT(*)/COUNT(DISTINCT source) →
   (2451, 11). De paso, cerrado un hallazgo de seguridad de Supabase: la
   tabla chunks quedó pública vía la API REST (RLS deshabilitado, alerta
   automática de Supabase) — se habilitó `ALTER TABLE chunks ENABLE ROW
   LEVEL SECURITY;` sin policies (el backend conecta por rol directo de
   Postgres, no por la API REST/anon key, así que no se vio afectado),
   verificado con `SELECT relrowsecurity FROM pg_class` → true.
3. ✅ (2026-07-15) — Actualizado el SYSTEM_PROMPT (graph.py) con el caso de uso real:
   soporte técnico de instrumentación de campo para agua potable/saneamiento,
   con instrucción explícita de grounding (usar rag_search antes de responder,
   citar fuente, no inventar datos de calibración/rangos/procedimientos) y de
   cuándo usar create_ticket. README.md reescrito: caso de uso, cómo funciona,
   de dónde sale el corpus (nota de compliance), cómo correrlo.
4. ✅ (2026-07-17) — Generar ground truth con LLM + structured output (patrón HW4 de M4).
   Diseño acordado con Juan antes de programar: la unidad de generación no podía ser "documento
   completo" (11 docs, demasiado grueso — cualquier chunk del documento contaría como acierto en
   Hit Rate) ni "5 preguntas por documento" al estilo de un proyecto anterior de Juan en Valkimia
   (mismo problema de granularidad). Se resolvió con sampling proporcional al tamaño real de cada
   documento: 1 anclaje cada 20 chunks (equiespaciado por chunk_index, no al azar, para cubrir todo
   el manual), ventana de 2 chunks consecutivos por anclaje (cubre procedimientos cortos que cruzan
   un chunk; criterio de "acierto vecino" ±1 justificado por el 20% de overlap real de
   CHUNK_STEP=800/CHUNK_SIZE=1000 — a esa distancia dos chunks ya no comparten texto). El "chunk
   correcto" de cada pregunta queda definido por construcción (los chunk_ids de la ventana que vio
   el LLM), no por una heurística posterior. Se acotó el alcance a 4 categorías que sí alimentan
   Hit Rate/MRR (factual, procedimental, inferencial, borde) — preguntas "no soportadas"
   (out-of-scope) quedan pendientes aparte porque no tienen chunk correcto y sirven para otro tipo
   de eval (nivel agente, no retrieval). `evals/generate_ground_truth.py` corrido contra Supabase +
   OpenAI reales (confirmado con Juan antes de ejecutar, ~130 llamadas pagas): 520 preguntas en
   `evals/ground_truth_retrieval.json`. Detalle y hallazgo pendiente de revisar en "Estado actual
   del repo" arriba.
5. ✅ (2026-07-18) — Portado hit_rate/mrr/evaluate() a evals/retrieval_metrics.py, patrón M4
   parametrizado para _vector_search/_keyword_search/_hybrid_search de src/tools.py (acierto por
   chunk_ids, no filename — ver paso 4). La primera corrida real (top_k=5, 520 preguntas) destapó
   un bug real en _keyword_search: hit_rate 0.008, prácticamente inútil. Investigado y arreglado en
   la misma sesión (dos intentos fallidos antes del fix real — ver CHANGELOG 2026-07-18 para la
   progresión completa): plainto_tsquery armaba un AND de las 15-20 palabras de cada pregunta
   parafraseada (criterio casi imposible de cumplir), agravado por el corpus bilingüe (8/11 PDFs en
   inglés) y por que 'simple' no elimina stopwords españolas. Fix: OR armado a mano
   (_build_or_tsquery) + filtro de stopwords ES/EN (_STOPWORDS) en src/tools.py. Verificado con
   Juan que la brecha ES/EN resultante ya no es un artefacto sino el límite estructural real de
   keyword search monolingüe (ver nota en "Estado actual del repo"); descartada la idea de separar
   en dos RAGs por idioma porque el corpus no tiene cobertura duplicada (8 PDFs solo existen en
   inglés). Métricas finales @top_k=5: vector 0.231/0.141, keyword 0.300/0.197 (supera a vector),
   hybrid 0.312/0.180 (hit_rate mejora, pero MRR queda entre los dos individuales — RRF con k=60
   default no suma toda la ventaja de keyword). El fix cambia también el rag_search() real que usa
   el agente (mismo _keyword_search), no solo las métricas — 7 tests de test_rules.py verificados
   en verde con la query SQL nueva.
6. ✅ (2026-07-18) — Barrido de k de RRF (k=[1,50,60,100,200]) contra las 520 preguntas del ground
   truth, top_k=5. Resultado: k=1 gana en hit_rate (0.3173) y MRR (0.1858) a la vez — sin trade-off
   que resolver con el criterio acordado (priorizar hit_rate: el agente manda todo el top-k al LLM
   como contexto, no hay "posición #1" que importe como en un buscador tradicional). k=50/60/100/200
   dan resultados idénticos entre sí (0.3115/0.1797) — con candidate_k=10, un k mucho mayor que el
   rango de posiciones aplana las diferencias de rank hasta volverlas irrelevantes, no es que 60 sea
   "casi tan bueno" como 100, es que a partir de cierto punto k deja de cambiar el resultado. Default
   actualizado de 60 a 1 en `rrf()` (`src/ingestion.py`) y `_hybrid_search()` (`src/tools.py`,
   parámetro `rrf_k`) — cambia el comportamiento real de `rag_search()` en producción, no solo las
   métricas. 7 tests de `test_rules.py` verificados en verde con el nuevo default.

**Capa 5B.4 completa (6/6 pasos), 2026-07-18.**

Nota (2026-07-15): al pushear el trabajo pendiente de 5B.4 pasos 1-2 (primera vez
que corría CI desde la migración a Postgres de 5B.2), aparecieron dos fallas en
GitHub Actions — ninguna causada por el push en sí, latentes desde antes, recién
visibles porque CI no corría hacía rato (local estaba varios commits adelante de
origin/main):
- Job rules: ImportError al importar src.graph — src/ingestion.py creaba el
  cliente de OpenAI a nivel de módulo (_client = OpenAI()), exigiendo API key
  solo con importar, y ese job corre a propósito sin ninguna. Arreglado con
  cliente perezoso. Efecto secundario encontrado en el camino: 2 tests de
  tests/test_rules.py (test_rag_search_contains_query_word,
  test_rag_search_returns_string) llaman rag_search() de verdad — dejaron de
  ser "deterministas sin API" desde 5B.2 sin que nadie lo notara, porque CI no
  había vuelto a correr. Ahora se saltan con pytest.skip si falta
  OPENAI_API_KEY/DATABASE_URL. Job rules verificado en verde con y sin esas
  env vars (ver detalle en "Estado actual del repo" arriba).
- Job evals: RuntimeError "Falta DATABASE_URL" — sigue roto, a propósito. Ver
  nota en ci.yml arriba. Se destraba con el paso 4 de acá arriba (ground truth
  nuevo + decidir si CI usa una Supabase separada de la real antes de meter esa
  credencial como secret).

── PLAN PARA CERRAR CAPA 5B (definido 2026-07-06, tras repaso M3 Zoomcamp) ──
Ver courses/POST_COURSE_ZOOMCAMP_M3.md para el detalle completo de la auditoría y el
porqué de cada punto. Orden acordado originalmente, uno por sesión — reordenado el
2026-07-13 (ver nota abajo):

Sesión 0 — 5B.4, corpus real + evals de M4. ✅ COMPLETA (2026-07-18, 6/6 pasos —
  ver plan arriba y detalle completo en CORPUS_INSTRUMENTACION.MD).

Sesión 1 — 5B.3 (Postgres checkpointer). ✅ COMPLETA (2026-07-24). Cierra Capa 5B
  formalmente. Diseño cerrado el 2026-07-07, código completo el 2026-07-23, verificado
  contra Supabase real el 2026-07-24 (ver detalle en PRÓXIMO PASO). Nota (2026-07-18):
  esta sesión se había pausado por el
  curso en paralelo (LLM Zoomcamp M5, Monitoring, HW con entrega 2026-07-20).
  Actualización (2026-07-22): HW5 entregado, videos/apuntes de M5 completos (ver
  courses/POST_COURSE_ZOOMCAMP_M5.md) — la pausa ya no aplicaba, por eso se retomó
  5B.3 el 2026-07-23.

Sesión 2 — batch de limpieza y mejoras chicas (todo mecánico, sin conceptos nuevos,
15-45 min cada uno):
- ✅ (2026-07-28) Paso 6: sacado build_index()/set_index()/_index/InMemoryIndex/
  KeywordIndex muerto de src/main.py, src/tools.py y src/ingestion.py (ya no
  alimentaban a rag_search() desde 5B.2). Verificado con git grep (sin referencias
  restantes) y pytest tests/test_rules.py (7/7).
- ✅ (2026-07-28 código, 2026-07-29 verificado) Prender tracing real del agente
  (LANGCHAIN_TRACING_V2 para el runtime de /chat, no solo para evals/ — gap
  encontrado en la auditoría de M3, reconfirmado en la auditoría de M5). Aplicado
  el patrón de M5 — nombrar spans por paso interno (rag_search, vector/keyword) y
  tokens/costo como atributos de span, vía LangSmith (no vía OTel crudo, ver
  POSPUESTO). `_vector_search`/`_keyword_search` instrumentados con `@traceable`
  (spans `agent.rag_search.vector`/`agent.rag_search.keyword`, `run_type="retriever"`,
  gateado por `LANGCHAIN_API_KEY` igual que evaluators.py) + fix de orden de imports
  en main.py (`load_dotenv()` antes de `import src.graph`, si no la instrumentación
  quedaba desactivada en producción). El LLM call de `agent_node` y los tool-calls
  `rag_search`/`create_ticket` quedan auto-trazados por LangChain una vez prendido
  `LANGCHAIN_TRACING_V2`, sin código extra (incluye tokens/costo, LangSmith los
  calcula solo). **Verificado 2026-07-29:** con `LANGCHAIN_TRACING_V2=true` ya en
  `.env`, servidor local levantado y un request real a `/chat` (pregunta sobre rango
  de medición de un transmisor Rosemount) generó un trace real en LangSmith con el
  árbol esperado — `ChatOpenAI` trazado automático, `rag_search` con
  `agent.rag_search.vector` (0.73s) y `agent.rag_search.keyword` (1.00s) anidados
  adentro como spans hijos. Confirmado por Juan con captura del dashboard.
- ✅ (2026-07-29) Poblado `ChatResponse.tool_calls_used` en main.py (deuda técnica desde
  Capa 5A, 2026-06-20, campo siempre devolvía `[]`): recorre `result["messages"]` tras
  `graph.invoke()` y junta los `.tool_calls[].name` de los mensajes que llamaron una
  tool, sin duplicados. Verificado con `pytest tests/test_rules.py` (7/7).
- ✅ (2026-07-29) `max_tokens=800` explícito en `get_bound_llm()` (aprendizaje empírico
  de M3: resúmenes largos escalan ~2.3x tokens de output). 800 alcanza de sobra para
  una respuesta técnica puntual con cita de fuente, y pone un techo real a un caso que
  se desborde.
- ~~Actualizar el SYSTEM_PROMPT de graph.py~~ — hecho en 5B.4 paso 3 (2026-07-15),
  ya no es parte de esta sesión.
- ✅ (2026-07-29) Arreglado el contrato de `RAGResult.score` (src/schemas.py): decía
  `ge=0.0/le=1.0` y se describía como "similitud coseno", pero `rag_search()` le pasa
  el score de RRF (no coseno). Era safe hoy SOLO por casualidad — con `rrf_k=1` el
  máximo de RRF da exactamente 1.0 (un chunk en rank 0 de ambas listas: 0.5+0.5); si
  cambiara `rrf_k`, un score>1.0 hubiera tirado `ValidationError` dentro de
  `rag_search()` en producción. Sacado el `le=1.0`, corregida la descripción a "score
  de fusión RRF" (detectado 2026-07-24, corregido 2026-07-29).
- ✅ (2026-07-29) Redominado el schema de `create_ticket` (src/schemas.py:TicketInput):
  las categorías `bug/feature/question/other` eran vocabulario prestado del curso
  DeepLearning (soporte de software) y no encajaban en instrumentación de campo.
  Reemplazadas por `field_instrument_failure/biological_process_anomaly/
  pump_maintenance/undocumented_query` — tomadas del borrador ya existente en
  CORPUS_INSTRUMENTACION.MD ("Categorías sugeridas para create_ticket") y traducidas a
  inglés para seguir la convención del resto del `Literal` (`low/medium/high`).
  `tests/test_rules.py` actualizado (summary + categorías de ejemplo del dominio real
  en vez de "el cliente no puede iniciar sesión"). Cambio de schema barato, sin
  persistencia (ver POSPUESTO para la persistencia real). Detectado 2026-07-24,
  corregido 2026-07-29.

**Sesión 2 completa (2026-07-29).** Los 6 ítems del batch de limpieza (paso 6 dead
code, tracing real, tool_calls_used, max_tokens, contrato de RAGResult.score,
TicketInput redominado) están cerrados.

Nota (2026-07-11): este plan asumía "Sesión 2 → recién ahí arrancar M4". En la
práctica M4 se cursó en paralelo, sin esperar a la Sesión 2, y ya terminó (videos +
HW ✓, ver courses/POST_COURSE_ZOOMCAMP_M4.md).

Nota (2026-07-13): con CORPUS_INSTRUMENTACION.MD ya diseñado, Juan decidió priorizar
el corpus nuevo (Sesión 0 / 5B.4) por delante de las Sesiones 1 y 2, que quedan en
pausa sin cambios hasta que 5B.4 avance.

Nota (2026-07-24, revisión estratégica con Opus 4.8): repaso completo del repo +
roadmap. Objetivo confirmado: portfolio para conseguir trabajo, pero SIN fecha dura
→ balancear profundidad de retrieval (ya muy sólida) con cerrar huecos de "producto
navegable". Diagnóstico: se profundizó mucho en retrieval y quedaron huecos de
producto (CI en rojo, sin deploy, create_ticket stub, evals de generación nunca
corridos sobre el corpus real). Reordenamiento de prioridades acordado, DESPUÉS de
cerrar 5B.3:
1. CI en verde + seguridad — arreglar/aislar el job de evals roto (ver ci.yml) y
   ADELANTAR la rotación de credenciales + limpieza de historial de git a AHORA (ya
   no "antes de hacerlo público": reescribir historial se vuelve más difícil cuanto
   más crece, ver POSPUESTO actualizado).
2. Evals del corpus real — correr el LLM-as-judge sobre las 520 preguntas de
   instrumentación (medir si el agente RESPONDE bien, no solo si recupera; ver
   POSPUESTO "LLM-as-judge sobre corpus nuevo"). Sinérgico con el punto 1: ese
   dataset puede alimentar el job de CI de evals que hoy está roto.
Sesión 2 (limpieza) y deploy (Capa 6) quedan después, sin fecha. Modelo de trabajo:
Sonnet 5 para construir día-a-día, Opus 4.8 para sesiones de arquitectura/estrategia.

Actualización (2026-07-24, misma sesión): Capa 5B.3 verificada contra Supabase real y
commiteada/pusheada (`921ab4f`). Capa 5B y Capa 5 quedan completas. Arranca la
prioridad 1 de arriba: CI en verde + seguridad (rotación de credenciales + limpieza de
historial de git).

Actualización (2026-07-27): al abrir la prioridad 1 (arreglar/aislar el job de evals de
CI), apareció que el job estaba roto en dos capas distintas, no solo la técnica (falta
DATABASE_URL): golden_set.json seguía siendo sobre LangGraph docs, corpus que ya no
existe en Supabase — conectar DATABASE_URL sin cambiar eso solo hubiera cambiado el
error, no arreglado el job. Se decidió resolver el bloqueo de contenido primero: nuevo
`evals/generate_golden_set.py` (48 preguntas del corpus de instrumentación, 12 por
categoría, con expected_answer grounded generada por LLM a partir de las 520 preguntas
y chunk_ids ya verificados en 5B.4) + `accuracy_evaluator` nuevo en `evaluators.py`
(compara la respuesta del agente contra esa referencia — complementa, no reemplaza, a
`relevance_evaluator`). Wireado en `run_evals.py` y corrido contra Supabase+OpenAI
reales: 48 casos, relevancia 4.44/5, accuracy 3.88/5, 85% con cita (resultados en
`evals/results/2026-07-27/`). La prioridad 2 (evals del corpus real) queda así
adelantada y parcialmente resuelta — con 48 preguntas sampleadas, no las 520 completas
(decisión de costo/alcance, ver POSPUESTO). La prioridad 1 sigue sin cerrar: falta
agregar DATABASE_URL como secret de CI (con un rol de Postgres de solo lectura, no la
credencial completa — decidido con Juan, no implementado) y reemplazar las 2 preguntas
hardcodeadas del dominio viejo en `tests/test_evals.py`. La rotación de credenciales +
limpieza de historial de git tampoco se tocó todavía.

Actualización (2026-07-28): cerrados los dos pendientes técnicos que quedaban de la
prioridad 1. Creado en Supabase el rol `ci_readonly` (GRANT SELECT solo sobre `chunks`
+ policy de RLS scopeada a ese rol, ver detalle en `ci.yml` arriba) y agregado como
secret `DATABASE_URL` en GitHub Actions. Reemplazadas las 2 preguntas hardcodeadas del
dominio viejo en `tests/test_evals.py` por preguntas reales de instrumentación de campo.
Verificado en dos niveles: local (3 tests de `test_evals.py` en verde contra
Supabase+OpenAI reales) y en CI real — push del commit `1945750`, run #17 verde en
ambos jobs (`rules` y `evals`). **La prioridad 1 (CI en verde + seguridad) queda
cerrada en su parte de CI.** Lo único que sigue pendiente de esa prioridad es la
rotación de credenciales reales + limpieza de historial de git (ver POSPUESTO abajo) —
no se tocó hoy: al probar la conexión de `ci_readonly` se expuso sin querer la
password real de `DATABASE_URL` en el chat de la sesión; Juan restauró esa misma
password en `.env` (no generó una nueva), así que la credencial de producción sigue
siendo la misma de antes — la rotación real todavía no pasó.

Actualización (2026-07-28, sesión tarde): resuelto el resto de la prioridad 1.
Mail automático de Supabase (`rls_disabled_in_public`) detectó que las 4 tablas del
checkpointer (`checkpoints`/`checkpoint_blobs`/`checkpoint_writes`/
`checkpoint_migrations`, creadas en 5B.3) nunca pasaron por el
`ALTER TABLE ... ENABLE ROW LEVEL SECURITY` que sí tenía `chunks` desde julio —
corregido con el mismo patrón (RLS sin policies; el rol de la app conecta directo
por Postgres, no por la API REST, así que no se ve afectado). Verificado con
`SELECT rowsecurity FROM pg_tables` (las 5 tablas en `true`) + `pytest
tests/test_rules.py` (7/7). En el camino se rotaron las dos credenciales reales:
`OPENAI_API_KEY` (proyecto nuevo scopeado creado en OpenAI, key vieja para revocar)
y la password de `DATABASE_URL` (reset en Supabase) — motivo extra: durante esta
sesión se expuso por error, en el chat, la `OPENAI_API_KEY` nueva (un comando
`sed` que no truncó como se esperaba), sumado a la exposición de `DATABASE_URL` de
la sesión de la mañana (ver arriba). Ambas rotaciones verificadas con pytest en
verde. **La prioridad 1 queda completamente cerrada**, salvo la limpieza del
historial de git (ver POSPUESTO) — ya no es urgente en el sentido de "credencial
viva expuesta" (las viejas quedaron inertes), es higiene pendiente antes de
publicar el repo como portfolio.

Arrancada también la Sesión 2 (limpieza mecánica, ver plan arriba): paso 6 (dead
code) completo, tracing real en progreso — detalle en la sección de Sesión 2.

Actualización (2026-07-29): cerrado el ítem de tracing real de la Sesión 2 — ver
detalle de verificación en la sección de Sesión 2 arriba.

Actualización (2026-07-29, tarde): cerrados los 3 ítems restantes de la Sesión 2
(`ChatResponse.tool_calls_used`, `max_tokens` explícito, contrato de
`RAGResult.score`, redominar `TicketInput`) — **Sesión 2 completa**, ver detalle en
su sección arriba.

**Cambio de prioridad:** Juan entrega este repo tal cual como proyecto final del
**LLM Zoomcamp 2026** (DataTalks.Club) — deadline 2026-08-10. Detalle completo del
handoff del curso en
`courses/PROJECT_APPROVAL_HANDOFF.md`. Auditoría del repo contra la rúbrica oficial
(9 criterios 0-2 pts + 3 best practices) hecha 2026-07-29: hoy ~12/21. Plan de acción
acordado con Juan, en orden de ROI (puntos de rúbrica por hora), objetivo ~19/21 antes
del deadline:
1. Dockerfile de la app (containerization 0→1)
2. README: mencionar explícitamente los criterios de evaluación (regla dura del curso)
3. Endpoint de feedback de usuario (monitoring 0→1, revisado 2026-07-31: apuntando a
   0→2 — ver detalle en la actualización del 2026-07-31 más abajo)
4. Comparar 2 system prompts con evals/run_evals.py (LLM evaluation 1→2)
5. Query rewriting (best practice)
6. Ajustar instrucciones de reproducibility (dataset con copyright, techo incierto)
7. Limpieza del historial de git (`.env` viejo — ver POSPUESTO abajo, ahora SÍ en
   alcance de esta entrega) + repo privado→público
Deploy a cloud (bonus +2) y el 2do punto de containerization/monitoring (docker-compose
completo, dashboard) quedan como stretch post-19/21, a decidir según cómo vaya la
semana — no están en el plan fijo. Capa 6 (deploy) del mapa de capas más abajo sigue
`PENDIENTE` en el sentido de "no hay código", pero el bonus de deploy es justamente
parte de esa capa.

Actualización (2026-07-30): arrancado el punto 1 (Dockerfile). Creados `Dockerfile`
(`python:3.12-slim`, copia `requirements.txt` primero para cachear la capa de
`pip install`, después `src/`, `EXPOSE 8000`, `CMD uvicorn src.main:app --host
0.0.0.0 --port 8000`) y `.dockerignore` nuevo (excluye `.venv/`, `.git/`, `docs/`,
`tests/`, `.env`, etc. — sin esto `docker build` copiaría el `.venv/` completo al
contexto). Decisión explicada a Juan: la imagen no incluye `docs/pdfs/` (la ingesta
ya corrió contra Supabase, la app en runtime solo consulta la base) ni `.env`
(secretos van con `--env-file .env` en `docker run`, nunca en la imagen). Sin
probar esa sesión — próximo paso pedido explícitamente por Juan: active recall
sobre Docker antes de tocar el build.

Actualización (2026-07-31): active recall de Docker hecho al arrancar la sesión
(Dockerfile/imagen/container, build vs run, por qué `.dockerignore` — las tres
respuestas de Juan correctas). **Build y run probados y verificados:**
`docker build -t agentic-rag-fastapi .` (~61s, sin errores) y
`docker run --env-file .env -p 8000:8000 agentic-rag-fastapi` levantaron un
container real que conectó a Postgres, corrió `checkpointer.setup()` y respondió
un `POST /chat` real con `rag_search` funcionando (cita de fuente correcta,
`tool_calls_used` poblado). Container detenido y eliminado al terminar la prueba.
**Punto 1 del plan (containerization) completo, 0→1 en la rúbrica.**

**Punto 2 del plan (README) completo:** agregada la sección "Criterios de evaluacion
(LLM Zoomcamp 2026)" en `README.md` — tabla con los 9 criterios oficiales, cada uno
apuntando a dónde vive en el repo (regla dura del curso: el README debe mencionar
los criterios explícitamente). Sin inflar: Monitoring y las 2 best practices que
faltan (reranking, query rewriting) están marcadas como "Pendiente", no se reportan
como hechas. Sumado también el comando `docker run` a "Como correrlo". Próximo paso:
punto 3 del plan, endpoint de feedback de usuario (monitoring 0→1).

**Decisión 2026-07-31 sobre el punto 3 (monitoring):** en vez del endpoint de
feedback solo (0→1), se decidió con Juan un enfoque más barato para llegar a 2/2 —
el criterio pide feedback de usuario **y** dashboard con ≥5 gráficos. LangSmith ya
está prendido desde la Sesión 2 (2026-07-29) y su dashboard de proyecto ya expone
varios gráficos gratis (cantidad de runs, latencia, tokens/costo, error rate) sin
armar nada nuevo — no es "el dashboard" que uno construye, pero cumple la letra del
criterio. Plan: el endpoint de feedback escribe en Postgres (tabla chica) **y**
además manda el feedback a LangSmith con `client.create_feedback(run_id, ...)`
(dependencia `langsmith` ya instalada, no suma librería nueva) para que quede
asociado a cada trace real y aparezca en el dashboard. Evita armar el stack
Postgres+Grafana completo (que seguía como stretch post-19/21) para llegar al mismo
puntaje.

**Arrancado 2026-07-31 (noche), a paso a paso con active recall:**
1. ✅ `ChatResponse.run_id` (`src/schemas.py`) + generado con `uuid.uuid4()` en
   `main.py` antes de `graph.invoke()`, pasado por `config["run_id"]` (fuerza a
   LangSmith a usar ese UUID en vez de generar el suyo) y devuelto en la respuesta
   de `/chat`. Necesario para poder asociar feedback a una conversación puntual
   después con `client.create_feedback(run_id=...)`.
2. ✅ Tabla `feedback` (`id`, `run_id uuid`, `thread_id`, `score real`, `comment`,
   `created_at`) creada en el `lifespan` de `main.py`, mismo patrón idempotente que
   `checkpointer.setup()` (`CREATE TABLE IF NOT EXISTS` + RLS sin policies). Decisión:
   reusa el pool `psycopg_pool` que ya abre el checkpointer (evita el lag de
   conexión nueva por request que tiene `rag_search()`, ver POSPUESTO). Verificado
   contra Supabase real: tabla existe, columnas correctas, `rowsecurity = true`.
   `src/main.py` y `src/schemas.py` todavía sin commit al cierre de esta sesión.
3. ✅ (2026-08-01) `FeedbackInput` (schema) + ruta `POST /feedback` (INSERT a la tabla +
   `client.create_feedback()` a LangSmith) — ver detalle en `src/main.py`/`src/schemas.py`
   arriba. Commit `2810fb4`. **Punto 3 del plan de entrega completo — monitoring 0→2.**

**Decisión 2026-07-31 sobre RAGAS (ver POSPUESTO abajo):** confirmado con Juan que
se suma como upgrade **condicional** — solo si el plan core (puntos 3-7) cierra con
tiempo de sobra antes del 10/08. Framework elegido: **RAGAS** (ya estaba anotado
desde el 18/07; coincide con las métricas de generación que faltan — faithfulness,
answer relevancy, context precision/recall — y es el nombre más reconocible para
evaluación de RAG específicamente en búsquedas laborales de AI/LLM Engineer, más
que alternativas más genéricas como DeepEval). Estimado ~1.5-2.5h — el riesgo que
puede estirarlo es compatibilidad de versión entre `ragas` y `langchain==1.2.15`/
`langchain-core==1.3.2` (RAGAS suele ir atrás soportando versiones nuevas de
LangChain), no la lógica del script en sí.

**Actualización (2026-08-01):** cierra el punto 3 (feedback de usuario, ver arriba,
commit `2810fb4`) y arranca el punto 4 (comparar prompts/modelos, LLM evaluation 1→2).

**Punto 4, en progreso — código completo, decisión de producción pendiente:**
`src/graph.py` y `evals/run_evals.py` refactorizados (ver detalle en "Estado actual
del repo" arriba) para poder comparar variantes sin tocar el comportamiento de
producción/CI. Se sumó comparar tambien **modelo**, no solo prompt — decisión de
Juan de aprovechar el mismo mecanismo (closure factory) para probar `gpt-4.1-nano`
contra el `gpt-4o-mini` de siempre, ya que salía barato una vez parametrizado el
prompt. Metodología acordada con Juan: un solo cambio de variable por corrida (4
combinaciones aisladas: baseline/direct_answer x mini/nano), nunca dos cambios
mezclados en una misma comparación.

- `prompts/system_prompt.txt` (el de producción, movido tal cual desde `graph.py`) y
  `prompts/system_prompt_direct_answer.txt` (Variante B) nuevos. La Variante B ataca
  un hallazgo real sin investigar del 2026-07-27 (ver arriba): 5/48 preguntas
  respondibles con el manual terminaban en `create_ticket` en vez de una respuesta
  directa. Se agregó una instrucción explícita de prioridad: responder directo con
  `rag_search` si el manual cubre la consulta, reservar `create_ticket` para lo que
  el manual no cubre o requiere intervención física.
- **Bug real encontrado y arreglado en el camino:** el feedback de `run_evals.py` a
  LangSmith nunca se mandó desde que se implementó (2026-07-27) — `run_id` siempre
  daba `None` (ver detalle en la entrada de `run_evals.py` arriba). Fix aplicado y
  verificado con `client.list_feedback()`.
- `evals/compare_prompts.py` y `evals/cost_report.py` nuevos (ver "Estado actual del
  repo" arriba).
- **Corrida real completa (48 preguntas x 4 variantes, 2026-08-01), calidad + costo
  (costo real vía `cost_report.py`, sumando el árbol completo de cada trace en
  LangSmith):**

  | Variante | Relevancia | Accuracy | Citas | `create_ticket` | Costo total (48) | Costo x caso |
  |---|---|---|---|---|---|---|
  | baseline_mini (producción actual) | 4.40/5 | 3.60/5 | 81% | 9/48 | $0.0214 | $0.00045 |
  | baseline_nano | 4.90/5 | 4.27/5 | 92% | 0/48 | $0.0150 | $0.00031 |
  | direct_answer_mini | 4.62/5 | 3.94/5 | 94% | 2/48 | $0.0229 | $0.00048 |
  | direct_answer_nano | 4.75/5 | 4.08/5 | 94% | 0/48 | $0.0156 | $0.00033 |

  (conteo de `create_ticket` sacado de los logs del stub, no del JSON de métricas —
  no se persiste ese dato en `evaluate_case()` hoy).

  **Lectura:** el prompt nuevo funciona como se hipotetizó, pero solo se nota con
  `gpt-4o-mini` (9→2 tickets, mejora las 4 métricas). Con `gpt-4.1-nano`, el prompt
  VIEJO ya elimina el problema solo (0/48 tickets) y da las mejores métricas de las
  cuatro variantes, siendo ~30% más barato que `gpt-4o-mini` con cualquiera de los
  dos prompts. **Decisión pendiente de confirmar con Juan** entre `baseline_nano`
  (mejor en las 3 dimensiones, pero `gpt-4.1-nano` sin kilometraje previo en el
  resto del pipeline) y `direct_answer_mini` (se queda con el modelo ya probado en
  todo el proyecto, mejora 100% atribuible al prompt — historia más prolija para
  contar en una entrevista).
- **Sin commitear:** `src/graph.py`, `evals/run_evals.py` (modificados),
  `evals/compare_prompts.py`, `evals/cost_report.py`, `prompts/` (nuevos) — se
  commitean juntos cuando se confirme y aplique la decisión de arriba (cuál
  combinación queda como default de producción).

**Actualización (2026-08-01, noche) — el punto 4 se cierra con decisión final, y se abre
una duda de Juan que termina siendo su propia mini-investigación (temperatura):**

Antes de decidir entre `baseline_nano` y `direct_answer_mini` con los 48 casos de
arriba, Juan planteó una objeción válida: "si me quedo con el modelo que mide peor
solo porque ya lo probamos, no es un criterio, es sesgo". Se armó un criterio más
duro en 3 pasos, cada uno con evidencia concreta:

1. **Extender el golden set con casos de escalamiento reales** (ver `golden_set.json`
   arriba, 48→56) — la comparación de 48 preguntas solo medía accuracy en preguntas
   *contestables*, dejando afuera la decisión de mayor riesgo para este dominio: si
   el agente escala con `create_ticket` en vez de inventar, cuando la consulta cae
   fuera del corpus. `tool_call_evaluator` nuevo en `evaluators.py` (ver arriba) mide
   esto de forma code-based, no con LLM-judge.
2. **Segunda corrida completa de `compare_prompts.py` (56 casos x 4 variantes):**

   | Variante | Relevancia | Accuracy | Citas | Tool-call (escalamiento) |
   |---|---|---|---|---|
   | baseline_mini | 4.43/5 | 3.69/5 | 77% | 8/8 (100%) |
   | baseline_nano | 4.68/5 | 4.12/5 | 84% | 7/8 (88%) |
   | direct_answer_mini | 4.77/5 | 4.17/5 | 84% | 8/8 (100%) |
   | direct_answer_nano | 4.80/5 | 4.23/5 | 88% | 6/8 (75%) |

   **Hallazgo que decide la comparación:** nano falló los *mismos* 2 casos de
   escalamiento (transmisor Yokogawa fuera del corpus, caudalímetro de marca
   genérica) en ambas variantes de prompt — no es ruido, es sistemático. En vez de
   escalar, inventó un rango de medición genérico (`baseline_nano`) y fabricó un
   procedimiento de calibración citando "la documentación consultada" para un
   equipo que el corpus no cubre (`direct_answer_nano`) — exactamente lo que el
   `SYSTEM_PROMPT` prohíbe explícitamente. Mini no falló ni un caso (16/16 entre las
   dos variantes de prompt). **Decisión final: `direct_answer_mini`.** No es "nos
   quedamos con el conocido por costumbre" — es una ventaja medible y reproducible
   en la dimensión que más importa para este dominio (no inventar en zona gris),
   sumada a que el prompt nuevo ya corrige el problema original de mini (exceso de
   tickets, ver corrida de 48 casos arriba).
3. **Duda de Juan, ya con el ganador elegido:** "¿no deberíamos fijar la temperatura
   para que invente menos?" — válida: `get_bound_llm()` nunca fijaba `temperature`
   (corría al default implícito de OpenAI, 1.0). `temperature` ahora es parámetro
   explícito en `src/graph.py`/`run_evals.py` (ver arriba). `evals/
   compare_temperature.py` nuevo: sweep de 4 valores (0.0/0.3/0.6/1.0) x 2 corridas
   sobre `direct_answer_mini`:

   | Temp | Accuracy avg | Spread (estabilidad) | Tool-call |
   |---|---|---|---|
   | 0.0 | 4.00 | 0.04 | 100% |
   | 0.3 | 4.07 | 0.10 | 100% |
   | 0.6 | 4.12 | 0.05 | 100% |
   | 1.0 (default actual) | 4.03 | **0.18** | 100% |

   Verificado que no hay bug (se leyó `llm.temperature` directo del objeto
   `ChatOpenAI` para confirmar que el valor pedido llega de verdad). La aparente
   tendencia "más temperatura = más accuracy" no se sostiene con test pareado
   (comparación cruzada temp 0.0 vs 0.6: 3-6/6-6/4-5/2-5, sin significancia) ni con
   temp=1.0 rompiendo el patrón (cae de vuelta a 4.03, con el doble de spread que
   cualquier otro valor) — es ruido de muestreo del LLM-judge sobre 48 preguntas, no
   una tendencia causal. Lo único que sí es señal limpia: **temp=1.0 es la más
   inestable de las cuatro**, confirmando la sospecha original de Juan de que no
   fijarla agrega ruido innecesario (tanto a las mediciones como, potencialmente, al
   comportamiento real en producción). **Decisión final: `temperature=0.3`** — punto
   medio entre estabilidad (spread 0.10, muy por debajo del 0.18 de referencia) y
   tasa de citas (86% vs 78% a temp=0.0, con hipótesis de que sea un efecto de
   estilo — respuestas más tersas a temp 0 que omiten mencionar la fuente aunque
   hayan usado `rag_search` igual — más que un problema real de grounding).
   - Corrida en background: se cortó sola a los 5/8 (`status: killed`, sin causa
     visible en el código ni en los logs — nada indica timeout de la app ni error de
     OpenAI). Las 3 corridas faltantes (`temp0.6_run2`, `temp1.0_run1`,
     `temp1.0_run2`) se relanzaron aparte reusando `build_eval_graph`/
     `run_eval_pass` — cada corrida guarda su JSON apenas termina, así que no se
     perdió ninguna de las 5 ya hechas.
   - **Queda anotado, no bloqueante:** correr un sweep chico de `gpt-4.1-nano` a
     temperatura baja (0.0/0.3) para confirmar si eso corrige su falla de
     escalamiento — curiosidad de Juan sobre si el problema era más de muestreo que
     de conocimiento del modelo. No cambia la decisión ya tomada salvo que el
     resultado sea sorprendente.
- **Punto 6 del plan (reproducibility) cerrado en la misma sesión:** `README.md` —
  "Como correrlo" reforzado con checklist explícito de requisitos (API key de
  OpenAI, Postgres con `pgvector`, los 11 PDFs) y mención directa de que los links
  del corpus (`CORPUS_INSTRUMENTACION.MD`) son gratuitos y verificados HTTP 200, no
  solo un "ver sección anterior" pasivo. Agregado el camino de reproducir evals sin
  re-ingerir (los datasets ya están commiteados). Fila "Reproducibility" de la tabla
  de criterios actualizada. El techo real (¿alcanza 2/2 sin el dataset físicamente
  adentro del repo?) queda a criterio del revisor humano — no es algo que más
  documentación pueda resolver, ya se discutió con Juan.
- **Actualización (2026-08-03): punto 4 aplicado y commiteado.** `graph_builder =
  build_graph()` en `src/graph.py` ya usa los defaults nuevos (`TEMPERATURE = 0.3`,
  `SYSTEM_PROMPT` desde `system_prompt_direct_answer.txt`) — tests verificados en
  verde (7/7) antes de commitear. Commit `8fabcf6` agrupa esto con el resto del
  trabajo del punto 4 que venía sin commitear (framework de comparación, evals
  corridos, `README.md`) — pusheado a `origin/main`.
- **Punto 5 (query rewriting) implementado y validado el mismo día — ver detalle en
  `src/tools.py` arriba y en `CHANGELOG.md` 2026-08-03.** Mejora sustancial y medible
  en hybrid search: hit_rate 0.317 → 0.4154 (+31%), mrr 0.186 → 0.2197, sobre las 520
  preguntas completas de `ground_truth_retrieval.json`. Pendiente de commitear
  (`src/tools.py`, `prompts/query_rewrite.txt`).
- **Punto 6 reconfirmado cerrado (2026-08-03):** revisado a pedido de Juan si hacía
  falta agregar algo más sobre copyright del dataset — ya estaba completo desde el
  2026-08-01 (`README.md` + `CORPUS_INSTRUMENTACION.MD`, con cita explícita de los
  Términos de Uso de Emerson). Sin cambios.
- **Próximo paso concreto:** commitear `src/tools.py` + `prompts/query_rewrite.txt`
  (query rewriting, punto 5), y seguir con el punto 7 (limpieza de historial de git +
  repo público) — requiere confirmar con Juan el plan explícito antes de ejecutar
  (operación destructiva, ver POSPUESTO).
- Sesión cerrada acá por hoy (2026-08-03).

**Actualización (2026-08-04):** commiteado y pusheado el punto 5 (`src/tools.py` +
`prompts/query_rewrite.txt`, commit `2eed98a` — reescrito a `d47031b` por la limpieza
de historial, ver abajo). **Arranca el punto 7 (limpieza de historial de git):** plan
explícito confirmado con Juan antes de ejecutar (backup primero, ensayo en copia
descartable, recién después el repo real). Backup completo (`git bundle --all`,
verificado) hecho antes de tocar nada. `git-filter-repo` instalado y corrido
(`--path .env --invert-paths`) primero contra una copia de prueba, verificado ahí
(`.env` fuera del historial, contenido idéntico al repo real), y recién después
aplicado al repo real local — verificado también: `.env` fuera de los 43 commits,
`pytest tests/test_rules.py` 7/7 en verde, escaneo de todo el historial sin patrones
de credenciales reales, reflog y objetos sueltos limpios. **Falta solo el
`git push origin --force --all`** — no ejecutado hoy por la regla de horario del
repo (nunca commit/push 9-18hs ARG lun-vie); queda para después de las 18hs o el fin
de semana, junto con pasar el repo de privado a público.

**Arrancado también el stretch #1 (RAGAS, condicional a que el core cierre con
margen — ver más abajo):** confirmada la compatibilidad de `ragas==0.4.3` con las
versiones pineadas del proyecto (`langchain==1.2.15`/`langchain-core==1.3.2`/
`langchain-openai==1.2.1`/`openai==2.33.0`) en un venv aislado, sin tocar
`requirements.txt` todavía — el riesgo de versión que este mismo archivo tenía
anotado no se materializó. Import viejo (`from ragas.metrics import ...`) deprecado
a favor de `ragas.metrics.collections` — se va a usar la ruta nueva cuando se
escriba el script. **Decisión de diseño tomada:** los `contexts` que RAGAS va a
juzgar (`faithfulness`/`context_precision`/`context_recall`) se toman de lo que el
agente realmente vio en una corrida real (capturando el output de la tool call
`rag_search` vía `run_evals.py`/`build_eval_graph`), no de una llamada directa a
`_hybrid_search()` — más fiel a qué contexto tuvo el LLM cuando generó cada
respuesta puntual, evita evaluar `faithfulness` contra chunks que el agente ni vio.
`ground_truth` = `expected_answer` de los 48 casos de `evals/golden_set.json` que lo
tienen (quedan afuera los 8 de escalamiento, que usan `expected_tool`). Sin código
escrito todavía — el venv de prueba no toca el repo.
- **Próximo paso concreto:** force-push del punto 7 + pasar el repo a público
  (fuera de la ventana horaria); en paralelo/después, escribir `evals/ragas_eval.py`
  con el diseño ya acordado arriba.
- Sesión cerrada acá por hoy (2026-08-04).

**Actualización (2026-08-05):** commit `e885f2d` (cierre de la entrada de arriba,
CHANGELOG/ROADMAP) + **`git push origin --force --all` ejecutado** (confirmado
explícitamente por Juan antes de correrlo) — `origin/main` ya tiene el historial
reescrito sin `.env` (verificado con `git fetch` + `git log origin/main`). El punto 7
queda cerrado del lado de código/git; solo falta que Juan pase el repo de privado a
público en GitHub, a su criterio, más adelante.

**Stretch #1 (RAGAS) completado.** Al instalar de verdad en el venv del proyecto
(no en el venv aislado del 2026-08-04) apareció un hallazgo real que contradice lo
"verificado" ese día: `ragas==0.4.3` no fija versión de `langchain-community`, y la
última (`0.4.2`) borró `langchain_community/chat_models/vertexai.py` — módulo que
`ragas/llms/base.py` importa sin condición al cargar el paquete (`import ragas`
fallaba de entrada, ni siquiera llegaba a usarse). El test aislado del 04/08 no lo
detectó (probablemente resolvió una `langchain-community` distinta en ese momento).
Fix: `langchain-community==0.4.1` pineado explícito en `requirements.txt` (ahí el
módulo todavía existe, y solo pide `langchain-core>=1.0.1`) — de paso subió
`langchain-core` de `1.3.2` a `1.5.3` (piso real de `langchain-classic`, dependencia
transitiva de `langchain-community`). `pip check` limpio y `pytest tests/test_rules.py`
7/7 en verde con las versiones nuevas.

`evals/ragas_eval.py` escrito con el diseño ya acordado (ver detalle completo en
"Estado actual del repo" arriba: 3 bugs reales encontrados y arreglados corriendo el
script de punta a punta, no solo leyendo docs) y corrido contra los 48 casos completos
de `golden_set.json`: 46/48 puntuados, faithfulness 0.783, answer_relevancy 0.708,
context_precision 0.571, context_recall 0.679 (`evals/results/2026-08-05/
11-46-58_ragas.json`). De paso, se creó (fuera de este repo) la skill de usuario
`esquema-de-tarea` en `~/.claude/skills/` — no es parte del código de
`agentic-rag-fastapi`, no se documenta más acá.
- **Próximo paso concreto:** pasar el repo a público (Juan, cuando pueda). Según el
  timeline de abajo, si queda margen antes del 10/08 sigue el stretch #2 (Streamlit).
  Nada de lo de hoy se commiteó (sesión dentro de la ventana 9-18hs ARG lun-vie).
- Sesión cerrada acá por hoy (2026-08-05).

**Timeline armado con Juan (2026-08-01)** para lo que resta del plan de entrega,
contra su disponibilidad real (1.5h lunes a viernes, 3h sábados, 0h domingos):

| # | Tarea | Estimado |
|---|---|---|
| 4 | Cerrar comparación de prompts/modelos (elegir ganador, aplicar, commit) | 0.5–1h |
| 5 | Query rewriting (best practice) | 1.5–2.5h |
| 6 | Reproducibility (instrucciones, nota de copyright del dataset) | 0.5–1h |
| 7 | Limpieza historial de git + repo público | 1–2h |
| — | Cierre de docs (ROADMAP/CHANGELOG/README final) | 0.5h |

**Actualización (2026-08-03):** puntos 4, 5 y 6 completos (ver detalle arriba y en
`CHANGELOG.md`). Quedan el punto 7 (limpieza de historial de git, necesita plan
explícito confirmado con Juan antes de ejecutar) y el cierre de docs final.

Core estimado ~5.5h — con el ritmo de trabajo confirmado (Juan: "a veces incluso
demoro menos de lo que estimamos"), terminaría el jueves 6/8, dejando viernes 7/8 +
sábado 8/8 (~4.5h) de margen antes del deadline, sin tocar el lunes 10/8 (reservado
como buffer de entrega, no para tareas nuevas). **Orden de stretch confirmado con
Juan, si el core cierra con margen:** RAGAS → Streamlit (front de chat simple con
pulgar arriba/abajo, consumiendo `/chat` y `/feedback` — no suma puntos de rúbrica,
Interface ya está en 2/2, pero es barato dado lo que ya existe y da visibilidad de
portfolio) → deploy a cloud (bonus +2) → Grafana (el más lejano: LangSmith ya cubre
Monitoring, armar Grafana sería infraestructura nueva sin ROI de rúbrica, compite
por el mismo tiempo que RAGAS/deploy en vez de sumar gratis).

── POSPUESTO (registrado, no bloquea nada de lo de arriba) ──
- Connection pool para Postgres (hoy conexión nueva por request en rag_search(),
  anotado como mejora de performance desde 5B.2).
- Limpiar el historial de git (`.env` trackeado en commits viejos hasta `834e71a`,
  pendiente desde 2026-07-02). Las credenciales reales ya fueron rotadas
  (2026-07-28, ver arriba) — lo que queda en el historial son keys inertes, así que
  esto ya no es una emergencia de seguridad, es prolijidad antes de publicar el
  repo como portfolio. Operación destructiva e irreversible (`git filter-repo` +
  force-push) — confirmar plan explícito con Juan antes de tocar el historial,
  no ejecutar de forma autónoma. Actualización (2026-07-29): ahora SÍ entra en el
  alcance de la entrega del LLM Zoomcamp (ver "Cambio de prioridad" arriba) — Juan
  confirmó que quiere el historial limpio antes de pasar el repo a público.
  **Actualización (2026-08-05): force-push ejecutado y verificado — `origin/main`
  ya tiene el historial reescrito, sin `.env`.** Ver "Actualización (2026-08-05)"
  arriba. Solo falta pasar el repo de privado a público en GitHub, a criterio de
  Juan, sin fecha fija.
- Supervisor multi-agente / create_react_agent prebuilt — descartados por ahora
  en el handoff de M3 (repo monolítico resuelve bien el dominio actual).
- .env.example volvió a guardarse en UTF-16 (se había corregido a UTF-8 el
  2026-07-01) — detectado 2026-07-15 al escribir el README, no se tocó para no
  desviarse del paso 3.
- ~~Separar los prompts a archivo(s) propio(s) en vez de vivir inline en graph.py~~
  — RESUELTO 2026-08-01: `prompts/system_prompt.txt` + `prompts/
  system_prompt_direct_answer.txt`, cargados con `load_prompt()` en `src/graph.py`
  (pedido de Juan, 2026-07-15, al corregir que ROADMAP.md listaba un
  src/prompts.py que nunca existió — se resolvió al necesitar una segunda
  variante para el punto 4 del plan de entrega, ver arriba).
- Persistencia real de create_ticket en Postgres (capa futura explícita opcional,
  no deuda escondida — discutido 2026-07-24). El concepto de escalar SÍ encaja en el
  dominio (orden de trabajo cuando el manual no cubre la consulta o requiere técnico
  de campo), pero hoy la tool es un stub que solo hace print() y devuelve un string;
  nunca persiste. Primero se redomina el schema (ver Sesión 2); la tabla tickets +
  INSERT real + recuperación cierran el caso de uso end-to-end recién cuando se
  encare el deploy (Capa 6) — no antes, no es prioridad con el objetivo actual.
- Framework de evals de generación (RAGAS u otro) como capa adicional sobre las
  métricas propias, no reemplazo — discutido 2026-07-18. Orden decidido:
  primero terminar hit_rate/mrr propios (pasos 5-6 de 5B.4, ya cerrado) porque
  programarlos a mano es la señal de conocimiento real; recién después sumar
  RAGAS (o similar) para métricas de generación end-to-end (faithfulness,
  answer relevancy, context precision/recall) que son tediosas de replicar
  bien a mano. Combinación retrieval-metrics propias + RAGAS para generación
  es el objetivo para un repo profesional — no portar hit_rate/mrr a una
  librería externa.
- FTS por idioma real (columna `language` por chunk, detectada al ingestar +
  `to_tsvector(lang::regconfig, content)` en vez del `'simple'` global fijo de
  hoy) — discutido 2026-07-18 al arreglar `_keyword_search` (ver paso 5 de
  5B.4 y CHANGELOG). Es el patrón "de producción" correcto para corpus
  multilingües, pero sobre-ingeniería para 11 documentos; el filtro de
  stopwords ES/EN alcanza para el tamaño actual del corpus. Reconsiderar si
  el corpus crece a más idiomas o más documentos por idioma.
- ~~LLM-as-judge (relevance) sobre las 520 preguntas del corpus nuevo~~ —
  RESUELTO PARCIALMENTE 2026-07-27: `evals/generate_golden_set.py` arma un
  golden_set.json nuevo (48 preguntas, no las 520 — sampling estratificado
  12 por categoría) con expected_answer grounded, y `accuracy_evaluator`
  (nuevo en `evaluators.py`) corre junto a `relevance_evaluator` vía
  `run_evals.py`. Corrida real: relevancia 4.44/5, accuracy 3.88/5. Sigue
  pendiente si algún día se quiere correr sobre las 520 completas en vez de
  la muestra de 48 (más costo, no decidido que haga falta todavía).
- Migrar de LangSmith a OpenTelemetry puro para tracing — discutido 2026-07-22
  al revisar el handoff de M5 (Monitoring, LLM Zoomcamp). No hay señal
  concreta hoy de que LangSmith se quede corto; sería una migración motivada
  por dos escenarios hipotéticos a futuro: (1) el agente crece con pasos que
  no son LangChain/LangGraph (llamadas propias, otros servicios/lenguajes)
  que LangSmith no puede trazar, o (2) el volumen de trazas supera el tier
  gratuito (5.000/mes, ver Capa 3B) y el costo o el vendor lock-in empiezan a
  pesar. Hasta que uno de esos dos pase, LangSmith sigue siendo la elección
  correcta para este stack (estándar de industria para LangGraph, ya
  integrado con evals) — no resta profesionalismo al repo.
```

---

## Capa 1 — AI Agents in LangGraph ✅

**Curso:** DeepLearning.AI — Harrison Chase
**Construido:**
- `src/state.py` — AgentState con TypedDict
- `src/tools.py` — stubs de rag_search() y create_ticket()
- `src/graph.py` — StateGraph con routing y MemorySaver
- `src/config.py` — validación de API key al startup
- `src/main.py` — FastAPI con /chat

**Decisiones activas:**
- MemorySaver hasta Capa 5, luego migrar a Postgres checkpointer
- Tools como stubs hasta Capa 5
- gpt-4o-mini por defecto para reducir costos

---

## Capa 2 — Automated Testing for LLMOps ✅

**Curso:** DeepLearning.AI — Rob Zuber (CircleCI)
**Traducción de stack:** CircleCI → GitHub Actions

**Construido:**
- `tests/conftest.py` — fixtures compartidos
- `tests/test_rules.py` — tests deterministas
- `tests/test_evals.py` — LLM-as-judge con gpt-4o-mini
- `tests/reports/` — pytest-html
- `.github/workflows/ci.yml` — rules en cada push, evals solo en main

**Decisiones activas:**
- rag_search() sigue siendo stub, test_evals.py usa known_context del golden_set
- Cuando llegue RAG real (Capa 5), known_context pasa a ser el chunk recuperado

---

## Capa 3A — Evaluating AI Agents (evaluadores a mano) ✅

**Curso:** DeepLearning.AI — John Gilhuly + Aman Khan (Arize AI)
**Traducción de stack:** Arize Phoenix → LangSmith (ver Capa 3B)

**Construido:**
- `evals/golden_set.json` — 20 preguntas con expected_answer y category
- `evals/evaluators.py` — relevance (LLM-judge), citation (code), convergence (code)
- `evals/run_evals.py` — corre evals, guarda resultados por fecha/hora
- `tests/test_evals.py` — actualizado para usar evaluators.py compartido
- `.github/workflows/ci.yml` — agrega evals en main con MAX_EVAL_CASES=1

---

## Capa 3B — LangSmith ✅

**Por qué LangSmith y no Phoenix:**
- Integración nativa con LangGraph (una variable de entorno, sin cambiar graph.py)
- Es lo que piden en entrevistas para roles con LangGraph
- Tier gratuito: 5.000 trazas/mes

**Integrado:**
- `evals/evaluators.py` — `relevance_evaluator` decorado con `@traceable`
- `evals/run_evals.py` — scores enviados con `client.create_feedback()`
- `.github/workflows/ci.yml` — `LANGCHAIN_API_KEY` como secret
- `.env.example` — variables con placeholders

**Regla activa:** si LANGCHAIN_API_KEY no está en el .env, LangSmith
se desactiva silenciosamente. El código nunca rompe sin esa key.

---

## Capa 4 — Pydantic for LLM Workflows ✅

**Curso:** DeepLearning.AI
**Estado:** completa — videos ✅ — código ✅ (commit f552cfd, 2026-06-07)

**Conceptos aprendidos en el curso:**
- `BaseModel` con typed fields, `Field()` constraints (ge/le/min_length/max_length)
- `Literal[]` para campos con valores permitidos fijos
- `Optional[]` para campos no obligatorios
- `client.beta.chat.completions.parse()` con `response_format=MyModel`
- Manejo de `ValidationError` con try/except

**Construido en el repo:**
- `src/schemas.py` con modelos Pydantic:
  - `ChatRequest` — validación del input de /chat (message + thread_id)
  - `ChatResponse` — respuesta tipada del agente (response + tool_calls_used)
  - `TicketInput` — args_schema para create_ticket() (summary + category + priority)
  - `RAGResult` — contrato de rag_search() (content + source + score)
- `src/main.py` — endpoint /chat usa `ChatRequest` + `response_model=ChatResponse`
- `src/tools.py` — `create_ticket` tiene `args_schema=TicketInput`; `rag_search` serializa `RAGResult`

**Por qué importa para Capa 5:** `RAGResult` ya define el contrato que `ingestion.py`
debe satisfacer. `TicketInput` está listo para conectarse a Postgres cuando llegue Supabase.

---

## Capa 5 — RAG real con PDFs ✅ COMPLETADA (2026-07-24)

**Curso:** LLM Zoomcamp — DataTalks.Club (M1 completo 2026-06-20)
**Decisión:** Zoomcamp sobre Coursera (proyecto real + comunidad + profundidad)

**Plan de construcción en dos subfases:**

**5A — Índice en memoria (M1 aplicado):**
- `src/ingestion.py` nuevo: carga texto → chunking con ventana deslizante → embeddings → índice numpy/minsearch
- `rag_search()` reemplaza stub: genera embedding de la query → busca top-N chunks por cosine similarity
- `RAGResult` (Capa 4) es el contrato que ya existe — la interfaz no cambia

**5B — pgvector/Supabase + Postgres FTS (M2 aplicado):**
- Migrar índice en memoria → Supabase (Postgres + pgvector)
- MemorySaver → Postgres checkpointer
- test_evals.py: `known_context` pasa a ser el chunk real recuperado

**Por qué construir 5A antes de ver M2:**
- La interfaz (`rag_search` → `RAGResult`) no cambia al migrar — solo el backend
- Entender el problema (similitud semántica en numpy) antes de la solución (pgvector) es mejor aprendizaje
- Tener un pipeline funcional acelera la integración de M2

**Qué se construye:**
- Reemplazar rag_search() stub por retrieval real
- Ingesta de PDFs: chunking + embeddings + almacenamiento
- Supabase como base de datos (Postgres + pgvector) — en 5B
- rag_search() conecta a Supabase y devuelve chunks relevantes — en 5B
- MemorySaver se migra a Postgres checkpointer — en 5B
- test_evals.py pasa de known_context fijo a chunk real recuperado

---

## Capa 6 — Deploy en AWS ⬜ PENDIENTE (H2)

**Timing:** después de Capa 5
**Opciones:** App Runner o ECS Fargate (decidir al llegar)

---

## Reglas técnicas del stack

1. Nunca sugerir librerías fuera del stack sin consultarme y explicar por qué.

2. Nunca saltar una capa. El estado actual está arriba — respetarlo.

3. Traducir siempre las herramientas del curso al stack del proyecto:
   - CircleCI → GitHub Actions
   - Arize Phoenix → LangSmith
   - Pinecone → Supabase/pgvector
   - Cualquier otra → preguntar antes

4. El modelo siempre es gpt-4o-mini salvo indicación explícita.

5. Supabase y pgvector no se tocan hasta Capa 5.
   MemorySaver es suficiente hasta entonces.

6. LangSmith (Capa 3B) debe degradarse silenciosamente si
   LANGCHAIN_API_KEY no está en el .env. Nunca romper sin esa key.

7. Antes de cada sesión, recordarme en qué capa estamos
   y qué falta completar según el estado de arriba.