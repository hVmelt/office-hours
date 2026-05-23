"""
Embedding with a persistent cache.
The cache key is a hash of (model, input_type, text) — so if the text
or model changes, we re-embed; otherwise we read from disk.
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import voyageai

voyage = voyageai.Client()
MODEL = "voyage-3"
CACHE_PATH = Path("cache/embeddings.json")


def _key(text: str, input_type: str) -> str:
    """Stable cache key for a (text, input_type) pair."""
    raw = f"{MODEL}|{input_type}|{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        with CACHE_PATH.open() as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(exist_ok=True)
    with CACHE_PATH.open("w") as f:
        json.dump(cache, f)


def embed_texts(texts: list[str], input_type: str) -> np.ndarray:
    """
    Embed a list of strings, using the cache to skip already-embedded text.
    input_type is 'document' for stored chunks, 'query' for questions.
    """
    cache = _load_cache()

    # Identify which texts we actually need to embed via the API.
    to_embed: list[tuple[int, str]] = []  # (original_index, text)
    embeddings: list[list[float] | None] = [None] * len(texts)

    for i, text in enumerate(texts):
        key = _key(text, input_type)
        if key in cache:
            embeddings[i] = cache[key]
        else:
            to_embed.append((i, text))

    # Call the API only for cache misses.
    if to_embed:
        print(f"  embedding {len(to_embed)} new texts (cache hit: {len(texts) - len(to_embed)})...")
        new_texts = [t for _, t in to_embed]
        result = voyage.embed(new_texts, model=MODEL, input_type=input_type)
        for (i, text), vec in zip(to_embed, result.embeddings):
            embeddings[i] = vec
            cache[_key(text, input_type)] = vec
        _save_cache(cache)
    else:
        print(f"  all {len(texts)} embeddings found in cache")

    return np.array(embeddings)