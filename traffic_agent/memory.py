from __future__ import annotations

import json
from pathlib import Path


def load_offset(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("offset"), int):
            return int(data["offset"])
    except json.JSONDecodeError:
        return None
    return None


def save_offset(path: Path, offset: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"offset": offset}), encoding="utf-8")


def thread_path(thread_dir: Path, chat_id: int) -> Path:
    return thread_dir / f"{chat_id}.json"


def load_thread(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    messages: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content[:8000]})
    return messages


def save_thread(path: Path, messages: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(messages, ensure_ascii=False), encoding="utf-8")


def trim_thread(messages: list[dict[str, str]], max_turns: int) -> list[dict[str, str]]:
    keep = max(1, max_turns) * 2
    if len(messages) <= keep:
        return messages
    return messages[-keep:]
