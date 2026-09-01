# evals/abstention_threshold.py
"""Barrido de umbral de confianza sobre distancia coseno cruda de _vector_search,
contra evals/critical_eval_set.json (Fase 4 del esquema de profesionalizacion
post-auditoria).

Se corre a mano (python -m evals.abstention_threshold) contra Supabase + OpenAI
reales -- mismo patron que retrieval_metrics.py/compare_prompts.py. No lo llama
la app ni CI.

Primer intento (2026-09-01, ver EXPERIMENTS.md "Umbral de abstencion sobre
score RRF: descartado"): se probo el score FUSIONADO de _hybrid_search() y no
sirvio -- 26/28 casos dieron el mismo score exacto (0.5), porque RRF mide
POSICION en el ranking, no similitud real, y _vector_search siempre devuelve
sus top_k vecinos mas cercanos aunque ninguno sea relevante.

Esta version usa en cambio la distancia coseno CRUDA de _vector_search (antes
de fusionar nada) -- señal continua real: 0 = identico, valores mas altos =
menos parecido. La hipotesis es que preguntas sin respuesta en el corpus
tengan una distancia consistentemente mas alta que las que si tienen chunks
relevantes. Se reporta lo que salga, no se elige el umbral que mejor quede.

Las categorias "ambigua" (la respuesta correcta es pedir aclaracion, no
abstenerse) y "mixta" (mezcla contenido real e inventado en la misma pregunta)
no entran en el calculo de falsos positivos/negativos -- no encajan en el
marco binario "hay chunk relevante / no hay". Se reportan aparte, a modo
diagnostico.
"""

import json
from datetime import datetime
from pathlib import Path

from src.ingestion import embed_texts
from src.tools import _get_connection, _vector_search

CRITICAL_SET_PATH = Path(__file__).parent / "critical_eval_set.json"
RESULTS_DIR = Path(__file__).parent / "results"
TOP_K = 5
SWEEP_STEPS = 20

# Categorias "limpias" para el calculo de FP/FN -- las que de verdad esperan
# "no hay informacion en el corpus", sin matices de tono.
CLEAN_UNANSWERABLE = {"relacionado_ausente", "producto_no_documentado", "fuera_de_dominio"}
DIAGNOSTIC_ONLY = {"ambigua", "mixta"}


def load_critical_set() -> list[dict]:
    return json.loads(CRITICAL_SET_PATH.read_text(encoding="utf-8"))


def top_distance(conn, query_embedding, top_k: int = TOP_K) -> float:
    """Distancia coseno del vecino MAS cercano que devuelve _vector_search (menor = mas parecido)."""
    results = _vector_search(conn, query_embedding, top_k)
    return results[0][1] if results else float("inf")


def score_cases(cases: list[dict]) -> list[dict]:
    """Corre embed_texts + _vector_search real y devuelve cada caso con su top_distance."""
    questions = [c["question"] for c in cases]
    embeddings = embed_texts(questions)

    conn = _get_connection()
    try:
        return [
            {**case, "top_distance": round(top_distance(conn, embedding), 4)}
            for case, embedding in zip(cases, embeddings)
        ]
    finally:
        conn.close()


def build_threshold_range(scored: list[dict], steps: int = SWEEP_STEPS) -> list[float]:
    """Barrido adaptado al rango real observado -- no un rango adivinado a ciegas."""
    distances = [c["top_distance"] for c in scored]
    low, high = min(distances), max(distances)
    if low == high:
        return [low]
    step = (high - low) / steps
    return [round(low + i * step, 4) for i in range(steps + 1)]


def sweep_thresholds(answerable: list[dict], clean_unanswerable: list[dict], thresholds: list[float]) -> list[dict]:
    """FN (answerable rechazadas) y FP (unanswerable aceptadas) para cada umbral candidato.

    Distancia: menor = mas parecido, al reves que el score RRF -- por eso aca se
    abstiene cuando top_distance > threshold, no cuando es menor.
    """
    rows = []
    for threshold in thresholds:
        false_negatives = sum(1 for c in answerable if c["top_distance"] > threshold)
        false_positives = sum(1 for c in clean_unanswerable if c["top_distance"] <= threshold)
        rows.append(
            {
                "threshold": threshold,
                "false_negatives": false_negatives,
                "false_negative_rate": round(false_negatives / len(answerable), 4),
                "false_positives": false_positives,
                "false_positive_rate": round(false_positives / len(clean_unanswerable), 4),
            }
        )
    return rows


def save_results(scored: list[dict], sweep: list[dict]) -> Path:
    timestamp = datetime.now()
    day_dir = RESULTS_DIR / timestamp.date().isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    output_path = day_dir / f"{timestamp.strftime('%H-%M-%S')}_abstention_threshold_distance.json"

    payload = {"generated_at": timestamp.isoformat(), "scored_cases": scored, "sweep": sweep}
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def main() -> None:
    cases = load_critical_set()
    print(f"Embebiendo y buscando {len(cases)} preguntas del critical set...")
    scored = score_cases(cases)

    print(f"\nDistancia coseno del vecino mas cercano por pregunta (top_k={TOP_K}):\n")
    for c in scored:
        flag = "answerable" if c["answerable"] else f"unanswerable ({c['category']})"
        print(f"  {c['id']:5s} distance={c['top_distance']:.4f}  {flag:32s} {c['question'][:60]}")

    answerable = [c for c in scored if c["answerable"]]
    clean_unanswerable = [c for c in scored if not c["answerable"] and c["category"] in CLEAN_UNANSWERABLE]
    diagnostic = [c for c in scored if not c["answerable"] and c["category"] in DIAGNOSTIC_ONLY]

    thresholds = build_threshold_range(answerable + clean_unanswerable)
    sweep = sweep_thresholds(answerable, clean_unanswerable, thresholds)
    print(
        f"\nBarrido de umbral (answerable={len(answerable)}, "
        f"unanswerable_limpio={len(clean_unanswerable)}):\n"
    )
    print(f"  {'umbral':>8s}  {'FN answerable':>18s}  {'FP unanswerable':>18s}")
    for row in sweep:
        fn_pct = row["false_negative_rate"] * 100
        fp_pct = row["false_positive_rate"] * 100
        print(
            f"  {row['threshold']:>8.4f}  "
            f"{row['false_negatives']:>2d}/{len(answerable)} ({fn_pct:>5.1f}%)      "
            f"{row['false_positives']:>2d}/{len(clean_unanswerable)} ({fp_pct:>5.1f}%)"
        )

    print("\nDiagnostico -- 'ambigua'/'mixta', no entran en FP/FN (ver docstring):\n")
    for c in diagnostic:
        print(f"  {c['id']:5s} distance={c['top_distance']:.4f}  {c['category']:10s} {c['question'][:60]}")

    output_path = save_results(scored, sweep)
    print(f"\nResultados completos guardados en: {output_path}")


if __name__ == "__main__":
    main()
