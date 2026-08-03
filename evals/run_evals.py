"""Runner local para evaluaciones sistematicas del agente."""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langsmith import Client  # Cliente para enviar feedback a LangSmith

from evals.evaluators import (
    accuracy_evaluator,
    citation_evaluator,
    convergence_evaluator,
    relevance_evaluator,
    tool_call_evaluator,
)
from src.graph import MODEL_NAME, SYSTEM_PROMPT, build_graph

GOLDEN_SET_PATH = ROOT_DIR / "evals" / "golden_set.json"
RESULTS_DIR = ROOT_DIR / "evals" / "results"


def build_eval_graph(system_prompt: str = SYSTEM_PROMPT, model_name: str = MODEL_NAME, temperature: float = 1.0):
    """Compila un grafo para evals con MemorySaver -- no depende de Postgres,
    a diferencia del graph de main.py (no necesita sobrevivir un reinicio)."""
    return build_graph(system_prompt, model_name, temperature).compile(checkpointer=MemorySaver())


# Grafo default usado por main()/CI: prompt y modelo de produccion, sin cambios
# de comportamiento respecto a antes de parametrizar build_graph() en src/graph.py.
graph = build_eval_graph()


def load_golden_set(limit: int | None = None) -> list[dict[str, str]]:
    """Carga los casos base de evaluacion."""
    cases = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    if limit is None:
        return cases
    return cases[:limit]


def invoke_agent(graph, question: str) -> tuple[dict, uuid.UUID]:
    """Invoca el grafo dado con un thread_id y run_id aislados para cada pregunta.

    El run_id se genera ANTES del invoke y se pasa por config["run_id"] -- mismo
    patron que /chat en main.py -- para poder asociarle feedback despues. AgentState
    no trae "run_id" de vuelta en el resultado, por eso no se puede leer del trace.
    """
    run_id = uuid.uuid4()
    config = {"configurable": {"thread_id": f"eval-{run_id}"}, "run_id": run_id}
    trace = graph.invoke({"messages": [HumanMessage(content=question)]}, config=config)
    return trace, run_id


def evaluate_case(graph, case: dict[str, str]) -> dict[str, object]:
    """Ejecuta el agente para un caso y devuelve las metricas calculadas, junto
    con el run_id generado para poder enviarle feedback despues a LangSmith.

    Dos tipos de caso conviven en el golden set:
    - Q&A con expected_answer (el flujo original): se juzga con accuracy_evaluator
      contra la referencia.
    - Escalamiento con expected_tool (ej. create_ticket): no hay respuesta de
      referencia con la que comparar texto -- lo que importa es si el agente
      decidio llamar la tool correcta, asi que se verifica con tool_call_evaluator
      (code-based, sobre la traza) en vez de un LLM-judge.
    """
    trace, run_id = invoke_agent(graph, case["question"])
    # obtenemos la respuesta final asumiendo que el ultimo mensaje es la respuesta del agente
    answer = trace["messages"][-1].content

    # calcular métricas usando los evaluadores reutilizables
    relevance_score = relevance_evaluator(case["question"], answer)
    has_citation = citation_evaluator(answer)
    steps = convergence_evaluator(trace)

    result: dict[str, object] = {
        "id": case["id"],
        "question": case["question"],
        "source": case.get("source"),
        "category": case["category"],
        "answer": answer,
        "relevance_score": relevance_score,
        "has_citation": has_citation,
        "convergence_steps": steps,
        "run_id": str(run_id),
    }

    if "expected_tool" in case:
        result["expected_tool"] = case["expected_tool"]
        result["tool_call_correct"] = tool_call_evaluator(trace, case["expected_tool"])
    else:
        result["expected_answer"] = case["expected_answer"]
        result["accuracy_score"] = accuracy_evaluator(case["question"], case["expected_answer"], answer)

    return result


def build_summary(results: list[dict[str, object]]) -> dict[str, float]:
    """Calcula metricas agregadas de la corrida.

    avg_accuracy y tool_call_rate se calculan solo sobre el subconjunto de
    resultados que trae esa metrica (Q&A vs. escalamiento, ver evaluate_case) --
    quedan ausentes del summary si ningun caso de ese tipo entro en la corrida
    (ej. un MAX_EVAL_CASES chico que solo tomo casos de un tipo).
    """
    total = len(results)
    avg_relevance = sum(item["relevance_score"] for item in results) / total
    citation_rate = sum(1 for item in results if item["has_citation"]) / total
    avg_steps = sum(item["convergence_steps"] for item in results) / total

    summary = {
        "total_cases": total,
        "avg_relevance": round(avg_relevance, 2),
        "citation_rate": round(citation_rate, 2),
        "avg_steps": round(avg_steps, 2),
    }

    accuracy_results = [item for item in results if "accuracy_score" in item]
    if accuracy_results:
        summary["avg_accuracy"] = round(
            sum(item["accuracy_score"] for item in accuracy_results) / len(accuracy_results), 2
        )
        summary["accuracy_cases"] = len(accuracy_results)

    tool_results = [item for item in results if "tool_call_correct" in item]
    if tool_results:
        summary["tool_call_rate"] = round(
            sum(1 for item in tool_results if item["tool_call_correct"]) / len(tool_results), 2
        )
        summary["tool_call_cases"] = len(tool_results)

    return summary


