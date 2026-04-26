import type {
  AppContext,
  AssetsResponse,
  CalendarDay,
  CalendarResponse,
  DayDetailsResponse,
  HoverPreview,
  VenueAsset,
  VenueProfile,
  VenueSummary,
  VenuesResponse
} from "@/lib/types";
import { toDateString } from "@/lib/formatting";

const FALLBACK_LABEL = "Tryb zapasowy - backend niedostępny";

export function fallbackAppContext(): AppContext {
  const now = new Date();
  const warsawDate = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Warsaw",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(now);
  return {
    current_date: warsawDate,
    current_datetime: now.toISOString(),
    timezone: "Europe/Warsaw",
    default_month: warsawDate.slice(0, 7),
    default_selected_date: warsawDate,
    available_history_start: "2022-01-01",
    available_forecast_end: `${now.getFullYear() + 1}-12-31`,
    data_freshness: { label: FALLBACK_LABEL },
    weather_refresh_status: { label: FALLBACK_LABEL }
  };
}

const fallbackProfiles: VenueProfile[] = [
  {
    venue_slug: "aquapark_fala",
    name: "Aquapark Fala",
    type: "aquapark mieszany",
    city: "Łódź",
    address: "al. Unii Lubelskiej 4, 94-208 Łódź",
    latitude: 51.7596,
    longitude: 19.4156,
    description: "Całoroczny aquapark z basenami, zjeżdżalniami, saunami i letnią strefą zewnętrzną.",
    weather_profile: "mieszany",
    seasonality_profile: "wysokie lato, mocne weekendy i święta",
    visitor_benchmark_notes: "Szacunek demonstracyjny.",
    operational_areas: ["wejście", "ratownicy", "baseny", "zjeżdżalnie", "gastronomia", "parking"],
    marketing_segments: ["rodziny", "studenci", "turyści", "wellness"],
    image_asset_key: "aquapark_fala_primary",
    data_quality_status: FALLBACK_LABEL
  },
  {
    venue_slug: "orientarium_zoo_lodz",
    name: "Orientarium Zoo Łódź",
    type: "zoo i atrakcja całoroczna",
    city: "Łódź",
    address: "ul. Konstantynowska 8/10, 94-303 Łódź",
    latitude: 51.7638,
    longitude: 19.4108,
    description: "Zoo i Orientarium z pawilonami, ekspozycjami zewnętrznymi oraz ruchem rodzinnym i turystycznym.",
    weather_profile: "zewnętrzny z odpornością pawilonów",
    seasonality_profile: "wiosna, lato, weekendy i wycieczki szkolne",
    visitor_benchmark_notes: "Szacunek demonstracyjny.",
    operational_areas: ["kasy", "kolejki", "pawilony", "ścieżki", "gastronomia", "parking"],
    marketing_segments: ["rodziny", "turyści", "grupy szkolne"],
    image_asset_key: "orientarium_zoo_lodz_primary",
    data_quality_status: FALLBACK_LABEL
  }
];

export function fallbackVenues(): VenuesResponse {
  return { venues: fallbackProfiles.map(profileToSummary), data_quality_label: FALLBACK_LABEL };
}

export function fallbackVenue(slug: string): VenueProfile {
  return fallbackProfiles.find((profile) => profile.venue_slug === slug) ?? fallbackProfiles[0];
}

export function fallbackAssets(slug: string): AssetsResponse {
  const localPath = slug === "orientarium_zoo_lodz" ? "public/venues/orientarium.jpg" : "public/venues/aquapark-fala.jpg";
  const asset: VenueAsset = {
    asset_key: `${slug}_primary`,
    venue_slug: slug,
    asset_type: "venue_photo",
    local_path: localPath,
    source_url: slug === "orientarium_zoo_lodz" ? "https://zoo.lodz.pl/" : "https://aquapark.lodz.pl/",
    source_name: slug === "orientarium_zoo_lodz" ? "Orientarium Zoo Łódź" : "Aquapark Fala",
    attribution: "Lokalny zasób projektu.",
    license_notes: "Przed publicznym użyciem potwierdź zgodę lub licencję.",
    usage_status: "manual_asset_available",
    file_exists: true
  };
  return { venue_slug: slug, assets: [asset] };
}

