# Service embedding — sentence-transformers all-MiniLM-L6-v2 (384 dim, lokal/gratis).
#
# Di Vercel, sentence-transformers/torch tidak diinstal (bundle terlalu besar).
# Bila model tidak tersedia, dipakai fallback embedding hash 384-dim yang
# deterministik agar fitur pencarian resource tetap berjalan (kualitas lebih rendah).
#
# sentence-transformers di-import LAZY agar startup tetap cepat.

import hashlib
import logging
import math
import re
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - hanya untuk type checker
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
_TOKEN_RE = re.compile(r"[a-z0-9\u4e00-\u9fff]+")


@lru_cache(maxsize=1)
def _model() -> "SentenceTransformer | None":
    # Import berat dilakukan di sini (saat pertama dipakai), bukan saat app start.
    try:
        from sentence_transformers import SentenceTransformer

        logger.info("Memuat model embedding %s ...", MODEL_NAME)
        return SentenceTransformer(MODEL_NAME)
    except Exception as exc:  # noqa: BLE001 - termasuk ImportError / gagal download model
        logger.warning(
            "sentence-transformers tidak tersedia; memakai fallback hash embedding (%s)",
            exc,
        )
        return None


def _hash_embedding(text: str) -> list[float]:
    # Hashing trick deterministik: token → bucket 384, signed, lalu dinormalisasi.
    vector = [0.0] * EMBEDDING_DIM
    for token in _TOKEN_RE.findall(text.lower()):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "little") % EMBEDDING_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def generate_embedding(text: str) -> list[float]:
    # Embedding satu teks (dinormalisasi agar cosine similarity = dot product).
    model = _model()
    if model is None:
        return _hash_embedding(text)
    vector = model.encode(text, normalize_embeddings=True)
    return [float(value) for value in vector]


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    # Embedding batch (lebih cepat untuk seed).
    model = _model()
    if model is None:
        return [_hash_embedding(text) for text in texts]
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [[float(value) for value in row] for row in vectors]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    # Cosine similarity dua vektor.
    import numpy as np

    va = np.asarray(a, dtype=float)
    vb = np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)
