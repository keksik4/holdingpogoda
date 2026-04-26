from datetime import date, timedelta
from pathlib import Path
import math
import random

import pandas as pd

from backend.config import PROJECT_ROOT


FACILITY_ZONES = ["outdoor", "indoor", "mixed"]


def create_sample_csv_files(force: bool = False) -> dict[str, str]:
    sample_dir = PROJECT_ROOT / "data" / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    attendance_path = sample_dir / "attendance_sample.csv"
    events_path = sample_dir / "events_sample.csv"
    campaigns_path = sample_dir / "campaigns_sample.csv"
    if force or not attendance_path.exists():
        _attendance_frame().to_csv(attendance_path, index=False)
    if force or not events_path.exists():
        _events_frame().to_csv(events_path, index=False)
    if force or not campaigns_path.exists():
        _campaigns_frame().to_csv(campaigns_path, index=False)
    return {
        "attendance": str(attendance_path),
        "events": str(events_path),
        "campaigns": str(campaigns_path),
    }


def _attendance_frame() -> pd.DataFrame:
    random.seed(42)
    rows = []
    start = date.today() - timedelta(days=180)
    open_hours = range(9, 21)
    for day_index in range(180):
        current = start + timedelta(days=day_index)
        weekday = current.weekday()
        month = current.month
        weekend_multiplier = 1.55 if weekday >= 5 else 1.0
        summer_multiplier = 1.35 if month in {6, 7, 8} else 1.0
        shoulder_multiplier = 1.15 if month in {4, 5, 9, 10} else 0.88 if month in {1, 2, 11, 12} else 1.0
        holiday_hint = 1.25 if (current.day in {1, 3, 15} and month in {1, 5, 8, 11}) else 1.0
        weather_wave = 1 + 0.18 * math.sin(day_index / 10) + 0.08 * math.cos(day_index / 4)
        for hour in open_hours:
            hour_peak = 1 + 0.7 * math.exp(-((hour - 14) ** 2) / 9)
            base = 26 * weekend_multiplier * summer_multiplier * shoulder_multiplier * holiday_hint * weather_wave * hour_peak
            zone = "mixed"
            if hour in {10, 11, 12, 13, 14, 15, 16} and month in {5, 6, 7, 8, 9}:
                zone = "outdoor"
            if month in {1, 2, 11, 12} or hour >= 18:
                zone = "indoor"
            visitors = max(4, int(random.gauss(base, base * 0.12)))
            online_share = 0.62 if weekday >= 5 else 0.52
            tickets_online = int(visitors * online_share)
            tickets_offline = visitors - tickets_online
            rows.append(
                {
                    "date": current.isoformat(),
                    "hour": hour,
                    "visitors": visitors,
                    "tickets_online": tickets_online,
                    "tickets_offline": tickets_offline,
                    "revenue_tickets": round(visitors * random.uniform(32, 48), 2),
                    "revenue_gastro": round(visitors * random.uniform(9, 23), 2),
                    "revenue_parking": round(visitors * random.uniform(2.5, 7.5), 2),
                    "facility_zone": zone,
                    "notes": "DEMO synthetic attendance for Pogoda w Łodzi MVP",
                }
            )
    return pd.DataFrame(rows)


def _events_frame() -> pd.DataFrame:
    today = date.today()
    rows = [
        (today - timedelta(days=142), "Spring family opening", 0.18, "seasonal", "outdoor", "DEMO event"),
        (today - timedelta(days=91), "Outdoor music afternoon", 0.24, "concert", "outdoor", "DEMO event"),
        (today - timedelta(days=56), "Rainy day indoor tournament", 0.16, "competition", "indoor", "DEMO event"),
        (today - timedelta(days=21), "Weekend food trucks", 0.21, "food", "mixed", "DEMO event"),
        (today + timedelta(days=5), "Forecast-aware family weekend", 0.20, "family", "mixed", "DEMO future event"),
        (today + timedelta(days=17), "Indoor challenge day", 0.14, "competition", "indoor", "DEMO future event"),
        (today + timedelta(days=44), "Summer preview festival", 0.26, "festival", "outdoor", "DEMO future event"),
        (today + timedelta(days=83), "Late summer night opening", 0.19, "special_hours", "mixed", "DEMO future event"),
    ]
    return pd.DataFrame(
        rows,
        columns=["date", "event_name", "expected_impact", "event_type", "indoor_or_outdoor", "notes"],
    )


def _campaigns_frame() -> pd.DataFrame:
    today = date.today()
    rows = [
        (
            today - timedelta(days=160),
            today - timedelta(days=135),
            "DEMO spring warm-up",
            "social",
            7000,
            "families",
            "early season offer",
            0.08,
            "clearly fake sample campaign",
        ),
        (
            today - timedelta(days=75),
            today - timedelta(days=45),
            "DEMO weather-proof fun",
            "search",
            9500,
            "teens and groups",
            "indoor backup message",
            0.11,
            "clearly fake sample campaign",
        ),
        (
            today - timedelta(days=12),
            today + timedelta(days=10),
            "DEMO short-term family boost",
            "social",
            5200,
            "families",
            "weekend weather push",
            0.09,
            "clearly fake sample campaign",
        ),
        (
            today + timedelta(days=20),
            today + timedelta(days=50),
            "DEMO summer pre-sale",
            "newsletter",
            12000,
            "season-pass prospects",
            "sunny day bundle",
            0.13,
            "clearly fake sample campaign",
        ),
        (
            today + timedelta(days=70),
            today + timedelta(days=110),
            "DEMO groups and companies",
            "display",
            16000,
            "corporate groups",
            "weather-stable group planning",
            0.10,
            "clearly fake sample campaign",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "date_start",
            "date_end",
            "campaign_name",
            "channel",
            "budget_pln",
            "target_segment",
            "message_type",
            "expected_impact",
            "notes",
        ],
    )
