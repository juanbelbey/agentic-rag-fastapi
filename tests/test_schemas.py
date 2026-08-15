"""Tests de validacion de los modelos Pydantic en src/schemas.py.

Cada modelo es un contrato en un borde del sistema (ver docstring del modulo) --
estos tests confirman que ese contrato realmente rechaza datos invalidos, no
solo que existe.
"""

import pytest
from pydantic import ValidationError

from src.schemas import ChatRequest, FeedbackInput, RAGResult, TicketInput


# ─── ChatRequest ─────────────────────────────────────────────────────────────

class TestChatRequest:
    def test_valid_payload(self):
        req = ChatRequest(message="hola", thread_id="t1")
        assert req.message == "hola"
        assert req.thread_id == "t1"

    def test_empty_message_is_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="", thread_id="t1")

    def test_empty_thread_id_is_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="hola", thread_id="")

    def test_missing_thread_id_is_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="hola")


# ─── FeedbackInput ───────────────────────────────────────────────────────────

class TestFeedbackInput:
    def test_valid_payload_without_comment(self):
        fb = FeedbackInput(run_id="r1", thread_id="t1", score=1.0)
        assert fb.comment is None

    def test_score_above_one_is_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackInput(run_id="r1", thread_id="t1", score=1.5)

    def test_score_below_zero_is_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackInput(run_id="r1", thread_id="t1", score=-0.1)

    @pytest.mark.parametrize("score", [0.0, 0.5, 1.0])
    def test_score_within_range_is_accepted(self, score):
        fb = FeedbackInput(run_id="r1", thread_id="t1", score=score)
        assert fb.score == score


# ─── TicketInput ─────────────────────────────────────────────────────────────

class TestTicketInput:
    def test_valid_payload_defaults_priority_to_medium(self):
        ticket = TicketInput(summary="Falla en transmisor de presion", category="field_instrument_failure")
        assert ticket.priority == "medium"

    def test_summary_too_short_is_rejected(self):
        with pytest.raises(ValidationError):
            TicketInput(summary="abc", category="field_instrument_failure")

    def test_summary_too_long_is_rejected(self):
        with pytest.raises(ValidationError):
            TicketInput(summary="x" * 301, category="field_instrument_failure")

    def test_invalid_category_is_rejected(self):
        with pytest.raises(ValidationError):
            TicketInput(summary="Falla en transmisor de presion", category="categoria_inventada")

    def test_invalid_priority_is_rejected(self):
        with pytest.raises(ValidationError):
            TicketInput(
                summary="Falla en transmisor de presion",
                category="field_instrument_failure",
                priority="urgentisimo",
            )


# ─── RAGResult ───────────────────────────────────────────────────────────────

class TestRAGResult:
    def test_valid_payload_without_score(self):
        result = RAGResult(content="texto recuperado", source="manual.pdf")
        assert result.score is None

    def test_empty_content_is_rejected(self):
        with pytest.raises(ValidationError):
            RAGResult(content="", source="manual.pdf")

    def test_negative_score_is_rejected(self):
        with pytest.raises(ValidationError):
            RAGResult(content="texto", source="manual.pdf", score=-0.1)
