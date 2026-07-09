# CHANGELOG
# agentic-rag-fastapi

Registro cronológico de cambios. Cada entrada corresponde a uno o más commits.
Formato: fecha · tipo · descripción · qué capa representa.

---

## 2026-07-07 — Capa 5B.3 arranca: diseño del Postgres checkpointer (sin código todavía)
**Commit:** `cd2d5f9` (solo el commit pendiente de 5B.2, ver entrada de abajo — 5B.3 en sí no tiene código)

- Sesión de diseño para Capa 5B.3 (`MemorySaver` → `PostgresSaver`), sin escribir código todavía. Decisiones tomadas, a implementar la próxima sesión:
  - **Conexión persistente, no por-request:** a diferencia de `rag_search()` (que abre/cierra conexión una vez por consulta del usuario), el checkpointer se invoca en cada transición de nodo del grafo (`agent → tools → agent`), potencialmente varias veces por un solo `/chat`. Abrir/cerrar en cada paso sería mucho más caro — la conexión tiene que vivir durante todo el ciclo de vida de la app.
  - **`graph.py` deja de compilar el grafo él mismo:** hoy `graph = graph_builder.compile(checkpointer=MemorySaver())` corre al importar el módulo, antes de que exista el `lifespan` de `main.py`. Como `PostgresSaver` necesita una conexión real, compilar a nivel de módulo dejaría de ser viable (I/O como efecto secundario de un `import`). Plan: `graph.py` exporta `graph_builder` sin compilar; quien lo importe decide con qué checkpointer compilarlo.
  - **Tres consumidores de `graph` a día de hoy** (`src/main.py`, `tests/conftest.py`, `evals/run_evals.py`) — cada uno va a compilar distinto: `main.py` con `PostgresSaver` (conexión real), `conftest.py`/`run_evals.py` con `MemorySaver()` para no acoplar tests/evals a que Supabase esté arriba.
  - **Patrón de producción para la conexión:** no una conexión cruda, sino un `psycopg_pool.ConnectionPool` abierto en el `lifespan` (startup) y cerrado al shutdown. Razón: los endpoints `def` (sync) de FastAPI corren en un threadpool, así que pueden llegar varios `/chat` concurrentes — una sola conexión compartida entre threads no es segura.
  - **Dependencia nueva:** `langgraph-checkpoint-postgres` (paquete oficial de LangChain para `PostgresSaver`) — trae `psycopg` (v3), no `psycopg2` (el que ya usa `tools.py`). Se acepta la convivencia de dos drivers de Postgres en el repo a propósito — migrar `tools.py` a psycopg3 sería scope creep sin necesidad real.
  - `PostgresSaver` necesita `.setup()` una vez para crear sus tablas propias en Postgres — idempotente, se puede llamar en cada arranque del `lifespan` sin problema.
- **Nada instalado ni codeado todavía** — queda pendiente de confirmación con Juan antes de instalar `langgraph-checkpoint-postgres` y empezar a tocar archivos.
- **Próximo paso concreto:** instalar `langgraph-checkpoint-postgres`, después implementar en orden: `graph.py` (exportar `graph_builder`), `main.py` (pool + `PostgresSaver` + `.setup()` en el `lifespan`), `tests/conftest.py` y `evals/run_evals.py` (compilar con `MemorySaver()`).

---

## 2026-07-04 — Capa 5B.2 completa: rag_search() migrado a Postgres
**Commit:** `cd2d5f9` (commiteado el 2026-07-07, tres días después de escrito)

