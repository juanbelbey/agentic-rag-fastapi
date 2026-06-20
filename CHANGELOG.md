# CHANGELOG
# agentic-rag-fastapi

Registro cronológico de cambios. Cada entrada corresponde a uno o más commits.
Formato: fecha · tipo · descripción · qué capa representa.

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
