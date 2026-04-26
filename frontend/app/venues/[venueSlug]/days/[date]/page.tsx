import Link from "next/link";
import { ArrowUpRight, CalendarDays, ChevronRight, Clock3, Database, Gauge, Megaphone, ShieldCheck, TrendingUp, UsersRound } from "lucide-react";
import { AppHeader } from "@/components/AppHeader";
import { DataQualityBadge } from "@/components/DataQualityBadge";
import { FallbackBanner } from "@/components/FallbackBanner";
import { HourlyVisitorsChart } from "@/components/HourlyVisitorsChart";
import { VenueImage } from "@/components/VenueImage";
import { WeatherIcon } from "@/components/WeatherIcon";
import {
  formatDateLabel,
  formatPercent,
  formatVisitors,
  loadLabel,
  providerLabel,
  relationLabel,
  riskLabel,
  riskTone,
  translateBackendText,
  translateRecommendation,
  weatherLabel
} from "@/lib/formatting";
import { getDayDetails, getVenueAssets } from "@/lib/api";
import type { DayDetailsResponse, HourlyVisitorPoint } from "@/lib/types";

interface DayDetailsPageProps {
  params: { venueSlug: string; date: string };
}

export default async function DayDetailsPage({ params }: DayDetailsPageProps) {
  const [detailsResult, assetsResult] = await Promise.all([getDayDetails(params.venueSlug, params.date), getVenueAssets(params.venueSlug)]);
  const details = detailsResult.data;
  const isFallback = detailsResult.source === "demo_fallback";
  const confidence = confidenceValue(details);
  const peakRange = peakHourRange(details);
  const providers = providerNames(details);

  return (
    <>
      <AppHeader active="forecasts" compact />
      <main className="product-screen">
        <FallbackBanner visible={isFallback} message={detailsResult.error} />

        <nav className="mb-2 flex items-center gap-2 font-body text-[11px] text-ink-soft">
          <Link href="/" className="hover:text-ink">Obiekty</Link>
          <ChevronRight className="h-3 w-3" strokeWidth={1.4} />
          <Link href={`/venues/${params.venueSlug}/calendar`} className="hover:text-ink">Kalendarz</Link>
          <ChevronRight className="h-3 w-3" strokeWidth={1.4} />
          <span className="border-b-2 border-air-blue pb-0.5 text-ink">Szczegóły dnia</span>
        </nav>

        <section className="grid grid-cols-1 items-center gap-4 lg:grid-cols-[1fr_360px]">
          <div className="min-w-0">
            <h1 className="truncate font-display text-[40px] font-extrabold leading-none tracking-[-0.055em] text-ink">{details.venue_info.name}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 font-body text-xs text-ink-soft">
              <span className="inline-flex items-center gap-1.5">
                <CalendarDays className="h-4 w-4 text-brand-blue" strokeWidth={1.45} />
                {formatDateLabel(details.selected_date)}
              </span>
              <span>{relationLabel(details.date_relation)}</span>
              <span>{details.venue_id ? `profil: ${details.venue_id}` : "profil operacyjny"}</span>
            </div>
          </div>
          <div className="hidden h-[92px] overflow-hidden rounded-[14px] border border-line bg-white shadow-soft lg:block">
            <VenueImage venueSlug={params.venueSlug} asset={assetsResult.data.assets[0] ?? details.venue_info.image_asset_status} className="h-full rounded-[14px]" />
          </div>
        </section>

        <section className="mt-3 grid grid-cols-2 gap-2 lg:grid-cols-6">
          <KpiCard icon={UsersRound} label="Frekwencja" value={formatVisitors(details.expected_visitors)} helper="osób" accent="blue" />
          <KpiCard icon={TrendingUp} label="Zakres" value={`${formatVisitors(details.low_base_high.low)}-${formatVisitors(details.low_base_high.high)}`} helper="osób" />
          <KpiCard icon={ShieldCheck} label="Ryzyko" value={riskLabel(details.weather_risk)} valueClass={riskTone(details.weather_risk)} helper="pogoda i ruch" />
          <KpiCard icon={Gauge} label="Pewność" value={confidence == null ? "Niska" : `${confidence}%`} helper="model" />
          <KpiCard
            icon={ArrowUpRight}
            label="Trend"
            value={formatPercent(details.comparison_to_typical_day.difference_percent ?? 0)}
            helper="vs typowy dzień"
            valueClass={(details.comparison_to_typical_day.difference_percent ?? 0) >= 0 ? "text-risk-green" : "text-risk-orange"}
          />
          <KpiCard icon={Clock3} label="Szczyt" value={peakRange} helper="okno operacyjne" />
        </section>

        <section className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-[1.05fr_0.8fr_0.7fr]">
          <div className="space-y-3">
            <HourlyVisitorsChart data={details.hourly_visitor_curve} expectedTotal={details.expected_visitors} selectedDateLabel={formatDateLabel(details.selected_date, "short")} compact />
            <WeatherConsensusPanel details={details} providers={providers} />
          </div>

          <div className="grid grid-cols-1 gap-3">
            <RecommendationPanel title="Operacje" icon={ShieldCheck} items={details.operations_recommendations} />
            <RecommendationPanel title="Marketing" icon={Megaphone} items={details.marketing_recommendations} />
            <HourlyLoadPanel rows={details.hourly_visitor_curve} />
          </div>

          <aside className="space-y-3">
            <SelectedDayCard details={details} confidence={confidence} providers={providers} />
            <FactorsCard details={details} />
          </aside>
        </section>
      </main>
    </>
  );
}

