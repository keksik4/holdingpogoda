from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.weather_models import NormalizedWeatherRecord, WeatherConsensusRecord
from backend.services.weather_common import (
    model_to_dict,
    numeric_consensus,
    relative_disagreement,
    utcnow,
)
from backend.services.weather_cache import read_cache, write_cache
from backend.services.weather_normalization import NORMALIZED_FIELDS, robust_average
from backend.services.weather_provider_registry import fetch_weather_inputs, provider_catalog
from backend.services.venue_profiles import get_venue_profile
from backend.services.app_context import warsaw_now
from backend.services.weather_interpretation import interpret_weather


NUMERIC_FIELDS = [
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
]


DISAGREEMENT_SCALES = {
    "temperature": 8.0,
    "apparent_temperature": 8.0,
    "precipitation": 8.0,
    "rain": 8.0,
    "snowfall": 4.0,
    "cloud_cover": 100.0,
    "humidity": 100.0,
    "wind_speed": 18.0,
    "wind_gusts": 24.0,
    "pressure": 35.0,
}


def calculate_weather_consensus(
    db: Session,
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
) -> dict[str, Any]:
    now = utcnow()
    start_datetime = start_datetime or datetime.combine(date.today(), time.min)
    end_datetime = end_datetime or (now + timedelta(days=16))
    rows = (
        db.query(NormalizedWeatherRecord)
        .filter(
            NormalizedWeatherRecord.target_datetime >= start_datetime,
            NormalizedWeatherRecord.target_datetime <= end_datetime,
        )
        .order_by(NormalizedWeatherRecord.target_datetime, NormalizedWeatherRecord.provider, NormalizedWeatherRecord.fetched_at.desc())
        .all()
    )
    if not rows:
        return {
            "status": "no_weather_records",
            "message": "Fetch at least one weather provider before calculating consensus.",
            "records": 0,
            "items": [],
        }
    latest_by_target_provider: dict[tuple[datetime, str], NormalizedWeatherRecord] = {}
    for row in rows:
        key = (row.target_datetime, row.provider)
        if key not in latest_by_target_provider:
            latest_by_target_provider[key] = row
    grouped: dict[datetime, list[NormalizedWeatherRecord]] = defaultdict(list)
    for row in latest_by_target_provider.values():
        grouped[row.target_datetime].append(row)
    created: list[WeatherConsensusRecord] = []
    for target_datetime, provider_rows in grouped.items():
        consensus_values = {}
        missing_fields: list[str] = []
        disagreement_parts: list[float] = []
        for field in NUMERIC_FIELDS:
            values = [getattr(row, field) for row in provider_rows]
            value, _ = numeric_consensus(values)
            consensus_values[field] = value
            if field in DISAGREEMENT_SCALES:
                disagreement_parts.append(relative_disagreement(values, DISAGREEMENT_SCALES[field]))
            if all(item is None for item in values):
                missing_fields.append(field)
        descriptions = [row.weather_description for row in provider_rows if row.weather_description]
        weather_description = Counter(descriptions).most_common(1)[0][0] if descriptions else None
        codes = [row.weather_code for row in provider_rows if row.weather_code]
        weather_code = Counter(codes).most_common(1)[0][0] if codes else None
        provider_count = len(provider_rows)
        provider_names = sorted({row.provider for row in provider_rows})
        field_completeness = 1 - (len(missing_fields) / max(len(NUMERIC_FIELDS), 1))
        provider_coverage = 1.0 if provider_count >= 3 else 0.85 if provider_count == 2 else 0.65
        disagreement = round(sum(disagreement_parts) / max(len(disagreement_parts), 1), 4)
        # Confidence deliberately falls when providers disagree, because operations teams need scenario planning then.
        confidence = round(max(0.05, min(0.98, provider_coverage * 0.45 + (1 - disagreement) * 0.45 + field_completeness * 0.10)), 4)
        existing = (
            db.query(WeatherConsensusRecord)
            .filter(WeatherConsensusRecord.target_datetime == target_datetime)
            .one_or_none()
        )
        payload = {
            "calculated_at": now,
            "target_datetime": target_datetime,
            "latitude": get_settings().default_latitude,
            "longitude": get_settings().default_longitude,
            **consensus_values,
            "weather_code": weather_code,
            "weather_description": weather_description,
            "provider_count": provider_count,
            "providers_used": ", ".join(provider_names),
            "missing_fields": ", ".join(missing_fields),
            "provider_disagreement_score": disagreement,
            "forecast_confidence_score": confidence,
        }
        if existing is None:
            existing = WeatherConsensusRecord(**payload)
            db.add(existing)
        else:
            for key, value in payload.items():
                setattr(existing, key, value)
        created.append(existing)
    db.commit()
    return {
        "status": "ok",
        "records": len(created),
        "items": [model_to_dict(row) for row in created[:72]],
    }


