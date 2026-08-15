# STACK.md
# Decisiones de tecnología — agentic-rag-fastapi

Este archivo es la fuente de verdad sobre qué librerías usamos, por qué, y cuándo usar cada una.
Antes de agregar una dependencia nueva, consultarlo.

---

## Librerías activas

### Orquestación del agente
| Librería | Versión | Rol |
|---|---|---|
| `langgraph` | 1.1.10 | Grafo del agente (`StateGraph`, routing, checkpointer) |
| `langchain-core` | 1.5.3 | Primitivas compartidas (`@tool`, `ToolNode`, `AnyMessage`, `add_messages`) |
| `langchain-openai` | 1.2.1 | Integración OpenAI (`ChatOpenAI`, embeddings) |
| `langchain` | 1.2.15 | Dependencia transitiva de los anteriores |

### LLM y embeddings
| Librería | Versión | Rol |
|---|---|---|
| `openai` | 2.33.0 | Cliente directo de la API de OpenAI |

**Modelos en uso:**
- `gpt-4o-mini` — modelo de chat del agente y del juez de evals
- `text-embedding-3-small` — embeddings de ingesta y de la query en `rag_search`

### API
| Librería | Versión | Rol |
|---|---|---|
| `fastapi` | 0.136.1 | Servidor HTTP — endpoints `POST /chat`, `GET /stats` |
| `uvicorn` | 0.46.0 | ASGI server para correr FastAPI |
| `slowapi` | 0.1.9 | Rate limiting del deploy público en Render |

### Validación y esquemas
| Librería | Versión | Rol |
|---|---|---|
| `pydantic` | 2.12.4 | Schemas en bordes del sistema (ver regla abajo) |

### Observabilidad
| Librería | Versión | Rol |
|---|---|---|
| `langsmith` | 0.7.37 | Trazas de evals + feedback scores — degradación silenciosa sin API key |

### Retrieval — Postgres/pgvector (Supabase)
| Librería | Versión | Rol |
|---|---|---|
| `psycopg2-binary` | 2.9.11 | Cliente Postgres (queries de `rag_search`, `chat_logs`) |
| `pgvector` | 0.4.1 | Tipo `vector` de Postgres desde Python |
| `numpy` | 2.4.6 | Arrays de embeddings en el pipeline de ingesta |
| `langgraph-checkpoint-postgres` | 3.1.0 | Checkpointer de LangGraph sobre Postgres (reemplaza `MemorySaver`) |
| `psycopg[binary]` | 3.3.4 | psycopg v3 + pool, requerido por el checkpointer — convive con psycopg2 de arriba |
| `psycopg-pool` | 3.3.1 | Pool de conexiones para el checkpointer |

### Ingesta
| Librería | Versión | Rol |
|---|---|---|
| `pypdf` | 5.1.0 | Extracción de texto de los PDFs del corpus |

### Evaluación
| Librería | Versión | Rol |
|---|---|---|
| `ragas` | 0.4.3 | Métricas de generación (faithfulness, etc.) sobre el RAG real |
| `langchain-community` | 0.4.1 | Pin explícito por compatibilidad con `ragas` — ver comentario en `requirements.txt` |

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
| Pinecone, Weaviate | Supabase/pgvector | Stack unificado: Supabase ya maneja Postgres + vector + auth |
| Arize Phoenix | LangSmith | Integración nativa con LangGraph, tier gratuito, más relevante en el mercado |
| CircleCI | GitHub Actions | Evitar cuenta extra; equivalente para este proyecto |
| LlamaIndex, LangChain RAG | Implementación propia | El objetivo es entender el pipeline, no abstraerlo |
| `faiss` | pgvector | El índice vive en Postgres — no hace falta una librería de índice en memoria aparte |