- `src/tools.py`: pasos 4 y 5 del plan, últimos de 5B.2:
  - `_hybrid_search(conn, query, query_embedding, top_k, candidate_k=10)` — pide `candidate_k=10` candidatos a `_vector_search`/`_keyword_search`, fusiona con `rrf()` de `ingestion.py` (sin cambios, ya era agnóstica al origen del id), corta a `top_k`. Mismo patrón de "candidatos más anchos que el resultado final" que el `InMemoryIndex.hybrid_search()` de 5A.2.
  - `rag_search()` reescrito por completo: abre conexión con `_get_connection()` dentro de un `try/finally` (garantiza `conn.close()` incluso si algo falla a mitad de camino, sin tragarse la excepción), embebe la query con `embed_texts([query])[0]`, llama `_hybrid_search()`, trae `content`/`source` con `SELECT ... WHERE id = ANY(ids)`, y reordena el resultado con un diccionario `{id: (content, source)}` recorriendo `fused` (no las filas de Postgres, que vuelven en su propio orden y no en el de relevancia de RRF).
  - `_index`/`InMemoryIndex`/`set_index()` quedan sin uso real — `rag_search()` ya no los toca. Limpieza pospuesta a un paso 6 aparte (ver abajo).
- **Verificado contra infraestructura real:** `rag_search.invoke({"query": "que es langgraph", "top_k": 3})` contra Supabase trajo los 3 chunks correctos de `langgraph-intro.txt` con scores de RRF coherentes (~0.033 para el resultado en ambas listas). Los 7 tests de `tests/test_rules.py` pasan sin modificar nada — el contrato de `rag_search()` (string JSON, contiene palabras de la query) se mantuvo intacto aunque cambió todo el motor de búsqueda por debajo.
- Repaso de conceptos de la sesión: orden lógico de evaluación SQL (`WHERE`/`HAVING` se evalúan antes que `SELECT`, por eso ninguno de los dos puede usar alias del `SELECT` — corregí una premisa mía equivocada sobre `HAVING` a mitad de la explicación, confirmado con la doc de Postgres), qué hace realmente `to_tsvector`/`plainto_tsquery` (normalizar texto a raíces de palabras sin stopwords) y por qué embeber la query en cada request no se puede cachear igual que los chunks (la tabla `chunks` es el corpus fijo que se reutiliza siempre; la query es la sonda, casi nunca se repite, y guardarla en la misma tabla contaminaría las búsquedas futuras), `try/finally` vs `try/except` para garantizar cierre de conexión sin tragarse errores.
- **Próximo paso concreto:** Capa 5B.3 — Postgres checkpointer. Aparte, pendiente el paso 6 (sesión separada): sacar `build_index()`/`set_index()` del lifespan de `main.py` (re-embebe docs en cada arranque de uvicorn para un índice que ya no se usa) y decidir si se borra `InMemoryIndex` del todo.

---

## 2026-07-03 — Capa 5B.2: pasos 1-3/5 (conexión Postgres + queries SQL)
**Commit:** `2a5657f`

- `src/tools.py`: tres funciones privadas nuevas, primer código real de 5B.2:
  - `_get_connection()` — `psycopg2.connect(DATABASE_URL)` + `register_vector(conn)`, conexión nueva por llamada (sin pool, decisión tomada en la sesión anterior)
  - `_vector_search(conn, query_embedding, top_k)` — `SELECT id, embedding <=> %s AS distance ... ORDER BY distance LIMIT %s`, devuelve `[(chunk_id, distance), ...]`
  - `_keyword_search(conn, query, top_k)` — Postgres FTS (`to_tsvector('spanish', ...)` / `plainto_tsquery` / `ts_rank`), devuelve `[(chunk_id, rank), ...]`
  - Ninguna está conectada todavía a `rag_search()`, que sigue usando `_index` (InMemoryIndex) sin cambios — por eso Pylance marca las tres como "not accessed", esperado hasta el paso 5.
