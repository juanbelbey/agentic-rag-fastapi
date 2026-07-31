"""Tests de reglas deterministas.

Verifican condiciones que siempre deben cumplirse sin invocar el LLM ni el grafo.
La mayoria son baratos y rapidos: sin red, sin costo, sin API key. Excepcion:
los tests de rag_search (desde 5B.2 pega contra Postgres + OpenAI de verdad)
se saltan solos si faltan OPENAI_API_KEY/DATABASE_URL -- ver skip_if_no_rag_env.

Estructura:
- TestResponseFormat: reglas sobre el formato de cualquier respuesta del agente.
- TestToolBehavior:   reglas sobre lo que devuelven las tools directamente.
"""

import os

import pytest

from src.tools import create_ticket, rag_search


def skip_if_no_rag_env() -> None:
    """rag_search() pega contra OpenAI (embeddings) y Postgres real desde 5B.2."""
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("DATABASE_URL"):
        pytest.skip("OPENAI_API_KEY/DATABASE_URL no configuradas para tests de rag_search")


# ─── Reglas sobre formato de respuesta ───────────────────────────────────────

class TestResponseFormat:
    """Reglas que aplican a cualquier string de respuesta del agente."""

    def test_valid_responses_are_not_empty(self, sample_responses):
        # Las respuestas validas nunca deben ser cadenas vacias o solo espacios.
        for response in sample_responses["valid"]:
            assert response.strip() != "", (
                f"Se detecto una respuesta vacia: {repr(response)}"
            )

    def test_valid_responses_under_1000_chars(self, sample_responses):
        # Limite de longitud: respuestas muy largas sugieren un loop o error.
        for response in sample_responses["valid"]:
            assert len(response) < 1000, (
                f"Respuesta demasiado larga ({len(response)} chars): {response[:80]}..."
            )

    def test_invalid_responses_fail_not_empty_rule(self, sample_responses):
        # Confirma que los ejemplos invalidos SI violan la regla de no-vacio.
        # Esto verifica que nuestros datos de prueba son correctos.
        for response in sample_responses["invalid"]:
            assert response.strip() == "", (
                f"Se esperaba respuesta vacia pero no lo era: {repr(response)}"
            )


# ─── Reglas sobre el comportamiento de las tools ─────────────────────────────

class TestToolBehavior:
    """Reglas sobre lo que devuelven las tools del agente de forma determinista.

    Importante: las tools tienen @tool de LangChain, entonces son objetos
    StructuredTool, no funciones Python puras. Se llaman con .invoke(dict).
    """

    def test_rag_search_contains_query_word(self):
        # Al menos una palabra del query debe aparecer en el resultado.
        skip_if_no_rag_env()
        query = "politica de reembolso"
        result = rag_search.invoke({"query": query})

        words = query.split()
        assert any(word in result for word in words), (
            f"Ninguna palabra del query '{query}' encontrada en: {result}"
        )

    def test_rag_search_returns_string(self):
        # El resultado siempre debe ser un string, nunca None ni otro tipo.
        skip_if_no_rag_env()
        result = rag_search.invoke({"query": "consulta de prueba"})
        assert isinstance(result, str)

    def test_create_ticket_contains_summary(self):
        # El resumen enviado debe aparecer en la confirmacion devuelta.
        summary = "Transmisor de presion Rosemount descalibrado en la linea de impulsion"
        result = create_ticket.invoke({"summary": summary, "category": "field_instrument_failure"})

        assert summary in result, (
            f"El summary no aparece en la respuesta de create_ticket: {result}"
        )

    def test_create_ticket_returns_string(self):
        # La confirmacion siempre debe ser un string.
        result = create_ticket.invoke({"summary": "Test ticket", "category": "undocumented_query"})
        assert isinstance(result, str)
