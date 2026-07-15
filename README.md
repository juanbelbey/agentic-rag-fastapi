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

```bash
python -m venv .venv
.venv/Scripts/activate  # source .venv/bin/activate en Linux/Mac
pip install -r requirements.txt
cp .env.example .env  # completar OPENAI_API_KEY y DATABASE_URL
```

Requiere una tabla `chunks` en Postgres/Supabase con la extension `vector` habilitada (ver `ROADMAP.md`, Capa 5B.0). La ingesta (`python -m scripts.ingest`) necesita los manuales en `docs/pdfs/` — no estan en el repo por copyright, ver seccion anterior.

```bash
uvicorn src.main:app --reload
```

`POST /chat` con `{"message": "...", "thread_id": "..."}`.
