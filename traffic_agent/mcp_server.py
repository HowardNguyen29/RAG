from __future__ import annotations

import argparse
import inspect
import os
from pathlib import Path
from typing import Sequence

from mcp.server.fastmcp import FastMCP

from traffic_agent.config import bootstrap_env
from traffic_agent.services.routing import RoutingService
from traffic_agent.services.weather import WeatherService


mcp = FastMCP("traffic-agent")


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _optional_float_env(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return float(value)


def _routing_service() -> RoutingService:
    return RoutingService(api_key=_required_env("TOMTOM_API_KEY"))


def _weather_service() -> WeatherService:
    return WeatherService()


@mcp.tool()
def best_route(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> str:
    """Find least-congested route between two coordinates and return detailed guidance."""
    routing = _routing_service()
    return routing.best_route_text(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
    )


@mcp.tool()
def get_weather(lat: float, lon: float, num_hours: int = 2) -> str:
    """Get current weather and next n-hour rain outlook for a coordinate."""
    weather = _weather_service()
    return weather.weather_text(lat=lat, lon=lon, num_hours=num_hours)


@mcp.tool()
def get_lat_lon(address: str) -> str:
    """Get coordinate lat,lon from an address string via TomTom geocoding."""
    routing = _routing_service()
    return routing.geocode(address)


@mcp.tool()
def home_to_work() -> str:
    """Get route from HOME_* to WORK_* coordinates and include rain-jacket advice."""
    home_lat = _optional_float_env("HOME_LAT")
    home_lon = _optional_float_env("HOME_LON")
    work_lat = _optional_float_env("WORK_LAT")
    work_lon = _optional_float_env("WORK_LON")
    if None in (home_lat, home_lon, work_lat, work_lon):
        return "HOME_LAT/HOME_LON/WORK_LAT/WORK_LON are not fully configured."

    routing = _routing_service()
    weather = _weather_service()
    route_text = routing.best_route_text(
        origin_lat=home_lat,
        origin_lon=home_lon,
        dest_lat=work_lat,
        dest_lon=work_lon,
    )
    weather_text = weather.weather_text(lat=work_lat, lon=work_lon, num_hours=2)
    return f"{route_text}\n\n{weather_text}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Traffic MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP transport. Use 'sse' to reuse one running server across clients.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host when transport is sse")
    parser.add_argument("--port", type=int, default=8765, help="Bind port when transport is sse")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    bootstrap_env(Path(__file__).resolve().parents[1])
    args = build_parser().parse_args(argv)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    # SSE mode lets many clients connect to one always-on MCP server.
    run_signature = inspect.signature(mcp.run)
    supports_host = "host" in run_signature.parameters
    supports_port = "port" in run_signature.parameters

    if supports_host or supports_port:
        kwargs: dict[str, object] = {"transport": "sse"}
        if supports_host:
            kwargs["host"] = args.host
        if supports_port:
            kwargs["port"] = args.port
        mcp.run(**kwargs)
        return

    # Backward-compatible fallback for older MCP versions that do not expose host/port.
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
