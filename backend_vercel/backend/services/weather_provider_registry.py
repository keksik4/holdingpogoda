from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo
import unicodedata

import httpx

from backend.config import get_settings
from backend.services.app_context import date_relation, warsaw_now
from backend.services.seeded_fallback import deterministic_weather_variation
from backend.services.weather_cache import read_cache, write_cache
from backend.services.weather_normalization import normalized_weather_record, number


PROVIDER_DEFINITIONS = [
    {"provider": "openweather-forecast", "role": "provider A forecast", "active": True},
    {"provider": "open-meteo-forecast", "role": "provider B forecast", "active": True},
    {"provider": "meteosource-30day", "role": "optional 30-day forecast provider", "active": True},
    {"provider": "ncep-cfs-30day", "role": "free 30-day NOAA NCEP CFS ensemble", "active": True},
    {"provider": "open-meteo-history", "role": "historical actual weather", "active": True},
    {"provider": "open-meteo-historical-forecast", "role": "archived forecast", "active": True},
    {"provider": "met-no-locationforecast", "role": "independent forecast comparison", "active": True},
    {"provider": "imgw-synop", "role": "official Polish observation", "active": True},
]


def provider_catalog() -> list[dict[str, Any]]:
    return PROVIDER_DEFINITIONS


def fetch_weather_inputs(
    latitude: float,
    longitude: float,
    target_date: date,
    live_fetch: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not live_fetch:
        synthetic = _seasonal_proxy(latitude, longitude, target_date)
        statuses = {
            provider["provider"]: {
                "status": "skipped_for_month_range",
                "role": provider["role"],
                "reason": "Calendar ranges use cached provider data where available and a seasonal proxy otherwise. Day details can refresh live consensus.",
            }
            for provider in PROVIDER_DEFINITIONS
        }
        statuses["seasonal-calibration-proxy"] = {
            "status": "fallback_used",
            "role": "non-provider calibrated seasonal weather proxy",
        }
        return [synthetic], statuses
    relation = date_relation(target_date)
    records: list[dict[str, Any]] = []
    statuses: dict[str, Any] = {}
    location_key = f"lat{latitude:.4f}_lon{longitude:.4f}".replace(".", "_")
    for provider in PROVIDER_DEFINITIONS:
        name = provider["provider"]
        try:
            cached, cache_metadata = read_cache(f"provider_{name}", location_key, target_date)
            if cached is not None:
                record = cached.get("record")
                if record:
                    records.append(record)
                    statuses[name] = {
                        "status": "ok",
                        "role": provider["role"],
                        "fetched_at": record["fetched_at"],
                        "cache_metadata": cache_metadata,
                    }
                    continue
            if name == "openweather-forecast" and relation in {"today", "forecast"}:
                record = _fetch_openweather_forecast(latitude, longitude, target_date)
            elif name == "open-meteo-forecast" and relation in {"today", "forecast"}:
                record = _fetch_open_meteo_forecast(latitude, longitude, target_date)
            elif name == "meteosource-30day" and relation in {"today", "forecast"}:
                record = _fetch_meteosource_forecast(latitude, longitude, target_date)
            elif name == "ncep-cfs-30day" and relation in {"today", "forecast"}:
                record = _fetch_ncep_cfs_seasonal(latitude, longitude, target_date)
            elif name == "open-meteo-history" and relation == "historical":
                record = _fetch_open_meteo_history(latitude, longitude, target_date)
            elif name == "open-meteo-historical-forecast" and relation == "historical" and target_date >= date(2022, 1, 1):
                record = _fetch_open_meteo_historical_forecast(latitude, longitude, target_date)
            elif name == "met-no-locationforecast" and warsaw_now().date() <= target_date <= warsaw_now().date() + timedelta(days=9):
                record = _fetch_met_no(latitude, longitude, target_date)
            elif name == "imgw-synop" and relation == "today":
                record = _fetch_imgw(latitude, longitude)
            else:
                statuses[name] = {"status": "not_applicable_for_date", "role": provider["role"]}
                continue
            if record:
                write_cache(
                    f"provider_{name}",
                    location_key,
                    target_date,
                    {"record": record},
                    provider_failed=False,
                    refresh_reason="provider_refreshed",
                )
                records.append(record)
                statuses[name] = {"status": "ok", "role": provider["role"], "fetched_at": record["fetched_at"]}
            else:
                statuses[name] = {"status": "missing_data", "role": provider["role"]}
        except Exception as exc:  # noqa: BLE001
            statuses[name] = {"status": "error", "role": provider["role"], "error": str(exc)}
    if not records:
        synthetic = _seasonal_proxy(latitude, longitude, target_date)
        records.append(synthetic)
        statuses["seasonal-calibration-proxy"] = {
            "status": "fallback_used",
            "role": "non-provider calibrated seasonal weather proxy",
        }
    return records, statuses


def _target_noon(target_date: date) -> datetime:
    timezone = ZoneInfo(get_settings().default_timezone)
    return datetime.combine(target_date, time(hour=12), tzinfo=timezone)


def _closest_hour(payload: dict[str, Any], target_date: date) -> int | None:
    times = payload.get("hourly", {}).get("time", [])
    target_prefix = target_date.isoformat()
    candidates = [idx for idx, value in enumerate(times) if str(value).startswith(target_prefix)]
    if not candidates:
        return None
    return min(candidates, key=lambda idx: abs(int(str(times[idx])[11:13]) - 12) if len(str(times[idx])) >= 13 else 99)


def _hourly_value(payload: dict[str, Any], field: str, idx: int) -> float | None:
    return number((payload.get("hourly", {}).get(field) or [None])[idx] if idx is not None and idx < len(payload.get("hourly", {}).get(field, [])) else None)


def _fetch_open_meteo_forecast(latitude: float, longitude: float, target_date: date) -> dict[str, Any] | None:
    settings = get_settings()
    days = max(1, min(16, (target_date - warsaw_now().date()).days + 1))
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": settings.default_timezone,
        "forecast_days": days,
        "hourly": "temperature_2m,apparent_temperature,precipitation,precipitation_probability,rain,snowfall,cloud_cover,relative_humidity_2m,wind_speed_10m,wind_gusts_10m,pressure_msl,uv_index,weather_code",
    }
    with httpx.Client(timeout=settings.api_timeout_seconds) as client:
        response = client.get(settings.openmeteo_base_url, params=params)
        response.raise_for_status()
        payload = response.json()
    idx = _closest_hour(payload, target_date)
    if idx is None:
        return None
    return normalized_weather_record(
        target_datetime=_target_noon(target_date),
        provider="open-meteo-forecast",
        fetched_at=warsaw_now(),
        provider_confidence=0.90,
        temperature=_hourly_value(payload, "temperature_2m", idx),
        apparent_temperature=_hourly_value(payload, "apparent_temperature", idx),
        precipitation=_hourly_value(payload, "precipitation", idx),
        precipitation_probability=_hourly_value(payload, "precipitation_probability", idx),
        rain=_hourly_value(payload, "rain", idx),
        snowfall=_hourly_value(payload, "snowfall", idx),
        cloud_cover=_hourly_value(payload, "cloud_cover", idx),
        humidity=_hourly_value(payload, "relative_humidity_2m", idx),
        wind_speed=_hourly_value(payload, "wind_speed_10m", idx),
        wind_gusts=_hourly_value(payload, "wind_gusts_10m", idx),
        pressure=_hourly_value(payload, "pressure_msl", idx),
        uv_index=_hourly_value(payload, "uv_index", idx),
        weather_code=_hourly_value(payload, "weather_code", idx),
    )


