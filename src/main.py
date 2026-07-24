# src/main.py
"""Entrada FastAPI minima para conversar con el grafo del agente."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from src.config import Settings, load_settings
from src.graph import graph_builder
from src.ingestion import build_index
from src.schemas import ChatRequest, ChatResponse
from src.tools import set_index

DOCS_DIR = Path(__file__).parent.parent / "docs"

settings: Settings | None = None
graph = None
pool: ConnectionPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: valida config, construye el indice RAG y compila el grafo con checkpointer real."""
    global settings, graph, pool
    settings = load_settings()

    documents = [
        (path.read_text(encoding="utf-8"), path.name)
        for path in DOCS_DIR.glob("*.txt")
    ]
    if documents:
        set_index(build_index(documents))

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Falta DATABASE_URL en el entorno.")

    # autocommit=True: cada operacion del checkpointer se confirma sola, sin dejar
    # transacciones abiertas. prepare_threshold=0: evita prepared statements, que
    # pueden fallar si DATABASE_URL pasa por un pooler tipo pgbouncer.
    pool = ConnectionPool(
        conninfo=database_url,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    )
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    graph = graph_builder.compile(checkpointer=checkpointer)

    yield  # la app corre aqui

    pool.close()


app = FastAPI(title="Agentic RAG FastAPI", version="0.1.0", lifespan=lifespan)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """Envia un mensaje al grafo usando thread_id para persistencia."""
    if settings is None or graph is None:
        raise HTTPException(status_code=500, detail="La configuracion no fue inicializada")

    config = {"configurable": {"thread_id": payload.thread_id}}

    try:
        result = graph.invoke(
            {"messages": [{"role": "user", "content": payload.message}]},
            config=config,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al ejecutar el agente: {exc}") from exc

    last_message = result["messages"][-1]
    return ChatResponse(thread_id=payload.thread_id, response=getattr(last_message, "content", ""))
