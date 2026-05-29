"""
Vector search via Postgres + pgvector.
"""

import numpy as np
from db import get_connection


def top_k(query_vec: np.ndarray, k: int = 5, session_id: str | None = None) -> list[dict]:
    """
    Find the k chunks most similar to the query vector, restricted to
    documents that are either public demo docs or owned by this session.

    Uses pgvector's cosine distance operator (<=>).
    Distance is 1 - cosine_similarity, so we convert it back for a score
    that matches our day-2 interpretation (higher = more similar).
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                documents.name AS doc,
                chunks.page AS page,
                chunks.text AS text,
                1 - (chunks.embedding <=> %s) AS score
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            WHERE documents.is_demo = TRUE OR documents.session_id = %s
            ORDER BY chunks.embedding <=> %s
            LIMIT %s
            """,
            (query_vec, session_id, query_vec, k),
        )
        rows = cur.fetchall()

    return [
        {"doc": row[0], "page": row[1], "text": row[2], "score": float(row[3])}
        for row in rows
    ]