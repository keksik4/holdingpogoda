from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.weather_common import provider_status_payload
from backend.services.weather_consensus import (
    calculate_weather_consensus,
    get_weather_consensus,
    weather_provider_comparison,
)
from backend.services.weather_imgw import fetch_imgw_current
from backend.services.weather_met_no import fetch_met_no_forecast
from backend.services.weather_open_meteo import (
    fetch_open_meteo_forecast,
    fetch_open_meteo_historical_forecast,
    fetch_open_meteo_history,
)


router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/providers/status")
def provider_status(db: Session = Depends(get_db)):
    return {"providers": provider_status_payload(db)}


@router.get("/forecast/open-meteo")
def open_meteo_forecast(days: int = Query(7, ge=1, le=16), db: Session = Depends(get_db)):
    return fetch_open_meteo_forecast(db, days=days)


@router.get("/forecast/met-no")
def met_no_forecast(db: Session = Depends(get_db)):
    return fetch_met_no_forecast(db)


@router.get("/current/imgw")
def imgw_current(db: Session = Depends(get_db)):
    return fetch_imgw_current(db)


@router.get("/consensus")
def weather_consensus(fetch_first: bool = False, db: Session = Depends(get_db)):
    fetch_results = []
    if fetch_first:
        fetch_results.append(fetch_open_meteo_forecast(db))
        fetch_results.append(fetch_met_no_forecast(db))
        fetch_results.append(fetch_imgw_current(db))
    result = calculate_weather_consensus(db)
    return result | {"fetch_results": fetch_results, "comparison": weather_provider_comparison(db)}


@router.get("/history")
def weather_history(
    start_date: date | None = None,
    end_date: date | None = None,
    source: str = Query("actual", pattern="^(actual|historical_forecast)$"),
    db: Session = Depends(get_db),
):
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=30))
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date.")
    if source == "historical_forecast":
        return fetch_open_meteo_historical_forecast(db, start_date=start_date, end_date=end_date)
    return fetch_open_meteo_history(db, start_date=start_date, end_date=end_date)


@router.get("/consensus/records")
def weather_consensus_records(
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
    limit: int = Query(240, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    return {"items": get_weather_consensus(db, start_datetime, end_datetime, limit)}
