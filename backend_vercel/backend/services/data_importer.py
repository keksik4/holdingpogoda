import shutil
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from backend.config import PROJECT_ROOT
from backend.models.business_models import AttendanceRecord, CampaignRecord, EventRecord
from backend.services.demo_data_generator import create_sample_csv_files


ATTENDANCE_COLUMNS = [
    "date",
    "hour",
    "visitors",
    "tickets_online",
    "tickets_offline",
    "revenue_tickets",
    "revenue_gastro",
    "revenue_parking",
    "facility_zone",
    "notes",
]
EVENT_COLUMNS = ["date", "event_name", "expected_impact", "event_type", "indoor_or_outdoor", "notes"]
CAMPAIGN_COLUMNS = [
    "date_start",
    "date_end",
    "campaign_name",
    "channel",
    "budget_pln",
    "target_segment",
    "message_type",
    "expected_impact",
    "notes",
]


class CsvValidationError(ValueError):
    """Raised when an imported business CSV is readable but not usable."""


def ensure_demo_business_data(db: Session) -> dict[str, Any]:
    paths = create_sample_csv_files()
    imported = {}
    if db.query(AttendanceRecord).count() == 0:
        imported["attendance"] = import_attendance_csv(db, paths["attendance"], is_demo=True)
    if db.query(EventRecord).count() == 0:
        imported["events"] = import_events_csv(db, paths["events"], is_demo=True)
    if db.query(CampaignRecord).count() == 0:
        imported["campaigns"] = import_campaigns_csv(db, paths["campaigns"], is_demo=True)
    return {"demo_mode": any(imported.values()), "sample_paths": paths, "imported": imported}


def import_attendance_csv(db: Session, file_path: str | Path, is_demo: bool = False) -> dict[str, Any]:
    path = Path(file_path)
    df = _read_csv(path, ATTENDANCE_COLUMNS)
    _coerce_date(df, "date")
    for column in ["hour", "visitors", "tickets_online", "tickets_offline"]:
        _coerce_numeric(df, column, integer=True, minimum=0)
    for column in ["revenue_tickets", "revenue_gastro", "revenue_parking"]:
        _coerce_numeric(df, column, minimum=0)
    invalid_hours = df[(df["hour"] < 0) | (df["hour"] > 23)]
    if not invalid_hours.empty:
        raise CsvValidationError(f"Column hour must be between 0 and 23. Bad CSV rows: {_row_numbers(invalid_hours)}.")
    _require_text(df, "facility_zone")
    rows = [
        AttendanceRecord(
            date=row["date"],
            hour=int(row["hour"]),
            visitors=int(row["visitors"]),
            tickets_online=int(row["tickets_online"]),
            tickets_offline=int(row["tickets_offline"]),
            revenue_tickets=float(row["revenue_tickets"]),
            revenue_gastro=float(row["revenue_gastro"]),
            revenue_parking=float(row["revenue_parking"]),
            facility_zone=str(row["facility_zone"]).strip(),
            notes=_clean_text(row.get("notes")),
            source_file=str(path),
            is_demo=is_demo,
        )
        for _, row in df.iterrows()
    ]
    removed_demo_rows = 0
    if not is_demo:
        removed_demo_rows = db.query(AttendanceRecord).filter(AttendanceRecord.is_demo.is_(True)).delete()
    db.add_all(rows)
    db.commit()
    raw_copy = _copy_to_raw(path, "attendance")
    return {
        "rows_imported": len(rows),
        "source": str(path),
        "raw_copy": raw_copy,
        "is_demo": is_demo,
        "removed_demo_rows": removed_demo_rows,
        "message": _import_message("attendance", is_demo, removed_demo_rows),
    }


