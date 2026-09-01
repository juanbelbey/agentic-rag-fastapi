"""Logging estructurado: cada log queda como una linea JSON, no texto libre.

Por que: un log de texto libre ("error al buscar") solo se puede leer. Un
log estructurado ("evento=rag_search_failed run_id=... error_type=...") se
puede filtrar y contar -- es lo que permite responder "¿cuantos fallos hubo
hoy y de que tipo?" en vez de solo poder mirar la ultima linea.

Distinto de LangSmith (traza UNA ejecucion puntual para debuggearla paso a
paso): esto es para contar/filtrar fallos a lo largo del tiempo, no para
inspeccionar una corrida especifica.
"""

import json
import logging

# Claves que trae cualquier LogRecord por defecto -- lo que se pasa via
# extra={...} en una llamada a logger queda AFUERA de este set, y es
# justamente lo que queremos capturar como campos propios del JSON.
_DEFAULT_RECORD_KEYS = logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()


class JSONFormatter(logging.Formatter):
    """Convierte un LogRecord en una linea JSON con los campos de `extra`."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _DEFAULT_RECORD_KEYS
        }
        payload.update(extra)

        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Configura el root logger para emitir JSON a stdout (Render lee stdout)."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
