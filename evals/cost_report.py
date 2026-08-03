"""Reporta costo/tokens reales por variante, leyendo los traces de LangSmith
asociados a los run_id guardados en evals/results/*.json.

No se puede calcular el costo desde el JSON de resultados solo (no guarda
tokens) -- se reconstruye consultando cada trace en LangSmith, que ya calcula
total_cost agregando todo el arbol de la corrida (LLM calls + tool calls).

Script manual (python -m evals.cost_report <archivo1.json> <archivo2.json> ...),
no lo llama la app ni CI -- mismo patron que retrieval_metrics.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from langsmith import Client


def report(paths: list[Path]) -> None:
    load_dotenv(ROOT_DIR / ".env")
    client = Client()

    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        run_ids = [r["run_id"] for r in data["results"] if r.get("run_id")]

        # list_runs con run_ids trae todo en pocas llamadas -- read_run() una
        # corrida a la vez pega el rate limit de LangSmith con 48 corridas seguidas.
        runs = list(client.list_runs(run_ids=run_ids))

        total_tokens = 0
        total_cost = 0.0
        missing = 0
        for run in runs:
            if run.total_cost is None:
                missing += 1
                continue
            total_tokens += run.total_tokens or 0
            total_cost += float(run.total_cost)

        n = len(run_ids) - missing
        avg_cost = total_cost / n if n else 0.0
        print(
            f"{path.stem:30s} casos={n:3d}  tokens_totales={total_tokens:7d}  "
            f"costo_total=${total_cost:.4f}  costo_x_caso=${avg_cost:.5f}"
            + (f"  (sin costo: {missing})" if missing else "")
        )


if __name__ == "__main__":
    paths = [Path(arg) for arg in sys.argv[1:]]
    if not paths:
        raise SystemExit("Uso: python -m evals.cost_report <archivo1.json> [archivo2.json ...]")
    report(paths)
