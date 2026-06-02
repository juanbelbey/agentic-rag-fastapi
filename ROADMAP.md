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
- LangSmith (observabilidad y evals) — se integra en Capa 3B
- Supabase (Postgres + pgvector) — se incorpora en Capa 5
- GitHub Actions (CI)
- Deploy: Render/Fly.io (H1) → AWS (H2)

---

## Mapa de capas

```
CAPA 1 — Esqueleto del agente         ← COMPLETADA
CAPA 2 — Tests y CI                   ← COMPLETADA
CAPA 3 — Observabilidad y evals       ← EN PROGRESO
  3A — Evaluadores a mano             ← COMPLETADA
  3B — Integración LangSmith          ← PENDIENTE
CAPA 4 — Outputs tipados con Pydantic ← PENDIENTE
CAPA 5 — RAG real con PDFs            ← PENDIENTE (H2, LLM Zoomcamp)
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
├── tools.py       ✅ rag_search() y create_ticket() como stubs (@tool)
├── graph.py       ✅ StateGraph con routing condicional y MemorySaver
├── prompts.py     ✅ system prompts
└── main.py        ✅ FastAPI con POST /chat y persistencia por thread_id

tests/
├── conftest.py    ✅ fixtures: agent_graph, sample_responses, invoke_agent
├── test_rules.py  ✅ 7 tests deterministas, sin API, 0.05s
├── test_evals.py  ✅ LLM-as-judge usando evaluators.py compartido
└── reports/       ✅ pytest-html local + artefacto en CI

evals/
├── golden_set.json  ✅ 20 preguntas sobre LangGraph docs
├── evaluators.py    ✅ relevance, citation, convergence evaluators
├── run_evals.py     ✅ corre evals y guarda en results/ por fecha/hora
└── results/         ✅ JSONs organizados por YYYY-MM-DD/HH-MM-SS

.github/
└── workflows/
    └── ci.yml     ✅ rules en cada push, evals solo en main (MAX_EVAL_CASES=1)

── PENDIENTE ──
Capa 3B: integración LangSmith (ver sección más abajo)
Capa 4: src/schemas.py + outputs tipados
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

## Capa 3B — LangSmith ⬜ PENDIENTE

**Por qué LangSmith y no Phoenix:**
- Integración nativa con LangGraph (una variable de entorno, sin cambiar graph.py)
- Es lo que piden en entrevistas para roles con LangGraph
- Tier gratuito: 5.000 trazas/mes

**Setup:**
```bash
pip install langsmith
```
```
# Agregar al .env:
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...   ← obtener en smith.langchain.com
LANGCHAIN_PROJECT=agentic-rag-fastapi
```

**Archivos a modificar:**
- `evals/run_evals.py` — enviar scores con `client.create_feedback()`
- `evals/evaluators.py` — decorar `relevance_evaluator` con `@traceable`
- `.github/workflows/ci.yml` — agregar LANGCHAIN_API_KEY como secret
- `.env.example` — agregar las tres variables con placeholders

**Regla crítica:** si LANGCHAIN_API_KEY no está en el .env, LangSmith
se desactiva silenciosamente. El código nunca debe romper sin esa key.

---

## Capa 4 — Pydantic for LLM Workflows ⬜ PENDIENTE

**Curso:** DeepLearning.AI

**Qué se construye:**
- `src/schemas.py` con modelos Pydantic:
  - `ChatRequest` — validación del input de /chat
  - `ChatResponse` — respuesta tipada del agente
  - `Ticket` — estructura para create_ticket()
  - `RAGResult` — estructura para rag_search()
- El endpoint /chat pasa de dict a ChatRequest validado
- create_ticket() pasa de string a objeto Ticket validado

**Por qué importa:** Ticket validado con Pydantic está listo para
insertarse en Postgres cuando llegue Supabase en Capa 5.

---

## Capa 5 — RAG real con PDFs ⬜ PENDIENTE (H2)

**Curso:** LLM Zoomcamp — DataTalks.Club
**Decisión:** Zoomcamp sobre Coursera (proyecto real + comunidad + profundidad)
**Timing:** arranca junio 2026, para entonces Capas 1-4 están completas

**Qué se construye:**
- Reemplazar rag_search() stub por retrieval real
- Ingesta de PDFs: chunking + embeddings + insert en pgvector
- Supabase como base de datos (Postgres + pgvector)
- rag_search() conecta a Supabase y devuelve chunks relevantes
- MemorySaver se migra a Postgres checkpointer
- test_evals.py pasa de known_context fijo a chunk real recuperado

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
