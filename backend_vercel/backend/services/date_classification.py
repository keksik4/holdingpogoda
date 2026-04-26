from __future__ import annotations

from datetime import date

from backend.services.app_context import warsaw_now


def classify_date(target_date: date) -> str:
    today = warsaw_now().date()
    if target_date < today:
        return "historical"
    if target_date == today:
        return "today"
    return "forecast"
