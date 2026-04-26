from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from backend.services.app_context import current_app_context, date_relation, warsaw_now
from backend.services.attendance_calibration import calibration_summary, confidence_from_weather_and_calibration
from backend.services.data_quality import data_quality_label, venue_data_quality
from backend.services.contract_metadata import freshness_metadata, public_benchmark_source
from backend.services.realistic_attendance_generator import (
    generate_calibrated_attendance,
    load_daily_attendance,
    load_hourly_attendance,
)
from backend.services.forecast_validation import calendar_day_is_best_candidate, clamp_daily_visitors, scenario_range, validate_hourly_curve
from backend.services.holding_lodz_knowledge import (
    base_daily_visitors,
    bottlenecks_for_hour,
    calendar_multiplier,
    holding_profile_for_venue,
    object_id_for_venue,
    seasonal_multiplier,
    select_hourly_profile,
    source_summary,
    weather_multiplier,
    weekday_multiplier,
)
from backend.services.venue_demand_model import explanation_for_forecast, weather_adjustment
from backend.services.venue_profiles import get_venue_profile, list_venue_profiles, venue_summary_for_frontend
from backend.services.weather_consensus import venue_weather_consensus


_FORECAST_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def venue_selection_forecast_payload() -> dict[str, Any]:
    context = current_app_context()
    today = date.fromisoformat(context["current_date"])
    venues = []
    for venue_slug in [profile["venue_slug"] for profile in list_venue_profiles()]:
        venue = get_venue_profile(venue_slug)
        summary = venue_summary_for_frontend(venue)
        forecast_days = [_canonical_forecast(venue_slug, today + timedelta(days=offset))["calendar_day"] for offset in range(3)]
        summary["hover_preview"] = {
            "today_expected_visitors": forecast_days[0]["expected_visitors"],
            "tomorrow_expected_visitors": forecast_days[1]["expected_visitors"],
            "day_after_tomorrow_expected_visitors": forecast_days[2]["expected_visitors"],
            "weather_icon": forecast_days[0]["weather_icon"],
            "risk_label": forecast_days[0]["risk_level"],
            "confidence": forecast_days[0]["confidence_score"],
            "days": [
                {
                    "date": item["date"],
                    "label": ["Dzisiaj", "Jutro", "Pojutrze"][index],
                    "expected_visitors": item["expected_visitors"],
                    "weather_icon": item["weather_icon"],
                    "risk_level": item["risk_level"],
                    "confidence_score": item["confidence_score"],
                    "source_count": item["weather_consensus_brief"]["providerCount"],
                    "weather_status": item.get("weather_data_status", "dane częściowe"),
                }
                for index, item in enumerate(forecast_days)
            ],
            "data_quality_label": data_quality_label(True),
            "value_quality": {
                "expected_visitors": data_quality_label(True),
                "weather": "Ta sama prognoza kanoniczna co kalendarz i szczegóły dnia.",
            },
            "is_calibrated_demo": True,
            "source_metadata": public_benchmark_source(["Homepage preview uses canonical venue/date forecasts shared with calendar and day details."]),
        }
        venues.append(summary)
    return {
        "venues": venues,
        "data_quality_label": data_quality_label(True),
        "source_metadata": public_benchmark_source(["Venue previews use the canonical forecast cache keyed by venue and date."]),
        "freshness_metadata": freshness_metadata(),
    }


