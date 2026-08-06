# CHANGELOG
# agentic-rag-fastapi

Registro cronológico de cambios. Cada entrada corresponde a uno o más commits.
Formato: fecha · tipo · descripción · qué capa representa.

---

## 2026-08-05 — Force-push del historial (cierra punto 7) + RAGAS completo (stretch #1)
**Commits:** `e885f2d` (docs — cierre de la entrada 2026-08-04, ya pusheado junto con el
force-push de abajo). Todo lo de código de hoy (`requirements.txt`, `evals/ragas_eval.py`)
sigue sin commitear — sesión corrida entera dentro de la ventana 9-18hs ARG lun-vie.

- **Cierra el punto 7 del plan de entrega:** `git push origin --force --all` ejecutado
  (confirmación explícita de Juan inmediatamente antes, dado lo irreversible del lado
  GitHub). Verificado con `git fetch` + `git log origin/main`: el remoto ya tiene el
  historial reescrito del 2026-08-04 (sin `.env`), `HEAD` en `e885f2d`. Solo falta que
  Juan pase el repo de privado a público, a su criterio, sin fecha fija.
- **Stretch #1 (RAGAS) completado — con un hallazgo real que contradice lo "verificado"
  el 2026-08-04:** al instalar `ragas==0.4.3` en el venv real del proyecto (no en el venv
  aislado usado para el test de compatibilidad), `import ragas` falló de entrada —
  `ragas/llms/base.py` importa sin condición `langchain_community.chat_models.vertexai.
  ChatVertexAI`, módulo que la última `langchain-community` (`0.4.2`, no pineada por
  `ragas`) ya no tiene. El test aislado del 04/08 no lo detectó, probablemente porque
  resolvió una versión distinta de `langchain-community` en ese momento. Investigado
  descargando wheels de varias versiones sin instalar (`pip download --no-deps`) para
  ubicar dónde se sacó el módulo: sigue presente en `0.4.1`, que además solo pide
  `langchain-core>=1.0.1` (compatible con el resto del stack). Fix aplicado a
  `requirements.txt`: `langchain-community==0.4.1` pineado explícito (con comentario del
  porqué) + `langchain-core` subido de `1.3.2` a `1.5.3` (piso real que exige
  `langchain-classic`, dependencia transitiva de `langchain-community`, no elección
  propia). `pip check` limpio, `pytest tests/test_rules.py` 7/7 en verde con las
  versiones nuevas.
- **`evals/ragas_eval.py` nuevo** — diseño ya acordado el 04/08 (`ragas.metrics.collections`:
  `Faithfulness`/`AnswerRelevancy`/`ContextPrecision`/`ContextRecall`; `contexts` tomados
  del `ToolMessage` real de la tool call a `rag_search` en la traza, no de
  `_hybrid_search()` aparte; juez `gpt-4o-mini` vía `llm_factory` + `OpenAIEmbeddings`
  default `text-embedding-3-small`, igual que `src/ingestion.py`). Tres bugs reales
  encontrados y arreglados corriendo el script de punta a punta (no solo leyendo la API):
  1. El `.score()` sync de cada métrica llama internamente a `agenerate()`, que exige un
     cliente async — con `OpenAI()` normal tira `TypeError: Cannot use agenerate() with a
     synchronous client`. Fix: `AsyncOpenAI()`.
  2. Sin `max_tokens` explícito, la salida estructurada de `faithfulness` se truncó a
     mitad de camino en la primera corrida completa
     (`instructor.v2.core.errors.IncompleteOutputException`). Fix: `max_tokens=2048` en
     `llm_factory`.
  3. El primer `try/except` de `evaluate_case()` solo envolvía el scoring de RAGAS, no el
     `invoke_agent()` del agente — un `psycopg2.OperationalError: server closed the
     connection unexpectedly` real (Postgres/Supabase, transitorio) a mitad de una tool
     call tiró abajo la corrida completa por segunda vez, mismo patrón de riesgo que dejó
     `compare_temperature.py` a medio terminar el 2026-08-01 (una corrida larga sin aislar
     el punto de falla pierde todo el trabajo previo, no solo el caso que falló). Fix:
     `try/except` ampliado a todo el cuerpo de `evaluate_case()`.
  - **Corrida real completa (48 casos de `golden_set.json` con `expected_answer`,
    `direct_answer_mini` en producción):** 46/48 puntuados (2 sin contexts recuperados —
    `g026`/`g039`, `rag_search` no devolvió resultados para esas preguntas; hallazgo de
    retrieval, no bug del script). **faithfulness 0.783, answer_relevancy 0.708,
    context_precision 0.571, context_recall 0.679** —
    `evals/results/2026-08-05/11-46-58_ragas.json`.
- De paso, creada (fuera de este repo) la skill de usuario `esquema-de-tarea` en
  `~/.claude/skills/` — tooling personal de Claude Code, no forma parte del código de
  `agentic-rag-fastapi`.
- **Próximo paso concreto:** pasar el repo a público en GitHub (Juan, sin fecha fija).
  Commitear `requirements.txt` + `evals/ragas_eval.py` + esta entrada de CHANGELOG fuera
  de la ventana 9-18hs. Si queda margen antes del 10/08, seguir con el stretch #2
  (Streamlit) según el timeline del 2026-08-01.
- Sesión cerrada acá por hoy, a pedido de Juan — sin commits (regla de horario).

---

## 2026-08-04 — Cierra el punto 5 (commit) + limpieza del historial de git (punto 7, local) + arranca RAGAS
**Commits:** `2eed98a` (query rewriting del punto 5, pusheado — hash reescrito a `d47031b`
por la limpieza de historial de más abajo) + resto de esta entrada sin commitear, ver
"Próximo paso concreto"

- **Arranca el punto 7 del plan de entrega:** sacar `.env` del historial de git. Quedó
  trackeado desde el commit inicial (`65d1bc2`, 28/04) hasta que se sacó del tracking en
  `834e71a` (02/07) — credenciales reales (`OPENAI_API_KEY`, `DATABASE_URL` de Supabase)
  visibles en esos commits viejos. Ya rotadas desde el 2026-07-28 (ver entrada de ese día),
  así que esto es higiene antes de pasar el repo a público para el peer review del curso,
  no una emergencia de credencial viva.
- **Backup previo:** `git bundle create --all` del estado íntegro del repo antes de tocar
  nada (43 commits, `HEAD` en `2eed98a`), guardado fuera del repo
  (`projects/agentic-rag-fastapi-backup-2026-08-04.bundle`) y verificado con
  `git bundle verify`. En el camino apareció un error propio: un primer intento con
  `git -C agentic-rag-fastapi bundle create <ruta relativa>` resolvió la ruta relativa
  *adentro* del repo en vez de al lado — quedó una copia duplicada del bundle sin
  trackear dentro del working tree (se hubiera colado en un commit con un `git add -A`
  descuidado, re-metiendo el historial viejo con `.env` adentro de un blob del historial
  nuevo). Detectado con `git status`/`diff -rq` contra un clon de prueba y borrado antes
  de comitear nada.
- **Ensayo primero, no directo sobre el repo real:** clonado el bundle a una carpeta
  descartable, corrido ahí `git-filter-repo --path .env --invert-paths --force`
  (`git-filter-repo` instalado vía pip, no viene con git). Reescribió los 43 commits
  (esperable — el primero afectado es el commit inicial, así que cualquier hijo cambia
  de hash) en ~1.3s. Verificado en la copia de prueba: `.env` ya no aparece en
  `git log --all --full-history`, y el contenido trackeado es idéntico al repo real
  (diff completo, ignorando fin de línea CRLF/LF) — las únicas diferencias son los
  archivos ya gitignored de siempre (`.env`, `docs/pdfs`, `reports/`,
  `evals/results` viejos).
- **Aplicado al repo real (local):** mismo comando sobre el working directory real.
  `git-filter-repo` saca el remote `origin` por seguridad — re-agregado a mano después.
  Verificado de nuevo ahí: `.env` fuera del historial, `git status` limpio,
  `pytest tests/test_rules.py` → **7/7 en verde** con el historial reescrito.
- **Repaso a fondo antes del push** (pedido explícito de Juan, sin apurar el force-push):
  reflog local vacío y repo sin objetos sueltos (`git count-objects -v` → todo empacado
  en 1 pack, `garbage: 0`) — `git-filter-repo` ya había limpiado los restos del historial
  viejo. Escaneo de **todo** el historial reescrito (no solo por nombre de archivo, por
  contenido) buscando patrones de credenciales reales (`sk-...`, `AKIA...`, connection
  strings de Postgres con user:pass, claves privadas) → nada encontrado. Confirmado que
  ningún otro nombre de archivo tipo `.env` existió nunca en el historial salvo
  `.env.example` (solo placeholders). `origin/main` confirmado todavía en el historial
  viejo (`2eed98a`) — nada tocó GitHub todavía, el force-push sigue siendo el único paso
  pendiente.
- **Sin pushear:** son las 09:09 ART (martes) al terminar la reescritura — cae dentro de
  la ventana 9-18hs lun-vie que no debe quedar como timestamp de push en este repo. El
  repo local ya está listo; falta el `git push origin --force --all` (irreversible en
  GitHub, requiere confirmación puntual de Juan inmediatamente antes) y, después,
  pasar el repo de privado a público.
- **Arrancado el stretch #1 (RAGAS), mientras se espera la ventana de horario para el
  push** — condicional a que el core (puntos 1-7) cierre con margen, confirmado con
  Juan que el punto 7 ya está resuelto salvo el push, así que hay lugar:
  - Concepto explicado con active recall antes de instalar nada: las 4 métricas de
    RAGAS (`faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`)
    y su relación con `evals/evaluators.py` ya existente — `answer_relevancy` es
    reference-free como `relevance_evaluator`; `context_recall` es la que sí necesita
    `ground_truth` (no `context_precision`, que tiene variante reference-free),
    equivalente a `accuracy_evaluator`.
  - **Compatibilidad de versiones verificada** (el riesgo que ya estaba anotado en
    POSPUESTO desde el 18/07): `ragas==0.4.3` instala e importa sin conflicto junto a
    `langchain==1.2.15`/`langchain-core==1.3.2`/`langchain-openai==1.2.1`/
    `openai==2.33.0`, probado en un venv aislado (no se tocó `requirements.txt` ni el
    `.venv` del proyecto). Único hallazgo: el import `from ragas.metrics import ...`
    está deprecado a favor de `ragas.metrics.collections` — se usa la ruta nueva al
    escribir el script, y se pinea `ragas==0.4.3` en `requirements.txt` cuando se
    integre (mismo patrón que el resto de las dependencias — la deprecación es
    justamente la razón para pinear, no para dejar sin fijar).
  - **Decisión de diseño de `contexts`:** se toman de una corrida real del agente
    (capturando el output de la tool call `rag_search` vía
    `run_evals.py`/`build_eval_graph`), no de una llamada directa a `_hybrid_search()`
    — más fiel a qué contexto tuvo el LLM al generar cada respuesta, evita juzgar
    `faithfulness` contra chunks que el agente ni vio. `ground_truth` = `expected_answer`
    de los 48 casos de `evals/golden_set.json` que lo tienen (quedan afuera los 8 de
    escalamiento, que usan `expected_tool`).
  - Sin código escrito todavía — el venv de prueba no toca el repo real.
