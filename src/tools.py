"""Tools del agente con schemas Pydantic.

args_schema conecta cada tool con su modelo de validación:
- LangChain usa el schema para informar al LLM qué campos enviar
- Pydantic valida los argumentos antes de ejecutar el cuerpo
"""

import json
import os

import psycopg2
from dotenv import load_dotenv
from langchain_core.tools import tool
from pgvector.psycopg2 import register_vector

from src.ingestion import InMemoryIndex, embed_texts, rrf
from src.schemas import RAGResult, TicketInput

# Índice global en memoria — se construye una vez con build_index() al arrancar.
# Arranca vacío; rag_search() lo detecta y avisa en vez de romper.
_index: InMemoryIndex = InMemoryIndex()


def _get_connection():
    """Abre una conexión nueva a Postgres (sin pool todavía, una por llamada)."""
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Falta DATABASE_URL en el entorno.")
    conn = psycopg2.connect(database_url)
    register_vector(conn)
    return conn


def _vector_search(conn, query_embedding, top_k: int) -> list[tuple[int, float]]:
    """Devuelve [(chunk_id, distance), ...] ordenados por distancia coseno (menor = más parecido)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, embedding <=> %s AS distance FROM chunks ORDER BY distance LIMIT %s;",
            (query_embedding, top_k),
        )
        return cur.fetchall()


def _keyword_search(conn, query: str, top_k: int) -> list[tuple[int, float]]:
    """Devuelve [(chunk_id, rank), ...] usando Postgres full-text search (mayor rank = más relevante)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, ts_rank(to_tsvector('spanish', content), plainto_tsquery('spanish', %s)) AS rank
            FROM chunks
            WHERE to_tsvector('spanish', content) @@ plainto_tsquery('spanish', %s)
            ORDER BY rank DESC
            LIMIT %s;
            """,
            (query, query, top_k),
        )
        return cur.fetchall()


def set_index(index: InMemoryIndex) -> None:
    """Reemplaza el índice activo. Se llama desde main.py al iniciar la app."""
    global _index
    _index = index


@tool(args_schema=TicketInput)
def create_ticket(summary: str, category: str, priority: str = "medium") -> str:
    """Crea un ticket y devuelve una confirmacion."""
    print(f"[create_ticket] category={category} priority={priority} summary={summary}")
    return (
        f"Ticket creado — categoria: '{category}', "
        f"prioridad: '{priority}', resumen: '{summary}'."
    )


@tool
def rag_search(query: str, top_k: int = 3) -> str:
    """Busca chunks relevantes combinando vector search + keyword search + RRF."""
    if not _index.is_ready():
        result = RAGResult(
            content="El índice aún no está cargado. Llama a build_index() primero.",
            source="system",
            score=None,
        )
        return result.model_dump_json()

    # 1. Candidatos de ambos índices — más amplio que top_k para que RRF tenga con qué trabajar
    vector_results, keyword_results = _index.hybrid_search(query, vector_top_k=10, keyword_top_k=10)

    # 2. Fusionar por posición
    fused = rrf(vector_results, keyword_results)

    # 3. Top-K del ranking fusionado
    results = [
        RAGResult(
            content=_index.chunks[idx],
            source=_index.sources[idx],
            score=round(score, 4),
        )
        for idx, score in fused[:top_k]
    ]

    return json.dumps([r.model_dump() for r in results])


TOOLS = [rag_search, create_ticket]
