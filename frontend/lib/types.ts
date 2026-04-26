export type RiskLevel = "low" | "medium" | "high" | "unknown" | string;
export type ApiSource = "backend" | "demo_fallback";

export interface ApiResult<T> {
  data: T;
  source: ApiSource;
  error?: string;
}

export interface AppContext {
  current_date: string;
  current_datetime: string;
  timezone: string;
  default_month: string;
  default_selected_date: string;
  available_history_start: string;
  available_forecast_end: string;
  data_freshness: Record<string, unknown>;
  weather_refresh_status: Record<string, unknown>;
}

export interface ValueQuality {
  [key: string]: string | undefined;
}

export interface VenueAssetStatus {
  usage_status: string;
  local_path: string;
  source_name: string;
  license_notes: string;
  file_exists?: boolean;
}

export interface VenueAsset extends VenueAssetStatus {
  asset_key?: string;
  venue_slug: string;
  asset_type: string;
  source_url?: string;
  attribution?: string;
}

export interface HoverPreview {
  today_expected_visitors: number | null;
  tomorrow_expected_visitors: number | null;
  day_after_tomorrow_expected_visitors: number | null;
  weather_icon: string;
  risk_label: RiskLevel;
  confidence?: number;
  days?: Array<{
    date: string;
    label: string;
    expected_visitors: number | null;
    weather_icon: string;
    risk_level: RiskLevel;
    confidence_score?: number;
    source_count?: number;
    weather_status?: string;
  }>;
  data_quality_label: string;
  value_quality?: ValueQuality;
  is_calibrated_demo: boolean;
}

export interface VenueSummary {
  name: string;
  slug: string;
  type: string;
  city: string;
  address: string;
  short_description: string;
  weather_sensitivity_label: string;
  image_asset_status: VenueAssetStatus;
  data_quality_label: string;
  hover_preview?: HoverPreview;
}

export interface VenueProfile {
  venue_slug: string;
  name: string;
  type: string;
  city: string;
  address: string;
  latitude: number;
  longitude: number;
  description: string;
  weather_profile: string;
  seasonality_profile: string;
  visitor_benchmark_notes: string;
  operational_areas: string[];
  marketing_segments: string[];
  image_asset_key: string;
  data_quality_status: string;
}

export interface VenuesResponse {
  venues: VenueSummary[];
  data_quality_label: string;
}

export interface AssetsResponse {
  venue_slug: string;
  assets: VenueAsset[];
}

export interface DailyFactors {
  base_daily_visitors?: number;
  weekday_multiplier?: number;
  seasonal_multiplier?: number;
  weather_multiplier?: number;
  holiday_multiplier?: number;
  event_multiplier?: number;
  trend_multiplier?: number;
  venue_specific_adjustment?: number;
}

export interface CalendarDay {
  date: string;
  day_number: number;
  date_relation?: "historical" | "today" | "forecast" | string;
  weather_icon: string;
  expected_visitors: number;
  estimated_visitors?: number;
  visitors_low: number;
  visitors_base: number;
  visitors_high: number;
  risk_level: RiskLevel;
  weather_risk?: RiskLevel;
  best_day: boolean;
  confidence_score?: number;
  provider_disagreement_score?: number;
  daily_factors?: DailyFactors;
  explanation?: string;
  data_quality_label: string;
  value_quality?: ValueQuality;
  data_sources?: string[];
  is_calibrated_demo: boolean;
}

export interface CalendarResponse {
  venue_info: VenueSummary;
  venue?: VenueSummary;
  current_date?: string;
  selected_date?: string;
  month: string;
  days: CalendarDay[];
  data_freshness?: unknown;
  weather_consensus_summary?: unknown;
  calibration_summary?: unknown;
  holding_lodz_knowledge_base?: unknown;
  data_quality?: unknown;
}

export interface NormalizedWeatherPoint {
  datetime?: string;
  source?: "openweather" | "openmeteo" | string;
  temperatureC?: number | null;
  apparentTemperatureC?: number | null;
  precipitationMm?: number | null;
  precipitationProbability?: number | null;
  cloudCover?: number | null;
  windSpeedKmh?: number | null;
  weatherCode?: string | number | null;
  conditionLabel?: string | null;
}

