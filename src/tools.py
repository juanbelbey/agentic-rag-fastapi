"""Tools del agente con schemas Pydantic.

args_schema conecta cada tool con su modelo de validación:
- LangChain usa el schema para informar al LLM qué campos enviar
- Pydantic valida los argumentos antes de ejecutar el cuerpo
"""

import json
import os
import re

import psycopg2
from dotenv import load_dotenv
from langchain_core.tools import tool
from pgvector.psycopg2 import register_vector

from src.ingestion import InMemoryIndex, embed_texts, rrf
from src.schemas import RAGResult, TicketInput

# Índice global en memoria — se construye una vez con build_index() al arrancar.
# Arranca vacío; rag_search() lo detecta y avisa en vez de romper.
_index: InMemoryIndex = InMemoryIndex()

# Stopwords español + inglés para _keyword_search. El corpus mezcla documentos en
# ambos idiomas y las preguntas siempre llegan en español -- sin este filtro, el
# OR de _keyword_search matchea chunks solo por compartir "de"/"la"/"el"/"para" con
# la pregunta, no contenido real. Medido contra los 520 casos de
# evals/ground_truth_retrieval.json: sin filtro, hit_rate en documentos en español
# 0.4554 (inflado por stopwords) vs 0.0101 en documentos en inglés (donde esas
# palabras casi no aparecen por azar) -- la brecha confirma la contaminación.
_STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "las", "un", "una", "del", "al",
    "que", "con", "para", "por", "se", "su", "sus", "es", "lo", "como", "más",
    "pero", "le", "ya", "o", "este", "esta", "estos", "estas", "ese", "esa",
    "eso", "entre", "cuando", "sin", "sobre", "también", "me", "hasta", "hay",
    "donde", "quien", "quién", "quienes", "quiénes", "desde", "todo", "todos",
    "nos", "durante", "uno", "unos", "les", "ni", "contra", "otros", "otro",
    "otra", "otras", "ante", "ellos", "ella", "él", "e", "esto", "mí", "antes",
    "algunos", "qué", "yo", "tanto", "mucho", "muchos", "poco", "cual", "cuál",
    "cuáles", "cómo", "cuándo", "cuánto", "cuánta", "nada", "ser", "estar",
    "tener", "haber",
    "the", "a", "an", "of", "to", "in", "for", "on", "with", "at", "by", "from",
    "is", "are", "be", "this", "that", "and", "or", "as", "it", "was", "were",
    "will", "shall", "can", "may", "not", "if", "then",
}


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


def _build_or_tsquery(query: str) -> str | None:
    """Tokeniza la query, saca stopwords (_STOPWORDS) y arma 'palabra1 | palabra2 | ...'.

    None si no queda ningún término de contenido (query compuesta solo de stopwords).
    """
    tokens = re.findall(r"\w+", query.lower())
    keywords = [t for t in tokens if t not in _STOPWORDS]
    return " | ".join(keywords) if keywords else None


def _keyword_search(conn, query: str, top_k: int) -> list[tuple[int, float]]:
    """Devuelve [(chunk_id, rank), ...] usando Postgres full-text search (mayor rank = más relevante).

    Config 'simple' (sin stemming por idioma) + tsquery armado con OR ('|') entre
    palabras de contenido (ver _build_or_tsquery/_STOPWORDS) en vez de plainto_tsquery
    (que arma AND de todas las palabras): con preguntas parafraseadas de 15-20 palabras,
    exigir que TODAS aparezcan en el mismo chunk es un criterio casi imposible de
    cumplir. El filtro de stopwords evita que el OR matchee solo por "de"/"la"/"el"
    compartidas con la pregunta -- medido: sin filtro, hit_rate 0.4554 en documentos en
    español (inflado por stopwords) vs 0.0101 en documentos en inglés. Ver
    evals/retrieval_metrics.py (paso 5 de 5B.4).
    """
    tsquery_text = _build_or_tsquery(query)
    if tsquery_text is None:
        return []

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, ts_rank(to_tsvector('simple', content), to_tsquery('simple', %s)) AS rank
            FROM chunks
            WHERE to_tsvector('simple', content) @@ to_tsquery('simple', %s)
            ORDER BY rank DESC
            LIMIT %s;
            """,
            (tsquery_text, tsquery_text, top_k),
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