def calendar_forecast_payload(venue_slug: str, month: str | None = None, force_weather: bool = False) -> dict[str, Any]:
    context = current_app_context()
    month = month or context["default_month"]
    target_month = datetime.strptime(month, "%Y-%m").date()
    start = target_month.replace(day=1)
    end = target_month.replace(day=monthrange(target_month.year, target_month.month)[1])
    ensure_date_range(venue_slug, start, end)
    venue = get_venue_profile(venue_slug)
    daily = load_daily_attendance(venue_slug)
    month_rows = daily[(pd.to_datetime(daily["date"]).dt.year == start.year) & (pd.to_datetime(daily["date"]).dt.month == start.month)].copy()
    forecasts = [_canonical_forecast(venue_slug, row["date"], force_weather=force_weather) for _, row in month_rows.sort_values("date").iterrows()]
    enriched = [item["calendar_day"] for item in forecasts]
    threshold = _best_day_threshold(enriched)
    days = [
        item | {"best_day": calendar_day_is_best_candidate(item, threshold)}
        for item in enriched
    ]
    return {
        "current_date": context["current_date"],
        "selected_date": context["default_selected_date"] if month == context["default_month"] else start.isoformat(),
        "month": month,
        "venue_info": venue_summary_for_frontend(venue),
        "venue": venue_summary_for_frontend(venue),
        "days": days,
        "data_freshness": {
            "weather": {
                "cache_hits": sum(1 for item in forecasts if item["consensus"].get("cache_metadata", {}).get("cache_hit")),
                "items": len(forecasts),
            },
            "attendance": "calibrated demo attendance generated locally",
        },
        "weather_consensus_summary": {
            "providers_available": forecasts[0]["consensus"].get("providers_available", []) if forecasts else [],
            "providers_used_this_month": sorted({provider for item in forecasts for provider in item["consensus"].get("providers_used", [])}),
            "incomplete_days": [item["calendar_day"]["date"] for item in forecasts if item["consensus"].get("source_count", 0) < 2 and item["calendar_day"]["date_relation"] in {"today", "forecast"}],
        },
        "calibration_summary": calibration_summary(venue_slug, month_rows),
        "holding_lodz_knowledge_base": source_summary(),
        "data_quality": venue_data_quality(venue_slug),
        "source_metadata": public_benchmark_source(
            [
                "Calendar values are deterministic calibrated estimates.",
                "Weather icons come from cached weather consensus or a clearly marked seasonal proxy.",
            ]
        ),
        "freshness_metadata": freshness_metadata(),
    }


def day_forecast_payload(
    venue_slug: str,
    selected_date: date,
    force_weather: bool = False,
    live_weather: bool = True,
) -> dict[str, Any]:
    canonical = _canonical_forecast(venue_slug, selected_date, force_weather=force_weather)
    venue = get_venue_profile(venue_slug)
    daily = load_daily_attendance(venue_slug)
    row = canonical["row"]
    consensus = canonical["consensus"]
    day = canonical["calendar_day"]
    hourly_curve = _hourly_curve_for_daily_total(
        venue_slug,
        selected_date,
        day["expected_visitors"],
        day["confidence_score"],
        consensus,
        day.get("weather_impact_label", "neutralny wpływ"),
    )
    peak_hours = [item for item in hourly_curve if item["peak_hour_flag"]]
    typical = _typical_day_visitors(daily, selected_date)
    relation = date_relation(selected_date)
    explanation = explanation_for_forecast(venue_slug, selected_date, relation, row.to_dict(), consensus)
    return {
        "venue_info": venue_summary_for_frontend(venue),
        "selected_date": selected_date.isoformat(),
        "date_relation": relation,
        "expected_visitors": day["expected_visitors"],
        "low_base_high": {"low": day["visitors_low"], "base": day["visitors_base"], "high": day["visitors_high"]},
        "hourly_visitor_curve": hourly_curve,
        "peak_hours": peak_hours,
        "weather_consensus": consensus,
        "providers_used": consensus["providers_used"],
        "provider_disagreement_score": consensus.get("provider_disagreement_score", 0),
        "weather_risk": day["weather_risk"],
        "venue_id": object_id_for_venue(venue_slug),
        "estimated_visitors": day["expected_visitors"],
        "confidence": day["confidence_score"],
        "daily_factors": day["daily_factors"],
        "hourly_forecast": day.get("hourly_forecast_preview", hourly_curve),
        "data_sources": day["data_sources"],
        "holding_lodz_profile": holding_profile_for_venue(venue_slug),
        "weather_details": {
            "weather_icon": consensus["weather_icon_key"],
            "weather_impact_score": day["weather_impact_score"],
            "forecast_confidence": day["confidence_score"],
            "note": consensus["weather_explanation"],
            "data_quality_label": "Real weather API consensus where providers are available; calibrated proxy otherwise",
            "temperature": consensus.get("temperature_avg"),
            "apparent_temperature": consensus.get("apparent_temperature_avg"),
            "precipitation_probability": consensus.get("precipitation_probability_avg"),
            "wind_speed": consensus.get("wind_speed_avg"),
            "label_pl": consensus.get("weather_label_pl"),
            "confidence_note": consensus.get("weather_confidence_note"),
            "is_weather_fallback": consensus.get("is_weather_fallback"),
        },
        "operations_recommendations": _operations(day, peak_hours),
        "marketing_recommendations": _marketing(venue_slug, day, consensus),
        "risk_and_readiness": _readiness(day, venue),
        "comparison_to_typical_day": {
            "typical_visitors": typical,
            "difference": day["expected_visitors"] - typical,
            "difference_percent": round((day["expected_visitors"] - typical) / max(typical, 1) * 100, 1),
        },
        "forecast_explanation": explanation,
        "explanation": explanation,
        "calibration_confidence": day["confidence_score"],
        "data_quality_labels": venue_data_quality(venue_slug)["labels"],
        "value_quality": {
            "expected_visitors": data_quality_label(True),
            "weather_consensus": "Pełny konsensus pogodowy" if consensus.get("source_count", 0) >= 2 else "Dane częściowe - brak drugiego źródła",
            "hourly_visitor_curve": data_quality_label(True),
            "recommendations": data_quality_label(True),
        },
        "is_calibrated_demo": True,
        "source_metadata": public_benchmark_source(
            [
                "Day detail values are generated by the same forecast engine used by the calendar.",
                "Hourly values are reconciled to the daily expected visitor total.",
            ]
        ),
        "freshness_metadata": freshness_metadata(consensus.get("cache_metadata")),
    }