def save_results(
    summary: dict[str, float], results: list[dict[str, object]], variant_label: str | None = None
) -> Path:
    """Guarda la corrida en evals/results/YYYY-MM-DD/HH-MM-SS[_variante].json."""
    timestamp = datetime.now()
    day_dir = RESULTS_DIR / timestamp.date().isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{variant_label}" if variant_label else ""
    output_path = day_dir / f"{timestamp.strftime('%H-%M-%S')}{suffix}.json"

    payload = {
        "generated_at": timestamp.isoformat(),
        "summary": summary,
        "results": results,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def get_case_limit() -> int | None:
    """Lee un limite opcional de casos desde MAX_EVAL_CASES."""
    raw_value = os.getenv("MAX_EVAL_CASES")
    if not raw_value:
        return None
    return int(raw_value)


def send_feedback(client: Client | None, result: dict[str, object]) -> None:
    """Manda relevance/accuracy/tool_call a LangSmith para un caso ya evaluado.
    Best-effort: si no hay cliente, no hay run_id, o falla la llamada, no rompe
    la ejecucion. tool_call_correct es bool -- se manda como score 0.0/1.0, mismo
    rango que relevance/accuracy normalizados que ya recibe LangSmith."""
    run_id = result.get("run_id")
    if not client or run_id is None:
        return
    for key, feedback_key in (
        ("relevance_score", "relevance"),
        ("accuracy_score", "accuracy"),
        ("tool_call_correct", "tool_call"),
    ):
        if key not in result:
            continue
        value = result[key]
        score = float(value) if isinstance(value, bool) else value
        try:
            client.create_feedback(run_id, key=feedback_key, score=score)
        except Exception:
            pass


def run_eval_pass(
    graph, cases: list[dict[str, str]], client: Client | None, variant_label: str | None = None
) -> tuple[dict[str, float], Path]:
    """Corre el golden set completo contra un grafo dado, envia feedback caso a
    caso (no al final -- si el script se corta a mitad de camino, no se pierde
    el feedback ya mandado) y guarda los resultados."""
    results: list[dict[str, object]] = []
    for case in cases:
        result = evaluate_case(graph, case)
        results.append(result)
        send_feedback(client, result)

    summary = build_summary(results)
    output_path = save_results(summary, results, variant_label=variant_label)
    return summary, output_path


def main() -> None:
    """Corre una ronda completa de evaluacion (prompt/modelo de produccion) y
    muestra un resumen.

    Si `LANGCHAIN_API_KEY` está presente en el entorno, crea un cliente de
    LangSmith y envía feedback por cada caso evaluado. Si no está, la parte
    de LangSmith se saltea silenciosamente.
    """
    load_dotenv(ROOT_DIR / ".env")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no configurada. Carga el .env antes de correr evals.")

    # Crear cliente de LangSmith solo si hay clave de LangChain (opcional)
    client = Client() if os.getenv("LANGCHAIN_API_KEY") else None

    cases = load_golden_set(limit=get_case_limit())
    summary, output_path = run_eval_pass(graph, cases, client)

    print("Evaluacion completada")
    print(f"Casos evaluados: {summary['total_cases']}")
    print(f"Relevancia promedio: {summary['avg_relevance']}/5")
    if "avg_accuracy" in summary:
        print(f"Precision promedio: {summary['avg_accuracy']}/5 ({summary['accuracy_cases']} casos Q&A)")
    if "tool_call_rate" in summary:
        print(
            f"Tool-call rate (escalamiento): {summary['tool_call_rate'] * 100:.0f}% "
            f"({summary['tool_call_cases']} casos)"
        )
    print(f"Porcentaje con cita: {summary['citation_rate'] * 100:.0f}%")
    print(f"Pasos promedio: {summary['avg_steps']}")
    print(f"Resultados guardados en: {output_path}")


if __name__ == "__main__":
    main()