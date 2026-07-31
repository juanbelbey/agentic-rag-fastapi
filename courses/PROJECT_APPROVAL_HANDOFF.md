# Handoff — Proyecto final LLM Zoomcamp 2026 (rumbo a aprobación)

> Generado desde el repo `llm-zoomcamp-2026-code` el 2026-07-28. Pegar este archivo completo en la sesión de Claude del repo `agentic-rag-fastapi`. El objetivo de este documento es que esa sesión (que ya conoce el código del proyecto en detalle) tenga todo lo que necesita del lado del curso para auditar el repo contra los criterios oficiales y armar un plan de acción concreto.

---

## 1. Contexto y decisión ya tomada

- Juan cursa el **LLM Zoomcamp 2026** (DataTalks.Club) y va a entregar **`agentic-rag-fastapi` tal cual** como proyecto final del curso — no arma un repo separado.
- **Deadlines:** primer intento **03/08/2026**, segundo y último intento **10/08/2026**. El objetivo real acordado es **cerrar para el 10/08**, usando el 03/08 como intento oportunista *solo si* para esa fecha el repo ya cubre la mayoría de los criterios objetivos (ver nota al final sobre por qué no hay riesgo en intentarlo antes si no está listo).
- Dataset: Juan ya tiene uno definido (no es el FAQ de DTC — está prohibido explícitamente por las reglas del curso, ver sección 3).
- El repo es privado hoy. **Para la entrega y el peer review el curso pide un link público de GitHub + un commit hash** — confirmar visibilidad antes de la entrega.

---

## 2. Criterios de evaluación oficiales (fuente: `project.md` del repo del curso, DataTalksClub/llm-zoomcamp)

Puntaje objetivo, 9 criterios, cada uno 0–2 puntos (máx 18) + best practices (máx +3) + bonus (máx +5):

| Criterio | 0 pts | 1 pt | 2 pts |
|---|---|---|---|
| **Problem description** | No descrito | Descrito pero breve/confuso | Bien descrito, queda claro qué problema resuelve |
| **Retrieval flow** | Sin knowledge base ni LLM | Solo LLM, sin knowledge base | Knowledge base + LLM en el flujo |
| **Retrieval evaluation** | Sin evaluación | Se evalúa un solo enfoque de retrieval | Se evalúan múltiples enfoques y se usa el mejor |
| **LLM evaluation** | Sin evaluación | Se evalúa un solo enfoque (ej. un prompt) | Se evalúan múltiples enfoques y se usa el mejor |
| **Interface** | Ninguna forma de interactuar | CLI, script o notebook | UI (ej. Streamlit) o API (ej. FastAPI) o web app |
| **Ingestion pipeline** | Sin ingesta | Semi-automatizada (notebook/script) | Automatizada con herramienta dedicada (Kestra, dlt, Airflow, Prefect) |
| **Monitoring** | Sin monitoring | Feedback de usuario **O** dashboard | Feedback de usuario **Y** dashboard con ≥5 gráficos |
| **Containerization** | Sin contenedores | Dockerfile de la app **O** docker-compose solo de dependencias | Todo en docker-compose |
| **Reproducibility** | Sin instrucciones, o falta data | Instrucciones incompletas, o completas pero falta data | Instrucciones claras, dataset accesible, corre fácil, versiones de dependencias especificadas |

**Best practices (+1 c/u, máx +3):**
- [ ] Hybrid search (texto + vector, al menos evaluado)
- [ ] Document re-ranking
- [ ] Query rewriting

**Bonus (no cubierto en el curso):**
- [ ] Deploy a la nube (+2)
- [ ] Hasta +3 puntos extra a discreción del reviewer por algo destacado

**Reglas duras:**
- El dataset **no puede ser** el FAQ de DTC usado en los módulos del curso.
- No se puede reusar en full/parte un proyecto de otro curso/bootcamp, ni el propio proyecto de una edición anterior del curso, ni reusar el intento 1 sin cambios como intento 2 si el intento 1 ya aprobó. Esto **no aplica** al caso de Juan (dataset propio, primera vez).
- README debe explicar el problema, el dataset y el flujo asumiendo que el lector **no vio el curso**. Debe mencionar explícitamente los criterios de evaluación (para que el reviewer los ubique fácil). Agregar screenshots de la UI/dashboard si ayuda.

