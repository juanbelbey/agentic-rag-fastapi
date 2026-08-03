"""Compara prompt x modelo contra el golden set (punto 4 del plan de entrega LLM Zoomcamp).

Corre 4 combinaciones aisladas -- un solo cambio de variable por corrida, nunca
prompt y modelo a la vez -- para poder atribuir cualquier diferencia de metricas
a una sola causa:
  baseline_mini       : prompt de produccion + gpt-4o-mini (referencia actual)
  baseline_nano       : prompt de produccion + gpt-4.1-nano (mismo prompt, modelo mas barato)
  direct_answer_mini  : prompt "direct answer" + gpt-4o-mini (mismo modelo, prompt nuevo)
  direct_answer_nano  : prompt "direct answer" + gpt-4.1-nano (los dos cambios, comparado
                        contra los tres anteriores para ver si se combinan sin sorpresas)

Script manual (python -m evals.compare_prompts), no lo llama la app ni CI -- mismo
patron que generate_golden_set.py / retrieval_metrics.py.
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
from src.graph import MODEL_NAME, SYSTEM_PROMPT, load_prompt

CHEAP_MODEL = "gpt-4.1-nano"
DIRECT_ANSWER_PROMPT = load_prompt("system_prompt_direct_answer.txt")

VARIANTS = [
    ("baseline_mini", SYSTEM_PROMPT, MODEL_NAME),
    ("baseline_nano", SYSTEM_PROMPT, CHEAP_MODEL),
    ("direct_answer_mini", DIRECT_ANSWER_PROMPT, MODEL_NAME),
    ("direct_answer_nano", DIRECT_ANSWER_PROMPT, CHEAP_MODEL),
]


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no configurada. Carga el .env antes de correr evals.")

    client = Client() if os.getenv("LANGCHAIN_API_KEY") else None
    cases = load_golden_set(limit=get_case_limit())

    print(f"Comparando {len(VARIANTS)} variantes sobre {len(cases)} casos del golden set\n")

    summaries: dict[str, dict[str, float]] = {}
    for label, prompt, model in VARIANTS:
        graph = build_eval_graph(prompt, model)
        summary, output_path = run_eval_pass(graph, cases, client, variant_label=label)
        summaries[label] = summary
        accuracy_part = f"accuracy={summary['avg_accuracy']}/5  " if "avg_accuracy" in summary else ""
        tool_call_part = (
            f"tool_call_rate={summary['tool_call_rate'] * 100:.0f}%  " if "tool_call_rate" in summary else ""
        )
        print(
            f"{label:20s} relevancia={summary['avg_relevance']}/5  "
            f"{accuracy_part}{tool_call_part}"
            f"citas={summary['citation_rate'] * 100:.0f}%  "
            f"pasos={summary['avg_steps']}  -> {output_path.name}"
        )

    print("\nComparacion completa. JSONs completos en evals/results/.")


if __name__ == "__main__":
    main()
