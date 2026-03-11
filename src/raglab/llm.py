from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List, Optional

import requests


class BaseLLM:
    name: str = "base"

    def generate(self, question: str, contexts: List[str]) -> str:
        raise NotImplementedError


class MockLLM(BaseLLM):
    name = "mock"

    def generate(self, question: str, contexts: List[str]) -> str:
        if not contexts:
            return "Khong tim thay doan nao phu hop trong index."
        top = contexts[0].strip()
        return (
            "Tra loi (mock):\n"
            f"- Cau hoi: {question}\n"
            "- Tom tat nhanh tu doan lien quan nhat:\n"
            f"{top}"
        )


@dataclass
class ChatCompletionsLLM(BaseLLM):
    name: str = "chat"
    url: str = ""
    api_key: str = ""
    model: str = ""
    timeout: int = 60

    def generate(self, question: str, contexts: List[str]) -> str:
        if not self.url or not self.model:
            raise ValueError("LLM url/model is not configured")

        system_prompt = (
            "Ban la tro ly RAG. Tra loi ngan gon, dung thong tin tu context. "
            "Neu context khong du, noi ro khong chac chan."
        )
        ctx_lines = "\n\n".join([f"[{i+1}] {c}" for i, c in enumerate(contexts)])
        user_prompt = f"Cau hoi: {question}\n\nContext:\n{ctx_lines}"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        resp = requests.post(self.url, headers=headers, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Unexpected LLM response format") from exc


def create_llm(
    name: str,
    *,
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> BaseLLM:
    name = name.lower().strip()
    if name == "mock":
        return MockLLM()
    if name == "chat":
        return ChatCompletionsLLM(
            url=url or os.getenv("LLM_URL", ""),
            api_key=api_key or os.getenv("LLM_API_KEY", ""),
            model=model or os.getenv("LLM_MODEL", ""),
        )
    raise ValueError(f"Unknown LLM: {name}")
