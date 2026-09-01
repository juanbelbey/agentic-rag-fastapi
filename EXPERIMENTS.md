# EXPERIMENTS.md
# Historial de decisiones basadas en datos — agentic-rag-fastapi

Este archivo cuenta, en orden cronológico, cada mejora de calidad (retrieval y
generación) que se probó, midió y decidió con evidencia — no con intuición. Es
la versión "para contar" de lo que `ROADMAP.md`/`CHANGELOG.md` documentan con
todo el detalle técnico. Los números crudos de cada experimento están en
`evals/results/experiments_log.csv` (formato largo: fecha, área, experimento,
variante, métrica, valor) — pensado para alimentar un dashboard o gráfico más
adelante sin tener que releer este archivo a mano.

Convención: cada entrada dice qué se probó, qué se encontró, y qué se decidió
en base a eso. Cuando hay un hallazgo real (bug, sorpresa, dato que contradice
la hipótesis inicial), se marca explícito — es la parte más valiosa para
mostrar en una entrevista.

---

## Retrieval

### 2026-07-18 — Bug real en keyword search (hit_rate 0.008 → 0.300)

**Qué se probó:** portar hit_rate/mrr (patrón M4 de LLM Zoomcamp) a
`evals/retrieval_metrics.py` y correrlo contra las 520 preguntas reales de
`ground_truth_retrieval.json`.

**Qué se encontró:** keyword search prácticamente no funcionaba (hit_rate
0.008 — 4 de cada 500 preguntas). Causa: `plainto_tsquery` arma un AND de
todas las palabras de la pregunta; con preguntas parafraseadas de 15-20
palabras, cumplir el AND completo es casi imposible. Se agravaba porque el
corpus es bilingüe (8/11 PDFs en inglés) y la config `'simple'` no filtra
stopwords en español.

**Qué se decidió:** reescribir el armado de la query — OR a mano
(`_build_or_tsquery`) en vez de AND, más un filtro de stopwords ES/EN
(`_STOPWORDS`) para que el OR no matchee solo por palabras como "de"/"la"/"el".

**Resultado:** hit_rate 0.008 → 0.300, mrr → 0.197 (@top_k=5). El fix toca el
`_keyword_search` real que usa `rag_search()` en producción, no solo las
métricas.

### 2026-07-18 — Barrido de k de RRF (default 60 → 1)

**Qué se probó:** RRF (Reciprocal Rank Fusion) combina vector + keyword con
un parámetro `k` que amortigua diferencias de ranking. Se barrió
k=[1, 50, 60, 100, 200] contra las mismas 520 preguntas.

**Qué se encontró:** k=1 gana en hit_rate y mrr *a la vez* (sin trade-off que
resolver) — 0.3173/0.1858 contra 0.3115/0.1797 del resto. k=50/60/100/200 dan
resultados prácticamente idénticos entre sí: con `candidate_k=10`, un k mucho
mayor que el rango de posiciones aplana las diferencias de rank hasta
volverlas irrelevantes.

**Por qué importa el criterio:** se priorizó hit_rate sobre mrr a propósito —
el agente manda todo el top-k como contexto al LLM, no hay "posición #1" que
importe como en un buscador tradicional de resultados ordenados.

**Qué se decidió:** default de `rrf_k` cambiado de 60 a 1 en `rrf()`
(`src/ingestion.py`) y `_hybrid_search()` (`src/tools.py`) — cambia el
comportamiento real de producción, no solo las métricas.

### 2026-08-03 — Query rewriting: la brecha ES/EN (hit_rate hybrid +31%)

**Qué se probó:** el corpus mezcla español e inglés (8/11 PDFs en inglés);
las preguntas del golden set están en español. Se agregó
`_rewrite_query_impl()` — reescribe la query a inglés técnico con
`gpt-4o-mini` (T=0, `@lru_cache`) antes de armar el tsquery, dentro de
`_keyword_search_impl`. El vector search no lo necesita (el embedding ya es
multilingüe).

**Qué se encontró:** la reescritura no es un parche cosmético — mueve la
aguja en las dos búsquedas que dependen de ella indirectamente (keyword
standalone y hybrid, que usa keyword por dentro).

