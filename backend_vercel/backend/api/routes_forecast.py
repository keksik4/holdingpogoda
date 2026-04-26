from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.forecasting import build_forecast


router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/operational")
def operational_forecast(
    facility_profile: str = Query("mixed", pattern="^(outdoor|indoor|mixed)$"),
    db: Session = Depends(get_db),
):
    try:
        return build_forecast(db, horizon="operational", facility_profile=facility_profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tactical")
def tactical_forecast(
    facility_profile: str = Query("mixed", pattern="^(outdoor|indoor|mixed)$"),
    db: Session = Depends(get_db),
):
    try:
        return build_forecast(db, horizon="tactical", facility_profile=facility_profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/strategic")
def strategic_forecast(
    facility_profile: str = Query("mixed", pattern="^(outdoor|indoor|mixed)$"),
    db: Session = Depends(get_db),
):
    try:
        return build_forecast(db, horizon="strategic", facility_profile=facility_profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
