# ROADMAP.md
# Plan completo de especialización — AI Engineer 2026
# Juan Belbey

## Para qué existe este archivo

Este archivo le da a Copilot el mapa completo del proyecto:
qué cursos hice, qué construí con cada uno, qué viene después,
y qué capa del repo flagship corresponde a cada etapa.

Copilot nunca debe improvisar qué viene después. Todo está acá.

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
- Supabase (Postgres + pgvector) — se incorpora en la fase RAG real
- GitHub Actions (CI)
- Deploy: Render/Fly.io (H1) → AWS (H2)

---

## Mapa de capas: qué construye cada curso

```
CAPA 1 — Esqueleto del agente         ← COMPLETADA (LangGraph)
CAPA 2 — Tests y CI                   ← EN PROGRESO (Automated Testing)
CAPA 3 — Observabilidad y evals       ← PRÓXIMA (Evaluating AI Agents)
CAPA 4 — Outputs tipados              ← PENDIENTE (Pydantic for LLM Workflows)
CAPA 5 — RAG real con PDFs            ← PENDIENTE (LLM Zoomcamp o Coursera)
CAPA 6 — Deploy en AWS                ← PENDIENTE (H2)
```

Cada capa se construye sobre la anterior. Nunca se salta una capa.
Nunca se espera terminar todos los cursos para empezar a construir.

---

## Estado actual del repo por archivo

```
src/
├── config.py      ✅ validación temprana de OPENAI_API_KEY
├── state.py       ✅ AgentState con TypedDict
├── tools.py       ✅ rag_search() y create_ticket() como stubs
├── graph.py       ✅ StateGraph con routing condicional y MemorySaver
├── prompts.py     ✅ system prompts
└── main.py        ✅ FastAPI con POST /chat y persistencia por thread_id

tests/
├── conftest.py    ✅ fixtures compartidos (agent_graph, invoke_agent)
├── test_rules.py  🔄 en construcción (Capa 2)
├── test_evals.py  🔄 en construcción (Capa 2)
└── reports/       ⬜ pendiente (pytest-html)

evals/
└── golden_set.json ⬜ pendiente (Capa 3)

.github/
└── workflows/
    └── ci.yml     ⬜ pendiente (Capa 2)
```

---

## Curso 1 — AI Agents in LangGraph ✅ COMPLETADO

**Plataforma:** DeepLearning.AI
**Duración:** ~4 horas
**Instructor:** Harrison Chase (LangChain)

**Qué enseña:**
- Loop ReAct: razonar → actuar → observar
- StateGraph, nodes, edges, TypedDict de estado
- Routing condicional con add_conditional_edges
- Persistencia con MemorySaver y thread_id
- Human in the loop con interrupt_before
- Grafos multi-nodo con roles especializados

**Qué se construyó en el repo (Capa 1):**
- `src/state.py` — AgentState
- `src/tools.py` — stubs de rag_search() y create_ticket()
- `src/graph.py` — StateGraph con routing y MemorySaver
- `src/config.py` — validación de API key
- `src/main.py` — FastAPI con /chat

**Decisiones tomadas:**
- Usar MemorySaver ahora, migrar a Postgres checkpointer cuando llegue Supabase
- Tools como stubs hasta que llegue la capa de RAG real
- gpt-4o-mini como modelo por defecto para reducir costos mientras se aprende

---

## Curso 2 — Automated Testing for LLMOps 🔄 EN PROGRESO

**Plataforma:** DeepLearning.AI
**Duración:** ~52 minutos
**Instructor:** Rob Zuber (CircleCI)

**Qué enseña:**
- Tests deterministas (rules-based): rápidos, sin LLM, baratos
- Model-graded evals: LLM-as-judge para calidad de respuestas
- CI pipeline: automatizar tests en cada push
- El curso usa CircleCI — nosotros usamos GitHub Actions

**Qué se construye en el repo (Capa 2):**
- `tests/conftest.py` — fixtures compartidos ✅ hecho
- `tests/test_rules.py` — tests deterministas del agente
- `tests/test_evals.py` — evaluaciones con LLM-as-judge (gpt-4o-mini)
- `tests/reports/report.html` — reporte visual con pytest-html
- `.github/workflows/ci.yml` — GitHub Actions
  - test_rules.py corre en cada push a cualquier rama
  - test_evals.py corre solo en push a main (ahorra tokens)

**Dataset para tests:**
- Fuente: documentación oficial de LangGraph
  https://langchain-ai.github.io/langgraph/
- Guardar en: `data/docs/langgraph_docs.pdf`
- Golden set: `evals/golden_set.json` con 20 preguntas
  sobre conceptos de LangGraph con respuestas esperadas

**Nota importante:**
- rag_search() sigue siendo stub hasta la Capa 5
- test_evals.py usa known_context hardcodeado ahora
- Cuando llegue el RAG real, known_context pasa a ser el chunk recuperado