**Resultado (520 preguntas, sin re-correr el barrido de k — RRF fusiona solo
por ranking, no depende del texto de la query):**
- keyword: hit_rate 0.300 → 0.3288, mrr 0.197 → 0.2368
- hybrid (el que usa `rag_search()` real): hit_rate 0.317 → 0.4154 (**+31%**),
  mrr 0.186 → 0.2197

**Qué se decidió:** query rewriting queda en producción, gateado por
`LANGCHAIN_API_KEY` igual que el resto de la instrumentación opt-in.

### 2026-08-06 — `top_k` de producción (3 → 5)

**Qué se encontró revisando resultados de RAGAS:** `rag_search()` en
producción usaba `top_k=3`, pero las métricas de hit_rate/mrr de arriba se
midieron con `top_k=5` — producción recuperaba *menos* contexto que el
retrieval ya de por sí limitado que se estaba midiendo. Tres preguntas del
golden set (`g002`, `g016`, `g029`) llegaron a `context_precision` **y**
`context_recall` en 0.0 — ninguno de los 3 chunks recuperados era relevante.

**Qué se decidió:** subir el default a `top_k=5` para alinear producción con
lo medido. Ver sección RAGAS abajo para el resultado.

### 2026-09-01 — Umbral de abstención sobre score RRF: descartado

**Qué se probó:** `evals/critical_eval_set.json` (28 casos: 15 answerable
curadas del golden set + 13 unanswerable nuevas, verificadas contra los PDFs
reales con `pypdf` antes de escribirlas — ver `docs/PROJECT_CAPABILITY_AUDIT.md`,
gap de evaluation reliability). Hipótesis: el score RRF del mejor chunk que
devuelve `_hybrid_search()` separa preguntas con respuesta real en el corpus de
preguntas sin ella, y un umbral fijo sobre ese score puede activar abstención
en el agente. Barrido de 21 umbrales candidatos (0.00 a 1.00, paso 0.05) —
`evals/abstention_threshold.py`.

**Qué se encontró (hallazgo real, no positivo):** el score RRF **no separa
nada** — 26 de los 28 casos (answerable y unanswerable por igual) dieron
exactamente `0.5000`, sin importar si la pregunta tenía respuesta real en el
corpus o era sobre la capital de Francia. Ningún umbral del barrido logra un
punto intermedio: por debajo de 0.55 pasan el 100% de los casos (FN=0%,
FP=100%); en 0.55+ se cortan el 100% de los answerable junto con casi todos
los unanswerable (FN=100%). Es una función escalón, no una señal graduable.

**Por qué pasa:** `_vector_search` siempre devuelve sus `top_k` vecinos más
cercanos aunque ninguno sea realmente relevante — similitud coseno no tiene
concepto de "no hay match", solo "esto es lo menos lejano". Ese resultado
top-1 cae en rank 0 del lado vector, y RRF con `k=1` le asigna 1/(1+0+1)=0.5
por el solo hecho de rankear primero — **RRF mide posición en el ranking
fusionado, no similitud real**. La keyword search sí distingue mejor
(devuelve vacío si el tsquery no matchea nada), pero su aporte al score fusionado
es demasiado chico para mover la aguja salvo casos puntuales (`c018`: 0.6429).

**Qué se decidió:** NO implementar abstención basada en umbral de score RRF —
la señal no existe con la arquitectura de retrieval actual.

**Segundo intento, mismo día — distancia coseno cruda de `_vector_search`:**
mismo `critical_eval_set.json`, ahora con la distancia del vecino más cercano
(antes de fusionar con keyword search), barrido adaptado al rango real
observado (0.2534 a 0.8868). Esta vez sí hay una distribución continua real,
no un escalón — pero con un techo claro: el mejor punto de balance (umbral
≈0.44) todavía deja **5/15 (33%) falsos negativos** (answerable rechazadas) y
**3/8 (37.5%) falsos positivos** (unanswerable aceptadas). Ningún umbral logra
bajar los dos errores a la vez.

