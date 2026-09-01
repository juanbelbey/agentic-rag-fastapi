# Case study — agentic-rag-fastapi

Un sistema de soporte con RAG híbrido sobre manuales técnicos de instrumentación de campo, con un agente LangGraph que decide cuándo buscar en la documentación y cuándo escalar a un ticket, evaluado con tres métricas complementarias y con un dashboard de costo/latencia propio. Demo vivo: `agentic-rag-fastapi.streamlit.app`.

## El problema

Un caso de uso realista de soporte técnico: un usuario pregunta sobre instrumentación de campo (transmisores de presión, temperatura, flujo), el sistema busca en 11 manuales de fabricantes reales, responde con citas, y si la pregunta corresponde a una falla o un caso de escalamiento, crea un ticket. El corpus mezcla español e inglés (manuales oficiales vienen mayormente en inglés, las preguntas de usuario en español) — esa mezcla terminó siendo la fuente de las decisiones más importantes del proyecto.

## Decisiones basadas en datos, no en intuición

Cada cambio de retrieval o generación se midió antes de adoptarse, con un dataset propio de 520 preguntas (factual/procedimental/inferencial/borde) ancladas a chunks reales del corpus:

- **Keyword search AND→OR con stopwords:** el `plainto_tsquery` original de Postgres (AND de todas las palabras) era inviable contra preguntas parafraseadas de 15-20 palabras. Cambiar a OR con una lista de stopwords ES/EN llevó el `hit_rate` de 0.008 a 0.300 — el salto más grande del proyecto, con causa diagnosticada, no un ajuste a ciegas.
- **Query rewriting a inglés antes del FTS:** con 8 de 11 PDFs en inglés y las preguntas siempre en español, reescribir la query a inglés técnico antes del keyword search llevó el `hit_rate` híbrido de 0.317 a 0.4154 (+31% relativo). El vector search no necesitó este paso — el embedding ya es multilingüe.
- **RRF k=1 vs. el k=60 típico del paper:** un barrido completo (k=1/50/60/100/200) contra las 520 preguntas mostró que k=1 gana, pero por un margen marginal (~0.6 puntos porcentuales en hit_rate y MRR). Vale como ejemplo de metodología — comparar antes de adoptar un default — no como el hallazgo central del proyecto.
- **Prompt, modelo y temperatura de producción** se eligieron comparando variantes de forma aislada (una variable por corrida, `compare_prompts.py`/`compare_temperature.py`) contra el mismo golden set, no por preferencia.

## Cómo se evalúa la calidad

Tres métricas complementarias, no una sola:
- **LLM-as-judge sin referencia** (`relevance`, 1-5): ¿la respuesta es útil?
- **LLM-as-judge con referencia** (`accuracy`, 1-5): ¿coincide técnicamente con la respuesta esperada?
- **RAGAS** (faithfulness, answer relevancy, context precision/recall): evaluado contra los *contexts que el agente realmente vio* en su traza, no contra una llamada aislada al retrieval — evita el error común de medir retrieval y generación con contextos distintos.

Resultados reales guardados (56 casos del golden set, prompt/modelo de producción): `avg_relevance=4.77/5`, `avg_accuracy=4.02/5`, `tool_call_rate=100%` (8/8 casos de escalamiento), `citation_rate=86%`. RAGAS sobre los 48 casos con respuesta de referencia: `faithfulness=0.776`, `answer_relevancy=0.718`, `context_precision=0.563`, `context_recall=0.773`.

Vale una aclaración honesta: `relevance` y `answer_relevancy` de RAGAS terminan preguntando algo parecido (¿la respuesta atiende la pregunta?, ambas sin comparar contra una referencia) — el overlap conceptual es real. `accuracy` (contra la respuesta esperada) y `faithfulness` (contra el contexto recuperado, detecta alucinación) sí miden ejes distintos y complementarios.

## Arquitectura del agente

Un grafo de LangGraph construido a mano (no un `create_react_agent` prearmado): dos nodos, `agent` y `tools`, con routing condicional sobre si el modelo pidió usar una tool. Persistencia de conversación real con `PostgresSaver` por `thread_id` (verificado contra Supabase en producción, no un `MemorySaver` de demo). El grafo está parametrizado por `system_prompt`/`model_name`/`temperature` — es lo que permitió comparar variantes reales sin duplicar código, sosteniendo las decisiones de la sección anterior.

## Observabilidad de negocio, no solo tracing

Además de LangSmith (tracing opt-in, best-effort), el sistema registra latencia, tokens y costo estimado por request en una tabla propia (`chat_logs`), y feedback de usuario (👍/👎) ligado a cada respuesta. Un dashboard con Altair muestra esto de forma independiente de terceros — funciona aunque LangSmith esté caído o rate-limited.

## Qué no está resuelto todavía (honesto, no vendido)

- **El sistema no sabe decir "no sé".** Si el retrieval devuelve chunks irrelevantes con score bajo, igual se presentan como evidencia — no hay umbral de confianza ni casos de "sin respuesta" en el dataset de evaluación.
- **La resiliencia del agente depende casi enteramente de los defaults de LangGraph** — sin retry/backoff ante fallos transitorios de OpenAI o Postgres, sin límite de recursión propio.
- **El camino de error no deja rastro.** Si `/chat` falla, no hay logging estructurado ni tasa de error visible en el dashboard — el sistema observa el éxito, no el fallo.
- **Los números de retrieval reportados no son reproducibles por un tercero** sin el corpus real, que es copyrighted y no se commitea. La metodología sí es reproducible (hay un corpus sintético equivalente para correr el pipeline de ingesta de punta a punta).
- **El golden set de evaluación es LLM-generado, sin revisión humana documentada** — útil para desarrollo, pero no calificaría como "human-verified ground truth" ante una pregunta directa.

## Por qué esto importa

El diferencial de este proyecto no es "armé un RAG" — es que cada pieza compleja (retrieval híbrido, evaluación multi-métrica, experimentación aislada por variable) está ahí porque midió algo y esa medición cambió una decisión real de producción, documentada en `EXPERIMENTS.md`. Lo que falta —abstención, reliability del agente, observabilidad de fallos— no es una sorpresa: está identificado, priorizado, y es exactamente el tipo de trabajo que separa un prototipo bien evaluado de un sistema listo para producción.