- `scripts/ingest.py`: comentario de `register_vector` ampliado para explicar que traduce el tipo `vector` en los dos sentidos (Python→Postgres al insertar, Postgres→Python al mandar el embedding de la query como parámetro en `_vector_search`).
- Repaso de conceptos de la sesión: pool de conexiones vs. conexión por request (por qué el `InMemoryIndex` sí puede ser global/compartido y una conexión a Postgres no — dato inmutable vs. estado de conversación), TCP vs HTTP, sockets, el operador `<=>` de pgvector, parametrización con `%s` y por qué previene SQL injection, orden lógico de evaluación de SQL (`WHERE` se evalúa antes que `SELECT`, por qué `plainto_tsquery` se repite en la query de FTS).
- **Housekeeping:** `.claude/skills/actualizar-roadmap-changelog.skill` estaba como ZIP sin extraer (Claude Code no lo reconocía como skill). Se extrajo a `.claude/skills/actualizar-roadmap-changelog/SKILL.md` y se borró el zip original.
- **Inconsistencia encontrada y corregida en ROADMAP.md:** la línea de `tools.py` en "Estado actual del repo" todavía decía "cosine similarity real" sin mencionar el hybrid search (TF-IDF + RRF) agregado en 5A.2 — quedó desactualizada desde esa sesión (2026-07-01).
- **Próximo paso concreto:** paso 4 de 5B.2 — fusionar `_vector_search()` + `_keyword_search()` con `rrf()`. Después, paso 5: reemplazar `_index.hybrid_search()` dentro de `rag_search()`, resolviendo cómo traer `content`/`source` para cada `id` ganador del RRF.

---

## 2026-07-02 — Repaso 5B.0/5B.1 + commit + arranque de 5B.2 (sin código todavía)
**Commit:** `834e71a`

- Repaso de active recall de las tres preguntas pendientes de la sesión anterior (HNSW vs IVFFlat/B-tree, por qué separar ingesta de serving, por qué TRUNCATE) — las tres cerradas y entendidas.
- `scripts/ingest.py`: se agregaron comentarios en primera persona sobre cada función y paso del flujo, a pedido de Juan, para reforzar la comprensión.
- **Hallazgo de seguridad:** `.env` estaba trackeado en git desde el commit `0e97122` (antes de existir `.gitignore`), a pesar de que `.gitignore` ya lo excluye. Con el `DATABASE_URL` nuevo a punto de commitearse, eso hubiera expuesto la password real de Supabase en el historial de GitHub. Se corrigió con `git rm --cached .env` en este mismo commit — `.env` sigue en disco, pero deja de versionarse desde ahora.
- **Pendiente sin resolver (no bloquea 5B.2):** las credenciales reales (`OPENAI_API_KEY`, `DATABASE_URL`) siguen visibles en commits viejos del historial de git. Falta (a) rotar esas keys y (b) limpiar el historial (`git filter-repo` o similar) antes de publicar el repo.
- **5B.2 arrancó pero sin código:** se definió el plan de 5 pasos (ver ROADMAP.md) y se tomó la primera decisión — `rag_search()` va a abrir/cerrar una conexión psycopg2 nueva en cada llamada (igual que `scripts/ingest.py`), sin connection pool todavía. El pool queda anotado como mejora de rendimiento para más adelante, una vez que la versión simple ande.
- **Próximo paso concreto (para la próxima sesión):** implementar la pieza 1 — la conexión a Postgres dentro de `rag_search()` (o un helper nuevo), reemplazando el uso de `_index` para esa parte. Después seguir con la query de vector search (paso 2 del plan).

---

## 2026-07-01 — Capa 5B.0 + 5B.1: infraestructura Supabase + script de ingesta
**Commit:** `834e71a` (commiteado el 2026-07-02, un día después de escrito)