- **Próximo paso concreto:** fuera de la ventana horaria (después de las 18hs de hoy o
  el fin de semana) — force-push, confirmar CI en verde con el historial nuevo, pasar
  el repo a público, y comitear esta misma entrada de CHANGELOG (aclarando que los
  hashes citados en entradas anteriores a esta fecha ya no son resolubles en GitHub).
  En paralelo o después: escribir `evals/ragas_eval.py` con el diseño ya acordado.
- Sesión cerrada acá por hoy, a pedido de Juan.

---

## 2026-08-03 — Aplica la decisión final del punto 4 + implementa query rewriting (punto 5)
**Commits:** `8fabcf6` (aplica la decisión final — prompt `direct_answer` + `temperature=0.3`
en `src/graph.py` — junto con el resto del punto 4 que venía sin commitear desde el
2026-08-01) + query rewriting (`src/tools.py`, `prompts/query_rewrite.txt`), commiteado
el 2026-08-04 como `2eed98a` (ver entrada de ese día).

- **Punto 4 cerrado del todo:** `graph_builder = build_graph()` en `src/graph.py` ya no usa
  los defaults viejos — `TEMPERATURE = 0.3` (constante nueva, mismo patrón que `MODEL_NAME`)
  y `SYSTEM_PROMPT = load_prompt("system_prompt_direct_answer.txt")` (antes
  `system_prompt.txt`). `pytest tests/test_rules.py` verificado en verde (7/7) antes de
  commitear. Commit `8fabcf6` agrupa esto con el resto del trabajo del punto 4 que venía sin
  commitear (framework de comparación, evals corridos, `README.md`) — pusheado a
  `origin/main`.
- **Punto 5 (query rewriting, best practice de RAG) implementado y validado con datos
  reales:**
  - Concepto: reescribir la query de búsqueda con un LLM antes de buscar, para alinear
    vocabulario — distinto de multi-query/RAG-fusion (que genera *N* variantes y fusiona
    resultados); acá se reemplaza con **una sola** query reescrita.
  - Decisión de diseño: el rewrite se aplica **solo** a `_keyword_search` (matching léxico
    exacto, vulnerable a la brecha ES/EN del corpus bilingüe) — **no** a `_vector_search`
    (el embedding ya es multilingüe, una pregunta en español y su traducción caen cerca en
    el espacio semántico).
  - `_rewrite_query_impl()` nueva en `src/tools.py`: llama a `gpt-4o-mini` con
    `temperature=0` (tarea mecánica, no creativa) + prompt nuevo
    (`prompts/query_rewrite.txt`, traduce vocabulario técnico a inglés sin tocar nombres de
    marca/modelo). Mismo patrón `@traceable` opcional (gateado por `LANGCHAIN_API_KEY`) que
    `_vector_search`/`_keyword_search` — span `agent.rag_search.rewrite`. Cliente de OpenAI
    lazy-init (`_get_client()`), mismo patrón que `src/ingestion.py`.
  - **Ubicación importante:** el rewrite vive dentro de `_keyword_search_impl`, no en
    `_hybrid_search` — el primer intento lo puso ahí, pero `evals/retrieval_metrics.py` mide
    la fila "keyword" llamando a `_keyword_search` *directo* (sin pasar por hybrid), así que
    esa fila no se hubiera enterado del cambio. Puesto en `_keyword_search_impl`, cualquier
    llamador se beneficia por igual (medición standalone y producción vía `_hybrid_search`).
  - `_rewrite_query_impl` decorada con `@lru_cache(maxsize=1024)`: es determinística
    (`temperature=0`, misma query → mismo resultado), y sin cache cada pasada de
    `evals/retrieval_metrics.py` que toca keyword search reescribiría las mismas 520
    preguntas de nuevo (7 de las 8 pasadas del script tocan keyword).
  - `load_prompt`/`PROMPTS_DIR` duplicados localmente en `tools.py` (no importados desde
    `graph.py`) para evitar un import circular — `graph.py` ya importa `TOOLS` desde
    `tools.py`.
- **Validación real** (corrida ad hoc sobre vector/keyword/hybrid, sin re-correr el barrido
  de `k` de RRF — ya cerrado en 5B.4 con `k=1`, y `rrf()` fusiona solo por posición de
  ranking, no le importa el texto de la query, así que no hay razón para esperar que el `k`
  óptimo cambie):

  | Método | hit_rate antes → después | mrr antes → después |
  |---|---|---|
  | vector | 0.231 → 0.2308 | 0.141 → 0.1413 |
  | keyword | 0.300 → **0.3288** | 0.197 → **0.2368** |
  | hybrid | 0.317 → **0.4154** | 0.186 → **0.2197** |

  Vector sin cambios (esperable, no lo toca el rewrite). Keyword mejora en ambas métricas
  (+9.6% hit_rate, +20% mrr) — se achica la brecha ES/EN, el objetivo original. Hybrid (el
  que usa `rag_search()` en producción) tiene el salto más grande: **hit_rate +31%** (0.317
  → 0.4154), mrr +18% — mejora sustancial y medible, no marginal, sobre las 520 preguntas
  completas de `evals/ground_truth_retrieval.json`.
- **Punto 6 (reproducibility, nota de copyright del dataset) revisado, sin cambios:**
  confirmado que ya estaba completo desde el 2026-08-01 (`README.md` líneas 22/30/69 +
  `CORPUS_INSTRUMENTACION.MD`, sección "Compliance — qué sí y qué no", con cita explícita
  de los Términos de Uso de Emerson) — no hacía falta agregar nada nuevo.
- **Pendiente:** commitear `src/tools.py` + `prompts/query_rewrite.txt` (implementación de
  query rewriting, todavía sin commit). Seguir con el punto 7 (limpieza de historial de git
  + repo público).

---

## 2026-08-01 (noche) — Cierra el punto 4 (decisión final modelo/prompt/temperatura) y el punto 6 (reproducibility)
**Commits:** pendiente (todo el trabajo de esta sesión sigue sin commitear — se junta con el
resto del punto 4 al aplicar la decisión final a producción, ver "Próximo paso concreto")

- **Extendido el golden set con casos de escalamiento reales:** 8 preguntas hand-crafted nuevas
  (`g049`-`g056`, `evals/golden_set.json` 48→56) que fuerzan `create_ticket` — 2 por cada
  categoría de `TicketInput` (`field_instrument_failure`, `biological_process_anomaly`,
  `pump_maintenance`, `undocumented_query`). Motivación: la comparación de modelos/prompts de la
  entrada anterior solo medía accuracy en preguntas *contestables*, dejando sin testear la
  decisión de mayor riesgo del dominio — escalar en vez de inventar cuando la consulta cae fuera
  del corpus.
  - `evals/evaluators.py`: `tool_call_evaluator(trace, expected_tool)` nuevo — code-based (no
    LLM-judge), verifica si la tool esperada aparece en la traza, mismo patrón que
    `tool_calls_used` de `main.py`.
  - `evals/run_evals.py`: `evaluate_case()` ahora ramifica — casos con `expected_answer` siguen
    el flujo viejo (`accuracy_evaluator` contra referencia), casos con `expected_tool` usan
    `tool_call_evaluator`. `build_summary()` calcula `avg_accuracy`/`tool_call_rate` por separado
    (ausentes del summary si no hay casos de ese tipo en la corrida). `send_feedback()` manda
    también `tool_call` a LangSmith.
- **Segunda corrida completa (56 casos x 4 variantes) — decide el punto 4:**

  | Variante | Relevancia | Accuracy | Citas | Tool-call (escalamiento) |
  |---|---|---|---|---|
  | baseline_mini | 4.43/5 | 3.69/5 | 77% | 8/8 (100%) |
  | baseline_nano | 4.68/5 | 4.12/5 | 84% | 7/8 (88%) |
  | direct_answer_mini | 4.77/5 | 4.17/5 | 84% | 8/8 (100%) |
  | direct_answer_nano | 4.80/5 | 4.23/5 | 88% | 6/8 (75%) |

  **Hallazgo que decide la comparación:** nano falló los mismos 2 casos de escalamiento
  (transmisor Yokogawa fuera del corpus, caudalímetro de marca genérica) en ambas variantes de
  prompt — no es ruido, es sistemático. En vez de escalar, inventó un rango de medición genérico
  (`baseline_nano`) y fabricó un procedimiento de calibración citando "la documentación
  consultada" para un equipo que el corpus no cubre (`direct_answer_nano`) — exactamente lo que
  el `SYSTEM_PROMPT` prohíbe explícitamente. Mini no falló ni un caso (16/16 entre las dos
  variantes de prompt). **Decisión final: `direct_answer_mini`.** No es "nos quedamos con el
  conocido por costumbre" — es una ventaja medible y reproducible en la dimensión que más importa
  para este dominio (no inventar en zona gris), sumada a que el prompt nuevo ya corrige el
  problema original de mini (exceso de tickets, ver entrada anterior).
- **Sweep de temperatura sobre el ganador** (duda de Juan: ¿fijar la temperatura ayuda a que
  invente menos?): `get_bound_llm`/`build_agent_node`/`build_graph` (`src/graph.py`) y
  `build_eval_graph` (`evals/run_evals.py`) ahora aceptan `temperature` explícito (default `1.0`
  — el que ya regía sin fijarse en ningún lado, no cambia comportamiento existente).
  `evals/compare_temperature.py` nuevo: 4 valores (0.0/0.3/0.6/1.0) x 2 corridas sobre
  `direct_answer_mini`.

  | Temp | Accuracy avg | Spread (estabilidad) | Tool-call |
  |---|---|---|---|
  | 0.0 | 4.00 | 0.04 | 100% |
  | 0.3 | 4.07 | 0.10 | 100% |
  | 0.6 | 4.12 | 0.05 | 100% |
  | 1.0 (default actual) | 4.03 | **0.18** | 100% |

  Verificado que no hay bug (se leyó `llm.temperature` directo del objeto `ChatOpenAI` para
  confirmar que el valor pedido llega de verdad, sin gastar API). La aparente tendencia "más
  temperatura = más accuracy" no se sostiene con test pareado (comparación cruzada temp 0.0 vs
  0.6: 3-6/6-6/4-5/2-5, sin significancia) ni con temp=1.0 rompiendo el patrón (cae de vuelta a
  4.03, con el doble de spread que cualquier otro valor) — es ruido de muestreo del LLM-judge
  sobre 48 preguntas, no una tendencia causal. Lo único que sí es señal limpia: **temp=1.0 es la
  más inestable de las cuatro**, confirmando la sospecha original de Juan. **Decisión final:
  `temperature=0.3`** — punto medio entre estabilidad (spread 0.10, muy por debajo del 0.18 de
  referencia) y tasa de citas (86% vs 78% a temp=0.0, probable efecto de estilo — respuestas más
  tersas a temp 0 que omiten mencionar la fuente aunque hayan usado `rag_search` igual — más que
  un problema real de grounding).
  - La corrida en background se cortó sola a los 5/8 (`status: killed`, sin causa visible en el
    código ni en los logs). Las 3 corridas faltantes se relanzaron reusando las mismas funciones
    (`build_eval_graph`/`run_eval_pass`) sin repetir las 5 ya guardadas — cada corrida escribe su
    JSON apenas termina, no se perdió nada.
  - **Queda anotado, no bloqueante:** sweep chico de `gpt-4.1-nano` a temperatura baja (curiosidad
    de Juan sobre si el problema de escalamiento era más de muestreo que de conocimiento del
    modelo) — no cambia la decisión ya tomada salvo resultado sorprendente.
