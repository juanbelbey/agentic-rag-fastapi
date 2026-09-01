# src/ingestion.py
"""Pipeline de ingesta: texto → chunks → embeddings."""

import numpy as np
from openai import OpenAI


def chunk_text(text: str, source: str, size: int = 500, step: int = 250) -> list[tuple[str, str]]:
    """Divide un texto en chunks con ventana deslizante.

    Devuelve lista de (chunk, source) para mantener la procedencia de cada pieza.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append((chunk, source))
        start += step
    return chunks


_client: OpenAI | None = None

# Reintentos explicitos ante errores transitorios de OpenAI -- ver el
# comentario largo en src/graph.py::MAX_RETRIES (misma decision, mismo valor).
_MAX_RETRIES = 2


def _get_client() -> OpenAI:
    """Crea el cliente de OpenAI recien la primera vez que hace falta.

    Antes se creaba al importar el modulo (`_client = OpenAI()` a nivel de
    modulo), lo que exigia OPENAI_API_KEY solo por importar src.tools/src.graph
    -- rompia el job "rules" de CI, que corre sin API key a proposito.
    """
    global _client
    if _client is None:
        _client = OpenAI(max_retries=_MAX_RETRIES)
    return _client


# La API de embeddings limita cada request a 300k tokens y 2048 items. Con
# corpus chicos (Capa 5A, ~16 chunks) un solo request alcanza; con el corpus
# real (2451 chunks) lo supera, así que lo partimos en lotes de 300 (300 chunks
# de hasta 1000 caracteres caben cómodos debajo de los dos límites) y unimos
# las respuestas.
_BATCH_SIZE = 300


def embed_texts(texts: list[str]) -> np.ndarray:
    """Genera embeddings para una lista de textos. Devuelve matriz (N, 1536)."""
    client = _get_client()
    batches = [
        client.embeddings.create(model="text-embedding-3-small", input=texts[i : i + _BATCH_SIZE])
        for i in range(0, len(texts), _BATCH_SIZE)
    ]
    vectors = [item.embedding for response in batches for item in response.data]
    return np.array(vectors, dtype=np.float32)


def rrf(
    list_a: list[tuple[int, float]],
    list_b: list[tuple[int, float]],
    k: int = 1,
) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion: combina dos listas de resultados por posición, no por score.

    k=1 (no el 60 del paper original): medido contra las 520 preguntas de
    evals/ground_truth_retrieval.json (5B.4 paso 6, barrido k=[1,50,60,100,200]),
    k=1 ganó en hit_rate y MRR a la vez. k bajo le da mucho más peso a la posición
    exacta -- deja que la lista que rankeó mejor un chunk domine la fusión, en vez
    de diluirla contra la otra lista. A partir de k=50 los resultados quedan
    identicos entre si (con candidate_k=10, k>>10 aplana las diferencias de rank
    hasta volverlas irrelevantes).
    """
    scores: dict[int, float] = {}
    for rank, (idx, _) in enumerate(list_a):
        # _ descarta el score original — RRF solo usa la posición (rank)
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    for rank, (idx, _) in enumerate(list_b):
        # si un chunk aparece en ambas listas, sus contribuciones se suman
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
