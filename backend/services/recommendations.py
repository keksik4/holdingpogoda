import json
import re
from datetime import date
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from backend.models.business_models import AttendanceRecord
from backend.models.forecast_models import ForecastRecord, RecommendationRecord
from backend.services.forecasting import build_forecast, get_latest_forecast


def generate_recommendations(
    db: Session,
    business_view: str,
    horizon: str = "operational",
    facility_profile: str = "mixed",
) -> dict[str, Any]:
    business_view = business_view if business_view in {"management", "operations", "marketing"} else "management"
    rows = get_latest_forecast(db, horizon=horizon, facility_profile=facility_profile)
    if not rows:
        build_forecast(db, horizon=horizon, facility_profile=facility_profile)
        rows = get_latest_forecast(db, horizon=horizon, facility_profile=facility_profile)
    if business_view == "management":
        payload = _management_view(db, rows, horizon, facility_profile)
    elif business_view == "operations":
        payload = _operations_view(rows, horizon, facility_profile)
    else:
        payload = _marketing_view(rows, horizon, facility_profile)
    db.query(RecommendationRecord).filter(
        RecommendationRecord.business_view == business_view,
        RecommendationRecord.horizon == horizon,
        RecommendationRecord.facility_profile == facility_profile,
    ).delete()
    record = RecommendationRecord(
        business_view=business_view,
        horizon=horizon,
        facility_profile=facility_profile,
        title=payload["title"],
        summary=payload["executive_summary"] if business_view == "management" else payload["summary"],
        priority=payload["priority"],
        payload_json=json.dumps(payload, ensure_ascii=False),
        is_demo=payload["demo_mode"],
    )
    db.add(record)
    db.commit()
    return payload


def _management_view(db: Session, rows: list[dict[str, Any]], horizon: str, facility_profile: str) -> dict[str, Any]:
    total_expected = sum(item["expected_visitors"] for item in rows)
    total_low = sum(item["low_scenario"] for item in rows)
    total_high = sum(item["high_scenario"] for item in rows)
    total_revenue = sum(item["expected_revenue"] for item in rows)
    historical_avg = _historical_average_for_span(db, rows)
    comparison = ((total_expected - historical_avg) / historical_avg * 100) if historical_avg else 0.0
    avg_confidence = mean([item["confidence_score"] for item in rows]) if rows else 0
    risks = []
    opportunities = []
    if avg_confidence < 0.55:
        risks.append("Forecast confidence is limited; use low/base/high scenarios for staffing and campaign spend.")
    if comparison > 20:
        opportunities.append("Visitor demand is materially above the historical average; prepare upsell and queue capacity.")
    if comparison < -15:
        risks.append("Expected demand is below historical average; consider targeted offers and cost control.")
    if any(item["provider_disagreement_score"] > 0.45 for item in rows):
        risks.append("Weather providers disagree on some periods; scenario planning is recommended.")
    if not opportunities:
        opportunities.append("Demand is within a manageable range; optimize revenue per visitor through bundles and timed offers.")
    priority = "high" if comparison > 20 or avg_confidence < 0.5 else "medium"
    return {
        "title": f"Management forecast for {horizon} planning",
        "priority": priority,
        "horizon": horizon,
        "facility_profile": facility_profile,
        "expected_visitors": round(total_expected, 0),
        "low_scenario": round(total_low, 0),
        "base_scenario": round(total_expected, 0),
        "high_scenario": round(total_high, 0),
        "expected_revenue_estimate": round(total_revenue, 2),
        "comparison_to_historical_average_percent": round(comparison, 1),
        "risks": risks,
        "opportunities": opportunities,
        "executive_summary": (
            f"Expected attendance is {round(total_expected):,.0f} visitors for the {horizon} horizon. "
            f"This is {round(comparison, 1)}% versus comparable historical demand, with average confidence {round(avg_confidence, 2)}."
        ),
        "demo_mode": any(item["is_demo"] for item in rows),
    }


