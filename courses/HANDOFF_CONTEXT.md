# Handoff Context — LLM Zoomcamp 2026
> Este archivo se acumula módulo a módulo. Copiarlo a la sesión del repo flagship (`agentic-rag-fastapi`) para trabajar el POST_COURSE de cada módulo.

---

## M1 — Agentic RAG

### Estado
- HW entregado ✓ | Notebook completa Q1–Q6 ✓ | Apuntes escritos ✓

### Qué vimos (conceptos clave)

| Concepto | Descripción |
|---|---|
| **RAG pipeline** | Indexing → Retrieval → Generation. Sin índice: O(n) por búsqueda. Con índice: acceso directo con score de relevancia (TF-IDF). |
| **minsearch.Index** | Keyword search liviano en memoria. `text_fields` para búsqueda, `keyword_fields` para filtrar exacto. `.fit(docs)` + `.search(query)`. |
| **RAGBase + subclase** | Clase base con `search`, `build_context`, `build_prompt`, `llm`, `rag`. Se subclasea sobreescribiendo solo lo que cambia. `LessonRAG` sobreescribió `search`, `build_context`, `llm`. |
| **Chunking (sliding window)** | `size=2000, step=1000` → overlap de 1000 chars. Reduce tokens ~3x frente a documentos completos. Cada chunk hereda `filename` y agrega `start`. |
| **RAG agéntico vs RAG común** | RAG común: un retrieval + un LLM call, flujo fijo. RAG agéntico: loop mientras el modelo pida tool calls. El LLM decide cuándo buscar y cuándo responder. |
| **Function calling** | El LLM no ejecuta código: devuelve un mensaje especial con función + args. Tu código lo ejecuta y devuelve el resultado. El loop para cuando no hay más `function_call` en la respuesta. |
| **toyaikit** | Wrapper sobre la Responses API de OpenAI. `Tools` + `OpenAIResponsesRunner` manejan el loop agéntico sin código manual. |

### Qué implementamos en la notebook

- Cliente OpenAI + función `llm()` básica
- Carga de 72 lesson pages desde GitHub (commit `8c1834d`) con `gitsource`
- `minsearch.Index` sobre documentos completos → keyword search
- `LessonRAG(RAGBase)`: subclase con `search`, `build_context`, `llm`, `rag` propios
- Chunking: 72 docs → 295 chunks con `chunk_documents(size=2000, step=1000)`
- RAG sobre chunks vs documentos completos → 2310 vs 7127 input tokens (~3x reducción)
- Loop agéntico manual con `function_call` detection
- Loop agéntico con `toyaikit`: `Tools` + `OpenAIResponsesRunner` → 3 search calls automáticos

### Candidatos para incorporar al repo flagship

| Patrón | Por qué es relevante |
|---|---|
| **Subclase de RAGBase** | Patrón limpio para tener múltiples estrategias de retrieval sin duplicar código. Útil si el repo tiene más de un tipo de documento o índice. |
| **Chunking con overlap** | Si el repo indexa documentos largos, aplicar `size=2000, step=1000` reduce tokens y mejora precisión del retrieval. Ya probado: ~3x menos tokens. |
| **Loop agéntico manual** | La versión sin framework es más transparente para debugging y testing. Útil como referencia o fallback. |
| **toyaikit runner** | Si el repo ya usa OpenAI Responses API, `OpenAIResponsesRunner` elimina el boilerplate del loop. Evaluar si vale la dependencia extra. |

---

## M2 — Vector Search

### Estado
- HW entregado ✓ | Notebook completa Q1–Q6 ✓ | Apuntes escritos ✓

### Respuestas confirmadas

| Q | Pregunta | Respuesta |
|---|---|---|
| Q1 | v[0] del embedding de la query | `-0.02` |
| Q2 | Cosine similarity query vs `07-sqlitesearch-vector.md` | `0.37` |
| Q3 | Chunk con mayor score contra la query | `02-vector-search/lessons/07-sqlitesearch-vector.md` |
| Q4 | Primer resultado de minsearch VectorSearch | `04-evaluation/lessons/05-search-metrics.md` |
| Q5 | Aparece en vector search pero no en text search | `02-vector-search/lessons/08-pgvector.md` |
| Q6 | Primer resultado RRF hybrid search | `01-agentic-rag/lessons/13-function-calling.md` |

### Qué vimos (conceptos clave)

| Concepto | Descripción |
|---|---|
| **ONNX Embedder** | `all-MiniLM-L6-v2` sin PyTorch. Vectores de 384 dimensiones, normalizados. ~30x más liviano que sentence-transformers. `.encode(text)` y `.encode_batch(texts)`. |
| **Dot product = cosine similarity** | Cuando ambos vectores están normalizados: `A · B` = cosine similarity. No hace falta dividir. Rango: -1 a 1. |
| **Chunking con overlap** | Mismo parámetro que M1 (`size=2000, step=1000`). Un doc entero → embedding difuso. Chunks → embeddings específicos. 72 docs → 295 chunks. |
| **Vector search manual** | Matriz `X` (295×384) con `encode_batch` + `X.dot(v)` → score de todos los chunks en un solo paso. `np.argmax` da el más similar. |
| **minsearch.VectorSearch** | Index que acepta matriz X precalculada + metadata. `.fit(X, docs)` + `.search(vector, num_results=N)`. Sin infraestructura adicional. |
| **Vector vs Text search** | Vector gana en paráfrasis/conceptos. Text gana en keywords exactas, nombres propios, siglas. Regla: query conceptual → vector; keyword técnica → text; dudas → hybrid. |
| **RRF — Reciprocal Rank Fusion** | Combina listas de ranking sin comparar scores crudos. `Σ 1/(k + rank)` por lista. `k=60` (default del paper). Un doc top en ambas listas supera a uno muy top en solo una. |

### Qué implementamos en la notebook

- `Embedder` (ONNX) con `.encode()` y `.encode_batch()`
- Carga de 72 docs con `gitsource` (mismo corpus que M1)
- Cosine similarity a mano con dot product
- Matriz `X` (295×384) + scoring manual con `X.dot(v)`
- `minsearch.VectorSearch`: fit con X precalculada, search con vector de query
- `minsearch.Index`: keyword search sobre los mismos chunks para comparar
- Función `rrf()` implementada desde cero: acepta lista de listas, retorna top N fusionados

### Candidatos para incorporar al repo flagship

| Patrón | Por qué es relevante |
|---|---|
| **ONNX Embedder** | Reemplaza sentence-transformers: sin PyTorch = Docker más chico, deploy más simple. Vectores idénticos, ~30x menos dependencias. |
| **Vector search con minsearch** | Si el repo no usa pgvector todavía, `minsearch.VectorSearch` da vector search en memoria sin infraestructura. Bueno para prototipado y testing. |
| **Función `rrf()` standalone** | Agnóstica al motor. Se enchufra sobre cualquier par `(vector_results, text_results)` sin tocar la lógica de retrieval existente. |
| **Hybrid search (vector + keyword + RRF)** | Mejora recall sin elegir un solo método. El resultado de Q6 demostró que el doc ganador (`13-function-calling.md`) no era primero en ninguna lista individual. |

### Preguntas para decidir en el repo flagship

1. ¿El repo ya tiene retrieval? ¿Con qué motor (pgvector, ChromaDB, minsearch, otro)?
2. ¿El deploy corre en Docker? → ahí la ganancia del ONNX embedder es más concreta
3. ¿Hay un endpoint de búsqueda? → RRF se agrega como capa encima sin tocar lógica actual

---

*Próximo módulo: M3 — se agrega una sección nueva cuando esté completo.*
