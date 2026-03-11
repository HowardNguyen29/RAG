from __future__ import annotations

from typing import Any

import requests


def traffic_level(travel_time_min: float, delay_min: float) -> tuple[str, float]:
    if travel_time_min <= 0:
        return ("thong thoang", 0.0)
    delay_ratio = max(delay_min / travel_time_min, 0.0)
    if delay_ratio < 0.1:
        return ("thong thoang", delay_ratio)
    if delay_ratio < 0.3:
        return ("hoi dong", delay_ratio)
    return ("ket cung", delay_ratio)


def extract_instructions(route: dict[str, Any]) -> list[str]:
    guidance = route.get("guidance", {})
    instructions: list[str] = []

    for group in guidance.get("instructionGroups", []):
        for inst in group.get("instructions", []):
            msg = inst.get("message", "").strip()
            if not msg:
                continue
            street = inst.get("street", "").strip()
            roads = inst.get("roadNumbers", [])
            parts = [msg]
            if street:
                parts.append(f"vao {street}")
            if roads:
                parts.append(f"({', '.join(roads)})")
            instructions.append(" ".join(parts))

    if not instructions:
        for inst in guidance.get("instructions", []):
            msg = (inst.get("message", "") or inst.get("text", "")).strip()
            if msg:
                instructions.append(msg)

    if not instructions:
        summary = route.get("summary", {})
        distance_km = round(summary.get("lengthInMeters", 0) / 1000, 1)
        travel_min = round(summary.get("travelTimeInSeconds", 0) / 60, 1)
        instructions = [
            "Di theo tuyen GPS den diem dich.",
            f"Quang duong: {distance_km} km.",
            f"Thoi gian uoc tinh: {travel_min} phut.",
        ]

    return instructions[:25]


class RoutingService:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get_routes(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        max_alternatives: int = 5,
    ) -> list[dict[str, Any]]:
        url = (
            "https://api.tomtom.com/routing/1/calculateRoute/"
            f"{origin_lat},{origin_lon}:{dest_lat},{dest_lon}/json"
        )
        params = {
            "key": self.api_key,
            "routeType": "fastest",
            "traffic": "true",
            "maxAlternatives": max_alternatives,
            "instructionsType": "tagged",
            "language": "vi-VN",
            "routeRepresentation": "polyline",
            "sectionType": "traffic",
        }
        response = requests.get(url, params=params, timeout=40)
        response.raise_for_status()
        routes = response.json().get("routes", [])
        if not routes:
            raise RuntimeError("TomTom did not return any route")
        return routes

    def best_route_text(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> str:
        routes = self.get_routes(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
        )
        ranked: list[dict[str, Any]] = []
        for idx, route in enumerate(routes, start=1):
            summary = route.get("summary", {})
            travel_min = summary.get("travelTimeInSeconds", 0) / 60
            delay_min = summary.get("trafficDelayInSeconds", 0) / 60
            level, delay_ratio = traffic_level(travel_min, delay_min)
            ranked.append(
                {
                    "route_idx": idx,
                    "travel_min": round(travel_min, 1),
                    "delay_min": round(delay_min, 1),
                    "distance_km": round(summary.get("lengthInMeters", 0) / 1000, 1),
                    "level": level,
                    "delay_ratio": round(delay_ratio, 2),
                    "instructions": extract_instructions(route),
                }
            )

        score = {"thong thoang": 0, "hoi dong": 1, "ket cung": 2}
        ranked.sort(
            key=lambda item: (
                score.get(item["level"], 99),
                item["delay_ratio"],
                item["travel_min"],
            )
        )

        best = ranked[0]
        lines = [
            f"Tinh trang: {best['level']}",
            f"Thoi gian: {best['travel_min']} phut (tre {best['delay_min']} phut)",
            f"Quang duong: {best['distance_km']} km",
            f"So tuyen da kiem tra: {len(ranked)}",
            "",
            f"Huong dan ({len(best['instructions'])} buoc):",
        ]
        lines.extend(f"{i}. {inst}" for i, inst in enumerate(best["instructions"], start=1))
        return "\n".join(lines)

    def geocode(self, address: str) -> str:
        url = f"https://api.tomtom.com/search/2/geocode/{address}.json"
        response = requests.get(url, params={"key": self.api_key}, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            raise RuntimeError("Khong tim thay toa do cho dia chi nay")
        lat = results[0]["position"]["lat"]
        lon = results[0]["position"]["lon"]
        return f"{lat}, {lon}"
