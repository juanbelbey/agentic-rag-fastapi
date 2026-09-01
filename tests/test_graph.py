"""Tests de configuracion de src/graph.py (sin invocar el LLM real)."""

from types import SimpleNamespace

from langgraph.graph import END

from src.graph import (
    MAX_RETRIES,
    RECURSION_LIMIT,
    SYSTEM_PROMPT,
    get_bound_llm,
    route_after_agent,
)


class TestGetBoundLLM:
    def test_llm_has_explicit_max_retries(self, monkeypatch):
        # Antes de la Fase 2 (agent reliability) ChatOpenAI se creaba sin
        # max_retries, asi que quedaba en manos del default implicito del SDK
        # de openai -- este test fija esa decision como algo explicito.
        # ChatOpenAI() solo exige que la key este presente (no la valida) --
        # una key dummy alcanza para construir el objeto sin pegar a la red.
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")

        llm = get_bound_llm()

        assert llm.bound.max_retries == MAX_RETRIES


class TestRecursionLimit:
    def test_is_explicit_and_far_below_the_langgraph_default(self):
        # El default de LangGraph en este proyecto es 10007 (ver comentario en
        # src/graph.py) -- lo que importa aca es que quede muy por debajo de
        # eso, no un numero magico exacto.
        assert 0 < RECURSION_LIMIT < 100


# ─── route_after_agent() en aislamiento ───────────────────────────────────────
# Sin compilar el grafo ni invocar el LLM: state es un dict a mano, last_message
# un objeto minimo con (o sin) tool_calls.

class TestRouteAfterAgent:
    def test_routes_to_tools_when_last_message_has_tool_calls(self):
        state = {"messages": [SimpleNamespace(tool_calls=[{"name": "rag_search"}])]}
        assert route_after_agent(state) == "tools"

    def test_routes_to_end_when_tool_calls_is_empty_list(self):
        # [] es falsy -- getattr(..., None) or [] en route_after_agent depende
        # de esto para no confundir "no llamo tools" con "atributo ausente".
        state = {"messages": [SimpleNamespace(tool_calls=[])]}
        assert route_after_agent(state) == END

    def test_routes_to_end_when_message_has_no_tool_calls_attribute(self):
        # Mensajes de tipo texto plano (ej. HumanMessage) no tienen tool_calls --
        # route_after_agent usa getattr(..., None) justamente para no romper aca.
        state = {"messages": [SimpleNamespace(content="hola")]}
        assert route_after_agent(state) == END


# ─── Regresion de las reglas de abstencion del prompt (Fase 4) ────────────────
# No hay logica de umbral en codigo (RRF y distancia coseno se descartaron por
# evidencia -- ver EXPERIMENTS.md): la abstencion depende 100% de estas
# instrucciones en el prompt. Sin este test, editar el prompt podria borrar una
# regla sin que nada lo detecte hasta que fallen casos reales de nuevo.
class TestAbstentionPromptRules:
    def test_rejects_out_of_domain_questions(self):
        assert "no tiene relacion con instrumentacion de campo" in SYSTEM_PROMPT

    def test_does_not_generalize_between_similar_products(self):
        assert "no generalices a partir de otros modelos similares" in SYSTEM_PROMPT

    def test_asks_for_clarification_on_ambiguous_questions(self):
        assert "pedi la aclaracion necesaria" in SYSTEM_PROMPT

    def test_verifies_each_part_of_multi_claim_questions(self):
        assert "verifica cada una por separado" in SYSTEM_PROMPT

    def test_cites_document_name_only_never_a_url(self):
        assert "nunca inventes una URL ni un link" in SYSTEM_PROMPT
