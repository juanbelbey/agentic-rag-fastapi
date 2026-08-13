# agentic-rag-fastapi

Agente de soporte tecnico con RAG real (LangGraph + FastAPI + Postgres/pgvector) sobre manuales de instrumentacion de campo.

## Caso de uso

Asistente para operadores y tecnicos de sistemas municipales de agua potable y saneamiento (plantas potabilizadoras, redes de distribucion, plantas de tratamiento cloacal): responde consultas sobre instrumentacion de campo (transmisores de presion, caudal y temperatura de Emerson/Rosemount, Siemens Sitrans y Endress+Hauser) — calibracion, codigos de error, rangos de medicion, mantenimiento — citando la fuente del manual, y crea un ticket cuando la consulta no esta cubierta por la documentacion o requiere escalarse a soporte humano.

Dominio elegido a partir de experiencia real: 2 anios como consultor tecnico en agua potable y saneamiento (plantas potabilizadoras, redes de distribucion, tratamiento cloacal para la Municipalidad de Monte Vera) — no un demo generico.

## Como funciona

- **Agente**: LangGraph (`StateGraph` con routing condicional entre `agent` y `tools`)
- **Retrieval**: hybrid search (vector + full-text de Postgres) fusionado con Reciprocal Rank Fusion, sobre Supabase/pgvector
- **Tools**: `rag_search` (busca en los manuales tecnicos), `create_ticket` (escala lo que no esta cubierto)
- **API**: FastAPI, endpoint `POST /chat`

Ver `ROADMAP.md` para el estado actual del proyecto y `STACK.md` para las decisiones de librerias.

## Documentacion tecnica: de donde sale

El corpus son 11 manuales oficiales de Emerson/Rosemount, Siemens Sitrans y Endress+Hauser (instrumentacion de presion, caudal y temperatura), descargados de los dominios oficiales de cada fabricante. Tienen copyright — no se redistribuyen: los PDFs originales estan en `.gitignore`, el repo solo versiona el script de ingesta. Detalle de fuentes y links oficiales en `CORPUS_INSTRUMENTACION.MD`.

## Como correrlo

**Requisitos para reproducir el pipeline completo:**
- Python 3.12, dependencias fijadas en `requirements.txt` (`pip install -r requirements.txt` instala versiones exactas, no rangos)
- Cuenta de OpenAI con API key (de pago — la ingesta completa embebe ~2451 chunks)
- Postgres con la extension `vector` habilitada (Supabase free tier alcanza, ver `ROADMAP.md` Capa 5B.0)
- Los 11 PDFs del corpus — no estan en el repo por copyright, pero son **descargables gratis y sin login** desde los dominios oficiales de cada fabricante: los 11 links directos (verificados HTTP 200) y el nombre de archivo exacto que espera cada uno estan en `CORPUS_INSTRUMENTACION.MD`. Se descargan a mano y se guardan en `docs/pdfs/` con esos nombres antes de ingerir.

```bash
python -m venv .venv
.venv/Scripts/activate  # source .venv/bin/activate en Linux/Mac
pip install -r requirements.txt
cp .env.example .env  # completar OPENAI_API_KEY y DATABASE_URL
python -m scripts.ingest  # requiere docs/pdfs/ poblado, ver arriba
```

```bash
uvicorn src.main:app --reload
```

`POST /chat` con `{"message": "...", "thread_id": "..."}`.

Alternativa con Docker (no reingiere nada, solo consulta la base ya poblada):

```bash
docker build -t agentic-rag-fastapi .
docker run --env-file .env -p 8000:8000 agentic-rag-fastapi
```

**Reproducir los evals sin pagar de nuevo la ingesta:** `evals/ground_truth_retrieval.json` (520 preguntas de retrieval) y `evals/golden_set.json` (56 casos de generacion, incluye 8 de escalamiento a `create_ticket`) ya estan commiteados — no hace falta regenerarlos. Con una tabla `chunks` ya poblada (propia o restaurada de un dump), `python -m evals.retrieval_metrics` y `python -m evals.run_evals` corren directo sobre esos datasets. Los resultados de corridas ya hechas quedan en `evals/results/YYYY-MM-DD/` para inspeccionar sin correr nada.

## Criterios de evaluacion (LLM Zoomcamp 2026)

Este repo es la entrega del proyecto final del [LLM Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp) (DataTalks.Club). Mapa de los 9 criterios oficiales a donde vive cada uno en el codigo:

| Criterio | Donde esta |
|---|---|
| Problem description | Este README, seccion "Caso de uso" |
| Retrieval flow | Knowledge base (Supabase/pgvector) + LLM en el flujo — hybrid search (vector + full-text) fusionado con RRF, `src/tools.py` (`rag_search`) |
| Retrieval evaluation | `evals/generate_ground_truth.py` + `evals/retrieval_metrics.py` — hit_rate/MRR comparados entre vector-only, keyword-only e hybrid sobre 520 preguntas (`evals/ground_truth_retrieval.json`), ver `ROADMAP.md` Capa 5B.4 |
| LLM evaluation | `evals/evaluators.py` + `evals/run_evals.py` sobre `evals/golden_set.json`, corrido en CI (`.github/workflows/ci.yml`, job `evals`); comparación de ≥2 enfoques (prompt × modelo, 4 combinaciones) en `evals/compare_prompts.py`, decisión final documentada con datos en `EXPERIMENTS.md` |
| Interface | API REST con FastAPI — `POST /chat` (`src/main.py`) |
| Ingestion pipeline | `scripts/ingest.py` — chunking + embeddings OpenAI + carga a Postgres/pgvector, script dedicado (no notebook manual) |
| Monitoring | Tabla `chat_logs` (latencia/tokens/costo estimado por request) + `GET /stats` + dashboard `streamlit_app/pages/1_📊_Monitoring.py` (4 metric tiles + 5 gráficos), ver `CHANGELOG.md` 2026-08-11 |
| Containerization | `docker-compose.yml` levanta backend (`Dockerfile`) + frontend (`streamlit_app/Dockerfile`) juntos con un solo comando, ver `CHANGELOG.md` 2026-08-12 |
| Reproducibility | Seccion "Como correrlo" arriba; versiones fijas en `requirements.txt`; dataset con copyright pero accesible: 11 links directos verificados HTTP 200 en `CORPUS_INSTRUMENTACION.MD`; evals reproducibles sin re-ingerir (datasets ya commiteados) |

Best practices: hybrid search ✅ (evaluado, ver Retrieval evaluation arriba). Query rewriting ✅ (`_rewrite_query_impl()` en `src/tools.py`, reescribe la query a inglés técnico antes del keyword search — hit_rate hybrid 0.317 → 0.415, +31%, sobre las 520 preguntas de `evals/ground_truth_retrieval.json`). Re-ranking: pendiente.