- **5B.0 (infra Supabase):** proyecto Supabase creado, extensión `vector` habilitada, tabla `chunks` (`id`, `content text`, `source text`, `chunk_index int`, `embedding vector(1536)`) + índice `hnsw` (`vector_cosine_ops`). Conexión verificada con `psycopg2` usando `DATABASE_URL` (Session pooler, usuario `postgres.<project-ref>`)
- `.env.example`: agrega `DATABASE_URL` (además, se corrigió que el archivo estaba guardado en UTF-16 en vez de UTF-8 — se leía corrupto)
- `requirements.txt`: agrega `psycopg2-binary==2.9.11` y `pgvector==0.4.1`
- **5B.1 (script de ingesta):** `scripts/ingest.py` (nuevo) — lee `docs/*.txt`, reutiliza `chunk_text`/`embed_texts` de `src/ingestion.py`, hace `TRUNCATE` + insert batch (`execute_values`) en la tabla `chunks`. Se corre a mano (`python -m scripts.ingest`), no en el lifespan de `main.py` — ingesta y serving quedan separados a propósito
- **Verificado:** 16 chunks insertados desde `langgraph-intro.txt` con `chunk_index` correcto por documento
- `rag_search()` **no cambió** — sigue usando el `InMemoryIndex` de 5A.2. La tabla de Supabase está poblada pero todavía no la consulta nadie (eso es 5B.2)
- `ROADMAP.md` actualizado: 5B.0 y 5B.1 marcadas completas, próximo paso es 5B.2

**Nota de proceso (para retomar mañana):** esta sesión avanzó dos sub-capas seguidas (5B.0 y 5B.1) sin pausar entre piezas para preguntas de comprensión — más rápido de lo que pide el estilo de trabajo acordado (AGENTS.md / COPILOT_STRATEGY.md: ir de a poco, explicar, pregunta de active recall, esperar respuesta). Mañana conviene repasar ambas piezas con calma antes de seguir a 5B.2:
- ¿Por qué HNSW en vez de IVFFlat, y qué hace distinto de un índice normal de Postgres (B-tree)?
- ¿Por qué separar el script de ingesta del lifespan de `main.py` en vez de reconstruir todo en cada arranque?
- ¿Por qué `TRUNCATE` antes de insertar, y qué pasaría si se corriera el script sin el truncate?

**Pendiente futuro (no bloquea 5B):** sumar soporte de PDFs reales en la ingesta antes de publicar el repo — la tabla ya es agnóstica a la fuente, solo falta extracción de texto (pypdf/pdfplumber) en `scripts/ingest.py`.

---

## 2026-06-20 — Capa 5A completa: RAG en memoria con embeddings y cosine similarity
**Commit:** `feat: Capa 5A`

- `src/ingestion.py` (nuevo): pipeline completo — chunking con ventana deslizante, embeddings con `text-embedding-3-small`, `InMemoryIndex` con numpy
- `src/tools.py`: `rag_search()` reemplaza stub por cosine similarity real sobre el índice; devuelve lista de `RAGResult` con scores reales
- `src/main.py`: `lifespan` construye el índice al arrancar leyendo `docs/*.txt`; reemplaza `@app.on_event` deprecado
- `docs/langgraph-intro.txt` (nuevo): base de conocimiento inicial sobre LangGraph, alineada con el golden_set
- `requirements.txt`: agrega `numpy==2.4.6` y `langsmith==0.7.37`
- `ROADMAP.md`, `CHANGELOG.md`, `STACK.md`: documentación actualizada

**Verificado:** endpoint `/chat` llama `rag_search()` de forma real (confirmado con print temporal en uvicorn)

**Deuda técnica pendiente:**
- `test_rag_search_contains_query_word` pasa por razones equivocadas (índice vacío en tests)
- `ChatResponse.tool_calls_used` siempre devuelve `[]` — no se popula todavía

---

## 2026-06-07 — Capa 4 completa: schemas Pydantic
**Commit:** `f552cfd`

- Nuevo `src/schemas.py` con los 4 modelos del sistema:
  - `ChatRequest` / `ChatResponse` — contrato del endpoint `/chat`
  - `TicketInput` — args_schema que LangChain usa para describir `create_ticket()` al LLM
  - `RAGResult` — contrato de salida de `rag_search()`, listo para Capa 5
- `src/main.py` — endpoint `/chat` tipado: recibe `ChatRequest`, devuelve `ChatResponse`
- `src/tools.py` — `create_ticket` con `args_schema=TicketInput`; `rag_search` serializa `RAGResult`
- `pytest.ini` — configuración de pytest centralizada

---

