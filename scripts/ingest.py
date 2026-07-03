# scripts/ingest.py
"""Ingesta manual: docs/*.txt -> chunks -> embeddings -> tabla chunks en Supabase.

Se corre a mano (python -m scripts.ingest) cada vez que se agregan o cambian
documentos. main.py NO llama a este script: el servidor solo lee de la tabla,
ingesta y serving son responsabilidades separadas (Capa 5B.1).
"""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from psycopg2.extras import execute_values

from src.ingestion import chunk_text, embed_texts

DOCS_DIR = Path(__file__).parent.parent / "docs"


# Recorro docs/ y leo cada .txt tal cual está en disco. Devuelvo una lista
# de tuplas (texto completo, nombre de archivo) porque más adelante necesito
# los dos datos juntos: el texto para chunkear y el nombre para guardarlo
# como "source" de cada chunk en la tabla.
def load_documents() -> list[tuple[str, str]]:
    """Lee cada .txt de docs/ y devuelve (texto, nombre_de_archivo)."""
    return [
        (path.read_text(encoding="utf-8"), path.name)
        for path in DOCS_DIR.glob("*.txt")
    ]


# Esta es la función que corro a mano cuando quiero (re)ingestar los docs.
# No la llamo desde main.py a propósito: ingesta y serving son dos cosas
# separadas, así el server no vuelve a pagar embeddings ni duplica filas
# cada vez que hago uvicorn --reload.
def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "Falta DATABASE_URL. Agrega en .env: "
            "DATABASE_URL=tu-connection-string-de-supabase"
        )

    documents = load_documents()
    if not documents:
        print("No hay documentos en docs/*.txt. Nada para ingestar.")
        return

    # Chunkeo cada documento por separado (reusando chunk_text de src/ingestion.py,
    # la misma función de la Capa 5A) y voy aplanando todo en tres listas paralelas
    # -- me sirve tenerlas así porque execute_values después necesita filas, no un
    # dict por chunk.
    contents: list[str] = []
    sources: list[str] = []
    chunk_indices: list[int] = []
    for text, source in documents:
        for i, (chunk, src) in enumerate(chunk_text(text, source)):
            contents.append(chunk)
            sources.append(src)
            chunk_indices.append(i)

    print(f"Chunkeados {len(contents)} chunks de {len(documents)} documentos.")

    # Un solo llamado a embed_texts con todos los chunks juntos, no uno por chunk.
    # Esto ya lo tenía resuelto de la Capa 5A: mandar el batch completo es más
    # barato y rápido que hacer una llamada a la API por cada chunk.
    embeddings = embed_texts(contents)
    print("Embeddings generados.")

    # register_vector le enseña a psycopg2 a traducir el tipo vector de pgvector
    # en los dos sentidos (Python -> Postgres y Postgres -> Python). Acá usamos
    # el sentido Python -> Postgres para insertar listas de floats en la columna
    # embedding; sin esto, la inserción rompe. El otro sentido (mandar un vector
    # como parámetro de una query, ej. "embedding <=> %s") lo vamos a necesitar
    # en rag_search() para el vector search, aunque ahí no insertemos nada.
    conn = psycopg2.connect(database_url)
    register_vector(conn)
    try:
        with conn.cursor() as cur:
            # TRUNCATE antes de insertar: sin esto, cada vez
            # que corro el script a mano se duplicarían los chunks.
            cur.execute("TRUNCATE TABLE chunks RESTART IDENTITY;")
            rows = list(zip(contents, sources, chunk_indices, embeddings))
            execute_values(
                cur,
                "INSERT INTO chunks (content, source, chunk_index, embedding) VALUES %s",
                rows,
            )
        conn.commit()
        print(f"Insertados {len(rows)} chunks en Supabase.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
