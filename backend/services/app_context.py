from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from backend.config import get_settings
from backend.services.contract_metadata import freshness_metadata, source_metadata


def warsaw_now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().default_timezone)).replace(microsecond=0)


def current_app_context() -> dict:
    now = warsaw_now()
    current_date = now.date()
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "product_name": "Pogoda w Łodzi",
        "current_date": current_date.isoformat(),
        "current_datetime": now.isoformat(),
        "timezone": settings.default_timezone,
        "default_month": f"{current_date.year}-{current_date.month:02d}",
        "default_selected_date": current_date.isoformat(),
        "available_history_start": date(2022, 1, 1).isoformat(),
        "available_forecast_end": (current_date + timedelta(days=180)).isoformat(),
        "data_freshness": {
            "attendance": "calibrated demo attendance generated locally; replace with internal gate data in production",
            "holidays": "public holiday API or local placeholders",
            "weather": "cached provider weather consensus when available",
        },
        "weather_refresh_status": {
            "near_term_forecast_ttl_minutes": 45,
            "daily_forecast_ttl_minutes": 240,
            "historical_ttl_minutes": 10080,
            "provider_failure_ttl_minutes": 15,
        },
        "source_metadata": source_metadata(
            source_type="real",
            label="Backend application clock",
            confidence=1.0,
            is_demo=False,
            notes=["Today is calculated on the backend in Europe/Warsaw timezone."],
        ),
        "freshness_metadata": freshness_metadata(),
    }


def date_relation(target_date: date) -> str:
    today = warsaw_now().date()
    if target_date < today:
        return "historical"
    if target_date == today:
        return "today"
    return "forecast"
