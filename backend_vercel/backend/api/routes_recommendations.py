from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.recommendations import generate_recommendations


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/management")
def management_recommendations(
    horizon: str = Query("operational", pattern="^(operational|tactical|strategic)$"),
    facility_profile: str = Query("mixed", pattern="^(outdoor|indoor|mixed)$"),
    db: Session = Depends(get_db),
):
    try:
        return generate_recommendations(db, "management", horizon=horizon, facility_profile=facility_profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/operations")
def operations_recommendations(
    horizon: str = Query("operational", pattern="^(operational|tactical|strategic)$"),
    facility_profile: str = Query("mixed", pattern="^(outdoor|indoor|mixed)$"),
    db: Session = Depends(get_db),
):
    try:
        return generate_recommendations(db, "operations", horizon=horizon, facility_profile=facility_profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/marketing")
def marketing_recommendations(
    horizon: str = Query("operational", pattern="^(operational|tactical|strategic)$"),
    facility_profile: str = Query("mixed", pattern="^(outdoor|indoor|mixed)$"),
    db: Session = Depends(get_db),
):
    try:
        return generate_recommendations(db, "marketing", horizon=horizon, facility_profile=facility_profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
