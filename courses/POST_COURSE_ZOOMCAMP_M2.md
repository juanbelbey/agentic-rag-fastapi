# POST-COURSE HANDOFF: LLM Zoomcamp — Módulo 2
# DataTalks.Club — Vector Search (Alexey Grigorev)

## Contexto

Acabo de terminar el Módulo 2 del LLM Zoomcamp 2026.
Ver ROADMAP.md para el estado completo del repo.

Capas completadas hasta ahora:
- Capa 1 ✅ — Esqueleto del agente (LangGraph)
- Capa 2 ✅ — Tests y CI
- Capa 3A ✅ — Evaluadores a mano
- Capa 3B ✅ — Integración LangSmith
- Capa 4 ✅ — Outputs tipados con Pydantic
- Capa 5A ✅ — RAG en memoria (numpy + cosine similarity + OpenAI embeddings, commit 0c1370b)

Capa en progreso luego de M2:
- Capa 5A.2 ⬜ — Hybrid search: keyword + vector + RRF en memoria
- Capa 5B ⬜ — pgvector/Supabase + Postgres FTS + RRF (infraestructura real)

---

## Qué aprendí en el módulo

| Concepto | Qué es | Dónde aplica en mi repo |
|---|---|---|
| ONNX Embedder | `all-MiniLM-L6-v2` sin PyTorch. Vectores de 384 dims, normalizados. Sin costo de API. | **Decisión tomada: no se adopta.** Seguimos con `text-embedding-3-small`. ONNX podría reducir el Docker, pero rompe compatibilidad con los vectores ya generados y agrega una dependencia nueva sin ganancia arquitectural en nuestro caso. |
| Dot product = cosine similarity | Cuando ambos vectores están normalizados: `A · B` = cosine similarity sin dividir. Rango -1 a 1. | Valida la implementación de `InMemoryIndex` en `src/ingestion.py`. Lo que construimos en 5A ya hacía esto correctamente. |
| Vector search manual (numpy) | Matriz `X` (N×D) con `encode_batch` + `X.dot(v)` → scores en un solo paso. `np.argmax` da el más similar. | Confirma la arquitectura del `InMemoryIndex`. Capa 5A estaba bien construida. |
| minsearch.VectorSearch | Index que acepta matriz X precalculada. `.fit(X, docs)` + `.search(vector, num_results=N)`. | **No se adopta.** Nuestro `InMemoryIndex` con numpy hace lo mismo. Sin ganancia real en reemplazarlo. |
| Vector vs Text search | Vector: gana en paráfrasis y conceptos. Text: gana en keywords exactas, nombres propios, siglas. | `rag_search()` actual solo hace vector search. Para mejorar recall, hay que combinar ambos. Eso es 5A.2. |
| RRF — Reciprocal Rank Fusion | Combina listas de ranking sin comparar scores crudos. `Σ 1/(k + rank)` por lista. `k=60` (default del paper). | Núcleo de 5A.2: combinar vector_results + keyword_results → top-N por RRF. La interfaz de `rag_search()` no cambia. |

---

## Lo que M2 valida del repo actual

**Capa 5A estaba bien construida.** El pipeline que implementamos (chunking → OpenAI embeddings → InMemoryIndex numpy → cosine similarity) es exactamente lo que M2 enseña, solo con diferente embedder (ONNX vs OpenAI). La arquitectura es idéntica.

Esto significa que cuando migremos a pgvector en 5B, el patrón conceptual ya está internalizado. Lo único que cambia es el backend de almacenamiento y búsqueda.

---

## Lo que construyo luego de M2

### Capa 5A.2 — Hybrid search en memoria

**Objetivo:** mejorar el recall de `rag_search()` combinando vector search + keyword search + RRF.
La interfaz pública `rag_search(query: str) → list[RAGResult]` **no cambia**.

**Por qué implementar esto antes de 5B:**
- RRF en numpy es más fácil de entender que RRF sobre Postgres full-text search + pgvector
- El patrón (dos listas → RRF → top-N) se entiende en el caso simple y luego se repite en 5B
- Agrega valor real: el doc ganador en M2 (`13-function-calling.md`) no era primero en ninguna lista individual

**Archivos a modificar:**

`src/ingestion.py`
- Agregar `KeywordIndex` sobre los mismos chunks (TF-IDF liviano o minsearch.Index)
- `InMemoryIndex` ahora contiene tanto el vector index como el keyword index
- Método `hybrid_search(query, vector_top_k, keyword_top_k)` → dos listas pre-fusión

`src/tools.py`
- `rag_search()` llama a `hybrid_search()` y aplica `rrf()` internamente
- La función `rrf(results_a, results_b, k=60)` puede vivir en `ingestion.py` (evitar nuevo archivo)

**Qué NO toca esta capa:**
- `src/graph.py` — el routing no cambia
- `src/schemas.py` — `RAGResult` no cambia
- `evals/golden_set.json` — las preguntas no cambian