**Por qué falla en un subconjunto específico:** el umbral separa bien
`fuera_de_dominio` (`c022`, "capital de Francia", distancia 0.8868 — la más
alta de las 28) pero falla sistemáticamente en `producto_no_documentado`:
preguntas sobre el Rosemount 8800 o un Yokogawa EJA110 (`c019`/`c020`,
distancia ~0.38) quedan **más cerca** que varias preguntas answerable reales
(`c010`, 0.6273; `c012`, 0.4843) — porque el tema general (calibración de
transmisores de presión) es semánticamente similar aunque el producto
específico no esté documentado. La distancia coseno mide similitud temática,
no verifica si el hecho puntual (este modelo, este protocolo) está
realmente en el chunk.

**Qué se decidió:** ningún corte numérico puro (RRF o distancia) alcanza para
sostener la abstención por sí solo — la distancia ayuda con lo obviamente
fuera de dominio pero no distingue "mismo tema, producto equivocado", que es
justamente el caso más común de alucinación en este dominio. Sub-paso (e)
queda pendiente de decidir con Juan: la evidencia apunta a usar la distancia
como señal de apoyo (ej. anotar el chunk como "posible baja confianza" en el
output de la tool) combinada con instrucción explícita en el prompt para que
el LLM verifique el hecho puntual, no reemplazar el criterio semántico por un
umbral automático.

**Hipótesis intermedia de Juan, descartada con datos:** ¿usar el keyword
search actual como segunda señal (si el término específico no aparece por
keyword, descartar)? Se verificó con `_rewrite_query`/`_build_or_tsquery`
sobre 3 casos reales (Rosemount 8800, Yokogawa EJA110, FieldSense FS-200): el
tsquery arma un OR de TODAS las palabras de la pregunta reescrita
(`'pressure | range | rosemount | 8800'`), así que matchea por palabras
genéricas del dominio ("pressure", "range") sin que el término específico
("8800") haya aparecido en ningún chunk — el rank resultante (0.0667) fue
más alto que el de una pregunta real y válida (`c001`, rank 0.0533). El OR
del keyword search (elegido a propósito para el bug de preguntas
parafraseadas, ver arriba) no sirve para aislar términos específicos sin
modificarlo — necesitaría un chequeo nuevo y separado (extraer el término
identificador y verificar su presencia literal), no reusar el keyword search
tal como está. Marcado como candidato futuro, no construido.

### 2026-09-01 — Comportamiento real del agente completo ante el critical set

**Qué se probó:** en vez de seguir midiendo señales de retrieval aisladas, se
corrió el agente COMPLETO (`graph.invoke()`, LLM + `rag_search` reales) contra
las 28 preguntas de `critical_eval_set.json` (`evals/critical_set_agent_check.py`)
para ver si el criterio semántico del LLM (sin ningún cambio de prompt
todavía) ya resuelve el problema de abstención en la práctica.

**Qué se encontró (revisión manual de las 13 respuestas a preguntas
unanswerable):**
- **`relacionado_ausente` (3/3 correctas):** el agente declina limpio en los
  3 casos (Modbus, CANopen, Bluetooth) sin inventar nada — "no soporta
  comunicación Modbus... es compatible con HART", etc. El criterio semántico
  ya funciona bien acá.
