from datetime import date
from typing import Any

import pandas as pd

from backend.services.benchmark_calibration import annual_anchor_for_venue


def calibration_summary(venue_slug: str, month_rows: pd.DataFrame) -> dict[str, Any]:
    year = int(pd.to_datetime(month_rows["date"]).dt.year.iloc[0]) if not month_rows.empty else date.today().year
    annual_anchor = annual_anchor_for_venue(venue_slug, year)
    monthly_total = int(month_rows["visitors_base"].sum()) if not month_rows.empty else 0
    return {
        "annual_public_benchmark_anchor": round(annual_anchor),
        "month_total_estimate": monthly_total,
        "average_daily_estimate": round(monthly_total / max(len(month_rows), 1)),
        "status": "calibrated_to_public_benchmark",
        "is_calibrated_demo": True,
        "note": "Daily values are calibrated demo estimates, not internal gate counts.",
    }


def confidence_from_weather_and_calibration(row: dict[str, Any], consensus: dict[str, Any]) -> float:
    base = float(row.get("forecast_confidence", 0.72))
    weather_confidence = float(consensus.get("forecast_confidence_score", 0.55))
    return round(max(0.35, min(0.96, base * 0.55 + weather_confidence * 0.45)), 4)
