"""Tests de retry/backoff de src/tools.py (sin Postgres/OpenAI reales).

_search_chunks() abre conexion nueva en cada intento (ver comentario en
src/tools.py) -- estos tests mockean _get_connection y _hybrid_search para
simular fallos transitorios sin tocar la base real.
"""

import psycopg2
import pytest

from src import tools


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, rows):
        self._rows = rows
        self.closed = False

    def cursor(self):
        return FakeCursor(self._rows)

    def close(self):
        self.closed = True


class TestSearchChunksRetry:
    def test_retries_on_operational_error_then_succeeds(self, monkeypatch):
        attempts = {"count": 0}

        def flaky_get_connection():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise psycopg2.OperationalError("simulado: conexion caida")
            return FakeConnection(rows=[(1, "contenido de prueba", "doc.pdf")])

        monkeypatch.setattr(tools, "_get_connection", flaky_get_connection)
        monkeypatch.setattr(tools, "_hybrid_search", lambda conn, query, embedding, top_k: [(1, 0.5)])

        fused, rows = tools._search_chunks("consulta", query_embedding=[0.0], top_k=5)

        # Fallo dos veces (conexion nueva cada vez) y recien la 3ra tuvo exito.
        assert attempts["count"] == 3
        assert fused == [(1, 0.5)]
        assert rows == [(1, "contenido de prueba", "doc.pdf")]

    def test_gives_up_after_max_attempts(self, monkeypatch):
        attempts = {"count": 0}

        def always_fails():
            attempts["count"] += 1
            raise psycopg2.OperationalError("simulado: siempre caida")

        monkeypatch.setattr(tools, "_get_connection", always_fails)

        with pytest.raises(psycopg2.OperationalError):
            tools._search_chunks("consulta", query_embedding=[0.0], top_k=5)

        # 3 intentos totales (stop_after_attempt(3)), no reintentos infinitos.
        assert attempts["count"] == 3

    def test_does_not_retry_non_transient_errors(self, monkeypatch):
        # ProgrammingError (ej. columna que no existe) no es un fallo transitorio --
        # reintentar una query rota nunca la arregla, tenacity debe dejarlo pasar
        # de una sin reintentar.
        attempts = {"count": 0}

        def raises_programming_error():
            attempts["count"] += 1
            raise psycopg2.ProgrammingError("simulado: columna inexistente")

        monkeypatch.setattr(tools, "_get_connection", raises_programming_error)

        with pytest.raises(psycopg2.ProgrammingError):
            tools._search_chunks("consulta", query_embedding=[0.0], top_k=5)

        assert attempts["count"] == 1
