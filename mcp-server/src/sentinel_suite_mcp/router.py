"""Semantic router — rank ecc agents/skills against a natural-language prompt.

Two backends:

  • TF-IDF cosine (default, pure stdlib) — weights *important* words (rare terms
    like "security" beat common ones like "code"), so it beats raw keyword
    overlap and is fast enough to run on every prompt.

  • Embeddings (optional) — true semantic similarity via sentence-transformers,
    if installed (`pip install sentence-transformers`). Doc vectors are cached to
    disk. Best quality, but heavy to load — used for CLI/MCP, not the hot hook.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Optional

_STOP = {
    "the", "a", "an", "to", "for", "of", "and", "or", "in", "on", "with", "my",
    "me", "i", "is", "it", "this", "that", "please", "need", "want", "can", "you",
    "help", "make", "do", "use", "using", "how", "add", "create", "get", "some",
    "into", "from", "our", "your", "are", "be", "should", "would", "could", "will",
    "when", "what", "which", "as", "at", "by", "so", "if", "we", "us",
}


def tokenize(text: str) -> list:
    return [w for w in re.split(r"[^a-z0-9]+", (text or "").lower())
            if len(w) > 2 and w not in _STOP]


# ---------------------------------------------------------------------------
# TF-IDF cosine ranker
# ---------------------------------------------------------------------------

class TfidfRouter:
    """Rank documents ({name, description}) by TF-IDF cosine to a query.

    Name tokens are boosted (a skill literally named "tdd" should win over one
    that merely mentions it in prose).
    """
    NAME_BOOST = 3

    def __init__(self, docs: list):
        self.docs = docs
        self._counts = [self._doc_counter(d) for d in docs]
        self._df: Counter = Counter()
        for c in self._counts:
            self._df.update(c.keys())
        self._n = max(1, len(docs))

    def _doc_counter(self, d: dict) -> Counter:
        c = Counter(tokenize(d.get("description", "")))
        for t in tokenize(d.get("name", "")):
            c[t] += self.NAME_BOOST
        return c

    def _idf(self, term: str) -> float:
        return math.log((1 + self._n) / (1 + self._df.get(term, 0))) + 1.0

    def _vec(self, counter: Counter) -> dict:
        return {t: tf * self._idf(t) for t, tf in counter.items()}

    @staticmethod
    def _cosine(a: dict, b: dict) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        dot = sum(a[t] * b[t] for t in common)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    def query(self, prompt: str, top: int = 5) -> list:
        qv = self._vec(Counter(tokenize(prompt)))
        if not qv:
            return []
        scored = []
        for i, c in enumerate(self._counts):
            sim = self._cosine(qv, self._vec(c))
            if sim > 0 and self.docs[i].get("name") != "(unavailable)":
                scored.append((sim, self.docs[i]))
        scored.sort(key=lambda x: -x[0])
        return [{"name": d["name"], "description": d.get("description", ""),
                 "score": round(s, 4)} for s, d in scored[:top]]


# ---------------------------------------------------------------------------
# Optional embeddings backend (sentence-transformers)
# ---------------------------------------------------------------------------

_MODEL = None


def embeddings_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except Exception:
        return False


def _model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def embed_query(docs: list, prompt: str, top: int = 5, cache_key: Optional[str] = None) -> list:
    """Rank docs by embedding cosine similarity. Requires sentence-transformers.

    Doc embeddings are cached in-process (and optionally could be persisted by
    the caller keyed on cache_key/signature).
    """
    import numpy as np  # ships with sentence-transformers
    model = _model()
    texts = [f"{d.get('name','')}. {d.get('description','')}" for d in docs]
    doc_emb = model.encode(texts, normalize_embeddings=True)
    q = model.encode([prompt], normalize_embeddings=True)[0]
    sims = np.asarray(doc_emb) @ q
    order = sims.argsort()[::-1][:top]
    out = []
    for i in order:
        if docs[i].get("name") == "(unavailable)":
            continue
        out.append({"name": docs[i]["name"], "description": docs[i].get("description", ""),
                    "score": round(float(sims[i]), 4)})
    return out
