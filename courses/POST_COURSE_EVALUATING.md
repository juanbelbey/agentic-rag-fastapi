# POST-COURSE HANDOFF: Evaluating AI Agents
# DeepLearning.AI — John Gilhuly + Aman Khan (Arize AI)

## Contexto

Acabo de terminar el curso "Evaluating AI Agents" de DeepLearning.AI.
Ver ROADMAP.md para el estado completo del repo.

Capas completadas hasta ahora:
- Capa 1 ✅ — Esqueleto del agente (LangGraph)
- Capa 2 ✅ — Tests y CI (Automated Testing)

Ahora construyo la Capa 3: observabilidad y evals sistemáticas.

---

## Qué aprendí en el curso

| Concepto | Qué es | Dónde aplica en mi repo |
|---|---|---|
| Trazas (traces) | Registro de cada paso que da el agente | Debug de qué nodo falló en una cadena |
| Observabilidad | Ver el agente desde adentro, no solo su output | Entender por qué rag_search() devolvió algo malo |
| Evaluación componente por componente | Evaluar router, tools y memoria por separado | No solo "¿fue buena la respuesta?" sino "¿qué parte falló?" |
| Code-based evaluator | Función Python que da score sin LLM | Rápido y barato, para reglas claras |
| LLM-as-judge | LLM que evalúa otro LLM con prompt estructurado | Para calidad semántica que código no puede medir |
| Convergence score | Pasos hasta llegar a respuesta final | Detectar si el agente da vueltas innecesarias |
| Ejemplos desde trazas | Generar casos de test a partir de ejecuciones reales | Golden set construido desde uso real, no inventado |

---

## Estado actual del repo antes de esta capa

```
evals/
└── .gitkeep        ← vacío, listo para poblar

tests/
├── conftest.py     ✅
├── test_rules.py   ✅
└── test_evals.py   ✅ (LLM-as-judge básico, known_context hardcodeado)
```

Lo que test_evals.py tiene ahora es un juez básico con contexto fijo.
Esta capa lo convierte en un sistema de evaluación real y sistemático.

---

## Lo que quiero construir ahora (Capa 3)

### Archivos a crear en orden:

**1. `evals/golden_set.json`**
- 20 preguntas sobre documentación de LangGraph
- Cada entrada con: id, question, expected_answer, source, category
- Categorías: graph_structure, persistence, tools, human_in_loop, routing
- Antes de escribirlo: explicame por qué el golden set se construye
  desde trazas reales y no solo inventando preguntas

**2. `evals/evaluators.py`**
- Función `relevance_evaluator(question, answer) -> score (1-5)`
  usando LLM-as-judge con gpt-4o-mini
- Función `citation_evaluator(answer) -> bool`
  verifica que la respuesta mencione una fuente (code-based, sin LLM)
- Función `convergence_evaluator(trace) -> int`
  cuenta pasos hasta respuesta final (code-based)
- Antes de escribirlo: explicame cuándo usar code-based vs LLM-as-judge
  y por qué no usamos siempre el LLM

**3. `evals/run_evals.py`**
- Carga el golden_set.json
- Para cada pregunta: invoca el agente y corre los tres evaluadores
- Guarda resultados en `evals/results/YYYY-MM-DD.json`
- Imprime resumen: score promedio, % de respuestas con cita, pasos promedio
- Antes de escribirlo: explicame por qué guardamos resultados por fecha
  y no solo el último resultado

**4. Actualizar `tests/test_evals.py`**
- Importar los evaluadores de `evals/evaluators.py`
- Reemplazar el juez hardcodeado por los evaluadores reales
- Mantener el skip si no hay OPENAI_API_KEY

**5. Actualizar `.github/workflows/ci.yml`**
- Agregar paso que corre `evals/run_evals.py` solo en push a main
- Guardar el archivo de resultados como artefacto del workflow

---

## Cómo quiero trabajar en esta sesión

- Un archivo por vez, en el orden de arriba
- Antes de cada archivo: concepto central en 3-4 líneas + analogía
  (vengo de JS, las analogías ayudan)
- Después de cada archivo: una pregunta de comprensión para mí
- Al terminar run_evals.py: correrlo una vez y ver el output en consola
- Clasificar cada cambio como [aprendizaje], [ingeniería] o [producción]

---

## Restricciones

- gpt-4o-mini como modelo del juez (costo bajo)
- Sin Arize Phoenix ni herramientas de observabilidad externas todavía
  (el curso las usa, nosotros implementamos los conceptos a mano primero)
- rag_search() sigue siendo stub — los evals usan known_context del golden set
- Sin Supabase todavía (ver ROADMAP.md, eso es Capa 5)
- Los evaluadores tienen que poder correr localmente sin CI

---

## Pregunta inicial para arrancar

Antes de escribir cualquier código, quiero que me expliques:

**¿Por qué evaluar el router por separado de las tools?
¿Qué problema concreto resuelve eso que no resolvería
evaluar solo la respuesta final?**

Después de tu respuesta, arrancamos con `golden_set.json`.
