from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from traffic_agent.bot import RuntimeOptions, TrafficTelegramBot
from traffic_agent.config import load_app_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Telegram traffic/weather agent bot")
    parser.add_argument("--offset-file", default=".telegram/offset.json", help="Path to store update offset")
    parser.add_argument("--thread-dir", default=".telegram/threads", help="Directory to store chat thread memory")
    parser.add_argument(
        "--tool-backend",
        choices=["mcp", "local"],
        default="mcp",
        help="Tool execution backend. 'mcp' runs tools via MCP server.",
    )
    parser.add_argument(
        "--mcp-client-mode",
        choices=["sse", "stdio"],
        default="sse",
        help="How bot connects to MCP server when --tool-backend=mcp.",
    )
    parser.add_argument(
        "--mcp-server-module",
        default="traffic_agent.mcp_server",
        help="Python module path for MCP server when --mcp-client-mode=stdio.",
    )
    parser.add_argument(
        "--mcp-server-url",
        default="http://127.0.0.1:8000/sse",
        help="SSE URL for running MCP server when --mcp-client-mode=sse.",
    )
    parser.add_argument("--max-turns", type=int, default=12, help="How many latest turns to keep per chat")
    parser.add_argument("--poll-timeout", type=int, default=25, help="Telegram long polling timeout (seconds)")
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Sleep delay after each polling cycle")
    parser.add_argument("--once", action="store_true", help="Process available updates once and exit")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    config = load_app_config()
    options = RuntimeOptions(
        offset_file=Path(args.offset_file),
        thread_dir=Path(args.thread_dir),
        tool_backend=args.tool_backend,
        mcp_client_mode=args.mcp_client_mode,
        mcp_server_module=args.mcp_server_module,
        mcp_server_url=args.mcp_server_url,
        max_turns=args.max_turns,
        poll_timeout=args.poll_timeout,
        sleep_seconds=args.sleep_seconds,
        once=args.once,
    )

    bot = TrafficTelegramBot(config=config, options=options)
    bot.run()


if __name__ == "__main__":
    main()