function KpiCard({
  icon: Icon,
  label,
  value,
  helper,
  valueClass,
  accent
}: {
  icon: typeof UsersRound;
  label: string;
  value: string;
  helper: string;
  valueClass?: string;
  accent?: "blue";
}) {
  return (
    <div className="metric-card flex min-h-[70px] items-center gap-2 px-3 py-2">
      <Icon className={accent === "blue" ? "h-6 w-6 text-brand-blue" : "h-5 w-5 text-brand-blue"} strokeWidth={1.45} />
      <div className="min-w-0">
        <p className="truncate font-body text-[10px] text-ink-soft">{label}</p>
        <p className={`mt-1 truncate font-body text-[19px] font-semibold leading-none tracking-[-0.04em] ${valueClass ?? "text-ink"}`}>{value}</p>
        <p className="mt-1 font-body text-[10px] text-ink-soft">{helper}</p>
      </div>
    </div>
  );
}

function WeatherConsensusPanel({ details, providers }: { details: DayDetailsResponse; providers: string[] }) {
  const consensus = details.weather_consensus;
  const probability = details.weather_details.precipitation_probability ?? consensus?.precipitationProbability ?? consensus?.precipitation_probability_avg;
  const temperature = details.weather_details.temperature ?? consensus?.temperatureC ?? consensus?.temperature_avg;
  const sourceEntries = Object.entries(consensus?.sources ?? {}).slice(0, 2);
  return (
    <div className="soft-panel p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-body text-sm font-semibold text-ink">Konsensus pogodowy</p>
          <p className="mt-1 font-body text-[11px] leading-4 text-ink-soft">{translateBackendText(details.weather_details.note)}</p>
        </div>
        <WeatherIcon icon={details.weather_details.weather_icon} tone={details.weather_risk === "high" ? "orange" : "teal"} className="h-8 w-8" />
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2">
        <MiniSignal label="Temp." value={temperature == null ? "brak" : `${Math.round(temperature)}°C`} />
        <MiniSignal label="Opad" value={probability == null ? "brak" : `${Math.round(probability)}%`} />
        <MiniSignal label="Rozbieżność" value={`${Math.round((details.provider_disagreement_score ?? consensus?.provider_disagreement_score ?? 0) * 100)}%`} />
        <MiniSignal label="Źródła" value={providers.length ? `${providers.length}` : "1"} />
      </div>
      <div className="mt-3 divide-y divide-line rounded-[10px] border border-line">
        {(sourceEntries.length ? sourceEntries : providers.map((provider) => [provider, undefined] as const)).slice(0, 3).map(([provider, source]) => (
          <div key={provider} className="grid grid-cols-[92px_1fr_52px] items-center gap-2 px-2 py-1.5 font-body text-[11px]">
            <span className="truncate text-ink-soft">{providerLabel(provider)}</span>
            <span className="truncate text-ink">{source?.conditionLabel ? translateBackendText(source.conditionLabel) : weatherLabel(details.weather_details.weather_icon)}</span>
            <span className="text-right text-ink-soft">{source?.temperatureC == null ? "" : `${Math.round(source.temperatureC)}°C`}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecommendationPanel({ title, icon: Icon, items }: { title: string; icon: typeof ShieldCheck; items: string[] }) {
  return (
    <section className="soft-panel p-3">
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5 text-brand-blue" strokeWidth={1.4} />
        <h2 className="font-display text-[18px] font-extrabold leading-none tracking-[-0.04em] text-ink">{title}</h2>
      </div>
      <div className="mt-2 divide-y divide-line">
        {items.length ? (
          items.slice(0, 3).map((item, index) => (
            <p key={`recommendation-${index}`} className="py-2 font-body text-[11px] leading-4 text-ink first:pt-0 last:pb-0">
              {translateRecommendation(item)}
            </p>
          ))
        ) : (
          <p className="font-body text-[11px] leading-4 text-ink-soft">Brak rekomendacji z backendu.</p>
        )}
      </div>
    </section>
  );
}

function HourlyLoadPanel({ rows }: { rows: HourlyVisitorPoint[] }) {
  const peakRows = [...rows].sort((a, b) => b.expected_visitors - a.expected_visitors).slice(0, 3);
  return (
    <section className="soft-panel p-3">
      <p className="font-body text-sm font-semibold text-ink">Najbardziej obciążone godziny</p>
      <div className="mt-2 space-y-1.5">
        {peakRows.map((row) => (
          <div key={`${row.hour}-${row.expected_visitors}`} className="grid grid-cols-[48px_1fr_70px] items-center gap-2 font-body text-[11px]">
            <span className="font-semibold text-ink">{row.hour}:00</span>
            <span className="truncate text-ink-soft">{loadLabel(row.load_level)} · {translateBackendText(row.operational_note)}</span>
            <span className="text-right font-semibold text-ink">{formatVisitors(row.expected_visitors)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function SelectedDayCard({ details, confidence, providers }: { details: DayDetailsResponse; confidence: number | null; providers: string[] }) {
  return (
    <section className="soft-panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-body text-sm font-semibold text-ink">Wybrany dzień</p>
          <p className="mt-1 font-body text-xs text-ink-soft">{formatDateLabel(details.selected_date)}</p>
        </div>
        {details.date_relation === "today" ? <span className="rounded-[8px] bg-brand-blue px-2.5 py-1 font-body text-[11px] font-semibold text-white">Dziś</span> : null}
      </div>
      <div className="mt-3 flex items-end gap-3">
        <WeatherIcon icon={details.weather_details.weather_icon} tone={details.weather_risk === "high" ? "orange" : "teal"} className="h-8 w-8" />
        <div>
          <p className="font-body text-[34px] font-semibold leading-none tracking-[-0.05em] text-brand-blue">{formatVisitors(details.expected_visitors)}</p>
          <p className="mt-1 font-body text-[11px] text-ink-soft">prognozowana frekwencja</p>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 border-y border-line py-3">
        <MiniSignal label="Pogoda" value={weatherLabel(details.weather_details.weather_icon, details.weather_details.label_pl)} />
        <MiniSignal label="Ryzyko" value={riskLabel(details.weather_risk)} valueClass={riskTone(details.weather_risk)} />
        <MiniSignal label="Pewność" value={confidence == null ? "Niska" : `${confidence}%`} />
        <MiniSignal label="Źródła" value={providers.length ? `${providers.length}` : "1"} />
      </div>
      <p className="mt-3 line-clamp-3 font-body text-[11px] leading-4 text-ink-soft">{translateBackendText(details.forecast_explanation ?? details.explanation)}</p>
    </section>
  );
}

function FactorsCard({ details }: { details: DayDetailsResponse }) {
  const factors = details.daily_factors ?? {};
  const checklist = details.risk_and_readiness.readiness_checklist ?? [];
  return (
    <section className="soft-panel p-4">
      <div className="flex items-center gap-2">
        <Database className="h-5 w-5 text-brand-blue" strokeWidth={1.45} />
        <p className="font-body text-sm font-semibold text-ink">Sygnały modelu</p>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <MiniSignal label="Baza" value={formatVisitors(factors.base_daily_visitors)} />
        <MiniSignal label="Tydzień" value={factorValue(factors.weekday_multiplier)} />
        <MiniSignal label="Sezon" value={factorValue(factors.seasonal_multiplier)} />
        <MiniSignal label="Pogoda" value={factorValue(factors.weather_multiplier)} />
      </div>
      <div className="mt-3 border-t border-line pt-2">
        {checklist.slice(0, 3).map((item, index) => (
          <p key={`checklist-${index}`} className="font-body text-[11px] leading-4 text-ink-soft">• {translateBackendText(item)}</p>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {(details.data_sources ?? ["holding_lodz_raw_profile"]).slice(0, 3).map((source) => (
          <DataQualityBadge key={source} label={source} compact />
        ))}
      </div>
    </section>
  );
}

function MiniSignal({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div>
      <p className="font-body text-[10px] text-ink-soft">{label}</p>
      <p className={`mt-0.5 truncate font-body text-xs font-semibold leading-5 ${valueClass ?? "text-ink"}`}>{value}</p>
    </div>
  );
}

function confidenceValue(details: DayDetailsResponse): number | null {
  const raw = details.confidence ?? details.calibration_confidence ?? details.weather_details.forecast_confidence ?? details.weather_consensus?.forecast_confidence_score;
  return typeof raw === "number" ? Math.round(raw * 100) : null;
}

function peakHourRange(details: DayDetailsResponse): string {
  const hours = details.peak_hours?.map((point) => point.hour) ?? details.hourly_visitor_curve.filter((point) => point.peak_hour_flag).map((point) => point.hour);
  if (!hours.length) return "W trakcie";
  return `${Math.min(...hours)}:00-${Math.max(...hours) + 1}:00`;
}

function providerNames(details: DayDetailsResponse): string[] {
  const fromSources = Object.keys(details.weather_consensus?.sources ?? {});
  if (fromSources.length) return fromSources;
  return details.providers_used ?? details.weather_consensus?.providers_used ?? [];
}

function factorValue(value?: number): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "brak";
  return `×${value.toFixed(2).replace(".00", "")}`;
}
