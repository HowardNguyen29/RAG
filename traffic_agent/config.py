from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    bot_token: str
    tomtom_api_key: str
    openai_api_key: str
    openai_model: str
    home_lat: float | None
    home_lon: float | None
    work_lat: float | None
    work_lon: float | None


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


def bootstrap_env(repo_root: Path | None = None) -> None:
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[1]

    candidates = [Path.cwd() / ".env", repo_root / ".env"]
    seen: set[str] = set()
    for path in candidates:
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        _load_dotenv_file(path)


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _optional_float_env(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid float for {name}: {value!r}") from exc


def load_app_config(repo_root: Path | None = None) -> AppConfig:
    bootstrap_env(repo_root=repo_root)
    return AppConfig(
        bot_token=_required_env("BOT_TOKEN"),
        tomtom_api_key=_required_env("TOMTOM_API_KEY"),
        openai_api_key=_required_env("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        home_lat=_optional_float_env("HOME_LAT"),
        home_lon=_optional_float_env("HOME_LON"),
        work_lat=_optional_float_env("WORK_LAT"),
        work_lon=_optional_float_env("WORK_LON"),
    )
