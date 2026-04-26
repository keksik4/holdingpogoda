import { CloudRain, Gauge, ThermometerSun, Wind } from "lucide-react";
import { DataQualityBadge } from "@/components/DataQualityBadge";
import { WeatherIcon } from "@/components/WeatherIcon";
import { riskLabel, riskTone } from "@/lib/formatting";
import type { RiskLevel, WeatherDetails } from "@/lib/types";

interface WeatherSummaryCardProps {
  details: WeatherDetails;
  risk: RiskLevel;
}

export function WeatherSummaryCard({ details, risk }: WeatherSummaryCardProps) {
  const confidence = Math.round((details.forecast_confidence ?? 0) * 100);
  const impact = Math.round(details.weather_impact_score ?? 0);
  const providerState =
    details.data_quality_label.toLowerCase().includes("proxy") || details.data_quality_label.toLowerCase().includes("fallback")
      ? "Sygnał zastępczy"
      : "Konsensus gotowy";
  return (
    <section className="soft-panel p-6 md:p-7">
      <div className="flex items-start gap-5">
        <WeatherIcon icon={details.weather_icon} tone={risk === "high" ? "orange" : "teal"} className="h-12 w-12" />
        <div>
          <p className="font-body text-sm text-air-teal">Prognoza pogody</p>
          <h2 className="mt-2 font-display text-[28px] leading-none tracking-[-0.04em] text-ink">
            {details.temperature == null ? "Sygnał pogodowy" : `${Math.round(details.temperature)}°`}
          </h2>
        </div>
      </div>
      <div className="mt-7 grid grid-cols-2 gap-5 font-body">
        <Metric icon={Gauge} label="Pewność" value={`${confidence}%`} />
        <Metric icon={ThermometerSun} label="Wpływ pogody" value={`${impact > 0 ? "+" : ""}${impact}%`} />
        <Metric icon={CloudRain} label="Ryzyko pogodowe" value={riskLabel(risk)} valueClass={riskTone(risk)} />
        <Metric icon={Wind} label="Status źródeł" value={providerState} />
      </div>
      <div className="mt-6 rounded-[13px] bg-[#f7faf8] px-5 py-4">
        <p className="font-body text-sm leading-7 text-ink-soft">{details.note}</p>
      </div>
      <div className="mt-5">
        <DataQualityBadge label={details.data_quality_label} compact />
      </div>
    </section>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  valueClass
}: {
  icon: typeof Gauge;
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="mt-0.5 h-5 w-5 text-ink-soft" strokeWidth={1.45} />
      <div>
        <p className="text-xs text-ink-soft">{label}</p>
        <p className={valueClass ?? "text-ink"}>{value}</p>
      </div>
    </div>
  );
}
