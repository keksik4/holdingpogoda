from typing import Any

import pandas as pd

from backend.config import PROJECT_ROOT


EVENTS_REALISTIC_PATH = PROJECT_ROOT / "data" / "sample" / "events_realistic.csv"


def load_realistic_events(venue_slug: str | None = None) -> list[dict[str, Any]]:
    df = pd.read_csv(EVENTS_REALISTIC_PATH)
    if venue_slug:
        df = df[df["venue_slug"] == venue_slug]
    return df.fillna("").to_dict(orient="records")


def event_impact_by_date(venue_slug: str) -> dict[str, float]:
    events = load_realistic_events(venue_slug)
    impact: dict[str, float] = {}
    for event in events:
        impact[event["date"]] = impact.get(event["date"], 0.0) + float(event["expected_impact"])
    return impact
