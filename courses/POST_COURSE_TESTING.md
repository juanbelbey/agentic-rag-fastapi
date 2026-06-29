# POST-COURSE HANDOFF: Automated Testing for LLMOps
# DeepLearning.AI — Rob Zuber (CircleCI)

## Contexto

Acabo de terminar el curso "Automated Testing for LLMOps" de DeepLearning.AI.
Ya tengo construida la primera capa del repo flagship `agentic-rag-fastapi`:
- `src/state.py` — AgentState con TypedDict
- `src/tools.py` — rag_search() y create_ticket() como stubs
- `src/graph.py` — StateGraph con routing condicional y MemorySaver
- `src/config.py` — validación temprana de OPENAI_API_KEY
- `src/main.py` — FastAPI con endpoint POST /chat y persistencia por thread_id

Ahora quiero agregar la segunda capa: **tests automatizados**.

---

## Qué aprendí en el curso

| Concepto | Qué es | Dónde aplica en mi repo |
|---|---|---|
| Rules-based tests | Tests deterministas, sin LLM, instantáneos | Validar formato y estructura de respuestas del agente |
| Model-graded evals | Un LLM evalúa la respuesta de otro LLM | Evaluar si rag_search() responde con fidelidad al contexto |
| CI pipeline | Tests que corren solos en cada push a GitHub | GitHub Actions en .github/workflows/ci.yml |
| LLM-as-judge | Prompt estructurado para que el LLM dé score 1-5 | Métrica de relevancia para el agente RAG |

---

## Lo que quiero construir ahora

La capa de tests del repo. La carpeta `tests/` está vacía. Quiero poblarla.

### Archivos a crear (en orden):

**1. `tests/conftest.py`**
- Fixtures compartidos para todos los tests
- Fixture que inicializa el grafo del agente para tests
- Fixture con ejemplos de respuestas válidas e inválidas
- Antes de escribirlo: explicame qué es un fixture en pytest y por qué conviene centralizarlos acá

**2. `tests/test_rules.py`**
- Tests deterministas que no usan el LLM (rápidos y baratos)
- Quiero testear al menos estas reglas sobre mi agente:
  - La respuesta nunca es un string vacío
  - La respuesta tiene menos de 1000 caracteres (evitar respuestas descontroladas)
  - Si se llama a rag_search(), el resultado contiene al menos una palabra del query
  - create_ticket() devuelve una confirmación con el summary recibido
- Antes de escribirlo: explicame la diferencia entre un test unitario y un test de integración en el contexto de agentes LLM

**3. `tests/test_evals.py`**
- Evaluaciones con LLM-as-judge (más lentas, se corren menos seguido)
- Un eval que pregunta al LLM: "¿Esta respuesta es relevante para esta pregunta? Score 1-5"
- Un eval que verifica que el agente no alucina (responde solo con lo que tiene en contexto)
- Quiero que el judge use `gpt-4o-mini` para mantener el costo bajo
- Antes de escribirlo: explicame por qué separamos rules-based de model-graded en archivos distintos

**4. `.github/workflows/ci.yml`**
- GitHub Actions que corre `test_rules.py` en cada push a cualquier rama
- Solo corre `test_evals.py` cuando el push es a `main` (para no gastar tokens en cada commit)
- Necesita la OPENAI_API_KEY como secret de GitHub
- Antes de escribirlo: explicame cómo GitHub Actions sabe qué secrets usar y cómo los configuro

**5. `reports/` + reporte HTML**
- Instalar pytest-html: `pip install pytest-html`
- Correr tests con: `pytest tests/ --html=reports/report.html --self-contained-html`
- El reporte queda en `reports/report.html`, se abre en el browser para revisión manual
- En el `ci.yml`, configurar que el reporte quede guardado como artefacto de cada corrida
- Antes de hacerlo: explicame cómo GitHub Actions guarda artefactos y por cuánto tiempo

---

## Cómo quiero trabajar en esta sesión

- Un archivo por vez, en el orden de arriba
- Antes de cada archivo: explicame el concepto central en 3-4 líneas
- Después de cada archivo: una pregunta de comprensión para mí
- Al terminar `test_rules.py`: corremos los tests con `pytest tests/test_rules.py -v` y vemos que pasen
- Al terminar `test_evals.py`: corremos uno solo para validar que el judge funciona
- Al terminar el `ci.yml`: hacemos un push y vemos el workflow correr en GitHub

---

## Dataset para los tests y evals

Usamos documentación oficial de LangGraph como base del RAG.

**Fuente:** https://langchain-ai.github.io/langgraph/
- Descargar o copiar secciones clave como texto plano o PDF
- Guardar en `data/docs/langgraph_docs.pdf` (o `.txt`)

**Golden set:** crear `evals/golden_set.json` con 20 preguntas y respuestas esperadas.
Ejemplos de preguntas:
- "¿Cuál es la diferencia entre add_edge y add_conditional_edges?"
- "¿Cómo se implementa persistencia con MemorySaver en LangGraph?"
- "¿Qué es un StateGraph y cuándo conviene usarlo?"
- "¿Cómo se define el estado de un agente con TypedDict?"
- "¿Qué hace interrupt_before en un grafo?"

**Formato del golden_set.json:**
```json
[
  {
    "id": "q001",
    "question": "¿Cuál es la diferencia entre add_edge y add_conditional_edges?",
    "expected_answer": "add_edge conecta dos nodos de forma fija. add_conditional_edges usa una función de routing para decidir el próximo nodo según el estado.",
    "source": "langgraph_docs"
  }
]
```

El model-graded eval compara la respuesta del agente contra el `expected_answer` usando LLM-as-judge.

---

## Restricciones

- Los tests tienen que pasar con el código actual del repo (stubs incluidos)
- Sin dependencias nuevas si no son necesarias (pytest ya está instalado)
- El model-graded eval tiene que tener un costo estimado por corrida (tokens usados)
- No instales CircleCI — el curso lo usa pero nosotros usamos GitHub Actions

---

## Pregunta inicial para arrancar

Antes de escribir cualquier código, quiero que me expliques:

**¿Por qué en aplicaciones LLM los tests tradicionales no alcanzan y necesitamos model-graded evals? ¿Qué problema concreto resuelven?**

Después de tu respuesta, arrancamos con `conftest.py`.