- **Punto 6 del plan (reproducibility) cerrado:** `README.md` — "Como correrlo" reforzado con
  checklist explícito de requisitos (API key de OpenAI, Postgres con `pgvector`, los 11 PDFs) y
  mención directa de que los links del corpus (`CORPUS_INSTRUMENTACION.MD`) son gratuitos y
  verificados HTTP 200, no solo un "ver sección anterior" pasivo. Agregado el camino de
  reproducir evals sin re-ingerir (los datasets ya están commiteados). Fila "Reproducibility" de
  la tabla de criterios actualizada. El techo real (¿alcanza 2/2 sin el dataset físicamente
  adentro del repo?) queda a criterio del revisor humano, no resoluble con más documentación.
- **Todo lo de arriba sigue sin aplicar/commitear:** la decisión (`direct_answer_mini` +
  `temperature=0.3`) está tomada pero `graph_builder = build_graph()` en `src/graph.py` todavía
  usa los defaults viejos. Archivos a commitear juntos cuando se aplique: `src/graph.py`,
  `evals/run_evals.py`, `evals/evaluators.py`, `evals/golden_set.json`,
  `evals/compare_prompts.py`, `evals/compare_temperature.py`, `evals/cost_report.py`, `prompts/`,
  `README.md`.
- **Próximo paso concreto:** aplicar la decisión final a `src/graph.py` (prompt + temperatura),
  correr los tests, commitear el punto 4 + punto 6 juntos, y seguir con el punto 5 (query
  rewriting).
- Sesión cerrada acá por hoy, a pedido de Juan — continúa mañana.

---

## 2026-08-01 — Cierra punto 3 (feedback) + punto 4 en progreso (comparación prompt x modelo, corrida real)
**Commits:** `2810fb4` (`POST /feedback`) + cambios de punto 4 sin commitear (`src/graph.py`,
`evals/run_evals.py`, `evals/compare_prompts.py`, `evals/cost_report.py`, `prompts/`)

- **Cierra el punto 3 del plan (monitoring 0→2):** `FeedbackInput` (`src/schemas.py`) + ruta
  `POST /feedback` (`src/main.py`) — INSERT a la tabla `feedback` sobre el pool existente, y
  `client.create_feedback(run_id, key="user_score", score, comment)` a LangSmith si
  `LANGCHAIN_API_KEY` está seteada (mismo patrón opt-in/fail-silent que `tools.py`). Verificado
  end-to-end con OpenAI real (créditos recargados esta sesión, cuenta vieja de julio 2025 había
  vencido): `POST /chat` real → `run_id` real → `POST /feedback` con ese `run_id` → confirmado en
  Postgres (`SELECT`) y en LangSmith (`client.list_feedback()` devuelve `key="user_score"` con el
  score/comment correctos). Commit `2810fb4` (solo código; `ROADMAP.md`/`CHANGELOG.md` quedan para
  el cierre de docs, por convención de commits separados).
- **Arranca el punto 4 (LLM evaluation 1→2, comparar múltiples approaches):** decidido con Juan
  comparar no solo 2 prompts sino también 2 modelos (`gpt-4o-mini` vs `gpt-4.1-nano`), en 4
  combinaciones aisladas — un solo cambio de variable por corrida, nunca prompt y modelo a la vez.
  - `src/graph.py` refactorizado: `SYSTEM_PROMPT` deja de vivir inline (resuelve un pendiente de
    POSPUESTO del 2026-07-15) — se lee con `load_prompt()` nuevo desde `prompts/system_prompt.txt`
    (directorio nuevo). `build_agent_node(system_prompt, model_name)` (closure factory) y
    `build_graph(system_prompt=SYSTEM_PROMPT, model_name=MODEL_NAME)` nuevos —
    `graph_builder = build_graph()` mantiene exactamente el mismo comportamiento para
    `main.py`/`conftest.py`, que no se tocaron.
  - `prompts/system_prompt_direct_answer.txt` nuevo (Variante B): agrega una instrucción de
    prioridad — responder directo con `rag_search` si el manual cubre la consulta, reservar
    `create_ticket` para lo que el manual no cubre o requiere intervención física. Ataca un
    hallazgo real sin investigar del 2026-07-27 (5/48 preguntas respondibles terminaban en
    `create_ticket` en vez de una respuesta directa).
  - `evals/run_evals.py` refactorizado para reusar en comparaciones: `build_eval_graph()`,
    `invoke_agent`/`evaluate_case` reciben el `graph` como parámetro, `run_eval_pass()`/
    `send_feedback()` extraídos. `main()` (el que corre CI) sin cambios de comportamiento.
  - **Bug real encontrado y arreglado en el camino:** el feedback de `run_evals.py` a LangSmith
    nunca se mandó desde que se implementó (2026-07-27) — `run_id` en `evaluate_case()` siempre
    daba `None` (intentaba leerlo de `trace.get("run_id")`, pero `AgentState` nunca tuvo ese
    campo). Fix: `invoke_agent()` genera el `run_id` ANTES de invocar (mismo patrón que
    `main.py`) y lo devuelve junto al trace. Verificado con `client.list_feedback()`.
  - `evals/compare_prompts.py` nuevo: corre las 4 combinaciones contra el golden set completo (48
    preguntas), guarda cada una con su propio JSON en `evals/results/`.
  - `evals/cost_report.py` nuevo: reconstruye costo/tokens reales por variante leyendo los traces
    de LangSmith asociados a los `run_id` guardados (`client.list_runs(run_ids=...)` — `read_run()`
    uno a uno pega el rate limit de LangSmith con 48 corridas seguidas).
  - **Corrida real completa (48 preguntas x 4 variantes) — calidad y costo:**

    | Variante | Relevancia | Accuracy | Citas | `create_ticket` | Costo x caso |
    |---|---|---|---|---|---|
    | baseline_mini (producción actual) | 4.40/5 | 3.60/5 | 81% | 9/48 | $0.00045 |
    | baseline_nano | 4.90/5 | 4.27/5 | 92% | 0/48 | $0.00031 |
    | direct_answer_mini | 4.62/5 | 3.94/5 | 94% | 2/48 | $0.00048 |
    | direct_answer_nano | 4.75/5 | 4.08/5 | 94% | 0/48 | $0.00033 |

    El prompt nuevo funciona como se hipotetizó, pero solo se nota con `gpt-4o-mini` (9→2
    tickets, mejora las 4 métricas). Con `gpt-4.1-nano`, el prompt VIEJO ya elimina el problema
    solo (0/48 tickets) y da las mejores métricas de las cuatro, siendo ~30% más barato que
    `gpt-4o-mini` con cualquiera de los dos prompts.
  - **Decisión pendiente de confirmar con Juan** entre `baseline_nano` (mejor en las 3
    dimensiones, pero `gpt-4.1-nano` sin kilometraje previo en el resto del pipeline) y
    `direct_answer_mini` (se queda con el modelo ya probado en todo el proyecto). Sin commitear
    hasta confirmar — se commitea junto con el cambio de default de producción.
- **Timeline armado con Juan** para lo que resta del plan de entrega (puntos 4-7 + cierre de
  docs, ~5.5h core) contra su disponibilidad real (1.5h lunes a viernes, 3h sábados) — detalle
  completo en la sección de `ROADMAP.md` de hoy. Orden de stretch confirmado si el core cierra
  con margen: RAGAS → Streamlit (front simple de chat + pulgar arriba/abajo) → deploy a cloud →
  Grafana.
- **Próximo paso concreto:** confirmar la decisión de arriba (qué combinación pasa a producción),
  aplicarla como default, commitear todo el trabajo del punto 4, y seguir con el punto 5 (query
  rewriting).
- Sesión cerrada acá por hoy, a pedido de Juan — posible continuación más tarde el mismo día o el
  lunes.

---

## 2026-07-31 (noche) — Pusheados los 3 commits pendientes + arranca endpoint de feedback (punto 3 del plan)
**Commits:** `acc1df9`, `2315f56`, `9eb92b8` (pusheados a origin/main) + cambios nuevos sin commitear (`src/main.py`, `src/schemas.py`)

- Pusheados a `origin/main` los 3 commits que quedaban locales de sesiones anteriores (ver entradas
  de abajo, ya actualizadas con sus hashes reales) — el historial de git queda al día con lo
  documentado.
- **Arrancado el punto 3 del plan** (endpoint de feedback de usuario, monitoring 0→2), primera
  pieza de varias — concepto explicado y verificado con Juan antes de escribir código:
  - `ChatResponse.run_id` nuevo (`src/schemas.py`). Generado con `uuid.uuid4()` en `src/main.py`
    **antes** de `graph.invoke()` y pasado por `config["run_id"]` — así LangSmith usa ese mismo UUID
    para el trace en vez de generar el suyo propio, y queda disponible para devolverlo en la
    respuesta y asociarle feedback después vía `client.create_feedback(run_id=...)`.
  - Tabla `feedback` (`id bigserial`, `run_id uuid`, `thread_id text`, `score real`, `comment text`,
    `created_at timestamptz`) creada en el `lifespan` de `main.py`, mismo patrón idempotente que
    `checkpointer.setup()`: `CREATE TABLE IF NOT EXISTS` + `ENABLE ROW LEVEL SECURITY` sin policies
    (mismo criterio que `chunks`/tablas del checkpointer — el rol de `DATABASE_URL` es dueño de la
    tabla y bypassea RLS por default, la API REST/anon no). Decisión explícita: reusar el pool
    `psycopg_pool` que ya abre el checkpointer en vez de una conexión nueva por request (patrón de
    `rag_search()` en `tools.py`, anotado en POSPUESTO como mejora pendiente) — evita ese mismo lag
    de conexión para el endpoint nuevo.
  - **Verificado contra Supabase real:** `uvicorn` local levantado, confirmado con un script
    descartable (fuera del repo) que la tabla existe con las columnas esperadas y
    `rowsecurity = true`. Servidor de prueba detenido al terminar.
- **Falta para cerrar el punto 3:** schema `FeedbackInput`, endpoint `POST /feedback` en `main.py`
  (INSERT a la tabla + `client.create_feedback()` a LangSmith), y committear `src/main.py` +
  `src/schemas.py` (todavía sin commit al cierre de esta sesión).
- **Próximo paso concreto:** `FeedbackInput` (schema) + ruta `POST /feedback`, mismo ritmo de a una
  pieza por vez con pregunta de active recall.
