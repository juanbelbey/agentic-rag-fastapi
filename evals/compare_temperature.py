"""Sweep de temperatura sobre la combinacion prompt x modelo ganadora (punto 4 del
plan de entrega LLM Zoomcamp, extension acordada con Juan tras ver que dos corridas
identicas de compare_prompts.py con temperature=1.0 (default de OpenAI, nunca fijado
en get_bound_llm()) dieron accuracy distinta -- ej. baseline_mini 3.60 -> 3.69,
baseline_nano 4.27 -> 4.12 -- solo por la aleatoriedad del muestreo.

Fija prompt="direct_answer" y modelo=gpt-4o-mini (ganador de compare_prompts.py,
ver evals/results/2026-08-01/) y varia SOLO temperature, en 4 valores. Cada valor
corre 2 pasadas completas sobre el golden set (mismo criterio que compare_prompts.py:
una corrida sola no distingue "mejoro por la temperatura" de "salio mejor por azar").

Script manual (python -m evals.compare_temperature), no lo llama la app ni CI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from langsmith import Client

from evals.run_evals import build_eval_graph, get_case_limit, load_golden_set, run_eval_pass
from src.graph import MODEL_NAME, load_prompt

WINNING_PROMPT = load_prompt("system_prompt_direct_answer.txt")
WINNING_MODEL = MODEL_NAME  # gpt-4o-mini

TEMPERATURES = [0.0, 0.3, 0.6, 1.0]
RUNS_PER_TEMPERATURE = 2


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no configurada. Carga el .env antes de correr evals.")

    client = Client() if os.getenv("LANGCHAIN_API_KEY") else None
    cases = load_golden_set(limit=get_case_limit())

    print(
        f"Sweep de temperatura ({TEMPERATURES}) x {RUNS_PER_TEMPERATURE} corridas "
        f"sobre {len(cases)} casos -- prompt=direct_answer, modelo={WINNING_MODEL}\n"
    )

    for temperature in TEMPERATURES:
        for run_n in range(1, RUNS_PER_TEMPERATURE + 1):
            label = f"temp{temperature}_run{run_n}"
            graph = build_eval_graph(WINNING_PROMPT, WINNING_MODEL, temperature)
            summary, output_path = run_eval_pass(graph, cases, client, variant_label=label)
            accuracy_part = f"accuracy={summary['avg_accuracy']}/5  " if "avg_accuracy" in summary else ""
            tool_call_part = (
                f"tool_call_rate={summary['tool_call_rate'] * 100:.0f}%  " if "tool_call_rate" in summary else ""
            )
            print(
                f"{label:16s} relevancia={summary['avg_relevance']}/5  "
                f"{accuracy_part}{tool_call_part}"
                f"citas={summary['citation_rate'] * 100:.0f}%  "
                f"pasos={summary['avg_steps']}  -> {output_path.name}"
            )

    print("\nSweep completo. JSONs completos en evals/results/.")


if __name__ == "__main__":
    main()