export function fallbackCalendar(slug: string, month?: string): CalendarResponse {
  const context = fallbackAppContext();
  const selectedMonth = month || context.default_month;
  const [year, monthNumber] = selectedMonth.split("-").map(Number);
  const daysInMonth = new Date(year, monthNumber, 0).getDate();
  const generated = Array.from({ length: daysInMonth }, (_, index) =>
    fallbackCalendarDay(slug, `${selectedMonth}-${String(index + 1).padStart(2, "0")}`)
  );
  const threshold = quantile(generated.map((day) => day.expected_visitors), 0.78);
  const days = generated.map((day) => ({ ...day, best_day: day.expected_visitors >= threshold && day.risk_level !== "high" }));
  const venue = profileToSummary(fallbackVenue(slug));
  return {
    venue_info: venue,
    venue,
    current_date: context.current_date,
    selected_date: context.default_selected_date,
    month: selectedMonth,
    days,
    data_freshness: { label: FALLBACK_LABEL },
    weather_consensus_summary: { label: FALLBACK_LABEL },
    calibration_summary: { status: FALLBACK_LABEL },
    data_quality: { label: FALLBACK_LABEL }
  };
}

export function fallbackDayDetails(slug: string, dateString: string): DayDetailsResponse {
  const profile = fallbackVenue(slug);
  const day = fallbackCalendarDay(slug, dateString);
  const hours = slug === "aquapark_fala" ? range(9, 21) : range(9, 18);
  const weights = hours.map((hour) => {
    const center = slug === "aquapark_fala" ? 15 : 13;
    const spread = slug === "aquapark_fala" ? 2.8 : 2.1;
    return 1 + 1.7 * Math.exp(-((hour - center) ** 2) / (2 * spread * spread));
  });
  const expected = distribute(day.expected_visitors, weights);
  const typical = distribute(Math.max(1, Math.round(day.expected_visitors * 0.86)), weights);
  const peak = Math.max(...expected);
  const hourly = hours.map((hour, index) => ({
    datetime: `${dateString}T${String(hour).padStart(2, "0")}:00:00`,
    date: dateString,
    hour,
    hour_label: `${String(hour).padStart(2, "0")}:00`,
    expected_visitors: expected[index],
    estimated_visitors: expected[index],
    typical_visitors: typical[index],
    confidence_score: day.risk_level === "high" ? 0.62 : day.risk_level === "medium" ? 0.72 : 0.82,
    peak_hour_flag: expected[index] >= peak * 0.92,
    occupancy_percent: Math.round((expected[index] / peak) * 100),
    load_level: expected[index] >= peak * 0.9 ? "wysoki" : expected[index] >= peak * 0.55 ? "średni" : "niski",
    weather_impact: "dane szacunkowe",
    operational_note: "Dane szacunkowe z trybu zapasowego.",
    data_quality_label: FALLBACK_LABEL,
    is_calibrated_demo: true
  }));

  return {
    venue_info: profileToSummary(profile),
    selected_date: dateString,
    date_relation: "forecast",
    expected_visitors: day.expected_visitors,
    estimated_visitors: day.expected_visitors,
    low_base_high: { low: day.visitors_low, base: day.visitors_base, high: day.visitors_high },
    weather_risk: day.risk_level,
    daily_factors: {
      base_daily_visitors: slug === "aquapark_fala" ? 4247 : 3836,
      weekday_multiplier: 1,
      seasonal_multiplier: 1,
      weather_multiplier: 1,
      holiday_multiplier: 1,
      event_multiplier: 1
    },
    data_sources: ["tryb_zapasowy"],
    weather_details: {
      weather_icon: day.weather_icon,
      weather_impact_score: day.risk_level === "low" ? 8 : day.risk_level === "medium" ? -2 : -12,
      forecast_confidence: day.risk_level === "high" ? 0.62 : 0.72,
      note: "Backend jest niedostępny, więc widok pokazuje dane szacunkowe.",
      data_quality_label: FALLBACK_LABEL
    },
    hourly_visitor_curve: hourly,
    hourly_forecast: hourly,
    peak_hours: hourly.filter((point) => point.peak_hour_flag),
    operations_recommendations: ["Utrzymaj ostrożny plan operacyjny do czasu odświeżenia danych backendu."],
    marketing_recommendations: ["Nie zwiększaj budżetu kampanii bez potwierdzenia prognozy z backendu."],
    risk_and_readiness: {
      risk_level: day.risk_level,
      weather_risk: day.risk_level,
      crowd_risk: day.risk_level,
      operational_readiness: "Plan wariantowy",
      readiness_checklist: profile.operational_areas,
      data_quality_label: FALLBACK_LABEL
    },
    comparison_to_typical_day: {
      typical_visitors: Math.round(day.expected_visitors * 0.86),
      difference: Math.round(day.expected_visitors * 0.14),
      difference_percent: 14
    },
    data_quality_labels: [FALLBACK_LABEL],
    value_quality: { expected_visitors: FALLBACK_LABEL, weather_details: FALLBACK_LABEL },
    is_calibrated_demo: true
  };
}