def import_events_csv(db: Session, file_path: str | Path, is_demo: bool = False) -> dict[str, Any]:
    path = Path(file_path)
    df = _read_csv(path, EVENT_COLUMNS)
    _coerce_date(df, "date")
    _coerce_numeric(df, "expected_impact", minimum=-1)
    for column in ["event_name", "event_type", "indoor_or_outdoor"]:
        _require_text(df, column)
    rows = [
        EventRecord(
            date=row["date"],
            event_name=str(row["event_name"]).strip(),
            expected_impact=float(row["expected_impact"]),
            event_type=str(row["event_type"]).strip(),
            indoor_or_outdoor=str(row["indoor_or_outdoor"]).strip(),
            notes=_clean_text(row.get("notes")),
            source_file=str(path),
            is_demo=is_demo,
        )
        for _, row in df.iterrows()
    ]
    removed_demo_rows = 0
    if not is_demo:
        removed_demo_rows = db.query(EventRecord).filter(EventRecord.is_demo.is_(True)).delete()
    db.add_all(rows)
    db.commit()
    raw_copy = _copy_to_raw(path, "events")
    return {
        "rows_imported": len(rows),
        "source": str(path),
        "raw_copy": raw_copy,
        "is_demo": is_demo,
        "removed_demo_rows": removed_demo_rows,
        "message": _import_message("events", is_demo, removed_demo_rows),
    }


def import_campaigns_csv(db: Session, file_path: str | Path, is_demo: bool = False) -> dict[str, Any]:
    path = Path(file_path)
    df = _read_csv(path, CAMPAIGN_COLUMNS)
    _coerce_date(df, "date_start")
    _coerce_date(df, "date_end")
    _coerce_numeric(df, "budget_pln", minimum=0)
    _coerce_numeric(df, "expected_impact", minimum=-1)
    for column in ["campaign_name", "channel", "target_segment", "message_type"]:
        _require_text(df, column)
    invalid_windows = df[df["date_end"] < df["date_start"]]
    if not invalid_windows.empty:
        raise CsvValidationError(f"date_end must be on or after date_start. Bad CSV rows: {_row_numbers(invalid_windows)}.")
    rows = [
        CampaignRecord(
            date_start=row["date_start"],
            date_end=row["date_end"],
            campaign_name=str(row["campaign_name"]).strip(),
            channel=str(row["channel"]).strip(),
            budget_pln=float(row["budget_pln"]),
            target_segment=str(row["target_segment"]).strip(),
            message_type=str(row["message_type"]).strip(),
            expected_impact=float(row["expected_impact"]),
            notes=_clean_text(row.get("notes")),
            source_file=str(path),
            is_demo=is_demo,
        )
        for _, row in df.iterrows()
    ]
    removed_demo_rows = 0
    if not is_demo:
        removed_demo_rows = db.query(CampaignRecord).filter(CampaignRecord.is_demo.is_(True)).delete()
    db.add_all(rows)
    db.commit()
    raw_copy = _copy_to_raw(path, "campaigns")
    return {
        "rows_imported": len(rows),
        "source": str(path),
        "raw_copy": raw_copy,
        "is_demo": is_demo,
        "removed_demo_rows": removed_demo_rows,
        "message": _import_message("campaigns", is_demo, removed_demo_rows),
    }


def clear_demo_business_data(db: Session) -> dict[str, int]:
    counts = {
        "attendance": db.query(AttendanceRecord).filter(AttendanceRecord.is_demo.is_(True)).delete(),
        "events": db.query(EventRecord).filter(EventRecord.is_demo.is_(True)).delete(),
        "campaigns": db.query(CampaignRecord).filter(CampaignRecord.is_demo.is_(True)).delete(),
    }
    db.commit()
    return counts


