import { WeatherIcon } from "@/components/WeatherIcon";
import { RiskDot } from "@/components/RiskDot";
import { DataQualityBadge } from "@/components/DataQualityBadge";
import { formatVisitors } from "@/lib/formatting";
import type { ApiSource, HoverPreview } from "@/lib/types";

interface VenueHoverPreviewProps {
  preview?: HoverPreview;
  source?: ApiSource;
}

const fallbackItems = [
  { label: "Dzisiaj", key: "today_expected_visitors" },
  { label: "Jutro", key: "tomorrow_expected_visitors" },
  { label: "Pojutrze", key: "day_after_tomorrow_expected_visitors" }
] as const;

export function VenueHoverPreview({ preview, source }: VenueHoverPreviewProps) {
  if (!preview) return null;
  const items = preview.days?.length
    ? preview.days
    : fallbackItems.map((item) => ({
        label: item.label,
        expected_visitors: preview[item.key],
        weather_icon: preview.weather_icon,
        risk_level: preview.risk_label,
        confidence_score: preview.confidence
      }));

  return (
    <div className="mx-2 mb-2 rounded-[12px] border border-line bg-[#fbfdff] px-1.5 py-2 sm:mx-5 sm:mb-5 sm:rounded-[14px] sm:px-3 sm:py-3">
      <div className="grid grid-cols-3 divide-x divide-line">
        {items.map((item, index) => (
          <div key={`${item.label}-${index}`} className="px-1 text-center sm:px-3">
            <p className="font-body text-[9px] font-semibold text-ink sm:text-[12px]">{item.label}</p>
            <p className="mt-1 font-body text-[13px] leading-none tracking-[-0.03em] text-ink sm:text-[24px]">{formatVisitors(item.expected_visitors)}</p>
            <p className="mt-1 font-body text-[9px] text-ink-soft sm:text-[11px]">osób</p>
            <div className="mt-1.5 flex items-center justify-center gap-1 sm:mt-2 sm:gap-2">
              <WeatherIcon icon={item.weather_icon} className="h-3.5 w-3.5 sm:h-5 sm:w-5" tone={index === 1 ? "teal" : "muted"} />
              <RiskDot risk={item.risk_level} withLabel />
            </div>
            {typeof item.confidence_score === "number" ? (
              <p className="mt-1 hidden font-body text-[10px] text-ink-soft sm:block">Pewność {Math.round(item.confidence_score * 100)}%</p>
            ) : null}
          </div>
        ))}
      </div>
      <div className="mt-2 flex justify-center sm:mt-3">
        <DataQualityBadge label={preview.data_quality_label} source={source} compact />
      </div>
    </div>
  );
}
