from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from traffic_agent.config import AppConfig
from traffic_agent.prompts import build_system_prompt


def build_agent_executor(config: AppConfig, tools: list[Any]) -> Any:
    model = ChatOpenAI(
        model=config.openai_model,
        temperature=0,
        api_key=config.openai_api_key,
    )
    system_prompt = build_system_prompt(config)
    return create_agent(model=model, tools=tools, system_prompt=system_prompt)


def extract_text_from_agent_result(result: Any) -> str:
    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if not messages:
            return ""

        last = messages[-1]
        content = last.get("content") if isinstance(last, dict) else getattr(last, "content", "")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    chunks.append(item.get("text", ""))
                elif isinstance(item, str):
                    chunks.append(item)
            return "\n".join([chunk for chunk in chunks if chunk]).strip()

        return str(content)

    return str(result)
