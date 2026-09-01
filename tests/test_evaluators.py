"""Tests unitarios de evals/evaluators.py -- solo las funciones code-based/puras
(extract_score, tool_call_evaluator, convergence_evaluator). relevance_evaluator/
accuracy_evaluator pegan contra el LLM juez y no se testean aca (ver test_evals.py).
"""

from types import SimpleNamespace

import pytest

from evals.evaluators import convergence_evaluator, extract_score, tool_call_evaluator


# ─── extract_score() ──────────────────────────────────────────────────────────

class TestExtractScore:
    def test_extracts_single_digit(self):
        assert extract_score("4") == 4

    def test_extracts_digit_from_surrounding_text(self):
        assert extract_score("Numero: 5") == 5

    def test_extracts_first_valid_digit_when_several_appear(self):
        # re.search encuentra el primer match de izquierda a derecha -- no el
        # "mas relevante", el primero. Documentado con este test porque no es
        # obvio a simple vista.
        assert extract_score("El score es 2, no 4") == 2

    def test_raises_when_no_digit_1_to_5_present(self):
        with pytest.raises(ValueError):
            extract_score("no hay ningun numero valido aca")

    def test_raises_when_only_out_of_range_digits_present(self):
        # 0, 6, 7, 8, 9 quedan fuera del rango [1-5] a proposito.
        with pytest.raises(ValueError):
            extract_score("score: 0 o quizas 9")


# ─── tool_call_evaluator() ────────────────────────────────────────────────────

class TestToolCallEvaluator:
    def test_true_when_expected_tool_was_called(self):
        trace = {"messages": [SimpleNamespace(tool_calls=[{"name": "create_ticket"}])]}
        assert tool_call_evaluator(trace, "create_ticket") is True

    def test_false_when_a_different_tool_was_called(self):
        trace = {"messages": [SimpleNamespace(tool_calls=[{"name": "rag_search"}])]}
        assert tool_call_evaluator(trace, "create_ticket") is False

    def test_false_when_no_tool_was_called(self):
        trace = {"messages": [SimpleNamespace(tool_calls=[]), SimpleNamespace(content="hola")]}
        assert tool_call_evaluator(trace, "create_ticket") is False

    def test_accepts_a_plain_list_of_messages_not_only_a_dict(self):
        # trace = state["messages"] o state directamente, ver docstring de la funcion.
        trace = [SimpleNamespace(tool_calls=[{"name": "rag_search"}])]
        assert tool_call_evaluator(trace, "rag_search") is True


# ─── convergence_evaluator() ──────────────────────────────────────────────────

class TestConvergenceEvaluator:
    def test_counts_messages_in_a_dict_trace(self):
        trace = {"messages": [SimpleNamespace(), SimpleNamespace(), SimpleNamespace()]}
        assert convergence_evaluator(trace) == 3

    def test_counts_messages_in_a_plain_list_trace(self):
        trace = [SimpleNamespace(), SimpleNamespace()]
        assert convergence_evaluator(trace) == 2

    def test_raises_type_error_for_unsupported_trace(self):
        with pytest.raises(TypeError):
            convergence_evaluator(42)
