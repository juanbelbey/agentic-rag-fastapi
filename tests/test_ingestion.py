"""Tests unitarios de src/ingestion.py: chunk_text() y rrf().

Ambas son funciones puras (sin red, sin costo, sin API key) -- a diferencia de
embed_texts(), que si pega contra OpenAI y no se testea aca.
"""

import pytest

from src.ingestion import chunk_text, rrf


# ─── chunk_text() ────────────────────────────────────────────────────────────

class TestChunkText:
    def test_empty_text_returns_no_chunks(self):
        assert chunk_text("", source="doc.txt") == []

    def test_whitespace_only_text_returns_no_chunks(self):
        # Cada chunk se recorta con .strip() antes de agregarse; si queda
        # vacio, se descarta.
        assert chunk_text("   \n  ", source="doc.txt", size=500, step=250) == []

    def test_text_shorter_than_size_returns_single_chunk(self):
        result = chunk_text("hola mundo", source="doc.txt", size=500, step=250)
        assert result == [("hola mundo", "doc.txt")]

    def test_sliding_window_with_overlap(self):
        # size=4, step=2 sobre "abcdefghij" (10 chars): ventanas que arrancan
        # en 0,2,4,6,8 (en 10 el while para: 10 < len(text)=10 es False).
        result = chunk_text("abcdefghij", source="doc.txt", size=4, step=2)
        assert result == [
            ("abcd", "doc.txt"),
            ("cdef", "doc.txt"),
            ("efgh", "doc.txt"),
            ("ghij", "doc.txt"),
            ("ij", "doc.txt"),
        ]

    def test_every_chunk_keeps_the_given_source(self):
        result = chunk_text("texto de prueba con varias palabras", source="manual.pdf", size=10, step=5)
        assert all(source == "manual.pdf" for _, source in result)

    def test_no_chunk_is_empty(self):
        result = chunk_text("a  " * 20, source="doc.txt", size=5, step=3)
        assert all(chunk.strip() != "" for chunk, _ in result)


# ─── rrf() ────────────────────────────────────────────────────────────────

class TestRRF:
    def test_both_lists_empty_returns_empty(self):
        assert rrf([], []) == []

    def test_single_list_ranks_by_position_not_original_score(self):
        # El score original (segundo elemento de la tupla) se descarta -- solo
        # importa la posicion en la lista.
        result = rrf([(1, 0.99), (2, 0.01)], [])
        assert [idx for idx, _ in result] == [1, 2]

    def test_item_in_both_lists_beats_item_top_in_only_one(self):
        # Mismo caso que documenta el docstring de rrf(): un chunk que aparece
        # en ambas listas (aunque no sea el primero en ninguna) le gana a uno
        # que es #1 en una sola lista.
        vector_results = [(1, 0.9)]  # idx 1: primero en vector
        keyword_results = [(2, 0.9), (1, 0.5)]  # idx 2: primero en keyword; idx 1: segundo

        result = rrf(vector_results, keyword_results, k=1)

        scores = dict(result)
        assert scores[1] > scores[2]
        assert [idx for idx, _ in result][0] == 1

    def test_scores_match_reciprocal_rank_formula(self):
        result = rrf([(10, 0.0)], [(10, 0.0)], k=1)
        # idx 10 esta en rank 0 de ambas listas: 1/(k+0+1) + 1/(k+0+1) = 2 * 0.5
        assert result == [(10, pytest.approx(1.0))]

    def test_lower_k_gives_more_weight_to_exact_rank(self):
        # A menor k, la diferencia de score entre rank 0 y rank 1 es mayor.
        list_a = [(1, 0.0), (2, 0.0)]
        gap_k1 = dict(rrf(list_a, [], k=1))[1] - dict(rrf(list_a, [], k=1))[2]
        gap_k60 = dict(rrf(list_a, [], k=60))[1] - dict(rrf(list_a, [], k=60))[2]
        assert gap_k1 > gap_k60
