from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np


@dataclass
class SearchResult:
    text: str
    meta: Dict[str, Any]
    score: float


class VectorIndex:
    def __init__(self, dim: int) -> None:
        self.dim = int(dim)
        self.embeddings = np.empty((0, self.dim), dtype=np.float32)
        self.chunks: List[Dict[str, Any]] = []
        self.meta: Dict[str, Any] = {}

    def add(self, embeddings: np.ndarray, texts: Iterable[str], metadatas: Iterable[Dict[str, Any]]) -> None:
        texts = list(texts)
        metadatas = list(metadatas)
        if len(texts) != len(metadatas):
            raise ValueError("texts and metadatas must have same length")
        if embeddings.shape[0] != len(texts) or embeddings.shape[1] != self.dim:
            raise ValueError("embeddings shape does not match index dim")

        self.embeddings = np.vstack([self.embeddings, embeddings.astype(np.float32, copy=False)])
        for text, meta in zip(texts, metadatas):
            self.chunks.append({"text": text, "meta": meta})

    def search(self, query_vec: np.ndarray, top_k: int = 5) -> List[SearchResult]:
        if self.embeddings.size == 0:
            return []
        query_vec = np.asarray(query_vec, dtype=np.float32)
        if query_vec.shape[0] != self.dim:
            raise ValueError("query vector dim mismatch")

        scores = self.embeddings @ query_vec
        top_k = min(top_k, len(scores))
        idxs = np.argpartition(-scores, top_k - 1)[:top_k]
        idxs = idxs[np.argsort(-scores[idxs])]

        results: List[SearchResult] = []
        for idx in idxs:
            chunk = self.chunks[int(idx)]
            results.append(SearchResult(text=chunk["text"], meta=chunk["meta"], score=float(scores[idx])))
        return results

    def save(self, path: str, meta: Dict[str, Any]) -> None:
        os.makedirs(path, exist_ok=True)
        np.save(os.path.join(path, "embeddings.npy"), self.embeddings)
        with open(os.path.join(path, "chunks.jsonl"), "w", encoding="utf-8") as f:
            for chunk in self.chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        with open(os.path.join(path, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        self.meta = meta

    @classmethod
    def load(cls, path: str) -> "VectorIndex":
        embeddings = np.load(os.path.join(path, "embeddings.npy"))
        with open(os.path.join(path, "chunks.jsonl"), "r", encoding="utf-8") as f:
            chunks = [json.loads(line) for line in f if line.strip()]
        with open(os.path.join(path, "meta.json"), "r", encoding="utf-8") as f:
            meta = json.load(f)

        index = cls(dim=int(embeddings.shape[1]))
        index.embeddings = embeddings.astype(np.float32, copy=False)
        index.chunks = chunks
        index.meta = meta
        return index
