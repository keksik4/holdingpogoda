from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    hour: Mapped[int] = mapped_column(Integer, index=True)
    visitors: Mapped[int] = mapped_column(Integer)
    tickets_online: Mapped[int] = mapped_column(Integer)
    tickets_offline: Mapped[int] = mapped_column(Integer)
    revenue_tickets: Mapped[float] = mapped_column(Float)
    revenue_gastro: Mapped[float] = mapped_column(Float)
    revenue_parking: Mapped[float] = mapped_column(Float)
    facility_zone: Mapped[str] = mapped_column(String(80), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class EventRecord(Base):
    __tablename__ = "event_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    event_name: Mapped[str] = mapped_column(String(160))
    expected_impact: Mapped[float] = mapped_column(Float)
    event_type: Mapped[str] = mapped_column(String(80))
    indoor_or_outdoor: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class CampaignRecord(Base):
    __tablename__ = "campaign_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date_start: Mapped[date] = mapped_column(Date, index=True)
    date_end: Mapped[date] = mapped_column(Date, index=True)
    campaign_name: Mapped[str] = mapped_column(String(160))
    channel: Mapped[str] = mapped_column(String(80))
    budget_pln: Mapped[float] = mapped_column(Float)
    target_segment: Mapped[str] = mapped_column(String(120))
    message_type: Mapped[str] = mapped_column(String(120))
    expected_impact: Mapped[float] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
