from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from traffic_agent.agent_runtime import build_agent_executor, extract_text_from_agent_result
from traffic_agent.config import AppConfig
from traffic_agent.mcp_client import (
    LocalMCPConfig,
    LocalMCPToolClient,
    MCPToolClient,
    RemoteMCPConfig,
    RemoteSSEMCPToolClient,
)
from traffic_agent.memory import (
    load_offset,
    load_thread,
    save_offset,
    save_thread,
    thread_path,
    trim_thread,
)
from traffic_agent.prompts import augment_with_config_fallback
from traffic_agent.services.routing import RoutingService
from traffic_agent.services.telegram import TelegramClient
from traffic_agent.services.weather import WeatherService
from traffic_agent.tools import build_tools


@dataclass(frozen=True)
class RuntimeOptions:
    offset_file: Path
    thread_dir: Path
    tool_backend: str = "mcp"
    mcp_client_mode: str = "sse"
    mcp_server_module: str = "traffic_agent.mcp_server"
    mcp_server_url: str = "http://127.0.0.1:8000/sse"
    max_turns: int = 12
    poll_timeout: int = 25
    sleep_seconds: float = 1.0
    once: bool = False


class TrafficTelegramBot:
    def __init__(self, config: AppConfig, options: RuntimeOptions) -> None:
        self.config = config
        self.options = options
        if self.options.tool_backend not in {"local", "mcp"}:
            raise ValueError("tool_backend must be either 'local' or 'mcp'")
        if self.options.mcp_client_mode not in {"stdio", "sse"}:
            raise ValueError("mcp_client_mode must be either 'stdio' or 'sse'")

        self.routing = RoutingService(api_key=config.tomtom_api_key)
        self.weather = WeatherService()
        self.mcp_client: MCPToolClient | None = None
        if self.options.tool_backend == "mcp":
            if self.options.mcp_client_mode == "stdio":
                self.mcp_client = LocalMCPToolClient(
                    LocalMCPConfig(module=self.options.mcp_server_module)
                )
            else:
                self.mcp_client = RemoteSSEMCPToolClient(
                    RemoteMCPConfig(server_url=self.options.mcp_server_url)
                )
        self.tools = build_tools(
            config=config,
            routing=self.routing,
            weather=self.weather,
            tool_backend=self.options.tool_backend,
            mcp_client=self.mcp_client,
        )
        self.agent = build_agent_executor(config=config, tools=self.tools)
        self.telegram = TelegramClient(bot_token=config.bot_token)

        self.options.thread_dir.mkdir(parents=True, exist_ok=True)
        self.next_offset = load_offset(self.options.offset_file)

    def process_user_message(self, chat_id: int, text: str) -> str:
        normalized = text.strip()
        if not normalized:
            return "Tin nhan rong."

        if normalized in {"/start", "/help"}:
            return (
                "Lenh co san:\n"
                "/home2work - Tim duong it tac nhat tu nha den cong ty + goi y ao mua\n"
                "/ping - Kiem tra bot song\n"
                "/reset - Xoa bo nho hoi thoai cua chat nay\n"
                "\n"
                "Neu ban noi 'nha'/'cong ty' ma khong gui toa do, bot se fallback toa do tu CONFIG.\n"
                "\n"
                "Ban cung co the chat tu do, vi du:\n"
                "- Tim duong tu 10.78,106.70 den 10.80,106.65\n"
                "- Cho toi biet co can mac ao mua o cong ty khong"
            )

        if normalized == "/ping":
            return "pong"

        thread_file = thread_path(self.options.thread_dir, chat_id)
        if normalized == "/reset":
            if thread_file.exists():
                thread_file.unlink()
            return "Da xoa bo nho hoi thoai cho chat nay."

        history = load_thread(thread_file)

        if normalized == "/home2work":
            user_prompt = (
                f"Bay gio la {datetime.now().strftime('%H:%M %d/%m/%Y')}. "
                "Tim duong it tac nhat tu nha den cong ty va cho loi khuyen ao mua."
            )
        else:
            user_prompt = normalized

        user_prompt = augment_with_config_fallback(user_prompt, config=self.config)

        model_input_messages = [*history, {"role": "user", "content": user_prompt}]
        result: Any = self.agent.invoke({"messages": model_input_messages})
        text_out = extract_text_from_agent_result(result).strip()
        if not text_out:
            return "Khong co noi dung tra loi."

        history.extend(
            [
                {"role": "user", "content": normalized[:8000]},
                {"role": "assistant", "content": text_out[:8000]},
            ]
        )
        save_thread(thread_file, trim_thread(history, max_turns=self.options.max_turns))
        return text_out

    def run(self) -> None:
        print("Telegram agent started. Waiting for messages...")

        while True:
            try:
                updates = self.telegram.get_updates(offset=self.next_offset, timeout_s=self.options.poll_timeout)
                for update in updates:
                    update_id = int(update["update_id"])
                    self.next_offset = update_id + 1
                    save_offset(self.options.offset_file, self.next_offset)

                    message = update.get("message") or {}
                    chat = message.get("chat") or {}
                    text = message.get("text")
                    if text is None or "id" not in chat:
                        continue

                    chat_id = int(chat["id"])
                    try:
                        answer = self.process_user_message(chat_id=chat_id, text=text)
                    except Exception as exc:  # pragma: no cover
                        answer = f"Loi khi xu ly: {_format_error_for_user(exc)}"
                    self.telegram.send_message(chat_id=chat_id, text=answer)

                if self.options.once:
                    break
                time.sleep(self.options.sleep_seconds)
            except KeyboardInterrupt:
                break
            except Exception as exc:  # pragma: no cover
                print(f"[warn] loop error: {exc}")
                time.sleep(5)


def _flatten_exceptions(exc: BaseException) -> list[BaseException]:
    members = getattr(exc, "exceptions", None)
    if isinstance(members, (list, tuple)) and members:
        flat: list[BaseException] = []
        for child in members:
            if isinstance(child, BaseException):
                flat.extend(_flatten_exceptions(child))
        if flat:
            return flat
    return [exc]


def _format_error_for_user(exc: BaseException) -> str:
    leaf = _flatten_exceptions(exc)[-1]
    text = str(leaf).strip() or leaf.__class__.__name__
    msg = f"{leaf.__class__.__name__}: {text}"

    lowered = msg.lower()
    if "mcp sse call failed" in lowered or "connect" in lowered or "connection refused" in lowered:
        return f"{msg}. Kiem tra MCP server dang chay: python -m traffic_agent.mcp_server --transport sse"
    return msg
