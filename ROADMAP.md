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
CAPA 5 — RAG real con PDFs            ← EN PROGRESO
  5A  — Índice en memoria (numpy)     ✅ COMPLETADA (2026-06-20)
  5A.2 — Hybrid search + RRF          ✅ COMPLETADA (2026-07-01)
  5B  — pgvector/Supabase + FTS       ← EN PROGRESO
    5B.0 — Infraestructura Supabase   ✅ COMPLETADA (2026-07-01)
    5B.1 — Script de ingesta          ✅ COMPLETADA (2026-07-01)
    5B.2 — Migrar rag_search()        ← EN PROGRESO (plan definido, código sin empezar)
    5B.3 — Postgres checkpointer      ← PENDIENTE
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
├── tools.py       ✅ rag_search() con cosine similarity real + create_ticket() con TicketInput
├── graph.py       ✅ StateGraph con routing condicional y MemorySaver
├── prompts.py     ✅ system prompts
├── main.py        ✅ FastAPI POST /chat + lifespan construye índice al arrancar
├── schemas.py     ✅ ChatRequest, ChatResponse, TicketInput, RAGResult (Capa 4)
└── ingestion.py   ✅ chunking + embeddings OpenAI + InMemoryIndex numpy + KeywordIndex TF-IDF + rrf() (Capa 5A/5A.2)

scripts/
└── ingest.py      ✅ ingesta manual: docs/*.txt → chunks → embeddings → tabla chunks en Supabase (Capa 5B.1)

docs/
└── langgraph-intro.txt  ✅ base de conocimiento inicial (extraída del golden_set)

tests/
├── conftest.py    ✅ fixtures: agent_graph, sample_responses, invoke_agent
├── test_rules.py  ✅ 7 tests deterministas, sin API, 0.05s
├── test_evals.py  ✅ LLM-as-judge usando evaluators.py compartido
└── reports/       ✅ pytest-html local + artefacto en CI

evals/
├── golden_set.json  ✅ 20 preguntas sobre LangGraph docs
├── evaluators.py    ✅ relevance (LLM-judge), citation (code), convergence (code)
│                       + @traceable para LangSmith (Capa 3B)
├── run_evals.py     ✅ corre evals, guarda resultados por fecha/hora
│                       + client.create_feedback() para LangSmith (Capa 3B)
└── results/         ✅ JSONs organizados por YYYY-MM-DD/HH-MM-SS
                        (corridas: 2026-05-29, 05-30, 06-01, 06-03)

.github/
└── workflows/
    └── ci.yml     ✅ rules en cada push, evals solo en main (MAX_EVAL_CASES=1)
                      + LANGCHAIN_API_KEY como secret (Capa 3B)

── PRÓXIMO PASO ──
Capa 5B.2, pieza 1: conectar rag_search() a Postgres.
Decisión ya tomada (2026-07-02): arrancar simple — abrir/cerrar una conexión
psycopg2 nueva en cada llamada a rag_search() (igual que scripts/ingest.py),
NO un connection pool todavía. El pool queda anotado como mejora de
rendimiento para después, una vez que la versión simple funcione.

Plan completo de 5B.2 (en orden):
1. Conexión a Postgres desde rag_search()          ← EMPEZAR ACÁ
2. Query SQL de vector search (embedding <=> query, ORDER BY distancia)
3. Query SQL de keyword search (Postgres FTS: to_tsvector / ts_rank)
4. Fusionar ambas listas con rrf() — la función de ingestion.py NO cambia,
   solo mira (id, score) genéricos, no le importa si el id viene de una
   lista en memoria o de una fila de Postgres
5. Reemplazar _index.hybrid_search() dentro de rag_search() por lo nuevo
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

## Capa 5 — RAG real con PDFs ← EN PROGRESO

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