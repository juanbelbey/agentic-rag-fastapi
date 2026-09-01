# evals/critical_set_agent_check.py
"""Corre el agente COMPLETO (LLM + rag_search real, no solo retrieval aislado)
contra evals/critical_eval_set.json -- para ver como se comporta HOY frente a
las 13 preguntas unanswerable, antes de decidir si hace falta un chequeo de
confianza en el codigo o alcanza con reforzar el prompt (ver EXPERIMENTS.md,
entrada "Umbral de abstencion sobre score RRF/distancia").

Se corre a mano (python -m evals.critical_set_agent_check) contra OpenAI +
Postgres reales -- mismo patron que compare_prompts.py/run_evals.py. No lo
llama la app ni CI. No hay auto-scoring: se imprime pregunta + respuesta para
revision manual, la clasificacion "alucina / se abstiene / pide aclaracion"
la hace una persona leyendo, no un juez LLM (evita gastar el doble en costo
para responder una pregunta que un humano puede leer en un vistazo).
"""

import json
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from src.graph import graph_builder

CRITICAL_SET_PATH = Path(__file__).parent / "critical_eval_set.json"
RESULTS_DIR = Path(__file__).parent / "results"


def load_critical_set() -> list[dict]:
    return json.loads(CRITICAL_SET_PATH.read_text(encoding="utf-8"))


def run_case(graph, case: dict) -> dict:
    result = graph.invoke(
        {"messages": [{"role": "user", "content": case["question"]}]},
        config={"configurable": {"thread_id": f"critical-{case['id']}"}},
    )
    answer = getattr(result["messages"][-1], "content", "")

    tools_used: list[str] = []
    for message in result["messages"]:
        for tool_call in getattr(message, "tool_calls", None) or []:
            if tool_call["name"] not in tools_used:
                tools_used.append(tool_call["name"])

    return {**case, "agent_answer": answer, "tools_used": tools_used}


def main() -> None:
    cases = load_critical_set()
    graph = graph_builder.compile(checkpointer=MemorySaver())

    print(f"Corriendo el agente completo sobre {len(cases)} preguntas del critical set...\n")
    results = []
    for i, case in enumerate(cases, start=1):
        result = run_case(graph, case)
        results.append(result)

        flag = "answerable" if case["answerable"] else f"unanswerable ({case['category']})"
        print(f"[{i}/{len(cases)}] {case['id']} ({flag}) -- tools: {result['tools_used']}")
        print(f"  Q: {case['question']}")
        print(f"  A: {result['agent_answer'][:250]}")
        print()

    timestamp = datetime.now()
    day_dir = RESULTS_DIR / timestamp.date().isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    output_path = day_dir / f"{timestamp.strftime('%H-%M-%S')}_critical_set_agent_check.json"
    output_path.write_text(
        json.dumps({"generated_at": timestamp.isoformat(), "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Resultados completos guardados en: {output_path}")


if __name__ == "__main__":
    main()
