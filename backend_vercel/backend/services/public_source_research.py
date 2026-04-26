import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.config import PROJECT_ROOT


SOURCE_DIR = PROJECT_ROOT / "data" / "sources"
BENCHMARK_PATH = SOURCE_DIR / "public_benchmarks.csv"
SOURCE_MANIFEST_PATH = SOURCE_DIR / "source_manifest.json"


def load_public_benchmarks(venue_slug: str | None = None) -> list[dict[str, Any]]:
    df = pd.read_csv(BENCHMARK_PATH)
    if venue_slug:
        df = df[df["venue_slug"] == venue_slug]
    return df.fillna("").to_dict(orient="records")


def load_source_manifest() -> list[dict[str, Any]]:
    with SOURCE_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def refresh_public_source_files() -> dict[str, Any]:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "status": "ok",
        "message": "Public source files are file-backed in this MVP. Manual source research is encoded in data/sources.",
        "source_manifest": str(SOURCE_MANIFEST_PATH),
        "public_benchmarks": str(BENCHMARK_PATH),
        "source_count": len(load_source_manifest()),
        "benchmark_count": len(load_public_benchmarks()),
    }


def sources_for_venue(venue_slug: str) -> list[dict[str, Any]]:
    return [
        row
        for row in load_source_manifest()
        if row.get("venue_slug") in {venue_slug, "all"}
    ]