def _operations_view(rows: list[dict[str, Any]], horizon: str, facility_profile: str) -> dict[str, Any]:
    peak_rows = sorted(rows, key=lambda item: item["expected_visitors"], reverse=True)[:8]
    avg = mean([item["expected_visitors"] for item in rows]) if rows else 0
    alerts = []
    checklist = [
        "Confirm staffing roster against peak forecast",
        "Check queue lane opening plan",
        "Confirm parking overflow plan",
        "Prepare cleaning and security shift coverage",
        "Align gastronomy preparation with high scenario",
    ]
    max_visitors = peak_rows[0]["expected_visitors"] if peak_rows else 0
    queue_risk = _risk_level(max_visitors, avg, 1.25)
    parking_risk = _risk_level(max_visitors, avg, 1.35)
    gastronomy_load = _risk_level(max_visitors, avg, 1.15)
    if queue_risk == "high":
        alerts.append("Expected visitors exceed normal operating load; open additional entry lanes before the peak.")
    if any(item["confidence_score"] < 0.55 for item in peak_rows):
        alerts.append("Some peak periods have low confidence; keep standby staffing available.")
    staffing = _staffing_recommendation(max_visitors, facility_profile)
    return {
        "title": f"Operations plan for {horizon}",
        "priority": "high" if queue_risk == "high" or parking_risk == "high" else "medium",
        "summary": f"Peak expected load is {round(max_visitors)} visitors. Staffing recommendation: {staffing}.",
        "predicted_peak_days_and_hours": peak_rows,
        "staffing_recommendation": staffing,
        "queue_risk": queue_risk,
        "parking_risk": parking_risk,
        "gastronomy_load": gastronomy_load,
        "infrastructure_readiness_checklist": checklist,
        "alerts": alerts,
        "horizon": horizon,
        "facility_profile": facility_profile,
        "demo_mode": any(item["is_demo"] for item in rows),
    }


def _marketing_view(rows: list[dict[str, Any]], horizon: str, facility_profile: str) -> dict[str, Any]:
    candidates = sorted(
        rows,
        key=lambda item: (item["confidence_score"], item["expected_visitors"], -item["provider_disagreement_score"]),
        reverse=True,
    )[:10]
    rainy_high = [
        item
        for item in rows
        if item["expected_visitors"] > _average_expected(rows) * 1.15
        and _precipitation_from_summary(item.get("weather_summary")) >= 2.0
    ]
    low_confidence = [item for item in rows if item["confidence_score"] < 0.55]
    if facility_profile == "outdoor":
        angle = "Weather-window family offer focused on sunny, dry outdoor activity."
        segment = "families, groups, and day-trip visitors"
    elif facility_profile == "indoor":
        angle = "Bad-weather backup plan and comfortable indoor entertainment."
        segment = "families, teens, and groups seeking reliable plans"
    else:
        angle = "Flexible plan: outdoor fun when weather is good, indoor fallback when it changes."
        segment = "families and mixed-age groups"
    recommendations = []
    if candidates:
        recommendations.append("Increase campaign budget on high-confidence days with above-average expected visitors.")
    if rainy_high:
        recommendations.append("Use indoor-focused messaging when rain risk overlaps with high demand.")
    if low_confidence:
        recommendations.append("Avoid large media commitments on low-confidence days; use smaller short-term boosts.")
    if not recommendations:
        recommendations.append("Keep spend steady and use weather-specific creative variants.")
    wasted_spend_risk = "high" if len(low_confidence) > max(2, len(rows) * 0.25) else "medium" if low_confidence else "low"
    return {
        "title": f"Marketing plan for {horizon}",
        "priority": "high" if candidates and wasted_spend_risk == "low" else "medium",
        "summary": f"Best campaign angle: {angle}",
        "best_days_to_increase_campaign_budget": candidates,
        "suggested_communication_angle": angle,
        "weather_based_campaign_recommendation": recommendations,
        "target_segment_suggestion": segment,
        "risk_of_wasted_campaign_spend": wasted_spend_risk,
        "horizon": horizon,
        "facility_profile": facility_profile,
        "demo_mode": any(item["is_demo"] for item in rows),
    }


def _historical_average_for_span(db: Session, rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    unique_dates = {date.fromisoformat(item["target_date"]) for item in rows}
    comparable_weekdays = {target.weekday() for target in unique_dates}
    attendance = db.query(AttendanceRecord).all()
    daily = {}
    for row in attendance:
        if row.date.weekday() in comparable_weekdays:
            daily[row.date] = daily.get(row.date, 0) + row.visitors
    if not daily:
        return 0.0
    daily_values = list(daily.values())
    days_needed = len(unique_dates)
    return float(mean(daily_values) * days_needed)


def _staffing_recommendation(max_visitors: float, facility_profile: str) -> str:
    base_staff = max(6, int(max_visitors / 45))
    if facility_profile == "outdoor":
        base_staff += 3
    elif facility_profile == "indoor":
        base_staff += 1
    return f"{base_staff} core staff plus {max(2, int(base_staff * 0.25))} standby staff for peak periods"


def _risk_level(value: float, average: float, threshold: float) -> str:
    if average <= 0:
        return "medium"
    ratio = value / average
    if ratio >= threshold:
        return "high"
    if ratio >= threshold * 0.88:
        return "medium"
    return "low"


def _average_expected(rows: list[dict[str, Any]]) -> float:
    return mean([item["expected_visitors"] for item in rows]) if rows else 0.0


def _precipitation_from_summary(summary: str | None) -> float:
    if not summary:
        return 0.0
    match = re.search(r"precipitation ([0-9]+(?:\.[0-9]+)?) mm", summary)
    return float(match.group(1)) if match else 0.0
