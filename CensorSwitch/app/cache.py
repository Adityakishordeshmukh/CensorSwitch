"""
Student B: semantic cache.

SemanticCache below is a WORKING but NAIVE placeholder: it normalizes text and does
substring/exact matching, so it only catches identical-ish questions. Your job is to
replace `_similarity` with real semantic similarity, for example:

    from sentence_transformers import SentenceTransformer
    import numpy as np

    model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed(text: str) -> np.ndarray:
        return model.encode(text, normalize_embeddings=True)

    def _similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))  # cosine similarity, since both are normalized

Then swap the linear scan in `lookup()` for a FAISS index once entries grow past a
few hundred, so lookup stays fast:

    import faiss
    index = faiss.IndexFlatIP(384)  # 384 = embedding dim for MiniLM

Tune `settings.cache_similarity_threshold` (currently in app/config.py) once you have
real embeddings -- 0.90-0.95 is a reasonable starting range for cosine similarity.
"""

import re
from dataclasses import dataclass

from app.config import settings


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


@dataclass
class CacheEntry:
    normalized_prompt: str
    original_prompt: str
    answer: str
    provider: str


class SemanticCache:
    def __init__(self):
        self._entries: list[CacheEntry] = []

    def _similarity(self, a: str, b: str) -> float:
        """Placeholder similarity: 1.0 for exact match, else word-overlap ratio.
        Replace with real embedding cosine similarity (see module docstring)."""
        if a == b:
            return 1.0
        words_a, words_b = set(a.split()), set(b.split())
        if not words_a or not words_b:
            return 0.0
        overlap = len(words_a & words_b) / len(words_a | words_b)
        return overlap

    def lookup(self, prompt: str) -> CacheEntry | None:
        normalized = _normalize(prompt)
        best_entry, best_score = None, 0.0
        for entry in self._entries:
            score = self._similarity(normalized, entry.normalized_prompt)
            if score > best_score:
                best_entry, best_score = entry, score
        if best_entry and best_score >= settings.cache_similarity_threshold:
            return best_entry
        return None

    def store(self, prompt: str, answer: str, provider: str) -> None:
        self._entries.append(
            CacheEntry(
                normalized_prompt=_normalize(prompt),
                original_prompt=prompt,
                answer=answer,
                provider=provider,
            )
        )

    def stats(self) -> dict:
        return {"entries": len(self._entries)}


# Shared instance used by the gateway
semantic_cache = SemanticCache()
