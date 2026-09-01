"""Grafo minimo del agente con LLM, tools y persistencia en memoria."""

from pathlib import Path
from typing import Literal

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.state import AgentState
from src.tools import TOOLS


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    """Lee un system prompt versionado desde prompts/."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.3
SYSTEM_PROMPT = load_prompt("system_prompt_direct_answer.txt")

# Limite explicito de pasos del grafo (agent -> tools -> agent -> ...) antes de
# tirar GraphRecursionError. Antes no se fijaba en ningun lado, asi que
# quedaba en el default de LangGraph -- que en la version instalada de este
# proyecto es 10007, no el 25 clasico de versiones viejas. Practicamente sin
# techo: un agente que entra en loop sin converger tendria margen para miles
# de llamadas reales a OpenAI antes de frenar solo. Una conversacion normal
# de este agente usa entre 2 y 6 pasos (agent -> tools -> agent, a veces con
# rag_search + create_ticket en la misma vuelta); 25 da margen generoso para
# eso y corta un loop real mucho antes de que salga caro.
RECURSION_LIMIT = 25

# Reintentos explicitos ante errores transitorios de OpenAI (rate limit,
# timeout, conexion). Antes no se fijaba nunca, asi que el SDK de openai
# aplicaba su propio default (tambien 2) sin que quedara documentado ni
# testeado en este proyecto -- ver Fase 2 del esquema de profesionalizacion
# (agent reliability). Valor bajo a proposito: /chat es sincronico y el
# usuario espera la respuesta, cada retry suma latencia real. Mismo patron
# en src/tools.py y src/ingestion.py.
MAX_RETRIES = 2


def get_bound_llm(model_name: str = MODEL_NAME, temperature: float = TEMPERATURE) -> ChatOpenAI:
    """Crea el modelo con tools enlazadas solo cuando hace falta invocarlo."""
    return ChatOpenAI(
        model=model_name, max_tokens=800, temperature=temperature, max_retries=MAX_RETRIES
    ).bind_tools(TOOLS)


def build_agent_node(system_prompt: str = SYSTEM_PROMPT, model_name: str = MODEL_NAME, temperature: float = TEMPERATURE):
    """Devuelve un agent_node cerrado sobre un prompt, modelo y temperatura dados (para comparar variantes en evals)."""

    def agent_node(state: AgentState) -> AgentState:
        llm = get_bound_llm(model_name, temperature)
        # El * desempaqueta la lista: [a, *[b, c]] -> [a, b, c].
        # Asi evitamos enviar una lista anidada de mensajes al modelo.
        response = llm.invoke([SystemMessage(content=system_prompt), *state["messages"]])
        # El nodo devuelve SOLO el parche de estado que produce.
        # Con add_messages en AgentState, LangGraph anexa este mensaje al historial.
        return {"messages": [response]}

    return agent_node


def route_after_agent(state: AgentState) -> Literal["tools", "__end__"]:
    """Decide si el agente debe usar tools o terminar la ejecucion."""
    last_message = state["messages"][-1]

    # getattr(obj, "attr", default) lee un atributo de forma segura.
    # Si last_message no tiene tool_calls, devuelve None y no rompe.
    if getattr(last_message, "tool_calls", None):
        return "tools"

    return END


def build_graph(system_prompt: str = SYSTEM_PROMPT, model_name: str = MODEL_NAME, temperature: float = TEMPERATURE) -> StateGraph:
    """Arma el StateGraph sin compilar, con el prompt, modelo y temperatura dados."""
    builder = StateGraph(AgentState)
    builder.add_node("agent", build_agent_node(system_prompt, model_name, temperature))
    builder.add_node("tools", ToolNode(TOOLS))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_after_agent)
    builder.add_edge("tools", "agent")
    return builder


graph_builder = build_graph()