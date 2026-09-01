"""Tools del agente con schemas Pydantic.

args_schema conecta cada tool con su modelo de validación:
- LangChain usa el schema para informar al LLM qué campos enviar
- Pydantic valida los argumentos antes de ejecutar el cuerpo
"""

import json
import os
import re
from functools import lru_cache
from pathlib import Path

import psycopg2
import tenacity
from dotenv import load_dotenv
from langchain_core.tools import tool
from langsmith import traceable  # Decorador opcional para instrumentar funciones con LangSmith
from openai import OpenAI
from pgvector.psycopg2 import register_vector

from src.ingestion import embed_texts, rrf
from src.schemas import RAGResult, TicketInput

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


def _vector_search_impl(conn, query_embedding, top_k: int) -> list[tuple[int, float]]:
    """Devuelve [(chunk_id, distance), ...] ordenados por distancia coseno (menor = más parecido)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, embedding <=> %s AS distance FROM chunks ORDER BY distance LIMIT %s;",
            (query_embedding, top_k),
        )
        return cur.fetchall()


# Span propio en LangSmith -- sin esto, _vector_search es una llamada psycopg2 cruda
# que no aparece en el trace (solo lo nativo de LangChain se traza automáticamente
# con LANGCHAIN_TRACING_V2). Mismo patrón opt-in que evaluators.py: sin
# LANGCHAIN_API_KEY, corre la función pura sin decorar.
if os.getenv("LANGCHAIN_API_KEY"):
    _vector_search = traceable(name="agent.rag_search.vector", run_type="retriever")(_vector_search_impl)
else:
    _vector_search = _vector_search_impl


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    """Lee un prompt versionado desde prompts/.

    Duplicado de src/graph.py:load_prompt -- no se importa de ahi porque
    graph.py ya importa TOOLS desde este modulo (crearia un import circular).
    """
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


QUERY_REWRITE_PROMPT = _load_prompt("query_rewrite.txt")
REWRITE_MODEL = "gpt-4o-mini"

# Reintentos explicitos ante errores transitorios de OpenAI -- ver el
# comentario largo en src/graph.py::MAX_RETRIES (misma decision, mismo valor).
_MAX_RETRIES = 2

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Crea el cliente de OpenAI recien la primera vez que hace falta (mismo patron que src/ingestion.py)."""
    global _client
    if _client is None:
        _client = OpenAI(max_retries=_MAX_RETRIES)
    return _client


@lru_cache(maxsize=1024)
def _rewrite_query_impl(query: str) -> str:
    """Reescribe la query en ingles tecnico para mejorar el matching de _keyword_search.

    No se aplica a _vector_search: el embedding ya es multilingue (una pregunta
    en espanol y su traduccion caen cerca en el espacio semantico), la brecha
    ES/EN solo golpea al matching lexical exacto del full-text search.

    Cacheada (misma query -> mismo resultado, temperature=0 es determinista):
    sin esto, cada pasada de evals/retrieval_metrics.py que toca keyword search
    reescribe las mismas 520 preguntas de nuevo. maxsize=1024 acota el cache en
    un proceso de FastAPI de larga duracion, en vez de crecer sin limite.
    """
    client = _get_client()
    response = client.chat.completions.create(
        model=REWRITE_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": QUERY_REWRITE_PROMPT},
            {"role": "user", "content": query},
        ],
    )
    rewritten = response.choices[0].message.content.strip()
    return rewritten if rewritten else query


if os.getenv("LANGCHAIN_API_KEY"):
    _rewrite_query = traceable(name="agent.rag_search.rewrite", run_type="llm")(_rewrite_query_impl)
else:
    _rewrite_query = _rewrite_query_impl


def _build_or_tsquery(query: str) -> str | None:
    """Tokeniza la query, saca stopwords (_STOPWORDS) y arma 'palabra1 | palabra2 | ...'.

    None si no queda ningún término de contenido (query compuesta solo de stopwords).
    """
    tokens = re.findall(r"\w+", query.lower())
    keywords = [t for t in tokens if t not in _STOPWORDS]
    return " | ".join(keywords) if keywords else None


def _keyword_search_impl(conn, query: str, top_k: int) -> list[tuple[int, float]]:
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
    tsquery_text = _build_or_tsquery(_rewrite_query(query))
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


if os.getenv("LANGCHAIN_API_KEY"):
    _keyword_search = traceable(name="agent.rag_search.keyword", run_type="retriever")(_keyword_search_impl)
else:
    _keyword_search = _keyword_search_impl


def _hybrid_search(
    conn, query: str, query_embedding, top_k: int, candidate_k: int = 10, rrf_k: int = 1
) -> list[tuple[int, float]]:
    """Combina _vector_search + _keyword_search con RRF. Devuelve [(chunk_id, rrf_score), ...].

    rrf_k expone el parámetro k de rrf() -- default 1, no 60, desde el barrido real
    del paso 6 de 5B.4 (ver rrf() en src/ingestion.py para el detalle de la medición).
    """
    vector_results = _vector_search(conn, query_embedding, candidate_k)
    keyword_results = _keyword_search(conn, query, candidate_k)
    fused = rrf(vector_results, keyword_results, k=rrf_k)
    return fused[:top_k]


@tool(args_schema=TicketInput)
def create_ticket(summary: str, category: str, priority: str = "medium") -> str:
    """Crea un ticket y devuelve una confirmacion."""
    print(f"[create_ticket] category={category} priority={priority} summary={summary}")
    return (
        f"Ticket creado — categoria: '{category}', "
        f"prioridad: '{priority}', resumen: '{summary}'."
    )


# Reintentos ante errores transitorios de conexion a Postgres (network blip,
# pooler momentaneamente sin slots, timeout). OperationalError es la clase que
# psycopg2 usa para eso -- errores de query (sintaxis, tipos, etc.) son
# ProgrammingError/otros y no se reintentan, porque reintentar una query rota
# nunca la arregla. 3 intentos totales (igual que MAX_RETRIES=2 de OpenAI en
# graph.py: 1 intento + 2 reintentos), con backoff exponencial para no
# insistir de inmediato sobre un servicio ya saturado.
@tenacity.retry(
    retry=tenacity.retry_if_exception_type(psycopg2.OperationalError),
    wait=tenacity.wait_exponential(multiplier=0.5, min=0.5, max=4),
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
)
def _search_chunks(query: str, query_embedding, top_k: int) -> tuple[list[tuple[int, float]], list[tuple]]:
    """Abre una conexion, corre la busqueda hibrida y trae las filas de chunks.

    Retry-safe a proposito: cada intento abre una conexion NUEVA (via
    _get_connection() adentro de la funcion decorada) en vez de reintentar
    sobre una conexion que ya fallo -- una conexion rota no se arregla sola.
    """
    conn = _get_connection()
    try:
        fused = _hybrid_search(conn, query, query_embedding, top_k)
        if not fused:
            return fused, []

        ids = [chunk_id for chunk_id, _ in fused]
        with conn.cursor() as cur:
            cur.execute("SELECT id, content, source FROM chunks WHERE id = ANY(%s);", (ids,))
            rows = cur.fetchall()
        return fused, rows
    finally:
        conn.close()


@tool
def rag_search(query: str, top_k: int = 5) -> str:
    """Busca chunks relevantes combinando vector search + keyword search + RRF (Postgres)."""
    query_embedding = embed_texts([query])[0]
    fused, rows = _search_chunks(query, query_embedding, top_k)

    if not fused:
        result = RAGResult(
            content="No se encontraron resultados para esta búsqueda.",
            source="system",
            score=None,
        )
        return result.model_dump_json()

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
