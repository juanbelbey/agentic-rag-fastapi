"""Tools del agente con schemas Pydantic.

args_schema conecta cada tool con su modelo de validación:
- LangChain usa el schema para informar al LLM qué campos enviar
- Pydantic valida los argumentos antes de ejecutar el cuerpo
"""

import json

import numpy as np
from langchain_core.tools import tool

from src.ingestion import InMemoryIndex, embed_texts
from src.schemas import RAGResult, TicketInput

# Índice global en memoria — se construye una vez con build_index() al arrancar.
# Arranca vacío; rag_search() lo detecta y avisa en vez de romper.
_index: InMemoryIndex = InMemoryIndex()


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
    """Busca los chunks más relevantes en el índice en memoria y devuelve los resultados como JSON."""
    if not _index.is_ready():
        result = RAGResult(
            content="El índice aún no está cargado. Llama a build_index() primero.",
            source="system",
            score=None,
        )
        return result.model_dump_json()

    # 1. Vectorizar la query
    query_vec = embed_texts([query])[0]  # forma (1536,)

    # 2. Cosine similarity contra todos los chunks del índice
    norms = np.linalg.norm(_index.embeddings, axis=1) * np.linalg.norm(query_vec)
    scores = (_index.embeddings @ query_vec) / norms  # forma (N,)

    # 3. Top-K índices ordenados de mayor a menor score
    top_indices = np.argsort(scores)[::-1][:top_k]

    # 4. Armar resultados
    results = [
        RAGResult(
            content=_index.chunks[i],
            source=_index.sources[i],
            score=float(scores[i]),
        )
        for i in top_indices
    ]

    return json.dumps([r.model_dump() for r in results])


TOOLS = [rag_search, create_ticket]
