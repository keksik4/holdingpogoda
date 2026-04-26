from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class FeatureRecord(Base):
    __tablename__ = "feature_records"
    __table_args__ = (
        UniqueConstraint("date", "hour", "facility_profile", name="uq_feature_date_hour_profile"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    built_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    date: Mapped[date] = mapped_column(Date, index=True)
    hour: Mapped[int] = mapped_column(Integer, index=True)
    facility_profile: Mapped[str] = mapped_column(String(40), default="mixed", index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)
    is_weekend: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public_holiday: Mapped[bool] = mapped_column(Boolean, default=False)
    month: Mapped[int] = mapped_column(Integer)
    season: Mapped[str] = mapped_column(String(20))
    is_school_holiday_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    is_long_weekend_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    apparent_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation: Mapped[float | None] = mapped_column(Float, nullable=True)
    rain: Mapped[float | None] = mapped_column(Float, nullable=True)
    snowfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_score: Mapped[float] = mapped_column(Float, default=0.0)
    outdoor_comfort_score: Mapped[float] = mapped_column(Float, default=0.0)
    indoor_preference_score: Mapped[float] = mapped_column(Float, default=0.0)
    provider_disagreement_score: Mapped[float] = mapped_column(Float, default=0.0)
    forecast_confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    campaign_active: Mapped[bool] = mapped_column(Boolean, default=False)
    campaign_budget: Mapped[float] = mapped_column(Float, default=0.0)
    event_active: Mapped[bool] = mapped_column(Boolean, default=False)
    event_expected_impact: Mapped[float] = mapped_column(Float, default=0.0)
    lag_visitors_1_day: Mapped[float | None] = mapped_column(Float, nullable=True)
    lag_visitors_7_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    rolling_avg_7_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    rolling_avg_30_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    visitors: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_future: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class ForecastRecord(Base):
    __tablename__ = "forecast_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    horizon: Mapped[str] = mapped_column(String(40), index=True)
    facility_profile: Mapped[str] = mapped_column(String(40), index=True)
    target_date: Mapped[date] = mapped_column(Date, index=True)
    hour: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    expected_visitors: Mapped[float] = mapped_column(Float)
    low_scenario: Mapped[float] = mapped_column(Float)
    high_scenario: Mapped[float] = mapped_column(Float)
    expected_revenue: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(80))
    model_outputs_json: Mapped[str] = mapped_column(Text, default="{}")
    confidence_score: Mapped[float] = mapped_column(Float)
    provider_disagreement_score: Mapped[float] = mapped_column(Float, default=0.0)
    forecast_confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    weather_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class ModelEvaluationRecord(Base):
    __tablename__ = "model_evaluation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    model_name: Mapped[str] = mapped_column(String(80), index=True)
    facility_profile: Mapped[str] = mapped_column(String(40), default="mixed", index=True)
    mae: Mapped[float] = mapped_column(Float)
    rmse: Mapped[float] = mapped_column(Float)
    mape: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class RecommendationRecord(Base):
    __tablename__ = "recommendation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    business_view: Mapped[str] = mapped_column(String(40), index=True)
    horizon: Mapped[str] = mapped_column(String(40), index=True)
    facility_profile: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(220))
    summary: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(40), default="medium")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
