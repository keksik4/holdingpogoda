from datetime import datetime
from typing import Any
import unicodedata

import httpx
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.services.weather_common import (
    default_location,
    missing_fields,
    save_raw_weather_payload,
    update_provider_status,
    upsert_normalized_weather,
    utcnow,
)


LODZ_STATION_NAMES = {"lodz", "lodz-lublinek"}


def fetch_imgw_current(db: Session) -> dict[str, Any]:
    settings = get_settings()
    latitude, longitude, _ = default_location()
    provider = "imgw-synop"
    url = "https://danepubliczne.imgw.pl/api/data/synop"
    try:
        with httpx.Client(timeout=settings.api_timeout_seconds) as client:
            response = client.get(url)
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
        station = _find_lodz_station(payload)
        if not station:
            update_provider_status(db, provider, False, 0, ["station_lodz"], "Lodz station not found in IMGW synop data.")
            return {
                "provider": provider,
                "status": "missing_station",
                "message": "IMGW responded, but a Lodz station was not present in this synop payload.",
                "raw_payload_path": raw_path,
                "available_stations_sample": [row.get("stacja") for row in payload[:10]],
            }
        record = _normalize_station(station, raw_path, latitude, longitude)
        count = upsert_normalized_weather(db, [record])
        update_provider_status(db, provider, True, count, missing_fields(record))
        return {"provider": provider, "status": "ok", "records": count, "raw_payload_path": raw_path, "station": station}
    except Exception as exc:  # noqa: BLE001
        raw_path = save_raw_weather_payload(
            db,
            provider=provider,
            endpoint=url,
            payload={},
            request_url=url,
            error_message=str(exc),
        )
        update_provider_status(db, provider, False, 0, [], str(exc))
        return {"provider": provider, "status": "error", "error": str(exc), "raw_payload_path": raw_path}


def _find_lodz_station(payload: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in payload:
        if _ascii_station_name(row.get("stacja", "")) in LODZ_STATION_NAMES:
            return row
    for row in payload:
        if "lodz" in _ascii_station_name(row.get("stacja", "")):
            return row
    return None


def _ascii_station_name(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value).casefold())
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.replace(" ", "-")


def _normalize_station(station: dict[str, Any], raw_path: str, latitude: float, longitude: float) -> dict[str, Any]:
    measurement_date = station.get("data_pomiaru")
    measurement_hour = int(float(station.get("godzina_pomiaru") or 12))
    if measurement_date:
        target_datetime = datetime.fromisoformat(measurement_date).replace(hour=measurement_hour)
    else:
        target_datetime = utcnow()
    precipitation = _number(station.get("suma_opadu"))
    return {
        "provider": "imgw-synop",
        "fetched_at": utcnow(),
        "forecast_generated_at": None,
        "target_datetime": target_datetime,
        "latitude": latitude,
        "longitude": longitude,
        "temperature": _number(station.get("temperatura")),
        "apparent_temperature": None,
        "precipitation": precipitation,
        "rain": precipitation,
        "snowfall": None,
        "cloud_cover": None,
        "humidity": _number(station.get("wilgotnosc_wzgledna")),
        "wind_speed": _number(station.get("predkosc_wiatru")),
        "wind_gusts": None,
        "pressure": _number(station.get("cisnienie")),
        "uv_index": None,
        "sunshine_duration": None,
        "weather_code": None,
        "weather_description": "Official IMGW local observation",
        "raw_payload_path": raw_path,
    }


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