def _canonical_forecast(venue_slug: str, target_date: date, force_weather: bool = False) -> dict[str, Any]:
    key = (venue_slug, target_date.isoformat())
    if not force_weather and key in _FORECAST_CACHE:
        return _FORECAST_CACHE[key]
    ensure_date_range(venue_slug, target_date, target_date)
    daily = load_daily_attendance(venue_slug)
    row = _row_for_date(daily, target_date)
    if row is None:
        raise ValueError(f"No calibrated attendance row found for {venue_slug} on {target_date}.")
    consensus = venue_weather_consensus(venue_slug, target_date, force=force_weather, live_fetch=_should_live_fetch_weather(target_date))
    day = _calendar_day(row, consensus)
    result = {"row": row, "consensus": consensus, "calendar_day": day}
    if not force_weather:
        _FORECAST_CACHE[key] = result
    return result


def _should_live_fetch_weather(target_date: date) -> bool:
    today = warsaw_now().date()
    return today <= target_date <= today + timedelta(days=30)


def forecast_validation_payload(venue_slug: str, month: str) -> dict[str, Any]:
    calendar = calendar_forecast_payload(venue_slug, month)
    unrealistic = []
    for day in calendar["days"]:
        details = day_forecast_payload(venue_slug, date.fromisoformat(day["date"]), live_weather=False)
        hourly_total = sum(item["expected_visitors"] for item in details["hourly_visitor_curve"])
        if abs(hourly_total - day["expected_visitors"]) > max(5, day["expected_visitors"] * 0.01):
            unrealistic.append({"date": day["date"], "issue": "daily_hourly_mismatch", "daily": day["expected_visitors"], "hourly": hourly_total})
        peak = max((item["expected_visitors"] for item in details["hourly_visitor_curve"]), default=0)
        if peak > day["expected_visitors"] * 0.25:
            unrealistic.append({"date": day["date"], "issue": "peak_hour_too_high", "peak": peak, "daily": day["expected_visitors"]})
    return {
        "venue_slug": venue_slug,
        "month": month,
        "daily_hourly_reconciliation_status": "ok" if not unrealistic else "review_needed",
        "benchmark_calibration_status": calendar["calibration_summary"]["status"],
        "weather_provider_status": calendar["weather_consensus_summary"],
        "unrealistic_values_found": unrealistic,
        "notes": [
            "Calendar and day-details values are generated from the same calibrated forecast engine.",
            "Hourly values are integer-distributed to reconcile to the daily total.",
        ],
    }


def ensure_date_range(venue_slug: str, start: date, end: date) -> None:
    daily = load_daily_attendance(venue_slug)
    if daily.empty or start < min(daily["date"]) or end > max(daily["date"]):
        generate_calibrated_attendance(min(start, date(2022, 1, 1)), max(end, warsaw_now().date() + timedelta(days=210)))


