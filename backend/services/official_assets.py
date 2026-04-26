import json
from pathlib import Path
from typing import Any

from backend.config import PROJECT_ROOT


ASSET_MANIFEST_PATH = PROJECT_ROOT / "data" / "sources" / "asset_manifest.json"


def load_asset_manifest() -> list[dict[str, Any]]:
    with ASSET_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        assets = json.load(handle)
    return [_with_local_status(asset) for asset in assets]


def get_assets_for_venue(venue_slug: str) -> list[dict[str, Any]]:
    return [asset for asset in load_asset_manifest() if asset["venue_slug"] == venue_slug]


def get_asset_for_venue(venue_slug: str) -> dict[str, Any]:
    assets = get_assets_for_venue(venue_slug)
    if not assets:
        return {
            "venue_slug": venue_slug,
            "asset_type": "venue_photo",
            "local_path": "",
            "source_url": "",
            "source_name": "",
            "attribution": "No asset manifest row exists yet.",
            "license_notes": "Source missing.",
            "usage_status": "source_missing",
            "file_exists": False,
        }
    return assets[0]


def _with_local_status(asset: dict[str, Any]) -> dict[str, Any]:
    local_path = PROJECT_ROOT / asset["local_path"]
    asset = asset.copy()
    asset["file_exists"] = local_path.exists()
    if asset["usage_status"] == "missing_manual_asset" and local_path.exists():
        asset["usage_status"] = "manual_asset_available"
    return asset
