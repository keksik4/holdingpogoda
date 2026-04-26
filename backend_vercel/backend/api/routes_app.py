from fastapi import APIRouter

from backend.schemas.product_contracts import AppContextResponse
from backend.services.app_context import current_app_context


router = APIRouter(prefix="/app", tags=["app-context"])


@router.get("/context", response_model=AppContextResponse)
def app_context():
    return current_app_context()
