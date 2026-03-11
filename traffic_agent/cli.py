from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

# Allow `python traffic_agent/cli.py` from repository root.
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from traffic_agent.bot import RuntimeOptions, TrafficTelegramBot
from traffic_agent.config import load_app_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Telegram traffic/weather agent bot")
    parser.add_argument("--offset-file", default=".telegram/offset.json", help="Path to store update offset")
    parser.add_argument("--thread-dir", default=".telegram/threads", help="Directory to store chat thread memory")
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
        max_turns=args.max_turns,
        poll_timeout=args.poll_timeout,
        sleep_seconds=args.sleep_seconds,
        once=args.once,
    )

    bot = TrafficTelegramBot(config=config, options=options)
    bot.run()


if __name__ == "__main__":
    main()
