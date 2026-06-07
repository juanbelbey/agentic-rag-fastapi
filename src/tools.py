# src/tools.py
"""Tools del agente con schemas Pydantic.

args_schema conecta cada tool con su modelo de validación:
- LangChain usa el schema para informar al LLM qué campos enviar
- Pydantic valida los argumentos antes de ejecutar el cuerpo
"""

from langchain_core.tools import tool

from src.schemas import RAGResult, TicketInput


@tool(args_schema=TicketInput)
def create_ticket(summary: str, category: str, priority: str = "medium") -> str:
    """Crea un ticket y devuelve una confirmacion."""
    print(f"[create_ticket] category={category} priority={priority} summary={summary}")
    return (
        f"Ticket creado — categoria: '{category}', "
        f"prioridad: '{priority}', resumen: '{summary}'."
    )


@tool
def rag_search(query: str) -> str:
    """Busca informacion en la base de conocimiento."""
    result = RAGResult(
        content=f"Resultado simulado para: '{query}'",
        source="guia-interna-agentic-rag-fastapi.md",
        score=None,
    )
    return result.model_dump_json()


TOOLS = [rag_search, create_ticket]