# Posicionamiento de servicios GenAI — evidencia de agentic-rag-fastapi

Qué servicios puede respaldar hoy el trabajo demostrado en `agentic-rag-fastapi`, con qué evidencia concreta y con qué límite honesto — para no prometer lo que el repo todavía no sostiene.

## Servicios que el repo respalda hoy

| Servicio | ¿Se puede ofrecer hoy? | Evidencia | Límite a comunicar |
|---|---|---|---|
| **A. Auditoría de sistemas RAG** | Sí | Metodología replicable, la misma usada para auditar este propio proyecto | Validada sobre este único proyecto/corpus — sin track record todavía sobre stacks o corpus ajenos. No ofrecer como "sin limitaciones" |
| **B. Optimización de retrieval** | Sí | Baseline→mejoras medidas y documentadas (fix AND→OR +37pp de hit_rate, query rewriting +31% relativo) | Cualquier mejora propuesta (ej. reranking) va acompañada de la medición antes de prometer el resultado — no asumir ROI sin correr el experimento primero |
| **C. Pipeline de evaluación RAG/LLM** | Sí, con alcance acotado | Evaluación multi-métrica real (LLM-as-judge sin/con referencia + RAGAS) | Sin gates de CI ni golden set con revisión humana — es evaluación ad-hoc bien instrumentada, no QA continuo con gates |
| **D. Asistente documental / RAG prototype** | Sí | El proyecto entero es esto, con deploy vivo | — |
| **E. Desarrollo de componentes GenAI para otro equipo** | Sí, con alcance acotado | Retrieval/evaluation/agent/tool/API, cada uno con evidencia propia por separado | La pieza de reliability/observabilidad de fallos no tiene la misma evidencia que el resto — no ofrecerla sin aclarar el gap |
| **F. Agent observability / evaluation** | Sí, con alcance acotado | LangGraph + LangSmith + métricas propias reales | Alerting/error-tracking todavía no existe — no prometerlo como parte del servicio |

## Posicionamiento recomendado

Tres formulaciones, cada una con su evidencia y el rol al que apunta:

1. **"Diseño y evalúo sistemas RAG híbridos con decisiones basadas en datos, desde retrieval hasta observabilidad de negocio."**
   Enfatiza RAG + evaluación + rigor experimental. Roles: RAG Engineer, Applied AI Engineer. Servicios: A, B, C, D.

2. **"Construyo agentes con LangGraph con estado y routing propios, evaluados con LLM-as-judge y RAGAS."**
   Enfatiza agentes + evaluación combinados. La orquestación está sólida (grafo armado a mano, persistencia real verificada); deliberadamente no se afirma nada sobre resiliencia de producción — ese gap es real y está identificado, no se oculta. Roles: GenAI Engineer, AI Solutions Engineer. Servicios: C, E, F.

3. **"Sumo criterio de evaluación y medición a equipos que ya construyen con LLMs, sin necesitar liderar la arquitectura completa."**
   Enfatiza colaboración como especialista secundario en evaluación dentro de equipos más grandes — AI Evaluation como especialización defendible del perfil, sin inflarla a "es lo único que hago". Roles: colaborador en software factories/agencias/consultoras. Servicios: C, F.

## Qué no ofrecer todavía sin aclarar el gap

- **"Production-ready"** sin matices — no hay evidencia suficiente de manejo de errores, seguridad ante carga, o recovery para sostenerlo.
- **Resiliencia de agentes** como si ya estuviera resuelta — hoy depende casi enteramente de los defaults del framework (sin retry/backoff, sin límite de recursión propio).
- **Observabilidad de fallos / alerting** como parte de un paquete de "agent observability" — el repo demuestra observabilidad de negocio (costo/latencia/uso) real, no de incidentes.
- **Reranking u otras mejoras de retrieval sin medir primero** — el propio proyecto aplica el estándar de "medir antes de construir" en sus propias decisiones (RRF, query rewriting); ofrecer una mejora sin ese mismo estándar sería inconsistente con la evidencia que la respalda.
- **Auditorías de RAG "sin limitaciones"** — la metodología es sólida, pero está probada sobre un solo proyecto propio; no hay track record todavía sobre corpus o stacks de terceros.
