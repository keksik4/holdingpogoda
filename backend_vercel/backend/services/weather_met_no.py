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
)


def _symbol_description(symbol: str | None) -> str | None:
    if not symbol:
        return None
    return symbol.replace("_", " ").replace("day", "").replace("night", "").strip().title()


def fetch_met_no_forecast(
    db: Session,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    default_latitude, default_longitude, _ = default_location()
    latitude = latitude or default_latitude
    longitude = longitude or default_longitude
    url = "https://api.met.no/weatherapi/locationforecast/2.0/complete"
    params = {"lat": latitude, "lon": longitude}
    provider = "met-no-locationforecast"
    try:
        with httpx.Client(timeout=settings.api_timeout_seconds) as client:
            response = client.get(url, params=params, headers={"User-Agent": settings.met_no_user_agent})
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
        records = _normalize(payload, raw_path, latitude, longitude)
        count = upsert_normalized_weather(db, records)
        missing = [field for record in records[:24] for field in missing_fields(record)]
        update_provider_status(db, provider, True, count, missing)
        return {"provider": provider, "status": "ok", "records": count, "raw_payload_path": raw_path, "sample": records[:3]}
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


def _normalize(payload: dict[str, Any], raw_path: str, latitude: float, longitude: float) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    fetched_at = utcnow()
    forecast_generated_at = parse_datetime(payload.get("properties", {}).get("meta", {}).get("updated_at")) or fetched_at
    for item in payload.get("properties", {}).get("timeseries", []):
        target_datetime = parse_datetime(item.get("time"))
        details = item.get("data", {}).get("instant", {}).get("details", {})
        next_1h = item.get("data", {}).get("next_1_hours", {})
        next_6h = item.get("data", {}).get("next_6_hours", {})
        precipitation = (
            _number(next_1h.get("details", {}).get("precipitation_amount"))
            if next_1h
            else _number(next_6h.get("details", {}).get("precipitation_amount"))
        )
        symbol = next_1h.get("summary", {}).get("symbol_code") or next_6h.get("summary", {}).get("symbol_code")
        if target_datetime is None:
            continue
        records.append(
            {
                "provider": "met-no-locationforecast",
                "fetched_at": fetched_at,
                "forecast_generated_at": forecast_generated_at,
                "target_datetime": target_datetime,
                "latitude": latitude,
                "longitude": longitude,
                "temperature": _number(details.get("air_temperature")),
                "apparent_temperature": None,
                "precipitation": precipitation,
                "rain": precipitation,
                "snowfall": None,
                "cloud_cover": _number(details.get("cloud_area_fraction")),
                "humidity": _number(details.get("relative_humidity")),
                "wind_speed": _number(details.get("wind_speed")),
                "wind_gusts": _number(details.get("wind_speed_of_gust")),
                "pressure": _number(details.get("air_pressure_at_sea_level")),
                "uv_index": None,
                "sunshine_duration": None,
                "weather_code": symbol,
                "weather_description": _symbol_description(symbol),
                "raw_payload_path": raw_path,
            }
        )
    return records


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
