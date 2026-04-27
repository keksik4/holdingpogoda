import type { RiskLevel, VenueAsset, VenueAssetStatus } from "@/lib/types";

export function formatVisitors(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "Dane szacunkowe";
  return new Intl.NumberFormat("pl-PL").format(Math.round(value));
}

export function formatPercent(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "0%";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1).replace(".0", "")}%`;
}

export function formatDateLabel(dateString: string, style: "short" | "long" = "long"): string {
  const date = parseDateString(dateString);
  return new Intl.DateTimeFormat("pl-PL", {
    weekday: style === "long" ? "long" : "short",
    month: style === "long" ? "long" : "short",
    day: "numeric"
  }).format(date);
}

export function formatMonthTitle(month: string): string {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Intl.DateTimeFormat("pl-PL", { month: "long", year: "numeric" }).format(new Date(year, monthNumber - 1, 1));
}

export function addMonths(month: string, delta: number): string {
  const [year, monthNumber] = month.split("-").map(Number);
  const next = new Date(year, monthNumber - 1 + delta, 1);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`;
}

export function parseDateString(dateString: string): Date {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function toDateString(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function riskLabel(risk: RiskLevel | undefined): string {
  if (risk === "low") return "Niskie";
  if (risk === "medium") return "Średnie";
  if (risk === "high") return "Wysokie";
  return "Brak oceny";
}

export function riskTone(risk: RiskLevel | undefined): string {
  if (risk === "low") return "text-risk-green";
  if (risk === "medium") return "text-risk-amber";
  if (risk === "high") return "text-risk-orange";
  return "text-ink-soft";
}

export function dataQualityShort(label?: string): string {
  if (!label) return "Dane szacunkowe";
  const normalized = normalize(label);
  if (normalized.includes("części") || normalized.includes("czesci") || normalized.includes("partial")) return "Dane częściowe";
  if (normalized.includes("brak drugiego")) return "Brak drugiego źródła";
  if (normalized.includes("fallback") || normalized.includes("zapas")) return "Tryb zapasowy";
  if (normalized.includes("calibrated") || normalized.includes("demo")) return "Estymacja";
  if (normalized.includes("benchmark")) return "Benchmark publiczny";
  if (normalized.includes("weather") || normalized.includes("pogod")) return "Pogoda";
  if (normalized.includes("backend")) return "Backend";
  if (normalized.includes("holding")) return "Profil operacyjny";
  if (normalized.includes("real")) return "Dane API";
  return translateBackendText(label);
}

export function assetUrl(asset?: VenueAsset | VenueAssetStatus | null): string | null {
  if (!asset) return null;
  const isLocalAllowed = asset.usage_status === "manual_asset_available" || Boolean(asset.file_exists);
  if (isLocalAllowed && asset.local_path) {
    return `/${asset.local_path.replace(/\\/g, "/").replace(/^public\//, "")}`;
  }
  if ("source_url" in asset && asset.usage_status === "remote_asset_allowed" && asset.source_url) {
    return asset.source_url;
  }
  return null;
}

export function venueKindLabel(type: string): string {
  const normalized = normalize(type);
  if (normalized.includes("aquapark")) return "Aquapark";
  if (normalized.includes("zoo")) return "Zoo / atrakcja całoroczna";
  return translateBackendText(type);
}

export function weatherSensitivityTone(label: string): "teal" | "orange" {
  const normalized = normalize(label);
  return normalized.includes("outdoor-heavy") || normalized.includes("zewn") ? "orange" : "teal";
}

export function weatherSensitivityLabel(label: string): string {
  const normalized = normalize(label);
  if (normalized.includes("outdoor-heavy") || normalized.includes("zewn")) return "Silna wrażliwość na pogodę";
  if (normalized.includes("mixed") || normalized.includes("miesz")) return "Mieszana wrażliwość pogodowa";
  return translateBackendText(label);
}

export function venueDescription(venueSlug: string, fallback: string): string {
  if (venueSlug === "aquapark_fala") {
    return "Całoroczny aquapark z basenami, zjeżdżalniami, saunami i letnią strefą zewnętrzną.";
  }
  if (venueSlug === "orientarium_zoo_lodz") {
    return "Zoo i Orientarium z pawilonami, ekspozycjami zewnętrznymi oraz ruchem rodzinnym i turystycznym.";
  }
  return translateBackendText(fallback);
}

export function providerLabel(provider: string): string {
  const normalized = normalize(provider);
  if (normalized.includes("openweather")) return "OpenWeather";
  if (normalized.includes("open-meteo") || normalized.includes("openmeteo")) return "Open-Meteo";
  if (normalized.includes("meteosource")) return "Meteosource";
  if (normalized.includes("met-no")) return "MET Norway";
  if (normalized.includes("imgw")) return "IMGW";
  if (normalized.includes("seasonal")) return "Sygnał sezonowy";
  return translateBackendText(provider);
}

export function relationLabel(value?: string): string {
  if (value === "historical") return "dzień historyczny";
  if (value === "today") return "dzisiaj";
  if (value === "forecast") return "prognoza";
  return "prognoza";
}

export function weatherLabel(icon?: string, fallback?: string | null): string {
  const normalized = normalize(icon ?? "");
  if (fallback) return translateBackendText(fallback);
  if (normalized.includes("storm")) return "Burza";
  if (normalized.includes("rain") || normalized.includes("shower")) return "Deszcz";
  if (normalized.includes("snow")) return "Śnieg";
  if (normalized.includes("partly") || normalized.includes("mixed")) return "Zmienne warunki";
  if (normalized.includes("sun")) return "Słonecznie";
  if (normalized.includes("cloud")) return "Pochmurno";
  if (normalized.includes("wind")) return "Wiatr";
  return "Dane pogodowe";
}

export function loadLabel(value?: string): string {
  const normalized = normalize(value ?? "");
  if (normalized === "krytyczny" || normalized === "critical") return "Krytyczny";
  if (normalized === "wysoki" || normalized === "high") return "Wysoki";
  if (normalized === "średni" || normalized === "sredni" || normalized === "medium") return "Średni";
  if (normalized === "niski" || normalized === "low") return "Niski";
  return "Szacunkowy";
}

export function translateBackendText(value?: string | null): string {
  if (!value) return "Dane szacunkowe";

  const cleaned = value.trim();
  const normalized = normalize(cleaned);
  const exact: Record<string, string> = {
    calibrated_to_public_benchmark: "kalibracja do benchmarku publicznego",
    public_benchmark_calibrated_demo_attendance: "estymacja kalibrowana benchmarkiem publicznym",
    holding_lodz_raw_profile: "profil operacyjny Holding Łódź",
    openmeteo: "Open-Meteo",
    openweather: "OpenWeather",
    meteosource: "Meteosource",
    "seasonal-calibration-proxy": "estymacja sezonowa",
    historical: "dzień historyczny",
    forecast: "prognoza",
    today: "dzisiaj",
    "entry queues": "kolejki wejściowe",
    lifeguards: "ratownicy",
    "outdoor pools": "baseny zewnętrzne",
    gastronomy: "gastronomia",
    parking: "parking",
    "feeding windows": "godziny karmień",
    "school groups": "grupy szkolne",
    "good": "dobra",
    "scenario planning": "plan wariantowy",
    "real weather api consensus where providers are available; calibrated proxy otherwise": "konsensus pogodowy API tam, gdzie dostawcy są dostępni; w pozostałych dniach estymacja sezonowa",
    "real weather api consensus where available": "konsensus pogodowy API",
    "weather consensus or calibrated proxy": "konsensus pogody lub estymacja",
    "calibrated demo attendance": "kalibrowana estymacja frekwencji",
    "mixed indoor/outdoor aquapark": "aquapark mieszany",
    "zoo and indoor-outdoor attraction": "zoo i atrakcja całoroczna",
    low: "niskie",
    medium: "średnie",
    high: "wysokie",
    critical: "krytyczne"
  };
  if (exact[cleaned] || exact[normalized]) return exact[cleaned] ?? exact[normalized];

  const peakMatch = cleaned.match(/Plan peak coverage around\s+(.+?)\.?$/i);
  if (peakMatch) {
    return `Zaplanuj wzmocnioną obsadę w godzinach ${peakMatch[1].replace(/\s+-\s+/g, "-")}.`;
  }

  return cleaned
    .replace(/_/g, " ")
    .replace(/weekend \/ holiday \/ hot: critical pool load/gi, "weekend, święto lub upał: bardzo wysokie obciążenie basenów")
    .replace(/weekend \/ holiday \/ hot/gi, "weekend, święto lub upał")
    .replace(/critical pool load/gi, "bardzo wysokie obciążenie basenów")
    .replace(/critical entry queues/gi, "bardzo wysokie obciążenie wejścia")
    .replace(/critical zoo load/gi, "bardzo wysokie obciążenie zoo")
    .replace(/entry queues/gi, "kolejki wejściowe")
    .replace(/lifeguards/gi, "ratownicy")
    .replace(/outdoor pools/gi, "baseny zewnętrzne")
    .replace(/feeding windows/gi, "godziny karmień")
    .replace(/school groups/gi, "grupy szkolne")
    .replace(/Plan peak coverage around/gi, "Zaplanuj wzmocnioną obsadę w godzinach")
    .replace(/peak/gi, "szczyt")
    .replace(/Good/g, "Dobra")
    .replace(/Scenario planning/g, "Plan wariantowy")
    .replace(/Real weather API consensus where providers are available; calibrated proxy otherwise/g, "Konsensus pogodowy API tam, gdzie dostawcy są dostępni; w pozostałych dniach estymacja sezonowa")
    .replace(/Real weather API consensus where available/g, "Konsensus pogodowy API")
    .replace(/Weather consensus or calibrated proxy/g, "Konsensus pogody lub estymacja")
    .replace(/Calibrated demo attendance/g, "Kalibrowana estymacja frekwencji")
    .replace(/official public benchmark/gi, "benchmark publiczny")
    .replace(/mixed indoor\/outdoor aquapark/gi, "aquapark mieszany")
    .replace(/zoo and indoor-outdoor attraction/gi, "zoo i atrakcja całoroczna")
    .replace(/\blow\b/gi, "niskie")
    .replace(/\bmedium\b/gi, "średnie")
    .replace(/\bhigh\b/gi, "wysokie")
    .replace(/\bcritical\b/gi, "krytyczne");
}

export function translateRecommendation(text: string): string {
  const peakMatch = text.match(/Plan peak coverage around\s+(.+?)\.?$/i);
  if (peakMatch) {
    return `Zaplanuj wzmocnioną obsadę w godzinach ${peakMatch[1].replace(/\s+-\s+/g, "-")}.`;
  }

  const dictionary: Record<string, string> = {
    "Prepare high-capacity staffing, queue lanes, parking overflow and cleaning rounds.":
      "Przygotuj maksymalną obsadę, dodatkowe kolejki, parking rezerwowy i częstsze obchody czystości.",
    "Prepare reinforced staffing, queue monitoring, parking guidance and cleaning rounds.":
      "Wzmocnij obsadę, monitoruj kolejki, ustaw wsparcie parkingowe i zaplanuj częstsze sprzątanie.",
    "Use standard staffing with a small flexible support pool.":
      "Utrzymaj standardową obsadę z małą rezerwą elastyczną.",
    "Weather risk is high, so prepare indoor routing and scenario staffing.":
      "Ryzyko pogodowe jest wysokie, przygotuj trasy wewnętrzne i wariantową obsadę.",
    "Use weather-positive campaign messaging for family and day-trip audiences.":
      "Użyj pogodowego komunikatu dla rodzin i gości planujących jednodniowy wyjazd.",
    "Emphasize indoor Orientarium resilience and timed-ticket planning.":
      "Podkreśl odporność pawilonów Orientarium i zachęcaj do planowania godzin wejścia.",
    "Keep spend aligned with demand; avoid over-boosting when confidence is moderate.":
      "Utrzymaj budżet zgodnie z popytem; przy umiarkowanej pewności unikaj nadmiernego boostu."
  };
  return dictionary[text] ?? translateBackendText(text);
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}
