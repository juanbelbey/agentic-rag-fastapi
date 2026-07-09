# POST-COURSE HANDOFF: LLM Zoomcamp — Módulo 3
# DataTalks.Club — AI Orchestration with Kestra

> Nota: este módulo usa **Kestra** como orquestador. El repo flagship (`agentic-rag-fastapi`)
> no usa Kestra — usa **LangGraph** (aprendido en cursos de DeepLearning.AI). Por eso esta
> sección no traspasa YAML de Kestra: traduce los *conceptos* a sus equivalentes en LangGraph,
> que es lo transferible.

## Contexto

Acabo de terminar el Módulo 3 del LLM Zoomcamp 2026.
Ver ROADMAP.md para el estado completo del repo.

Capas completadas hasta ahora:
- Capa 1 ✅ — Esqueleto del agente (LangGraph, `StateGraph` custom)
- Capa 2 ✅ — Tests y CI
- Capa 3A ✅ — Evaluadores a mano
- Capa 3B ✅ — Integración LangSmith (solo en `evals/`, ver hallazgo abajo)
- Capa 4 ✅ — Outputs tipados con Pydantic
- Capa 5A ✅ — RAG en memoria (numpy + cosine similarity)
- Capa 5A.2 ✅ — Hybrid search en memoria (TF-IDF + RRF)
- Capa 5B.0/5B.1 ✅ — Infraestructura Supabase + script de ingesta
- Capa 5B.2 ✅ — `rag_search()` migrado a Postgres (pgvector + FTS + RRF real)

Capa en progreso luego de M3:
- Capa 5B.3 ⬜ — Postgres checkpointer (MemorySaver → checkpointer real)
- Paso 6 (aparte, no bloquea) ⬜ — limpiar `_index`/`InMemoryIndex`/`build_index()` del lifespan

### Estado del módulo
- HW3 entregado ✓ (resuelto corriendo Kestra real vía Docker + Gemini 2.5 Flash, excepción
  puntual por deadline — no es el flujo normal de trabajo del repo)
- Videos de las 9 lecciones: pendientes de repaso
- Apuntes (`M3-lessons/apuntes.md`): completos

---

## Qué vi en el módulo (conceptos, agnósticos de framework)

| Concepto | En Kestra | Equivalente en LangGraph |
|---|---|---|
| **Agentic loop** | `AIAgent` plugin: das goal + tools, Kestra corre el loop (LLM → tool → repetir hasta que no haya más tool calls) | `create_react_agent` (prebuilt) o un `StateGraph` propio con nodo LLM + `ToolNode` + arista condicional que vuelve al LLM mientras haya `tool_calls` |
| **Multi-agente (agent-as-tool)** | Un `AIAgent` principal usa otro `AIAgent` como tool | Patrón **supervisor**: un grafo por agente especializado invocado como tool desde el supervisor, o `langgraph-supervisor` ya armado |
| **Memoria entre ejecuciones** | `memory: KestraKVStore` con `memoryId` | `checkpointer` (`MemorySaver`, `SqliteSaver`, `PostgresSaver`) + `thread_id` |
| **Tools del agente** | Catálogo de plugins: `TavilyWebSearch`, `CodeExecution`, MCP clients | `TavilySearchResults`, `PythonREPLTool`, MCP vía `langchain-mcp-adapters` — superficie casi 1:1 |
| **Observabilidad de tokens** | `tokenUsage.totalTokenCount` logueado por ejecución por defecto | LangSmith tracing (`LANGCHAIN_TRACING_V2=true`) o `response.usage_metadata` sin LangSmith |
| **Agente vs workflow tradicional** | Pasos deterministas/auditables → workflow fijo; decisiones dinámicas → agente | Misma regla, endpoint por endpoint: `prompt \| llm \| parser` fijo vs `StateGraph` con loop agéntico |
| **Salida estructurada confiable** | Prompt pidiendo "JSON puro" (frágil, depende de que el modelo obedezca) | `llm.with_structured_output(PydanticModel)` — validación real |

### Qué implementé en la notebook (HW3)
- Levanté Kestra local (Docker Compose) con Gemini 2.5 Flash + Tavily
- Corrí `4_simple_agent.yaml` 3 veces (short/long/prompt modificado), medí tokens reales de output (Q3–Q5)
- Confirmé empíricamente: resumen largo ≈2.3x más tokens de output que uno corto; agregar
  oraciones al prompt escala el output de forma similar (no lineal con "un poco más de texto")
- Respondí Q1, Q2, Q6 sobre context engineering, RAG y cuándo NO usar agentes

---

## Auditoría contra el repo real (no asumido, verificado leyendo el código)

Antes de proponer nada, reviso el estado real de `src/graph.py`, `src/tools.py`,
`src/main.py`, `src/schemas.py` y `src/config.py` para responder con evidencia,
no con suposiciones:

**1. ¿`create_react_agent` prebuilt o `StateGraph` custom?**
Custom, a propósito. `graph.py` tiene `agent_node` + `ToolNode` + `route_after_agent`
escritos a mano desde Capa 1, específicamente para entender el mecanismo antes de
usar el prebuilt (mismo criterio que "aprender, no autocompletar" de COPILOT_STRATEGY.md).
No hay ganancia en reemplazarlo — ya funciona y ya está entendido.

