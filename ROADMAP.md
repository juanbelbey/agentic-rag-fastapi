# ROADMAP.md
# agentic-rag-fastapi — project status & architecture
# Juan Belbey

## Qué es este archivo

Fuente de verdad del estado actual del proyecto: qué está construido, por qué,
y qué queda pendiente. Creció de forma incremental, módulo por módulo,
siguiendo el curriculum del LLM Zoomcamp (DataTalks.Club) — el mapa de capas
de abajo refleja ese orden de construcción. El historial commit por commit
vive en `CHANGELOG.md`; las decisiones basadas en datos (experimentos de
retrieval/generación) viven en `EXPERIMENTS.md`.

---

## Resumen

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
CAPA 5 — RAG real con PDFs            ✅ COMPLETADA
  5A  — Índice en memoria (numpy)     ✅ COMPLETADA
  5A.2 — Hybrid search + RRF          ✅ COMPLETADA
  5B  — pgvector/Supabase + FTS       ✅ COMPLETADA
    5B.0 — Infraestructura Supabase   ✅ COMPLETADA
    5B.1 — Script de ingesta          ✅ COMPLETADA
    5B.2 — Migrar rag_search()        ✅ COMPLETADA
    5B.3 — Postgres checkpointer      ✅ COMPLETADA (verificado contra Supabase
                                          real: setup() crea tablas, persistencia
                                          por thread_id confirmada)
    5B.4 — Corpus real + evals M4     ✅ COMPLETADA (+ corpus sintético para
                                          reproducibility, ver CORPUS_INSTRUMENTACION.MD)
CAPA 6 — Deploy                       ✅ Render (backend) — AWS queda pendiente
                                          para otro momento

Post-submission hardening (2026-09-01, ver EXPERIMENTS.md para el detalle):
FASE 1 — Failure observability        ✅ COMPLETADA
FASE 2 — Agent reliability            ✅ COMPLETADA
FASE 3 — Testing gaps                 ✅ COMPLETADA
FASE 4 — Critical eval set + abstención ✅ COMPLETADA (gap conocido y documentado:
                                          preguntas con una parte real + una
                                          inventada en la misma pregunta)
FASE 5 — CI en 3 niveles              ✅ COMPLETADA
FASE 6 — README (problema/caso de uso) 🔶 EN CURSO (intro reescrita con feedback
                                          real de evaluadores; falta sección de
                                          hardening en el README)
