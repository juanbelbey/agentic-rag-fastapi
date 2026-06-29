# POST-COURSE HANDOFF: AI Agents in LangGraph
# DeepLearning.AI — Harrison Chase & Rotem Weiss

## Contexto

Acabo de terminar el curso "AI Agents in LangGraph" de DeepLearning.AI.
Este es el primer curso de mi plan de especialización como AI Engineer.
Ahora quiero convertir lo que aprendí en la primera capa real del repo flagship `agentic-rag-fastapi`.

**No quiero repasar el curso. Quiero construir.**

---

## Qué cubrió el curso (mapa de conceptos)

| Lección | Concepto clave | Dónde conecta con mi repo |
|---|---|---|
| Build an Agent from Scratch | Loop ReAct: razonar → actuar → observar | Lógica central del agente |
| LangGraph Components | StateGraph, nodes, edges, TypedDict | Estructura de `graph.py` y `state.py` |
| Agentic Search Tools | Tavily como tool estructurada para agentes | Patrón para `rag_search()` |
| Persistence and Streaming | Checkpointer + thread_id | Memoria por conversación de usuario |
| Human in the Loop | interrupt_before para pausar el grafo | Confirmación antes de crear ticket |
| Essay Writer | Grafo multi-nodo con roles especializados | Flujo: retrieval → respuesta → evaluación |

---

## Lo que quiero construir ahora

La primera capa del repo flagship: **el esqueleto del agente que corra localmente**.

No tiene que conectarse a Supabase todavía. No tiene que tener RAG real todavía.
Tiene que tener la arquitectura correcta para que todo lo demás encaje después.

### Archivos a crear (en orden):

**1. `src/state.py`**
- `AgentState` como TypedDict
- Campos: `messages`, `next_action` (opcional por ahora)
- Explicame por qué TypedDict y no una clase normal antes de escribirlo

**2. `src/tools.py`**
- `rag_search(query: str) -> str` → por ahora devuelve un string hardcodeado simulando un resultado
- `create_ticket(summary: str, category: str) -> str` → por ahora imprime y devuelve confirmación
- Quiero entender: ¿cómo sabe LangGraph que estas funciones son tools del agente?

**3. `src/graph.py`**
- StateGraph con al menos: nodo de razonamiento (llm) + nodo de herramienta (tools)
- Routing condicional: si el LLM quiere usar una tool, va al nodo de tools; si no, termina
- Checkpointer con MemorySaver (después migraremos a Postgres)
- Antes de escribirlo: explicame la diferencia entre `add_edge` y `add_conditional_edges`

**4. `src/config.py`**
- Carga de variables de entorno con python-dotenv
- `OPENAI_API_KEY` como única key obligatoria por ahora

**5. `src/main.py`**
- FastAPI app mínima con un endpoint `POST /chat` que recibe `{"message": "...", "thread_id": "..."}`
- Llama al grafo y devuelve la respuesta del agente
- Quiero que el thread_id permita persistencia entre llamadas

---

## Cómo quiero trabajar en esta sesión

- Construimos archivo por archivo, en el orden de arriba
- Antes de cada archivo: explicame el concepto central en 3-4 líneas
- Después de cada archivo: una pregunta de comprensión para mí
- Cada archivo que terminemos: hacemos commit con mensaje descriptivo
- Al final: el repo debe correr con `uvicorn src.main:app --reload` y responder en `/chat`

---

## Restricciones

- Sin dependencias innecesarias todavía (no Supabase, no pgvector, no Tavily real)
- Sin tests todavía (eso viene con el próximo curso)
- Sin Docker todavía
- Usá `MemorySaver` para persistencia, no Postgres todavía
- El modelo es `gpt-4o-mini` por defecto (menor costo mientras aprendo)

---

## Pregunta inicial para arrancar

Antes de escribir cualquier código, quiero que me expliques:

**¿Por qué en LangGraph el estado tiene que ser un TypedDict y qué pasa si intento pasar un objeto cualquiera?**

Después de tu respuesta, arrancamos con `state.py`.