def get_weather_consensus(
    db: Session,
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
    limit: int = 240,
) -> list[dict[str, Any]]:
    query = db.query(WeatherConsensusRecord)
    if start_datetime:
        query = query.filter(WeatherConsensusRecord.target_datetime >= start_datetime)
    if end_datetime:
        query = query.filter(WeatherConsensusRecord.target_datetime <= end_datetime)
    rows = query.order_by(WeatherConsensusRecord.target_datetime).limit(limit).all()
    return [model_to_dict(row) for row in rows]


def weather_provider_comparison(db: Session, hours: int = 48) -> dict[str, Any]:
    start = datetime.combine(date.today(), time.min)
    end = start + timedelta(hours=hours)
    rows = (
        db.query(NormalizedWeatherRecord)
        .filter(NormalizedWeatherRecord.target_datetime >= start, NormalizedWeatherRecord.target_datetime <= end)
        .order_by(NormalizedWeatherRecord.target_datetime, NormalizedWeatherRecord.provider)
        .all()
    )
    grouped: dict[datetime, dict[str, Any]] = {}
    for row in rows:
        bucket = grouped.setdefault(row.target_datetime, {"target_datetime": row.target_datetime.isoformat(), "providers": {}})
        bucket["providers"][row.provider] = {
            "temperature": row.temperature,
            "precipitation": row.precipitation,
            "wind_speed": row.wind_speed,
            "cloud_cover": row.cloud_cover,
            "humidity": row.humidity,
            "weather_description": row.weather_description,
            "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
        }
    return {"hours": hours, "items": list(grouped.values())}


def venue_weather_consensus(
    venue_slug: str,
    target_date: date,
    force: bool = False,
    live_fetch: bool = True,
) -> dict[str, Any]:
    cached, metadata = read_cache("consensus", venue_slug, target_date, force=force)
    if cached is not None:
        today = warsaw_now().date()
        needs_two_sources = live_fetch and today <= target_date <= today + timedelta(days=30)
        if not needs_two_sources or int(cached.get("source_count", 0) or 0) >= 2:
            return cached | {"cache_metadata": metadata}
    venue = get_venue_profile(venue_slug)
    latitude = float(venue["latitude"])
    longitude = float(venue["longitude"])
    records, source_status = fetch_weather_inputs(latitude, longitude, target_date, live_fetch=live_fetch)
    consensus = _consensus_from_records(venue_slug, target_date, records, source_status)
    provider_failed = not any(status.get("status") == "ok" for status in source_status.values())
    return write_cache("consensus", venue_slug, target_date, consensus, provider_failed=provider_failed)


def venue_weather_consensus_range(venue_slug: str, start_date: date, end_date: date, force: bool = False) -> dict[str, Any]:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date.")
    items = []
    current = start_date
    today = warsaw_now().date()
    while current <= end_date:
        items.append(venue_weather_consensus(venue_slug, current, force=force, live_fetch=current == today))
        current += timedelta(days=1)
    return {
        "venue_slug": venue_slug,
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "items": items,
        "providers_available": provider_catalog(),
        "cache_summary": {
            "cache_hits": sum(1 for item in items if item.get("cache_metadata", {}).get("cache_hit")),
            "items": len(items),
        },
    }


