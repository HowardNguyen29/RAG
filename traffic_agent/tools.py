from __future__ import annotations

from typing import Any

from langchain.tools import tool

from traffic_agent.config import AppConfig
from traffic_agent.services.routing import RoutingService
from traffic_agent.services.weather import WeatherService


def build_tools(
    config: AppConfig,
    routing: RoutingService,
    weather: WeatherService,
) -> list[Any]:
    @tool
    def best_route(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> str:
        """Find least-congested route between two coordinates and return detailed guidance."""
        return routing.best_route_text(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
        )

    @tool
    def get_weather(lat: float, lon: float, num_hours: int = 2) -> str:
        """Get current weather and next n-hour rain outlook for a coordinate."""
        return weather.weather_text(lat=lat, lon=lon, num_hours=num_hours)

    @tool
    def get_lat_lon(address: str) -> str:
        """Get coordinate lat,lon from an address string via TomTom geocoding."""
        return routing.geocode(address)

    @tool
    def home_to_work() -> str:
        """Get route from HOME_* to WORK_* coordinates and include rain-jacket advice."""
        if None in (config.home_lat, config.home_lon, config.work_lat, config.work_lon):
            return "HOME_LAT/HOME_LON/WORK_LAT/WORK_LON are not fully configured."

        route_text = routing.best_route_text(
            origin_lat=config.home_lat,
            origin_lon=config.home_lon,
            dest_lat=config.work_lat,
            dest_lon=config.work_lon,
        )
        weather_text = weather.weather_text(lat=config.work_lat, lon=config.work_lon, num_hours=2)
        return f"{route_text}\n\n{weather_text}"

    return [best_route, get_weather, home_to_work, get_lat_lon]
