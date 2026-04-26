from datetime import date
from typing import Any

import httpx
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.services.weather_common import (
    default_location,
    missing_fields,
    parse_datetime,
    save_raw_weather_payload,
    update_provider_status,
    upsert_normalized_weather,
    utcnow,
    weather_description_from_code,
)


OPEN_METEO_HOURLY_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "snowfall",
    "cloud_cover",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_gusts_10m",
    "pressure_msl",
    "weather_code",
    "uv_index",
    "sunshine_duration",
]


def _base_params(latitude: float, longitude: float, timezone: str) -> dict[str, Any]:
    return {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "hourly": ",".join(OPEN_METEO_HOURLY_FIELDS),
    }


def _normalize_hourly_payload(
    payload: dict[str, Any],
    provider: str,
    raw_payload_path: str,
    forecast_generated_at=None,
) -> list[dict[str, Any]]:
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    latitude = float(payload.get("latitude", 0))
    longitude = float(payload.get("longitude", 0))
    fetched_at = utcnow()
    records: list[dict[str, Any]] = []
    for idx, time_value in enumerate(times):
        target_datetime = parse_datetime(time_value)
        if target_datetime is None:
            continue
        weather_code = _value(hourly, "weather_code", idx)
        record = {
            "provider": provider,
            "fetched_at": fetched_at,
            "forecast_generated_at": forecast_generated_at,
            "target_datetime": target_datetime,
            "latitude": latitude,
            "longitude": longitude,
            "temperature": _value(hourly, "temperature_2m", idx),
            "apparent_temperature": _value(hourly, "apparent_temperature", idx),
            "precipitation": _value(hourly, "precipitation", idx),
            "rain": _value(hourly, "rain", idx),
            "snowfall": _value(hourly, "snowfall", idx),
            "cloud_cover": _value(hourly, "cloud_cover", idx),
            "humidity": _value(hourly, "relative_humidity_2m", idx),
            "wind_speed": _value(hourly, "wind_speed_10m", idx),
            "wind_gusts": _value(hourly, "wind_gusts_10m", idx),
            "pressure": _value(hourly, "pressure_msl", idx),
            "uv_index": _value(hourly, "uv_index", idx),
            "sunshine_duration": _value(hourly, "sunshine_duration", idx),
            "weather_code": None if weather_code is None else str(weather_code),
            "weather_description": weather_description_from_code(weather_code),
            "raw_payload_path": raw_payload_path,
        }
        records.append(record)
    return records


def _value(hourly: dict[str, list[Any]], field: str, idx: int) -> float | None:
    values = hourly.get(field)
    if values is None or idx >= len(values) or values[idx] is None:
        return None
    try:
        return float(values[idx])
    except (TypeError, ValueError):
        return None


def fetch_open_meteo_forecast(
    db: Session,
    latitude: float | None = None,
    longitude: float | None = None,
    days: int = 7,
) -> dict[str, Any]:
    settings = get_settings()
    default_latitude, default_longitude, timezone = default_location()
    latitude = latitude or default_latitude
    longitude = longitude or default_longitude
    url = "https://api.open-meteo.com/v1/forecast"
    params = _base_params(latitude, longitude, timezone) | {"forecast_days": max(1, min(days, 16))}
    return _fetch_and_store(db, "open-meteo-forecast", url, params)


def fetch_open_meteo_history(
    db: Session,
    start_date: date,
    end_date: date,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    default_latitude, default_longitude, timezone = default_location()
    latitude = latitude or default_latitude
    longitude = longitude or default_longitude
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = _base_params(latitude, longitude, timezone) | {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    return _fetch_and_store(db, "open-meteo-history", url, params)


def fetch_open_meteo_historical_forecast(
    db: Session,
    start_date: date,
    end_date: date,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    default_latitude, default_longitude, timezone = default_location()
    latitude = latitude or default_latitude
    longitude = longitude or default_longitude
    url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    params = _base_params(latitude, longitude, timezone) | {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    return _fetch_and_store(db, "open-meteo-historical-forecast", url, params)


def _fetch_and_store(db: Session, provider: str, url: str, params: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    try:
        with httpx.Client(timeout=settings.api_timeout_seconds) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        raw_path = save_raw_weather_payload(
            db,
            provider=provider,
            endpoint=url,
            payload=payload,
            status_code=response.status_code,
            request_url=str(response.url),
        )
        forecast_generated_at = utcnow() if provider != "open-meteo-history" else None
        normalized = _normalize_hourly_payload(payload, provider, raw_path, forecast_generated_at)
        count = upsert_normalized_weather(db, normalized)
        missing = [field for record in normalized[:24] for field in missing_fields(record)]
        update_provider_status(db, provider, True, count, missing)
        return {
            "provider": provider,
            "status": "ok",
            "records": count,
            "raw_payload_path": raw_path,
            "sample": normalized[:3],
        }
    except Exception as exc:  # noqa: BLE001
        raw_path = save_raw_weather_payload(
            db,
            provider=provider,
            endpoint=url,
            payload={"params": params},
            request_url=url,
            error_message=str(exc),
        )
        update_provider_status(db, provider, False, 0, [], str(exc))
        return {"provider": provider, "status": "error", "error": str(exc), "raw_payload_path": raw_path}
