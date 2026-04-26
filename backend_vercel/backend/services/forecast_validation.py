from __future__ import annotations

from typing import Any


def clamp_daily_visitors(venue_slug: str, visitors: int) -> int:
    bounds = {
        "aquapark_fala": (450, 18500),
        "orientarium_zoo_lodz": (250, 13500),
    }
    minimum, maximum = bounds.get(venue_slug, (100, 20000))
    return max(minimum, min(maximum, int(visitors)))


def scenario_range(base: int, confidence: float, weather_risk: str) -> dict[str, int]:
    risk_uncertainty = {"low": 0.08, "medium": 0.13, "high": 0.20, "unknown": 0.18}.get(weather_risk, 0.15)
    uncertainty = max(risk_uncertainty, 0.08 + (1 - confidence) * 0.16)
    return {
        "low": max(0, int(round(base * (1 - uncertainty)))),
        "base": int(base),
        "high": int(round(base * (1 + uncertainty))),
    }


def validate_hourly_curve(total: int, curve: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not curve:
        return curve
    current_total = sum(int(item.get("expected_visitors", 0)) for item in curve)
    if current_total != total:
        difference = total - current_total
        order = sorted(range(len(curve)), key=lambda index: curve[index].get("expected_visitors", 0), reverse=True)
        cursor = 0
        step = 1 if difference > 0 else -1
        while difference != 0 and order:
            index = order[cursor % len(order)]
            next_value = int(curve[index]["expected_visitors"]) + step
            if next_value >= 0:
                curve[index]["expected_visitors"] = next_value
                difference -= step
            cursor += 1
    peak_limit = max(1, int(round(total * 0.18)))
    for item in curve:
        item["expected_visitors"] = min(int(item["expected_visitors"]), peak_limit)
    current_total = sum(int(item.get("expected_visitors", 0)) for item in curve)
    if current_total != total:
        difference = total - current_total
        order = sorted(range(len(curve)), key=lambda index: curve[index].get("expected_visitors", 0))
        cursor = 0
        while difference > 0 and order:
            index = order[cursor % len(order)]
            if curve[index]["expected_visitors"] < peak_limit:
                curve[index]["expected_visitors"] += 1
                difference -= 1
            cursor += 1
            if cursor > len(order) * max(peak_limit, 1):
                break
    peak = max((int(item["expected_visitors"]) for item in curve), default=0)
    for item in curve:
        item["peak_hour_flag"] = bool(peak and int(item["expected_visitors"]) >= peak * 0.92)
    return curve


def calendar_day_is_best_candidate(day: dict[str, Any], threshold: int) -> bool:
    return bool(
        day["expected_visitors"] >= threshold
        and day.get("weather_risk") != "high"
        and day.get("confidence_score", 0) >= 0.55
    )
