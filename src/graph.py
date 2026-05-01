"""Grafo minimo del agente con LLM, tools y persistencia en memoria."""

from typing import Literal

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.state import AgentState
from src.tools import TOOLS


MODEL_NAME = "gpt-4o-mini"
SYSTEM_PROMPT = (
    "You are the first local skeleton of an agentic RAG assistant. "
    "Use tools when they help answer the user clearly."
)


def get_bound_llm() -> ChatOpenAI:
    """Crea el modelo con tools enlazadas solo cuando hace falta invocarlo."""
    # "-> ChatOpenAI" es una anotacion de tipo de retorno (no ejecuta nada por si sola).
    # Esta funcion no recibe parametros; construye y devuelve un LLM listo para tools.
    return ChatOpenAI(model=MODEL_NAME).bind_tools(TOOLS)


def agent_node(state: AgentState) -> AgentState:
    """Llama al modelo y devuelve el siguiente mensaje del agente."""
    llm = get_bound_llm()
    # El * desempaqueta la lista: [a, *[b, c]] -> [a, b, c].
    # Asi evitamos enviar una lista anidada de mensajes al modelo.
    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), *state["messages"]])
    # El nodo devuelve SOLO el parche de estado que produce.
    # Con add_messages en AgentState, LangGraph anexa este mensaje al historial.
    return {"messages": [response]}


def route_after_agent(state: AgentState) -> Literal["tools", "__end__"]:
    """Decide si el agente debe usar tools o terminar la ejecucion."""
    last_message = state["messages"][-1]

    # getattr(obj, "attr", default) lee un atributo de forma segura.
    # Si last_message no tiene tool_calls, devuelve None y no rompe.
    if getattr(last_message, "tool_calls", None):
        return "tools"

    return END


tool_node = ToolNode(TOOLS)

graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", route_after_agent)
graph_builder.add_edge("tools", "agent")

checkpointer = MemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)