from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any

from backend.services.weather_interpretation import interpret_weather


NORMALIZED_FIELDS = [
    "temperature",
    "apparent_temperature",
    "precipitation",
    "precipitation_probability",
    "rain",
    "snowfall",
    "cloud_cover",
    "humidity",
    "wind_speed",
    "wind_gusts",
    "pressure",
    "uv_index",
]


def number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def normalized_weather_record(
    *,
    target_datetime: datetime,
    provider: str,
    fetched_at: datetime,
    provider_confidence: float,
    weather_description: str | None = None,
    weather_code: str | int | None = None,
    **values: Any,
) -> dict[str, Any]:
    description = weather_description or description_from_code(weather_code, values)
    return {
        "target_datetime": target_datetime.isoformat(),
        "provider": provider,
        "temperature": number(values.get("temperature")),
        "apparent_temperature": number(values.get("apparent_temperature")),
        "precipitation": number(values.get("precipitation")),
        "precipitation_probability": number(values.get("precipitation_probability")),
        "rain": number(values.get("rain")),
        "snowfall": number(values.get("snowfall")),
        "cloud_cover": number(values.get("cloud_cover")),
        "humidity": number(values.get("humidity")),
        "wind_speed": number(values.get("wind_speed")),
        "wind_gusts": number(values.get("wind_gusts")),
        "pressure": number(values.get("pressure")),
        "uv_index": number(values.get("uv_index")),
        "weather_code": None if weather_code is None else str(weather_code),
        "weather_description": description,
        "weather_icon": weather_icon_from_values(description, values | {"weather_code": weather_code}),
        "provider_confidence": provider_confidence,
        "fetched_at": fetched_at.isoformat(),
    }


def robust_average(values: list[float | None]) -> float | None:
    cleaned = sorted(float(value) for value in values if value is not None)
    if not cleaned:
        return None
    if len(cleaned) <= 2:
        return round(median(cleaned), 2)
    trimmed = cleaned[1:-1] or cleaned
    return round(sum(trimmed) / len(trimmed), 2)


def weather_icon_from_values(description: str | None, values: dict[str, Any]) -> str:
    interpretation = interpret_weather(
        weather_code=values.get("weather_code"),
        precipitation_probability=number(values.get("precipitation_probability")),
        precipitation=number(values.get("precipitation")),
        rain=number(values.get("rain")),
        snowfall=number(values.get("snowfall")),
        cloud_cover=number(values.get("cloud_cover")),
        temperature=number(values.get("temperature")),
        wind_speed=number(values.get("wind_speed")),
        source_count=1,
        confidence=0.6,
        is_fallback=False,
    )
    if interpretation["icon_key"] != "unknown":
        return interpretation["icon_key"]
    text = (description or "").lower()
    if "cloud" in text or "overcast" in text:
        return "cloud"
    if "partly" in text or "mixed" in text:
        return "partly_cloudy"
    return "unknown"


def description_from_code(code: str | int | None, values: dict[str, Any]) -> str:
    if code is None:
        icon = weather_icon_from_values(None, values)
        return {
            "storm": "Storm risk",
            "snow": "Snow",
            "rain": "Rain",
            "cloud": "Cloudy",
            "partly_cloudy": "Partly cloudy",
            "sun": "Clear",
        }[icon]
    try:
        numeric_code = int(float(str(code)))
    except ValueError:
        return str(code).replace("_", " ").title()
    if 200 <= numeric_code <= 299:
        return "Thunderstorm"
    if 300 <= numeric_code <= 599:
        return "Rain"
    if 600 <= numeric_code <= 699:
        return "Snow"
    if 700 <= numeric_code <= 799:
        return "Fog or low visibility"
    if numeric_code == 800:
        return "Clear"
    if numeric_code in {801, 802}:
        return "Partly cloudy"
    if numeric_code in {803, 804}:
        return "Cloudy"
    if numeric_code in {95, 96, 99}:
        return "Thunderstorm"
    if numeric_code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
        return "Rain"
    if numeric_code in {71, 73, 75, 77, 85, 86}:
        return "Snow"
    if numeric_code in {3, 45, 48}:
        return "Cloudy"
    if numeric_code in {1, 2}:
        return "Partly cloudy"
    if numeric_code == 0:
        return "Clear"
    return "Mixed conditions"


def consensus_icon(records: list[dict[str, Any]]) -> tuple[str, str]:
    priority = {"storm": 5, "snow": 4, "rain": 3, "wind": 2, "fog": 2, "cloud": 1, "partly_cloudy": 1, "sun": 0, "unknown": -1}
    icons = [record.get("weather_icon") or "unknown" for record in records]
    chosen = max(icons, key=lambda icon: priority.get(icon, 0)) if icons else "unknown"
    return chosen, {
        "storm": "Storm or severe rain risk",
        "snow": "Snow",
        "rain": "Rain likely",
        "wind": "Windy",
        "fog": "Fog",
        "cloud": "Cloudy",
        "partly_cloudy": "Mixed or partly cloudy",
        "sun": "Clear or sunny",
        "unknown": "Weather data unavailable",
    }[chosen]
