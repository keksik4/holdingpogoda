from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class RawWeatherPayload(Base):
    __tablename__ = "raw_weather_payloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    endpoint: Mapped[str] = mapped_column(String(200))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_payload_path: Mapped[str] = mapped_column(String(500))
    request_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class NormalizedWeatherRecord(Base):
    __tablename__ = "normalized_weather_records"
    __table_args__ = (
        UniqueConstraint("provider", "target_datetime", "forecast_generated_at", name="uq_provider_target_generated"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    forecast_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    target_datetime: Mapped[datetime] = mapped_column(DateTime, index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    apparent_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation: Mapped[float | None] = mapped_column(Float, nullable=True)
    rain: Mapped[float | None] = mapped_column(Float, nullable=True)
    snowfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_gusts: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    uv_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    sunshine_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    weather_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    raw_payload_path: Mapped[str | None] = mapped_column(String(500), nullable=True)


class WeatherConsensusRecord(Base):
    __tablename__ = "weather_consensus_records"
    __table_args__ = (UniqueConstraint("target_datetime", name="uq_weather_consensus_target"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    target_datetime: Mapped[datetime] = mapped_column(DateTime, index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    apparent_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation: Mapped[float | None] = mapped_column(Float, nullable=True)
    rain: Mapped[float | None] = mapped_column(Float, nullable=True)
    snowfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_gusts: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    uv_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    sunshine_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    weather_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    provider_count: Mapped[int] = mapped_column(Integer, default=0)
    providers_used: Mapped[str] = mapped_column(Text, default="")
    missing_fields: Mapped[str] = mapped_column(Text, default="")
    provider_disagreement_score: Mapped[float] = mapped_column(Float, default=0.0)
    forecast_confidence_score: Mapped[float] = mapped_column(Float, default=0.0)


class WeatherProviderStatus(Base):
    __tablename__ = "weather_provider_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False)
    last_successful_fetch: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_fields: Mapped[str] = mapped_column(Text, default="")
    records_last_fetch: Mapped[int] = mapped_column(Integer, default=0)
