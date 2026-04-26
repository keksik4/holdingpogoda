import json
from datetime import datetime
from pathlib import Path
from statistics import median, pstdev
from typing import Any

from sqlalchemy.orm import Session

from backend.config import PROJECT_ROOT, get_settings
from backend.models.weather_models import (
    NormalizedWeatherRecord,
    RawWeatherPayload,
    WeatherProviderStatus,
)


WEATHER_FIELDS = [
    "temperature",
    "apparent_temperature",
    "precipitation",
    "rain",
    "snowfall",
    "cloud_cover",
    "humidity",
    "wind_speed",
    "wind_gusts",
    "pressure",
    "uv_index",
    "sunshine_duration",
    "weather_code",
    "weather_description",
]


EXPECTED_WEATHER_PROVIDERS = [
    {
        "provider": "open-meteo-forecast",
        "display_name": "Open-Meteo Forecast API",
        "role": "Current and future forecast coverage.",
        "url": "https://open-meteo.com/en/docs",
    },
    {
        "provider": "open-meteo-history",
        "display_name": "Open-Meteo Historical Weather API",
        "role": "Historical actual weather.",
        "url": "https://open-meteo.com/en/docs/historical-weather-api",
    },
    {
        "provider": "open-meteo-historical-forecast",
        "display_name": "Open-Meteo Historical Forecast API",
        "role": "Archived forecasts for decision-time weather context.",
        "url": "https://open-meteo.com/en/docs/historical-forecast-api",
    },
    {
        "provider": "met-no-locationforecast",
        "display_name": "MET Norway Locationforecast API",
        "role": "Independent forecast comparison provider.",
        "url": "https://api.met.no/weatherapi/locationforecast/2.0/documentation",
    },
    {
        "provider": "imgw-synop",
        "display_name": "IMGW public synoptic data",
        "role": "Official Polish local observation reference where available.",
        "url": "https://danepubliczne.imgw.pl/pl/apiinfo",
    },
]


WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def weather_description_from_code(code: Any) -> str | None:
    if code is None or code == "":
        return None
    try:
        return WMO_WEATHER_CODES.get(int(float(code)), f"Weather code {code}")
    except (TypeError, ValueError):
        return str(code).replace("_", " ").title()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def save_raw_weather_payload(
    db: Session,
    provider: str,
    endpoint: str,
    payload: Any,
    status_code: int | None = None,
    request_url: str | None = None,
    error_message: str | None = None,
) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    safe_endpoint = endpoint.replace("/", "_").replace(":", "_").replace("?", "_")
    path = PROJECT_ROOT / "data" / "raw" / "weather" / f"{provider}_{safe_endpoint}_{timestamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "provider": provider,
                "endpoint": endpoint,
                "fetched_at": utcnow().isoformat(),
                "status_code": status_code,
                "request_url": request_url,
                "error_message": error_message,
                "payload": payload,
            },
            handle,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    db.add(
        RawWeatherPayload(
            provider=provider,
            endpoint=endpoint,
            status_code=status_code,
            raw_payload_path=str(path),
            request_url=request_url,
            error_message=error_message,
        )
    )
    db.commit()
    return str(path)


def missing_fields(record: dict[str, Any]) -> list[str]:
    return [
        field
        for field in WEATHER_FIELDS
        if record.get(field) is None and field not in {"uv_index", "sunshine_duration"}
    ]


def update_provider_status(
    db: Session,
    provider: str,
    is_available: bool,
    records_last_fetch: int = 0,
    missing: list[str] | None = None,
    error_message: str | None = None,
) -> WeatherProviderStatus:
    status = db.query(WeatherProviderStatus).filter(WeatherProviderStatus.provider == provider).one_or_none()
    now = utcnow()
    if status is None:
        status = WeatherProviderStatus(provider=provider)
        db.add(status)
    status.is_available = is_available
    status.last_attempt_at = now
    status.records_last_fetch = records_last_fetch
    status.missing_fields = ", ".join(sorted(set(missing or [])))
    status.last_error = error_message
    if is_available:
        status.last_successful_fetch = now
    db.commit()
    db.refresh(status)
    return status


def upsert_normalized_weather(db: Session, records: list[dict[str, Any]]) -> int:
    count = 0
    for item in records:
        existing = (
            db.query(NormalizedWeatherRecord)
            .filter(
                NormalizedWeatherRecord.provider == item["provider"],
                NormalizedWeatherRecord.target_datetime == item["target_datetime"],
                NormalizedWeatherRecord.forecast_generated_at == item.get("forecast_generated_at"),
            )
            .one_or_none()
        )
        if existing is None:
            existing = NormalizedWeatherRecord(**item)
            db.add(existing)
        else:
            for key, value in item.items():
                setattr(existing, key, value)
        count += 1
    db.commit()
    return count


def model_to_dict(model: Any) -> dict[str, Any]:
    data = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, (datetime,)):
            data[column.name] = value.isoformat()
        else:
            data[column.name] = value
    return data


def provider_status_payload(db: Session) -> list[dict[str, Any]]:
    rows = {row.provider: model_to_dict(row) for row in db.query(WeatherProviderStatus).all()}
    settings = get_settings()
    payload: list[dict[str, Any]] = []
    for provider in EXPECTED_WEATHER_PROVIDERS:
        row = rows.get(provider["provider"])
        if row is None:
            row = {
                "provider": provider["provider"],
                "is_available": False,
                "last_successful_fetch": None,
                "last_attempt_at": None,
                "last_error": None,
                "missing_fields": "",
                "records_last_fetch": 0,
                "status": "not_attempted",
            }
        else:
            row["status"] = "ok" if row["is_available"] else "error"
        row |= {
            "display_name": provider["display_name"],
            "role": provider["role"],
            "url": provider["url"],
        }
        if provider["provider"] == "met-no-locationforecast":
            row["user_agent_configured"] = bool(settings.met_no_user_agent)
            row["configuration_hint"] = "Set MET_NO_USER_AGENT in .env to a descriptive contact string."
        payload.append(row)
    return payload


def numeric_consensus(values: list[float | None]) -> tuple[float | None, float]:
    cleaned = [float(value) for value in values if value is not None]
    if not cleaned:
        return None, 0.0
    if len(cleaned) == 1:
        return cleaned[0], 0.0
    return median(cleaned), pstdev(cleaned)


def relative_disagreement(values: list[float | None], scale: float) -> float:
    cleaned = [float(value) for value in values if value is not None]
    if len(cleaned) < 2:
        return 0.0
    _, spread = numeric_consensus(cleaned)
    return min(1.0, spread / max(scale, 1.0))


def default_location() -> tuple[float, float, str]:
    settings = get_settings()
    return settings.default_latitude, settings.default_longitude, settings.default_timezone


def relative_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(Path(path).resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)
