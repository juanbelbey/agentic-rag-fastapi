"""Evals de generacion con RAGAS (stretch, ver ROADMAP/CHANGELOG 2026-08-04/05).

4 metricas que complementan evals/evaluators.py (relevance_evaluator/accuracy_evaluator):
- faithfulness: la respuesta no inventa/contradice mas alla de los contexts recuperados
- answer_relevancy: la respuesta responde lo que se pregunto (reference-free, como relevance_evaluator)
- context_precision: los contexts relevantes quedan arriba en el ranking (variante con reference)
- context_recall: los contexts recuperados alcanzan para cubrir la reference (equivalente a
  accuracy_evaluator, pero mide el retrieval en vez de la respuesta final)

Los contexts se toman de lo que el agente realmente vio -- el content de cada chunk
devuelto por la tool call real a rag_search en la traza (extract_contexts), no de
_hybrid_search() llamado aparte. Asi faithfulness/context_recall juzgan contra lo que
tuvo el LLM al generar esa respuesta puntual, no contra un retrieval hipotetico.

Corre solo sobre los casos de golden_set.json con expected_answer (quedan afuera los 8
de escalamiento -- usan expected_tool, no hay contexts que juzgar con estas 4 metricas).

Script manual (python -m evals.ragas_eval), no lo llama CI -- mismo patron que
compare_prompts.py/compare_temperature.py.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
from openai import AsyncOpenAI
from ragas.embeddings import OpenAIEmbeddings
from ragas.llms import llm_factory
from ragas.metrics.collections import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

from evals.run_evals import build_eval_graph, invoke_agent, load_golden_set, save_results

# Mismo juez que evaluators.py (JUDGE_MODEL) -- consistente con el resto de los evals.
RAGAS_JUDGE_MODEL = "gpt-4o-mini"


def extract_contexts(trace: dict) -> list[str]:
    """Contenido de los chunks que el agente recibio de rag_search en esta corrida.

    rag_search() (src/tools.py) devuelve un JSON de una lista de RAGResult
    (content/source/score) como ToolMessage.content. Si hubo mas de una llamada a
    rag_search en la misma traza, se acumulan los contexts de todas.
    """
    contexts: list[str] = []
    for message in trace["messages"]:
        if isinstance(message, ToolMessage) and message.name == "rag_search":
            try:
                payload = json.loads(message.content)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(payload, list):
                contexts.extend(item["content"] for item in payload if "content" in item)
    return contexts


def build_metrics() -> dict[str, object]:
    # AsyncOpenAI, no OpenAI: el .score() sync de cada metrica llama internamente
    # a asyncio.run(self.ascore(...)) -> llm.agenerate(), que exige un cliente
    # async (con un cliente sync tira "Cannot use agenerate() with a synchronous
    # client"). OpenAIEmbeddings detecta el tipo de cliente solo y expone
    # embed_text/aembed_text segun corresponda, asi que el mismo client sirve ahi.
    client = AsyncOpenAI()
    # max_tokens explicito: el default (sin fijar) trunco la respuesta estructurada
    # de faithfulness a mitad de camino en la primera corrida completa (2026-08-05)
    # -- instructor.v2.core.errors.IncompleteOutputException por limite de tokens.
    # 2048 cubre de sobra el JSON de statements/verdicts de un caso con varios chunks.
    llm = llm_factory(RAGAS_JUDGE_MODEL, client=client, max_tokens=2048)
    # Default model de OpenAIEmbeddings es text-embedding-3-small -- mismo modelo
    # que embed_texts() en src/ingestion.py, sin pasarlo explicito.
    embeddings = OpenAIEmbeddings(client=client)
    return {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
    }


def evaluate_case(graph, metrics: dict[str, object], case: dict[str, str]) -> dict[str, object]:
    """Un caso no debe tirar abajo toda la corrida -- todo el cuerpo (invoke del
    agente, no solo el scoring de RAGAS) va adentro del try. Primera version solo
    envolvia las 4 metricas y se perdio una corrida completa por un
    "server closed the connection unexpectedly" de Postgres a mitad de una tool
    call, dentro de invoke_agent (2026-08-05). Mismo motivo de fondo que dejo
    compare_temperature.py a medio terminar el 2026-08-01: una corrida larga sin
    aislar el punto de falla pierde todo el trabajo previo, no solo el caso que fallo.
    """
    result: dict[str, object] = {"id": case["id"], "question": case["question"]}
    try:
        trace, run_id = invoke_agent(graph, case["question"])
        answer = trace["messages"][-1].content
        contexts = extract_contexts(trace)
        result["answer"] = answer
        result["contexts_count"] = len(contexts)
        result["run_id"] = str(run_id)

        if not contexts:
            # Sin contexts no hay nada que las 4 metricas puedan juzgar -- se deja
            # constancia del caso en vez de forzar un score sobre una lista vacia.
            result["error"] = "sin contexts recuperados (rag_search no devolvio resultados o no se llamo)"
            return result

        result["faithfulness"] = metrics["faithfulness"].score(
            user_input=case["question"], response=answer, retrieved_contexts=contexts
        ).value
        result["answer_relevancy"] = metrics["answer_relevancy"].score(
            user_input=case["question"], response=answer
        ).value
        result["context_precision"] = metrics["context_precision"].score(
            user_input=case["question"], reference=case["expected_answer"], retrieved_contexts=contexts
        ).value
        result["context_recall"] = metrics["context_recall"].score(
            user_input=case["question"], retrieved_contexts=contexts, reference=case["expected_answer"]
        ).value
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def build_summary(results: list[dict[str, object]]) -> dict[str, float]:
    scored = [r for r in results if "error" not in r]
    summary: dict[str, float] = {"total_cases": len(results), "scored_cases": len(scored)}
    for key in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
        values = [r[key] for r in scored if key in r]
        if values:
            summary[f"avg_{key}"] = round(sum(values) / len(values), 3)
    return summary


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no configurada. Carga el .env antes de correr evals.")

    cases = [case for case in load_golden_set() if "expected_answer" in case]
    graph = build_eval_graph()
    metrics = build_metrics()

    results = [evaluate_case(graph, metrics, case) for case in cases]
    summary = build_summary(results)
    output_path = save_results(summary, results, variant_label="ragas")

    print("Evaluacion RAGAS completada")
    print(f"Casos evaluados: {summary['scored_cases']}/{summary['total_cases']}")
    for key in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
        avg_key = f"avg_{key}"
        if avg_key in summary:
            print(f"{key}: {summary[avg_key]}")
    print(f"Resultados guardados en: {output_path}")


if __name__ == "__main__":
    main()
