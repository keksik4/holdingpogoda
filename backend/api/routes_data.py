from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.config import PROJECT_ROOT
from backend.database import get_db
from backend.services.data_importer import (
    CsvValidationError,
    business_data_status,
    clear_demo_business_data,
    ensure_demo_business_data,
    import_attendance_csv,
    import_campaigns_csv,
    import_events_csv,
)
from backend.services.demo_data_generator import create_sample_csv_files


router = APIRouter(tags=["data"])


@router.post("/import/attendance")
def import_attendance(
    file: UploadFile | None = File(default=None),
    file_path: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    path, is_demo = _resolve_upload_or_sample(file, file_path, "attendance")
    return _safe_import(import_attendance_csv, db, path, is_demo)


@router.post("/import/events")
def import_events(
    file: UploadFile | None = File(default=None),
    file_path: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    path, is_demo = _resolve_upload_or_sample(file, file_path, "events")
    return _safe_import(import_events_csv, db, path, is_demo)


@router.post("/import/campaigns")
def import_campaigns(
    file: UploadFile | None = File(default=None),
    file_path: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    path, is_demo = _resolve_upload_or_sample(file, file_path, "campaigns")
    return _safe_import(import_campaigns_csv, db, path, is_demo)


@router.post("/import/demo")
def import_demo(db: Session = Depends(get_db)):
    return ensure_demo_business_data(db)


@router.post("/import/clear-demo")
def clear_demo(db: Session = Depends(get_db)):
    return {"removed": clear_demo_business_data(db), "message": "Removed generated demo business rows."}


@router.get("/data/status")
def data_status(db: Session = Depends(get_db)):
    return business_data_status(db)


def _resolve_upload_or_sample(file: UploadFile | None, file_path: str | None, category: str) -> tuple[Path, bool]:
    if file is not None:
        safe_name = Path(file.filename or f"{category}.csv").name
        target = PROJECT_ROOT / "data" / "raw" / "business" / f"uploaded_{category}_{safe_name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            handle.write(file.file.read())
        return target, False
    if file_path:
        return Path(file_path), False
    paths = create_sample_csv_files()
    return Path(paths[category]), True


def _safe_import(importer, db: Session, path: Path, is_demo: bool):
    try:
        return importer(db, path, is_demo=is_demo)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CsvValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
