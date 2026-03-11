from __future__ import annotations

from typing import Any

import requests


class TelegramClient:
    def __init__(self, bot_token: str, max_message_chars: int = 3900) -> None:
        self.bot_token = bot_token
        self.max_message_chars = max_message_chars

    def _api(self, method: str, payload: dict[str, Any], timeout: int = 40) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{self.bot_token}/{method}"
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data}")
        return data

    def get_updates(self, offset: int | None, timeout_s: int) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout_s, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        data = self._api("getUpdates", payload=payload, timeout=timeout_s + 10)
        return data.get("result", [])

    def send_message(self, chat_id: int, text: str) -> None:
        for chunk in split_text(text, self.max_message_chars):
            self._api("sendMessage", payload={"chat_id": chat_id, "text": chunk})


def split_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.splitlines(keepends=True):
        if current_len + len(line) > max_chars and current:
            chunks.append("".join(current).rstrip())
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line)

    if current:
        chunks.append("".join(current).rstrip())

    return chunks