- **`producto_no_documentado` (1/3 correcta, 1 dudosa, 1 alucinación real):**
  Yokogawa EJA110 → declina y escala con `create_ticket` (correcto). Rosemount
  8800 → dice que no está explícito pero igual generaliza ("los transmisores
  de la serie Rosemount suelen tener rangos que..."). **FieldSense FS-200
  (marca ficticia) → alucinación real: responde con instrucciones de
  mantenimiento de OTRO producto (un separador de un manual Siemens) y las
  presenta como propias del FS-200, citando la fuente real como si
  respaldara la respuesta inventada.**
- **`fuera_de_dominio` (1/2 — decisión de producto, no bug):** la pregunta de
  Windows 11 se rechaza bien; la de "capital de Francia" la responde
  (correctamente) y recién después aclara que su foco es soporte técnico.
  No es un bug, es una decisión de alcance sin resolver: ¿debería negarse a
  cualquier pregunta fuera de dominio aunque sea trivia inofensiva?
- **`ambigua` (2/3 correctas):** "¿cómo lo arreglo?" y "¿qué falla tiene el
  equipo?" piden aclaración correctamente. "¿Cuál es la configuración
  correcta?" NO pide aclaración — responde con procedimientos de 3
  fabricantes distintos sin preguntar cuál corresponde.
- **`mixta` (0/2 — el hallazgo más serio):** SITRANS P300 (mide presión, no
  caudal) → el agente afirma que sí mide caudal, con unidades inventadas,
  citando el manual real como fuente de una capacidad que el producto no
  tiene. Rosemount 3051 (rango real + "modo de comunicación satelital"
  inventado) → responde bien la parte real pero ignora por completo la parte
  inventada (ni la confirma ni la desmiente) **y además genera una URL de
  cita corrupta** (un string de `-0-0-0-0-...` repetido cientos de veces) —
  hallazgo separado, no relacionado con abstención: el prompt pide "citá la
  fuente" pero `RAGResult.source` es solo un nombre de archivo, nunca una
  URL, y el modelo fabrica un link que no existe en ningún lado del contexto.

**Qué se decidió:** el criterio semántico actual SÍ funciona para el caso más
fácil (tema totalmente ausente) pero falla de forma real en 3 patrones
específicos: (1) generalizar desde productos similares en vez de decir "no
tengo el dato de este modelo puntual", (2) no pedir aclaración ante preguntas
genuinamente ambiguas con múltiples interpretaciones válidas, (3) verificar
solo una parte de una pregunta con múltiples afirmaciones y quedarse callado
o inventar en el resto. Sub-paso (e) se enfoca en reforzar el prompt contra
estos 3 patrones puntuales (con ejemplos concretos, no instrucciones vagas) +
corregir la instrucción de citación para que nunca fabrique una URL. Política
de producto decidida con Juan: `fuera_de_dominio` se rechaza siempre, sin
excepción (ni trivia inofensiva). Resultados completos en
`evals/results/2026-09-01/17-33-21_critical_set_agent_check.json`.

**Validación del fix (mismo día) — 4 prompt agregados a
`prompts/system_prompt_direct_answer.txt`:** (1) no generalizar desde
productos similares, (2) pedir aclaración ante ambigüedad real, (3) verificar
cada parte de una pregunta multi-afirmación por separado, (4) citar solo
nombre de documento, nunca URL. Re-corridos los 6 casos que habían fallado:

| Caso | Antes | Después |
|---|---|---|
| `c019` (Rosemount 8800) | Generalizaba desde otros Rosemount | ✅ Declina limpio, sin generalizar |
| `c021` (FieldSense FS-200) | Alucinaba mantenimiento de otro producto | ✅ Declina y escala con `create_ticket` |
| `c022` (capital de Francia) | Respondía y después redirigía | ✅ Rechaza directo, sin responder |
| `c026` (configuración sin especificar) | Respondía por los 3 fabricantes | ✅ Pide aclaración |
| `c027` (Rosemount 3051 + "modo satelital" inventado) | Ignoraba la parte inventada en silencio, + URL corrupta | ⚠️ URL corregida (cita solo el nombre del PDF), pero ahora **responde la parte inventada** equiparándola a "multidrop" (real) como si validara la premisa de "modo satelital" — sigue mal, de otra forma |
| `c028` (SITRANS P300 mide caudal) | Afirmaba que sí mide caudal, con unidades inventadas | ❌ Sigue afirmando que mide caudal (solo agrega "no se especifican las unidades exactas") |

**Resultado: 4/6 arreglados, la categoría `mixta` (pregunta con una parte real
y una inventada en la misma consulta) sigue sin resolverse** — el prompt
engineering solucionó bien "tema totalmente ausente", "ambigüedad" y
"generalización entre productos", pero no alcanza para separar de forma
confiable una afirmación verdadera de una falsa dentro de la MISMA pregunta.
Gap real y documentado, no oculto: la Fase 4 mejora la abstención de forma
medible sin resolverla al 100% — mencionar esto explícitamente en cualquier
conversación sobre el proyecto (mismo criterio que "no usar production-ready
sin evidencia suficiente", ver `docs/PROJECT_CAPABILITY_AUDIT.md`).

---

## Generación (prompt, modelo, temperatura)

### 2026-07-27 — Primera corrida sobre el corpus real

Primera vez que el LLM-as-judge (`relevance_evaluator`/`accuracy_evaluator`)
corrió sobre las 48 preguntas del golden set de instrumentación (reemplazó al
golden set viejo de LangGraph docs). Resultado: relevancia 4.44/5, accuracy
3.88/5, 85% de respuestas con cita, 4.08 pasos promedio. Quedó un hallazgo sin
investigar: 5/48 preguntas respondibles con el manual terminaban en
`create_ticket` en vez de una respuesta directa — es la semilla del
experimento de prompt de abajo.

### 2026-08-01 — Comparación prompt × modelo (48 casos, luego 56)

**Qué se probó:** 4 combinaciones aisladas (metodología: un solo cambio de
variable por corrida) — prompt baseline vs. uno nuevo (`direct_answer`, que
prioriza responder directo con `rag_search` antes que escalar) × `gpt-4o-mini`
vs. `gpt-4.1-nano`.

**Primera corrida (48 casos, solo preguntas contestables):**

| Variante | Relevancia | Accuracy | Citas | Tickets |
|---|---|---|---|---|
| baseline_mini (producción) | 4.40/5 | 3.60/5 | 81% | 9/48 |
| baseline_nano | 4.90/5 | 4.27/5 | 92% | 0/48 |
| direct_answer_mini | 4.62/5 | 3.94/5 | 94% | 2/48 |
| direct_answer_nano | 4.75/5 | 4.08/5 | 94% | 0/48 |

`gpt-4.1-nano` medía mejor en las 4 dimensiones y ~30% más barato — decisión
obvia, en apariencia.

**El freno:** Juan objetó el criterio — "si me quedo con el modelo que mide
peor solo porque ya lo probamos, no es un criterio, es sesgo". Se extendió el
golden set con 8 casos de escalamiento reales (preguntas que el corpus NO
cubre — el agente debe escalar con `create_ticket`, no inventar) y se
re-corrió con las 56 preguntas + `tool_call_evaluator` nuevo (code-based, no
LLM-judge: mide si escaló o no, no compara texto).

**Segunda corrida (56 casos, con escalamiento):**

| Variante | Relevancia | Accuracy | Citas | Tool-call (escalamiento) |
|---|---|---|---|---|
| baseline_mini | 4.43/5 | 3.69/5 | 77% | 8/8 (100%) |
| baseline_nano | 4.68/5 | 4.12/5 | 84% | 7/8 (88%) |
| **direct_answer_mini** | **4.77/5** | **4.17/5** | 84% | **8/8 (100%)** |
| direct_answer_nano | 4.80/5 | 4.23/5 | 88% | 6/8 (75%) |

**Hallazgo que decidió todo:** nano falló los *mismos* 2 casos de
escalamiento en ambas variantes de prompt — no era ruido, era sistemático
(un transmisor Yokogawa fuera del corpus, un caudalímetro de marca genérica).
En vez de escalar, inventó datos citando "la documentación consultada" para
equipos que el corpus no cubre — justo lo que el `SYSTEM_PROMPT` prohíbe.
`gpt-4o-mini` no falló ni un caso.

**Decisión final: `direct_answer_mini`.** No por costumbre — ventaja medible
y reproducible en la dimensión de mayor riesgo del dominio (no inventar en
zona gris).

### 2026-08-01 — Barrido de temperatura

**La pregunta de Juan, ya con el modelo elegido:** "¿no deberíamos fijar la
temperatura para que invente menos?" — válida: nunca se había fijado
(corría al default implícito de OpenAI, 1.0).

| Temp | Accuracy | Estabilidad (spread) |
|---|---|---|
| 0.0 | 4.00/5 | 0.04 |
| **0.3** | **4.07/5** | **0.10** |
| 0.6 | 4.12/5 | 0.05 |
| 1.0 (default anterior) | 4.03/5 | **0.18** |

**Qué se encontró:** la aparente tendencia "más temperatura = más accuracy"
no se sostiene con comparación pareada — es ruido del LLM-judge sobre 48
preguntas, no una relación causal. Lo único que sí es señal limpia: **T=1.0
es la más inestable de las cuatro**, confirmando la sospecha de que no
fijarla agregaba ruido innecesario.

**Decisión final: `temperature=0.3`** — punto medio entre estabilidad
(spread 0.10, muy por debajo del 0.18 de referencia) y tasa de citas (86%
vs. 78% a T=0.0).

### 2026-08-05 / 2026-08-06 — RAGAS: faithfulness, answer relevancy, context precision/recall

**Qué se probó:** 4 métricas de RAGAS sobre los 48 casos con `expected_answer`
del golden set, con `direct_answer_mini` + T=0.3 ya en producción. `contexts`
tomados de lo que el agente realmente vio (la tool call real a `rag_search`
en la traza), no de una llamada aparte — juzga contra la realidad, no contra
un retrieval hipotético.

**Bugs reales encontrados corriendo el script de punta a punta** (no solo
leyendo la API de RAGAS): el `.score()` sync exige cliente `AsyncOpenAI`, no
`OpenAI`; sin `max_tokens` explícito la salida estructurada de `faithfulness`
se truncaba; el primer `try/except` no cubría el `invoke_agent()` completo y
una corrida se perdió entera por un error transitorio de Postgres a mitad de
una tool call.

**Resultado con `top_k=3` (2026-08-05):** faithfulness 0.783, answer_relevancy
0.708, context_precision 0.571, context_recall 0.679 (46/48 puntuados — 2
casos sin contexts recuperados).

**Lectura:** faithfulness/answer_relevancy (generación) están razonablemente
bien; context_precision/context_recall (retrieval) son las dos métricas
flojas — el LLM responde bien con lo que le dan, el problema es lo que le
dan. Coincide con el hit_rate hybrid ya conocido (0.317-0.415 según la
versión), y con 3 casos (`g002`, `g016`, `g029`) donde ninguno de los 3 chunks
recuperados era relevante.

**Resultado con `top_k=5` (2026-08-06):** faithfulness 0.776, answer_relevancy
0.718, context_precision 0.563, context_recall **0.773** (46/48 puntuados).

| Métrica | top_k=3 | top_k=5 | Δ |
|---|---|---|---|
| faithfulness | 0.783 | 0.776 | -0.007 |
| answer_relevancy | 0.708 | 0.718 | +0.010 |
| context_precision | 0.571 | 0.563 | -0.008 |
| context_recall | 0.679 | **0.773** | **+0.094** |

**Lectura:** el trade-off es el esperable — más contexto recuperado sube la
probabilidad de incluir el chunk correcto (`context_recall` +0.094, ~14%
relativo, la mejora real del experimento) a costa de diluir un poco la
proporción de chunks relevantes sobre el total (`context_precision` -0.008,
dentro de ruido). `faithfulness`/`answer_relevancy` se mantienen
prácticamente planas — el LLM no se confunde por tener 2 chunks más, ni gana
ni pierde ahí. Como `context_recall` era la métrica más floja de las cuatro y
la ganancia es clara mientras que la pérdida en precision es ruido, el cambio
queda como mejora neta. **Decisión: `top_k=5` default en producción.** El
techo real de retrieval sigue estando en `context_precision`/hit_rate — para
subirlo de verdad hace falta reranking, no otro ajuste de `top_k`.

---

## Próximos experimentos candidatos (no ejecutados todavía)

- Reranking (cross-encoder sobre el pool de `candidate_k=10` antes de cortar
  a `top_k`) — ataca la causa de fondo de `context_precision` bajo (RRF
  fusiona por ranking, no por relevancia semántica fina). Más impacto que
  subir `top_k`, pero es un componente nuevo (latencia + costo).
- Revisar granularidad de chunking (`CHUNK_SIZE=1000`/`CHUNK_STEP=800`) —
  chunks grandes pueden diluir la precisión del embedding.
- Sweep de `gpt-4.1-nano` a temperatura baja (0.0/0.3) — anotado en
  `ROADMAP.md`, curiosidad de si su falla de escalamiento es de muestreo o de
  conocimiento del modelo. No cambia la decisión ya tomada salvo resultado
  sorprendente.