---

## Curso 3 — Evaluating AI Agents ⬜ PRÓXIMO

**Plataforma:** DeepLearning.AI
**Instructor:** John Gilhuly + Aman Khan (Arize AI)

**Qué enseña:**
- Observabilidad real: trazas de cada paso del agente
- Debug visual: ver exactamente qué nodo falló y por qué
- Evaluación componente por componente:
  - El router: ¿eligió la tool correcta?
  - Las tools: ¿devolvieron lo esperado?
  - La memoria: ¿el contexto se mantuvo entre turnos?
- Tipos de evaluadores: code-based, LLM-as-judge, anotación humana
- Convergence score: ¿el agente resuelve en pocos pasos o da vueltas?
- Crear ejemplos de test a partir de trazas reales

**Qué se construye en el repo (Capa 3):**
- `evals/golden_set.json` — 20-40 preguntas sobre LangGraph docs
  con respuesta esperada y fuente
- `evals/run_evals.py` — script para correr evaluaciones
- `evals/results/` — resultados por fecha para comparar versiones
- Métricas a implementar:
  - Answer relevance (LLM-as-judge 1-5)
  - Citation coverage (¿la respuesta cita la fuente?)
  - Convergence score (pasos hasta respuesta final)

**Formato del golden_set.json:**
```json
[
  {
    "id": "q001",
    "question": "¿Cuál es la diferencia entre add_edge y add_conditional_edges?",
    "expected_answer": "add_edge conecta dos nodos de forma fija. add_conditional_edges usa una función de routing para decidir el próximo nodo según el estado.",
    "source": "langgraph_docs",
    "category": "graph_structure"
  }
]
```

---

## Curso 4 — Pydantic for LLM Workflows ⬜ PENDIENTE

**Plataforma:** DeepLearning.AI
**Instructor:** Ryan Keenan (DeepLearning.AI)

**Qué enseña:**
- Qué es structured output y por qué importa en sistemas LLM
- Pydantic BaseModel para definir esquemas de salida
- Validación de inputs del usuario antes de llamar al LLM
- Outputs tipados en API calls a OpenAI
- Tool calling con tipos garantizados
- Cómo LangGraph y otros frameworks usan Pydantic internamente

**Qué se construye en el repo (Capa 4):**
- `src/schemas.py` — modelos Pydantic para el proyecto:
  - `ChatRequest` — validación del input del endpoint /chat
  - `ChatResponse` — respuesta tipada del agente
  - `Ticket` — estructura de ticket para create_ticket()
  - `RAGResult` — estructura de resultado de rag_search()
- Reemplazar los stubs sin tipos por versiones tipadas
- El endpoint /chat pasa de recibir dict a recibir ChatRequest validado
- create_ticket() pasa de devolver string a devolver Ticket validado

**Por qué importa:**
- Antes de Pydantic: create_ticket() devuelve un string hardcodeado
- Después de Pydantic: devuelve un objeto Ticket con campos validados,
  listo para insertarse en Postgres cuando llegue Supabase

---

## Curso 5 — RAG real con PDFs ⬜ PENDIENTE (H2)

**Opciones (elegir una):**
- LLM Zoomcamp (DataTalks.Club) — 10 semanas, más profundo
- Optimizing & Deploying LLMs (Coursera) — 4-6 semanas, más rápido

**Qué se construye en el repo (Capa 5):**
- Reemplazar rag_search() stub por retrieval real
- Ingesta de PDFs: chunking + embeddings + insert en pgvector
- Supabase como base de datos (Postgres + pgvector)
- rag_search() conecta a Supabase y devuelve chunks relevantes
- Los tests de test_evals.py pasan de known_context hardcodeado
  a contexto real recuperado del vector store

---

## Reglas para Copilot

1. Nunca sugerir librerías o herramientas que no estén en este roadmap
   sin consultarme primero y explicar por qué.

2. Nunca saltar una capa. Si estamos en Capa 2, no construir
   cosas de Capa 3 aunque parezca obvio.

3. Cuando algo del curso usa una herramienta diferente a la del stack
   (ej: CircleCI en vez de GitHub Actions, Pinecone en vez de Supabase),
   siempre traducir al stack definido aquí.

4. Antes de cada sesión de construcción, recordarme en qué capa estamos
   y qué falta completar de esa capa.

5. Clasificar cada cambio propuesto como:
   - [aprendizaje] — para entender el patrón
   - [ingeniería] — buena práctica de código
   - [producción] — necesario para deploy real

6. El modelo siempre es gpt-4o-mini salvo que yo indique lo contrario.

7. Supabase y pgvector no se tocan hasta la Capa 5.
   MemorySaver es suficiente hasta entonces.