```

Nunca se salta una capa. Nunca se espera terminar todos los cursos
para empezar a construir.

---

## Estado actual del repo

Historial detallado (fechas, commits, debugging paso a paso) vive en `CHANGELOG.md`.
Decisiones basadas en datos (comparaciones antes/después) viven en `EXPERIMENTS.md`.
Acá solo el estado actual: qué hace cada módulo y qué decisiones técnicas activas
importan para entender su comportamiento hoy.

```
src/
├── config.py
├── state.py
├── tools.py
├── graph.py
├── main.py
├── schemas.py
├── ingestion.py
└── logging_config.py
```

- **`config.py`** — valida `OPENAI_API_KEY` al arranque (fail-fast).
- **`state.py`** — `AgentState` (`TypedDict` + reducer `add_messages`).
- **`logging_config.py`** — `JSONFormatter` sobre `logging` estándar (sin dependencia
  nueva), `configure_logging()` llamado al arranque en `main.py`. Todos los `except`
  que antes fallaban en silencio (`except Exception: pass` de inserts best-effort,
  feedback a LangSmith) ahora loguean con `logger.exception(...)` antes de continuar.
- **`tools.py`** — `rag_search()` sobre Postgres/pgvector:
  - `_vector_search` (similitud coseno sobre `embedding`).
  - `_keyword_search` — full-text search de Postgres con `config='simple'` (el corpus
    mezcla ES/EN) y un `tsquery` armado a mano con OR entre palabras
    (`_build_or_tsquery`) + lista de stopwords ES/EN — `plainto_tsquery` (AND de todas
    las palabras) es inviable con preguntas parafraseadas de 15-20 palabras.
  - `_rewrite_query_impl()` — reescribe la query a inglés técnico antes del keyword
    search (`gpt-4o-mini`, `temperature=0`, cacheada con `@lru_cache`) — el vector
    search no la necesita (embedding ya multilingüe).
  - `_hybrid_search` — fusiona vector + keyword con Reciprocal Rank Fusion (`rrf()`,
    `k=1` — valor elegido tras un barrido real contra 520 preguntas, no el `k=60`
    típico de RRF, ver `EXPERIMENTS.md`).
  - `create_ticket()` con `TicketInput` — sigue siendo un stub (`print()` + string),
    sin persistencia real en Postgres todavía.
  - `_vector_search`/`_keyword_search`/`_rewrite_query_impl` instrumentados con
    `@traceable` (LangSmith), opt-in por `LANGCHAIN_API_KEY` — sin esa key, no traza
    nada y no rompe.
  - `_search_chunks()` (conexión + `_hybrid_search` + fetch) decorada con
    `@tenacity.retry` (reintenta solo `psycopg2.OperationalError` — conexión/timeout,
    no errores de query — 3 intentos, backoff exponencial, cada intento abre una
    conexión nueva). Clientes de OpenAI (`tools.py`/`ingestion.py`) y `ChatOpenAI` de
    `graph.py` con `max_retries` explícito (`MAX_RETRIES`).
  - Pendiente: pool de conexiones (hoy abre una conexión nueva por request) y FTS por
    idioma real (columna `language` + `to_tsvector` por idioma, en vez del `'simple'`
    global — sobre-ingeniería para 11 documentos hoy, reconsiderar si el corpus crece).
- **`graph.py`** — `StateGraph` con routing condicional entre `agent` y `tools`.
  `SYSTEM_PROMPT` se carga desde `prompts/` (no vive inline) vía `load_prompt()` —
  incluye reglas de abstención (rechazo fuera de dominio, no generalizar entre
  productos similares, pedir aclaración ante ambigüedad, verificar cada parte de
  preguntas multi-afirmación, citar solo nombre de documento). En producción:
  `TEMPERATURE = 0.3`, `system_prompt_direct_answer.txt`, `gpt-4o-mini`,
  `max_tokens=800` — elegidos comparando variantes prompt×modelo×temperatura con datos
  reales (ver `EXPERIMENTS.md`). `RECURSION_LIMIT = 25` explícito (el default de
  LangGraph en la versión instalada es 10007 — prácticamente sin techo). Exporta
  `graph_builder` sin compilar — cada consumidor (`main.py`, tests, evals) decide su
  propio checkpointer.
- **`main.py`** — FastAPI: `POST /chat`, `POST /feedback`, `GET /stats`. El `lifespan`
  abre un pool real de Postgres (`psycopg_pool`), corre `checkpointer.setup()` (el
  checkpointer de LangGraph es Postgres, no `MemorySaver`) y crea las tablas
  `feedback`/`chat_logs` de forma idempotente (con columnas `status`/`error_type`).
  `/chat` registra latencia y costo estimado (tokens × precio de `gpt-4o-mini`) en
  `chat_logs` vía el helper `_log_chat()`, incluso si `graph.invoke()` falla (antes un
  fallo del agente era invisible: no quedaba fila en `chat_logs`). `except
  GraphRecursionError` propio (antes del `except Exception` genérico) con mensaje
  claro al cliente en vez del traceback crudo. El insert es best-effort (no rompe la
  respuesta si falla), pero ahora logueado. Rate limiting con `slowapi` (`/chat`
  10/min, `/feedback` 20/min, `/stats` 30/min) por IP real (`get_ipaddr`, necesario
  porque Render corre detrás de un proxy). Sin `GET /health` todavía (mejora anotada,
  no bloqueante — Render usa el chequeo TCP del puerto).
- **`schemas.py`** — `ChatRequest`/`ChatResponse`/`TicketInput`/`RAGResult`/
  `FeedbackInput` (Pydantic). `TicketInput.category` usa 4 categorías del dominio real
  (`field_instrument_failure`/`biological_process_anomaly`/`pump_maintenance`/
  `undocumented_query`). `RAGResult.score` documentado como score de fusión RRF, no
  similitud coseno.
- **`ingestion.py`** — `chunk_text()` (ventana deslizante) + `embed_texts()` (batchea
  de a 300 textos por request de embeddings) + `rrf()` (algoritmo de fusión, usado por
  `tools.py`). Cliente de OpenAI creado de forma perezosa (no al importar el módulo,
  para que el job `rules` de CI corra sin `OPENAI_API_KEY`).

```
scripts/
├── ingest.py
└── generate_synthetic_corpus.py
```

- **`scripts/ingest.py`** — ingesta manual (`python -m scripts.ingest`, no la llama la
  app): lee `docs/*.txt` y `docs/pdfs/*.pdf` por defecto (extracción con `pypdf`, sin
  OCR; `INGEST_PDFS_DIR` permite apuntar a `docs/pdfs_synthetic` en su lugar), chunkea
  (`CHUNK_SIZE=1000`/`CHUNK_STEP=800`, más grande que el default de `chunk_text()`
  porque estos manuales son más densos), embebe y hace `TRUNCATE` + insert en la tabla
  `chunks` de Supabase. Separado a propósito de `main.py` — ingesta y serving son
  responsabilidades distintas.
- **`scripts/generate_synthetic_corpus.py`** — genera los 11 PDFs de
  `docs/pdfs_synthetic/` con `gpt-4o-mini` (marcas/modelos ficticios: AquaPress,
  Rivertek, FieldSense) y `fpdf2`, mismo mix que el corpus real (3 fabricantes,
  manual/quickstart/datasheet). Script manual, no lo llama la app ni CI — ver
  `CORPUS_INSTRUMENTACION.MD`, sección "Corpus sintético".

```
docs/
├── pdfs/                (gitignored)
└── pdfs_synthetic/      (11 PDFs, comiteados)
archive/
└── langgraph-intro.txt
```

- **`docs/pdfs/`** — 11 manuales oficiales de instrumentación de campo (Emerson/
  Rosemount, Siemens Sitrans, Endress+Hauser), no committeados por copyright — ver
  `CORPUS_INSTRUMENTACION.MD`.
- **`docs/pdfs_synthetic/`** — 11 PDFs sintéticos equivalentes, sí comiteados: permite
  a un reviewer correr `scripts/ingest.py` de punta a punta sin descargar el corpus
  real a mano (criterio de reproducibility del Zoomcamp). No reemplaza el corpus real
  para las métricas ya reportadas (el ground truth se generó contra el real) — ver
  `CORPUS_INSTRUMENTACION.MD`, sección "Corpus sintético".
- **`archive/langgraph-intro.txt`** — corpus viejo (LangGraph docs), movido fuera de
  `docs/` para que no se mezcle con la ingesta real.

```
tests/
├── conftest.py
├── test_rules.py
├── test_evals.py
├── test_graph.py
├── test_tools.py
├── test_evaluators.py
├── test_logging_config.py
├── test_abstention_threshold.py
├── test_critical_eval_set.py
└── reports/
```

- **`conftest.py`** — fixtures compartidos (`agent_graph` compila `graph_builder` con
  `MemorySaver`, no depende de Postgres para correr).
- **`test_rules.py`** — tests deterministas; los que llaman `rag_search()` de
  verdad se saltan solos (`pytest.skip`) si falta `OPENAI_API_KEY`/`DATABASE_URL`.
- **`test_evals.py`** — LLM-as-judge reusando `evals/evaluators.py`: relevancia (RAG
  normal), tool routing (escalamiento) y abstención (pregunta fuera de dominio) —
  mismos 3 casos que corre el job `smoke` de CI.
- **`test_graph.py`** — config de `graph.py` sin invocar el LLM real (`MAX_RETRIES`,
  `RECURSION_LIMIT`), `route_after_agent()` en aislamiento total, y regresión de las
  reglas de abstención del prompt (`SYSTEM_PROMPT` contiene los substrings clave).
- **`test_tools.py`** — retry de `_search_chunks()` mockeado (se recupera, agota
  intentos, no reintenta errores no transitorios) — sin Postgres real.
- **`test_evaluators.py`** — evaluadores code-based/puros de `evals/evaluators.py`
  (`extract_score`, `tool_call_evaluator`, `convergence_evaluator`) — sin LLM.
- **`test_logging_config.py`** — `JSONFormatter` de `src/logging_config.py`.
- **`test_abstention_threshold.py`** — lógica pura de `evals/abstention_threshold.py`
  (conteo de falsos positivos/negativos), sin OpenAI/Postgres.
- **`test_critical_eval_set.py`** — estructura de `evals/critical_eval_set.json`
  (categorías válidas, ids únicos, etc.).
- **`reports/`** — reportes HTML de `pytest-html`, local y como artefacto de CI.

```
evals/
├── golden_set.json
├── ground_truth_retrieval.json
├── critical_eval_set.json
├── generate_ground_truth.py
├── generate_golden_set.py
├── retrieval_metrics.py
├── evaluators.py
├── run_evals.py
├── abstention_threshold.py
├── critical_set_agent_check.py
├── compare_prompts.py
├── compare_temperature.py
├── cost_report.py
├── ragas_eval.py
├── experiments_log.csv
└── results/
```

- **`golden_set.json`** — 56 casos: 48 con `expected_answer` (generada por LLM,
  grounded en chunks reales del corpus) + 8 de escalamiento con `expected_tool=
  "create_ticket"` (2 por categoría de `TicketInput`).
- **`generate_ground_truth.py` / `ground_truth_retrieval.json`** — 520 preguntas de
  retrieval (factual/procedimental/inferencial/borde) generadas con LLM + structured
  output, ancladas a ventanas de chunks de los 11 documentos. Script manual, no lo
  llama la app ni CI.
- **`generate_golden_set.py`** — samplea 48 de las 520 preguntas (12 por categoría) y
  genera `golden_set.json` con `expected_answer` grounded — mide generación, no
  retrieval (eso lo mide `ground_truth_retrieval.json`).
- **`critical_eval_set.json`** — 28 casos curados a mano (15 answerable + 13
  unanswerable, verificados contra los PDFs reales) para medir abstención: fuera de
  dominio, relacionado pero ausente, producto no documentado, ambigua, mixta (una
  parte real + una inventada). No es un muestreo aleatorio del golden set — diseño
  propio, ver `EXPERIMENTS.md`.
- **`retrieval_metrics.py`** — `hit_rate`/`mrr`/`evaluate()` para vector-only,
  keyword-only e hybrid, más el barrido de `k` de RRF. Script manual, corre en el job
  `full_eval` de CI (manual).
- **`evaluators.py`** — `relevance` (LLM-judge sin referencia), `accuracy` (LLM-judge
  contra `expected_answer`), `abstention` (LLM-judge: ¿rechazó una pregunta fuera de
  dominio en vez de responderla?), `citation`/`convergence` (code-based),
  `tool_call_evaluator` (code-based, verifica si la tool esperada apareció en la
  traza). Todos instrumentados con `@traceable` para LangSmith.
- **`abstention_threshold.py`** — barrido de umbral (RRF y distancia coseno) contra
  `critical_eval_set.json` — **descartado como solución**, ningún umbral separa
  answerable de unanswerable con evidencia suficiente (ver `EXPERIMENTS.md`). La
  abstención real quedó resuelta en el prompt (`graph.py`/`system_prompt_direct_answer.txt`),
  no con un corte numérico en código.
- **`critical_set_agent_check.py`** — corre el agente completo (no solo retrieval)
  contra `critical_eval_set.json` para revisión manual de las respuestas unanswerable.
- **`run_evals.py`** — corre el golden set completo (56 casos), guarda resultados por
  fecha/hora, manda feedback a LangSmith. Corre en el job `full_eval` de CI (manual,
  `workflow_dispatch`) — no en cada push.
- **`compare_prompts.py` / `compare_temperature.py`** — scripts manuales para comparar
  prompt×modelo y temperatura de forma aislada (una variable por vez). No corren en CI
  (decisión: son experimentos puntuales ya cerrados y documentados en `EXPERIMENTS.md`,
  no gates de regresión continuos).
- **`cost_report.py`** — costo/tokens reales por variante, leyendo traces de LangSmith.
- **`ragas_eval.py`** — 4 métricas de RAGAS (faithfulness, answer relevancy, context
  precision/recall) sobre los 48 casos con `expected_answer`, contra los chunks que el
  agente realmente vio en la traza (no una llamada aparte a `_hybrid_search`).
- **`results/`** — resultados de cada corrida, organizados por `YYYY-MM-DD/HH-MM-SS`.
- **`experiments_log.csv`** — historial de experimentos de retrieval/generación en
  formato largo, insumo de `EXPERIMENTS.md`.

```
.github/workflows/
└── ci.yml
```

- **`ci.yml`** — 3 niveles (ver `EXPERIMENTS.md` para el diseño):
  - **`rules`** (Nivel 1) — todo push/PR, 0 llamadas a LLM/DB real, tests deterministas.
  - **`smoke`** (Nivel 2) — solo push a `main`, 3 casos fijos contra el agente completo
    (RAG normal, tool routing, abstención) — gate de humo antes de mergear, costo
    mínimo. Reemplazó el `MAX_EVAL_CASES=1` (1 caso arbitrario) que corría antes.
  - **`full_eval`** (Nivel 3) — solo manual (`workflow_dispatch`), golden set completo
    (56 casos), RAGAS y retrieval (520 preguntas) — la evaluación sistemática completa,
    nunca automática en cada push.
  - Secrets: `OPENAI_API_KEY`/`DATABASE_URL` (rol de Postgres de solo lectura
    `ci_readonly`, `SELECT` únicamente sobre `chunks`, con RLS scopeada, para no
    exponer la credencial completa de producción en CI).

```
Dockerfile / .dockerignore
render.yaml
docker-compose.yml
```

- **`Dockerfile`** (raíz, backend) — `python:3.12-slim`, copia `requirements.txt` antes
  que `src/`/`prompts/` (cachea la capa de dependencias), `CMD` en forma shell
  (`exec uvicorn ... --port ${PORT:-8000}`) para tomar el puerto que Render inyecta en
  runtime y recibir `SIGTERM` directo. No incluye `docs/pdfs/` ni `.env`.
- **`render.yaml`** — Blueprint de Render para el backend: `runtime: docker` sobre el
  `Dockerfile` de arriba, `plan: free`/`region: oregon`, secrets cargados a mano en el
  dashboard (nunca committeados). Deploy real en
  `https://agentic-rag-fastapi.onrender.com`.
- **`docker-compose.yml`** — levanta `backend` (`Dockerfile` de la raíz) y `frontend`
  (`streamlit_app/Dockerfile`) juntos, en la red interna que crea Compose — cada
  servicio es accesible por su nombre como hostname (`BACKEND_URL=http://backend:8000`).

```
streamlit_app/
├── app.py
├── Dockerfile
├── requirements.txt
├── .streamlit/config.toml
└── pages/
    └── 1_📊_Monitoring.py
```

- **`app.py`** — frontend de chat: consume `POST /chat`/`POST /feedback` del backend,
  no toca `src/`. Historial y `thread_id` en `st.session_state` (persistencia real de
  la conversación la da el checkpointer de Postgres, vía `thread_id`). Botones 👍/👎
  ligados al `run_id` de cada respuesta. Maneja errores HTTP (429 del rate limit,
  backend caído) sin mostrar un stack trace crudo. `BACKEND_URL` resuelve en este
  orden: variable de entorno (docker-compose) → `st.secrets` (Streamlit Cloud) →
  `localhost` (dev local).
- **`pages/1_📊_Monitoring.py`** — dashboard de monitoring, consume `GET /stats` (no
  conecta a Postgres directo, para no exponer `DATABASE_URL` en un secret público). 4
  metric tiles (requests totales, latencia promedio, costo estimado total, % feedback
  positivo) + 5 gráficos (requests/día, latencia/día, costo acumulado, uso de tools,
  feedback), con pandas + Altair (paleta de colores validada, no la default de
  Streamlit). Capturas en `docs/screenshots/` (chat + monitoring), enlazadas desde el
  README junto con el link al live demo.
- **`Dockerfile`** — imagen del frontend para `docker-compose` (Streamlit Community
  Cloud no la usa, hace build directo desde el repo).
- **`requirements.txt`** — aislado del de la raíz (solo `streamlit`/`requests`) para no
  instalar las dependencias pesadas del backend (`psycopg`/`ragas`/`langgraph`) en
  Streamlit Cloud.

**Otros documentos del repo:** `EXPERIMENTS.md` (decisiones basadas en datos, versión
"para portfolio/entrevista" de los experimentos de retrieval y generación) y
`CORPUS_INSTRUMENTACION.MD` (de dónde sale el corpus y su estado de compliance).
