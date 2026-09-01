"""Tests estructurales de evals/critical_eval_set.json (Fase 4 -- ver EXPERIMENTS.md).

Guardia de regresion: si alguien edita el archivo a mano y rompe el esquema
(falta un campo, un id duplicado, una categoria mal escrita), esto lo detecta
sin necesidad de correr ningun script contra OpenAI/Postgres reales.
"""

import json
from pathlib import Path

CRITICAL_SET_PATH = Path(__file__).parent.parent / "evals" / "critical_eval_set.json"

ANSWERABLE_CATEGORIES = {"factual", "procedimental", "inferencial"}
UNANSWERABLE_CATEGORIES = {"relacionado_ausente", "producto_no_documentado", "fuera_de_dominio", "ambigua", "mixta"}


def load_cases() -> list[dict]:
    return json.loads(CRITICAL_SET_PATH.read_text(encoding="utf-8"))


class TestCriticalEvalSetSchema:
    def test_file_has_28_cases(self):
        # 15 answerable + 13 unanswerable, ver diseño en EXPERIMENTS.md.
        assert len(load_cases()) == 28

    def test_ids_are_unique(self):
        cases = load_cases()
        ids = [c["id"] for c in cases]
        assert len(ids) == len(set(ids))

    def test_every_case_has_required_base_fields(self):
        for case in load_cases():
            assert "id" in case
            assert "question" in case and case["question"].strip()
            assert isinstance(case["answerable"], bool)
            assert "category" in case

    def test_answerable_cases_use_golden_set_categories(self):
        answerable = [c for c in load_cases() if c["answerable"]]
        assert len(answerable) == 15
        for case in answerable:
            assert case["category"] in ANSWERABLE_CATEGORIES
            # Curadas del golden set existente, no escritas de cero -- ver EXPERIMENTS.md.
            assert "golden_set_id" in case
            assert "expected_answer" in case and case["expected_answer"].strip()

    def test_unanswerable_cases_use_expected_subcategories(self):
        unanswerable = [c for c in load_cases() if not c["answerable"]]
        assert len(unanswerable) == 13
        for case in unanswerable:
            assert case["category"] in UNANSWERABLE_CATEGORIES
            assert "expected_behavior" in case

    def test_ambiguous_cases_expect_clarification_not_abstention(self):
        # "ambigua" es un caso distinto al resto: lo correcto es pedir
        # aclaracion, no decir "no tengo informacion" -- ver diseño original.
        ambiguous = [c for c in load_cases() if c["category"] == "ambigua"]
        assert len(ambiguous) == 3
        assert all(c["expected_behavior"] == "clarify" for c in ambiguous)

    def test_mixed_cases_expect_partial_abstention(self):
        mixed = [c for c in load_cases() if c["category"] == "mixta"]
        assert len(mixed) == 2
        assert all(c["expected_behavior"] == "partial_abstain" for c in mixed)
