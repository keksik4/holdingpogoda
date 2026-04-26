import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from backend.config import PROJECT_ROOT, get_settings


def get_polish_public_holidays(year: int) -> list[dict[str, Any]]:
    cache_path = PROJECT_ROOT / "data" / "raw" / "business" / f"nager_pl_holidays_{year}.json"
    if cache_path.exists():
        with cache_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    settings = get_settings()
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/PL"
    try:
        with httpx.Client(timeout=settings.api_timeout_seconds) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
    except Exception:  # noqa: BLE001
        payload = _fallback_polish_holidays(year)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return payload


def get_polish_public_holiday_dates(years: set[int]) -> set[date]:
    dates: set[date] = set()
    for year in years:
        for holiday in get_polish_public_holidays(year):
            dates.add(date.fromisoformat(holiday["date"]))
    return dates


def _fallback_polish_holidays(year: int) -> list[dict[str, Any]]:
    fixed = [
        ("01-01", "New Year's Day"),
        ("01-06", "Epiphany"),
        ("05-01", "State Holiday"),
        ("05-03", "Constitution Day"),
        ("08-15", "Assumption of Mary"),
        ("11-01", "All Saints' Day"),
        ("11-11", "Independence Day"),
        ("12-25", "Christmas Day"),
        ("12-26", "Second Day of Christmas"),
    ]
    return [{"date": f"{year}-{month_day}", "localName": name, "name": name, "countryCode": "PL"} for month_day, name in fixed]
