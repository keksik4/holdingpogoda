from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.config import PROJECT_ROOT


LOGGER = logging.getLogger(__name__)
DATA_DIR = PROJECT_ROOT / "backend" / "data" / "holding_lodz"

VENUE_TO_OBJECT = {
    "aquapark_fala": "fala",
    "orientarium_zoo_lodz": "orientarium",
}

OBJECT_TO_VENUE = {value: key for key, value in VENUE_TO_OBJECT.items()}

DOW_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass(frozen=True)
class HoldingKnowledgeBase:
    baselines: dict[str, dict[str, Any]]
    weekday_multipliers: dict[str, dict[str, float]]
    month_multipliers: dict[str, dict[int, float]]
    hourly_profiles: dict[str, dict[str, list[dict[str, Any]]]]
    bottlenecks: dict[str, list[dict[str, Any]]]
    weather_rules: dict[str, list[dict[str, Any]]]
    calendar_rules: dict[str, list[dict[str, Any]]]
    sources: list[dict[str, Any]]
    loaded_from: str
    warnings: list[str]

    @property
    def is_loaded(self) -> bool:
        return not self.warnings


def object_id_for_venue(venue_slug: str) -> str:
    return VENUE_TO_OBJECT.get(venue_slug, venue_slug)


def venue_slug_for_object(object_id: str) -> str:
    return OBJECT_TO_VENUE.get(object_id, object_id)


@lru_cache(maxsize=1)
def load_holding_knowledge() -> HoldingKnowledgeBase:
    warnings: list[str] = []
    required = [
        "baselines.csv",
        "dow_multipliers.csv",
        "month_multipliers.csv",
        "hourly_profiles.csv",
        "bottlenecks.csv",
        "weather_rules.csv",
        "calendar_rules.csv",
        "sources.csv",
    ]
    missing = [name for name in required if not (DATA_DIR / name).exists()]
    if missing:
        message = f"Holding Lodz profile package missing files: {', '.join(missing)}"
        LOGGER.warning(message)
        warnings.append(message)

    baselines = {row["object_id"]: row for row in _read_csv("baselines.csv", warnings)}
    weekday_multipliers: dict[str, dict[str, float]] = {}
    for row in _read_csv("dow_multipliers.csv", warnings):
        weekday_multipliers.setdefault(row["object_id"], {})[row["dow"]] = _float(row.get("dow_factor"), 1.0)

    month_multipliers: dict[str, dict[int, float]] = {}
    for row in _read_csv("month_multipliers.csv", warnings):
        month_multipliers.setdefault(row["object_id"], {})[int(row["month"])] = _float(row.get("month_factor"), 1.0)

    hourly_profiles: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in _read_csv("hourly_profiles.csv", warnings):
        object_profiles = hourly_profiles.setdefault(row["object_id"], {})
        normalized = {
            "profile_id": row["profile_id"],
            "hour": int(row["hour"]),
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "share_of_daily_visitors": _float(row.get("share_of_daily_visitors"), 0.0),
            "occupancy_index": _float(row.get("occupancy_index"), 0.0),
            "notes": row.get("notes") or "",
            "source_refs": row.get("source_refs") or "",
            "confidence": _float(row.get("confidence"), 0.55),
        }
        object_profiles.setdefault(row["profile_id"], []).append(normalized)
    for object_profiles in hourly_profiles.values():
        for rows in object_profiles.values():
            rows.sort(key=lambda item: item["hour"])

    kb = HoldingKnowledgeBase(
        baselines=baselines,
        weekday_multipliers=weekday_multipliers,
        month_multipliers=month_multipliers,
        hourly_profiles=hourly_profiles,
        bottlenecks=_grouped_rows("bottlenecks.csv", warnings),
        weather_rules=_grouped_rows("weather_rules.csv", warnings),
        calendar_rules=_grouped_rows("calendar_rules.csv", warnings),
        sources=_read_csv("sources.csv", warnings),
        loaded_from=str(DATA_DIR),
        warnings=warnings,
    )
    _validate(kb)
    return kb


def holding_profile_for_venue(venue_slug: str) -> dict[str, Any]:
    kb = load_holding_knowledge()
    object_id = object_id_for_venue(venue_slug)
    baseline = kb.baselines.get(object_id, {})
    return {
        "venue_id": object_id,
        "venue_slug": venue_slug,
        "base_daily_visitors": int(_float(baseline.get("recommended_base_daily"), 0)),
        "baseline_confidence": _float(baseline.get("confidence"), 0.0),
        "weekday_multipliers": kb.weekday_multipliers.get(object_id, {}),
        "seasonal_multipliers": kb.month_multipliers.get(object_id, {}),
        "weather_rules": kb.weather_rules.get(object_id, []),
        "bottleneck_windows": kb.bottlenecks.get(object_id, []),
        "event_overlays": kb.calendar_rules.get(object_id, []),
        "hourly_profile_ids": sorted(kb.hourly_profiles.get(object_id, {}).keys()),
        "data_sources": ["holding_lodz_raw_profile"] if not kb.warnings else ["previous_backend_fallback"],
        "warnings": kb.warnings,
    }


