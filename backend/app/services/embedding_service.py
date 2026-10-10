# Service embedding — sentence-transformers all-MiniLM-L6-v2 (384 dim, lokal/gratis).

import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    # Load model sekali saja (lazy singleton).
    logger.info("Memuat model embedding %s ...", MODEL_NAME)
    return SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> list[float]:
    # Embedding satu teks (dinormalisasi agar cosine similarity = dot product).
    vector = _model().encode(text, normalize_embeddings=True)
    return [float(value) for value in vector]


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    # Embedding batch (lebih cepat untuk seed).
    vectors = _model().encode(texts, normalize_embeddings=True, batch_size=32)
    return [[float(value) for value in row] for row in vectors]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    # Cosine similarity dua vektor.
    va = np.asarray(a, dtype=float)
    vb = np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)