## 2026-06-03 — Baseline evals registrado
**Commit:** `0e97122`

- Primera corrida de evals guardada en `evals/results/2026-06-03/`
- Métricas de baseline: relevance 5.0/5, citation 5%, convergence 3.7 pasos promedio
- Referencia para comparar cuando `rag_search()` sea real en Capa 5

---

## 2026-06-02 — Capa 3B completa: observabilidad con LangSmith
**Commit:** `1d2bd23`

- `evals/evaluators.py` — `relevance_evaluator` decorado con `@traceable` (opt-in: solo si hay `LANGCHAIN_API_KEY`)
- `evals/run_evals.py` — scores enviados a LangSmith con `client.create_feedback()`
- `evals/golden_set.json` — 20 preguntas sobre LangGraph docs con `expected_answer` y `category`
- `.github/workflows/ci.yml` — `LANGCHAIN_API_KEY` como secret de CI
- `.env.example` actualizado con placeholders de LangSmith
- Regla activa: si no hay API key, LangSmith se desactiva silenciosamente

---

## 2026-05-12 — CI: reporte HTML de tests
**Commit:** `72d8b1d`

- `ci.yml` — job de rules genera reporte HTML con `pytest-html` y lo sube como artefacto
- `requirements.txt` — agrega `pytest-html`
- `.gitignore` — ignora `tests/reports/` (reportes locales no van al repo)

---

## 2026-05-11 — Capa 2 completa: CI con GitHub Actions
**Commit:** `8559383`

- `.github/workflows/ci.yml` — pipeline con dos jobs:
  - `rules`: corre en cada push (determinista, sin API, ~0.05s)
  - `evals`: corre solo en `main` con `MAX_EVAL_CASES=1` (con API key)
- `requirements.txt` reemplazado por dependencias limpias y mínimas

---

## 2026-05-10 — Tests de evaluación (LLM-as-judge)
**Commit:** `1c52e06`

- `tests/test_evals.py` — evaluaciones con LLM-as-judge:
  - `TestRelevanceEval`: relevance score ≥ 3/5 para respuestas de RAG y ticket
  - `TestTraceEval`: convergence (≥ 2 pasos en traza)

---

## 2026-05-09 — Tests deterministas
**Commit:** `e4bfa36`

- `tests/test_rules.py` — 4 tests sin LLM ni API:
  - `TestResponseFormat`: respuestas no vacías, bajo 1000 chars
  - `TestToolBehavior`: `rag_search` y `create_ticket` devuelven strings con el input

---

## 2026-05-08 — Fixtures compartidos de tests
**Commit:** `5674b7a`

- `tests/conftest.py` — fixtures de sesión:
  - `agent_graph`: grafo compilado reutilizable
  - `sample_responses`: ejemplos válidos/inválidos para reglas
  - `invoke_agent`: helper con skip automático si no hay `OPENAI_API_KEY`

---

## 2026-05-04 — Capa 1 completa: FastAPI + validación de config
**Commit:** `f6f5ca8`

- `src/config.py` — `load_settings()` valida `OPENAI_API_KEY` al startup (fail fast)
- `src/main.py` — endpoint `POST /chat` con `thread_id` para persistencia por conversación

---

## 2026-05-01 — Herramientas y grafo del agente
**Commit:** `7f158da`

- `src/tools.py` — stubs `rag_search()` y `create_ticket()` con `@tool`
- `src/graph.py` — `StateGraph` con routing condicional:
  - `agent_node` → `route_after_agent` → `tools` (si hay tool_calls) o `END`
  - Compilado con `MemorySaver` para persistencia en memoria

---

## 2026-04-29 — Estado del agente
**Commit:** `724eff4`

- `src/state.py` — `AgentState` con `TypedDict` + `add_messages` (reducer de LangGraph)

---

## 2026-04-28 — Estructura inicial del repo
**Commits:** `65d1bc2`, `4807156`

- Estructura de carpetas: `src/`, `tests/`, `evals/`
- `.gitignore` inicial
