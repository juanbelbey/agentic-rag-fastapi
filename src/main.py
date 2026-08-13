# src/main.py
"""Entrada FastAPI minima para conversar con el grafo del agente."""

import os
import time
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from langgraph.checkpoint.postgres import PostgresSaver
from langsmith import Client
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_ipaddr

# Precio de gpt-4o-mini verificado en platform.openai.com/docs/pricing el
# 2026-08-11. Solo cubre el LLM principal del chat (los AIMessage de
# result["messages"]) -- no incluye la llamada interna de query_rewrite()
# en tools.py, que corre aparte y no queda en ese arbol. El dashboard lo
# aclara como estimado, no como costo exacto (ver GET /stats).
PRICE_PER_1K_INPUT_USD = 0.00015
PRICE_PER_1K_OUTPUT_USD = 0.0006

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

        # Log por request de /chat -- alimenta GET /stats (dashboard de
        # monitoring). tool_calls_used como TEXT[] (psycopg adapta listas de
        # str automaticamente). estimated_cost_usd es una aproximacion, ver
        # nota de PRICE_PER_1K_*_USD arriba.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_logs (
                id BIGSERIAL PRIMARY KEY,
                run_id UUID NOT NULL,
                thread_id TEXT NOT NULL,
                tool_calls_used TEXT[] NOT NULL DEFAULT '{}',
                latency_ms INTEGER NOT NULL,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                estimated_cost_usd REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute("ALTER TABLE chat_logs ENABLE ROW LEVEL SECURITY")

    yield  # la app corre aqui

    pool.close()


app = FastAPI(title="Agentic RAG FastAPI", version="0.1.0", lifespan=lifespan)

# get_ipaddr (no get_remote_address): en Render la app corre detras de un
# proxy/load balancer, asi que request.client.host da la IP interna del
# proxy, no la del caller real. get_ipaddr lee X-Forwarded-For primero.
limiter = Limiter(key_func=get_ipaddr)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    """Envia un mensaje al grafo usando thread_id para persistencia."""
    if settings is None or graph is None:
        raise HTTPException(status_code=500, detail="La configuracion no fue inicializada")

    # Generado ANTES del invoke y pasado por config["run_id"]: asi LangSmith usa
    # este UUID para el trace en vez de generar el suyo propio -- lo necesitamos
    # en la mano para devolverlo en la respuesta y despues asociarle feedback.
    run_id = uuid.uuid4()
    config = {"configurable": {"thread_id": payload.thread_id}, "run_id": run_id}

    start = time.perf_counter()
    try:
        result = graph.invoke(
            {"messages": [{"role": "user", "content": payload.message}]},
            config=config,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al ejecutar el agente: {exc}") from exc
    latency_ms = round((time.perf_counter() - start) * 1000)

    last_message = result["messages"][-1]

    tool_calls_used: list[str] = []
    prompt_tokens = 0
    completion_tokens = 0
    for message in result["messages"]:
        for tool_call in getattr(message, "tool_calls", None) or []:
            name = tool_call["name"]
            if name not in tool_calls_used:
                tool_calls_used.append(name)
        usage = getattr(message, "usage_metadata", None)
        if usage:
            prompt_tokens += usage.get("input_tokens", 0)
            completion_tokens += usage.get("output_tokens", 0)

    estimated_cost_usd = (
        prompt_tokens / 1000 * PRICE_PER_1K_INPUT_USD
        + completion_tokens / 1000 * PRICE_PER_1K_OUTPUT_USD
    )

    if pool is not None:
        try:
            with pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO chat_logs
                        (run_id, thread_id, tool_calls_used, latency_ms,
                         prompt_tokens, completion_tokens, estimated_cost_usd)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run_id,
                        payload.thread_id,
                        tool_calls_used,
                        latency_ms,
                        prompt_tokens,
                        completion_tokens,
                        estimated_cost_usd,
                    ),
                )
        except Exception:
            # Best-effort, igual que el envio de feedback a LangSmith: loguear
            # la metrica no debe romper la respuesta real del chat.
            pass

    return ChatResponse(
        thread_id=payload.thread_id,
        response=getattr(last_message, "content", ""),
        tool_calls_used=tool_calls_used,
        run_id=str(run_id),
    )


@app.post("/feedback", status_code=201)
@limiter.limit("20/minute")
def feedback(request: Request, payload: FeedbackInput) -> dict[str, str]:
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


@app.get("/stats")
@limiter.limit("30/minute")
def stats(request: Request) -> dict[str, list[dict]]:
    """Datos crudos para el dashboard de monitoring (Streamlit agrega/grafica del
    lado del cliente -- este endpoint no hace agregacion, mismo criterio de
    simplicidad que el resto de la app). Ultimas 500 filas de cada tabla,
    suficiente para un demo de portfolio."""
    if pool is None:
        raise HTTPException(status_code=500, detail="La configuracion no fue inicializada")

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT created_at, latency_ms, tool_calls_used, prompt_tokens,
                       completion_tokens, estimated_cost_usd
                FROM chat_logs
                ORDER BY created_at DESC
                LIMIT 500
                """
            )
            chat_logs = cur.fetchall()

            cur.execute(
                """
                SELECT created_at, score
                FROM feedback
                ORDER BY created_at DESC
                LIMIT 500
                """
            )
            feedback_rows = cur.fetchall()

    return {"chat_logs": chat_logs, "feedback": feedback_rows}