def _calendar_day(row: pd.Series, consensus: dict[str, Any]) -> dict[str, Any]:
    holding = _holding_daily_estimate(row, consensus)
    factor, risk, weather_impact_score = weather_adjustment(row["venue_slug"], consensus)
    base = clamp_daily_visitors(row["venue_slug"], int(round(holding["estimated_visitors"] * factor)))
    confidence = confidence_from_weather_and_calibration(row.to_dict(), consensus)
    confidence = round(max(0.28, min(0.96, confidence * 0.72 + holding["confidence"] * 0.28)), 4)
    target_date = row["date"]
    explanation = explanation_for_forecast(row["venue_slug"], target_date, date_relation(target_date), row.to_dict(), consensus)
    scenarios = scenario_range(base, confidence, risk)
    return {
        "date": target_date.isoformat(),
        "day_number": target_date.day,
        "date_relation": date_relation(target_date),
        "weather_icon": consensus["weather_icon_key"],
        "expected_visitors": base,
        "visitors_low": scenarios["low"],
        "visitors_base": scenarios["base"],
        "visitors_high": scenarios["high"],
        "risk_level": risk,
        "weather_risk": risk,
        "best_day": False,
        "confidence_score": confidence,
        "weather_impact_score": weather_impact_score,
        "weather_impact_label": holding["weather_impact_label"],
        "daily_factors": holding["daily_factors"],
        "data_sources": holding["data_sources"],
        "venue_id": object_id_for_venue(row["venue_slug"]),
        "estimated_visitors": base,
        "provider_disagreement_score": consensus.get("provider_disagreement_score", 0),
        "weather_data_status": consensus.get("weather_data_status", "dane częściowe"),
        "has_weather_consensus": bool(consensus.get("has_weather_consensus")),
        "source_count": int(consensus.get("source_count", 0) or 0),
        "weather_consensus_brief": {
            "conditionGroup": consensus.get("conditionGroup"),
            "providerCount": consensus.get("providerCount", consensus.get("source_count", 0)),
            "disagreementScore": consensus.get("disagreementScore", consensus.get("provider_disagreement_score", 0)),
        },
        "demand_signal_score": float(row["demand_signal_score"]),
        "seasonality_score": float(row["seasonality_score"]),
        "holiday_impact_score": float(row["holiday_impact_score"]),
        "event_impact_score": float(row["event_impact_score"]),
        "trend_signal_score": float(row["trend_signal_score"]),
        "explanation": explanation,
        "data_quality_label": data_quality_label(True),
        "value_quality": {"expected_visitors": data_quality_label(True), "weather": "Weather consensus or calibrated proxy"},
        "is_calibrated_demo": True,
    }


def _holding_daily_estimate(row: pd.Series, consensus: dict[str, Any]) -> dict[str, Any]:
    venue_slug = row["venue_slug"]
    target_date = row["date"]
    fallback_base = int(row["visitors_base"])
    public_holiday = float(row.get("holiday_impact_score", 0) or 0) >= 20
    base, baseline_confidence, source = base_daily_visitors(venue_slug, fallback_base)
    dow_factor = weekday_multiplier(venue_slug, target_date, is_public_holiday=public_holiday)
    month_factor = seasonal_multiplier(venue_slug, target_date)
    calendar_factor, calendar_notes = calendar_multiplier(venue_slug, target_date, is_public_holiday=public_holiday)
    weather_factor, weather_label, weather_notes = weather_multiplier(venue_slug, consensus)
    event_factor = 1.0 + min(0.18, max(0.0, float(row.get("event_impact_score", 0) or 0) / 100))
    trend_factor = 1.0 + max(-0.08, min(0.10, (float(row.get("trend_signal_score", 50) or 50) - 50) / 500))
    confidence_penalty = float(consensus.get("confidencePenalty", 0) or 0)
    estimate = base * dow_factor * month_factor * calendar_factor * weather_factor * event_factor * trend_factor
    confidence = round(max(0.25, min(0.95, baseline_confidence * 0.55 + float(consensus.get("forecast_confidence_score", 0.55)) * 0.45 - confidence_penalty)), 4)
    return {
        "estimated_visitors": int(round(estimate)),
        "confidence": confidence,
        "weather_impact_label": weather_label,
        "notes": calendar_notes + weather_notes,
        "data_sources": [source, *([key for key in ["openweather", "openmeteo", "meteosource"] if key in consensus.get("sources", {})])],
        "daily_factors": {
            "base_daily_visitors": base,
            "weekday_multiplier": round(dow_factor, 4),
            "seasonal_multiplier": round(month_factor, 4),
            "weather_multiplier": round(weather_factor, 4),
            "holiday_multiplier": round(calendar_factor, 4),
            "event_multiplier": round(event_factor, 4),
            "trend_multiplier": round(trend_factor, 4),
            "venue_specific_adjustment": 1.0,
        },
    }