def _fetch_openweather_forecast(latitude: float, longitude: float, target_date: date) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.openweather_api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not configured.")
    if not (warsaw_now().date() <= target_date <= warsaw_now().date() + timedelta(days=5)):
        return None
    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": settings.openweather_api_key,
        "units": "metric",
        "lang": "pl",
    }
    with httpx.Client(timeout=settings.api_timeout_seconds) as client:
        response = client.get("https://api.openweathermap.org/data/2.5/forecast", params=params)
        response.raise_for_status()
        payload = response.json()
    target_prefix = target_date.isoformat()
    candidates = [
        item
        for item in payload.get("list", [])
        if str(item.get("dt_txt", "")).startswith(target_prefix)
    ]
    if not candidates:
        return None
    item = min(candidates, key=lambda row: abs(int(str(row.get("dt_txt", "2000-01-01 12:00:00"))[11:13]) - 12))
    main = item.get("main", {})
    wind = item.get("wind", {})
    rain = item.get("rain", {})
    snow = item.get("snow", {})
    clouds = item.get("clouds", {})
    weather = (item.get("weather") or [{}])[0]
    probability = number(item.get("pop"))
    return normalized_weather_record(
        target_datetime=_target_noon(target_date),
        provider="openweather-forecast",
        fetched_at=warsaw_now(),
        provider_confidence=0.82,
        weather_code=weather.get("id"),
        weather_description=weather.get("description") or weather.get("main"),
        temperature=main.get("temp"),
        apparent_temperature=main.get("feels_like"),
        precipitation=((number(rain.get("3h")) or 0) + (number(snow.get("3h")) or 0)) or None,
        precipitation_probability=None if probability is None else round(probability * 100, 1),
        rain=rain.get("3h"),
        snowfall=snow.get("3h"),
        cloud_cover=clouds.get("all"),
        humidity=main.get("humidity"),
        wind_speed=None if wind.get("speed") is None else round(float(wind["speed"]) * 3.6, 2),
        wind_gusts=None if wind.get("gust") is None else round(float(wind["gust"]) * 3.6, 2),
        pressure=main.get("pressure"),
    )


