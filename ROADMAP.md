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
CAPA 5 — RAG real con PDFs            ✅ COMPLETADA (2026-07-24)
  5A  — Índice en memoria (numpy)     ✅ COMPLETADA (2026-06-20)
  5A.2 — Hybrid search + RRF          ✅ COMPLETADA (2026-07-01)
  5B  — pgvector/Supabase + FTS       ✅ COMPLETADA (2026-07-24)
    5B.0 — Infraestructura Supabase   ✅ COMPLETADA (2026-07-01)
    5B.1 — Script de ingesta          ✅ COMPLETADA (2026-07-01)
    5B.2 — Migrar rag_search()        ✅ COMPLETADA (2026-07-04)
    5B.3 — Postgres checkpointer      ✅ COMPLETADA (2026-07-24; verificado contra
                                          Supabase real: setup() crea tablas,
                                          persistencia por thread_id confirmada)
    5B.4 — Corpus real + evals M4     ✅ COMPLETADA (2026-07-18; ver CORPUS_INSTRUMENTACION.MD)
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
├── tools.py       ✅ rag_search() sobre Postgres (5B.2): _get_connection + _vector_search
│                     + _keyword_search + _hybrid_search (RRF) + fetch de content/source por id
│                     + create_ticket() con TicketInput
│                     _keyword_search reescrita en 5B.4 paso 5 (2026-07-18): config 'simple'
│                     (no 'spanish' — corpus mezcla EN/ES) + tsquery armado a mano con OR ('|')
│                     entre palabras vía _build_or_tsquery(), no plainto_tsquery (fuerza AND de
│                     todas las palabras — inviable con preguntas parafraseadas de 15-20 palabras)
│                     + _STOPWORDS (ES+EN) para que el OR no matchee solo por "de"/"la"/"el"
│                     compartidas con la pregunta. Medido contra las 520 preguntas de
│                     evals/ground_truth_retrieval.json: keyword hit_rate 0.008 → 0.300 (ver
│                     CHANGELOG 2026-07-18 para la progresión completa del debugging).
│                     [dead code pendiente: _index/InMemoryIndex/set_index ya no los usa
│                     rag_search(), quedan sin uso hasta el paso 6 de la Sesión 2 (limpieza,
│                     no confundir con el paso 6 de 5B.4 abajo)]
├── graph.py       ✅ StateGraph con routing condicional — SYSTEM_PROMPT con el caso de uso real
│                     (instrumentación de campo, agua potable/saneamiento) desde 5B.4 paso 3
│                     (2026-07-15). Sigue inline en este archivo, no en uno propio (ver pendiente
│                     en POSPUESTO). Desde 5B.3 paso 2 (2026-07-23) exporta `graph_builder` SIN
│                     compilar (antes compilaba con MemorySaver a nivel de módulo) — cada
│                     consumidor decide su propio checkpointer llamando `.compile()`
├── main.py        ✅ FastAPI POST /chat + lifespan construye índice al arrancar
│                     [pendiente paso 6: ese build_index() ya no lo usa rag_search(),
│                     re-embebe docs.txt con la API de OpenAI en cada arranque para nada]
│                     Desde 5B.3 paso 3 (2026-07-23): el lifespan abre un `psycopg_pool.ConnectionPool`
│                     real a Postgres (autocommit=True, prepare_threshold=0 — ver nota abajo),
│                     corre `checkpointer.setup()` (idempotente, crea tablas de PostgresSaver) y
│                     recien ahi compila `graph_builder.compile(checkpointer=...)`, guardado en
│                     variable global `graph`. Pool se cierra despues del `yield`. `/chat` valida
│                     `graph is None` ademas de `settings is None`.
│                     Verificado contra Supabase real (2026-07-24): `checkpointer.setup()` crea
│                     las 4 tablas (checkpoints/checkpoint_blobs/checkpoint_writes/
│                     checkpoint_migrations) y dos `graph.invoke()` con el mismo thread_id
│                     confirman persistencia real de la conversación (script manual fuera del
│                     repo, no vive en scripts/).
├── schemas.py     ✅ ChatRequest, ChatResponse, TicketInput, RAGResult (Capa 4)
└── ingestion.py   ✅ chunking + embeddings OpenAI (embed_texts() batchea de a 300 textos por request,
                      límite de la API de OpenAI: 300k tokens / 2048 items por request, tocado 5B.4
                      paso 2) + InMemoryIndex numpy + KeywordIndex TF-IDF + rrf() (Capa 5A/5A.2).
                      Cliente de OpenAI (_client) se crea recién en embed_texts(), no al importar el
                      módulo (fix 2026-07-15) — antes exigía OPENAI_API_KEY solo con importar
                      src.graph/src.tools, tumbaba el job rules de CI

