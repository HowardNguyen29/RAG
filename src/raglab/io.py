from __future__ import annotations

import os
from pathlib import Path


def read_text(path: str) -> str:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(path)

    ext = path_obj.suffix.lower()
    if ext in {".txt", ".md"}:
        return path_obj.read_text(encoding="utf-8", errors="ignore")

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("pypdf is required to read PDF files") from exc

        reader = PdfReader(str(path_obj))
        parts = []
        for page in reader.pages:
            text = page.extract_text() or ""
            parts.append(text)
        return "\n".join(parts)

    raise ValueError(f"Unsupported file type: {ext}")