def business_data_status(db: Session) -> dict[str, Any]:
    attendance_count = db.query(AttendanceRecord).count()
    event_count = db.query(EventRecord).count()
    campaign_count = db.query(CampaignRecord).count()
    demo_attendance_count = db.query(AttendanceRecord).filter(AttendanceRecord.is_demo.is_(True)).count()
    real_attendance_count = db.query(AttendanceRecord).filter(AttendanceRecord.is_demo.is_(False)).count()
    return {
        "attendance_records": attendance_count,
        "event_records": event_count,
        "campaign_records": campaign_count,
        "real_attendance_records": real_attendance_count,
        "demo_attendance_records": demo_attendance_count,
        "real_event_records": db.query(EventRecord).filter(EventRecord.is_demo.is_(False)).count(),
        "demo_event_records": db.query(EventRecord).filter(EventRecord.is_demo.is_(True)).count(),
        "real_campaign_records": db.query(CampaignRecord).filter(CampaignRecord.is_demo.is_(False)).count(),
        "demo_campaign_records": db.query(CampaignRecord).filter(CampaignRecord.is_demo.is_(True)).count(),
        "uses_demo_attendance": real_attendance_count == 0 and demo_attendance_count > 0,
        "data_mode": _data_mode(real_attendance_count, demo_attendance_count),
        "demo_outputs_expected": real_attendance_count == 0,
    }


def _read_csv(path: Path, expected_columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}. Use an absolute path or upload a file in /docs.")
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001
        raise CsvValidationError(f"Could not read {path.name} as CSV. Original error: {exc}") from exc
    missing = [column for column in expected_columns if column not in df.columns]
    if missing:
        raise CsvValidationError(
            f"{path.name} is missing required columns: {', '.join(missing)}. "
            f"Expected columns: {', '.join(expected_columns)}."
        )
    df = df[expected_columns].dropna(how="all").copy()
    if df.empty:
        raise CsvValidationError(f"{path.name} has no data rows.")
    return df


def _coerce_date(df: pd.DataFrame, column: str) -> None:
    parsed = pd.to_datetime(df[column], errors="coerce")
    invalid = df[parsed.isna()]
    if not invalid.empty:
        raise CsvValidationError(f"Column {column} contains invalid dates. Use YYYY-MM-DD. Bad CSV rows: {_row_numbers(invalid)}.")
    df[column] = parsed.dt.date


def _coerce_numeric(df: pd.DataFrame, column: str, integer: bool = False, minimum: float | None = None) -> None:
    parsed = pd.to_numeric(df[column], errors="coerce")
    invalid = df[parsed.isna()]
    if not invalid.empty:
        raise CsvValidationError(f"Column {column} must be numeric. Bad CSV rows: {_row_numbers(invalid)}.")
    if minimum is not None:
        below_minimum = df[parsed < minimum]
        if not below_minimum.empty:
            raise CsvValidationError(f"Column {column} must be at least {minimum}. Bad CSV rows: {_row_numbers(below_minimum)}.")
    if integer:
        non_integer = df[(parsed % 1) != 0]
        if not non_integer.empty:
            raise CsvValidationError(f"Column {column} must contain whole numbers. Bad CSV rows: {_row_numbers(non_integer)}.")
        df[column] = parsed.astype(int)
    else:
        df[column] = parsed.astype(float)


def _require_text(df: pd.DataFrame, column: str) -> None:
    invalid = df[df[column].isna() | (df[column].astype(str).str.strip() == "")]
    if not invalid.empty:
        raise CsvValidationError(f"Column {column} cannot be empty. Bad CSV rows: {_row_numbers(invalid)}.")


def _copy_to_raw(path: Path, category: str) -> str:
    raw_dir = PROJECT_ROOT / "data" / "raw" / "business"
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / f"{category}_{path.stem}_{pd.Timestamp.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    shutil.copy2(path, target)
    return str(target)


def _clean_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)


def _row_numbers(df: pd.DataFrame) -> str:
    return ", ".join(str(index + 2) for index in df.index[:5])


def _import_message(category: str, is_demo: bool, removed_demo_rows: int) -> str:
    if is_demo:
        return f"Imported demo {category} data. Forecast outputs should be treated as demo."
    if removed_demo_rows:
        return f"Imported real {category} data and removed {removed_demo_rows} old demo rows for that table."
    return f"Imported real {category} data."


def _data_mode(real_count: int, demo_count: int) -> str:
    if real_count and demo_count:
        return "mixed_real_and_demo"
    if real_count:
        return "real_imported"
    if demo_count:
        return "demo"
    return "empty"
