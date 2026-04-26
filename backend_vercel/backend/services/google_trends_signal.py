from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from backend.config import PROJECT_ROOT


TREND_QUERIES = {
    "aquapark_fala": ["Aquapark Fala", "Fala Łódź", "basen Łódź", "aquapark Łódź"],
    "orientarium_zoo_lodz": ["Orientarium Łódź", "Zoo Łódź", "Orientarium", "zoo Łódź bilety"],
}

RAW_TRENDS_DIR = PROJECT_ROOT / "data" / "raw" / "google_trends"
PROCESSED_TRENDS_DIR = PROJECT_ROOT / "data" / "processed" / "google_trends"


def get_trend_signals(
    venue_slug: str,
    start_date: date | None = None,
    end_date: date | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    processed_path = PROCESSED_TRENDS_DIR / f"{venue_slug}_daily_trends.csv"
    if refresh:
        _try_fetch_pytrends(venue_slug, processed_path)
    if processed_path.exists():
        df = pd.read_csv(processed_path)
        if start_date:
            df = df[pd.to_datetime(df["date"]).dt.date >= start_date]
        if end_date:
            df = df[pd.to_datetime(df["date"]).dt.date <= end_date]
        return {
            "venue_slug": venue_slug,
            "status": "cached_google_trends_signal",
            "queries": TREND_QUERIES[venue_slug],
            "items": df.to_dict(orient="records"),
            "data_quality_label": "Google Trends signal",
            "note": "Relative demand signal only; not direct visitor counts.",
        }
    fallback = _fallback_trends(venue_slug, start_date, end_date)
    return {
        "venue_slug": venue_slug,
        "status": "pytrends_unavailable_or_not_refreshed",
        "queries": TREND_QUERIES[venue_slug],
        "items": fallback.to_dict(orient="records"),
        "data_quality_label": "Source missing",
        "note": "pytrends is optional. Neutral/seasonal fallback values are used for calibrated demo generation.",
    }


def trend_score_by_date(venue_slug: str, start_date: date, end_date: date) -> dict[str, float]:
    payload = get_trend_signals(venue_slug, start_date, end_date, refresh=False)
    return {str(row["date"]): float(row["trend_signal_score"]) for row in payload["items"]}


def _try_fetch_pytrends(venue_slug: str, processed_path: Path) -> None:
    try:
        from pytrends.request import TrendReq  # type: ignore
    except Exception:  # noqa: BLE001
        return
    PROCESSED_TRENDS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_TRENDS_DIR.mkdir(parents=True, exist_ok=True)
    pytrends = TrendReq(hl="pl-PL", tz=60)
    pytrends.build_payload(TREND_QUERIES[venue_slug], geo="PL", timeframe="today 12-m")
    interest = pytrends.interest_over_time()
    if interest.empty:
        return
    raw_path = RAW_TRENDS_DIR / f"{venue_slug}_interest_over_time.csv"
    interest.to_csv(raw_path)
    score = interest.drop(columns=["isPartial"], errors="ignore").mean(axis=1).reset_index()
    score.columns = ["date", "trend_signal_score"]
    score["date"] = pd.to_datetime(score["date"]).dt.date
    score["trend_signal_score"] = score["trend_signal_score"].clip(lower=0, upper=100).round(2)
    score.to_csv(processed_path, index=False)


def _fallback_trends(venue_slug: str, start_date: date | None, end_date: date | None) -> pd.DataFrame:
    start = start_date or date(date.today().year, 1, 1)
    end = end_date or date(date.today().year, 12, 31)
    dates = pd.date_range(start=start, end=end, freq="D")
    rows = []
    for current in dates:
        month = current.month
        if venue_slug == "aquapark_fala":
            score = 62 if month in {6, 7, 8} else 54 if month in {1, 2, 12} else 48
        else:
            score = 66 if month in {5, 6, 7, 8} else 56 if month in {4, 9, 10} else 42
        rows.append({"date": current.date().isoformat(), "trend_signal_score": float(score)})
    return pd.DataFrame(rows)