def base_daily_visitors(venue_slug: str, fallback: int) -> tuple[int, float, str]:
    kb = load_holding_knowledge()
    object_id = object_id_for_venue(venue_slug)
    row = kb.baselines.get(object_id)
    if not row:
        return fallback, 0.45, "previous_backend_fallback"
    value = int(round(_float(row.get("recommended_base_daily"), fallback)))
    confidence = _float(row.get("confidence"), 0.55)
    return value, confidence, "holding_lodz_raw_profile"


def weekday_multiplier(venue_slug: str, target_date: date, is_public_holiday: bool = False) -> float:
    kb = load_holding_knowledge()
    object_id = object_id_for_venue(venue_slug)
    rows = kb.weekday_multipliers.get(object_id, {})
    if is_public_holiday and "public_holiday" in rows:
        return rows["public_holiday"]
    return rows.get(DOW_KEYS[target_date.weekday()], 1.0)


def seasonal_multiplier(venue_slug: str, target_date: date) -> float:
    kb = load_holding_knowledge()
    object_id = object_id_for_venue(venue_slug)
    return kb.month_multipliers.get(object_id, {}).get(target_date.month, 1.0)


def calendar_multiplier(venue_slug: str, target_date: date, is_public_holiday: bool = False) -> tuple[float, list[str]]:
    object_id = object_id_for_venue(venue_slug)
    rules = load_holding_knowledge().calendar_rules.get(object_id, [])
    multiplier = 1.0
    notes: list[str] = []

    if venue_slug == "aquapark_fala":
        if date(target_date.year, 6, 27) <= target_date <= date(target_date.year, 8, 31):
            multiplier *= _rule_value(rules, "school_summer_break", 1.18)
            notes.append("wakacyjna korekta popytu")
        if target_date.month == 2 and 1 <= target_date.day <= 16:
            multiplier *= min(_rule_value(rules, "lodzkie_winter_break", 1.2), 1.28)
            notes.append("ferie zimowe")
        if is_public_holiday:
            multiplier *= min(_rule_value(rules, "majowka_or_corpus_christi", 1.2), 1.28)
            notes.append("święto lub długi weekend")

    if venue_slug == "orientarium_zoo_lodz":
        if target_date.month in {7, 8}:
            multiplier *= min(_rule_value(rules, "summer_tourism", 1.18), 1.25)
            notes.append("turystyka wakacyjna")
        if target_date.month in {3, 4, 5, 6} and target_date.weekday() in {1, 2, 3}:
            multiplier *= 1.08
            notes.append("sezon wycieczek szkolnych")
        if is_public_holiday:
            multiplier *= 1.18
            notes.append("święto lub długi weekend")

    return round(_clamp(multiplier, 0.85, 1.45), 4), notes


def weather_multiplier(venue_slug: str, consensus: dict[str, Any]) -> tuple[float, str, list[str]]:
    temp = _first_number(consensus, "temperatureC", "temperature_avg")
    apparent = _first_number(consensus, "apparentTemperatureC", "apparent_temperature_avg") or temp
    rain_prob = _first_number(consensus, "precipitationProbability", "precipitation_probability_avg") or 0
    precipitation = _first_number(consensus, "precipitationMm", "precipitation_avg") or 0
    wind = _first_number(consensus, "windSpeedKmh", "wind_speed_avg") or 0
    condition = str(consensus.get("conditionGroup") or consensus.get("weather_icon_key") or "").lower()
    storm_risk = 1.0 if condition == "storm" or rain_prob >= 85 or wind >= 55 else 0.0
    notes: list[str] = []

    if venue_slug == "aquapark_fala":
        factor = 1.0
        if temp is not None and temp > 30 and storm_risk < 0.3:
            factor *= 1.18
            notes.append("bardzo ciepło: mocny popyt na strefy wodne")
        elif temp is not None and temp > 25 and rain_prob < 40:
            factor *= 1.42
            notes.append("ciepło i sucho: wysoki popyt na strefę zewnętrzną")
        elif temp is not None and temp < 10:
            factor *= 0.94
            notes.append("chłodno: słabszy popyt rodzinny, mocniejsze sauny")
        if storm_risk >= 0.6:
            factor *= 0.68
            notes.append("burze lub silny opad obniżają komfort stref zewnętrznych")
        elif precipitation > 1 and temp is not None and temp > 20:
            factor *= 0.92
            notes.append("ciepły deszcz ogranicza zewnętrzne strefy, ale obiekt działa wewnątrz")
        elif rain_prob > 60:
            factor *= 0.90
            notes.append("ryzyko opadu obniża decyzje spontaniczne")
        if apparent is not None and apparent >= 28 and rain_prob < 45:
            factor *= 1.06
            notes.append("wysoka temperatura odczuwalna")
        return round(_clamp(factor, 0.58, 1.72), 4), _weather_impact_label(factor), notes

    factor = 1.0
    if storm_risk >= 0.6:
        factor *= 0.86
        notes.append("silna burza obniża komfort dojazdu")
    elif rain_prob > 50 or (temp is not None and temp < 8):
        factor *= 1.08
        notes.append("gorsza pogoda wzmacnia atrakcyjność pawilonów Orientarium")
    if temp is not None and 12 <= temp <= 26 and rain_prob < 30 and condition in {"sun", "sunny", "partly_cloudy", "mixed"}:
        factor *= 1.12
        notes.append("łagodna pogoda wspiera część zewnętrzną i wizyty rodzinne")
    if temp is not None and temp > 30:
        factor *= 0.98
        notes.append("upał lekko obniża komfort ogrodu, ale sezon wakacyjny utrzymuje popyt")
    return round(_clamp(factor, 0.78, 1.22), 4), _weather_impact_label(factor), notes


