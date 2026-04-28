# COPILOT_STRATEGY.md

## Quién soy y qué estoy construyendo

Soy Juan, AI Engineer en formación. Trabajo como GenAI Solutions Developer usando plataformas low-code (GEAI / Globant Enterprise AI). Mi objetivo es dar el salto al desarrollo con código: Python, FastAPI, LangGraph, RAG sobre Postgres/pgvector, y despliegue en AWS.

Tengo experiencia real en:
- Asistentes RAG en producción (ingesta, chunking, retrieval, metadata filtering)
- Agentes orquestadores en GEAI
- Un Playground interno propio (React + FastAPI + PostgreSQL + Docker)

Lo que me falta consolidar:
- Arquitectura de agentes con código (LangGraph)
- Testing y evaluación automatizada de LLMs
- Outputs tipados con Pydantic
- CI/CD + deploy real (Render → AWS)

---

## La estructura de este proyecto

Este repositorio tiene DOS partes con propósitos distintos. No las mezcles.

```
/
├── agentic-rag-fastapi/        ← EL PRODUCTO (repo flagship)
│   ├── src/
│   │   ├── graph.py            ← StateGraph principal
│   │   ├── state.py            ← AgentState (TypedDict)
│   │   ├── tools.py            ← rag_search() + create_ticket()
│   │   ├── prompts.py          ← system prompts y templates
│   │   ├── config.py           ← settings, env vars
│   │   └── main.py             ← FastAPI app
│   ├── tests/                  ← pytest, se puebla con el curso de Testing
│   ├── evals/                  ← golden_set.json + métricas, con el curso de Evaluating
│   ├── .env.example
│   ├── requirements.txt
│   └── README.md
│
└── courses/                    ← REFERENCIA DE ESTUDIO (no es el producto)
    ├── langgraph-agents/       ← curso terminado
    │   ├── notes.md            ← qué aprendí + mapa de conceptos
    │   └── *.ipynb             ← notebooks adaptadas (opcional)
    ├── automated-testing-llms/ ← próximo curso
    ├── evaluating-ai-agents/
    └── pydantic-llm-workflows/
```

---

## Cómo aprendo: el principio fundamental

Los cursos me dan patrones. El repo flagship es donde los aplico con mi dominio real.

**No copio notebooks al repo flagship.**
**No espero terminar todos los cursos para construir.**
**Cada curso habilita una capa nueva del mismo repo.**

| Después de este curso | Agrego esta capa al repo |
|---|---|
| AI Agents in LangGraph ✅ | `graph.py` + `state.py` + `tools.py` (esqueleto real) |
| Automated Testing for LLMOps | `tests/` + GitHub Actions básico |
| Evaluating AI Agents | `evals/` + golden_set.json + métricas |
| Pydantic for LLM Workflows | Outputs tipados en tools y nodos |

---

## Cómo uso Copilot: aprender, no autocompletar

Quiero que Copilot me enseñe mientras trabajo, no que escriba el código por mí.

**Uso correcto:**
- Escribo el esqueleto yo (`def rag_search(query: str) -> str:`) → Copilot sugiere el cuerpo → yo reviso y explico cada línea en voz alta o en comentarios
- Le pregunto en el chat: "¿Por qué este nodo necesita devolver un dict con la misma clave que el TypedDict?" antes de que Copilot lo complete
- Le pido que explique, no que escriba: "Explicame por qué `add_conditional_edges` necesita una función de routing en vez de un string directo"

**Uso incorrecto (evitar):**
- Pedirle que genere un archivo completo de una vez
- Aceptar sugerencias sin entender qué hace cada línea
- Usarlo para saltear la comprensión de un patrón nuevo

**Prompts útiles para Copilot Chat:**
- "Explicame este archivo como si estuviera aprendiendo orquestación de agentes por primera vez."
- "¿Cuál es la diferencia entre este patrón y cómo lo haría sin LangGraph?"
- "¿Qué pasa si el estado no tiene esta clave cuando el nodo la necesita?"
- "Agregame type hints sin cambiar la lógica."
- "¿Qué testearías primero en esta función?"

---

## Workflow por sesión de estudio

Tengo entre 3 y 5 horas semanales. Cada sesión sigue este orden:

### Si estoy en la fase de curso (consumo):
1. Ver el video en el browser de DeepLearning.AI
2. Ejecutar la notebook en el entorno del curso (sin bajar nada todavía)
3. Tomar notas en `courses/<nombre-curso>/notes.md`: qué aprendí + cómo conecta con el repo

### Si estoy en la fase de construcción (lo más importante):
1. Abrir `agentic-rag-fastapi/` en VSCode
2. Preguntarme: "¿Qué patrón del curso de hoy puedo implementar aquí, con mi dominio real?"
3. Implementar ese patrón desde cero, con mis datos (RAG sobre PDFs, tickets en Postgres)
4. Commit descriptivo: `feat: add persistence layer with thread_id per user session`
5. Nunca terminar la sesión sin al menos un commit al repo flagship

**Regla de proporción: 40% consumo / 60% construcción.**

---

## Cómo me acompañás en cada sesión

Cuando abro un archivo del repo flagship, quiero que:
1. Me recuerdes en qué capa estamos y qué falta construir
2. Me hagas preguntas antes de sugerir código: "¿Sabés por qué el estado necesita ser un TypedDict acá?"
3. Clasifiques cada cambio que proponés:
   - `[aprendizaje]` — para entender el patrón
   - `[ingeniería]` — buena práctica de código
   - `[producción]` — necesario para deploy real

Cuando termino un bloque de trabajo, quiero que me digas:
- Qué construí hoy
- Qué patrón del curso apliqué
- Cuál es el próximo micro paso

---

## Restricciones importantes

- No generes archivos completos de una vez. Construimos incremental.
- No sugieras agregar dependencias sin explicar por qué.
- No avances a la siguiente capa hasta que la anterior esté funcionando mínimamente.
- Si algo no entiendo, prioriza explicar antes de escribir más código.
- El repo flagship debe poder correrse localmente en cualquier momento con `uvicorn src.main:app`.

---

## Estado actual del repo (actualizar acá)

- [x] Curso terminado: AI Agents in LangGraph
- [ ] `graph.py` con StateGraph básico funcionando
- [ ] `state.py` con AgentState definido
- [ ] `tools.py` con rag_search() y create_ticket() como stubs
- [ ] `main.py` con FastAPI básico
- [ ] Primer commit al repo flagship
