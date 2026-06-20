# src/main.py
"""Entrada FastAPI minima para conversar con el grafo del agente."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from src.config import Settings, load_settings
from src.graph import graph
from src.ingestion import build_index
from src.schemas import ChatRequest, ChatResponse
from src.tools import set_index

DOCS_DIR = Path(__file__).parent.parent / "docs"

settings: Settings | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: valida config y construye el indice RAG."""
    global settings
    settings = load_settings()

    documents = [
        (path.read_text(encoding="utf-8"), path.name)
        for path in DOCS_DIR.glob("*.txt")
    ]
    if documents:
        set_index(build_index(documents))

    yield  # la app corre aqui


app = FastAPI(title="Agentic RAG FastAPI", version="0.1.0", lifespan=lifespan)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """Envia un mensaje al grafo usando thread_id para persistencia."""
    if settings is None:
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
