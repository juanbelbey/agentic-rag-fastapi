# src/ingestion.py
"""Pipeline de ingesta: texto → chunks → embeddings → índice en memoria."""

from collections import Counter
from dataclasses import dataclass, field
import math

import numpy as np
from openai import OpenAI


@dataclass
class InMemoryIndex:
    chunks: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    embeddings: np.ndarray | None = None
    keyword_index: "KeywordIndex" = field(default_factory=lambda: KeywordIndex())

    def is_ready(self) -> bool:
        return self.embeddings is not None and len(self.chunks) > 0

    def hybrid_search(
        self,
        query: str,
        vector_top_k: int = 10,
        keyword_top_k: int = 10,
    ) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
        """Devuelve (vector_results, keyword_results) antes de fusionar con RRF."""
        query_vec = embed_texts([query])[0]
        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_vec)
        cos_scores = (self.embeddings @ query_vec) / norms
        top_vector = sorted(enumerate(cos_scores.tolist()), key=lambda x: x[1], reverse=True)[:vector_top_k]

        top_keyword = self.keyword_index.search(query, keyword_top_k)

        return top_vector, top_keyword


class KeywordIndex:
    """Índice TF-IDF liviano sobre los mismos chunks del InMemoryIndex."""

    def __init__(self) -> None:
        self.docs: list[str] = []
        self._idf: dict[str, float] = {}

    def fit(self, docs: list[str]) -> None:
        self.docs = docs
        N = len(docs)
        df: Counter = Counter()
        for doc in docs:
            # set() para que un término que aparece 5 veces en el mismo doc
            # cuente como 1 aparición de documento, no como 5
            df.update(set(doc.lower().split()))
        # +1 en numerador y denominador para evitar división por cero y suavizar
        self._idf = {term: math.log((N + 1) / (count + 1)) for term, count in df.items()}

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        query_terms = query.lower().split()
        scores: list[float] = []
        for doc in self.docs:
            doc_terms = doc.lower().split()
            tf = Counter(doc_terms)
            doc_len = len(doc_terms)
            # TF-IDF por término de la query: cuán frecuente es en este doc × cuán raro es en el corpus
            score = sum((tf[t] / doc_len) * self._idf.get(t, 0.0) for t in query_terms)
            scores.append(score)
        # enumerate convierte [score0, score1, ...] en [(0, score0), (1, score1), ...]
        # para conservar el índice original del chunk al ordenar
        return sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]


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


def _get_client() -> OpenAI:
    """Crea el cliente de OpenAI recien la primera vez que hace falta.

    Antes se creaba al importar el modulo (`_client = OpenAI()` a nivel de
    modulo), lo que exigia OPENAI_API_KEY solo por importar src.tools/src.graph
    -- rompia el job "rules" de CI, que corre sin API key a proposito.
    """
    global _client
    if _client is None:
        _client = OpenAI()
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
    k: int = 60,
) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion: combina dos listas de resultados por posición, no por score."""
    scores: dict[int, float] = {}
    for rank, (idx, _) in enumerate(list_a):
        # _ descarta el score original — RRF solo usa la posición (rank)
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    for rank, (idx, _) in enumerate(list_b):
        # si un chunk aparece en ambas listas, sus contribuciones se suman
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def build_index(documents: list[tuple[str, str]], chunk_size: int = 500, chunk_step: int = 250) -> InMemoryIndex:
    """Toma documentos (texto, source), los chunkea, los embeddea y devuelve el índice listo."""
    all_chunks: list[str] = []
    all_sources: list[str] = []

    for text, source in documents:
        for chunk, src in chunk_text(text, source, chunk_size, chunk_step):
            all_chunks.append(chunk)
            all_sources.append(src)

    embeddings = embed_texts(all_chunks)

    keyword_index = KeywordIndex()
    keyword_index.fit(all_chunks)

    return InMemoryIndex(
        chunks=all_chunks,
        sources=all_sources,
        embeddings=embeddings,
        keyword_index=keyword_index,
    )
