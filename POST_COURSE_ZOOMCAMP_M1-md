# POST-COURSE HANDOFF: LLM Zoomcamp — Módulo 1
# DataTalks.Club — Agentic RAG (Harrison Chase / Alexey Grigorev)

## Contexto

Acabo de terminar el Módulo 1 del LLM Zoomcamp 2026.
Ver ROADMAP.md para el estado completo del repo.

Capas completadas hasta ahora:
- Capa 1 ✅ — Esqueleto del agente (LangGraph)
- Capa 2 ✅ — Tests y CI (Automated Testing)
- Capa 3A ✅ — Evaluadores a mano (Arize AI / Evaluating AI Agents)
- Capa 3B ✅ — Integración LangSmith
- Capa 4 ✅ — Outputs tipados con Pydantic (schemas.py completo, commit f552cfd 2026-06-07)

Capa en progreso:
- Capa 5A ⬜ — RAG en memoria (chunking + embeddings + numpy index)
- Capa 5B ⬜ — RAG con pgvector/Supabase (pendiente M2 del Zoomcamp)

Este handoff documenta qué aprendí en M1 y cómo alimenta la **Capa 5A**.
La precondición (Capa 4 completa) ya está satisfecha.

---

## Qué aprendí en el módulo                                                                                                                                                                                       
| Concepto | Qué es | Dónde aplica en mi repo |                                                                                                                                                                   |---|---|---|
| Indexing con minsearch | Índice en memoria: text_fields se buscan por TF-IDF, keyword_fields por match exacto | Analogía directa de lo que hace pgvector en Capa 5, con embeddings en vez de TF-IDF |           | Pipeline RAG | Indexing → Retrieval → Generation como tres etapas separadas | Estructura mentar en `src/tools.py` |
| Patrón RAGBase | Clase con `search`, `build_context`, `build_prompt`, `llm`, `rag`. Solo se sobreescriben los dos primeros al cambiar el schema | Informa cómo modularizar la lógica de retrieval en Capa 5 |   | Chunking con ventana deslizante | Documentos largos → chunks de 2000 chars con paso de 10de partida para `src/ingestion.py`: PDFs → chunks → embeddings → pgvector |
| RAG agéntico con function calling | El LLM devuelve `tool_calls` con nombre de función + args; el código ejecuta y devuelve el resultado; el loop para cuando no hay más tool_calls | Confirma que LangGraph ya implementa este mecanismo en el repo; ahora entiendo por qué |
| Conteo de tokens (`usage.input_tokens`) | El chunking redujo el contexto ~3× versus documentos completos | Métrica útil para monitorear en LangSmith cuando `rag_search()` sea real |

---

## Estado de la notebook al cerrar el módulo

La notebook `M1 lessons/HW1 - Juan Belbey.ipynb` corre de punta a punta:

- **Q1-Q2:** 72 lesson pages descargadas con `gitsource`, indexadas con minsearch
- **Q3:** `LessonRAG(RAGBase)` implementado — sobreescribe `search`, `build_context`, `llm`ma `filename/content` y exponer `usage`
- **Q4:** chunking con `chunk_documents(size=2000, step=1000)` → 1100 chunks
- **Q5:** RAG sobre chunks → ~3× menos tokens que sobre documentos completos
- **Q6:** agente con toyaikit + función `search` como tool → ~4 llamadas al search tool

El patrón `RAGBase` y el loop agéntico están implementados a mano, sin framework. Ahora sé qué hace LangGraph por debajo.

---

## Lo que construyo en Capa 5 usando lo aprendido en M1

### Archivo nuevo: `src/ingestion.py`

- Carga PDFs de documentación técnica (LangGraph docs)
- Aplica chunking con ventana deslizante (`size`, `step` configurables)
- Genera embeddings por chunk (OpenAI `text-embedding-3-small`)
- Inserta en Supabase/pgvector con metadata (`filename`, `start`)

Concepto central antes de escribirlo: ¿en qué se diferencia buscar por
embedding (cosine similarity) de buscar por TF-IDF, y cuándo falla cada uno?

### Archivo modificado: `src/tools.py` — `rag_search()`

- Reemplaza el stub actual por retrieval real sobre pgvector
- Recibe una query → genera embedding → busca los top-N chunks más similares
- Devuelve lista de `RAGResult` (schema definido en Capa 4)
- La interfaz pública no cambia: el grafo de LangGraph la llama igual que ahora

Concepto central antes de escribirlo: ¿por qué `rag_search()` devuelve
`RAGResult` tipado en vez de un dict libre, y qué rompe si el schema cambia?

### Qué NO toca esta capa

- `src/graph.py` — el agente no cambia, solo cambia lo que devuelve su tool
- `evals/golden_set.json` — las preguntas siguen siendo sobre LangGraph docs
- `evals/evaluators.py` — los evaluadores no cambian su interfaz
- `tests/test_evals.py` — `known_context` pasa a ser el chunk real recuperado
  (ese cambio va en Capa 5, pero es una línea, no una reescritura)
- MemorySaver — sigue siendo suficiente hasta que Supabase esté en Capa 5

---

## Cómo quiero trabajar en Capa 5

- Un archivo por vez, en el orden de arriba (ingestion.py primero)
- Antes de cada archivo: concepto central en 3-4 líneas + analogía con M1
- Después de cada archivo: una pregunta de comprensión
- Clasificar cada cambio como [aprendizaje], [ingeniería] o [producción]
- Sin Supabase local en la primera sesión: arrancar con un índice en memoria
  (minsearch o numpy) que tenga la misma interfaz, y migrar a pgvector después

---

## Restricciones

- `gpt-4o-mini` como modelo por defecto (igual que el resto del repo)
- No usar Pinecone ni Weaviate: el stack es Supabase/pgvector (ver ROADMAP)
- No tocar `src/graph.py` ni el routing del agente
- Capa 4 debe estar completa antes de arrancar (schemas.py define `RAGResult`)
- LangSmith debe seguir degradándose silenciosamente si no hay API key