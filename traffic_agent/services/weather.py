from __future__ import annotations

from datetime import datetime

import requests


class WeatherService:
    def weather_text(self, lat: float, lon: float, num_hours: int = 2) -> str:
        if num_hours < 1:
            num_hours = 1

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,precipitation_probability,precipitation",
            "current_weather": "true",
            "timezone": "Asia/Ho_Chi_Minh",
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        current = data["current_weather"]
        current_time = datetime.fromisoformat(current["time"])
        times = data["hourly"]["time"]
        temps = data["hourly"]["temperature_2m"]
        rain_probs = data["hourly"]["precipitation_probability"]

        start_idx = 0
        for idx, timestamp in enumerate(times):
            if datetime.fromisoformat(timestamp) >= current_time:
                start_idx = idx
                break

        end_idx = min(start_idx + num_hours, len(times))
        next_slots = []
        for idx in range(start_idx, end_idx):
            rain_prob = float(rain_probs[idx]) / 100.0
            next_slots.append(f"- {times[idx]} | {temps[idx]}C | rain_prob={rain_prob:.0%}")
            print(f"- {times[idx]} | {temps[idx]}C | rain_prob={rain_prob:.0%}")

        max_prob = max((float(rain_probs[idx]) for idx in range(start_idx, end_idx)), default=0.0)
        rain_advice = "NEN mang ao mua." if max_prob >= 40 else "Khong can ao mua."

        lines = [
            f"Current weather: temp={current.get('temperature')}C, wind={current.get('windspeed')} km/h",
            f"Next {num_hours}h forecast:",
            *next_slots,
            f"Advice: {rain_advice}",
        ]
        return "\n".join(lines)
