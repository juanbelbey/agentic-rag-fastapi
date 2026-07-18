# evals/retrieval_metrics.py
"""Hit Rate y MRR de retrieval sobre evals/ground_truth_retrieval.json (patron HW4, Modulo 4).

Se corre a mano (python -m evals.retrieval_metrics) contra Supabase + OpenAI
reales -- mismo patron que generate_ground_truth.py. No lo llama la app ni CI.

Adaptado del framework de M4 (compute_relevance/hit_rate/mrr/evaluate,
parametrizado por funcion de busqueda) a la ground truth propia: el acierto
no es "el documento correcto" (filename) sino "alguno de los chunk_ids de la
ventana que genero la pregunta" -- ver evals/generate_ground_truth.py.
"""

import json
from pathlib import Path

from src.ingestion import embed_texts
from src.tools import _get_connection, _hybrid_search, _keyword_search, _vector_search

GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth_retrieval.json"
TOP_K = 5


def load_ground_truth() -> list[dict]:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def compute_relevance(result_ids: list[int], expected_ids: list[int]) -> list[bool]:
    """Por resultado devuelto, si esta entre los chunk_ids esperados de la pregunta."""
    return [chunk_id in expected_ids for chunk_id in result_ids]


def hit_rate(relevance_total: list[list[bool]]) -> float:
    """Fraccion de preguntas donde algun resultado fue relevante, sin importar la posicion."""
    return sum(any(rel) for rel in relevance_total) / len(relevance_total)


def mrr(relevance_total: list[list[bool]]) -> float:
    """Promedio de 1/posicion del primer acierto (0 si no hubo ninguno)."""
    total = 0.0
    for rel in relevance_total:
        for rank, is_relevant in enumerate(rel, start=1):
            if is_relevant:
                total += 1 / rank
                break
    return total / len(relevance_total)


def _vector_search_ids(conn, query: str, query_embedding, top_k: int) -> list[int]:
    return [chunk_id for chunk_id, _ in _vector_search(conn, query_embedding, top_k)]


def _keyword_search_ids(conn, query: str, query_embedding, top_k: int) -> list[int]:
    return [chunk_id for chunk_id, _ in _keyword_search(conn, query, top_k)]


def _hybrid_search_ids(conn, query: str, query_embedding, top_k: int) -> list[int]:
    return [chunk_id for chunk_id, _ in _hybrid_search(conn, query, query_embedding, top_k)]


SEARCH_FUNCTIONS = {
    "vector": _vector_search_ids,
    "keyword": _keyword_search_ids,
    "hybrid": _hybrid_search_ids,
}


def evaluate(search_fn, ground_truth: list[dict], embeddings, conn, top_k: int = TOP_K) -> dict[str, float]:
    """Corre search_fn sobre cada pregunta de ground_truth y agrega hit_rate/mrr."""
    relevance_total = [
        compute_relevance(search_fn(conn, case["question"], embedding, top_k), case["chunk_ids"])
        for case, embedding in zip(ground_truth, embeddings)
    ]
    return {
        "hit_rate": round(hit_rate(relevance_total), 4),
        "mrr": round(mrr(relevance_total), 4),
    }


def main() -> None:
    ground_truth = load_ground_truth()
    questions = [case["question"] for case in ground_truth]
    print(f"Embebiendo {len(questions)} preguntas del ground truth...")
    embeddings = embed_texts(questions)

    conn = _get_connection()
    try:
        print(f"\nMetricas @top_k={TOP_K} sobre {len(ground_truth)} preguntas:\n")
        for name, search_fn in SEARCH_FUNCTIONS.items():
            metrics = evaluate(search_fn, ground_truth, embeddings, conn)
            print(f"  {name:8s} hit_rate={metrics['hit_rate']}  mrr={metrics['mrr']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