- Sesión cerrada acá por hoy, a pedido de Juan.

---

## 2026-07-31 — Docker build/run probados y verificados — containerization 0→1 cerrado
**Commits:** `2315f56` (Dockerfile + .dockerignore), `9eb92b8` (README + ROADMAP/CHANGELOG)

- **Active recall de Docker al arrancar la sesión** (pedido explícito de Juan en la
  entrada de ayer, antes de tocar el build): preguntas sobre Dockerfile vs imagen vs
  container, diferencia entre `docker build` y `docker run`, y por qué el
  `.dockerignore` excluye `.env`/`docs/pdfs/`. Las tres respuestas de Juan fueron
  correctas — se ajustó solo un matiz chico (la imagen es agnóstica al ambiente
  dev/QA/prod, lo que cambia entre containers de la misma imagen son las variables
  que se le pasan en `docker run`, no la imagen en sí).
- **`docker build -t agentic-rag-fastapi .`**: corrió sin errores (~61s, mayormente
  `pip install` de las dependencias sobre `python:3.12-slim`). Imagen
  `agentic-rag-fastapi:latest` creada.
- **`docker run --env-file .env -p 8000:8000 agentic-rag-fastapi`**: container
  levantado en background, logs confirman conexión real a Postgres (Supabase),
  `checkpointer.setup()` corrido, uvicorn arriba en `0.0.0.0:8000`.
- **`POST /chat` real contra el container** ("Cual es el rango de medicion de un
  transmisor de presion Rosemount?", `thread_id=docker-build-test`): 200 OK,
  `rag_search` encontró el chunk correcto (`siemens_sitrans-p320-p420_datasheet_es.pdf`),
  respuesta con cita de fuente, `tool_calls_used: ["rag_search"]` poblado — confirma
  además que el fix de `tool_calls_used` de la Sesión 2 (2026-07-29) funciona también
  dentro del container, no solo en local.
- Container detenido y eliminado (`docker stop` + `docker rm`) al terminar la prueba,
  sin dejar nada corriendo.
- **Punto 1 del plan de la entrega (containerization) queda completo — 0→1 en la
  rúbrica.**
- **Punto 2 del plan (README): agregada la sección "Criterios de evaluacion (LLM
  Zoomcamp 2026)"** — regla dura del curso, el README debe mencionar explícitamente
  los criterios para que el reviewer los ubique fácil. Tabla con los 9 criterios
  oficiales, cada uno apuntando a dónde vive en el repo (`evals/retrieval_metrics.py`
  para retrieval evaluation, `evals/run_evals.py` para LLM evaluation,
  `scripts/ingest.py` para ingestion pipeline, etc.) — sin inflar: Monitoring y
  reranking/query rewriting quedaron marcados como "Pendiente" porque todavía no
  existen. También sumado el comando `docker run` a la sección "Como correrlo".
- **Decidido el enfoque del punto 3 (monitoring), sin implementar todavía:** en vez
  del endpoint de feedback solo (0→1), apuntar a 2/2 aprovechando que LangSmith ya
  está prendido y su dashboard de proyecto ya expone varios gráficos gratis (runs,
  latencia, tokens/costo, error rate). El endpoint de feedback va a escribir en
  Postgres **y** mandar el feedback a LangSmith con `client.create_feedback(run_id,
  ...)` (dependencia ya instalada) para que quede asociado a cada trace — evita
  armar el stack Postgres+Grafana completo que seguía como stretch.
- **Confirmado con Juan el framework para el punto de evals de generación (RAGAS,
  ya anotado en POSPUESTO desde 2026-07-18):** se suma como upgrade condicional,
  solo si el plan core (puntos 3-7) cierra con tiempo de sobra antes del 10/08.
  Elegido por ser el nombre más reconocible para evaluación de RAG específicamente
  en búsquedas laborales de AI/LLM Engineer. Estimado ~1.5-2.5h, con riesgo de
  compatibilidad de versión entre `ragas` y `langchain==1.2.15` como principal
  fuente de incertidumbre.
- **Próximo paso concreto:** implementar el punto 3 del plan (endpoint de feedback +
  `create_feedback` a LangSmith).
- **Sesión cerrada acá por hoy**, a pedido de Juan.

---

## 2026-07-30 — Dockerfile (containerization 0→1), sin probar todavía
**Commit:** `2315f56`

- **Arrancado el punto 1 del plan de la entrega** (ver "Cambio de prioridad" en
  `ROADMAP.md`, 2026-07-29): containerization. Explicado el concepto a Juan antes de
  escribir código (Dockerfile = receta, imagen = resultado empaquetado del build,
  container = instancia corriendo; `docker build` construye la imagen, `docker run`
  levanta un container a partir de ella) y por qué la imagen no incluye `docs/pdfs/`
  (la ingesta ya corrió contra Supabase, la app en runtime solo consulta la base, no
  reingiere nada) ni `.env` (secretos se pasan en runtime con `--env-file`, nunca se
  copian a la imagen — la misma imagen sirve para dev y prod).
- **Creados dos archivos nuevos:**
  - `Dockerfile`: base `python:3.12-slim` (mismo Python que local, liviana; no hace
    falta build-essential/libpq-dev porque `psycopg[binary]`/`psycopg2-binary` ya
    traen wheels autocontenidos). `COPY requirements.txt` + `pip install` antes de
    `COPY src/` — cachea la capa de dependencias, no reinstala todo si solo cambia
    código. `EXPOSE 8000` + `CMD uvicorn src.main:app --host 0.0.0.0 --port 8000`
    (`0.0.0.0`, no `127.0.0.1`, para que sea alcanzable desde fuera del container).
  - `.dockerignore` (no existía): excluye `.venv/`, `.git/`, `.github/`,
    `.pytest_cache/`, `__pycache__/`, `.env`/`.env.example`, `docs/`, `tests/`,
    `reports/`, `evals/results/`, `courses/`, `archive/`, `scripts/`, `*.md`.
- **Sin probar esta sesión:** ni `docker build -t agentic-rag-fastapi .` ni
  `docker run --env-file .env -p 8000:8000 agentic-rag-fastapi` se corrieron
  todavía — queda para la próxima sesión.
- **Próximo paso concreto:** Juan pidió explícitamente que la próxima sesión arranque
  con preguntas de active recall sobre los conceptos de hoy (Dockerfile vs imagen vs
  container, build vs run, por qué `.dockerignore`) **antes** de probar el build —
  no saltar directo a `docker build`. Después de eso: probar el build/run real y
  seguir con el resto del plan (README con criterios de evaluación, endpoint de
  feedback, comparar system prompts, query rewriting, reproducibility, limpieza de
  historial de git).

---

## 2026-07-29 (tarde) — Cierra Sesión 2 completa + entrega LLM Zoomcamp 2026 (deadline 10/08)
**Commits:** `acc1df9` (código Sesión 2 completa: dead code + tracing + tool_calls_used + max_tokens + RAGResult/TicketInput), `9eb92b8` (docs — PROJECT_APPROVAL_HANDOFF.md nuevo + ROADMAP/CHANGELOG)

