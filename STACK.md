# STACK.md
# Decisiones de tecnología — agentic-rag-fastapi

Este archivo es la fuente de verdad sobre qué librerías usamos, por qué, y cuándo usar cada una.
Antes de agregar una dependencia nueva, consultarlo.

---

## Librerías activas

### Orquestación del agente
| Librería | Versión | Rol |
|---|---|---|
| `langgraph` | 1.1.10 | Grafo del agente (`StateGraph`, routing, `MemorySaver`) |
| `langchain-core` | 1.3.2 | Primitivas compartidas (`@tool`, `ToolNode`, `AnyMessage`, `add_messages`) |
| `langchain-openai` | 1.2.1 | Integración OpenAI (`ChatOpenAI`, embeddings) |
| `langchain` | 1.2.15 | Dependencia transitiva de los anteriores |

### LLM y embeddings
| Librería | Versión | Rol |
|---|---|---|
| `openai` | 2.33.0 | Cliente directo de la API de OpenAI |

**Modelos en uso:**
- `gpt-4o-mini` — modelo de chat del agente y del juez de evals
- `text-embedding-3-small` — embeddings para Capa 5A (pendiente de usar)

### API
| Librería | Versión | Rol |
|---|---|---|
| `fastapi` | 0.136.1 | Servidor HTTP — endpoint `POST /chat` |
| `uvicorn` | 0.46.0 | ASGI server para correr FastAPI |

### Validación y esquemas
| Librería | Versión | Rol |
|---|---|---|
| `pydantic` | 2.12.4 | Schemas en bordes del sistema (ver regla abajo) |

### Observabilidad
| Librería | Versión | Rol |
|---|---|---|
| `langsmith` | 0.7.37 | Trazas de evals + feedback scores — degradación silenciosa sin API key |

### Vectores (Capa 5A — en memoria)
| Librería | Versión | Rol |
|---|---|---|
| `numpy` | — | Array de embeddings + cosine similarity en memoria |

### Config y utilidades
| Librería | Versión | Rol |
|---|---|---|
| `python-dotenv` | 1.2.1 | Carga de `.env` al inicio |

### Tests
| Librería | Versión | Rol |
|---|---|---|
| `pytest` | 9.0.3 | Framework de tests |
| `pytest-html` | 4.2.0 | Reportes HTML en CI |

---

## Regla: cuándo usar `pydantic.BaseModel` vs `dataclasses.dataclass`

Esta distinción ya está en el código — respetarla evita inconsistencias.

### `pydantic.BaseModel` → bordes del sistema

Usarlo cuando el dato cruza una frontera: llega de afuera, sale hacia afuera, o lo valida LangChain.

```
src/schemas.py
├── ChatRequest     ← input del usuario al endpoint /chat
├── ChatResponse    ← output del agente al usuario
├── TicketInput     ← args que el LLM le pasa a create_ticket() (LangChain lo valida)
└── RAGResult       ← output de rag_search() hacia el agente
```

**Por qué Pydantic aquí:** valida tipos en runtime, genera JSON Schema automáticamente
(LangChain lo usa para describir las tools al LLM), y serializa con `.model_dump_json()`.

### `dataclasses.dataclass` → estructuras internas

Usarlo para datos que nunca salen del sistema o no necesitan validación.

```
src/config.py
└── Settings(frozen=True)   ← config de arranque: solo se lee, no se valida contra input externo

src/ingestion.py
└── InMemoryIndex           ← estado interno del índice: chunks + embeddings en memoria
```

**Por qué dataclass aquí:** más liviano, sin overhead de validación, suficiente para
estructuras donde controlamos todos los valores que entran.

### Resumen en una línea

> Si el dato viene de un usuario, un LLM, o una API externa → Pydantic.
> Si es estado interno que el código controla → dataclass.

---

## Decisiones de stack deliberadas (qué NO usamos y por qué)

| Alternativa descartada | Usamos en cambio | Razón |
|---|---|---|
| Pinecone, Weaviate | Supabase/pgvector (Capa 5B) | Stack unificado: Supabase ya maneja Postgres + vector + auth |
| Arize Phoenix | LangSmith | Integración nativa con LangGraph, tier gratuito, más relevante en el mercado |
| CircleCI | GitHub Actions | Evitar cuenta extra; equivalente para este proyecto |
| LlamaIndex, LangChain RAG | Implementación propia | El objetivo es entender el pipeline, no abstraerlo |
| `faiss` | numpy (Capa 5A) | numpy es suficiente para aprender cosine similarity sin instalar C++ deps |

---

## Dependencias pendientes de agregar a requirements.txt

| Librería | Estado | Acción |
|---|---|---|
| `langsmith` | Instalada, en uso en `evals/`, **no está en requirements.txt** | Agregar |
| `numpy` | En `ingestion.py`, **no está instalada ni en requirements.txt** | Instalar y agregar |

---

## Stack planificado para Capa 5B (no instalar hasta llegar)

- `supabase` — cliente Python de Supabase
- `pgvector` — extensión de Postgres para vectores (se activa desde Supabase, no requiere pip)
- Postgres checkpointer de LangGraph — reemplaza `MemorySaver`
