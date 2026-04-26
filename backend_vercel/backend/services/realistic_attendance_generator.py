from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from backend.config import PROJECT_ROOT
from backend.services.benchmark_calibration import (
    apply_benchmark_calibration,
    base_daily_from_annual,
    day_of_week_factor,
    seasonality_score,
)
from backend.services.data_quality import data_quality_label, venue_data_quality
from backend.services.google_trends_signal import trend_score_by_date
from backend.services.news_events_ingestor import event_impact_by_date
from backend.services.app_context import warsaw_now
from backend.services.contract_metadata import freshness_metadata, public_benchmark_source
from backend.services.venue_profiles import get_venue_profile, list_venue_profiles, venue_summary_for_frontend


DAILY_ATTENDANCE_PATH = PROJECT_ROOT / "data" / "processed" / "attendance_calibrated_daily.csv"
HOURLY_ATTENDANCE_PATH = PROJECT_ROOT / "data" / "processed" / "attendance_calibrated_hourly.csv"


def generate_calibrated_attendance(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    start_date = start_date or date(2025, 1, 1)
    end_date = end_date or date(2026, 12, 31)
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date.")
    daily_frames = []
    hourly_frames = []
    for venue in list_venue_profiles():
        daily = _generate_daily_for_venue(venue, start_date, end_date)
        hourly = _generate_hourly_for_venue(venue, daily)
        daily_frames.append(daily)
        hourly_frames.append(hourly)
    daily_df = pd.concat(daily_frames, ignore_index=True)
    hourly_df = pd.concat(hourly_frames, ignore_index=True)
    DAILY_ATTENDANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    daily_df.to_csv(DAILY_ATTENDANCE_PATH, index=False)
    hourly_df.to_csv(HOURLY_ATTENDANCE_PATH, index=False)
    return {
        "status": "ok",
        "daily_path": str(DAILY_ATTENDANCE_PATH),
        "hourly_path": str(HOURLY_ATTENDANCE_PATH),
        "daily_rows": len(daily_df),
        "hourly_rows": len(hourly_df),
        "venues": [venue["venue_slug"] for venue in list_venue_profiles()],
        "data_quality_label": data_quality_label(True),
    }


def ensure_calibrated_attendance() -> None:
    if not DAILY_ATTENDANCE_PATH.exists() or not HOURLY_ATTENDANCE_PATH.exists():
        generate_calibrated_attendance()


def load_daily_attendance(venue_slug: str | None = None) -> pd.DataFrame:
    ensure_calibrated_attendance()
    df = pd.read_csv(DAILY_ATTENDANCE_PATH)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    if venue_slug:
        df = df[df["venue_slug"] == venue_slug]
    return df


def load_hourly_attendance(venue_slug: str | None = None) -> pd.DataFrame:
    ensure_calibrated_attendance()
    df = pd.read_csv(HOURLY_ATTENDANCE_PATH)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    if venue_slug:
        df = df[df["venue_slug"] == venue_slug]
    return df


def venue_selection_payload() -> dict[str, Any]:
    ensure_calibrated_attendance()
    daily = load_daily_attendance()
    venues = []
    today = warsaw_now().date()
    for venue in list_venue_profiles():
        slug = venue["venue_slug"]
        summary = venue_summary_for_frontend(venue)
        venue_daily = daily[daily["venue_slug"] == slug]
        summary["hover_preview"] = {
            "today_expected_visitors": _visitors_for_date(venue_daily, today),
            "tomorrow_expected_visitors": _visitors_for_date(venue_daily, today + timedelta(days=1)),
            "day_after_tomorrow_expected_visitors": _visitors_for_date(venue_daily, today + timedelta(days=2)),
            "weather_icon": _weather_icon_for_row(_row_for_date(venue_daily, today)),
            "risk_label": _risk_level(_row_for_date(venue_daily, today)),
            "data_quality_label": data_quality_label(True),
            "value_quality": {
                "expected_visitors": data_quality_label(True),
                "weather_icon": "Seasonal weather proxy unless refreshed with real weather consensus",
                "risk_label": data_quality_label(True),
            },
            "is_calibrated_demo": True,
            "source_metadata": public_benchmark_source(["Homepage preview values are deterministic and calibrated from public benchmarks."]),
        }
        venues.append(summary)
    return {
        "venues": venues,
        "data_quality_label": data_quality_label(True),
        "source_metadata": public_benchmark_source(["Venue preview data is calibrated demo data unless replaced by internal attendance feeds."]),
        "freshness_metadata": freshness_metadata(),
    }


def calendar_payload(venue_slug: str, month: str) -> dict[str, Any]:
    venue = get_venue_profile(venue_slug)
    target_month = datetime.strptime(month, "%Y-%m").date()
    daily = load_daily_attendance(venue_slug)
    month_rows = daily[
        (pd.to_datetime(daily["date"]).dt.year == target_month.year)
        & (pd.to_datetime(daily["date"]).dt.month == target_month.month)
    ].copy()
    if month_rows.empty:
        generate_calibrated_attendance(date(2025, 1, 1), date(max(2026, target_month.year), 12, 31))
        daily = load_daily_attendance(venue_slug)
        month_rows = daily[
            (pd.to_datetime(daily["date"]).dt.year == target_month.year)
            & (pd.to_datetime(daily["date"]).dt.month == target_month.month)
        ].copy()
    threshold = month_rows["visitors_base"].quantile(0.75) if not month_rows.empty else 0
    days = []
    for _, row in month_rows.sort_values("date").iterrows():
        days.append(
            {
                "date": row["date"].isoformat(),
                "day_number": row["date"].day,
                "weather_icon": _weather_icon_for_row(row),
                "expected_visitors": int(row["visitors_base"]),
                "visitors_low": int(row["visitors_low"]),
                "visitors_base": int(row["visitors_base"]),
                "visitors_high": int(row["visitors_high"]),
                "risk_level": _risk_level(row),
                "best_day": bool(row["visitors_base"] >= threshold and row["weather_risk"] != "high"),
                "data_quality_label": data_quality_label(True),
                "value_quality": {
                    "expected_visitors": data_quality_label(True),
                    "low_base_high": data_quality_label(True),
                    "weather_icon": "Seasonal weather proxy unless refreshed with real weather consensus",
                    "risk_level": data_quality_label(True),
                },
                "is_calibrated_demo": True,
            }
        )
    return {
        "venue_info": venue_summary_for_frontend(venue),
        "month": month,
        "days": days,
        "data_quality": venue_data_quality(venue_slug),
    }


def day_details_payload(venue_slug: str, selected_date: date) -> dict[str, Any]:
    venue = get_venue_profile(venue_slug)
    daily = load_daily_attendance(venue_slug)
    hourly = load_hourly_attendance(venue_slug)
    row = _row_for_date(daily, selected_date)
    if row is None:
        generate_calibrated_attendance(date(2025, 1, 1), date(max(2026, selected_date.year), 12, 31))
        daily = load_daily_attendance(venue_slug)
        hourly = load_hourly_attendance(venue_slug)
        row = _row_for_date(daily, selected_date)
    if row is None:
        raise ValueError(f"No calibrated attendance row found for {venue_slug} on {selected_date}.")
    hourly_rows = hourly[(hourly["venue_slug"] == venue_slug) & (hourly["date"] == selected_date)].sort_values("hour")
    hourly_curve = [
        {
            "datetime": item["datetime"],
            "hour": int(item["hour"]),
            "expected_visitors": int(item["expected_visitors"]),
            "typical_visitors": int(item["typical_visitors"]),
            "confidence_score": float(item["confidence_score"]),
            "peak_hour_flag": bool(item["peak_hour_flag"]),
            "data_quality_label": data_quality_label(True),
            "is_calibrated_demo": True,
        }
        for _, item in hourly_rows.iterrows()
    ]
    peak_hours = [item for item in hourly_curve if item["peak_hour_flag"]]
    typical = _typical_day_visitors(daily, selected_date)
    return {
        "venue_info": venue_summary_for_frontend(venue),
        "selected_date": selected_date.isoformat(),
        "expected_visitors": int(row["visitors_base"]),
        "low_base_high": {
            "low": int(row["visitors_low"]),
            "base": int(row["visitors_base"]),
            "high": int(row["visitors_high"]),
        },
        "weather_risk": row["weather_risk"],
        "weather_details": {
            "weather_icon": _weather_icon_for_row(row),
            "weather_impact_score": float(row["weather_impact_score"]),
            "forecast_confidence": float(row["forecast_confidence"]),
            "note": "Weather details are seasonal/calibrated unless a real weather refresh is joined later.",
            "data_quality_label": "Seasonal weather proxy unless refreshed with real weather consensus",
        },
        "hourly_visitor_curve": hourly_curve,
        "peak_hours": peak_hours,
        "operations_recommendations": _operations_recommendations(row, peak_hours, venue),
        "marketing_recommendations": _marketing_recommendations(row, venue),
        "risk_and_readiness": _risk_and_readiness(row, venue),
        "comparison_to_typical_day": {
            "typical_visitors": typical,
            "difference": int(row["visitors_base"]) - typical,
            "difference_percent": round((int(row["visitors_base"]) - typical) / max(typical, 1) * 100, 1),
        },
            "data_quality_labels": venue_data_quality(venue_slug)["labels"],
            "value_quality": {
                "expected_visitors": data_quality_label(True),
                "low_base_high": data_quality_label(True),
                "hourly_visitor_curve": data_quality_label(True),
                "weather_details": "Seasonal weather proxy unless refreshed with real weather consensus",
                "recommendations": data_quality_label(True),
                "comparison_to_typical_day": data_quality_label(True),
            },
        "is_calibrated_demo": True,
    }


def _generate_daily_for_venue(venue: dict[str, Any], start_date: date, end_date: date) -> pd.DataFrame:
    venue_slug = venue["venue_slug"]
    trends = trend_score_by_date(venue_slug, start_date, end_date)
    events = event_impact_by_date(venue_slug)
    rows = []
    for current in pd.date_range(start=start_date, end=end_date, freq="D"):
        target_date = current.date()
        base = base_daily_from_annual(venue_slug, target_date)
        seasonality = seasonality_score(venue_slug, target_date.month)
        holiday_impact = _holiday_impact(target_date)
        school_impact = _school_holiday_impact(venue_slug, target_date)
        event_impact = events.get(target_date.isoformat(), 0.0)
        trend_score = trends.get(target_date.isoformat(), 50.0)
        trend_factor = 1 + ((trend_score - 50) / 100) * 0.18
        weather_impact, weather_risk = _weather_impact(venue_slug, target_date)
        day_factor = day_of_week_factor(venue_slug, target_date)
        raw = base * day_factor * (1 + holiday_impact + school_impact + event_impact) * trend_factor * weather_impact
        rows.append(
            {
                "date": target_date,
                "venue_slug": venue_slug,
                "raw_visitors": max(0, raw),
                "weather_risk": weather_risk,
                "forecast_confidence": _forecast_confidence(weather_risk),
                "demand_signal_score": round(min(100, max(0, seasonality * 0.45 + trend_score * 0.35 + day_factor * 20)), 2),
                "trend_signal_score": round(trend_score, 2),
                "event_impact_score": round(event_impact * 100, 2),
                "holiday_impact_score": round((holiday_impact + school_impact) * 100, 2),
                "seasonality_score": seasonality,
                "weather_impact_score": round((weather_impact - 1) * 100, 2),
                "notes": "Calibrated demo attendance, not internal ticketing data.",
                "is_calibrated_demo": True,
            }
        )
    df = pd.DataFrame(rows)
    df = apply_benchmark_calibration(df, venue_slug)
    df["visitors_base"] = df["raw_visitors"].round().astype(int)
    uncertainty = df["weather_risk"].map({"low": 0.10, "medium": 0.16, "high": 0.24}).fillna(0.18)
    df["visitors_low"] = (df["visitors_base"] * (1 - uncertainty)).round().astype(int)
    df["visitors_high"] = (df["visitors_base"] * (1 + uncertainty)).round().astype(int)
    df["visitors"] = df["visitors_base"]
    return df[
        [
            "date",
            "venue_slug",
            "visitors",
            "visitors_low",
            "visitors_base",
            "visitors_high",
            "weather_risk",
            "forecast_confidence",
            "demand_signal_score",
            "trend_signal_score",
            "event_impact_score",
            "holiday_impact_score",
            "seasonality_score",
            "weather_impact_score",
            "notes",
            "is_calibrated_demo",
        ]
    ]


def _generate_hourly_for_venue(venue: dict[str, Any], daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    venue_slug = venue["venue_slug"]
    for _, day in daily.iterrows():
        target_date = day["date"]
        hours = _open_hours(venue_slug, target_date)
        weights = _hourly_weights(venue_slug, hours, target_date)
        expected_values = _distribute_integer_total(int(day["visitors_base"]), weights)
        typical_values = _distribute_integer_total(max(1, int(day["visitors_base"] / day_of_week_factor(venue_slug, target_date))), weights)
        peak_threshold = max(expected_values) * 0.92 if expected_values else 0
        for hour, expected, typical in zip(hours, expected_values, typical_values, strict=True):
            rows.append(
                {
                    "datetime": datetime.combine(target_date, datetime.min.time()).replace(hour=hour).isoformat(),
                    "date": target_date,
                    "hour": hour,
                    "venue_slug": venue_slug,
                    "expected_visitors": expected,
                    "typical_visitors": typical,
                    "confidence_score": day["forecast_confidence"],
                    "peak_hour_flag": bool(expected >= peak_threshold and expected > 0),
                    "notes": "Hourly values are reconciled to the calibrated demo daily total.",
                    "is_calibrated_demo": True,
                }
            )
    return pd.DataFrame(rows)


def _open_hours(venue_slug: str, target_date: date) -> list[int]:
    if venue_slug == "aquapark_fala":
        return list(range(8, 22)) if target_date.month in {6, 7, 8} else list(range(9, 22))
    return list(range(9, 19)) if target_date.month in {4, 5, 6, 7, 8, 9} else list(range(9, 18))


def _hourly_weights(venue_slug: str, hours: list[int], target_date: date) -> list[float]:
    center = 15 if venue_slug == "aquapark_fala" else 13
    spread = 2.8 if venue_slug == "aquapark_fala" else 2.4
    weights = []
    for hour in hours:
        peak = 1.0 + 1.6 * pow(2.71828, -((hour - center) ** 2) / (2 * spread * spread))
        if venue_slug == "aquapark_fala" and target_date.month in {6, 7, 8} and hour >= 16:
            peak *= 1.12
        if venue_slug == "orientarium_zoo_lodz" and hour in {10, 11, 12, 13, 14}:
            peak *= 1.08
        weights.append(peak)
    total = sum(weights)
    return [weight / total for weight in weights]


def _distribute_integer_total(total: int, weights: list[float]) -> list[int]:
    raw = [total * weight for weight in weights]
    values = [int(value) for value in raw]
    remainder = total - sum(values)
    order = sorted(range(len(raw)), key=lambda index: raw[index] - values[index], reverse=True)
    for index in order[:remainder]:
        values[index] += 1
    return values


def _holiday_impact(target_date: date) -> float:
    fixed_holidays = {(1, 1), (1, 6), (5, 1), (5, 3), (8, 15), (11, 1), (11, 11), (12, 25), (12, 26)}
    if (target_date.month, target_date.day) in fixed_holidays:
        return 0.22
    if target_date.weekday() in {5, 6}:
        return 0.02
    return 0.0


def _school_holiday_impact(venue_slug: str, target_date: date) -> float:
    if date(target_date.year, 6, 28) <= target_date <= date(target_date.year, 8, 31):
        return 0.16 if venue_slug == "aquapark_fala" else 0.10
    if target_date.month == 2:
        return 0.10 if venue_slug == "aquapark_fala" else 0.05
    return 0.0


def _weather_impact(venue_slug: str, target_date: date) -> tuple[float, str]:
    month = target_date.month
    wave = ((target_date.timetuple().tm_yday * 37) % 100) / 100
    if venue_slug == "aquapark_fala":
        if month in {6, 7, 8}:
            return (1.18 if wave > 0.28 else 0.88, "low" if wave > 0.28 else "medium")
        if month in {11, 12, 1, 2}:
            return (1.03, "medium")
        return (1.08 if wave > 0.35 else 0.94, "low" if wave > 0.35 else "medium")
    if month in {5, 6, 7, 8, 9}:
        if wave < 0.18:
            return 0.80, "high"
        return (1.12, "low")
    if month in {11, 12, 1, 2}:
        return (0.88 if wave < 0.35 else 0.96, "medium")
    return (1.05 if wave > 0.25 else 0.90, "low" if wave > 0.25 else "medium")


def _forecast_confidence(weather_risk: str) -> float:
    return {"low": 0.82, "medium": 0.72, "high": 0.62}.get(weather_risk, 0.7)


def _visitors_for_date(df: pd.DataFrame, target_date: date) -> int | None:
    row = _row_for_date(df, target_date)
    return int(row["visitors_base"]) if row is not None else None


def _row_for_date(df: pd.DataFrame, target_date: date) -> pd.Series | None:
    if df.empty:
        return None
    matches = df[df["date"] == target_date]
    if matches.empty:
        return None
    return matches.iloc[0]


def _weather_icon_for_row(row: pd.Series | None) -> str:
    if row is None:
        return "unknown"
    if row["weather_risk"] == "high":
        return "rain"
    if float(row["weather_impact_score"]) > 8:
        return "sun"
    if row["weather_risk"] == "medium":
        return "cloud"
    return "partly_cloudy"


def _risk_level(row: pd.Series | None) -> str:
    if row is None:
        return "unknown"
    if row["weather_risk"] == "high" or float(row["forecast_confidence"]) < 0.65:
        return "high"
    if row["weather_risk"] == "medium":
        return "medium"
    return "low"


def _typical_day_visitors(daily: pd.DataFrame, selected_date: date) -> int:
    comparable = daily[
        (pd.to_datetime(daily["date"]).dt.month == selected_date.month)
        & (pd.to_datetime(daily["date"]).dt.weekday == selected_date.weekday())
    ]
    if comparable.empty:
        return int(daily["visitors_base"].mean())
    return int(comparable["visitors_base"].median())


def _operations_recommendations(row: pd.Series, peak_hours: list[dict[str, Any]], venue: dict[str, Any]) -> list[str]:
    visitors = int(row["visitors_base"])
    recommendations = []
    if visitors > 7000:
        recommendations.append("Prepare high-capacity queue lanes, parking overflow and additional cleaning/security cover.")
    elif visitors > 3500:
        recommendations.append("Use reinforced staffing during peak hours and monitor entry queues.")
    else:
        recommendations.append("Standard staffing with flexible support is sufficient.")
    if row["weather_risk"] == "high":
        recommendations.append("Weather risk is high; prepare indoor routing and conservative outdoor staffing.")
    if peak_hours:
        recommendations.append(f"Peak load expected around {', '.join(str(item['hour']) for item in peak_hours[:3])}:00.")
    return recommendations


def _marketing_recommendations(row: pd.Series, venue: dict[str, Any]) -> list[str]:
    if row["weather_risk"] == "low" and venue["venue_slug"] == "aquapark_fala":
        return ["Use short-term outdoor/summer creative and family day-trip messaging."]
    if row["weather_risk"] == "high" and venue["venue_slug"] == "orientarium_zoo_lodz":
        return ["Promote indoor Orientarium resilience and timed-ticket planning."]
    if float(row["trend_signal_score"]) > 60:
        return ["Demand signal is elevated; shift budget toward high-intent search and social campaigns."]
    return ["Keep campaign spend steady and use venue-specific family/tourism messaging."]


def _risk_and_readiness(row: pd.Series, venue: dict[str, Any]) -> dict[str, Any]:
    return {
        "risk_level": _risk_level(row),
        "weather_risk": row["weather_risk"],
        "readiness_checklist": venue["operational_areas"],
        "data_quality_label": data_quality_label(True),
    }