- **Cerrados los 4 ítems restantes de la Sesión 2** (batch de limpieza mecánica),
  uno por vez con explicación previa:
  - `ChatResponse.tool_calls_used` (`src/main.py`): antes siempre devolvía `[]`
    (deuda técnica desde Capa 5A, 2026-06-20). Ahora recorre `result["messages"]`
    después de `graph.invoke()` y junta los `.tool_calls[].name` de los mensajes
    que llamaron una tool, sin duplicados.
  - `max_tokens=800` explícito en `get_bound_llm()` (`src/graph.py`) — aprendizaje
    empírico de M3 (Zoomcamp): sin techo, resúmenes largos escalan ~2.3x en tokens
    de output. 800 alcanza de sobra para una respuesta técnica puntual con cita de
    fuente.
  - Contrato de `RAGResult.score` (`src/schemas.py`) corregido: decía
    `ge=0.0/le=1.0` y "similitud coseno", pero `rag_search()` le pasa el score de
    **RRF** (Reciprocal Rank Fusion) — un algoritmo que fusiona por *ranking*
    (posición en cada lista de resultados), no por los valores de similitud coseno
    ni de `ts_rank` de cada búsqueda (esos valores viven en escalas no
    comparables entre sí, por eso RRF los descarta y solo mira posiciones). El
    `le=1.0` era seguro hoy solo por casualidad (con `rrf_k=1` el máximo de RRF da
    exactamente 1.0); se sacó el `le=1.0` y se corrigió la descripción a "score de
    fusión RRF".
  - `TicketInput.category` (`src/schemas.py`) redominado: las 4 categorías
    genéricas de soporte de software (`bug/feature/question/other`, herencia de la
    Capa 1) reemplazadas por `field_instrument_failure/biological_process_anomaly/
    pump_maintenance/undocumented_query` — tomadas del borrador ya existente en
    `CORPUS_INSTRUMENTACION.MD` y traducidas a inglés para seguir la convención del
    resto del `Literal` (`low/medium/high`). `tests/test_rules.py` actualizado:
    los dos tests de `create_ticket` usaban un ejemplo del dominio viejo ("el
    cliente no puede iniciar sesión", categoría `question`/`bug`) — reemplazados
    por un caso real de instrumentación de campo.
  - Verificado con `pytest tests/test_rules.py` (7/7) después de cada cambio.
  - **Sesión 2 queda completa** (6/6 ítems: paso 6 dead code + tracing real +
    estos 4).
- **Cambio de prioridad, fuera de código:** Juan compartió
  `courses/PROJECT_APPROVAL_HANDOFF.md` — este repo se entrega tal cual como
  proyecto final del **LLM Zoomcamp 2026** (DataTalks.Club). Deadline real
  2026-08-10, intento oportunista 2026-08-03. Se auditó el repo contra la rúbrica
  oficial (9 criterios 0-2 pts + 3 best practices, máx 18+3): hoy ~12/21 —
  Problem description/Retrieval flow/Retrieval evaluation/Interface en 2, LLM
  evaluation/Ingestion pipeline/Reproducibility en 1, Monitoring/Containerization
  en 0, best practices solo hybrid search (1/3). Se armó con Juan un plan de
  acción priorizado por ROI (puntos de rúbrica por hora de trabajo disponible:
  hoy 1h, lun-vier 1.5h, sábados 3h) — detalle completo del plan y el cronograma
  día a día en la sección "Cambio de prioridad" de `ROADMAP.md`. La limpieza del
  historial de git (POSPUESTO desde 2026-07-02) pasa a estar en alcance de esta
  entrega — Juan confirmó que quiere el repo público y limpio para el peer review
  del curso.
- **Próximo paso concreto:** Dockerfile de la app (containerization 0→1,
  ~1.5h, planeado para mañana 2026-07-30).

---

## 2026-07-29 — Tracing real verificado en LangSmith — cierra el ítem de la Sesión 2
**Commit:** pendiente (cambios sin commitear al momento de escribir esta entrada)

- Cerrado el único pendiente que dejaba el paso de tracing de la entrada de ayer:
  faltaba agregar `LANGCHAIN_TRACING_V2=true` a `.env` y confirmar un trace real en
  LangSmith. `.env` ya lo tenía al arrancar la sesión (junto con `LANGCHAIN_API_KEY`
  y `LANGCHAIN_PROJECT`, confirmado con un chequeo de presencia sin exponer valores).
- **Verificación end-to-end:** servidor levantado localmente (`uvicorn src.main:app`)
  y un `POST /chat` real (`"Cual es el rango de medicion de un transmisor de presion
  Rosemount?"`, `thread_id=test-trace-verificacion`) contra Supabase+OpenAI reales.
  Respuesta con cita de fuente (`SITRANS P320/P420 Datasheet`), 200 OK, sin errores
  en el log del servidor.
- **Confirmado en el dashboard de LangSmith** (captura de Juan, proyecto
  `agentic.rag.fastapi`): el árbol de spans es el esperado — `ChatOpenAI gpt-4o-mini`
  trazado automático por el tracer global de LangChain (sin código propio), y dentro
  del span de la tool `rag_search` (4.29s), anidados como hijos, `agent.rag_search.
  vector` (0.73s) y `agent.rag_search.keyword` (1.00s) — el `@traceable` manual de
  `_vector_search`/`_keyword_search` se integra en la misma jerarquía que el tracer
  automático, siguiendo la pila de ejecución real (no por archivo ni por tipo de
  objeto).
- Servidor de prueba apagado al terminar (`taskkill /F /IM uvicorn.exe`), sin dejar
  procesos colgados.
- **El ítem de tracing real de la Sesión 2 queda cerrado.** Próximo paso dentro de
  esa sesión: `ChatResponse.tool_calls_used`, `max_tokens` explícito en
  `get_bound_llm()`, contrato de `RAGResult.score`, redominar `TicketInput`.

---

## 2026-07-28 (tarde) — RLS en tablas del checkpointer + rotación de credenciales + Sesión 2 arrancada
**Commit:** pendiente (cambios sin commitear al momento de escribir esta entrada)

- **Alerta real de Supabase, no simulada:** mail automático (`rls_disabled_in_public`)
  avisando que había una tabla pública sin RLS. Investigado con
  `SELECT schemaname, tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';`
  en el SQL Editor: `chunks` en `true` (ya corregido en 5B.4), pero las 4 tablas del
  checkpointer (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`,
  `checkpoint_migrations`, creadas por `PostgresSaver.setup()` en 5B.3) en `false` —
  nunca pasaron por el `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` manual que sí tuvo
  `chunks`. Corregidas con el mismo patrón: RLS habilitado sin policies (el backend
  conecta por rol directo de Postgres, no por la API REST/anon key, así que no se ve
  afectado). Verificado con la misma query (las 5 tablas en `true`) y con
  `pytest tests/test_rules.py` (7/7, confirma que el acceso real de la app a `chunks`
  sigue intacto).
- **Rotación de credenciales reales completada** (quedaba pendiente desde la entrada de
  la mañana): `OPENAI_API_KEY` nueva generada dentro de un proyecto scopeado creado en
  OpenAI (en vez de una key "All projects"), y password de `DATABASE_URL` reseteada en
  Supabase. Motivo extra que aceleró esto: durante la sesión Claude expuso por error, en
  el chat, la `OPENAI_API_KEY` nueva (un comando `sed` pensado para truncar el output no
  truncó nada) — se tuvo que rotar de nuevo apenas se detectó. Ambas rotaciones
  verificadas con `pytest tests/test_rules.py` en verde. El secret `DATABASE_URL` de
  GitHub Actions (rol `ci_readonly`, password propia) no se tocó.
- **La prioridad 1 (CI en verde + seguridad) queda completamente cerrada.** Lo único que
  sigue pendiente es la limpieza del historial de git — ya no es una emergencia (las
  credenciales viejas del historial quedaron inertes), es higiene antes de publicar el
  repo como portfolio (ver POSPUESTO en `ROADMAP.md`).
- **Arrancada la Sesión 2** (batch de limpieza mecánica, ver plan en `ROADMAP.md`):
  - **Paso 6 completo:** sacado código muerto de la Capa 5A —
    `InMemoryIndex`/`KeywordIndex`/`build_index()`/`set_index()`/`_index`, en
    `src/ingestion.py`, `src/tools.py` y `src/main.py`. Sin uso real desde que
    `rag_search()` migró a Postgres en 5B.2 (`main.py` seguía re-embebiendo
    `docs/*.txt` con la API de OpenAI en cada arranque para un índice que nadie leía
    después — y `docs/` ya ni tiene `.txt` desde 5B.4, solo `pdfs/`, así que el bloque
    tampoco encontraba qué indexar). `chunk_text()`, `embed_texts()` y `rrf()` se
    quedan — siguen en uso real (`scripts/ingest.py`, `rag_search()`,
    `_hybrid_search()`). Verificado con `git grep` (sin referencias restantes a los
    símbolos borrados) y `pytest tests/test_rules.py` (7/7).
  - **Tracing real, en progreso (no cerrado):** `_vector_search`/`_keyword_search` en
    `src/tools.py` instrumentados con `@traceable` de LangSmith (spans
    `agent.rag_search.vector`/`agent.rag_search.keyword`, `run_type="retriever"`),
    gateado por `LANGCHAIN_API_KEY` — mismo patrón opt-in que
    `evals/evaluators.py`. En el camino, encontrado y arreglado un bug real: en
    `src/main.py`, `from src.graph import graph_builder` (que dispara
    `import src.tools`) pasaba antes de que `load_settings()` cargara `.env` dentro
    del `lifespan()` — el gating de `LANGCHAIN_API_KEY` se evalúa a nivel de módulo,
    así que la instrumentación quedaba desactivada en producción aunque la key
    estuviera en `.env`. Arreglado moviendo `load_dotenv()` al principio de
    `main.py`, antes del import. Con `LANGCHAIN_TRACING_V2=true` prendido (falta que
    Juan lo agregue a `.env` — ya tiene `LANGCHAIN_API_KEY`/`LANGCHAIN_PROJECT`), el
    LLM call de `agent_node` y los tool-calls `rag_search`/`create_ticket` quedan
    auto-trazados por LangChain sin código extra (tokens/costo incluidos, LangSmith
    los calcula solo) — patrón de M5 aplicado vía LangSmith, no OTel crudo.
    Verificado por código que el wrapping se activa correctamente al importar
    `src.main`; falta verificar un trace real en LangSmith antes de dar el ítem por
    completo.
- **Próximo paso concreto:** agregar `LANGCHAIN_TRACING_V2=true` a `.env` y confirmar un
  trace real en LangSmith para cerrar el ítem de tracing. Después sigue el resto de la
  Sesión 2 (`ChatResponse.tool_calls_used`, `max_tokens` explícito, contrato de
  `RAGResult.score`, redominar `TicketInput`) y, aparte, la limpieza del historial de
  git cuando Juan confirme el plan.

---

## 2026-07-28 — CI en verde: rol read-only en Supabase + preguntas del dominio actual
**Commit:** `1945750`

- Cerrados los dos pendientes técnicos que dejaba el job `evals` de CI roto (ver
  entrada 2026-07-27 de abajo):
  - **Rol `ci_readonly` en Supabase:** `GRANT SELECT` únicamente sobre `chunks`
    (`CONNECT` en la base + `USAGE` en el schema, sin ningún permiso de
    escritura/DDL) en vez de reusar la credencial completa de producción. Como
    `chunks` tiene RLS activado sin policies desde 5B.4 paso 2, hizo falta además
    una policy scopeada a ese rol (`CREATE POLICY ... TO ci_readonly USING (true)`)
    — sin ella el `SELECT` hubiera devuelto 0 filas en vez de fallar, un error fácil
    de no notar. Verificado con un script descartable (fuera del repo, borrado
    después de usarlo): `SELECT COUNT(*) FROM chunks` → 2451 filas; `INSERT` →
    `permission denied`; `SELECT` sobre `checkpoints` (tabla fuera de su alcance) →
    también `permission denied`. Confirmado antes de esto que `evals/run_evals.py`
    compila con `MemorySaver` (no `PostgresSaver`) en CI, así que el rol nunca
    necesita ver las tablas del checkpointer.
  - Connection string de `ci_readonly` guardado como secret `DATABASE_URL` en
    GitHub Actions; `.github/workflows/ci.yml` actualizado para pasarlo como env
    var del job `evals`.
  - `tests/test_evals.py`: las 2 preguntas hardcodeadas del dominio viejo
    (reembolso, ticket de login por credenciales) reemplazadas por preguntas reales
    de instrumentación de campo — una factual tomada del golden set nuevo (flujo
    `rag_search`), una de escalado a técnico de planta por transmisor descalibrado
    (flujo `create_ticket`).
- **Verificado en dos niveles:** local (`pytest tests/test_evals.py`, 3 tests en
  verde contra Supabase+OpenAI reales) y en CI real — push del commit, run #17 de
  GitHub Actions verde en ambos jobs (`rules` y `evals`). Único aviso: deprecación
  de Node.js 20 en el runner de GitHub Actions, genérico de la plataforma, no
  relacionado a este repo ni bloqueante.
- **La prioridad 1 (CI en verde + seguridad) queda cerrada en su parte de CI.**
- **Hallazgo de seguridad en el camino:** al armar el connection string de
  `ci_readonly` se expuso sin querer, en texto plano dentro del chat de la sesión,
  la password real de `DATABASE_URL` de producción. Juan restauró esa misma
  password en `.env` (no generó una nueva) — la credencial de producción sigue
  siendo la misma de antes de la sesión. Motivo de más para no seguir posponiendo
  la rotación de credenciales (ver POSPUESTO en `ROADMAP.md`).
- **Próximo paso concreto:** lo único que queda pendiente de la prioridad 1 es la
  rotación de credenciales reales (`OPENAI_API_KEY`, `DATABASE_URL` de producción)
  + limpieza del historial de git. Sesión 2 de limpieza y evals sobre las 520
  preguntas completas (vs. las 48 del sample) siguen después, sin fecha.

---

## 2026-07-27 — Golden set nuevo del corpus real + accuracy_evaluator — evals de generación corridas
**Commit:** `1945750` (commiteado el 2026-07-28, un día después de escrito, junto con el
trabajo de esa sesión — ver entrada de arriba)

- Al abrir la prioridad 1 (arreglar/aislar el job `evals` de CI, roto con `RuntimeError:
  Falta DATABASE_URL`), se encontró que el problema no era solo técnico: `golden_set.json`
  seguía teniendo 20 preguntas sobre LangGraph docs, corpus que ya no existe en Supabase
  desde 5B.4. Conectar `DATABASE_URL` sin resolver eso solo hubiera cambiado el error, no
  arreglado el job — se priorizó resolver el contenido primero.
- `evals/generate_golden_set.py` (nuevo): samplea 12 preguntas por categoría (48 total,
  seed=42 fijo) de las 520 de `ground_truth_retrieval.json` (5B.4 paso 4), trae el
  contenido real de sus `chunk_ids` desde Supabase, y le pide al LLM (gpt-4o-mini,
  structured output) que escriba la `expected_answer` grounded en ese texto. No genera
  preguntas nuevas ni cambia el mapeo pregunta→chunk, ya verificado en 5B.4. Corrido
  contra Supabase+OpenAI reales: `evals/golden_set.json` sobrescrito con las 48 preguntas
  nuevas, reemplazando las 20 del corpus viejo.
- `evals/evaluators.py`: nuevo `accuracy_evaluator(question, expected_answer, answer)` —
  LLM-judge que compara la respuesta del agente contra la referencia del golden set.
  Complementa a `relevance_evaluator` (que juzga sin referencia), no lo reemplaza:
  `relevance_evaluator` sigue siendo el único evaluador que sirve para casos sin
  `expected_answer` (ej. el flujo de `create_ticket` en `test_evals.py`, o tráfico real en
  producción).
- `evals/run_evals.py`: cada caso corre `accuracy_evaluator` además de
  `relevance_evaluator`, el resumen agrega `avg_accuracy`, y el feedback a LangSmith manda
  las dos keys (`relevance`/`accuracy`) en vez de solo `relevance`.
- Corrida real completa contra las 48 preguntas del golden set nuevo: relevancia 4.44/5,
  accuracy 3.88/5, 85% con cita, 4.08 pasos promedio (resultados en
  `evals/results/2026-07-27/10-18-16.json`). **Hallazgo sin investigar:** 5 de las 48
  preguntas, todas respondibles con el manual, terminaron en `create_ticket` en vez de una
  respuesta directa por `rag_search` — candidato a explicar buena parte de la brecha entre
  relevancia y accuracy.
- **Próximo paso concreto:** cerrar la prioridad 1 (CI en verde + seguridad) — agregar
  `DATABASE_URL` como secret de CI usando un rol de Postgres de solo lectura (GRANT SELECT
  en `chunks`, sin permisos de escritura/DDL — decidido con Juan para no exponer la
  credencial completa de producción a CI, todavía no creado) y reemplazar las 2 preguntas
  hardcodeadas del dominio viejo (reembolso, ticket de login) en `tests/test_evals.py`. La
  rotación de credenciales + limpieza de historial de git sigue sin tocarse.

---

## 2026-07-24 (2) — Capa 5B.3 verificada contra Supabase real — Capa 5B y Capa 5 completas
**Commit:** `921ab4f`

- Script manual (pool + `checkpointer.setup()` + dos `graph.invoke()` con el mismo
  `thread_id`, fuera del repo) corrido contra Supabase real: `setup()` creó/confirmó las
  4 tablas de `PostgresSaver` (`checkpoints`/`checkpoint_blobs`/`checkpoint_writes`/
  `checkpoint_migrations`); el segundo invoke recordó el dato dado en el primero —
  persistencia real por `thread_id` confirmada, no solo código que compila.
- Commiteados y pusheados los 7 archivos que quedaban pendientes de la sesión de 5B.3
  (`src/graph.py`, `src/main.py`, `tests/conftest.py`, `evals/run_evals.py`,
  `requirements.txt`, `ROADMAP.md`, `CHANGELOG.md`).
- `ROADMAP.md`: 5B.3 pasa de "en progreso" a ✅ completa; con eso, Capa 5B
  (pgvector/Supabase + FTS) y Capa 5 (RAG real con PDFs) quedan completas — sus 5
  subcapas (5A, 5A.2, 5B.0–5B.4) ya estaban hechas.
- **Próximo paso concreto:** arranca la prioridad 1 de la revisión estratégica de más
  abajo — CI en verde + seguridad (arreglar/aislar el job de evals roto en `ci.yml` y
  rotar credenciales reales + limpiar historial de git).

---

## 2026-07-24 — Revisión estratégica del repo + roadmap (sin cambios de código)
**Commit:** pendiente (solo docs: ROADMAP.md + CHANGELOG.md)

- Sesión de review completo del repo y el roadmap con Opus 4.8 (el trabajo día-a-día
  venía con Sonnet 5). No se tocó código: se leyó el core (`tools.py`, `graph.py`,
  `ingestion.py`, `main.py`, `schemas.py`, `config.py`, `test_rules.py`, `ci.yml`) y
  se cruzó contra ROADMAP/CHANGELOG. Verificado que lo documentado de 5B.3 ("código
  de los 4 pasos completo, falta verificar contra Supabase real") coincide con el
  código real — sin inconsistencias de ✅.
- **Objetivo confirmado:** portfolio para conseguir trabajo, pero SIN fecha dura →
  balancear la profundidad de retrieval (ya sólida) con cerrar huecos de producto.
- **Prioridades reordenadas (después de cerrar 5B.3):** (1) CI en verde + seguridad
  — arreglar/aislar el job de evals roto y adelantar a AHORA la rotación de
  credenciales + limpieza de historial de git (deja de ser "antes de público");
  (2) evals del corpus real — LLM-as-judge sobre las 520 preguntas de instrumentación.
  Sinérgicas: el dataset de evals real puede alimentar el job de CI que hoy falla.
- **Hallazgos técnicos anotados para la Sesión 2 de limpieza:**
  - `RAGResult.score` (`src/schemas.py`) declara `ge=0.0/le=1.0` y "similitud coseno",
    pero `rag_search()` le pasa el score de RRF. No explota hoy solo porque con k=1 el
    máximo de RRF es exactamente 1.0; frágil si cambia k (score>1.0 → ValidationError
    en producción). Contrato mentiroso, arreglo de 2 min.
  - `create_ticket`: el schema `bug/feature/question` es vocabulario prestado del curso
    DeepLearning y no encaja en instrumentación. Decisión: redominar a orden de trabajo
    / aviso de mantenimiento (schema barato, sin persistencia); la persistencia real en
    Postgres queda como capa futura explícita opcional atada al deploy (Capa 6).
  - Confirmada la deriva menor ya conocida: el `build_index()` del lifespan de `main.py`
    quedó inerte (docs/ ya no tiene `.txt`), no "re-embebe en cada arranque" como decía
    la nota vieja — parte del código muerto a limpiar en Sesión 2.
- **Modelo de trabajo acordado:** Sonnet 5 para construir día-a-día; Opus 4.8 para
  sesiones de arquitectura/estrategia/bugs difíciles.
- **Próximo paso concreto:** cerrar 5B.3 (verificación contra Supabase real: script
  chico con pool + `setup()` + dos `invoke()` con el mismo `thread_id`), y recién ahí
  abrir el bloque de CI + seguridad. Se retoma con Sonnet 5.

---

## 2026-07-23 — Capa 5B.3 (Postgres checkpointer): código completo (4/4 pasos), falta verificar contra Supabase real
**Commit:** pendiente (cambios sin commitear al momento de escribir esta entrada)

- Arrancada Capa 5B.3 (MemorySaver → PostgresSaver), diseño ya cerrado desde 2026-07-07,
  desbloqueada el 2026-07-22 al terminar M5 del Zoomcamp. Los 4 pasos del plan quedaron
  implementados en la misma sesión:
  1. Instalado `langgraph-checkpoint-postgres==3.1.0` (trae `psycopg` v3 + `psycopg_pool`,
     conviven a propósito con `psycopg2-binary` que ya usa `tools.py` — no se migra ese
     archivo). Hallazgo en el camino: `psycopg` puro necesita la librería nativa `libpq`
     instalada en el sistema, ausente en este Windows — el import fallaba. Se resolvió
     instalando `psycopg[binary]` (wheel autocontenido, mismo motivo por el que el proyecto
     ya usa `psycopg2-binary` en vez de `psycopg2` a secas). `requirements.txt` actualizado.
  2. `src/graph.py`: dejó de compilar el grafo a nivel de módulo (antes corría al importar,
     antes de que exista el lifespan de FastAPI — mismo tipo de bug que el cliente de OpenAI
     de `ingestion.py` arreglado el 2026-07-15). Ahora exporta `graph_builder` sin compilar;
     se sacó el import de `MemorySaver` del archivo.
  3. `src/main.py`: el lifespan abre un `psycopg_pool.ConnectionPool` real a Postgres
     (`autocommit=True` — cada operación del checkpointer se confirma sola, sin dejar
     transacciones abiertas; `prepare_threshold=0` — evita prepared statements, que pueden
     fallar si `DATABASE_URL` pasa por un pooler tipo pgbouncer), llama `checkpointer.setup()`
     (idempotente, crea las tablas de `PostgresSaver` si no existen) y recién ahí compila
     `graph_builder.compile(checkpointer=...)`, guardado en la variable global `graph`. El
     pool se cierra después del `yield`. `/chat` ahora valida `graph is None` además de
     `settings is None`.
  4. `tests/conftest.py` y `evals/run_evals.py` ya no importan `graph` compilado (ese nombre
     dejó de existir en `src/graph.py`) — importan `graph_builder` y lo compilan ellos mismos
     con `MemorySaver()`: `conftest.py` dentro de la fixture `agent_graph` (lazy, por test),
     `run_evals.py` a nivel de módulo (sin el problema del paso 2, porque `MemorySaver` no
     abre ninguna conexión real ni depende de credenciales). Motivo de fondo: los evals/tests
     corren en una sola pasada de principio a fin, no necesitan que el estado sobreviva un
     reinicio — eso solo importa para `main.py`, que corre como servidor de larga duración.
  Verificado: los 7 tests de `test_rules.py` pasan en verde con el fix, y `python -c "import
  src.main"` / `python -c "import evals.run_evals"` importan sin errores.
- **Pendiente antes de cerrar 5B.3 (no se hizo hoy):** todo lo de arriba es código nuevo
  nunca corrido contra Supabase real. Falta confirmar que `checkpointer.setup()`
  efectivamente crea las tablas de `PostgresSaver`, y que un `/chat` real persiste y
  recupera una conversación por `thread_id` entre llamadas. No requiere levantar el
  servidor completo con `uvicorn` — alcanza con un script chico que abra el pool, corra
  `setup()`, compile el grafo y haga dos `graph.invoke()` seguidos con el mismo `thread_id`.
- **Próximo paso concreto:** esa verificación contra Supabase real, para recién ahí dar
  Capa 5B.3 (y Capa 5B completa) por cerrada.

---

## 2026-07-22 — M5 del Zoomcamp terminado (videos + homework) + handoff post-curso + Sesión 1 desbloqueada
**Commit:** `79a8f17`

- Terminado el Módulo 5 del LLM Zoomcamp (Monitoring): videos vistos, apuntes
  (`M5-lessons/apuntes.md`) completos y HW5 repasado (`M5-lessons/HW5 - Juan Belbey.ipynb`,
  Q1–Q6) — HW ya estaba entregado (excepción puntual corriendo código real contra OpenAI),
  faltaba el repaso.
- `courses/POST_COURSE_ZOOMCAMP_M5.md` (nuevo): handoff completo del módulo — tabla de
  respuestas confirmadas (Q1–Q6: 3 spans por trace, ~7000 input tokens, span `llm`
  concentra >99% del tiempo), conceptos clave de OpenTelemetry (trace/span/attributes,
  processor vs exporter, anidamiento automático de spans, instrumentación vía subclase +
  `super()`, exporter custom), y auditoría contra el código real del repo:
  - El runtime real (`/chat`) sigue sin tracing prendido — LangSmith (Capa 3B) solo cubre
    `evals/`, gap ya confirmado en el handoff de M3 y todavía sin resolver.
  - No hay collector propio desplegado en ningún lado (repo corre local o en Render/Fly.io) —
    montar uno ahora sería infraestructura sin usuario que la necesite.
  - Tokens y costo no se trackean en ningún lado del repo hoy — terreno limpio para aplicar
    el patrón de M5 (atributos de span, no logs sueltos) el día que se prenda tracing real.
  - **Decisión tomada:** adoptar el patrón de M5 (spans nombrados por paso interno,
    tokens/costo como atributos) pero implementado *dentro de LangSmith* (que ya soporta
    metadata por span vía `@traceable`), no con el exporter/collector OTel crudo del
    homework — segunda vía de tracing en paralelo sin necesidad real. Migrar de LangSmith a
    OpenTelemetry puro queda pospuesto en `ROADMAP.md`, condicionado a dos escenarios
    concretos (pasos no-LangChain que LangSmith no pueda trazar, o superar el tier gratuito
    de 5.000 trazas/mes) — hoy no hay señal de que eso esté pasando.
- **Consulta aparte resuelta (no es de M5):** se revisó si se había corrido LLM-as-judge
  sobre las 520 preguntas del ground truth nuevo (`evals/ground_truth_retrieval.json`,
  pasos 4-6 de 5B.4). Confirmado leyendo el JSON y `run_evals.py`: no se hizo — el archivo
  no tiene `expected_answer`, y `evaluators.py`/`run_evals.py` siguen corriendo solo contra
  `golden_set.json` (20 preguntas del corpus viejo). Anotado como pendiente aparte en
  `ROADMAP.md` (POSPUESTO), distinto del punto ya existente sobre RAGAS.
- `ROADMAP.md`: Sesión 1 (Capa 5B.3, Postgres checkpointer) marcada como desbloqueada — la
  pausa por HW5 ya no aplica. Sesión 2 actualizada para sumar el patrón de M5 al mismo
  cambio de "prender tracing real". Corregida una inconsistencia encontrada al pasar: el
  ítem "actualizar SYSTEM_PROMPT de graph.py" seguía listado como pendiente en Sesión 2
  pese a estar hecho desde el paso 3 de 5B.4 (2026-07-15) — tachado, ya no es parte de la
  cola. Dos entradas nuevas en POSPUESTO (LLM-as-judge sobre corpus nuevo, migración a OTel
  condicional).
- **Próximo paso concreto:** Capa 5B.3 (Postgres checkpointer) es la siguiente en la cola,
  sin condición pendiente — diseño de 4 pasos ya cerrado (ver PRÓXIMO PASO en `ROADMAP.md`).
  Estimado ~1.5-2h. Sesión 2 de limpieza (ahora con la pieza de M5 sumada) queda después,
  ~1.5h. El LLM-as-judge sobre las 520 preguntas queda aparte, sin bloquear nada, estimado
  como sesión completa (2-4h) por el costo de generar `expected_answer` + correr el juez
  contra el dataset real.

---

## 2026-07-18 (2) — Capa 5B.4 paso 6: barrido de k de RRF — Capa 5B.4 completa (6/6)
**Commit:** `d87ce34`

- **`_hybrid_search()` expone `rrf_k`** (default 60, sin cambiar `rag_search()` todavía) —
  pieza chica antes del barrido, para poder pasar `k` desde `evals/retrieval_metrics.py` sin tocar
  el comportamiento de producción mientras se mide.
- **`evals/retrieval_metrics.py` extendido** con `RRF_K_VALUES = [1, 50, 60, 100, 200]`
  (mismo patrón de la notebook de M4) y `sweep_rrf_k()`, reusando los embeddings ya calculados de
  las 520 preguntas (sin costo extra de OpenAI, solo más consultas a Postgres).
- **Criterio de decisión acordado con Juan antes de ver los números:** priorizar **hit_rate sobre
  MRR** — a diferencia de un buscador tradicional, `rag_search()` manda *todo* el top-k como
  contexto al LLM, así que la posición exacta dentro del top-k importa menos que si el chunk
  correcto está presente. Preferencia adicional por un `k` robusto en un rango antes que el pico
  aislado más alto (motivado por el hallazgo sin resolver del paso 4 sobre preguntas "forzadas" —
  no conviene sobreajustar un hiperparámetro a una sola muestra con caveats conocidos).
- **Resultado del barrido (top_k=5, 520 preguntas):**

  | k | hit_rate | mrr |
  |---|---|---|
  | **1** | **0.3173** | **0.1858** |
  | 50 | 0.3115 | 0.1797 |
  | 60 (default anterior) | 0.3115 | 0.1797 |
  | 100 | 0.3115 | 0.1797 |
  | 200 | 0.3115 | 0.1797 |

  `k=1` ganó en las dos métricas a la vez — no hubo trade-off que resolver con el criterio
  acordado. Mecanismo (derivado con Juan a mano antes de correr el barrido, con un ejemplo
  numérico de dos rankings): `k` bajo le da mucho más peso a la posición exacta, dejando que la
  lista que rankeó mejor un chunk (frecuentemente `keyword`, que ya venía con mejor MRR sola)
  domine la fusión en vez de diluirse contra `vector`. El hallazgo de que 50/60/100/200 dan
  resultados *idénticos* entre sí también tiene explicación mecánica, no es casualidad: con
  `candidate_k=10`, un `k` mucho mayor que el rango de posiciones (0-9) aplana las diferencias de
  `1/(k+rank+1)` entre puestos hasta volverlas irrelevantes para el orden final.
- **Default actualizado de 60 a 1** en `rrf()` (`src/ingestion.py`) y en el parámetro `rrf_k` de
  `_hybrid_search()` (`src/tools.py`) — cambia el comportamiento real de `rag_search()` en
  producción, no solo las métricas de evals. Métricas finales con el nuevo default (top_k=5):
  `hybrid` hit_rate=0.317, mrr=0.186 — supera a `vector` (0.231/0.141) y a `keyword`
  (0.300/0.197) en ambas métricas a la vez, sin trade-off. 7 tests de `test_rules.py` verificados
  en verde.
- **Capa 5B.4 completa (6/6 pasos).** Sesión 0 (prioridad desde 2026-07-13) cerrada. Sesión 1
  (5B.3, Postgres checkpointer) es la siguiente en la cola — pausada además por el curso en
  paralelo (LLM Zoomcamp M5, Monitoring, HW con entrega 2026-07-20); retomar después de esa
  entrega.

---

## 2026-07-18 — Capa 5B.4 paso 5: métricas hit_rate/mrr + bug de keyword search bilingüe encontrado y arreglado
**Commit:** `35a9ce5`

- **`evals/retrieval_metrics.py` nuevo:** porta el framework de M4 (`compute_relevance`/
  `hit_rate`/`mrr`/`evaluate`) parametrizado para `_vector_search`/`_keyword_search`/
  `_hybrid_search` de `src/tools.py` tal como están, usando `evals/ground_truth_retrieval.json`
  (520 preguntas) como dataset real. Adaptado del patrón de M4 en un punto: el acierto no se mide
  por `filename` (M4 evaluaba a nivel de página completa) sino por `chunk_ids` — la ventana exacta
  que vio el LLM al generar la pregunta (ver 5B.4 paso 4) — porque acá el chunking sí importa a
  nivel de precisión.
- **Hallazgo real corriendo la primera medición (top_k=5):** `keyword` hit_rate=0.008 — básicamente
  inútil — mientras `vector` daba 0.231. Investigado en vivo con Juan, con dos intentos fallidos
  antes del fix real:
  1. Hipótesis inicial (incorrecta): `_keyword_search` usaba `to_tsvector('spanish', ...)`, pero 8
     de los 11 PDFs del corpus son en inglés — cambiar a `'simple'` (sin stemming) pareció el fix
     obvio. Resultado: **empeoró** a hit_rate=0.0. Causa real: `plainto_tsquery` arma un AND de
     *todas* las palabras de la pregunta (15-20 palabras parafraseadas); con `'spanish'` al menos
     se eliminaban stopwords españolas del AND, con `'simple'` no — el AND terminaba exigiendo que
     palabras como "de"/"la"/"del" (que casi nunca aparecen en contenido en inglés) estuvieran en
     el chunk, condenando la búsqueda al fracaso en 8/11 documentos.
  2. Fix real (parte 1): reemplazar el AND de `plainto_tsquery` por un OR armado a mano
     (`palabra1 | palabra2 | ...` vía `to_tsquery`), para que cualquier término sume en `ts_rank`
     en vez de exigir que matcheen todos — mismo principio que `KeywordIndex` TF-IDF de
     `src/ingestion.py`. Con `'simple'` + OR: hit_rate 0.202, hybrid 0.269 (superando a vector por
     primera vez).
  3. **Juan detectó una duda metodológica válida antes de dar el hallazgo por cerrado:** con
     `'simple'` (sin stopwords) y OR, ¿no estaría el keyword search matcheando chunks solo por
     compartir "de"/"la"/"el"/"para" con la pregunta, sin relación real de contenido? Verificado
     empíricamente separando hit_rate por idioma del documento correcto: sin filtro de stopwords,
     documentos en español 0.4554 vs documentos en inglés 0.0101 — la brecha confirmaba
     contaminación por stopwords (compartidísimas en cualquier texto en español).
  4. Fix real (parte 2): `_STOPWORDS` (lista curada ES+EN) + `_build_or_tsquery()` en
     `src/tools.py` — filtra stopwords antes de armar el OR. Resultado, contra lo esperado: **no
     solo bajó el número de documentos en español, subieron los dos** (ES 0.4554→0.5893, EN
     0.0101→0.0811) — `ts_rank` no pondera por rareza (sin IDF), así que las stopwords no solo
     "hacían trampa" trayendo aciertos falsos, dominaban el ranking y tapaban la señal real de las
     palabras de contenido en ambos idiomas. La brecha ES/EN que queda ahora ya no es un artefacto:
     es el límite estructural real de keyword search monolingüe contra preguntas en español sobre
     documentos en inglés (solo matchean términos técnicos idénticos en ambos idiomas — modelos,
     unidades, protocolos).
  5. **Discutido con Juan y descartado como solución:** separar en dos RAGs por idioma. No aplica a
     este corpus porque no hay cobertura duplicada — los 5 PDFs de Rosemount y los 2 de
     Endress+Hauser *solo* existen en inglés, así que rutear una pregunta en español al índice
     "español" dejaría sin respuesta a cualquier consulta sobre esos documentos. La alternativa "de
     producción real" (columna `language` por chunk + `tsvector` por config detectado, en vez del
     `'simple'` global actual) queda anotada como mejora futura en POSPUESTO — sobre-ingeniería
     para 11 documentos, pero es el patrón correcto si el corpus creciera.
- **Métricas finales (top_k=5, 520 preguntas), progresión completa documentada para trazabilidad:**

  | config                          | vector      | keyword     | hybrid      |
  |----------------------------------|-------------|-------------|-------------|
  | `spanish` + AND (original)       | 0.231/0.141 | 0.008/0.005 | 0.229/0.142 |
  | `simple` + AND                   | 0.231/0.141 | 0.000/0.000 | 0.231/0.141 |
  | `simple` + OR sin stopwords       | 0.231/0.141 | 0.202/0.132 | 0.269/0.160 |
  | `simple` + OR + stopwords (final) | 0.231/0.141 | **0.300/0.197** | **0.312/0.180** |

  (hit_rate/mrr). Keyword solo termina superando a vector solo en ambas métricas — inesperado,
  consistente con un dominio de términos técnicos exactos (modelos, unidades, procedimientos
  cortos). Hybrid mejora el hit_rate sobre los dos, pero su MRR (0.180) queda *entre* vector y
  keyword sin superar al mejor individual (0.197) — señal concreta de que el RRF con `k=60`
  default no está sumando toda la ventaja de keyword, motiva el paso 6.
- **Efecto en producción, no solo en evals:** el fix de `_keyword_search` cambia el `rag_search()`
  real que usa el agente (mismo código, `src/tools.py`), no solo el script de métricas. Verificado
  que los 7 tests de `tests/test_rules.py` siguen pasando con la query SQL nueva.
- **Próximo paso concreto:** paso 6 de 5B.4 — barrido de `k` de RRF (1/50/100/200, patrón de la
  notebook de M4) contra el ground truth real, motivado por la brecha MRR hybrid vs keyword de
  arriba; decidir si el `k=60` default de `src/ingestion.py:104` se ajusta.

---

## 2026-07-17 — Capa 5B.4 paso 4: ground truth de retrieval generado con LLM + structured output
**Commit:** `15bf4bd` (commiteado el 2026-07-18, un día después de generado —
`evals/generate_ground_truth.py` y `evals/ground_truth_retrieval.json` quedaron untracked al
cierre de la sesión del 07-17)

- **Diseño discutido y acordado antes de programar (patrón de esta sesión: concepto antes de
  código):** portar el patrón de HW4 (Módulo 4) tal cual no calzaba — HW4 generaba preguntas por
  página (~4 chunks cada una, granularidad chica); acá cada documento tiene 223 chunks en promedio
  (rango real verificado contra Supabase: 57 a 485 chunks por PDF, 2451 total / 11 documentos).
  Generar preguntas por documento completo (como en un proyecto anterior de Juan en Valkimia, 10
  preguntas por documento) hubiera dejado el "acierto" en Hit Rate demasiado fácil de pasar
  (cualquier chunk del documento correcto cuenta). Resuelto con: sampling proporcional (1 anclaje
  cada 20 chunks, equiespaciado por documento → 130 ventanas reales, no ~123 estimadas a mano) +
  ventana de 2 chunks consecutivos por anclaje (cubre procedimientos cortos; criterio de "acierto
  vecino" ±1 justificado por el 20% de overlap de `CHUNK_STEP=800`/`CHUNK_SIZE=1000` — a esa
  distancia dos chunks ya no comparten texto, verificado con la aritmética del chunking real).
- **Categorías de pregunta:** factual, procedimental, inferencial, borde — decisión explícita de
  dejar afuera las preguntas "no soportadas" (out-of-scope) porque no tienen chunk correcto por
  construcción y sirven para un eval distinto (nivel agente, no retrieval); quedan anotadas como
  pendiente separado, no se generan hoy.
- **`evals/generate_ground_truth.py` nuevo:** lee `chunks` de Supabase agrupados por `source`,
  arma las ventanas de sampling, y por cada una llama a `client.beta.chat.completions.parse()`
  (mismo método de la API que Capa 4) con un modelo Pydantic (`GeneratedQuestions`) que fuerza la
  categoría de cada pregunta vía `Literal[...]`. El "chunk correcto" de cada pregunta queda
  definido por construcción: son los `chunk_ids` de la ventana que efectivamente vio el LLM, sin
  heurística posterior. Script manual (`python -m evals.generate_ground_truth`), mismo patrón que
  `scripts/ingest.py` — no lo llama la app ni CI.
- **Corrida real confirmada con Juan antes de ejecutar** (Supabase + OpenAI reales, costo pago):
  130 ventanas de anclaje sobre los 2451 chunks / 11 documentos → **520 preguntas** generadas en
  `evals/ground_truth_retrieval.json` (factual 138, procedimental 133, inferencial 128, borde 121).
- **Hallazgo sin resolver, anotado para revisar en el paso 5:** las 130 ventanas generaron
  exactamente 4 preguntas cada una, pese a que el prompt pedía explícitamente "entre 1 y 4, solo
  las categorías que el fragmento sostiene realmente" — no la cantidad forzada que se quería
  evitar. Se revisó a mano la primera ventana (`emerson_rosemount-2051_manual_en.pdf`, sección de
  advertencias de seguridad) y las 4 preguntas generadas ahí sí se leen como genuinas, no
  forzadas/repetidas — pero no se revisaron las 130. Queda pendiente ver si esto genera ruido en
  `hit_rate`/`mrr` cuando se corran de verdad (paso 5) — no se ajustó el prompt todavía, se decidió
  con Juan seguir con el dato real en vez de iterar a ciegas sobre una muestra de una sola ventana.
- **Próximo paso concreto:** paso 5 de 5B.4 — portar `hit_rate`/`mrr`/`evaluate()` a
  `evals/retrieval_metrics.py`, parametrizado para `_vector_search`/`_keyword_search`/
  `_hybrid_search` de `src/tools.py`, usando `evals/ground_truth_retrieval.json` como dataset real.

---

## 2026-07-15 — CI arreglado (job rules) + Capa 5B.4 paso 3: caso de uso real en system prompt y README
**Commit:** `c600192` (fix CI), `7da07f2` (paso 3) — de paso, se commiteó y pusheó el trabajo de
5B.4 pasos 1-2 y el handoff de M4 que llevaba días escrito sin subir (`8487502`, `aecfde5`;
contenido ya documentado en las entradas de 2026-07-11/13/14 de abajo, no se duplica acá)

- Al pushear hoy, corrió CI por primera vez desde la migración a Postgres de 5B.2 (el local venía
  varios commits adelante de `origin/main` desde hacía días). Aparecieron dos fallas en GitHub
  Actions — **ninguna causada por el push de hoy**, latentes desde antes:
  - **Job `rules`:** `ImportError` — `src/ingestion.py` creaba `_client = OpenAI()` a nivel de
    módulo, exigiendo `OPENAI_API_KEY` solo con importar `src.graph`/`src.tools`. Ese job corre a
    propósito sin API key (ver comentario en `ci.yml`). Arreglado con cliente perezoso
    (`_get_client()`, se crea recién dentro de `embed_texts()`).
  - Efecto secundario encontrado en el camino: `tests/test_rules.py::test_rag_search_contains_query_word`
    y `test_rag_search_returns_string` llaman `rag_search()` de verdad — dejaron de ser
    "deterministas sin API" desde que 5B.2 migró a Postgres, sin que nadie lo notara porque CI no
    había vuelto a correr desde entonces. Ahora usan `skip_if_no_rag_env()` (`pytest.skip` si falta
    `OPENAI_API_KEY`/`DATABASE_URL`), mismo patrón que `invoke_agent` en `conftest.py`. Verificado en
    los dos escenarios: sin esas env vars (5 passed, 2 skipped) y con `.env` real contra Supabase
    (7 passed).
  - **Job `evals`:** sigue fallando con `RuntimeError: Falta DATABASE_URL` — decidido no arreglarlo
    todavía. `rag_search()` necesita Postgres real desde 5B.2, pero `ci.yml` nunca sumó
    `DATABASE_URL` como secret de ese job. Conectarlo ahora no serviría: `golden_set.json` sigue
    siendo sobre LangGraph docs, corpus que ya no existe en Supabase (se truncó y reemplazó por el
    corpus de instrumentación en 5B.4 paso 2) — solo cambiaría el tipo de error, no daría señal
    real. Además, sumar esa credencial de producción como secret de CI es una decisión de seguridad
    aparte. Queda bloqueado por el paso 4 de 5B.4 (ground truth nuevo).
- **Capa 5B.4, paso 3 completo:** `SYSTEM_PROMPT` (`src/graph.py`) reescrito — pasa de ser el
  placeholder de Capa 1 a describir el caso de uso real (soporte técnico de instrumentación de
  campo para agua potable/saneamiento, Emerson/Rosemount + Siemens Sitrans + Endress+Hauser) con
  instrucción explícita de grounding (usar `rag_search` antes de responder, citar la fuente, no
  inventar datos de calibración/rangos/procedimientos) y de cuándo escalar con `create_ticket`.
  `README.md` reescrito de 2 líneas a: caso de uso (incluida la experiencia real de Juan como
  consultor técnico), cómo funciona el agente, nota de sourcing/compliance de los PDFs (exigida por
  `CORPUS_INSTRUMENTACION.MD`), y pasos para correrlo.
- **Decisión de alcance tomada antes de escribir:** las categorías nuevas de `create_ticket` que
  sugiere `CORPUS_INSTRUMENTACION.MD` (`falla_instrumento_campo`, etc.) quedan fuera de este paso —
  tocarían `src/schemas.py` y romperían 2 tests que hoy hardcodean `"question"`/`"bug"`
  (`tests/test_rules.py:69,77`). El paso 3 se cierra solo con system prompt + README.
- **Inconsistencia de documentación encontrada y corregida:** `ROADMAP.md` listaba `src/prompts.py`
  como archivo existente — nunca existió, el `SYSTEM_PROMPT` siempre vivió inline en `graph.py`.
  Corregido en "Estado actual del repo"; queda anotado como mejora pendiente (Juan prefiere separar
  los prompts a archivo(s) propio(s) a futuro).
- **Pendientes anotados, sin tocar hoy:** `.env.example` volvió a guardarse en UTF-16 (se había
  corregido a UTF-8 el 2026-07-01); confirmado con Juan que el repo de GitHub es privado hoy, así
  que la rotación de credenciales reales sigue sin ser urgente pero es condición explícita antes de
  hacerlo público.
- **Próximo paso concreto:** paso 4 de 5B.4 — generar ground truth con LLM + structured output
  (patrón HW4 de M4), usando los ejemplos de consulta de `CORPUS_INSTRUMENTACION.MD` como
  referencia de estilo. Es lo que en definitiva destraba el job `evals` de CI.

---

## 2026-07-14 — Capa 5B.4 (pasos 1 y 2 completos): PDFs descargados + ingesta real corrida contra Supabase
**Commit:** `aecfde5` (código: .gitignore, requirements.txt, scripts/ingest.py, src/ingestion.py,
rename docs/→archive/) + `8487502` (CORPUS_INSTRUMENTACION.MD) — ambos commiteados el 2026-07-15,
un día después de escrito

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
**Commit:** `8487502`, commiteado el 2026-07-15, dos días después de escrito

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
**Commit:** `8487502`, commiteado el 2026-07-15, cuatro días después de escrito

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