export interface WeatherConsensus {
  date?: string;
  target_datetime: string;
  venue_slug: string;
  providers_used: string[];
  providers_available?: unknown[];
  temperature_avg?: number | null;
  temperatureC?: number | null;
  apparent_temperature_avg?: number | null;
  apparentTemperatureC?: number | null;
  precipitation_avg?: number | null;
  precipitationMm?: number | null;
  precipitation_probability_avg?: number | null;
  precipitationProbability?: number | null;
  cloud_cover_avg?: number | null;
  cloudCover?: number | null;
  humidity_avg?: number | null;
  wind_speed_avg?: number | null;
  windSpeedKmh?: number | null;
  wind_gusts_avg?: number | null;
  uv_index_avg?: number | null;
  conditionGroup?: string;
  providerCount?: number;
  source_count?: number;
  weather_icon_consensus: string;
  weather_description_consensus: string;
  weather_label_pl?: string;
  provider_disagreement_score: number;
  disagreementScore?: number;
  confidencePenalty?: number;
  forecast_confidence_score: number;
  data_freshness_minutes: number;
  source_status?: Record<string, unknown>;
  sources?: Record<string, NormalizedWeatherPoint>;
  cache_metadata?: Record<string, unknown>;
}

export interface WeatherDetails {
  weather_icon: string;
  weather_impact_score: number;
  forecast_confidence: number;
  note: string;
  data_quality_label: string;
  temperature?: number | null;
  apparent_temperature?: number | null;
  precipitation_probability?: number | null;
  wind_speed?: number | null;
  label_pl?: string;
  confidence_note?: string;
}

export interface HourlyVisitorPoint {
  datetime: string;
  date?: string;
  hour: number;
  hour_label?: string;
  expected_visitors: number;
  estimated_visitors?: number;
  typical_visitors: number;
  confidence_score: number;
  confidence?: number;
  peak_hour_flag: boolean;
  occupancy_percent?: number;
  load_level?: "niski" | "średni" | "wysoki" | "krytyczny" | string;
  weather_impact?: string;
  operational_note?: string;
  profile_id?: string;
  data_source?: string;
  data_quality_label: string;
  is_calibrated_demo: boolean;
}

export interface LowBaseHigh {
  low: number;
  base: number;
  high: number;
}

export interface RiskAndReadiness {
  risk_level?: RiskLevel;
  weather_risk?: RiskLevel;
  crowd_risk?: RiskLevel;
  operational_readiness?: string;
  readiness_checklist?: string[];
  data_quality_label?: string;
}

export interface ComparisonToTypicalDay {
  typical_visitors?: number;
  difference?: number;
  difference_percent?: number;
}

export interface HoldingProfile {
  venue_id?: string;
  base_daily_visitors?: number;
  baseline_confidence?: number;
  hourly_profile_ids?: string[];
  data_sources?: string[];
}

export interface DayDetailsResponse {
  venue_info: VenueSummary;
  selected_date: string;
  date_relation?: "historical" | "today" | "forecast" | string;
  expected_visitors: number;
  estimated_visitors?: number;
  confidence?: number;
  venue_id?: string;
  low_base_high: LowBaseHigh;
  weather_risk: RiskLevel;
  provider_disagreement_score?: number;
  daily_factors?: DailyFactors;
  data_sources?: string[];
  holding_lodz_profile?: HoldingProfile;
  weather_consensus?: WeatherConsensus;
  providers_used?: string[];
  weather_details: WeatherDetails;
  hourly_visitor_curve: HourlyVisitorPoint[];
  hourly_forecast?: HourlyVisitorPoint[];
  peak_hours: HourlyVisitorPoint[];
  operations_recommendations: string[];
  marketing_recommendations: string[];
  risk_and_readiness: RiskAndReadiness;
  comparison_to_typical_day: ComparisonToTypicalDay;
  forecast_explanation?: string;
  explanation?: string;
  calibration_confidence?: number;
  data_quality_labels?: string[];
  value_quality?: ValueQuality;
  is_calibrated_demo: boolean;
}
