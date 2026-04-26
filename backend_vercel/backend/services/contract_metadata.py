from __future__ import annotations

from typing import Any
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.config import get_settings


def source_metadata(
    source_type: str,
    label: str,
    confidence: float,
    is_demo: bool = False,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "label": label,
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "is_demo": is_demo,
        "notes": notes or [],
    }


def freshness_metadata(cache_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    payload = {
        "generated_at": datetime.now(ZoneInfo(settings.default_timezone)).replace(microsecond=0).isoformat(),
        "timezone": settings.default_timezone,
    }
    if cache_metadata:
        payload.update(
            {
                "cache_hit": cache_metadata.get("cache_hit"),
                "cached_at": cache_metadata.get("cached_at"),
                "expires_at": cache_metadata.get("expires_at"),
                "refresh_reason": cache_metadata.get("refresh_reason"),
            }
        )
    return payload


def public_benchmark_source(notes: list[str] | None = None) -> dict[str, Any]:
    return source_metadata(
        source_type="calibrated_demo",
        label="Public benchmark calibrated demo attendance",
        confidence=0.72,
        is_demo=True,
        notes=notes
        or [
            "Attendance values are deterministic calibrated estimates.",
            "Replace with internal gate and ticketing data in production.",
        ],
    )


def venue_profile_source() -> dict[str, Any]:
    return source_metadata(
        source_type="official_public",
        label="Venue profile from public/manifest data",
        confidence=0.86,
        is_demo=False,
        notes=["Operational assumptions should be reviewed by the venue operator before production use."],
    )
