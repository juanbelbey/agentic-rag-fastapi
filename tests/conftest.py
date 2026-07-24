"""Fixtures compartidos para la capa de tests del proyecto."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

# Carga el .env desde la raiz del proyecto antes de que cualquier test corra.
load_dotenv(Path(__file__).parent.parent / ".env")

from src.graph import graph_builder


@pytest.fixture(scope="session")
def agent_graph():
    """Compila el grafo con MemorySaver para tests: no depende de Postgres."""
    return graph_builder.compile(checkpointer=MemorySaver())


@pytest.fixture
def sample_responses() -> dict[str, list[str]]:
    """Ejemplos de respuestas validas/invalidas para reglas deterministicas."""
    return {
        "valid": [
            "Hola, te ayudo con eso.",
            "Segun la busqueda simulada, revisa la guia interna de reembolsos.",
        ],
        "invalid": [
            "",
            " ",
        ],
    }


@pytest.fixture
def invoke_agent(agent_graph) -> Callable[[str, str | None], dict[str, Any]]:
    """Helper para invocar el grafo en tests con thread_id configurable."""

    def _invoke(message: str, thread_id: str | None = None) -> dict[str, Any]:
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY no configurada para tests que invocan el agente")

        tid = thread_id or f"test-{uuid.uuid4()}"
        config = {"configurable": {"thread_id": tid}}
        return agent_graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )

    return _invoke
