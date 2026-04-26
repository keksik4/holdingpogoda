import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from backend.config import PROJECT_ROOT
from backend.services.app_context import date_relation, warsaw_now


CACHE_DIR = PROJECT_ROOT / "data" / "processed" / "weather_cache"
CACHE_VERSION = "weather-openweather-openmeteo-consensus-v4"


def cache_ttl_minutes(target_date: date, provider_failed: bool = False) -> int:
    if provider_failed:
        return 15
    relation = date_relation(target_date)
    if relation == "today":
        return 45
    if relation == "forecast":
        return 240
    return 10080


def cache_path(kind: str, venue_slug: str, target_date: date) -> Path:
    safe_kind = kind.replace("/", "_")
    return CACHE_DIR / safe_kind / venue_slug / f"{target_date.isoformat()}.json"


def read_cache(kind: str, venue_slug: str, target_date: date, force: bool = False) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    path = cache_path(kind, venue_slug, target_date)
    if force or not path.exists():
        return None, {"cache_hit": False, "refresh_reason": "force" if force else "cache_miss"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("cache_metadata", {}).get("cache_version") != CACHE_VERSION:
            return None, {"cache_hit": False, "refresh_reason": "cache_version_changed"}
        expires_at = datetime.fromisoformat(payload["cache_metadata"]["expires_at"])
        if expires_at < warsaw_now():
            return None, payload["cache_metadata"] | {"cache_hit": False, "refresh_reason": "expired"}
        return payload, payload["cache_metadata"] | {"cache_hit": True, "refresh_reason": "cache_hit"}
    except Exception as exc:  # noqa: BLE001
        return None, {"cache_hit": False, "refresh_reason": f"cache_read_error: {exc}"}


def write_cache(
    kind: str,
    venue_slug: str,
    target_date: date,
    payload: dict[str, Any],
    provider_failed: bool = False,
    refresh_reason: str = "refreshed",
) -> dict[str, Any]:
    now = warsaw_now()
    expires_at = now + timedelta(minutes=cache_ttl_minutes(target_date, provider_failed=provider_failed))
    metadata = {
        "cache_hit": False,
        "cached_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "refresh_reason": refresh_reason,
        "cache_version": CACHE_VERSION,
    }
    path = cache_path(kind, venue_slug, target_date)
    payload = payload | {"cache_metadata": metadata}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except OSError as exc:
        payload["cache_metadata"] = payload["cache_metadata"] | {
            "cache_write_status": "skipped",
            "cache_write_error": str(exc),
        }
    return payload
