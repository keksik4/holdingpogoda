from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query

from backend.schemas.product_contracts import CalendarResponse, DayDetailsResponse, VenueProfileResponse, VenuesResponse
from backend.services.google_trends_signal import get_trend_signals
from backend.services.official_assets import get_assets_for_venue
from backend.services.public_source_research import load_public_benchmarks
from backend.services.attendance_forecast_engine import (
    calendar_forecast_payload,
    day_forecast_payload,
    forecast_validation_payload,
    venue_selection_forecast_payload,
)
from backend.services.weather_consensus import venue_weather_consensus, venue_weather_consensus_range
from backend.services.venue_profiles import get_venue_profile, venue_profile_contract
from backend.services.data_quality import venue_data_quality


router = APIRouter(prefix="/venues", tags=["venues"])


@router.get("", response_model=VenuesResponse)
def venues():
    return venue_selection_forecast_payload()


@router.get("/{venue_slug}", response_model=VenueProfileResponse)
def venue_detail(venue_slug: str):
    try:
        return venue_profile_contract(venue_slug)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{venue_slug}/calendar", response_model=CalendarResponse)
def venue_calendar(
    venue_slug: str,
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    year: int | None = None,
):
    try:
        if month is None and year is not None:
            month = f"{year}-01"
        if month is not None:
            datetime.strptime(month, "%Y-%m")
        return calendar_forecast_payload(venue_slug, month)
    except ValueError as exc:
        if "does not match format" in str(exc) or "unconverted data remains" in str(exc):
            raise HTTPException(status_code=422, detail="month must be a real month in YYYY-MM format.") from exc
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{venue_slug}/days/{selected_date}", response_model=DayDetailsResponse)
def venue_day_details(venue_slug: str, selected_date: date):
    try:
        return day_forecast_payload(venue_slug, selected_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{venue_slug}/weather/consensus")
def venue_weather_consensus_endpoint(venue_slug: str, selected_date: date = Query(..., alias="date")):
    try:
        get_venue_profile(venue_slug)
        return venue_weather_consensus(venue_slug, selected_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{venue_slug}/weather/consensus-range")
def venue_weather_consensus_range_endpoint(venue_slug: str, start: date, end: date):
    try:
        get_venue_profile(venue_slug)
        return venue_weather_consensus_range(venue_slug, start, end)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{venue_slug}/forecast/validation")
def venue_forecast_validation(venue_slug: str, month: str = Query(..., pattern=r"^\d{4}-\d{2}$")):
    try:
        get_venue_profile(venue_slug)
        datetime.strptime(month, "%Y-%m")
        return forecast_validation_payload(venue_slug, month)
    except ValueError as exc:
        if "does not match format" in str(exc) or "unconverted data remains" in str(exc):
            raise HTTPException(status_code=422, detail="month must be a real month in YYYY-MM format.") from exc
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{venue_slug}/assets")
def venue_assets(venue_slug: str):
    try:
        get_venue_profile(venue_slug)
        return {"venue_slug": venue_slug, "assets": get_assets_for_venue(venue_slug)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{venue_slug}/benchmarks")
def venue_benchmarks(venue_slug: str):
    try:
        get_venue_profile(venue_slug)
        return {
            "venue_slug": venue_slug,
            "benchmarks": load_public_benchmarks(venue_slug),
            "data_quality_label": "Official public benchmark",
            "note": "Benchmarks are calibration anchors, not internal daily attendance.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{venue_slug}/trend-signals")
def venue_trend_signals(
    venue_slug: str,
    start_date: date | None = None,
    end_date: date | None = None,
    refresh: bool = False,
):
    try:
        get_venue_profile(venue_slug)
        return get_trend_signals(venue_slug, start_date=start_date, end_date=end_date, refresh=refresh)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{venue_slug}/data-quality")
def venue_quality(venue_slug: str):
    try:
        get_venue_profile(venue_slug)
        return venue_data_quality(venue_slug)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
