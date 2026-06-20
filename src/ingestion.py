# src/ingestion.py
"""Pipeline de ingesta: texto → chunks → embeddings → índice en memoria."""

from dataclasses import dataclass, field

import numpy as np
from openai import OpenAI


@dataclass
class InMemoryIndex:
    chunks: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    embeddings: np.ndarray | None = None

    def is_ready(self) -> bool:
        return self.embeddings is not None and len(self.chunks) > 0


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


_client = OpenAI()


def embed_texts(texts: list[str]) -> np.ndarray:
    """Genera embeddings para una lista de textos. Devuelve matriz (N, 1536)."""
    response = _client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    vectors = [item.embedding for item in response.data]
    return np.array(vectors, dtype=np.float32)


def build_index(documents: list[tuple[str, str]], chunk_size: int = 500, chunk_step: int = 250) -> InMemoryIndex:
    """Toma documentos (texto, source), los chunkea, los embeddea y devuelve el índice listo."""
    all_chunks: list[str] = []
    all_sources: list[str] = []

    for text, source in documents:
        for chunk, src in chunk_text(text, source, chunk_size, chunk_step):
            all_chunks.append(chunk)
            all_sources.append(src)

    embeddings = embed_texts(all_chunks)

    return InMemoryIndex(
        chunks=all_chunks,
        sources=all_sources,
        embeddings=embeddings,
    )
