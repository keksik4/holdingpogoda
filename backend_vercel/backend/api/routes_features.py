from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.feature_engineering import build_features


router = APIRouter(tags=["features"])


@router.get("/features/build")
def features_build(
    facility_profile: str = Query("mixed", pattern="^(outdoor|indoor|mixed)$"),
    days_forward: int = Query(180, ge=7, le=220),
    db: Session = Depends(get_db),
):
    try:
        return build_features(db, facility_profile=facility_profile, days_forward=days_forward)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