def _fetch_meteosource_forecast(latitude: float, longitude: float, target_date: date) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.meteosource_api_key:
        raise RuntimeError("METEOSOURCE_API_KEY is not configured.")
    if not (warsaw_now().date() <= target_date <= warsaw_now().date() + timedelta(days=30)):
        return None
    params = {
        "lat": latitude,
        "lon": longitude,
        "sections": "daily",
        "language": "pl",
        "units": "metric",
        "key": settings.meteosource_api_key,
    }
    with httpx.Client(timeout=settings.api_timeout_seconds) as client:
        response = client.get(settings.meteosource_base_url, params=params)
        response.raise_for_status()
        payload = response.json()
    daily = payload.get("daily", {}).get("data", [])
    item = next((row for row in daily if str(row.get("day", "")).startswith(target_date.isoformat())), None)
    if item is None:
        return None
    weather = str(item.get("weather") or item.get("summary") or "")
    probability = item.get("probability") or item.get("precipitation_probability")
    precipitation = item.get("all_day", {}).get("precipitation", {}).get("total") if isinstance(item.get("all_day"), dict) else item.get("precipitation")
    all_day = item.get("all_day") if isinstance(item.get("all_day"), dict) else {}
    temperature = all_day.get("temperature") if isinstance(all_day.get("temperature"), (int, float, str)) else item.get("temperature")
    wind = all_day.get("wind_speed") if isinstance(all_day.get("wind_speed"), (int, float, str)) else item.get("wind_speed")
    return normalized_weather_record(
        target_datetime=_target_noon(target_date),
        provider="meteosource-30day",
        fetched_at=warsaw_now(),
        provider_confidence=0.78,
        weather_code=weather,
        weather_description=weather.replace("_", " ").strip().title() or None,
        temperature=temperature,
        apparent_temperature=temperature,
        precipitation=precipitation,
        precipitation_probability=probability,
        rain=precipitation,
        cloud_cover=item.get("cloud_cover"),
        wind_speed=wind,
    )


