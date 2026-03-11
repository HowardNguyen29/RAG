from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from raglab.chunking import chunk_text
from raglab.embeddings import create_embedder
from raglab.index import VectorIndex
from raglab.io import read_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Ingest a document and build a vector index.")
    p.add_argument("--input", required=True, help="Path to input PDF/TXT/MD")
    p.add_argument("--index", required=True, help="Output index directory")
    p.add_argument("--chunk-size", type=int, default=1200, help="Max chars per chunk")
    p.add_argument("--overlap", type=int, default=200, help="Overlap chars between chunks")
    p.add_argument(
        "--strategy",
        choices=["fixed", "sentence", "recursive"],
        default="recursive",
        help="Chunking strategy",
    )
    p.add_argument("--embedder", choices=["hash", "sbert"], default="hash")
    p.add_argument("--dim", type=int, default=768, help="Embedding dim (hash only)")
    p.add_argument("--embed-model", default=None, help="Embedding model name (sbert only)")
    return p


def main() -> None:
    args = build_parser().parse_args()

    text = read_text(args.input)
    chunks = chunk_text(
        text,
        max_chars=args.chunk_size,
        overlap=args.overlap,
        strategy=args.strategy,
    )
    if not chunks:
        raise SystemExit("No chunks produced. Check input file.")

    embedder = create_embedder(args.embedder, dim=args.dim, model=args.embed_model)
    embeddings = embedder.embed_documents(chunks)

    index = VectorIndex(dim=embeddings.shape[1])
    metadatas = [
        {
            "source": str(args.input),
            "chunk_id": i,
            "chars": len(c),
        }
        for i, c in enumerate(chunks)
    ]
    index.add(embeddings, chunks, metadatas)

    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "chunking": {
            "strategy": args.strategy,
            "chunk_size": args.chunk_size,
            "overlap": args.overlap,
        },
        "embedder": {
            "name": args.embedder,
            "dim": int(embeddings.shape[1]),
            "model": args.embed_model,
        },
        "counts": {
            "chunks": len(chunks),
        },
    }

    index.save(args.index, meta=meta)
    print(f"Saved index to {args.index} with {len(chunks)} chunks.")


if __name__ == "__main__":
    main()
