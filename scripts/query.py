from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from raglab.embeddings import create_embedder
from raglab.index import VectorIndex
from raglab.llm import create_llm


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Query a vector index.")
    p.add_argument("--index", required=True, help="Index directory")
    p.add_argument("--question", required=True, help="User question")
    p.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    p.add_argument("--llm", choices=["mock", "chat"], default="mock")
    p.add_argument("--llm-url", default=None, help="LLM endpoint (chat-completions compatible)")
    p.add_argument("--llm-api-key", default=None, help="LLM API key")
    p.add_argument("--llm-model", default=None, help="LLM model name")
    p.add_argument("--show-context", action="store_true", help="Print retrieved chunks")
    return p


def main() -> None:
    args = build_parser().parse_args()

    index = VectorIndex.load(args.index)
    embedder_cfg = index.meta.get("embedder", {})
    embedder = create_embedder(
        embedder_cfg.get("name", "hash"),
        dim=int(embedder_cfg.get("dim", 768)),
        model=embedder_cfg.get("model"),
    )

    query_vec = embedder.embed_query(args.question)
    results = index.search(query_vec, top_k=args.top_k)
    contexts = [r.text for r in results]

    llm = create_llm(
        args.llm,
        url=args.llm_url,
        api_key=args.llm_api_key,
        model=args.llm_model,
    )
    answer = llm.generate(args.question, contexts)

    print(answer)
    print("\n---\n")
    print("Top chunks:")
    for r in results:
        src = r.meta.get("source", "")
        cid = r.meta.get("chunk_id", "")
        print(f"- score={r.score:.4f} source={src} chunk={cid} chars={r.meta.get('chars')}")
        if args.show_context:
            print(r.text[:500].replace("\n", " "))
            print()


if __name__ == "__main__":
    main()