scripts/
└── ingest.py      ✅ ingesta manual: docs/pdfs/*.pdf → chunks → embeddings → tabla chunks en Supabase
                      (Capa 5B.1, extendido 5B.4 paso 2). _read_pdf() nuevo (pypdf, sin OCR) +
                      CHUNK_SIZE=1000/CHUNK_STEP=800 locales al script (no toca el default 500/250 de
                      src/ingestion.py:chunk_text()). Corrida real contra Supabase el 2026-07-14:
                      2451 chunks / 11 documentos insertados, verificado con SELECT COUNT(*).

docs/
└── pdfs/                 ✅ 11 PDFs de instrumentación de campo (Capa 5B.4 paso 1, 2026-07-14) —
                             5 Emerson/Rosemount, 4 Siemens/Sitrans, 2 Endress+Hauser, gitignored
                             (ver CORPUS_INSTRUMENTACION.MD)

archive/
└── langgraph-intro.txt  ✅ movido fuera de docs/ (2026-07-14, git mv) — ya no se ingesta con
                             el corpus real; scripts/ingest.py e InMemoryIndex (src/main.py) solo
                             leen docs/*.txt, docs/ ahora solo tiene pdfs/

tests/
├── conftest.py    ✅ fixtures: agent_graph, sample_responses, invoke_agent. Desde 5B.3 paso 4
│                     (2026-07-23): agent_graph importa `graph_builder` (sin compilar) y compila
│                     con `MemorySaver()` en la fixture — no depende de Postgres para correr
├── test_rules.py  ✅ 7 tests — 5 deterministas sin API; los 2 de rag_search pegan a Postgres+OpenAI
│                     reales desde 5B.2 y se saltan con pytest.skip si falta OPENAI_API_KEY/
│                     DATABASE_URL (fix 2026-07-15, mismo patrón que invoke_agent en conftest.py)
├── test_evals.py  ✅ LLM-as-judge usando evaluators.py compartido
└── reports/       ✅ pytest-html local + artefacto en CI

evals/
├── golden_set.json           ✅ (2026-07-27) 48 preguntas sobre el corpus real de instrumentación
│                                 (12 por categoría: factual/procedimental/inferencial/borde), con
│                                 expected_answer generada por LLM grounded en los chunks reales —
│                                 evals/generate_golden_set.py. Reemplaza las 20 preguntas viejas
│                                 sobre LangGraph docs (corpus que ya no existe en Supabase).
├── generate_ground_truth.py  ✅ (5B.4 paso 4, 2026-07-17) genera ground truth de retrieval:
│                                 samplea 1 anclaje cada 20 chunks por documento (equiespaciado),
│                                 ventana de 2 chunks consecutivos por anclaje, LLM + structured
│                                 output (client.beta.chat.completions.parse, patron HW4) genera
│                                 preguntas factual/procedimental/inferencial/borde por ventana.
│                                 Script manual (python -m evals.generate_ground_truth), no lo
│                                 llama la app ni CI — mismo patron que scripts/ingest.py.
│                                 [hallazgo sin resolver: las 130 ventanas generaron exactamente
│                                 4 preguntas cada una pese a que el prompt pedia "1 a 4, solo las
│                                 categorias que el fragmento sostiene" — muestreo manual de la
│                                 primera ventana no mostro preguntas forzadas, pero no se reviso
│                                 el resto; vigilar si esto genera ruido en hit_rate/mrr del paso 5]
├── ground_truth_retrieval.json ✅ (5B.4 paso 4, 2026-07-17) salida real de generate_ground_truth.py
│                                 contra Supabase+OpenAI: 520 preguntas (factual 138, procedimental
│                                 133, inferencial 128, borde 121) sobre 130 ventanas / 11 documentos.
│                                 Cada registro: question, category, chunk_ids (lista — 1 elemento
│                                 para ventanas de 1 chunk al final de un documento, 2 en el resto),
│                                 source. Commiteado 2026-07-18 (commit 15bf4bd).
├── generate_golden_set.py   ✅ (2026-07-27) genera evals/golden_set.json nuevo: samplea 12
│                                 preguntas por categoría (48 total, seed=42 fijo) de las 520 de
│                                 ground_truth_retrieval.json, trae el contenido real de sus
│                                 chunk_ids desde Supabase, y le pide al LLM que escriba la
│                                 expected_answer grounded en ese texto — no inventa preguntas
│                                 nuevas, reusa el mapeo pregunta→chunk ya verificado en 5B.4.
│                                 Distinto de generate_ground_truth.py: aquel mide retrieval
│                                 (hit_rate/mrr), este arma la referencia para medir generación
│                                 (accuracy_evaluator, ver evaluators.py abajo). Script manual
│                                 (python -m evals.generate_golden_set), no lo llama la app ni CI.
├── retrieval_metrics.py ✅ (5B.4 pasos 5-6, 2026-07-18) compute_relevance/hit_rate/mrr/evaluate,
│                            patron de M4 portado y parametrizado para _vector_search/
│                            _keyword_search/_hybrid_search de src/tools.py. Acierto definido por
│                            chunk_ids (no filename, a diferencia de M4 — ver nota del paso 4).
│                            Script manual (python -m evals.retrieval_metrics), no lo llama la app
│                            ni CI. Corrida real contra las 520 preguntas destapó y motivo el fix
│                            de _keyword_search en src/tools.py (ver "Estado actual del repo"
│                            arriba y CHANGELOG 2026-07-18 para la progresion completa). Tambien
│                            corre el barrido de k de RRF (RRF_K_VALUES) para el paso 6.
│                            Metricas finales @top_k=5, k=1 (default nuevo, ver src/ingestion.py):
│                            vector 0.231/0.141, keyword 0.300/0.197, hybrid 0.317/0.186
│                            (hit_rate/mrr) — hybrid ahora supera a los dos individuales en ambas
│                            metricas, sin trade-off.
├── evaluators.py    ✅ relevance (LLM-judge, sin referencia — juzga la respuesta en el vacío),
│                       accuracy (LLM-judge, nuevo 2026-07-27 — compara la respuesta del agente
│                       contra expected_answer del golden set; complementario a relevance, no
│                       lo reemplaza: relevance sigue siendo el único que sirve para casos sin
│                       referencia, ej. el flujo de create_ticket en test_evals.py), citation
│                       (code), convergence (code) + @traceable para LangSmith (Capa 3B)
├── run_evals.py     ✅ corre evals, guarda resultados por fecha/hora
│                       + client.create_feedback() para LangSmith (Capa 3B). Desde 5B.3 paso 4
│                       (2026-07-23): importa `graph_builder` y compila con `MemorySaver()` a
│                       nivel de módulo (sin problema, a diferencia de Postgres no abre ninguna
│                       conexión real ni depende de credenciales) — un eval es una corrida de
│                       una sola pasada, no necesita que el checkpoint sobreviva un reinicio.
│                       Desde 2026-07-27: cada caso corre accuracy_evaluator además de
│                       relevance_evaluator, el resumen agrega avg_accuracy, y el feedback a
│                       LangSmith manda las dos keys (relevance/accuracy) en vez de solo una.
└── results/         ✅ JSONs organizados por YYYY-MM-DD/HH-MM-SS
                        (corridas: 2026-05-29, 05-30, 06-01, 06-03, 2026-07-27 — primera corrida
                        real contra el golden set de instrumentación nuevo: 48 casos, relevancia
                        4.44/5, accuracy 3.88/5, 85% con cita, 4.08 pasos promedio. Hallazgo sin
                        investigar: 5/48 preguntas respondibles con el manual terminaron en
                        create_ticket en vez de una respuesta directa — candidato a explicar
                        parte de la brecha relevancia/accuracy)

.github/
└── workflows/
    └── ci.yml     ✅ rules en cada push, evals solo en main (MAX_EVAL_CASES=1)
                      + LANGCHAIN_API_KEY como secret (Capa 3B)
                      [conocido, roto a propósito: job evals falla con RuntimeError "Falta
                      DATABASE_URL" — rag_search() necesita Postgres real desde 5B.2, ese secret
                      nunca se agregó a evals. ACTUALIZADO 2026-07-27: el bloqueo de contenido ya
                      no aplica (golden_set.json dejó de ser sobre LangGraph docs, ver evals/
                      arriba) — sigue roto por dos motivos técnicos sin resolver: (1) falta
                      agregar DATABASE_URL como secret, decidido con Juan usar un rol de
                      Postgres de solo lectura (GRANT SELECT en chunks, sin permisos de
                      escritura/DDL) en vez de reusar la credencial completa de producción,
                      todavía no creado; (2) tests/test_evals.py tiene 2 preguntas
                      hardcodeadas en el código (no en golden_set.json) del dominio viejo
                      (reembolso, ticket de login) que también hay que reemplazar. Es el
                      próximo paso concreto de la prioridad 1 de más abajo]

── PRÓXIMO PASO ──
Capa 5B.2 completa (2026-07-04). rag_search() corre 100% sobre Postgres:
1. ✅ _get_connection()
2. ✅ _vector_search(conn, query_embedding, top_k)
3. ✅ _keyword_search(conn, query, top_k)
4. ✅ _hybrid_search(conn, query, query_embedding, top_k, candidate_k=10) — pide 10
   candidatos a cada búsqueda, fusiona con rrf(), corta a top_k (mismo patrón que
   el InMemoryIndex.hybrid_search() de 5A.2).
5. ✅ rag_search() reescrito: abre conexión (try/finally para garantizar close()),
   embebe la query con embed_texts([query])[0], llama _hybrid_search(), trae
   content/source con SELECT ... WHERE id = ANY(ids), y reordena con un diccionario
   {id: (content, source)} recorriendo fused (que ya viene ordenado por RRF) —
   sin eso, Postgres devuelve las filas en su propio orden, no en el de relevancia.
   Verificado contra Supabase real (query "que es langgraph") y con los 7 tests
   de test_rules.py pasando sin cambios.

Capa 5B.3 — Postgres checkpointer (MemorySaver → PostgresSaver). Diseño cerrado
(2026-07-07), código de los 4 pasos completo (2026-07-23) — falta verificar contra
Supabase real antes de dar la capa por cerrada (ver nota abajo):
1. ✅ (2026-07-23) Instalado langgraph-checkpoint-postgres==3.1.0 (trae psycopg v3 +
   psycopg_pool, driver distinto al psycopg2 que ya usa tools.py — conviven a
   propósito, no se migra tools.py). Hallazgo en el camino: `psycopg` puro necesita
   la librería nativa `libpq` instalada en el sistema — no está en este Windows, el
   import fallaba. Se instaló `psycopg[binary]` (wheel autocontenido, mismo motivo
   por el que el proyecto ya usa `psycopg2-binary` y no `psycopg2` a secas).
2. ✅ (2026-07-23) graph.py: ya no compila el grafo a nivel de módulo (antes corría
   al importar, antes de que exista el lifespan). Ahora exporta `graph_builder` sin
   compilar — se sacó el import de MemorySaver del archivo, ya no se usa ahí.
3. ✅ (2026-07-23) main.py: el lifespan abre un `psycopg_pool.ConnectionPool` real
   (kwargs `autocommit=True` — cada operación del checkpointer se confirma sola, sin
   dejar transacciones abiertas; `prepare_threshold=0` — evita prepared statements,
   que pueden fallar si DATABASE_URL pasa por un pooler tipo pgbouncer), llama
   `checkpointer.setup()` (idempotente) y compila `graph_builder.compile(checkpointer=...)`
   ahí adentro, guardado en variable global `graph`. Pool se cierra después del `yield`.
   `/chat` valida `graph is None` además de `settings is None`.
4. ✅ (2026-07-23) tests/conftest.py y evals/run_evals.py ya no importan `graph`
   compilado (ya no existe ese nombre) — importan `graph_builder` y compilan cada
   uno con `MemorySaver()`: conftest.py dentro de la fixture `agent_graph` (lazy, por
   test), run_evals.py a nivel de módulo (sin problema — MemorySaver no abre
   conexión real ni depende de credenciales, a diferencia del Postgres de main.py).
   7 tests de test_rules.py verificados en verde con el fix.

**Verificado contra Supabase real (2026-07-24):** script manual (pool + `setup()` + dos
`graph.invoke()` con el mismo `thread_id`, fuera del repo). `setup()` creó/confirmó las
4 tablas de PostgresSaver. El segundo invoke recordó el dato dado en el primero —
persistencia real confirmada, no solo código que compila.

**Capa 5B.3 completa, 2026-07-24. Capa 5B (pgvector/Supabase + FTS) y Capa 5 (RAG real
con PDFs) quedan completas.**

Capa 5B.4 — Corpus real (instrumentación de campo) + framework de evals de M4.
PRIORIDAD ACTUAL (decidido 2026-07-13). Plan completo en CORPUS_INSTRUMENTACION.MD
(no duplicado acá) — resuelve la decisión pospuesta en el handoff de M4
(courses/POST_COURSE_ZOOMCAMP_M4.md, 2026-07-11): portar hit_rate/mrr/evaluate()
quedaba condicionado a que docs/ dejara de tener un solo archivo. El corpus nuevo
(instrumentación de campo — presión/caudal/temperatura — para agua potable y
saneamiento, 12 PDFs de Emerson/Siemens/Endress+Hauser, justificado por experiencia
real de Juan como consultor técnico en el rubro) es ese salto de volumen. Pasos
(ver detalle en CORPUS_INSTRUMENTACION.MD):
1. ✅ Descargar los PDFs del checklist a carpeta fuente gitignored (2026-07-14).
   Terminaron siendo 11, no 12: los 6 links de Rosemount originales estaban
   rotos (URLs con codificación de caracteres corrupta, HTTP 400/404
   confirmado con curl) — reemplazados por 5 documentos en inglés verificados
   HTTP 200 (Emerson no publica todas las versiones ES); el bonus ES de 3051
   y el ítem "ampliar E+H" quedaron sin bajar. Detalle completo y checklist
   marcado en CORPUS_INSTRUMENTACION.MD. Los 11 PDFs están en docs/pdfs/,
   verificados %PDF válidos, renombrados fabricante_modelo_tipo_idioma.pdf.
2. ✅ (2026-07-14) — scripts/ingest.py extendido con soporte real de PDFs:
   load_documents() ahora también lee docs/pdfs/*.pdf vía _read_pdf() nuevo
   (pypdf.PdfReader, sin OCR — páginas escaneadas sin capa de texto quedan
   vacías). Se agregaron CHUNK_SIZE=1000/CHUNK_STEP=800 (antes 500/250
   default de chunk_text()) — manuales más largos/densos que
   docs/langgraph-intro.txt, con procedimientos y tablas que no conviene
   cortar cada 500 caracteres; el default de src/ingestion.py no se tocó
   (lo comparten Capa 5A en memoria y tests/evals), el ajuste queda local a
   este script. Decisión pypdf vs pdfplumber verificada empíricamente sobre
   páginas con tablas reales (ficha Siemens P320/P420 + manual Rosemount
   2051): texto plano equivalente entre ambas, extracción estructurada de
   tablas de pdfplumber funciona en Rosemount pero falla en Siemens (no
   confiable en todo el corpus) → se descarta pdfplumber, queda pypdf==5.1.0
   en requirements.txt. Evidencia real de headers/footers repetidos por
   página (título del doc + número de página, en Siemens y Rosemount) —
   **decisión tomada: no limpiar por ahora.** Previsualización sin costo
   (chunking de 3 PDFs de muestra sin llamar a embed_texts()) mostró que el
   ruido es 2-3 líneas cortas contra chunks de 1000 caracteres, dilución
   baja; se corre tal cual y se re-evalúa con datos reales de retrieval en
   el paso 6 si hace falta, antes de invertir en un limpiador por fabricante
   (5 formatos de header/footer distintos). docs/langgraph-intro.txt movido
   a archive/ (git mv) para que la ingesta real no lo mezcle con el corpus
   nuevo. Encontrado y arreglado en el camino: embed_texts()
   (src/ingestion.py) mandaba todos los chunks en un solo request — con
   2451 chunks (~626k tokens) supera el límite de la API de OpenAI (300k
   tokens / 2048 items por request); ahora batchea de a 300. **Corrida real
   contra Supabase (2026-07-14):** TRUNCATE + 2451 chunks insertados desde
   los 11 PDFs, verificado con SELECT COUNT(*)/COUNT(DISTINCT source) →
   (2451, 11). De paso, cerrado un hallazgo de seguridad de Supabase: la
   tabla chunks quedó pública vía la API REST (RLS deshabilitado, alerta
   automática de Supabase) — se habilitó `ALTER TABLE chunks ENABLE ROW
   LEVEL SECURITY;` sin policies (el backend conecta por rol directo de
   Postgres, no por la API REST/anon key, así que no se vio afectado),
   verificado con `SELECT relrowsecurity FROM pg_class` → true.
3. ✅ (2026-07-15) — Actualizado el SYSTEM_PROMPT (graph.py) con el caso de uso real:
   soporte técnico de instrumentación de campo para agua potable/saneamiento,
   con instrucción explícita de grounding (usar rag_search antes de responder,
   citar fuente, no inventar datos de calibración/rangos/procedimientos) y de
   cuándo usar create_ticket. README.md reescrito: caso de uso, cómo funciona,
   de dónde sale el corpus (nota de compliance), cómo correrlo.
4. ✅ (2026-07-17) — Generar ground truth con LLM + structured output (patrón HW4 de M4).
   Diseño acordado con Juan antes de programar: la unidad de generación no podía ser "documento
   completo" (11 docs, demasiado grueso — cualquier chunk del documento contaría como acierto en
   Hit Rate) ni "5 preguntas por documento" al estilo de un proyecto anterior de Juan en Valkimia
   (mismo problema de granularidad). Se resolvió con sampling proporcional al tamaño real de cada
   documento: 1 anclaje cada 20 chunks (equiespaciado por chunk_index, no al azar, para cubrir todo
   el manual), ventana de 2 chunks consecutivos por anclaje (cubre procedimientos cortos que cruzan
   un chunk; criterio de "acierto vecino" ±1 justificado por el 20% de overlap real de
   CHUNK_STEP=800/CHUNK_SIZE=1000 — a esa distancia dos chunks ya no comparten texto). El "chunk
   correcto" de cada pregunta queda definido por construcción (los chunk_ids de la ventana que vio
   el LLM), no por una heurística posterior. Se acotó el alcance a 4 categorías que sí alimentan
   Hit Rate/MRR (factual, procedimental, inferencial, borde) — preguntas "no soportadas"
   (out-of-scope) quedan pendientes aparte porque no tienen chunk correcto y sirven para otro tipo
   de eval (nivel agente, no retrieval). `evals/generate_ground_truth.py` corrido contra Supabase +
   OpenAI reales (confirmado con Juan antes de ejecutar, ~130 llamadas pagas): 520 preguntas en
   `evals/ground_truth_retrieval.json`. Detalle y hallazgo pendiente de revisar en "Estado actual
   del repo" arriba.
5. ✅ (2026-07-18) — Portado hit_rate/mrr/evaluate() a evals/retrieval_metrics.py, patrón M4
   parametrizado para _vector_search/_keyword_search/_hybrid_search de src/tools.py (acierto por
   chunk_ids, no filename — ver paso 4). La primera corrida real (top_k=5, 520 preguntas) destapó
   un bug real en _keyword_search: hit_rate 0.008, prácticamente inútil. Investigado y arreglado en
   la misma sesión (dos intentos fallidos antes del fix real — ver CHANGELOG 2026-07-18 para la
   progresión completa): plainto_tsquery armaba un AND de las 15-20 palabras de cada pregunta
   parafraseada (criterio casi imposible de cumplir), agravado por el corpus bilingüe (8/11 PDFs en
   inglés) y por que 'simple' no elimina stopwords españolas. Fix: OR armado a mano
   (_build_or_tsquery) + filtro de stopwords ES/EN (_STOPWORDS) en src/tools.py. Verificado con
   Juan que la brecha ES/EN resultante ya no es un artefacto sino el límite estructural real de
   keyword search monolingüe (ver nota en "Estado actual del repo"); descartada la idea de separar
   en dos RAGs por idioma porque el corpus no tiene cobertura duplicada (8 PDFs solo existen en
   inglés). Métricas finales @top_k=5: vector 0.231/0.141, keyword 0.300/0.197 (supera a vector),
   hybrid 0.312/0.180 (hit_rate mejora, pero MRR queda entre los dos individuales — RRF con k=60
   default no suma toda la ventaja de keyword). El fix cambia también el rag_search() real que usa
   el agente (mismo _keyword_search), no solo las métricas — 7 tests de test_rules.py verificados
   en verde con la query SQL nueva.
6. ✅ (2026-07-18) — Barrido de k de RRF (k=[1,50,60,100,200]) contra las 520 preguntas del ground
   truth, top_k=5. Resultado: k=1 gana en hit_rate (0.3173) y MRR (0.1858) a la vez — sin trade-off
   que resolver con el criterio acordado (priorizar hit_rate: el agente manda todo el top-k al LLM
   como contexto, no hay "posición #1" que importe como en un buscador tradicional). k=50/60/100/200
   dan resultados idénticos entre sí (0.3115/0.1797) — con candidate_k=10, un k mucho mayor que el
   rango de posiciones aplana las diferencias de rank hasta volverlas irrelevantes, no es que 60 sea
   "casi tan bueno" como 100, es que a partir de cierto punto k deja de cambiar el resultado. Default
   actualizado de 60 a 1 en `rrf()` (`src/ingestion.py`) y `_hybrid_search()` (`src/tools.py`,
   parámetro `rrf_k`) — cambia el comportamiento real de `rag_search()` en producción, no solo las
   métricas. 7 tests de `test_rules.py` verificados en verde con el nuevo default.

**Capa 5B.4 completa (6/6 pasos), 2026-07-18.**

Nota (2026-07-15): al pushear el trabajo pendiente de 5B.4 pasos 1-2 (primera vez
que corría CI desde la migración a Postgres de 5B.2), aparecieron dos fallas en
GitHub Actions — ninguna causada por el push en sí, latentes desde antes, recién
visibles porque CI no corría hacía rato (local estaba varios commits adelante de
origin/main):
- Job rules: ImportError al importar src.graph — src/ingestion.py creaba el
  cliente de OpenAI a nivel de módulo (_client = OpenAI()), exigiendo API key
  solo con importar, y ese job corre a propósito sin ninguna. Arreglado con
  cliente perezoso. Efecto secundario encontrado en el camino: 2 tests de
  tests/test_rules.py (test_rag_search_contains_query_word,
  test_rag_search_returns_string) llaman rag_search() de verdad — dejaron de
  ser "deterministas sin API" desde 5B.2 sin que nadie lo notara, porque CI no
  había vuelto a correr. Ahora se saltan con pytest.skip si falta
  OPENAI_API_KEY/DATABASE_URL. Job rules verificado en verde con y sin esas
  env vars (ver detalle en "Estado actual del repo" arriba).
- Job evals: RuntimeError "Falta DATABASE_URL" — sigue roto, a propósito. Ver
  nota en ci.yml arriba. Se destraba con el paso 4 de acá arriba (ground truth
  nuevo + decidir si CI usa una Supabase separada de la real antes de meter esa
  credencial como secret).

── PLAN PARA CERRAR CAPA 5B (definido 2026-07-06, tras repaso M3 Zoomcamp) ──
Ver courses/POST_COURSE_ZOOMCAMP_M3.md para el detalle completo de la auditoría y el
porqué de cada punto. Orden acordado originalmente, uno por sesión — reordenado el
2026-07-13 (ver nota abajo):

Sesión 0 — 5B.4, corpus real + evals de M4. ✅ COMPLETA (2026-07-18, 6/6 pasos —
  ver plan arriba y detalle completo en CORPUS_INSTRUMENTACION.MD).

Sesión 1 — 5B.3 (Postgres checkpointer). ✅ COMPLETA (2026-07-24). Cierra Capa 5B
  formalmente. Diseño cerrado el 2026-07-07, código completo el 2026-07-23, verificado
  contra Supabase real el 2026-07-24 (ver detalle en PRÓXIMO PASO). Nota (2026-07-18):
  esta sesión se había pausado por el
  curso en paralelo (LLM Zoomcamp M5, Monitoring, HW con entrega 2026-07-20).
  Actualización (2026-07-22): HW5 entregado, videos/apuntes de M5 completos (ver
  courses/POST_COURSE_ZOOMCAMP_M5.md) — la pausa ya no aplicaba, por eso se retomó
  5B.3 el 2026-07-23.

Sesión 2 — batch de limpieza y mejoras chicas (todo mecánico, sin conceptos nuevos,
15-45 min cada uno):
- Paso 6: sacar build_index()/set_index()/_index/InMemoryIndex muerto de
  src/main.py y src/tools.py (ya no alimentan a rag_search() desde 5B.2).
- Prender tracing real del agente (LANGCHAIN_TRACING_V2 para el runtime de /chat,
  no solo para evals/ — gap encontrado en la auditoría de M3, reconfirmado en la
  auditoría de M5). Actualización (2026-07-22, ver
  courses/POST_COURSE_ZOOMCAMP_M5.md): al prender esto, sumar en el mismo cambio
  el patrón de M5 — nombrar spans por paso interno (rag_search, vector/keyword,
  create_ticket) y tokens/costo como atributos de span, aplicado vía LangSmith
  (no vía OTel crudo, ver POSPUESTO).
- Poblar ChatResponse.tool_calls_used en main.py (deuda técnica desde Capa 5A,
  2026-06-20, campo siempre devuelve []).
- max_tokens explícito en get_bound_llm() (aprendizaje empírico de M3: resúmenes
  largos escalan ~2.3x tokens de output).
- ~~Actualizar el SYSTEM_PROMPT de graph.py~~ — hecho en 5B.4 paso 3 (2026-07-15),
  ya no es parte de esta sesión.
- Arreglar el contrato de RAGResult.score (src/schemas.py): dice ge=0.0/le=1.0 y se
  describe como "similitud coseno", pero rag_search() le pasa el score de RRF (no
  coseno). Safe hoy SOLO por casualidad — con k=1 el máximo de RRF es exactamente 1.0
  (un chunk en rank 0 de ambas listas: 0.5+0.5); si cambiara k, score>1.0 tiraría
  ValidationError dentro de rag_search() en producción. Sacar/subir el le=1.0 y
  corregir la descripción a "score de fusión RRF" (detectado 2026-07-24).
- Redominar el schema de create_ticket (src/schemas.py:TicketInput): las categorías
  bug/feature/question son vocabulario prestado del curso DeepLearning (soporte de
  software) y no encajan en instrumentación de campo. Reformular como orden de
  trabajo / aviso de mantenimiento con campos del dominio (equipo/modelo, planta,
  síntoma, código de error, prioridad). Cambio de schema barato, sin persistencia
  (ver POSPUESTO para la persistencia real). Detectado 2026-07-24.

Nota (2026-07-11): este plan asumía "Sesión 2 → recién ahí arrancar M4". En la
práctica M4 se cursó en paralelo, sin esperar a la Sesión 2, y ya terminó (videos +
HW ✓, ver courses/POST_COURSE_ZOOMCAMP_M4.md).

Nota (2026-07-13): con CORPUS_INSTRUMENTACION.MD ya diseñado, Juan decidió priorizar
el corpus nuevo (Sesión 0 / 5B.4) por delante de las Sesiones 1 y 2, que quedan en
pausa sin cambios hasta que 5B.4 avance.

Nota (2026-07-24, revisión estratégica con Opus 4.8): repaso completo del repo +
roadmap. Objetivo confirmado: portfolio para conseguir trabajo, pero SIN fecha dura
→ balancear profundidad de retrieval (ya muy sólida) con cerrar huecos de "producto
navegable". Diagnóstico: se profundizó mucho en retrieval y quedaron huecos de
producto (CI en rojo, sin deploy, create_ticket stub, evals de generación nunca
corridos sobre el corpus real). Reordenamiento de prioridades acordado, DESPUÉS de
cerrar 5B.3:
1. CI en verde + seguridad — arreglar/aislar el job de evals roto (ver ci.yml) y
   ADELANTAR la rotación de credenciales + limpieza de historial de git a AHORA (ya
   no "antes de hacerlo público": reescribir historial se vuelve más difícil cuanto
   más crece, ver POSPUESTO actualizado).
2. Evals del corpus real — correr el LLM-as-judge sobre las 520 preguntas de
   instrumentación (medir si el agente RESPONDE bien, no solo si recupera; ver
   POSPUESTO "LLM-as-judge sobre corpus nuevo"). Sinérgico con el punto 1: ese
   dataset puede alimentar el job de CI de evals que hoy está roto.
Sesión 2 (limpieza) y deploy (Capa 6) quedan después, sin fecha. Modelo de trabajo:
Sonnet 5 para construir día-a-día, Opus 4.8 para sesiones de arquitectura/estrategia.

Actualización (2026-07-24, misma sesión): Capa 5B.3 verificada contra Supabase real y
commiteada/pusheada (`921ab4f`). Capa 5B y Capa 5 quedan completas. Arranca la
prioridad 1 de arriba: CI en verde + seguridad (rotación de credenciales + limpieza de
historial de git).

Actualización (2026-07-27): al abrir la prioridad 1 (arreglar/aislar el job de evals de
CI), apareció que el job estaba roto en dos capas distintas, no solo la técnica (falta
DATABASE_URL): golden_set.json seguía siendo sobre LangGraph docs, corpus que ya no
existe en Supabase — conectar DATABASE_URL sin cambiar eso solo hubiera cambiado el
error, no arreglado el job. Se decidió resolver el bloqueo de contenido primero: nuevo
`evals/generate_golden_set.py` (48 preguntas del corpus de instrumentación, 12 por
categoría, con expected_answer grounded generada por LLM a partir de las 520 preguntas
y chunk_ids ya verificados en 5B.4) + `accuracy_evaluator` nuevo en `evaluators.py`
(compara la respuesta del agente contra esa referencia — complementa, no reemplaza, a
`relevance_evaluator`). Wireado en `run_evals.py` y corrido contra Supabase+OpenAI
reales: 48 casos, relevancia 4.44/5, accuracy 3.88/5, 85% con cita (resultados en
`evals/results/2026-07-27/`). La prioridad 2 (evals del corpus real) queda así
adelantada y parcialmente resuelta — con 48 preguntas sampleadas, no las 520 completas
(decisión de costo/alcance, ver POSPUESTO). La prioridad 1 sigue sin cerrar: falta
agregar DATABASE_URL como secret de CI (con un rol de Postgres de solo lectura, no la
credencial completa — decidido con Juan, no implementado) y reemplazar las 2 preguntas
hardcodeadas del dominio viejo en `tests/test_evals.py`. La rotación de credenciales +
limpieza de historial de git tampoco se tocó todavía.

── POSPUESTO (registrado, no bloquea nada de lo de arriba) ──
- Connection pool para Postgres (hoy conexión nueva por request en rag_search(),
  anotado como mejora de performance desde 5B.2).
- Rotar credenciales reales (OPENAI_API_KEY, DATABASE_URL) + limpiar historial de
  git (pendiente de seguridad desde 2026-07-02, no bloquea desarrollo local).
  Confirmado 2026-07-15: el repo en GitHub es privado hoy, así que no es urgente
  por exposición pública inmediata — pero es condición explícita antes de pasarlo
  a público. ACTUALIZADO 2026-07-24: adelantado — deja de ser "antes de público" y
  pasa a ser la prioridad #1 después de 5B.3 (junto con CI en verde). Motivo:
  reescribir historial de git se vuelve más difícil cuanto más crece, y es fácil que
  el repo se haga público por impulso/accidente con las keys adentro. Ver nota de la
  revisión estratégica 2026-07-24 en el plan de cierre de Capa 5B, arriba.
- Supervisor multi-agente / create_react_agent prebuilt — descartados por ahora
  en el handoff de M3 (repo monolítico resuelve bien el dominio actual).
- .env.example volvió a guardarse en UTF-16 (se había corregido a UTF-8 el
  2026-07-01) — detectado 2026-07-15 al escribir el README, no se tocó para no
  desviarse del paso 3.
- Separar los prompts a archivo(s) propio(s) en vez de vivir inline en graph.py
  (pedido de Juan, 2026-07-15, al corregir que ROADMAP.md listaba un
  src/prompts.py que nunca existió).
- Persistencia real de create_ticket en Postgres (capa futura explícita opcional,
  no deuda escondida — discutido 2026-07-24). El concepto de escalar SÍ encaja en el
  dominio (orden de trabajo cuando el manual no cubre la consulta o requiere técnico
  de campo), pero hoy la tool es un stub que solo hace print() y devuelve un string;
  nunca persiste. Primero se redomina el schema (ver Sesión 2); la tabla tickets +
  INSERT real + recuperación cierran el caso de uso end-to-end recién cuando se
  encare el deploy (Capa 6) — no antes, no es prioridad con el objetivo actual.
- Framework de evals de generación (RAGAS u otro) como capa adicional sobre las
  métricas propias, no reemplazo — discutido 2026-07-18. Orden decidido:
  primero terminar hit_rate/mrr propios (pasos 5-6 de 5B.4, en curso) porque
  programarlos a mano es la señal de conocimiento real; recién después sumar
  RAGAS (o similar) para métricas de generación end-to-end (faithfulness,
  answer relevancy, context precision/recall) que son tediosas de replicar
  bien a mano. Combinación retrieval-metrics propias + RAGAS para generación
  es el objetivo para un repo profesional — no portar hit_rate/mrr a una
  librería externa.
- FTS por idioma real (columna `language` por chunk, detectada al ingestar +
  `to_tsvector(lang::regconfig, content)` en vez del `'simple'` global fijo de
  hoy) — discutido 2026-07-18 al arreglar `_keyword_search` (ver paso 5 de
  5B.4 y CHANGELOG). Es el patrón "de producción" correcto para corpus
  multilingües, pero sobre-ingeniería para 11 documentos; el filtro de
  stopwords ES/EN alcanza para el tamaño actual del corpus. Reconsiderar si
  el corpus crece a más idiomas o más documentos por idioma.
- ~~LLM-as-judge (relevance) sobre las 520 preguntas del corpus nuevo~~ —
  RESUELTO PARCIALMENTE 2026-07-27: `evals/generate_golden_set.py` arma un
  golden_set.json nuevo (48 preguntas, no las 520 — sampling estratificado
  12 por categoría) con expected_answer grounded, y `accuracy_evaluator`
  (nuevo en `evaluators.py`) corre junto a `relevance_evaluator` vía
  `run_evals.py`. Corrida real: relevancia 4.44/5, accuracy 3.88/5. Sigue
  pendiente si algún día se quiere correr sobre las 520 completas en vez de
  la muestra de 48 (más costo, no decidido que haga falta todavía).
- Migrar de LangSmith a OpenTelemetry puro para tracing — discutido 2026-07-22
  al revisar el handoff de M5 (Monitoring, LLM Zoomcamp). No hay señal
  concreta hoy de que LangSmith se quede corto; sería una migración motivada
  por dos escenarios hipotéticos a futuro: (1) el agente crece con pasos que
  no son LangChain/LangGraph (llamadas propias, otros servicios/lenguajes)
  que LangSmith no puede trazar, o (2) el volumen de trazas supera el tier
  gratuito (5.000/mes, ver Capa 3B) y el costo o el vendor lock-in empiezan a
  pesar. Hasta que uno de esos dos pase, LangSmith sigue siendo la elección
  correcta para este stack (estándar de industria para LangGraph, ya
  integrado con evals) — no resta profesionalismo al repo.
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

## Capa 5 — RAG real con PDFs ✅ COMPLETADA (2026-07-24)

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