function profileToSummary(profile: VenueProfile): VenueSummary {
  return {
    name: profile.name,
    slug: profile.venue_slug,
    type: profile.type,
    city: profile.city,
    address: profile.address,
    short_description: profile.description,
    weather_sensitivity_label:
      profile.venue_slug === "orientarium_zoo_lodz" ? "Silna wrażliwość na pogodę" : "Mieszana wrażliwość pogodowa",
    image_asset_status: fallbackAssets(profile.venue_slug).assets[0],
    data_quality_label: FALLBACK_LABEL,
    hover_preview: fallbackHoverPreview(profile.venue_slug)
  };
}

function fallbackHoverPreview(slug: string): HoverPreview {
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  const dayAfterTomorrow = new Date(today);
  dayAfterTomorrow.setDate(today.getDate() + 2);
  const todayDay = fallbackCalendarDay(slug, toDateString(today));
  return {
    today_expected_visitors: fallbackVisitors(slug, today),
    tomorrow_expected_visitors: fallbackVisitors(slug, tomorrow),
    day_after_tomorrow_expected_visitors: fallbackVisitors(slug, dayAfterTomorrow),
    weather_icon: todayDay.weather_icon,
    risk_label: todayDay.risk_level,
    data_quality_label: FALLBACK_LABEL,
    value_quality: { expected_visitors: FALLBACK_LABEL },
    is_calibrated_demo: true
  };
}

function fallbackCalendarDay(slug: string, dateString: string): CalendarDay {
  const date = new Date(`${dateString}T12:00:00`);
  const base = fallbackVisitors(slug, date);
  const risk = riskForDate(slug, date);
  const uncertainty = risk === "high" ? 0.24 : risk === "medium" ? 0.16 : 0.1;
  return {
    date: dateString,
    day_number: date.getDate(),
    weather_icon: risk === "high" ? "rain" : risk === "medium" ? "cloud" : date.getDate() % 4 === 0 ? "partly_cloudy" : "sun",
    expected_visitors: base,
    estimated_visitors: base,
    visitors_low: Math.round(base * (1 - uncertainty)),
    visitors_base: base,
    visitors_high: Math.round(base * (1 + uncertainty)),
    risk_level: risk,
    weather_risk: risk,
    best_day: false,
    confidence_score: risk === "high" ? 0.58 : risk === "medium" ? 0.68 : 0.78,
    explanation: "Dane szacunkowe z trybu zapasowego.",
    data_quality_label: FALLBACK_LABEL,
    value_quality: { expected_visitors: FALLBACK_LABEL },
    data_sources: ["tryb_zapasowy"],
    is_calibrated_demo: true
  };
}

function fallbackVisitors(slug: string, date: Date): number {
  const month = date.getMonth() + 1;
  const day = date.getDay();
  const weekend = day === 0 || day === 6;
  const aquaparkSeason = [0.78, 0.94, 0.76, 0.86, 1.14, 1.28, 1.62, 1.58, 0.86, 0.76, 0.72, 0.9][month - 1];
  const zooSeason = [0.45, 0.75, 0.85, 1.05, 1.2, 1.25, 1.55, 1.63, 1.1, 0.95, 0.75, 0.78][month - 1];
  const base = slug === "aquapark_fala" ? 4247 : 3836;
  const season = slug === "aquapark_fala" ? aquaparkSeason : zooSeason;
  const weekendFactor = weekend ? (slug === "aquapark_fala" ? 1.55 : 1.6) : 0.9;
  const variation = 0.96 + ((date.getDate() * 17 + month * 11) % 10) / 100;
  return Math.max(300, Math.round(base * season * weekendFactor * variation));
}

function riskForDate(slug: string, date: Date): "low" | "medium" | "high" {
  const score = (date.getDate() * 19 + (date.getMonth() + 1) * 13 + (slug === "aquapark_fala" ? 7 : 11)) % 100;
  if (score < 12) return "high";
  if (score < 36) return "medium";
  return "low";
}

function range(start: number, endInclusive: number): number[] {
  return Array.from({ length: endInclusive - start + 1 }, (_, index) => start + index);
}

function distribute(total: number, weights: number[]): number[] {
  const weightTotal = weights.reduce((sum, weight) => sum + weight, 0);
  const raw = weights.map((weight) => (total * weight) / weightTotal);
  const values = raw.map(Math.floor);
  let remainder = total - values.reduce((sum, value) => sum + value, 0);
  const order = raw.map((value, index) => ({ index, fraction: value - Math.floor(value) })).sort((a, b) => b.fraction - a.fraction);
  for (const item of order) {
    if (remainder <= 0) break;
    values[item.index] += 1;
    remainder -= 1;
  }
  return values;
}

function quantile(values: number[], percentile: number): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.max(0, Math.floor((sorted.length - 1) * percentile)));
  return sorted[index];
}