def _fetch_ncep_cfs_seasonal(latitude: float, longitude: float, target_date: date) -> dict[str, Any] | None:
    settings = get_settings()
    today = warsaw_now().date()
    if not (today <= target_date <= today + timedelta(days=30)):
        return None
    forecast_days = max(1, min(32, (target_date - today).days + 1))
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": settings.default_timezone,
        "forecast_days": forecast_days,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,cloud_cover_mean,relative_humidity_2m_mean,pressure_msl_mean",
    }
    with httpx.Client(timeout=settings.api_timeout_seconds) as client:
        response = client.get("https://seasonal-api.open-meteo.com/v1/seasonal", params=params)
        response.raise_for_status()
        payload = response.json()
    daily = payload.get("daily", {}) or {}
    times = daily.get("time", []) or []
    target_iso = target_date.isoformat()
    if target_iso not in times:
        return None
    idx = times.index(target_iso)

    def _ensemble_mean(field: str) -> float | None:
        members = [key for key in daily.keys() if key.startswith(f"{field}_member") and isinstance(daily.get(key), list)]
        values: list[float] = []
        for member_key in members:
            series = daily.get(member_key) or []
            if idx < len(series):
                value = number(series[idx])
                if value is not None:
                    values.append(float(value))
        if not values:
            base_series = daily.get(field) or []
            if idx < len(base_series):
                value = number(base_series[idx])
                if value is not None:
                    return float(value)
            return None
        return sum(values) / len(values)

    temp_max = _ensemble_mean("temperature_2m_max")
    temp_min = _ensemble_mean("temperature_2m_min")
    if temp_max is None and temp_min is None:
        return None
    if temp_max is not None and temp_min is not None:
        temperature = (temp_max + temp_min) / 2
    else:
        temperature = temp_max if temp_max is not None else temp_min
    precipitation = _ensemble_mean("precipitation_sum")
    cloud_cover = _ensemble_mean("cloud_cover_mean")
    wind_speed = _ensemble_mean("wind_speed_10m_max")
    humidity = _ensemble_mean("relative_humidity_2m_mean")
    pressure = _ensemble_mean("pressure_msl_mean")
    horizon_days = max(0, (target_date - today).days)
    confidence = round(max(0.45, 0.78 - horizon_days * 0.011), 2)
    return normalized_weather_record(
        target_datetime=_target_noon(target_date),
        provider="ncep-cfs-30day",
        fetched_at=warsaw_now(),
        provider_confidence=confidence,
        temperature=temperature,
        apparent_temperature=temperature,
        precipitation=precipitation,
        rain=precipitation,
        cloud_cover=cloud_cover,
        humidity=humidity,
        wind_speed=wind_speed,
        pressure=pressure,
        weather_description="NOAA NCEP CFS ensemble mean",
    )


def _fetch_open_meteo_history(latitude: float, longitude: float, target_date: date) -> dict[str, Any] | None:
    return _fetch_open_meteo_archive("open-meteo-history", "https://archive-api.open-meteo.com/v1/archive", latitude, longitude, target_date, 0.88)


def _fetch_open_meteo_historical_forecast(latitude: float, longitude: float, target_date: date) -> dict[str, Any] | None:
    return _fetch_open_meteo_archive(
        "open-meteo-historical-forecast",
        "https://historical-forecast-api.open-meteo.com/v1/forecast",
        latitude,
        longitude,
        target_date,
        0.76,
    )


def _fetch_open_meteo_archive(provider: str, url: str, latitude: float, longitude: float, target_date: date, confidence: float) -> dict[str, Any] | None:
    settings = get_settings()
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": settings.default_timezone,
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "hourly": "temperature_2m,apparent_temperature,precipitation,rain,snowfall,cloud_cover,relative_humidity_2m,wind_speed_10m,wind_gusts_10m,pressure_msl,weather_code",
    }
    with httpx.Client(timeout=settings.api_timeout_seconds) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
    idx = _closest_hour(payload, target_date)
    if idx is None:
        return None
    return normalized_weather_record(
        target_datetime=_target_noon(target_date),
        provider=provider,
        fetched_at=warsaw_now(),
        provider_confidence=confidence,
        temperature=_hourly_value(payload, "temperature_2m", idx),
        apparent_temperature=_hourly_value(payload, "apparent_temperature", idx),
        precipitation=_hourly_value(payload, "precipitation", idx),
        rain=_hourly_value(payload, "rain", idx),
        snowfall=_hourly_value(payload, "snowfall", idx),
        cloud_cover=_hourly_value(payload, "cloud_cover", idx),
        humidity=_hourly_value(payload, "relative_humidity_2m", idx),
        wind_speed=_hourly_value(payload, "wind_speed_10m", idx),
        wind_gusts=_hourly_value(payload, "wind_gusts_10m", idx),
        pressure=_hourly_value(payload, "pressure_msl", idx),
        weather_code=_hourly_value(payload, "weather_code", idx),
    )