def _best_day_threshold(days: list[dict[str, Any]]) -> int:
    values = sorted(day["expected_visitors"] for day in days)
    if not values:
        return 0
    return values[int(len(values) * 0.76)]


def _row_for_date(df: pd.DataFrame, target_date: date) -> pd.Series | None:
    matches = df[df["date"] == target_date]
    return None if matches.empty else matches.iloc[0]


def _hourly_curve_for_daily_total(
    venue_slug: str,
    target_date: date,
    total: int,
    confidence: float,
    consensus: dict[str, Any] | None = None,
    weather_impact_label: str = "neutralny wpływ",
) -> list[dict[str, Any]]:
    consensus = consensus or {}
    profile_id, profile_rows, profile_source = select_hourly_profile(venue_slug, target_date, consensus)
    if profile_rows:
        weights = [max(0.0001, float(row["share_of_daily_visitors"])) for row in profile_rows]
        typical_weights = weights
        expected = _distribute_integer_total(total, weights)
        typical_total = max(1, int(round(total / max(0.55, min(1.65, weekday_multiplier(venue_slug, target_date) * seasonal_multiplier(venue_slug, target_date))))))
        typical = _distribute_integer_total(typical_total, typical_weights)
        peak = max(expected) if expected else 0
        curve = []
        for index, row in enumerate(profile_rows):
            occupancy_percent = int(round(min(100, max(0, float(row["occupancy_index"]) * 100))))
            bottlenecks = bottlenecks_for_hour(venue_slug, int(row["hour"]))
            load_level = _load_level(occupancy_percent, bottlenecks)
            note = _operational_note(row, bottlenecks, load_level)
            curve.append(
                {
                    "datetime": f"{target_date.isoformat()}T{int(row['hour']):02d}:00:00",
                    "date": target_date.isoformat(),
                    "hour": int(row["hour"]),
                    "hour_label": f"{int(row['hour']):02d}:00",
                    "estimated_visitors": expected[index],
                    "expected_visitors": expected[index],
                    "typical_visitors": typical[index],
                    "confidence_score": confidence,
                    "confidence": confidence,
                    "peak_hour_flag": expected[index] >= peak * 0.92 if peak else False,
                    "occupancy_percent": occupancy_percent,
                    "load_level": load_level,
                    "weather_impact": weather_impact_label,
                    "operational_note": note,
                    "profile_id": profile_id,
                    "data_source": profile_source,
                    "data_quality_label": data_quality_label(True),
                    "is_calibrated_demo": True,
                }
            )
        return validate_hourly_curve(total, curve)

    hourly = load_hourly_attendance(venue_slug)
    rows = hourly[(hourly["venue_slug"] == venue_slug) & (hourly["date"] == target_date)].sort_values("hour")
    if rows.empty:
        generate_calibrated_attendance(min(target_date, date(2022, 1, 1)), max(target_date, warsaw_now().date() + timedelta(days=210)))
        hourly = load_hourly_attendance(venue_slug)
        rows = hourly[(hourly["venue_slug"] == venue_slug) & (hourly["date"] == target_date)].sort_values("hour")
    weights = [max(1, int(row["expected_visitors"])) for _, row in rows.iterrows()]
    expected = _distribute_integer_total(total, weights)
    typical_total = max(1, int(sum(int(row["typical_visitors"]) for _, row in rows.iterrows()) * total / max(sum(weights), 1)))
    typical = _distribute_integer_total(typical_total, weights)
    peak = max(expected) if expected else 0
    curve = []
    for index, (_, row) in enumerate(rows.iterrows()):
        curve.append(
            {
                "datetime": row["datetime"],
                "date": target_date.isoformat(),
                "hour": int(row["hour"]),
                "expected_visitors": expected[index],
                "typical_visitors": typical[index],
                "confidence_score": confidence,
                "peak_hour_flag": expected[index] >= peak * 0.92 if peak else False,
                "occupancy_percent": int(round(expected[index] / max(peak, 1) * 100)),
                "load_level": _load_level(int(round(expected[index] / max(peak, 1) * 100)), []),
                "weather_impact": weather_impact_label,
                "operational_note": "Profil godzinowy z wcześniejszego generatora fallback.",
                "data_source": "previous_backend_fallback",
                "data_quality_label": data_quality_label(True),
                "is_calibrated_demo": True,
            }
        )
    return validate_hourly_curve(total, curve)


