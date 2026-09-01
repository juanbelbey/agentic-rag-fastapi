"""Tests del formatter de logging estructurado (sin tocar el logger real)."""

import json
import logging

from src.logging_config import JSONFormatter


def _make_record(message="algo paso", extra=None, exc_info=None):
    record = logging.LogRecord(
        name="agentic_rag",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )
    for key, value in (extra or {}).items():
        setattr(record, key, value)
    return record


class TestJSONFormatter:
    def test_output_is_valid_json(self):
        line = JSONFormatter().format(_make_record())
        json.loads(line)  # no debe tirar

    def test_includes_level_logger_and_message(self):
        payload = json.loads(JSONFormatter().format(_make_record("rag_search_failed")))
        assert payload["level"] == "ERROR"
        assert payload["logger"] == "agentic_rag"
        assert payload["message"] == "rag_search_failed"

    def test_extra_fields_become_top_level_keys(self):
        # Esto es lo que hace al log "estructurado": run_id/error_type quedan
        # como campos propios, no mezclados en el texto del mensaje.
        record = _make_record(extra={"run_id": "abc-123", "error_type": "RuntimeError"})
        payload = json.loads(JSONFormatter().format(record))
        assert payload["run_id"] == "abc-123"
        assert payload["error_type"] == "RuntimeError"

    def test_exc_info_is_included_when_present(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = _make_record("fallo", exc_info=sys.exc_info())
        payload = json.loads(JSONFormatter().format(record))
        assert "ValueError" in payload["exc_info"]
        assert "boom" in payload["exc_info"]
