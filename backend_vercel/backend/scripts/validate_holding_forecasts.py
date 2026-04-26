from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from backend.services.attendance_forecast_engine import _calendar_day, _hourly_curve_for_daily_total
from backend.services.holding_lodz_knowledge import source_summary


SCENARIOS = [
    (
        "Aquapark Fala, hot summer weekend",
        "aquapark_fala",
        date(2026, 7, 18),
        {
            "weather_icon_key": "sun",
            "weather_risk_level": "low",
            "temperature_avg": 31.0,
            "apparent_temperature_avg": 33.0,
            "precipitation_probability_avg": 12.0,
            "precipitation_avg": 0.0,
            "cloud_cover_avg": 18.0,
            "wind_speed_avg": 9.0,
            "forecast_confidence_score": 0.82,
            "provider_disagreement_score": 0.08,
            "confidencePenalty": 0.03,
            "conditionGroup": "sunny",
            "providerCount": 2,
            "sources": {"openweather": {}, "openmeteo": {}},
            "providers_used": ["openweather-forecast", "open-meteo-forecast"],
            "weather_explanation": "Gorący, suchy dzień z mocnym impulsem dla stref wodnych.",
        },
    ),
    (
        "Aquapark Fala, cold weekday evening pattern",
        "aquapark_fala",
        date(2026, 11, 18),
        {
            "weather_icon_key": "cloud",
            "weather_risk_level": "low",
            "temperature_avg": 6.0,
            "apparent_temperature_avg": 3.0,
            "precipitation_probability_avg": 22.0,
            "precipitation_avg": 0.0,
            "cloud_cover_avg": 84.0,
            "wind_speed_avg": 14.0,
            "forecast_confidence_score": 0.76,
            "provider_disagreement_score": 0.11,
            "confidencePenalty": 0.04,
            "conditionGroup": "cloudy",
            "providerCount": 2,
            "sources": {"openweather": {}, "openmeteo": {}},
            "providers_used": ["openweather-forecast", "open-meteo-forecast"],
            "weather_explanation": "Chłodny dzień, w którym sauny i strefa wewnętrzna stabilizują popyt.",
        },
    ),
    (
        "Orientarium, rainy weekday",
        "orientarium_zoo_lodz",
        date(2026, 10, 14),
        {
            "weather_icon_key": "rain",
            "weather_risk_level": "medium",
            "temperature_avg": 9.0,
            "apparent_temperature_avg": 7.0,
            "precipitation_probability_avg": 76.0,
            "precipitation_avg": 2.4,
            "cloud_cover_avg": 92.0,
            "wind_speed_avg": 18.0,
            "forecast_confidence_score": 0.70,
            "provider_disagreement_score": 0.18,
            "confidencePenalty": 0.08,
            "conditionGroup": "rain",
            "providerCount": 2,
            "sources": {"openweather": {}, "openmeteo": {}},
            "providers_used": ["openweather-forecast", "open-meteo-forecast"],
            "weather_explanation": "Deszcz wzmacnia atrakcyjność pawilonów, ale obniża komfort dojazdu.",
        },
    ),
    (
        "Orientarium, sunny spring school-trip day",
        "orientarium_zoo_lodz",
        date(2026, 5, 13),
        {
            "weather_icon_key": "partly_cloudy",
            "weather_risk_level": "low",
            "temperature_avg": 20.0,
            "apparent_temperature_avg": 20.0,
            "precipitation_probability_avg": 15.0,
            "precipitation_avg": 0.0,
            "cloud_cover_avg": 32.0,
            "wind_speed_avg": 10.0,
            "forecast_confidence_score": 0.84,
            "provider_disagreement_score": 0.06,
            "confidencePenalty": 0.02,
            "conditionGroup": "mixed",
            "providerCount": 2,
            "sources": {"openweather": {}, "openmeteo": {}},
            "providers_used": ["openweather-forecast", "open-meteo-forecast"],
            "weather_explanation": "Łagodna pogoda i sezon wycieczek szkolnych zwiększają poranny ruch.",
        },
    ),
]


def main() -> None:
    print("Holding Łódź knowledge base")
    print(source_summary())
    print()
    for label, venue_slug, target_date, consensus in SCENARIOS:
        row = _demo_row(venue_slug, target_date)
        day = _calendar_day(row, consensus)
        hourly = _hourly_curve_for_daily_total(
            venue_slug,
            target_date,
            day["expected_visitors"],
            day["confidence_score"],
            consensus,
            day["weather_impact_label"],
        )
        hourly_total = sum(item["expected_visitors"] for item in hourly)
        peak = max(hourly, key=lambda item: item["expected_visitors"])
        print(label)
        print(f"  date: {target_date.isoformat()}")
        print(f"  estimated_visitors: {day['expected_visitors']}")
        print(f"  hourly_total: {hourly_total}")
        print(f"  peak: {peak['hour']:02d}:00 = {peak['expected_visitors']} ({peak.get('load_level')})")
        print(f"  confidence: {day['confidence_score']}")
        print(f"  weather_risk: {day['weather_risk']}")
        print(f"  daily_factors: {day['daily_factors']}")
        print(f"  data_sources: {day['data_sources']}")
        print()


def _demo_row(venue_slug: str, target_date: date) -> pd.Series:
    return pd.Series(
        {
            "date": target_date,
            "venue_slug": venue_slug,
            "visitors_base": 4200 if venue_slug == "aquapark_fala" else 2800,
            "forecast_confidence": 0.72,
            "demand_signal_score": 55.0,
            "trend_signal_score": 55.0,
            "event_impact_score": 0.0,
            "holiday_impact_score": 0.0,
            "seasonality_score": 75.0 if target_date.month in {5, 6, 7, 8} else 45.0,
            "weather_impact_score": 0.0,
        }
    )


if __name__ == "__main__":
    main()
