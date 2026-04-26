from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.forecasting import get_model_evaluation


router = APIRouter(tags=["model"])


@router.get("/model/evaluation")
def model_evaluation(
    facility_profile: str = Query("mixed", pattern="^(outdoor|indoor|mixed)$"),
    db: Session = Depends(get_db),
):
    try:
        return get_model_evaluation(db, facility_profile=facility_profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
