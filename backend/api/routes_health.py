from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.services.data_importer import business_data_status


router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    settings = get_settings()
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "default_location": {
            "city": settings.default_city,
            "latitude": settings.default_latitude,
            "longitude": settings.default_longitude,
            "timezone": settings.default_timezone,
        },
        "business_data": business_data_status(db),
    }