def select_hourly_profile(venue_slug: str, target_date: date, consensus: dict[str, Any]) -> tuple[str, list[dict[str, Any]], str]:
    kb = load_holding_knowledge()
    object_id = object_id_for_venue(venue_slug)
    profiles = kb.hourly_profiles.get(object_id, {})
    temp = _first_number(consensus, "temperatureC", "temperature_avg")
    rain_prob = _first_number(consensus, "precipitationProbability", "precipitation_probability_avg") or 0
    weekend = target_date.weekday() >= 5

    if venue_slug == "aquapark_fala":
        if target_date.month in {6, 7, 8} and temp is not None and temp >= 24 and rain_prob < 50:
            profile_id = "summer_hot_external_zone_08_22"
        elif weekend:
            profile_id = "weekend_holiday_standard_09_22"
        elif target_date.weekday() in {1, 2, 3, 4}:
            profile_id = "weekday_morning_swim_07_22"
        else:
            profile_id = "weekday_standard_09_22"
    else:
        if target_date.month in {7, 8}:
            profile_id = "summer_tourism_09_19"
        elif weekend:
            profile_id = "weekend_holiday_09_19"
        elif target_date.month in {3, 4, 5, 6} and target_date.weekday() in {1, 2, 3}:
            profile_id = "weekday_school_trip_season_09_19"
        else:
            profile_id = "weekday_quiet_09_19"

    rows = profiles.get(profile_id) or next(iter(profiles.values()), [])
    if not rows:
        return "previous_backend_fallback", [], "previous_backend_fallback"
    return profile_id, rows, "holding_lodz_raw_profile"


def bottlenecks_for_hour(venue_slug: str, hour: int) -> list[dict[str, Any]]:
    object_id = object_id_for_venue(venue_slug)
    matches = []
    for row in load_holding_knowledge().bottlenecks.get(object_id, []):
        if _time_applies(row.get("time", ""), hour):
            matches.append(row)
    return matches


def source_summary() -> dict[str, Any]:
    kb = load_holding_knowledge()
    return {
        "loaded": not kb.warnings,
        "loaded_from": kb.loaded_from,
        "warnings": kb.warnings,
        "source_count": len(kb.sources),
        "sources": kb.sources[:12],
    }


def _read_csv(filename: str, warnings: list[str]) -> list[dict[str, str]]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception as exc:  # noqa: BLE001
        message = f"Could not load Holding Lodz data file {filename}: {exc}"
        LOGGER.warning(message)
        warnings.append(message)
        return []


def _grouped_rows(filename: str, warnings: list[str]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in _read_csv(filename, warnings):
        normalized = dict(row)
        for key in ["min_multiplier", "max_multiplier", "local_multiplier", "multiplier_or_overlay", "confidence"]:
            if key in normalized:
                normalized[key] = _float(normalized.get(key), 1.0 if "multiplier" in key else 0.55)
        grouped.setdefault(row["object_id"], []).append(normalized)
    return grouped


def _validate(kb: HoldingKnowledgeBase) -> None:
    for object_id in ["fala", "orientarium"]:
        if object_id not in kb.baselines:
            LOGGER.warning("Holding Lodz baseline missing for %s", object_id)
        if object_id not in kb.hourly_profiles:
            LOGGER.warning("Holding Lodz hourly profiles missing for %s", object_id)


def _float(value: Any, default: float) -> float:
    if value in {None, ""}:
        return default
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _first_number(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _rule_value(rules: list[dict[str, Any]], feature: str, default: float) -> float:
    for row in rules:
        if row.get("feature") == feature:
            return _float(row.get("multiplier_or_overlay"), default)
    return default


def _time_applies(value: str, hour: int) -> bool:
    if not value:
        return False
    if "-" in value:
        start, end = value.split("-", 1)
        return _hour(start) <= hour < _hour(end)
    return _hour(value) == hour


def _hour(value: str) -> int:
    return int(value.strip()[:2])


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _weather_impact_label(factor: float) -> str:
    if factor >= 1.15:
        return "silnie zwiększa popyt"
    if factor >= 1.04:
        return "lekko zwiększa popyt"
    if factor <= 0.88:
        return "obniża popyt"
    if factor <= 0.96:
        return "lekko obniża popyt"
    return "neutralny wpływ"