**No encontré en `project.md` un puntaje mínimo explícito para aprobar** — probablemente está en la plataforma del curso (`courses.datatalks.club`). Mientras Juan no confirme ese número, la apuesta más segura es cubrir los 9 criterios objetivos al máximo (18 pts) antes de invertir tiempo en bonus.

**Peer review:** para sumar puntos también hay que evaluar 3 proyectos de compañeros (+3 c/u). Es una acción de Juan en la plataforma del curso, no algo que dependa del código — mencionarlo pero no bloquea el trabajo técnico.

---

## 3. Qué instrucción darle a Claude en la sesión del repo flagship

1. **Auditar el repo actual contra cada uno de los 9 criterios objetivos + las 3 best practices** de la tabla de arriba, dando un puntaje estimado hoy por criterio (0/1/2) con la razón concreta.
2. Priorizar el plan de acción por **criterios en 0 primero** (más barato subir de 0→1 que de 1→2 en la mayoría de los casos), luego los que están en 1 con camino claro a 2.
3. Confirmar explícitamente:
   - Dataset ≠ FAQ de DTC ✓ (ya resuelto, Juan lo confirmó)
   - Visibilidad del repo: hoy privado → debe pasar a público antes de la entrega
   - README: ¿ya explica el problema/dataset/flujo sin asumir que el lector vio el curso? ¿Menciona los criterios de evaluación?
4. Armar un plan concreto con fecha límite **10/08/2026**, dejando el bonus (deploy a cloud) para después de asegurar los 9 criterios + best practices.
5. Si para el 03/08 ya se cubren la mayoría de los criterios, evaluar con Juan si conviene entregar como primer intento (no hay downside: si no aprueba, se puede seguir mejorando para el 10/08 — la regla de "no reusar intento 1 como intento 2" solo aplica si el intento 1 **aprobó**).

---

## 4. Contenido de referencia nuevo del curso (Módulos 6 y 7 — no cubierto en M1-M5)

Estos dos módulos no tienen homework en la edición 2026: son material de referencia directamente apuntado a preparar el proyecto final. Bajados a `M6-lessons/` y `M7-lessons/` en este repo.

### M6 — Best Practices (`M6-lessons/`)
- `02-hybrid-search.md` — combinar texto + vector (esto ya está cubierto conceptualmente por M2/M4 del curso, que Juan ya hizo — RRF, hit rate, MRR)
- `03-reranking.md` — **nuevo, no visto todavía**: re-rankear resultados de retrieval con un segundo modelo antes de pasarlos al LLM. Es uno de los 3 best-practice checkboxes del proyecto.
- `04-langchain.md` — mismos conceptos implementados con LangChain en vez de a mano.

### M7 — End-to-End Project Example (`M7-lessons/`)
Walkthrough completo de un proyecto real (`alexeygrigorev/fitness-assistant`) que cubre exactamente los mismos criterios de evaluación. Útil como referencia de implementación concreta, módulo por módulo:
- `02-evaluating-retrieval.md` — ground truth, Hit Rate, MRR, boosting (Juan ya implementó esto en M4, es reusable tal cual sobre el dataset del proyecto)
- `03-evaluating-rag.md` — LLM-as-a-Judge, comparar modelos/prompts (cubre el criterio "LLM evaluation")
- `04-interface.md` — Flask API + pipeline de ingesta + estructura de proyecto (cubre "Interface" e "Ingestion pipeline")
- `05-monitoring.md` — Docker Compose + logging a Postgres + Grafana (cubre "Monitoring" y "Containerization")
- `07-chunking.md` — estrategias de chunking para textos largos, útil si el dataset de Juan no es formato Q&A

También se bajó `M7-lessons/project.md` (copia local del criterio oficial, por si se pierde el link).

---

## 5. Nota final

Este documento **no** reemplaza el `HANDOFF_CONTEXT.md` de conceptos por módulo (M1–M5) que ya se viene pasando al repo flagship — es un documento aparte, enfocado puntualmente en qué hace falta para que el proyecto **apruebe** antes del 10/08. Una vez aprobado el curso, Juan sigue mejorando el repo con más calma (deploy a cloud, bonus points, pulido general).
