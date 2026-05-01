"""
State definition para el agente RAG.

El estado es el "contenedor de datos" que viaja entre nodos del grafo.
TypedDict le dice a LangGraph qué campos hay y qué tipo tienen.
Eso permite serialización automática (guardar/cargar en checkpointer).
"""

from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Estado del agente.
    
    Campos:
    - messages: historial de mensajes (input del user, output de LLM, observaciones de tools)
    - next_action: (opcional) proxima accion que el agente quiere tomar
    """
    messages: Annotated[list[AnyMessage], add_messages]
    next_action: NotRequired[str | None]
