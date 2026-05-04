"""Entrada FastAPI minima para conversar con el grafo del agente."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.config import Settings, load_settings
from src.graph import graph


class ChatRequest(BaseModel):
    """Payload de entrada del endpoint /chat."""

    message: str = Field(..., min_length=1, description="Mensaje del usuario")
    thread_id: str = Field(..., min_length=1, description="ID de conversacion")


class ChatResponse(BaseModel):
    """Payload de salida del endpoint /chat."""

    thread_id: str
    response: str


app = FastAPI(title="Agentic RAG FastAPI", version="0.1.0")
settings: Settings | None = None


@app.on_event("startup")
def on_startup() -> None:
    """Valida configuracion al iniciar la app (fail fast)."""
    global settings
    settings = load_settings()


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
