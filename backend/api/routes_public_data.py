from datetime import date

from fastapi import APIRouter, HTTPException, Query

from backend.services.public_source_research import load_source_manifest, refresh_public_source_files
from backend.services.realistic_attendance_generator import generate_calibrated_attendance
from backend.services.app_context import current_app_context
from backend.services.venue_profiles import list_venue_profiles
from backend.services.weather_consensus import venue_weather_consensus
from backend.services.attendance_forecast_engine import calendar_forecast_payload


router = APIRouter(prefix="/data", tags=["public-data"])


@router.post("/refresh-public-sources")
def refresh_public_sources():
    return refresh_public_source_files()


@router.post("/generate-calibrated-attendance")
def generate_attendance(start_date: date | None = None, end_date: date | None = None):
    try:
        return generate_calibrated_attendance(start_date=start_date, end_date=end_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/sources")
def data_sources():
    return {
        "sources": load_source_manifest(),
        "data_quality_labels": [
            "Official public benchmark",
            "Real weather API",
            "Google Trends signal",
            "Calibrated demo attendance",
            "Manual venue asset",
            "Source missing",
        ],
    }


@router.post("/refresh-weather")
def refresh_weather(
    venue_slug: str | None = None,
    target_date: date | None = Query(None, alias="date"),
    force: bool = False,
):
    target_date = target_date or date.fromisoformat(current_app_context()["current_date"])
    venues = [venue_slug] if venue_slug else [venue["venue_slug"] for venue in list_venue_profiles()]
    return {
        "date": target_date.isoformat(),
        "force": force,
        "items": [venue_weather_consensus(slug, target_date, force=force) for slug in venues],
    }


@router.post("/recalculate-forecasts")
def recalculate_forecasts(venue_slug: str | None = None, month: str | None = None):
    venues = [venue_slug] if venue_slug else [venue["venue_slug"] for venue in list_venue_profiles()]
    return {
        "month": month or current_app_context()["default_month"],
        "items": [calendar_forecast_payload(slug, month) for slug in venues],
        "status": "ok",
    }