def _consensus_from_records(
    venue_slug: str,
    target_date: date,
    records: list[dict[str, Any]],
    source_status: dict[str, Any],
) -> dict[str, Any]:
    providers_used = [record["provider"] for record in records if record["provider"] != "seasonal-calibration-proxy"]
    provider_names = [record["provider"] for record in records]
    numeric_values = {field: robust_average([record.get(field) for record in records]) for field in NORMALIZED_FIELDS}
    disagreement_parts = []
    for field in ["temperature", "precipitation", "cloud_cover", "humidity", "wind_speed", "wind_gusts"]:
        values = [record.get(field) for record in records if record.get(field) is not None]
        if len(values) >= 2:
            scale = {"temperature": 8, "precipitation": 8, "cloud_cover": 100, "humidity": 100, "wind_speed": 18, "wind_gusts": 24}[field]
            disagreement_parts.append(relative_disagreement(values, scale))
    disagreement = round(sum(disagreement_parts) / max(1, len(disagreement_parts)), 4)
    provider_coverage = min(1.0, len(providers_used) / 3) if providers_used else 0.38
    avg_provider_confidence = robust_average([record.get("provider_confidence") for record in records]) or 0.45
    confidence = round(max(0.05, min(0.98, provider_coverage * 0.42 + (1 - disagreement) * 0.33 + avg_provider_confidence * 0.25)), 4)
    source_count = len(providers_used)
    has_only_fallback = not providers_used
    incomplete_external_consensus = 0 < source_count < 2
    representative_code = _representative_weather_code(records)
    interpretation = interpret_weather(
        weather_code=representative_code,
        precipitation_probability=numeric_values["precipitation_probability"],
        precipitation=numeric_values["precipitation"],
        rain=numeric_values["rain"],
        snowfall=numeric_values["snowfall"],
        cloud_cover=numeric_values["cloud_cover"],
        temperature=numeric_values["temperature"],
        wind_speed=numeric_values["wind_speed"],
        source_count=source_count,
        confidence=confidence,
        is_fallback=has_only_fallback,
        provider_disagreement_score=disagreement,
    )
    if incomplete_external_consensus:
        confidence = min(confidence, 0.48)
        interpretation = interpretation | {
            "confidence": min(interpretation["confidence"], 0.48),
            "confidence_note": "Niska pewność: brak drugiego niezależnego źródła pogody dla tego dnia.",
            "explanation": f"{interpretation['explanation']} Brak drugiego źródła dla tego dnia, więc wynik jest oznaczony jako dane częściowe.",
        }
    fetched_times = [
        datetime.fromisoformat(record["fetched_at"])
        for record in records
        if record.get("fetched_at")
    ]
    newest_fetch = max(fetched_times) if fetched_times else utcnow()
    normalized_sources = _normalized_sources(records)
    condition_group = _condition_group(interpretation["icon_key"])
    return {
        "target_datetime": records[0]["target_datetime"] if records else datetime.combine(target_date, time(hour=12)).isoformat(),
        "date": target_date.isoformat(),
        "venue_slug": venue_slug,
        "providers_used": providers_used,
        "providerCount": source_count,
        "source_count": source_count,
        "has_weather_consensus": source_count >= 2,
        "is_weather_fallback": has_only_fallback,
        "weather_data_status": "pełny konsensus" if source_count >= 2 else "dane częściowe" if source_count == 1 else "brak zewnętrznych źródeł",
        "providers_available": provider_catalog(),
        "temperature_avg": numeric_values["temperature"],
        "temperatureC": numeric_values["temperature"],
        "apparent_temperature_avg": numeric_values["apparent_temperature"],
        "apparentTemperatureC": numeric_values["apparent_temperature"],
        "precipitation_avg": numeric_values["precipitation"],
        "precipitationMm": numeric_values["precipitation"],
        "precipitation_probability_avg": numeric_values["precipitation_probability"],
        "precipitationProbability": numeric_values["precipitation_probability"],
        "cloud_cover_avg": numeric_values["cloud_cover"],
        "cloudCover": numeric_values["cloud_cover"],
        "humidity_avg": numeric_values["humidity"],
        "wind_speed_avg": numeric_values["wind_speed"],
        "windSpeedKmh": numeric_values["wind_speed"],
        "wind_gusts_avg": numeric_values["wind_gusts"],
        "uv_index_avg": numeric_values["uv_index"],
        "conditionGroup": condition_group,
        "weather_icon_consensus": interpretation["icon_key"],
        "weather_description_consensus": interpretation["label_pl"],
        "weather_icon_key": interpretation["icon_key"],
        "weather_label_pl": interpretation["label_pl"],
        "weather_risk_level": interpretation["risk_level"],
        "weather_explanation": interpretation["explanation"],
        "weather_confidence_note": interpretation["confidence_note"],
        "provider_disagreement_score": disagreement,
        "disagreementScore": disagreement,
        "confidencePenalty": round(min(0.45, disagreement * 0.45 + (0.20 if source_count < 2 else 0)), 4),
        "forecast_confidence_score": min(confidence, interpretation["confidence"]),
        "data_freshness_minutes": round((utcnow() - newest_fetch.replace(tzinfo=None)).total_seconds() / 60, 1),
        "source_status": source_status,
        "sources": normalized_sources,
        "normalized_inputs": records,
    }


def _representative_weather_code(records: list[dict[str, Any]]) -> str | int | None:
    codes = [record.get("weather_code") for record in records if record.get("weather_code") is not None]
    if not codes:
        return None
    counter = Counter(str(code) for code in codes)
    return counter.most_common(1)[0][0]


def _normalized_sources(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for record in records:
        key = _provider_key(record.get("provider"))
        if key in {"seasonal-calibration-proxy", ""}:
            continue
        sources[key] = {
            "datetime": record.get("target_datetime"),
            "source": key,
            "temperatureC": record.get("temperature"),
            "apparentTemperatureC": record.get("apparent_temperature"),
            "precipitationMm": record.get("precipitation"),
            "precipitationProbability": record.get("precipitation_probability"),
            "cloudCover": record.get("cloud_cover"),
            "windSpeedKmh": record.get("wind_speed"),
            "weatherCode": record.get("weather_code"),
            "conditionLabel": record.get("weather_description"),
        }
    return sources


def _provider_key(provider: str | None) -> str:
    value = provider or ""
    if "openweather" in value:
        return "openweather"
    if "open-meteo" in value or "openmeteo" in value:
        return "openmeteo"
    if "meteosource" in value:
        return "meteosource"
    if "met-no" in value:
        return "met-no"
    if "imgw" in value:
        return "imgw"
    if "seasonal-calibration" in value:
        return "seasonal-calibration-proxy"
    return value


def _condition_group(icon_key: str) -> str:
    return {
        "sun": "sunny",
        "partly_cloudy": "mixed",
        "cloud": "cloudy",
        "rain": "rain",
        "storm": "storm",
        "snow": "snow",
        "fog": "fog",
        "wind": "mixed",
        "unknown": "unknown",
    }.get(icon_key, "unknown")
