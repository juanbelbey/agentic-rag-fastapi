# src/main.py
"""Entrada FastAPI minima para conversar con el grafo del agente."""

import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.postgres import PostgresSaver
from langsmith import Client
from psycopg_pool import ConnectionPool

# Carga .env antes de importar src.graph (que importa src.tools): ese import
# evalua `os.getenv("LANGCHAIN_API_KEY")` a nivel de modulo para decidir si
# instrumentar _vector_search/_keyword_search con LangSmith. Sin este
# load_dotenv() temprano, load_settings() (mas abajo, recien dentro de
# lifespan) llega demasiado tarde -- el import ya paso y la instrumentacion
# queda desactivada aunque LANGCHAIN_API_KEY este en .env.
load_dotenv()

from src.config import Settings, load_settings  # noqa: E402
from src.graph import graph_builder  # noqa: E402
from src.schemas import ChatRequest, ChatResponse, FeedbackInput  # noqa: E402

settings: Settings | None = None
graph = None
pool: ConnectionPool | None = None
langsmith_client: Client | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: valida config y compila el grafo con checkpointer real."""
    global settings, graph, pool, langsmith_client
    settings = load_settings()

    # Opt-in, mismo patron que _vector_search/_keyword_search en tools.py: sin
    # LANGCHAIN_API_KEY el feedback solo se guarda en Postgres, no se manda a
    # LangSmith.
    if os.getenv("LANGCHAIN_API_KEY"):
        langsmith_client = Client()

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

    # Idempotente, mismo patron que checkpointer.setup(): crea la tabla si no
    # existe, no hace nada si ya esta. RLS sin policies -- el rol de la app
    # conecta directo por Postgres, no por la API REST, mismo criterio que
    # chunks/checkpoint tables (ver ROADMAP 5B.4).
    with pool.connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id BIGSERIAL PRIMARY KEY,
                run_id UUID NOT NULL,
                thread_id TEXT NOT NULL,
                score REAL NOT NULL,
                comment TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute("ALTER TABLE feedback ENABLE ROW LEVEL SECURITY")

    yield  # la app corre aqui

    pool.close()


app = FastAPI(title="Agentic RAG FastAPI", version="0.1.0", lifespan=lifespan)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """Envia un mensaje al grafo usando thread_id para persistencia."""
    if settings is None or graph is None:
        raise HTTPException(status_code=500, detail="La configuracion no fue inicializada")

    # Generado ANTES del invoke y pasado por config["run_id"]: asi LangSmith usa
    # este UUID para el trace en vez de generar el suyo propio -- lo necesitamos
    # en la mano para devolverlo en la respuesta y despues asociarle feedback.
    run_id = uuid.uuid4()
    config = {"configurable": {"thread_id": payload.thread_id}, "run_id": run_id}

    try:
        result = graph.invoke(
            {"messages": [{"role": "user", "content": payload.message}]},
            config=config,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al ejecutar el agente: {exc}") from exc

    last_message = result["messages"][-1]

    tool_calls_used: list[str] = []
    for message in result["messages"]:
        for tool_call in getattr(message, "tool_calls", None) or []:
            name = tool_call["name"]
            if name not in tool_calls_used:
                tool_calls_used.append(name)

    return ChatResponse(
        thread_id=payload.thread_id,
        response=getattr(last_message, "content", ""),
        tool_calls_used=tool_calls_used,
        run_id=str(run_id),
    )


@app.post("/feedback", status_code=201)
def feedback(payload: FeedbackInput) -> dict[str, str]:
    """Guarda el feedback de un usuario (pulgar arriba/abajo) sobre una respuesta de /chat."""
    if pool is None:
        raise HTTPException(status_code=500, detail="La configuracion no fue inicializada")

    try:
        with pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO feedback (run_id, thread_id, score, comment)
                VALUES (%s, %s, %s, %s)
                """,
                (payload.run_id, payload.thread_id, payload.score, payload.comment),
            )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo guardar el feedback: {exc}") from exc

    if langsmith_client is not None:
        try:
            langsmith_client.create_feedback(
                payload.run_id, key="user_score", score=payload.score, comment=payload.comment
            )
        except Exception:
            # Mismo criterio que run_evals.py: LangSmith es best-effort, no debe
            # romper el endpoint si falla.
            pass

    return {"status": "ok"}
