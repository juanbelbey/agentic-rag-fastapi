"""Tools iniciales del agente.

Cada tool empieza como una funcion normal de Python.
El decorador @tool la convierte en una tool estructurada que el agente puede invocar.
"""

from langchain_core.tools import tool


@tool
def rag_search(query: str) -> str:
    """Busca informacion en una base de conocimiento simulada."""
    return (
        "Resultado simulado de RAG para la consulta: "
        f"'{query}'. Documento encontrado: guia-interna-agentic-rag-fastapi.md"
    )


@tool
def create_ticket(summary: str, category: str) -> str:
    """Crea un ticket simulado y devuelve una confirmacion."""
    print(f"[create_ticket] category={category} summary={summary}")
    return (
        "Ticket simulado creado correctamente con categoria "
        f"'{category}' y resumen '{summary}'."
    )


TOOLS = [rag_search, create_ticket]