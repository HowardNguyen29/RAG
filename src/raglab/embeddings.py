from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np


class BaseEmbedder:
    name: str = "base"

    @property
    def dim(self) -> int:
        raise NotImplementedError

    def embed_documents(self, texts: Iterable[str]) -> np.ndarray:
        raise NotImplementedError

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]


class HashEmbedder(BaseEmbedder):
    name = "hash"

    def __init__(self, dim: int = 768, seed: int = 13) -> None:
        self._dim = int(dim)
        self.seed = int(seed)
        if self._dim <= 0:
            raise ValueError("dim must be > 0")

    @property
    def dim(self) -> int:
        return self._dim

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[A-Za-z0-9_]+", text.lower())

    def _hash(self, token: str) -> tuple[int, int]:
        h = hashlib.blake2b((str(self.seed) + token).encode("utf-8"), digest_size=8).digest()
        val = int.from_bytes(h, "little", signed=False)
        idx = val % self._dim
        sign = 1 if (val >> 63) & 1 == 0 else -1
        return idx, sign

    def embed_documents(self, texts: Iterable[str]) -> np.ndarray:
        texts = list(texts)
        vecs = np.zeros((len(texts), self._dim), dtype=np.float32)
        for i, text in enumerate(texts):
            tokens = self._tokenize(text)
            if not tokens:
                continue
            for tok in tokens:
                idx, sign = self._hash(tok)
                vecs[i, idx] += sign
            norm = np.linalg.norm(vecs[i])
            if norm > 0:
                vecs[i] /= norm
        return vecs


class SentenceTransformerEmbedder(BaseEmbedder):
    name = "sbert"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: Optional[str] = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("sentence-transformers is not installed") from exc
        self.model = SentenceTransformer(model_name, device=device)
        self._dim = int(self.model.get_sentence_embedding_dimension())

    @property
    def dim(self) -> int:
        return self._dim

    def embed_documents(self, texts: Iterable[str]) -> np.ndarray:
        vecs = self.model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vecs, dtype=np.float32)


def create_embedder(
    name: str,
    *,
    dim: int = 768,
    model: Optional[str] = None,
    device: Optional[str] = None,
) -> BaseEmbedder:
    name = name.lower().strip()
    if name == "hash":
        return HashEmbedder(dim=dim)
    if name == "sbert":
        return SentenceTransformerEmbedder(model_name=model or "all-MiniLM-L6-v2", device=device)
    raise ValueError(f"Unknown embedder: {name}")
