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
    5B.2 — Migrar rag_search()        ✅ COMPLETADA (2026-07-04)
    5B.3 — Postgres checkpointer      ← EN PAUSA (diseño cerrado 2026-07-07, sin código;
                                          pospuesta detrás del corpus nuevo, ver 5B.4 abajo)
    5B.4 — Corpus real + evals M4     ← EN PROGRESO (paso 3/6 completo, 2026-07-15;
                                          ver CORPUS_INSTRUMENTACION.MD)
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
│                     [dead code pendiente: _index/InMemoryIndex/set_index ya no los usa
│                     rag_search(), quedan sin uso hasta el paso 6 (limpieza)]
├── graph.py       ✅ StateGraph con routing condicional y MemorySaver — SYSTEM_PROMPT con el caso
│                     de uso real (instrumentación de campo, agua potable/saneamiento) desde 5B.4
│                     paso 3 (2026-07-15); antes era el placeholder de Capa 1. Sigue inline en este
│                     archivo, no en uno propio (ver pendiente en POSPUESTO)
├── main.py        ✅ FastAPI POST /chat + lifespan construye índice al arrancar
│                     [pendiente paso 6: ese build_index() ya no lo usa rag_search(),
│                     re-embebe docs.txt con la API de OpenAI en cada arranque para nada]
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
├── conftest.py    ✅ fixtures: agent_graph, sample_responses, invoke_agent
├── test_rules.py  ✅ 7 tests — 5 deterministas sin API; los 2 de rag_search pegan a Postgres+OpenAI
│                     reales desde 5B.2 y se saltan con pytest.skip si falta OPENAI_API_KEY/
│                     DATABASE_URL (fix 2026-07-15, mismo patrón que invoke_agent en conftest.py)
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
                      [conocido, roto a propósito: job evals falla con RuntimeError "Falta
                      DATABASE_URL" — rag_search() necesita Postgres real desde 5B.2, ese secret
                      nunca se agregó a evals. No se arregla todavía: golden_set.json sigue siendo
                      sobre LangGraph docs (corpus viejo, ya no existe en Supabase), conectar
                      DATABASE_URL ahora solo cambiaría el error. Bloqueado por el paso 4 de 5B.4]

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
(2026-07-07), código pendiente — EN PAUSA, pospuesta detrás de 5B.4 (ver abajo):
1. ⬜ Instalar langgraph-checkpoint-postgres (trae psycopg v3 + psycopg_pool, driver
   distinto al psycopg2 que ya usa tools.py — conviven a propósito, no se migra tools.py).
2. ⬜ graph.py: dejar de compilar el grafo a nivel de módulo (hoy corre al importar,
   antes de que exista el lifespan). Exportar graph_builder sin compilar.
3. ⬜ main.py: abrir un psycopg_pool.ConnectionPool en el lifespan (no una conexión
   cruda — los endpoints sync de FastAPI corren en threadpool, pueden llegar varios
   /chat concurrentes), llamar checkpointer.setup() (idempotente, crea las tablas de
   PostgresSaver) y compilar graph_builder.compile(checkpointer=...) ahí adentro.
4. ⬜ tests/conftest.py y evals/run_evals.py: hoy importan graph ya compilado
   (from src.graph import graph) — pasan a compilar ellos mismos con MemorySaver(),
   para no depender de que Supabase esté arriba solo para correr tests/evals.

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
4. ⬜ Generar ground truth con LLM + structured output (patrón HW4 de M4).
5. ⬜ Portar hit_rate/mrr/evaluate() a evals/retrieval_metrics.py.
6. ⬜ Barrido de k de RRF contra el ground truth real; decidir si el k=60 default
   de src/ingestion.py:104 se ajusta.

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

Sesión 0 (nueva, prioridad actual) — 5B.4, corpus real + evals de M4. Ver plan de
  6 pasos arriba y detalle completo en CORPUS_INSTRUMENTACION.MD. Arranca antes que
  las Sesiones 1 y 2 de abajo porque resuelve una decisión que quedó pospuesta en
  el handoff de M4, y porque el paso 2 (soporte de PDFs en ingest.py) es prerequisito
  real para tener un corpus de producción, no solo para evals.

Sesión 1 — 5B.3 (Postgres checkpointer). Cierra Capa 5B formalmente.
  Diseño cerrado el 2026-07-07 (ver plan de 4 pasos arriba, en PRÓXIMO PASO) —
  EN PAUSA desde 2026-07-09, ahora detrás de la Sesión 0 en la cola. Nada instalado
  ni codeado todavía en 5B.3.

Sesión 2 — batch de limpieza y mejoras chicas (todo mecánico, sin conceptos nuevos,
15-45 min cada uno):
- Paso 6: sacar build_index()/set_index()/_index/InMemoryIndex muerto de
  src/main.py y src/tools.py (ya no alimentan a rag_search() desde 5B.2).
- Prender tracing real del agente (LANGCHAIN_TRACING_V2 para el runtime de /chat,
  no solo para evals/ — gap encontrado en la auditoría de M3).
- Poblar ChatResponse.tool_calls_used en main.py (deuda técnica desde Capa 5A,
  2026-06-20, campo siempre devuelve []).
- max_tokens explícito en get_bound_llm() (aprendizaje empírico de M3: resúmenes
  largos escalan ~2.3x tokens de output).
- Actualizar el SYSTEM_PROMPT de graph.py (sigue siendo el placeholder de Capa 1,
  no menciona rag_search/create_ticket reales — puede terminar fusionado con el
  paso 3 de la Sesión 0 si el system prompt nuevo ya lo cubre).

Nota (2026-07-11): este plan asumía "Sesión 2 → recién ahí arrancar M4". En la
práctica M4 se cursó en paralelo, sin esperar a la Sesión 2, y ya terminó (videos +
HW ✓, ver courses/POST_COURSE_ZOOMCAMP_M4.md).

Nota (2026-07-13): con CORPUS_INSTRUMENTACION.MD ya diseñado, Juan decidió priorizar
el corpus nuevo (Sesión 0 / 5B.4) por delante de las Sesiones 1 y 2, que quedan en
pausa sin cambios hasta que 5B.4 avance.

── POSPUESTO (registrado, no bloquea nada de lo de arriba) ──
- Connection pool para Postgres (hoy conexión nueva por request en rag_search(),
  anotado como mejora de performance desde 5B.2).
- Rotar credenciales reales (OPENAI_API_KEY, DATABASE_URL) + limpiar historial de
  git (pendiente de seguridad desde 2026-07-02, no bloquea desarrollo local).
  Confirmado 2026-07-15: el repo en GitHub es privado hoy, así que no es urgente
  por exposición pública inmediata — pero es condición explícita antes de pasarlo
  a público.
- Supervisor multi-agente / create_react_agent prebuilt — descartados por ahora
  en el handoff de M3 (repo monolítico resuelve bien el dominio actual).
- .env.example volvió a guardarse en UTF-16 (se había corregido a UTF-8 el
  2026-07-01) — detectado 2026-07-15 al escribir el README, no se tocó para no
  desviarse del paso 3.
- Separar los prompts a archivo(s) propio(s) en vez de vivir inline en graph.py
  (pedido de Juan, 2026-07-15, al corregir que ROADMAP.md listaba un
  src/prompts.py que nunca existió).
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