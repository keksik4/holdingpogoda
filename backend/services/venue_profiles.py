import json
from pathlib import Path
from typing import Any

from backend.config import PROJECT_ROOT
from backend.services.contract_metadata import freshness_metadata, venue_profile_source
from backend.services.official_assets import get_asset_for_venue


VENUE_PROFILE_PATH = PROJECT_ROOT / "data" / "sources" / "venue_profiles.json"


def load_venue_profiles() -> list[dict[str, Any]]:
    with VENUE_PROFILE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def list_venue_profiles() -> list[dict[str, Any]]:
    return load_venue_profiles()


def get_venue_profile(venue_slug: str) -> dict[str, Any]:
    for venue in load_venue_profiles():
        if venue["venue_slug"] == venue_slug:
            return venue
    raise ValueError(f"Unknown venue_slug: {venue_slug}. Expected one of: {', '.join(venue_slugs())}.")


def venue_slugs() -> list[str]:
    return [venue["venue_slug"] for venue in load_venue_profiles()]


def venue_summary_for_frontend(venue: dict[str, Any]) -> dict[str, Any]:
    asset = get_asset_for_venue(venue["venue_slug"])
    return {
        "name": venue["name"],
        "slug": venue["venue_slug"],
        "type": venue["type"],
        "city": venue["city"],
        "address": venue["address"],
        "short_description": venue["description"],
        "weather_sensitivity_label": weather_sensitivity_label(venue["weather_profile"]),
        "image_asset_status": {
            "usage_status": asset["usage_status"],
            "local_path": asset["local_path"],
            "source_name": asset["source_name"],
            "license_notes": asset["license_notes"],
        },
        "data_quality_label": venue["data_quality_status"],
    }


def venue_profile_contract(venue_slug: str) -> dict[str, Any]:
    venue = get_venue_profile(venue_slug).copy()
    venue["source_metadata"] = venue_profile_source()
    venue["freshness_metadata"] = freshness_metadata()
    return venue


def weather_sensitivity_label(weather_profile: str) -> str:
    labels = {
        "mixed_weather_sensitive": "Mixed weather sensitivity",
        "outdoor_heavy_with_indoor_resilience": "Outdoor-heavy with indoor resilience",
    }
    return labels.get(weather_profile, "Weather-sensitive")
