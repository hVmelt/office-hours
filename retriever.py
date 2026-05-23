"""
Vector search over chunks. Pure NumPy for now — Postgres + pgvector on day 3.
"""

import numpy as np


def top_k(
    query_vec: np.ndarray,
    chunk_vecs: np.ndarray,
    chunks: list[dict],
    k: int = 5,
) -> list[dict]:
    """
    Find the k chunks most similar to the query vector.
    Returns the chunk dicts with a 'score' field added.
    Voyage embeddings are pre-normalized, so dot product == cosine similarity.
    """
    similarities = chunk_vecs @ query_vec
    top_indices = np.argsort(similarities)[::-1][:k]
    results = []
    for i in top_indices:
        chunk = dict(chunks[i])
        chunk["score"] = float(similarities[i])
        results.append(chunk)
    return results