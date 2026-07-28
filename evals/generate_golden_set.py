# evals/generate_golden_set.py
"""Genera el golden set de evaluacion de GENERACION (no retrieval) para el corpus real.

Distinto de generate_ground_truth.py (que mide si el sistema RECUPERA el chunk
correcto via hit_rate/mrr): este script mide si la RESPUESTA final del agente es
correcta. Para eso hace falta una expected_answer de referencia, que hoy no existe
para el corpus de instrumentacion.

No genera preguntas nuevas ni cambia el mapeo pregunta->chunk: samplea preguntas ya
generadas y verificadas en evals/ground_truth_retrieval.json (5B.4 paso 4), balanceado
por categoria, trae el contenido real de sus chunk_ids desde Supabase, y le pide al
LLM que escriba la expected_answer grounded en ese texto (no puede inventar datos que
el fragmento no tiene).

Se corre a mano (python -m evals.generate_golden_set) contra Supabase + OpenAI reales.
Reemplaza evals/golden_set.json (que hoy tiene 20 preguntas del corpus viejo de
LangGraph docs, ya no existe en Supabase).
"""

import json
import random
from collections import defaultdict
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from evals.generate_ground_truth import _get_connection

MODEL_NAME = "gpt-4o-mini"
GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth_retrieval.json"
OUTPUT_PATH = Path(__file__).parent / "golden_set.json"

SAMPLES_PER_CATEGORY = 12
RANDOM_SEED = 42

PROMPT = (
    "Sos un tecnico de instrumentacion de campo (agua potable y saneamiento) "
    "escribiendo la respuesta de referencia (gold answer) para evaluar un agente "
    "de soporte tecnico.\n\n"
    "Te doy una pregunta y el fragmento real de manual que la responde. Escribi la "
    "respuesta correcta usando SOLO informacion del fragmento -- no agregues datos "
    "de calibracion, rangos o procedimientos que el texto no menciona. Respondé "
    "directo y tecnico, como si fueras el manual mismo.\n\n"
    "Pregunta: {question}\n\n"
    "Fragmento:\n{text}"
)


class GeneratedAnswer(BaseModel):
    answer: str


def load_ground_truth() -> list[dict]:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def sample_by_category(ground_truth: list[dict]) -> list[dict]:
    """Samplea SAMPLES_PER_CATEGORY preguntas por categoria, con seed fijo."""
    by_category: dict[str, list[dict]] = defaultdict(list)
    for item in ground_truth:
        by_category[item["category"]].append(item)

    rng = random.Random(RANDOM_SEED)
    sampled = []
    for category, items in sorted(by_category.items()):
        chosen = rng.sample(items, min(SAMPLES_PER_CATEGORY, len(items)))
        sampled.extend(chosen)
    return sampled


def fetch_chunk_contents(conn, chunk_ids: list[int]) -> dict[int, str]:
    with conn.cursor() as cur:
        cur.execute("SELECT id, content FROM chunks WHERE id = ANY(%s);", (chunk_ids,))
        return dict(cur.fetchall())


def generate_answer(client: OpenAI, question: str, window_text: str) -> str:
    completion = client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": PROMPT.format(question=question, text=window_text)}],
        response_format=GeneratedAnswer,
    )
    return completion.choices[0].message.parsed.answer


def main() -> None:
    load_dotenv()
    ground_truth = load_ground_truth()
    sampled = sample_by_category(ground_truth)
    print(f"{len(sampled)} preguntas sampleadas de {len(ground_truth)} (seed={RANDOM_SEED}).")

    conn = _get_connection()
    client = OpenAI()
    golden_set = []
    try:
        for n, item in enumerate(sampled, start=1):
            contents_by_id = fetch_chunk_contents(conn, item["chunk_ids"])
            window_text = "\n\n".join(
                contents_by_id[chunk_id] for chunk_id in item["chunk_ids"] if chunk_id in contents_by_id
            )
            answer = generate_answer(client, item["question"], window_text)

            golden_set.append(
                {
                    "id": f"g{n:03d}",
                    "question": item["question"],
                    "expected_answer": answer,
                    "source": item["source"],
                    "category": item["category"],
                }
            )
            print(f"[{n}/{len(sampled)}] {item['category']} · {item['source']}")
    finally:
        conn.close()

    OUTPUT_PATH.write_text(json.dumps(golden_set, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(golden_set)} preguntas -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
