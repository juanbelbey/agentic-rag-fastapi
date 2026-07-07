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


def _hybrid_search(conn, query: str, query_embedding, top_k: int, candidate_k: int = 10) -> list[tuple[int, float]]:
    """Combina _vector_search + _keyword_search con RRF. Devuelve [(chunk_id, rrf_score), ...]."""
    vector_results = _vector_search(conn, query_embedding, candidate_k)
    keyword_results = _keyword_search(conn, query, candidate_k)
    fused = rrf(vector_results, keyword_results)
    return fused[:top_k]


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
    """Busca chunks relevantes combinando vector search + keyword search + RRF (Postgres)."""
    conn = _get_connection()
    try:
        query_embedding = embed_texts([query])[0]
        fused = _hybrid_search(conn, query, query_embedding, top_k)

        if not fused:
            result = RAGResult(
                content="No se encontraron resultados para esta búsqueda.",
                source="system",
                score=None,
            )
            return result.model_dump_json()

        ids = [chunk_id for chunk_id, _ in fused]
        with conn.cursor() as cur:
            cur.execute("SELECT id, content, source FROM chunks WHERE id = ANY(%s);", (ids,))
            rows = cur.fetchall()
    finally:
        conn.close()

    # Diccionario id -> (content, source) para reordenar según el ranking de fused, no el orden de Postgres
    rows_by_id = {row_id: (content, source) for row_id, content, source in rows}

    results = [
        RAGResult(
            content=rows_by_id[chunk_id][0],
            source=rows_by_id[chunk_id][1],
            score=round(score, 4),
        )
        for chunk_id, score in fused
    ]

    return json.dumps([r.model_dump() for r in results])


TOOLS = [rag_search, create_ticket]
