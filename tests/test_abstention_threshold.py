"""Tests unitarios de la logica pura de evals/abstention_threshold.py (Fase 4).

build_threshold_range()/sweep_thresholds() no llaman a OpenAI ni Postgres --
solo hacen cuentas sobre scores ya calculados. Se testean con datos sinteticos
a proposito: esto verifica que el CONTEO de falsos positivos/negativos es
correcto, no que un umbral en particular separe bien (eso ya se midio con
datos reales y quedo documentado, no repetido, en EXPERIMENTS.md).
"""

from evals.abstention_threshold import build_threshold_range, sweep_thresholds


class TestBuildThresholdRange:
    def test_range_spans_observed_min_to_max(self):
        scored = [{"top_distance": 0.2}, {"top_distance": 0.8}, {"top_distance": 0.5}]
        thresholds = build_threshold_range(scored, steps=4)
        assert thresholds[0] == 0.2
        assert thresholds[-1] == 0.8
        assert len(thresholds) == 5  # steps + 1

    def test_single_value_returns_that_value_alone(self):
        # Sin esto, (high - low) / steps divide por cero.
        scored = [{"top_distance": 0.5}, {"top_distance": 0.5}]
        assert build_threshold_range(scored, steps=10) == [0.5]


class TestSweepThresholds:
    def test_low_threshold_rejects_everything(self):
        # Distancia: se abstiene cuando top_distance > threshold (ver docstring
        # de sweep_thresholds) -- threshold por debajo de toda distancia
        # observada rechaza todo: FN=100% (answerable rechazadas), FP=0.
        answerable = [{"top_distance": 0.3}, {"top_distance": 0.4}]
        unanswerable = [{"top_distance": 0.6}, {"top_distance": 0.7}]
        rows = sweep_thresholds(answerable, unanswerable, [0.1])
        row = rows[0]
        assert row["false_negatives"] == 2
        assert row["false_positives"] == 0

    def test_high_threshold_lets_everything_through(self):
        # threshold por encima de toda distancia observada: nada se rechaza
        # (FN=0), pero tampoco se filtra ningun unanswerable (FP=100%).
        answerable = [{"top_distance": 0.3}, {"top_distance": 0.4}]
        unanswerable = [{"top_distance": 0.6}, {"top_distance": 0.7}]
        rows = sweep_thresholds(answerable, unanswerable, [0.9])
        row = rows[0]
        assert row["false_negatives"] == 0
        assert row["false_positives"] == 2

    def test_boundary_is_inclusive_for_false_positives(self):
        # top_distance == threshold cuenta como "acepta" (FP), no como rechazo --
        # ver el <= en sweep_thresholds().
        answerable = [{"top_distance": 0.5}]
        unanswerable = [{"top_distance": 0.5}]
        rows = sweep_thresholds(answerable, unanswerable, [0.5])
        row = rows[0]
        assert row["false_negatives"] == 0
        assert row["false_positives"] == 1

    def test_rates_are_fractions_of_group_size(self):
        answerable = [{"top_distance": 0.9}] * 4  # los 4 quedan por encima del umbral -> rechazadas
        unanswerable = [{"top_distance": 0.1}] * 2  # los 2 quedan por debajo -> aceptadas
        rows = sweep_thresholds(answerable, unanswerable, [0.5])
        row = rows[0]
        assert row["false_negative_rate"] == 1.0
        assert row["false_positive_rate"] == 1.0