def _distribute_integer_total(total: int, weights: list[int]) -> list[int]:
    denominator = max(sum(weights), 1)
    raw = [total * weight / denominator for weight in weights]
    values = [int(value) for value in raw]
    remainder = total - sum(values)
    order = sorted(range(len(raw)), key=lambda index: raw[index] - values[index], reverse=True)
    for index in order[:remainder]:
        values[index] += 1
    return values


def _typical_day_visitors(daily: pd.DataFrame, selected_date: date) -> int:
    comparable = daily[
        (pd.to_datetime(daily["date"]).dt.month == selected_date.month)
        & (pd.to_datetime(daily["date"]).dt.weekday == selected_date.weekday())
    ]
    return int(comparable["visitors_base"].median()) if not comparable.empty else int(daily["visitors_base"].median())


def _operations(day: dict[str, Any], peak_hours: list[dict[str, Any]]) -> list[str]:
    visitors = day["expected_visitors"]
    items = []
    if visitors > 7000:
        items.append("Prepare high-capacity staffing, queue lanes, parking overflow and cleaning rounds.")
    elif visitors > 3500:
        items.append("Prepare reinforced staffing, queue monitoring, parking guidance and cleaning rounds.")
    else:
        items.append("Use standard staffing with a small flexible support pool.")
    if day["risk_level"] == "high":
        items.append("Weather risk is high, so prepare indoor routing and scenario staffing.")
    if peak_hours:
        items.append(f"Plan peak coverage around {min(item['hour'] for item in peak_hours)}:00 - {max(item['hour'] for item in peak_hours) + 1}:00.")
    return items


def _marketing(venue_slug: str, day: dict[str, Any], consensus: dict[str, Any]) -> list[str]:
    if venue_slug == "aquapark_fala" and day["risk_level"] == "low":
        return ["Use weather-positive campaign messaging for family and day-trip audiences."]
    if venue_slug == "orientarium_zoo_lodz" and day["risk_level"] != "low":
        return ["Emphasize indoor Orientarium resilience and timed-ticket planning."]
    return ["Keep spend aligned with demand; avoid over-boosting when confidence is moderate."]


def _readiness(day: dict[str, Any], venue: dict[str, Any]) -> dict[str, Any]:
    crowd_risk = "high" if day["expected_visitors"] > 7000 else "medium" if day["expected_visitors"] > 4200 else "low"
    return {
        "risk_level": day["risk_level"],
        "weather_risk": day["risk_level"],
        "crowd_risk": crowd_risk,
        "operational_readiness": "Good" if day["confidence_score"] >= 0.62 else "Scenario planning",
        "readiness_checklist": venue["operational_areas"],
        "data_quality_label": data_quality_label(True),
    }


def _load_level(occupancy_percent: int, bottlenecks: list[dict[str, Any]]) -> str:
    if any(str(item.get("crowd_status", "")).lower() in {"krytyczny", "bardzo wysoki"} for item in bottlenecks):
        return "krytyczny"
    if occupancy_percent >= 82 or any(str(item.get("crowd_status", "")).lower() == "wysoki" for item in bottlenecks):
        return "wysoki"
    if occupancy_percent >= 52:
        return "średni"
    return "niski"


def _operational_note(row: dict[str, Any], bottlenecks: list[dict[str, Any]], load_level: str) -> str:
    if bottlenecks:
        names = ", ".join(str(item.get("event")) for item in bottlenecks if item.get("event"))
        return f"{names}: {load_level} poziom obciążenia. {bottlenecks[0].get('notes', '')}".strip()
    note = str(row.get("notes") or "").strip()
    if note:
        return note
    if load_level in {"wysoki", "krytyczny"}:
        return "Wzmocnij obsadę i monitoruj kolejki w tym oknie."
    return "Standardowe monitorowanie obciążenia."
