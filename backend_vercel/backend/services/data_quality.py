from typing import Any

from backend.services.official_assets import get_asset_for_venue
from backend.services.public_source_research import load_public_benchmarks, sources_for_venue


QUALITY_LABELS = {
    "official_public_benchmark": "Official public benchmark",
    "real_weather_api": "Real weather API",
    "google_trends_signal": "Google Trends signal",
    "calibrated_demo_attendance": "Calibrated demo attendance",
    "manual_venue_asset": "Manual venue asset",
    "source_missing": "Source missing",
}


def venue_data_quality(venue_slug: str) -> dict[str, Any]:
    benchmarks = load_public_benchmarks(venue_slug)
    asset = get_asset_for_venue(venue_slug)
    return {
        "venue_slug": venue_slug,
        "labels": [
            QUALITY_LABELS["official_public_benchmark"] if benchmarks else QUALITY_LABELS["source_missing"],
            QUALITY_LABELS["real_weather_api"],
            QUALITY_LABELS["calibrated_demo_attendance"],
            QUALITY_LABELS["manual_venue_asset"] if asset.get("file_exists") else QUALITY_LABELS["source_missing"],
        ],
        "attendance": {
            "label": QUALITY_LABELS["calibrated_demo_attendance"],
            "note": "Daily and hourly visitor values are generated from public benchmarks and assumptions, not internal ticketing data.",
        },
        "benchmarks": {
            "label": QUALITY_LABELS["official_public_benchmark"] if benchmarks else QUALITY_LABELS["source_missing"],
            "count": len(benchmarks),
        },
        "weather": {
            "label": QUALITY_LABELS["real_weather_api"],
            "note": "Weather endpoints use Open-Meteo, MET Norway, IMGW where available, and consensus scoring.",
        },
        "trends": {
            "label": QUALITY_LABELS["google_trends_signal"],
            "note": "Optional relative demand signal; never interpreted as direct visitor counts.",
        },
        "assets": {
            "label": QUALITY_LABELS["manual_venue_asset"] if asset.get("file_exists") else QUALITY_LABELS["source_missing"],
            "usage_status": asset.get("usage_status"),
            "expected_local_path": asset.get("local_path"),
        },
        "sources": sources_for_venue(venue_slug),
    }


def data_quality_label(is_calibrated_demo: bool = True) -> str:
    return QUALITY_LABELS["calibrated_demo_attendance"] if is_calibrated_demo else "Imported internal attendance"
