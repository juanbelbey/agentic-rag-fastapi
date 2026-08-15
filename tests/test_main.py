"""Tests de I/O sobre los endpoints de src/main.py (POST /chat, POST /feedback, GET /stats).

TestClient se instancia sin `with` a proposito: eso evita que corra el lifespan
de la app (que abre un pool real contra Postgres y llama checkpointer.setup()).
Verificado: sin `with`, main.pool queda en None despues de instanciar el client
y de hacer requests -- confirmado corriendo este mismo chequeo antes de escribir
el archivo. Cada test mockea via monkeypatch los globals que necesita
(main.settings/main.graph/main.pool), nunca toca la base real.
"""

from fastapi.testclient import TestClient

from src import main

client = TestClient(main.app)


class FakeMessage:
    def __init__(self, content, tool_calls=None, usage_metadata=None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.usage_metadata = usage_metadata


class FakeGraph:
    def __init__(self, result):
        self._result = result

    def invoke(self, payload, config):
        return self._result


class FakeCursor:
    def __init__(self, chat_logs, feedback):
        self._chat_logs = chat_logs
        self._feedback = feedback
        self._sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self._sql = sql

    def fetchall(self):
        return self._chat_logs if "chat_logs" in self._sql else self._feedback


class FakeConnection:
    def __init__(self, chat_logs=None, feedback=None):
        self.executed = []
        self._chat_logs = chat_logs or []
        self._feedback = feedback or []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def cursor(self, row_factory=None):
        return FakeCursor(self._chat_logs, self._feedback)


class FakePool:
    def __init__(self, chat_logs=None, feedback=None):
        self.conn = FakeConnection(chat_logs, feedback)

    def connection(self):
        return self.conn


# ─── POST /chat ──────────────────────────────────────────────────────────────

class TestChatEndpoint:
    def test_rejects_empty_message(self):
        response = client.post("/chat", json={"message": "", "thread_id": "t1"})
        assert response.status_code == 422

    def test_rejects_missing_thread_id(self):
        response = client.post("/chat", json={"message": "hola"})
        assert response.status_code == 422

    def test_500_when_not_initialized(self, monkeypatch):
        monkeypatch.setattr(main, "settings", None)
        monkeypatch.setattr(main, "graph", None)
        response = client.post("/chat", json={"message": "hola", "thread_id": "t1"})
        assert response.status_code == 500

    def test_happy_path_returns_response_and_run_id(self, monkeypatch):
        fake_result = {"messages": [FakeMessage("respuesta del agente")]}
        monkeypatch.setattr(main, "settings", object())
        monkeypatch.setattr(main, "graph", FakeGraph(fake_result))
        monkeypatch.setattr(main, "pool", None)  # sin pool: no intenta loguear a Postgres

        response = client.post("/chat", json={"message": "hola", "thread_id": "t1"})

        assert response.status_code == 200
        body = response.json()
        assert body["response"] == "respuesta del agente"
        assert body["thread_id"] == "t1"
        assert body["tool_calls_used"] == []
        assert body["run_id"]

    def test_extracts_tool_calls_used(self, monkeypatch):
        fake_result = {
            "messages": [
                FakeMessage("", tool_calls=[{"name": "rag_search"}]),
                FakeMessage("respuesta final"),
            ]
        }
        monkeypatch.setattr(main, "settings", object())
        monkeypatch.setattr(main, "graph", FakeGraph(fake_result))
        monkeypatch.setattr(main, "pool", None)

        response = client.post("/chat", json={"message": "hola", "thread_id": "t1"})

        assert response.status_code == 200
        assert response.json()["tool_calls_used"] == ["rag_search"]

    def test_agent_exception_returns_500(self, monkeypatch):
        class BrokenGraph:
            def invoke(self, *args, **kwargs):
                raise RuntimeError("boom")

        monkeypatch.setattr(main, "settings", object())
        monkeypatch.setattr(main, "graph", BrokenGraph())
        monkeypatch.setattr(main, "pool", None)

        response = client.post("/chat", json={"message": "hola", "thread_id": "t1"})
        assert response.status_code == 500


# ─── POST /feedback ────────────────────────────────────────────────────────

class TestFeedbackEndpoint:
    def test_rejects_score_out_of_range(self):
        response = client.post("/feedback", json={"run_id": "r1", "thread_id": "t1", "score": 1.5})
        assert response.status_code == 422

    def test_500_when_not_initialized(self, monkeypatch):
        monkeypatch.setattr(main, "pool", None)
        response = client.post("/feedback", json={"run_id": "r1", "thread_id": "t1", "score": 1.0})
        assert response.status_code == 500

    def test_happy_path_inserts_and_returns_ok(self, monkeypatch):
        fake_pool = FakePool()
        monkeypatch.setattr(main, "pool", fake_pool)
        monkeypatch.setattr(main, "langsmith_client", None)

        response = client.post(
            "/feedback",
            json={"run_id": "r1", "thread_id": "t1", "score": 1.0, "comment": "genial"},
        )

        assert response.status_code == 201
        assert response.json() == {"status": "ok"}
        assert len(fake_pool.conn.executed) == 1


# ─── GET /stats ──────────────────────────────────────────────────────────────

class TestStatsEndpoint:
    def test_500_when_not_initialized(self, monkeypatch):
        monkeypatch.setattr(main, "pool", None)
        response = client.get("/stats")
        assert response.status_code == 500

    def test_returns_chat_logs_and_feedback(self, monkeypatch):
        chat_logs = [{"latency_ms": 100}]
        feedback = [{"score": 1.0}]
        monkeypatch.setattr(main, "pool", FakePool(chat_logs=chat_logs, feedback=feedback))

        response = client.get("/stats")

        assert response.status_code == 200
        body = response.json()
        assert body["chat_logs"] == chat_logs
        assert body["feedback"] == feedback
