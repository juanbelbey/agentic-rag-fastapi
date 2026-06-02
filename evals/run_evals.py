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
from langsmith import Client  # Cliente para enviar feedback a LangSmith

from evals.evaluators import (
    citation_evaluator,
    convergence_evaluator,
    relevance_evaluator,
)
from src.graph import graph


GOLDEN_SET_PATH = ROOT_DIR / "evals" / "golden_set.json"
RESULTS_DIR = ROOT_DIR / "evals" / "results"


def load_golden_set(limit: int | None = None) -> list[dict[str, str]]:
    """Carga los casos base de evaluacion."""
    cases = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    if limit is None:
        return cases
    return cases[:limit]


def invoke_agent(question: str) -> dict:
    """Invoca el grafo con un thread_id aislado para cada pregunta."""
    config = {"configurable": {"thread_id": f"eval-{uuid.uuid4()}"}}
    return graph.invoke({"messages": [HumanMessage(content=question)]}, config=config)


def evaluate_case(case: dict[str, str]) -> dict[str, object]:
    """Ejecuta el agente para un caso y devuelve las metricas calculadas.

    Además, devuelve `run_id` si el resultado del agente lo incluye, para
    poder enviar feedback externo (LangSmith) más tarde.
    """
    trace = invoke_agent(case["question"])
    # obtenemos la respuesta final asumiendo que el ultimo mensaje es la respuesta del agente
    answer = trace["messages"][-1].content

    # calcular métricas usando los evaluadores reutilizables
    relevance_score = relevance_evaluator(case["question"], answer)
    has_citation = citation_evaluator(answer)
    steps = convergence_evaluator(trace)

    # extraer run_id si el grafo lo devolvió (puede variar según implementation)
    run_id = None
    if isinstance(trace, dict):
        # intento seguro de obtener run_id sin fallar si no está presente
        run_id = trace.get("run_id")

    return {
        "id": case["id"],
        "question": case["question"],
        "expected_answer": case["expected_answer"],
        "source": case["source"],
        "category": case["category"],
        "answer": answer,
        "relevance_score": relevance_score,
        "has_citation": has_citation,
        "convergence_steps": steps,
        "run_id": run_id,
    }


def build_summary(results: list[dict[str, object]]) -> dict[str, float]:
    """Calcula metricas agregadas de la corrida."""
    total = len(results)
    avg_relevance = sum(item["relevance_score"] for item in results) / total
    citation_rate = sum(1 for item in results if item["has_citation"]) / total
    avg_steps = sum(item["convergence_steps"] for item in results) / total

    return {
        "total_cases": total,
        "avg_relevance": round(avg_relevance, 2),
        "citation_rate": round(citation_rate, 2),
        "avg_steps": round(avg_steps, 2),
    }


def save_results(summary: dict[str, float], results: list[dict[str, object]]) -> Path:
    """Guarda la corrida en evals/results/YYYY-MM-DD/HH-MM-SS.json."""
    timestamp = datetime.now()
    day_dir = RESULTS_DIR / timestamp.date().isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    output_path = day_dir / f"{timestamp.strftime('%H-%M-%S')}.json"

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


def main() -> None:
    """Corre una ronda completa de evaluacion y muestra un resumen.

    Si `LANGCHAIN_API_KEY` está presente en el entorno, crea un cliente de
    LangSmith y envía feedback por cada caso evaluado. Si no está, la parte
    de LangSmith se saltea silenciosamente.
    """
    load_dotenv(ROOT_DIR / ".env")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no configurada. Carga el .env antes de correr evals.")

    # Crear cliente de LangSmith solo si hay clave de LangChain (opcional)
    client = None
    if os.getenv("LANGCHAIN_API_KEY"):
        # el constructor usa la variable de entorno para autenticarse
        client = Client()

    case_limit = get_case_limit()
    cases = load_golden_set(limit=case_limit)

    results: list[dict[str, object]] = []
    # iteramos caso por caso para poder enviar feedback inmediatamente
    for case in cases:
        result = evaluate_case(case)
        results.append(result)

        # enviar feedback a LangSmith si tenemos cliente y run_id disponible
        run_id = result.get("run_id")
        score = result.get("relevance_score")
        if client and run_id is not None and score is not None:
            try:
                # crear feedback simple con la clave "relevance"
                client.create_feedback(run_id, key="relevance", score=score)
            except Exception:
                # No queremos que LangSmith rompa la ejecucion; falla silenciosamente
                pass

    summary = build_summary(results)
    output_path = save_results(summary, results)

    print("Evaluacion completada")
    print(f"Casos evaluados: {summary['total_cases']}")
    print(f"Relevancia promedio: {summary['avg_relevance']}/5")
    print(f"Porcentaje con cita: {summary['citation_rate'] * 100:.0f}%")
    print(f"Pasos promedio: {summary['avg_steps']}")
    print(f"Resultados guardados en: {output_path}")


if __name__ == "__main__":
    main()