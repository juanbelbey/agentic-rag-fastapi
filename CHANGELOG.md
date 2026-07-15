# CHANGELOG
# agentic-rag-fastapi

Registro cronológico de cambios. Cada entrada corresponde a uno o más commits.
Formato: fecha · tipo · descripción · qué capa representa.

---

## 2026-07-14 — Capa 5B.4 (pasos 1 y 2 completos): PDFs descargados + ingesta real corrida contra Supabase
**Commit:** pendiente (CORPUS_INSTRUMENTACION.MD, docs/pdfs/*, archive/langgraph-intro.txt, .gitignore,
requirements.txt, scripts/ingest.py, src/ingestion.py — sin commitear todavía)

- **Paso 1 completo:** de los 12 PDFs planeados en `CORPUS_INSTRUMENTACION.MD`
  se llegó a **11 finales**. Los 6 links de Rosemount originales devolvían
  HTTP 400/404 — no era un problema del sitio de Emerson sino URLs con
  codificación de caracteres corrupta en el checklist (`%EF%BF%BD` en vez de
  tildes reales, `%F3` en vez de `%C3%B3`). Verificados uno por uno con
  `curl`, reemplazados por 5 documentos en inglés confirmados HTTP 200
  (Emerson no publica todas las versiones en español; el bonus ES del 3051 y
  el ítem "ampliar Endress+Hauser" quedaron sin bajar por redundantes/
  opcionales). Los 11 PDFs (5 Emerson/Rosemount, 4 Siemens/Sitrans,
  2 Endress+Hauser) están en `docs/pdfs/`, verificados como `%PDF` válidos
  (firma de archivo + tamaño razonable, 1-11 MB), renombrados con convención
  `fabricante_modelo_tipo_idioma.pdf` (antes tenían nombres de descarga
  genéricos tipo `dl-rmt-00809-0100-4107.pdf`, confirmados con `pdftotext`
  contra el contenido real de cada uno antes de renombrar). `docs/pdfs/`
  agregada a `.gitignore` (compliance: los tres fabricantes tienen copyright
  sobre estos manuales, no se redistribuyen). `CORPUS_INSTRUMENTACION.MD`
  actualizado: checklist marcado `[x]` con mapeo a cada archivo final, nota
  explicando el fix de los links rotos.
- **Paso 2 completo:** `scripts/ingest.py` extendido — `load_documents()`
  ahora también lee `docs/pdfs/*.pdf` vía `_read_pdf()` nuevo (`pypdf`, sin
  OCR: páginas escaneadas sin capa de texto quedan vacías, no rompen la
  ingesta). `pypdf==5.1.0` agregado a `requirements.txt`.
- **Decisión: `CHUNK_SIZE=1000` / `CHUNK_STEP=800`** para este corpus (antes
  el default de `chunk_text()`, 500/250 — Juan lo recordaba como 1000/500,
  corregido con el código real). Los manuales de instrumentación son mucho
  más largos y densos que `docs/langgraph-intro.txt`, con procedimientos
  paso a paso y tablas de datos técnicos que no conviene cortar cada 500
  caracteres; el overlap baja de 50% a 20% porque duplicar la mitad de cada
  chunk en un corpus de 11 PDFs largos infla mucho el volumen a embeddear
  sin ganancia clara. El default de `src/ingestion.py:chunk_text()` no se
  tocó — lo comparten el pipeline en memoria de Capa 5A y los tests/evals —,
  el ajuste queda local a `scripts/ingest.py` vía dos constantes nuevas
  pasadas explícitas en la llamada dentro de `main()`.
- **Decisión: `pypdf` en vez de `pdfplumber`**, verificada empíricamente y no
  por reputación de la librería. Se instalaron ambas y se comparó su salida
  sobre páginas con tablas reales de dos PDFs del corpus (ficha técnica
  Siemens SITRANS P320/P420, manual de referencia Rosemount 2051 — ubicadas
  primero escaneando todo el documento con `pdfplumber.extract_tables()`
  para encontrar páginas con tablas de verdad, no solo texto corrido). El
  texto plano que devuelven ambas librerías resultó prácticamente idéntico.
  La extracción *estructurada* de tablas de `pdfplumber` funciona bien en el
  manual de Rosemount (tablas con bordes simples) pero falla en el datasheet
  de Siemens (detecta como "tabla" texto decorativo del encabezado en vez de
  la tabla real de parámetros) — no es confiable en todo el corpus, y como
  la tabla `chunks` solo guarda texto plano (no una estructura de tabla
  aparte), la ventaja no se traduce en nada usable. No justifica la
  dependencia extra (`pdfminer.six` + `Pillow`). `pdfplumber` no se agregó a
  `requirements.txt`.
- Encontrada evidencia concreta (no especulativa) de headers/footers
  repetidos en cada página de los PDFs — título del documento y número de
  página se repiten literalmente en Siemens (`"...SITRANS P320/P420 /
  Referencia técnica"` + `1/97`, `1/99`...) y en Rosemount (`"Configuration
  Reference Manual"` + `"November 2024 00809-0100-4107"`).
- **Decisión: no limpiar headers/footers por ahora.** Antes de decidir se
  armó una previsualización sin costo — un script descartable (fuera del
  repo, en el scratchpad de la sesión) que chunkea 3 PDFs de muestra (uno
  por fabricante: Emerson, Endress+Hauser, Siemens) con los mismos
  `CHUNK_SIZE`/`CHUNK_STEP` de `ingest.py`, sin llamar a `embed_texts()` ni
  tocar Supabase, y vuelca chunks de muestra (primero/medio/último) a un
  archivo para inspección manual. El header/footer resultó ser 2-3 líneas
  cortas (fecha, número de doc, URL, página) contra chunks de 1000
  caracteres — dilución baja, no bloquea correr tal cual. Siemens es un
  caso aparte: no es header/footer por página sino la portada completa
  duplicada como contraportada al final del documento. Se corre el corpus
  sin limpiar y se re-evalúa con datos reales de retrieval en el paso 6 si
  hace falta, en vez de invertir de entrada en un limpiador por fabricante
  (5 formatos de header/footer distintos, no es gratis).
- `docs/langgraph-intro.txt` (los 16 chunks viejos de M4/Capa 5A) movido a
  `archive/langgraph-intro.txt` (`git mv`, registrado como rename) para que
  la ingesta real no lo mezcle con el corpus de instrumentación —
  `scripts/ingest.py` y el `InMemoryIndex` de `src/main.py` (ya sin uso
  real desde 5B.2) solo leen `docs/*.txt`, que ahora queda vacío (`docs/`
  solo tiene `pdfs/`). Sin referencias a esa ruta en `tests/`, confirmado
  antes de mover.
- **Bug encontrado y arreglado en el camino:** `embed_texts()`
  (`src/ingestion.py`) mandaba todos los textos en un solo request a la API
  de embeddings — funcionaba con los 16 chunks de Capa 5A, pero con 2451
  chunks del corpus real (~626k tokens) supera el límite de OpenAI (300k
  tokens y 2048 items por request), tirando `BadRequestError` recién
  después de gastar tiempo en el chunking. Fix: `embed_texts()` ahora
  batchea internamente de a 300 textos por request y une las respuestas —
  transparente para los callers existentes (Capa 5A sigue mandando listas
  chicas, un solo batch).
- **Ingesta real corrida contra Supabase:** `python -m scripts.ingest` →
  2451 chunks insertados desde los 11 PDFs (`TRUNCATE` de los 16 chunks
  viejos + insert batch). Verificado con `SELECT COUNT(*), COUNT(DISTINCT
  source) FROM chunks` → `(2451, 11)`.
- **Hallazgo de seguridad cerrado:** alerta automática de Supabase — la
  tabla `chunks` quedaba accesible públicamente vía la API REST
  (PostgREST) porque Row-Level Security estaba deshabilitado. La app nunca
  usó esa API (conecta directo por Postgres con `psycopg2.connect(DATABASE_URL)`,
  confirmado revisando `src/tools.py` y `scripts/ingest.py` — no hay uso de
  `supabase-py` ni de la `anon key` en el repo), pero la API REST igual
  queda expuesta por default en todo proyecto Supabase. Se corrió `ALTER
  TABLE chunks ENABLE ROW LEVEL SECURITY;` sin policies en el SQL Editor
  del dashboard — el rol de `DATABASE_URL` tiene bypass de RLS por ser el
  rol propietario, así que la app no se vio afectada; lo único que cambió
  es que el rol `anon`/`authenticated` de la API REST pública queda sin
  acceso. Verificado con `SELECT relrowsecurity FROM pg_class WHERE
  relname = 'chunks'` → `true`.
- **Próximo paso concreto:** paso 3 de 5B.4 — actualizar el system prompt
  (`graph.py`) y el README con el caso de uso real de instrumentación de
  campo. Después siguen los pasos 4-6 (ground truth con LLM,
  `evals/retrieval_metrics.py`, barrido de `k` de RRF) — ninguno arrancado
  todavía.

---

## 2026-07-13 — Capa 5B.4 (nueva): plan de corpus real + evals de M4, priorizado
**Commit:** pendiente (CORPUS_INSTRUMENTACION.MD + ROADMAP.md + CHANGELOG.md, sin commitear todavía)

- `CORPUS_INSTRUMENTACION.MD` (nuevo): plan para reemplazar el corpus actual
  (`docs/langgraph-intro.txt`, 16 chunks) por uno real — instrumentación de campo
  (transmisores de presión, caudal y temperatura) para soporte técnico de sistemas
  municipales de agua potable y saneamiento. Incluye: justificación del dominio
  (experiencia real de Juan como consultor técnico, 2 años, plantas potabilizadoras +
  redes de distribución + tratamiento cloacal para la Municipalidad de Monte Vera),
  checklist de 12 PDFs oficiales (Emerson/Rosemount, Siemens Sitrans,
  Endress+Hauser), ejemplos de consultas para ground truth, categorías nuevas de
  `create_ticket`, y notas de compliance (PDFs con copyright: uso permitido para
  desarrollo/citas con fuente, evitar comitear los originales — carpeta fuente va a
  `.gitignore`).
- Esta iniciativa resuelve directamente la decisión pospuesta en el handoff de M4
  (2026-07-11, ver entrada de abajo): portar `hit_rate`/`mrr`/`evaluate()` quedaba
  condicionado a que `docs/` creciera más allá de un solo archivo — el corpus nuevo
  es ese salto de volumen.
- **Decisión de secuencia (con Juan):** este plan pasa a ser **Capa 5B.4**, prioridad
  actual — por delante de la Capa 5B.3 (Postgres checkpointer, diseño cerrado
  2026-07-07, en pausa desde 2026-07-09) y de la Sesión 2 de limpieza (también en
  pausa). Ambas quedan sin cambios en la cola, solo se corrieron detrás de 5B.4.
- `ROADMAP.md`: agregada la sub-capa 5B.4 al mapa de capas y al plan de cierre de
  Capa 5B (nueva "Sesión 0" antes de las Sesiones 1 y 2 ya existentes), con el plan
  de 6 pasos de `CORPUS_INSTRUMENTACION.MD` resumido (sin duplicar el detalle
  completo, que vive en ese archivo). El pendiente de "soporte de PDFs reales en
  `scripts/ingest.py`" pasa de la lista de POSPUESTO a paso activo (paso 2 de 5B.4).
- **Sin código todavía** — el paso 1 (descargar los 12 PDFs) es una acción manual de
  Juan, fuera del repo.
- **Próximo paso concreto:** Juan descarga los PDFs del checklist a una carpeta
  fuente gitignored; después, extender `scripts/ingest.py` con soporte real de PDFs
  (paso 2 de 5B.4).

---

## 2026-07-11 — M4 del Zoomcamp terminado (videos + homework) + handoff post-curso
**Commit:** pendiente (ROADMAP.md + courses/POST_COURSE_ZOOMCAMP_M4.md, sin commitear todavía)

- Terminado el Módulo 4 del LLM Zoomcamp (Evaluation and Monitoring): videos vistos y
  homework (`M4-lessons/HW4 - Juan Belbey.ipynb`, Q1–Q6) resuelto — HW ya estaba
  entregado, faltaba el repaso de videos que ahora está al día.
- `courses/POST_COURSE_ZOOMCAMP_M4.md` (nuevo): handoff completo del módulo — tabla de
  respuestas confirmadas (Q1–Q6: hit rate 0.76 de `text_search`, MRR 0.55 de
  `vector_search`, mejor `k` de RRF por MRR fue 1), conceptos clave (ground truth
  generado con LLM + structured output, Hit Rate, MRR, evaluación por filename no por
  chunk, tuning de `k` por medición), y auditoría contra el código real del repo:
  - No existe todavía ningún framework de Hit Rate/MRR en `evals/` — `golden_set.json`
    mide calidad de respuesta del agente (LLM-as-judge), no si `rag_search()` recupera
    el chunk correcto.
  - El `k=60` de `rrf()` (`src/ingestion.py:104`, heredado de 5A.2) nunca se midió
    contra un ground truth real — quedó en el default del paper sin verificar si es
    el óptimo para el corpus del repo.
  - **Decisión tomada:** portar el framework de M4 (ground truth por LLM +
    `hit_rate`/`mrr`/`evaluate()` + barrido de `k`) queda pospuesto hasta que
    `docs/` deje de tener un solo archivo (`langgraph-intro.txt`, 16 chunks) — bajo
    corpus, bajo retorno de construir el framework ahora. Ligado al pendiente ya
    anotado de soporte de PDFs reales en `scripts/ingest.py`.
- `ROADMAP.md`: actualizado el estado de M4 (terminado, no "pendiente de repaso"),
  y corregida una inconsistencia encontrada al revisar el plan de cierre de Capa 5B:
  el plan del 2026-07-06 asumía "Sesión 2 de limpieza → recién ahí arrancar M4", pero
  en la práctica M4 se cursó en paralelo sin esperar esa secuencia. Se dejó una nota
  aclarando el desvío en vez de reescribir el plan como si hubiera pasado como estaba
  previsto.
- **Próximo paso concreto:** Juan hace un esquema de M4 en cuaderno (papel), después
  empieza a portar al repo los contenidos aprendidos — con la salvedad de que los
  patrones concretos (hit_rate/mrr, tuning de `k`) ya quedaron pospuestos en el propio
  handoff hasta que el corpus crezca. La Sesión 2 de limpieza (paso 6, tracing real,
  `tool_calls_used`, `max_tokens`, `SYSTEM_PROMPT`) y la Capa 5B.3 (Postgres
  checkpointer) siguen en pausa, sin cambios, en la misma cola que ya estaba definida.

---

## 2026-07-07 — Capa 5B.3 arranca: diseño del Postgres checkpointer (sin código todavía)
**Commit:** `cd2d5f9` (solo el commit pendiente de 5B.2, ver entrada de abajo — 5B.3 en sí no tiene código)

- Sesión de diseño para Capa 5B.3 (`MemorySaver` → `PostgresSaver`), sin escribir código todavía. Decisiones tomadas, a implementar la próxima sesión:
  - **Conexión persistente, no por-request:** a diferencia de `rag_search()` (que abre/cierra conexión una vez por consulta del usuario), el checkpointer se invoca en cada transición de nodo del grafo (`agent → tools → agent`), potencialmente varias veces por un solo `/chat`. Abrir/cerrar en cada paso sería mucho más caro — la conexión tiene que vivir durante todo el ciclo de vida de la app.
  - **`graph.py` deja de compilar el grafo él mismo:** hoy `graph = graph_builder.compile(checkpointer=MemorySaver())` corre al importar el módulo, antes de que exista el `lifespan` de `main.py`. Como `PostgresSaver` necesita una conexión real, compilar a nivel de módulo dejaría de ser viable (I/O como efecto secundario de un `import`). Plan: `graph.py` exporta `graph_builder` sin compilar; quien lo importe decide con qué checkpointer compilarlo.
  - **Tres consumidores de `graph` a día de hoy** (`src/main.py`, `tests/conftest.py`, `evals/run_evals.py`) — cada uno va a compilar distinto: `main.py` con `PostgresSaver` (conexión real), `conftest.py`/`run_evals.py` con `MemorySaver()` para no acoplar tests/evals a que Supabase esté arriba.
  - **Patrón de producción para la conexión:** no una conexión cruda, sino un `psycopg_pool.ConnectionPool` abierto en el `lifespan` (startup) y cerrado al shutdown. Razón: los endpoints `def` (sync) de FastAPI corren en un threadpool, así que pueden llegar varios `/chat` concurrentes — una sola conexión compartida entre threads no es segura.
  - **Dependencia nueva:** `langgraph-checkpoint-postgres` (paquete oficial de LangChain para `PostgresSaver`) — trae `psycopg` (v3), no `psycopg2` (el que ya usa `tools.py`). Se acepta la convivencia de dos drivers de Postgres en el repo a propósito — migrar `tools.py` a psycopg3 sería scope creep sin necesidad real.
  - `PostgresSaver` necesita `.setup()` una vez para crear sus tablas propias en Postgres — idempotente, se puede llamar en cada arranque del `lifespan` sin problema.
- **Nada instalado ni codeado todavía** — queda pendiente de confirmación con Juan antes de instalar `langgraph-checkpoint-postgres` y empezar a tocar archivos.
- **Próximo paso concreto:** instalar `langgraph-checkpoint-postgres`, después implementar en orden: `graph.py` (exportar `graph_builder`), `main.py` (pool + `PostgresSaver` + `.setup()` en el `lifespan`), `tests/conftest.py` y `evals/run_evals.py` (compilar con `MemorySaver()`).

---

## 2026-07-04 — Capa 5B.2 completa: rag_search() migrado a Postgres
**Commit:** `cd2d5f9` (commiteado el 2026-07-07, tres días después de escrito)

- `src/tools.py`: pasos 4 y 5 del plan, últimos de 5B.2:
  - `_hybrid_search(conn, query, query_embedding, top_k, candidate_k=10)` — pide `candidate_k=10` candidatos a `_vector_search`/`_keyword_search`, fusiona con `rrf()` de `ingestion.py` (sin cambios, ya era agnóstica al origen del id), corta a `top_k`. Mismo patrón de "candidatos más anchos que el resultado final" que el `InMemoryIndex.hybrid_search()` de 5A.2.
  - `rag_search()` reescrito por completo: abre conexión con `_get_connection()` dentro de un `try/finally` (garantiza `conn.close()` incluso si algo falla a mitad de camino, sin tragarse la excepción), embebe la query con `embed_texts([query])[0]`, llama `_hybrid_search()`, trae `content`/`source` con `SELECT ... WHERE id = ANY(ids)`, y reordena el resultado con un diccionario `{id: (content, source)}` recorriendo `fused` (no las filas de Postgres, que vuelven en su propio orden y no en el de relevancia de RRF).
  - `_index`/`InMemoryIndex`/`set_index()` quedan sin uso real — `rag_search()` ya no los toca. Limpieza pospuesta a un paso 6 aparte (ver abajo).
- **Verificado contra infraestructura real:** `rag_search.invoke({"query": "que es langgraph", "top_k": 3})` contra Supabase trajo los 3 chunks correctos de `langgraph-intro.txt` con scores de RRF coherentes (~0.033 para el resultado en ambas listas). Los 7 tests de `tests/test_rules.py` pasan sin modificar nada — el contrato de `rag_search()` (string JSON, contiene palabras de la query) se mantuvo intacto aunque cambió todo el motor de búsqueda por debajo.
- Repaso de conceptos de la sesión: orden lógico de evaluación SQL (`WHERE`/`HAVING` se evalúan antes que `SELECT`, por eso ninguno de los dos puede usar alias del `SELECT` — corregí una premisa mía equivocada sobre `HAVING` a mitad de la explicación, confirmado con la doc de Postgres), qué hace realmente `to_tsvector`/`plainto_tsquery` (normalizar texto a raíces de palabras sin stopwords) y por qué embeber la query en cada request no se puede cachear igual que los chunks (la tabla `chunks` es el corpus fijo que se reutiliza siempre; la query es la sonda, casi nunca se repite, y guardarla en la misma tabla contaminaría las búsquedas futuras), `try/finally` vs `try/except` para garantizar cierre de conexión sin tragarse errores.
- **Próximo paso concreto:** Capa 5B.3 — Postgres checkpointer. Aparte, pendiente el paso 6 (sesión separada): sacar `build_index()`/`set_index()` del lifespan de `main.py` (re-embebe docs en cada arranque de uvicorn para un índice que ya no se usa) y decidir si se borra `InMemoryIndex` del todo.

---

## 2026-07-03 — Capa 5B.2: pasos 1-3/5 (conexión Postgres + queries SQL)
**Commit:** `2a5657f`

- `src/tools.py`: tres funciones privadas nuevas, primer código real de 5B.2:
  - `_get_connection()` — `psycopg2.connect(DATABASE_URL)` + `register_vector(conn)`, conexión nueva por llamada (sin pool, decisión tomada en la sesión anterior)
  - `_vector_search(conn, query_embedding, top_k)` — `SELECT id, embedding <=> %s AS distance ... ORDER BY distance LIMIT %s`, devuelve `[(chunk_id, distance), ...]`
  - `_keyword_search(conn, query, top_k)` — Postgres FTS (`to_tsvector('spanish', ...)` / `plainto_tsquery` / `ts_rank`), devuelve `[(chunk_id, rank), ...]`
  - Ninguna está conectada todavía a `rag_search()`, que sigue usando `_index` (InMemoryIndex) sin cambios — por eso Pylance marca las tres como "not accessed", esperado hasta el paso 5.
- `scripts/ingest.py`: comentario de `register_vector` ampliado para explicar que traduce el tipo `vector` en los dos sentidos (Python→Postgres al insertar, Postgres→Python al mandar el embedding de la query como parámetro en `_vector_search`).
- Repaso de conceptos de la sesión: pool de conexiones vs. conexión por request (por qué el `InMemoryIndex` sí puede ser global/compartido y una conexión a Postgres no — dato inmutable vs. estado de conversación), TCP vs HTTP, sockets, el operador `<=>` de pgvector, parametrización con `%s` y por qué previene SQL injection, orden lógico de evaluación de SQL (`WHERE` se evalúa antes que `SELECT`, por qué `plainto_tsquery` se repite en la query de FTS).
- **Housekeeping:** `.claude/skills/actualizar-roadmap-changelog.skill` estaba como ZIP sin extraer (Claude Code no lo reconocía como skill). Se extrajo a `.claude/skills/actualizar-roadmap-changelog/SKILL.md` y se borró el zip original.
- **Inconsistencia encontrada y corregida en ROADMAP.md:** la línea de `tools.py` en "Estado actual del repo" todavía decía "cosine similarity real" sin mencionar el hybrid search (TF-IDF + RRF) agregado en 5A.2 — quedó desactualizada desde esa sesión (2026-07-01).
- **Próximo paso concreto:** paso 4 de 5B.2 — fusionar `_vector_search()` + `_keyword_search()` con `rrf()`. Después, paso 5: reemplazar `_index.hybrid_search()` dentro de `rag_search()`, resolviendo cómo traer `content`/`source` para cada `id` ganador del RRF.

---

## 2026-07-02 — Repaso 5B.0/5B.1 + commit + arranque de 5B.2 (sin código todavía)
**Commit:** `834e71a`

- Repaso de active recall de las tres preguntas pendientes de la sesión anterior (HNSW vs IVFFlat/B-tree, por qué separar ingesta de serving, por qué TRUNCATE) — las tres cerradas y entendidas.
- `scripts/ingest.py`: se agregaron comentarios en primera persona sobre cada función y paso del flujo, a pedido de Juan, para reforzar la comprensión.
- **Hallazgo de seguridad:** `.env` estaba trackeado en git desde el commit `0e97122` (antes de existir `.gitignore`), a pesar de que `.gitignore` ya lo excluye. Con el `DATABASE_URL` nuevo a punto de commitearse, eso hubiera expuesto la password real de Supabase en el historial de GitHub. Se corrigió con `git rm --cached .env` en este mismo commit — `.env` sigue en disco, pero deja de versionarse desde ahora.
- **Pendiente sin resolver (no bloquea 5B.2):** las credenciales reales (`OPENAI_API_KEY`, `DATABASE_URL`) siguen visibles en commits viejos del historial de git. Falta (a) rotar esas keys y (b) limpiar el historial (`git filter-repo` o similar) antes de publicar el repo.
- **5B.2 arrancó pero sin código:** se definió el plan de 5 pasos (ver ROADMAP.md) y se tomó la primera decisión — `rag_search()` va a abrir/cerrar una conexión psycopg2 nueva en cada llamada (igual que `scripts/ingest.py`), sin connection pool todavía. El pool queda anotado como mejora de rendimiento para más adelante, una vez que la versión simple ande.
- **Próximo paso concreto (para la próxima sesión):** implementar la pieza 1 — la conexión a Postgres dentro de `rag_search()` (o un helper nuevo), reemplazando el uso de `_index` para esa parte. Después seguir con la query de vector search (paso 2 del plan).

---

## 2026-07-01 — Capa 5B.0 + 5B.1: infraestructura Supabase + script de ingesta
**Commit:** `834e71a` (commiteado el 2026-07-02, un día después de escrito)

- **5B.0 (infra Supabase):** proyecto Supabase creado, extensión `vector` habilitada, tabla `chunks` (`id`, `content text`, `source text`, `chunk_index int`, `embedding vector(1536)`) + índice `hnsw` (`vector_cosine_ops`). Conexión verificada con `psycopg2` usando `DATABASE_URL` (Session pooler, usuario `postgres.<project-ref>`)
- `.env.example`: agrega `DATABASE_URL` (además, se corrigió que el archivo estaba guardado en UTF-16 en vez de UTF-8 — se leía corrupto)
- `requirements.txt`: agrega `psycopg2-binary==2.9.11` y `pgvector==0.4.1`
- **5B.1 (script de ingesta):** `scripts/ingest.py` (nuevo) — lee `docs/*.txt`, reutiliza `chunk_text`/`embed_texts` de `src/ingestion.py`, hace `TRUNCATE` + insert batch (`execute_values`) en la tabla `chunks`. Se corre a mano (`python -m scripts.ingest`), no en el lifespan de `main.py` — ingesta y serving quedan separados a propósito
- **Verificado:** 16 chunks insertados desde `langgraph-intro.txt` con `chunk_index` correcto por documento
- `rag_search()` **no cambió** — sigue usando el `InMemoryIndex` de 5A.2. La tabla de Supabase está poblada pero todavía no la consulta nadie (eso es 5B.2)
- `ROADMAP.md` actualizado: 5B.0 y 5B.1 marcadas completas, próximo paso es 5B.2

**Nota de proceso (para retomar mañana):** esta sesión avanzó dos sub-capas seguidas (5B.0 y 5B.1) sin pausar entre piezas para preguntas de comprensión — más rápido de lo que pide el estilo de trabajo acordado (AGENTS.md / COPILOT_STRATEGY.md: ir de a poco, explicar, pregunta de active recall, esperar respuesta). Mañana conviene repasar ambas piezas con calma antes de seguir a 5B.2:
- ¿Por qué HNSW en vez de IVFFlat, y qué hace distinto de un índice normal de Postgres (B-tree)?
- ¿Por qué separar el script de ingesta del lifespan de `main.py` en vez de reconstruir todo en cada arranque?
- ¿Por qué `TRUNCATE` antes de insertar, y qué pasaría si se corriera el script sin el truncate?

**Pendiente futuro (no bloquea 5B):** sumar soporte de PDFs reales en la ingesta antes de publicar el repo — la tabla ya es agnóstica a la fuente, solo falta extracción de texto (pypdf/pdfplumber) en `scripts/ingest.py`.

---

## 2026-06-20 — Capa 5A completa: RAG en memoria con embeddings y cosine similarity
**Commit:** `feat: Capa 5A`

- `src/ingestion.py` (nuevo): pipeline completo — chunking con ventana deslizante, embeddings con `text-embedding-3-small`, `InMemoryIndex` con numpy
- `src/tools.py`: `rag_search()` reemplaza stub por cosine similarity real sobre el índice; devuelve lista de `RAGResult` con scores reales
- `src/main.py`: `lifespan` construye el índice al arrancar leyendo `docs/*.txt`; reemplaza `@app.on_event` deprecado
- `docs/langgraph-intro.txt` (nuevo): base de conocimiento inicial sobre LangGraph, alineada con el golden_set
- `requirements.txt`: agrega `numpy==2.4.6` y `langsmith==0.7.37`
- `ROADMAP.md`, `CHANGELOG.md`, `STACK.md`: documentación actualizada

**Verificado:** endpoint `/chat` llama `rag_search()` de forma real (confirmado con print temporal en uvicorn)

**Deuda técnica pendiente:**
- `test_rag_search_contains_query_word` pasa por razones equivocadas (índice vacío en tests)
- `ChatResponse.tool_calls_used` siempre devuelve `[]` — no se popula todavía

---

## 2026-06-07 — Capa 4 completa: schemas Pydantic
**Commit:** `f552cfd`

- Nuevo `src/schemas.py` con los 4 modelos del sistema:
  - `ChatRequest` / `ChatResponse` — contrato del endpoint `/chat`
  - `TicketInput` — args_schema que LangChain usa para describir `create_ticket()` al LLM
  - `RAGResult` — contrato de salida de `rag_search()`, listo para Capa 5
- `src/main.py` — endpoint `/chat` tipado: recibe `ChatRequest`, devuelve `ChatResponse`
- `src/tools.py` — `create_ticket` con `args_schema=TicketInput`; `rag_search` serializa `RAGResult`
- `pytest.ini` — configuración de pytest centralizada

---

## 2026-06-03 — Baseline evals registrado
**Commit:** `0e97122`

- Primera corrida de evals guardada en `evals/results/2026-06-03/`
- Métricas de baseline: relevance 5.0/5, citation 5%, convergence 3.7 pasos promedio
- Referencia para comparar cuando `rag_search()` sea real en Capa 5

---

## 2026-06-02 — Capa 3B completa: observabilidad con LangSmith
**Commit:** `1d2bd23`

- `evals/evaluators.py` — `relevance_evaluator` decorado con `@traceable` (opt-in: solo si hay `LANGCHAIN_API_KEY`)
- `evals/run_evals.py` — scores enviados a LangSmith con `client.create_feedback()`
- `evals/golden_set.json` — 20 preguntas sobre LangGraph docs con `expected_answer` y `category`
- `.github/workflows/ci.yml` — `LANGCHAIN_API_KEY` como secret de CI
- `.env.example` actualizado con placeholders de LangSmith
- Regla activa: si no hay API key, LangSmith se desactiva silenciosamente

---

## 2026-05-12 — CI: reporte HTML de tests
**Commit:** `72d8b1d`

- `ci.yml` — job de rules genera reporte HTML con `pytest-html` y lo sube como artefacto
- `requirements.txt` — agrega `pytest-html`
- `.gitignore` — ignora `tests/reports/` (reportes locales no van al repo)

---

## 2026-05-11 — Capa 2 completa: CI con GitHub Actions
**Commit:** `8559383`

- `.github/workflows/ci.yml` — pipeline con dos jobs:
  - `rules`: corre en cada push (determinista, sin API, ~0.05s)
  - `evals`: corre solo en `main` con `MAX_EVAL_CASES=1` (con API key)
- `requirements.txt` reemplazado por dependencias limpias y mínimas

---

## 2026-05-10 — Tests de evaluación (LLM-as-judge)
**Commit:** `1c52e06`

- `tests/test_evals.py` — evaluaciones con LLM-as-judge:
  - `TestRelevanceEval`: relevance score ≥ 3/5 para respuestas de RAG y ticket
  - `TestTraceEval`: convergence (≥ 2 pasos en traza)

---

## 2026-05-09 — Tests deterministas
**Commit:** `e4bfa36`

- `tests/test_rules.py` — 4 tests sin LLM ni API:
  - `TestResponseFormat`: respuestas no vacías, bajo 1000 chars
  - `TestToolBehavior`: `rag_search` y `create_ticket` devuelven strings con el input

---

## 2026-05-08 — Fixtures compartidos de tests
**Commit:** `5674b7a`

- `tests/conftest.py` — fixtures de sesión:
  - `agent_graph`: grafo compilado reutilizable
  - `sample_responses`: ejemplos válidos/inválidos para reglas
  - `invoke_agent`: helper con skip automático si no hay `OPENAI_API_KEY`

---

## 2026-05-04 — Capa 1 completa: FastAPI + validación de config
**Commit:** `f6f5ca8`

- `src/config.py` — `load_settings()` valida `OPENAI_API_KEY` al startup (fail fast)
- `src/main.py` — endpoint `POST /chat` con `thread_id` para persistencia por conversación

---

## 2026-05-01 — Herramientas y grafo del agente
**Commit:** `7f158da`

- `src/tools.py` — stubs `rag_search()` y `create_ticket()` con `@tool`
- `src/graph.py` — `StateGraph` con routing condicional:
  - `agent_node` → `route_after_agent` → `tools` (si hay tool_calls) o `END`
  - Compilado con `MemorySaver` para persistencia en memoria

---

## 2026-04-29 — Estado del agente
**Commit:** `724eff4`

- `src/state.py` — `AgentState` con `TypedDict` + `add_messages` (reducer de LangGraph)

---

## 2026-04-28 — Estructura inicial del repo
**Commits:** `65d1bc2`, `4807156`

- Estructura de carpetas: `src/`, `tests/`, `evals/`
- `.gitignore` inicial
