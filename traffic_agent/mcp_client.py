from __future__ import annotations

import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Protocol


class MCPToolClient(Protocol):
    def call_tool(self, name: str, arguments: dict[str, Any]) -> str: ...


@dataclass(frozen=True)
class LocalMCPConfig:
    module: str = "traffic_agent.mcp_server"
    command: str = sys.executable


@dataclass(frozen=True)
class RemoteMCPConfig:
    server_url: str = "http://127.0.0.1:8000/sse"


class LocalMCPToolClient:
    def __init__(self, config: LocalMCPConfig | None = None) -> None:
        self.config = config or LocalMCPConfig()

    async def _call_tool_async(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise RuntimeError(
                "MCP dependencies are missing. Install mcp package first."
            ) from exc

        server_params = StdioServerParameters(
            command=self.config.command,
            args=["-m", self.config.module],
            env=dict(os.environ),
        )

        async with stdio_client(server_params) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                return extract_result_text(result)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            return _run_async_compat(self._call_tool_async(name=name, arguments=arguments))
        except Exception as exc:
            raise RuntimeError(f"MCP stdio call failed: {_exception_summary(exc)}") from exc


class RemoteSSEMCPToolClient:
    def __init__(self, config: RemoteMCPConfig | None = None) -> None:
        self.config = config or RemoteMCPConfig()

    async def _call_tool_async(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client
        except ImportError as exc:
            raise RuntimeError(
                "MCP SSE client is unavailable. Install mcp package first."
            ) from exc

        async with sse_client(self.config.server_url) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                return extract_result_text(result)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            return _run_async_compat(self._call_tool_async(name=name, arguments=arguments))
        except Exception as exc:
            raise RuntimeError(
                f"MCP SSE call failed ({self.config.server_url}): {_exception_summary(exc)}"
            ) from exc


def _run_async_compat(coro: Any) -> str:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(lambda: asyncio.run(coro))
        return future.result()


def _flatten_exceptions(exc: BaseException) -> list[BaseException]:
    # ExceptionGroup (TaskGroup) can hide the underlying network error.
    members = getattr(exc, "exceptions", None)
    if isinstance(members, (list, tuple)) and members:
        flat: list[BaseException] = []
        for child in members:
            if isinstance(child, BaseException):
                flat.extend(_flatten_exceptions(child))
        if flat:
            return flat
    return [exc]


def _exception_summary(exc: BaseException) -> str:
    chain = _flatten_exceptions(exc)
    leaf = chain[-1]
    message = str(leaf).strip() or leaf.__class__.__name__
    return f"{leaf.__class__.__name__}: {message}"


def extract_result_text(result: Any) -> str:
    is_error = getattr(result, "isError", False) or getattr(result, "is_error", False)
    if is_error:
        raise RuntimeError(f"MCP tool call failed: {result}")

    content = getattr(result, "content", None)
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if isinstance(text, str) and text.strip():
                chunks.append(text)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                chunks.append(item["text"])
            else:
                raw = str(item)
                if raw:
                    chunks.append(raw)
        if chunks:
            return "\n".join(chunks).strip()

    if isinstance(result, dict):
        if isinstance(result.get("content"), list):
            return "\n".join(str(x) for x in result["content"]).strip()
        return str(result)

    return str(result)