**Pregunta de comprensión antes de implementar:**
¿Por qué RRF usa `1/(k + rank)` en vez de comparar directamente los scores de cosine similarity y BM25? (Pista: los scores de distintos sistemas no son comparables en escala)

---

### Capa 5B — Supabase + pgvector (actualizado con M2)

M2 agrega algo que no estaba en el plan original de 5B: usar **Postgres full-text search** (que ya tiene Supabase sin configuración extra) como el branch de keyword search, en vez de minsearch. Eso hace que en producción no necesites dos backends — todo está en Postgres.

**Plan actualizado de 5B:**
- `src/ingestion.py`: reemplaza `InMemoryIndex` por cliente Supabase + inserción en tabla con columna `embedding vector(1536)` (pgvector) y columna `content text` (para FTS)
- `src/tools.py`: `rag_search()` hace query SQL con `<=>` (cosine distance en pgvector) + Postgres `to_tsvector` / `ts_rank` + fusión con `rrf()`
- MemorySaver → Postgres checkpointer de LangGraph (misma instancia de Supabase)
- `tests/test_evals.py`: `known_context` pasa a ser el chunk real recuperado

**Por qué Postgres FTS y no minsearch en producción:**
- minsearch es in-process: no escala, se pierde al reiniciar
- Postgres FTS es persistente, indexado, y ya está en la misma base de datos
- Postgres FTS + pgvector + RRF es el stack estándar para hybrid search sin infraestructura extra

---

## Decisiones tomadas en este handoff

| Decisión | Elección | Razón |
|---|---|---|
| ONNX Embedder | No adoptar | Stack OpenAI ya funciona. Incompatibilidad de vectores. Sin ganancia arquitectural. |
| minsearch.VectorSearch | No adoptar | `InMemoryIndex` con numpy ya hace lo mismo. |
| Timing de RRF | Implementar en 5A.2 antes de 5B | Entender el patrón en numpy antes que en SQL. Luego se migra la misma lógica. |
| Keyword backend en 5B | Postgres FTS (no minsearch) | Todo en Postgres: persistente, sin segundo backend, estándar de industria. |

---

## Restricciones heredadas (sin cambio)

- `gpt-4o-mini` como modelo por defecto
- No usar Pinecone ni Weaviate: el stack es Supabase/pgvector
- No tocar `src/graph.py` ni el routing del agente
- LangSmith debe degradarse silenciosamente si no hay API key
- El repo debe poder correrse localmente en cualquier momento con `uvicorn src.main:app --reload`


Addendum — Capa 5B.2: RAG híbrido sobre Supabase/Postgres

(Construido por fuera del Zoomcamp, como extensión directa de los conceptos de M2)

Qué se implementó

┌────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│       Componente       │                                                                              Descripción                                                                              │
├────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ _hybrid_search()       │ Pide 10 candidatos a pgvector (distancia coseno <=>) y 10 a full-text search de Postgres (to_tsvector / plainto_tsquery / ts_rank), los fusiona con RRF y corta al    │
│                        │ top-k                                                                                                                                                                 │
├────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ rag_search() reescrito │ Embebe la query en tiempo real (text-embedding-3-small), corre la búsqueda híbrida contra la tabla chunks de Supabase, trae el texto de los chunks ganadores y        │
│                        │ reordena del lado de Python                                                                                                                                           │
├────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Reordenamiento en      │ Postgres no garantiza el orden cuando traés filas por ID — se construye un dict {id: chunk} y se reordena según el ranking RRF                                        │
│ Python                 │                                                                                                                                                                       │
└────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

Conceptos que solidificó esta capa (y que no cubrió el Zoomcamp)

┌──────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                 Concepto                 │                                               Aprendizaje concreto                                               │
├──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Full-text search en Postgres             │ to_tsvector normaliza el corpus a raíces; plainto_tsquery hace lo mismo con la query; @@ matchea; ts_rank puntúa │
├──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Por qué RRF usa posiciones y no scores   │ Cosine distance y ts_rank viven en escalas incomparables; la posición ordinal es el único denominador común      │
├──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Document embeddings vs. query embeddings │ El corpus es fijo → se cachea en Postgres. La query es una sonda que cambia → siempre en tiempo real             │
├──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Orden de evaluación SQL                  │ FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY: ni WHERE ni HAVING pueden usar alias del SELECT            │
├──────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ try/finally para recursos                │ finally garantiza el cierre de la conexión a Postgres pase lo que pase, sin atrapar ni silenciar el error        │
└──────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

Conexión con el diseño del sistema

Esta capa cerró el loop entre lo que el Zoomcamp enseñó (vector search + RRF conceptual) y lo que el sistema necesita en producción: búsqueda híbrida real contra una base de datos externa, con embeddings en tiempo real y fusión de rankings.