def _fetch_met_no(latitude: float, longitude: float, target_date: date) -> dict[str, Any] | None:
    settings = get_settings()
    params = {"lat": latitude, "lon": longitude}
    with httpx.Client(timeout=settings.api_timeout_seconds) as client:
        response = client.get(
            "https://api.met.no/weatherapi/locationforecast/2.0/complete",
            params=params,
            headers={"User-Agent": settings.met_no_user_agent},
        )
        response.raise_for_status()
        payload = response.json()
    target_prefix = target_date.isoformat()
    best = None
    for item in payload.get("properties", {}).get("timeseries", []):
        time_value = str(item.get("time", ""))
        if time_value.startswith(target_prefix):
            hour = int(time_value[11:13])
            if best is None or abs(hour - 12) < best[0]:
                best = (abs(hour - 12), item)
    if best is None:
        return None
    item = best[1]
    details = item.get("data", {}).get("instant", {}).get("details", {})
    next_1h = item.get("data", {}).get("next_1_hours", {})
    symbol = next_1h.get("summary", {}).get("symbol_code")
    precipitation = number(next_1h.get("details", {}).get("precipitation_amount"))
    return normalized_weather_record(
        target_datetime=_target_noon(target_date),
        provider="met-no-locationforecast",
        fetched_at=warsaw_now(),
        provider_confidence=0.82,
        weather_code=symbol,
        weather_description=str(symbol).replace("_", " ").replace("day", "").title() if symbol else None,
        temperature=details.get("air_temperature"),
        precipitation=precipitation,
        rain=precipitation,
        cloud_cover=details.get("cloud_area_fraction"),
        humidity=details.get("relative_humidity"),
        wind_speed=details.get("wind_speed"),
        wind_gusts=details.get("wind_speed_of_gust"),
        pressure=details.get("air_pressure_at_sea_level"),
    )


def _fetch_imgw(latitude: float, longitude: float) -> dict[str, Any] | None:
    settings = get_settings()
    with httpx.Client(timeout=settings.api_timeout_seconds) as client:
        response = client.get("https://danepubliczne.imgw.pl/api/data/synop")
        response.raise_for_status()
        payload = response.json()
    station = next((row for row in payload if "lodz" in _ascii(row.get("stacja", ""))), None)
    if not station:
        return None
    measurement_date = date.fromisoformat(station.get("data_pomiaru"))
    return normalized_weather_record(
        target_datetime=_target_noon(measurement_date),
        provider="imgw-synop",
        fetched_at=warsaw_now(),
        provider_confidence=0.72,
        weather_description="Official IMGW local observation",
        temperature=station.get("temperatura"),
        precipitation=station.get("suma_opadu"),
        rain=station.get("suma_opadu"),
        humidity=station.get("wilgotnosc_wzgledna"),
        wind_speed=station.get("predkosc_wiatru"),
        pressure=station.get("cisnienie"),
    )


def _seasonal_proxy(latitude: float, longitude: float, target_date: date) -> dict[str, Any]:
    month = target_date.month
    temp = {1: -1, 2: 1, 3: 6, 4: 12, 5: 18, 6: 22, 7: 24, 8: 23, 9: 18, 10: 11, 11: 5, 12: 1}[month]
    variation = deterministic_weather_variation(target_date, latitude, longitude)
    if month in {11, 12, 1, 2}:
        cloud = 58 + round(variation * 32)
        rain_prob = 22 + round(variation * 28)
    elif month in {5, 6, 7, 8}:
        cloud = 18 + round(variation * 58)
        rain_prob = 12 + round(variation * 48)
    else:
        cloud = 28 + round(variation * 55)
        rain_prob = 14 + round(variation * 42)
    precipitation = 0.0
    weather_code = 0
    if rain_prob >= 58 and variation > 0.82:
        precipitation = round(1.0 + variation * 2.4, 2)
        weather_code = 61
    elif cloud >= 82:
        weather_code = 3
    elif cloud >= 35:
        weather_code = 2
    return normalized_weather_record(
        target_datetime=_target_noon(target_date),
        provider="seasonal-calibration-proxy",
        fetched_at=warsaw_now(),
        provider_confidence=0.42,
        temperature=temp,
        apparent_temperature=temp - 1,
        precipitation_probability=rain_prob,
        precipitation=precipitation,
        rain=precipitation,
        cloud_cover=cloud,
        humidity=72,
        wind_speed=12,
        weather_code=weather_code,
        weather_description="Seasonal calibration proxy",
    )


def _ascii(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return normalized.encode("ascii", "ignore").decode("ascii").lower()
