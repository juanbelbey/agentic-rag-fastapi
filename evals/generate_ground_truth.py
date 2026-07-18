# evals/generate_ground_truth.py
"""Genera ground truth de retrieval con LLM + structured output (patron HW4, Modulo 4).

Se corre a mano (python -m evals.generate_ground_truth) contra Supabase + OpenAI
reales. No lo llama la app ni CI -- es preparacion de datos offline, mismo patron
que scripts/ingest.py. Alimenta el hit_rate/mrr del paso 5 (evals/retrieval_metrics.py,
todavia no existe).
"""

import json
import os
from collections import Counter
from pathlib import Path
from typing import Literal

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

MODEL_NAME = "gpt-4o-mini"
OUTPUT_PATH = Path(__file__).parent / "ground_truth_retrieval.json"

# Un anclaje cada STRIDE chunks, equiespaciados dentro de cada documento -- con
# los 2451 chunks reales del corpus esto da ~123 anclajes, no 2451 llamadas al LLM.
STRIDE = 20
# Ventana de contexto por anclaje: el chunk anclado + el siguiente (mismo source,
# chunk_index consecutivo). Cubre procedimientos cortos sin generar preguntas
# sobre texto que el LLM nunca vio. chunk_index empieza en 0 por documento
# (ver scripts/ingest.py), asi que "el siguiente" es siempre el chunk contiguo.
WINDOW_SIZE = 2

PROMPT = (
    "Sos un tecnico de instrumentacion de campo (agua potable y saneamiento) "
    "escribiendo preguntas para evaluar un sistema de busqueda documental.\n\n"
    "Te doy un fragmento real de un manual tecnico. Genera entre 1 y 4 preguntas "
    "que ese fragmento responde, usando SOLO las categorias que el fragmento "
    "realmente sostiene -- no inventes una pregunta de una categoria si el texto "
    "no da para eso:\n"
    "- factual: un dato puntual (rango, valor, especificacion).\n"
    "- procedimental: una secuencia de pasos (instalacion, calibracion, ajuste).\n"
    "- inferencial: requiere razonar sobre el texto, no copiar una frase "
    "(ej. que implica que una lectura este fuera de rango).\n"
    "- borde: un caso puntual o una excepcion mencionada en el texto.\n\n"
    "No copies frases textuales del fragmento en la pregunta -- usa tus propias "
    "palabras, como preguntaria un operador en el campo.\n\n"
    "Fragmento:\n{text}"
)


class GeneratedQuestion(BaseModel):
    question: str
    category: Literal["factual", "procedimental", "inferencial", "borde"]


class GeneratedQuestions(BaseModel):
    questions: list[GeneratedQuestion]


def _get_connection():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Falta DATABASE_URL en el entorno.")
    return psycopg2.connect(database_url)


def load_chunks_by_source() -> dict[str, list[tuple[int, int, str]]]:
    """Devuelve {source: [(id, chunk_index, content), ...]} ordenado por chunk_index."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, source, chunk_index, content FROM chunks "
                "ORDER BY source, chunk_index;"
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    by_source: dict[str, list[tuple[int, int, str]]] = {}
    for chunk_id, source, chunk_index, content in rows:
        by_source.setdefault(source, []).append((chunk_id, chunk_index, content))
    return by_source


def build_windows(
    by_source: dict[str, list[tuple[int, int, str]]],
) -> list[tuple[str, list[tuple[int, int, str]]]]:
    """Elige anclajes cada STRIDE chunks por documento y arma la ventana de contexto.

    Devuelve [(source, [(id, chunk_index, content), ...ventana de hasta WINDOW_SIZE...]), ...]
    """
    windows = []
    for source, chunks in by_source.items():
        for i in range(0, len(chunks), STRIDE):
            windows.append((source, chunks[i : i + WINDOW_SIZE]))
    return windows


def generate_questions(client: OpenAI, window_text: str) -> list[GeneratedQuestion]:
    completion = client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": PROMPT.format(text=window_text)}],
        response_format=GeneratedQuestions,
    )
    return completion.choices[0].message.parsed.questions


def main() -> None:
    load_dotenv()
    by_source = load_chunks_by_source()
    windows = build_windows(by_source)
    total_chunks = sum(len(chunks) for chunks in by_source.values())
    print(
        f"{len(windows)} ventanas de anclaje sobre {total_chunks} chunks "
        f"/ {len(by_source)} documentos."
    )

    client = OpenAI()
    ground_truth = []
    for n, (source, window) in enumerate(windows, start=1):
        window_text = "\n\n".join(content for _, _, content in window)
        questions = generate_questions(client, window_text)
        chunk_ids = [chunk_id for chunk_id, _, _ in window]

        for q in questions:
            ground_truth.append(
                {
                    "question": q.question,
                    "category": q.category,
                    "chunk_ids": chunk_ids,
                    "source": source,
                }
            )
        print(f"[{n}/{len(windows)}] {source} chunk {window[0][1]} -> {len(questions)} preguntas")

    OUTPUT_PATH.write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    by_category = Counter(item["category"] for item in ground_truth)
    print(f"\n{len(ground_truth)} preguntas generadas -> {OUTPUT_PATH}")
    for category, count in sorted(by_category.items()):
        print(f"  {category}: {count}")


if __name__ == "__main__":
    main()
