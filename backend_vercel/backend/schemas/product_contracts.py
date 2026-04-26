from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SourceType = Literal["real", "official_public", "aggregated", "estimated", "calibrated_demo", "fallback"]
DateRelation = Literal["historical", "today", "forecast"]
RiskLevel = Literal["low", "medium", "high", "unknown"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class SourceMetadata(ContractModel):
    source_type: SourceType
    label: str
    confidence: float = Field(ge=0, le=1)
    is_demo: bool = False
    notes: list[str] = Field(default_factory=list)


class FreshnessMetadata(ContractModel):
    generated_at: str
    timezone: str
    cache_hit: bool | None = None
    cached_at: str | None = None
    expires_at: str | None = None
    refresh_reason: str | None = None


class AppContextResponse(ContractModel):
    app_name: str
    product_name: str
    current_date: str
    current_datetime: str
    timezone: str
    default_month: str
    default_selected_date: str
    available_history_start: str
    available_forecast_end: str
    data_freshness: dict[str, Any]
    weather_refresh_status: dict[str, Any]
    source_metadata: SourceMetadata
    freshness_metadata: FreshnessMetadata


class VenueAssetStatus(ContractModel):
    usage_status: str
    local_path: str
    source_name: str
    license_notes: str
    file_exists: bool | None = None


class HoverPreview(ContractModel):
    today_expected_visitors: int | None
    tomorrow_expected_visitors: int | None
    day_after_tomorrow_expected_visitors: int | None
    weather_icon: str
    risk_label: str
    data_quality_label: str
    value_quality: dict[str, str] = Field(default_factory=dict)
    is_calibrated_demo: bool
    source_metadata: SourceMetadata | None = None


class VenueSummary(ContractModel):
    name: str
    slug: str
    type: str
    city: str
    address: str
    short_description: str
    weather_sensitivity_label: str
    image_asset_status: VenueAssetStatus
    data_quality_label: str
    hover_preview: HoverPreview | None = None


class VenueProfileResponse(ContractModel):
    venue_slug: str
    name: str
    type: str
    city: str
    address: str
    latitude: float
    longitude: float
    description: str
    weather_profile: str
    seasonality_profile: str
    visitor_benchmark_notes: str
    operational_areas: list[str]
    marketing_segments: list[str]
    image_asset_key: str
    data_quality_status: str
    source_metadata: SourceMetadata | None = None
    freshness_metadata: FreshnessMetadata | None = None


class VenuesResponse(ContractModel):
    venues: list[VenueSummary]
    data_quality_label: str
    source_metadata: SourceMetadata
    freshness_metadata: FreshnessMetadata


class CalendarDay(ContractModel):
    date: str
    day_number: int
    date_relation: str
    weather_icon: str
    expected_visitors: int
    visitors_low: int
    visitors_base: int
    visitors_high: int
    risk_level: str
    weather_risk: str
    best_day: bool
    confidence_score: float
    weather_impact_score: float | None = None
    demand_signal_score: float | None = None
    seasonality_score: float | None = None
    holiday_impact_score: float | None = None
    event_impact_score: float | None = None
    trend_signal_score: float | None = None
    explanation: str
    data_quality_label: str
    value_quality: dict[str, str] = Field(default_factory=dict)
    is_calibrated_demo: bool
    source_metadata: SourceMetadata | None = None


class CalendarResponse(ContractModel):
    current_date: str
    selected_date: str
    month: str
    venue_info: VenueSummary
    venue: VenueSummary
    days: list[CalendarDay]
    data_freshness: dict[str, Any]
    weather_consensus_summary: dict[str, Any]
    calibration_summary: dict[str, Any]
    data_quality: dict[str, Any]
    source_metadata: SourceMetadata
    freshness_metadata: FreshnessMetadata


class WeatherConsensusSummary(ContractModel):
    target_datetime: str
    date: str | None = None
    venue_slug: str
    providers_used: list[str]
    temperature_avg: float | None = None
    apparent_temperature_avg: float | None = None
    precipitation_avg: float | None = None
    precipitation_probability_avg: float | None = None
    cloud_cover_avg: float | None = None
    humidity_avg: float | None = None
    wind_speed_avg: float | None = None
    wind_gusts_avg: float | None = None
    uv_index_avg: float | None = None
    weather_icon_consensus: str
    weather_description_consensus: str
    provider_disagreement_score: float
    forecast_confidence_score: float
    data_freshness_minutes: float
    source_status: dict[str, Any] = Field(default_factory=dict)
    cache_metadata: dict[str, Any] = Field(default_factory=dict)


class WeatherDetails(ContractModel):
    weather_icon: str
    weather_impact_score: float
    forecast_confidence: float
    note: str
    data_quality_label: str
    temperature: float | None = None
    apparent_temperature: float | None = None
    precipitation_probability: float | None = None
    wind_speed: float | None = None


class HourlyVisitorPoint(ContractModel):
    datetime: str
    date: str | None = None
    hour: int
    expected_visitors: int
    typical_visitors: int
    confidence_score: float
    peak_hour_flag: bool
    data_quality_label: str
    is_calibrated_demo: bool


class LowBaseHigh(ContractModel):
    low: int
    base: int
    high: int


class RiskAndReadiness(ContractModel):
    risk_level: str | None = None
    weather_risk: str | None = None
    crowd_risk: str | None = None
    operational_readiness: str | None = None
    readiness_checklist: list[str] = Field(default_factory=list)
    data_quality_label: str | None = None


class ComparisonToTypicalDay(ContractModel):
    typical_visitors: int | None = None
    difference: int | None = None
    difference_percent: float | None = None


class DayDetailsResponse(ContractModel):
    venue_info: VenueSummary
    selected_date: str
    date_relation: str
    expected_visitors: int
    low_base_high: LowBaseHigh
    hourly_visitor_curve: list[HourlyVisitorPoint]
    peak_hours: list[HourlyVisitorPoint]
    weather_consensus: WeatherConsensusSummary
    providers_used: list[str]
    weather_risk: str
    weather_details: WeatherDetails
    operations_recommendations: list[str]
    marketing_recommendations: list[str]
    risk_and_readiness: RiskAndReadiness
    comparison_to_typical_day: ComparisonToTypicalDay
    forecast_explanation: str
    explanation: str
    calibration_confidence: float
    data_quality_labels: list[str]
    value_quality: dict[str, str]
    is_calibrated_demo: bool
    source_metadata: SourceMetadata
    freshness_metadata: FreshnessMetadata