**2. ¿Hay más de un rol de agente, o es monolítico?**
Monolítico. Un solo `agent_node`, un solo `SYSTEM_PROMPT`, dos tools (`rag_search`,
`create_ticket`) bindeadas al mismo LLM. El patrón agent-as-tool de Kestra
(research agent llamado por analyst agent) no tiene un caso de uso claro todavía:
el dominio actual (RAG + tickets) lo resuelve bien un solo agente. Separar en
supervisor + subagentes hoy sería sobre-ingeniería sin problema real que resolver.

**Hallazgo al pasar:** el `SYSTEM_PROMPT` de `graph.py` sigue siendo el placeholder
de Capa 1 ("You are the first local skeleton of an agentic RAG assistant...") —
nunca se actualizó para mencionar que ahora hay RAG real sobre Postgres y cuándo
usar cada tool. No es un bug, pero es deuda menor de prompt engineering.

**3. ¿Tracing/observabilidad ya resuelto?**
**Parcialmente — gap real encontrado.** LangSmith (Capa 3B) está integrado, pero
únicamente en `evals/evaluators.py` (`@traceable`) y `evals/run_evals.py`
(`client.create_feedback()`). El endpoint real `/chat` (`graph.invoke()` en
`src/main.py`) **no tiene tracing activado en ningún lado** — no hay
`LANGCHAIN_TRACING_V2` seteado para el runtime de la app, solo para las corridas
de evals. Hoy, si un usuario real dispara el agente y algo sale mal o loopea, la
única visibilidad es el `print()` de `create_ticket()`. Esto es exactamente el
gap que Kestra resuelve gratis (loguea tokens y tool calls por defecto) y que acá
no está — coincide con la prioridad "Alta" que había anotado antes de auditar.

**4. ¿JSON armado a mano o `with_structured_output`?**
Ninguno de los dos problemas de Kestra aplica literal: `rag_search()` y
`create_ticket()` usan tool-calling nativo de LangChain (`bind_tools` +
`args_schema=TicketInput`), que ya es function-calling estructurado — mismo
nivel (o mejor) que el mecanismo de Kestra. El problema real de "salida no
fiel" está en otro lado: `ChatResponse.tool_calls_used` **siempre devuelve `[]`**
(deuda técnica documentada desde Capa 5A, 2026-06-20, nunca resuelta) —
`main.py` no lo puebla a partir de `result["messages"]` aunque la información
(qué tools se llamaron) ya está ahí. Es la misma familia de problema que señala
M3 ("la API dice que devuelve algo estructurado y no lo hace"), aunque la causa
es distinta (campo sin poblar, no parseo frágil de prompt).

---

## Decisiones tomadas en este handoff

| Decisión | Elección | Razón |
|---|---|---|
| `create_react_agent` prebuilt | No adoptar | El `StateGraph` custom ya funciona y se construyó a propósito para aprender el mecanismo. Sin ganancia real. |
| Supervisor multi-agente | No adoptar por ahora | Dominio actual (RAG + tickets) resuelto bien por un solo agente. Revisar si el repo suma un tercer rol claramente distinto. |
| Tracing del runtime real (no solo evals) | **Adoptar — gap real confirmado** | LangSmith ya está en el repo pero no cubre `/chat`. Activarlo es una env var, no una reescritura. |
| Poblar `tool_calls_used` | Adoptar | Deuda técnica ya documentada desde Capa 5A, campo dead code. Barato de arreglar con lo que ya devuelve `graph.invoke()`. |
| Límite explícito de `max_tokens` en el LLM del agente | Evaluar | M3 mostró empíricamente que el output escala ~2.3x con resúmenes largos. Vale ponerle techo en `get_bound_llm()`. |
| Actualizar `SYSTEM_PROMPT` de Capa 1 | Evaluar (menor) | Sigue siendo el placeholder original, no menciona las tools reales. |

---

## Candidatos para la próxima sesión (orden sugerido)

1. **Tracing real del agente** (`LANGCHAIN_TRACING_V2` + `LANGCHAIN_PROJECT` para el
   runtime, no solo evals) — mayor impacto, menor costo, gap confirmado por auditoría.
2. **Poblar `ChatResponse.tool_calls_used`** en `main.py` a partir de `result["messages"]`
   — cierra deuda técnica ya anotada, un solo archivo.
3. **`max_tokens` explícito** en `get_bound_llm()` — aprendizaje directo de M3.
4. Actualizar `SYSTEM_PROMPT` — menor, se puede sumar al mismo bloque que el punto 2.
5. Seguir con **Capa 5B.3** (Postgres checkpointer) según el plan ya trazado en ROADMAP —
   no relacionado a M3, pero es lo próximo en la cola antes de estas mejoras si Juan
   prefiere no interrumpir la secuencia de capas.

Ninguno de estos se implementa todavía en esta sesión — quedan para decidir con Juan
cuál se ataca primero, uno por vez, con explicación antes de código (COPILOT_STRATEGY.md).

---

## Restricciones heredadas (sin cambio)

- `gpt-4o-mini` como modelo por defecto
- No usar Pinecone/Weaviate ni Kestra: el stack es Supabase/pgvector + LangGraph
- LangSmith debe seguir degradándose silenciosamente si no hay `LANGCHAIN_API_KEY`
- El repo debe poder correrse localmente en cualquier momento con `uvicorn src.main:app --reload`
- No saltar de Capa 5B.3 sin terminarla, salvo que Juan decida priorizar estas mejoras antes

---

*Próximo módulo: M4 — se agrega una sección nueva cuando esté completo.*
