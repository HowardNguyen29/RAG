from __future__ import annotations

import re
from typing import Iterable, List


DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " "]


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def split_sentences(text: str) -> List[str]:
    text = normalize_text(text)
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    return [p.strip() for p in parts if p.strip()]


def _fixed_split(text: str, max_chars: int, overlap: int) -> List[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    step = max_chars - overlap
    if step <= 0:
        step = max_chars

    chunks = []
    for i in range(0, len(text), step):
        chunk = text[i : i + max_chars]
        if chunk.strip():
            chunks.append(chunk.strip())
    return chunks


def _group_sentences(sentences: Iterable[str], max_chars: int) -> List[str]:
    chunks: List[str] = []
    current = ""
    for s in sentences:
        candidate = (current + " " + s).strip() if current else s
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks


def _recursive_split(text: str, max_chars: int, separators: List[str]) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    if not separators:
        return _fixed_split(text, max_chars, overlap=0)

    sep = separators[0]
    pieces = text.split(sep)
    if len(pieces) == 1:
        return _recursive_split(text, max_chars, separators[1:])

    chunks: List[str] = []
    current = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        candidate = (current + sep + piece) if current else piece
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(piece) > max_chars:
            chunks.extend(_recursive_split(piece, max_chars, separators[1:]))
        else:
            current = piece

    if current:
        chunks.append(current)

    return [c.strip() for c in chunks if c.strip()]


def _add_overlap(chunks: List[str], overlap: int) -> List[str]:
    if overlap <= 0:
        return chunks

    out: List[str] = []
    prev_raw = ""
    for raw in chunks:
        chunk = raw
        if prev_raw:
            chunk = prev_raw[-overlap:] + raw
        out.append(chunk)
        prev_raw = raw
    return out


def chunk_text(
    text: str,
    *,
    max_chars: int = 1200,
    overlap: int = 200,
    strategy: str = "recursive",
    separators: List[str] | None = None,
) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []

    strategy = strategy.lower().strip()
    if strategy == "fixed":
        return _fixed_split(text, max_chars=max_chars, overlap=overlap)

    if strategy == "sentence":
        sentences = split_sentences(text)
        chunks = _group_sentences(sentences, max_chars=max_chars)
        return _add_overlap(chunks, overlap=overlap)

    if strategy == "recursive":
        chunks = _recursive_split(text, max_chars=max_chars, separators=separators or DEFAULT_SEPARATORS)
        return _add_overlap(chunks, overlap=overlap)

    raise ValueError(f"Unknown strategy: {strategy}")
