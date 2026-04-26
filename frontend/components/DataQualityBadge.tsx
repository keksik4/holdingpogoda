import { cn } from "@/lib/cn";
import { dataQualityShort } from "@/lib/formatting";

interface DataQualityBadgeProps {
  label?: string;
  source?: "backend" | "demo_fallback";
  compact?: boolean;
}

export function DataQualityBadge({ label, source, compact = false }: DataQualityBadgeProps) {
  const finalLabel = source === "demo_fallback" ? "Tryb zapasowy - backend niedostępny" : label;
  const tone = toneFor(finalLabel);
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1 font-body text-[11px] leading-none tracking-[0.01em]",
        compact && "px-2 py-0.5 text-[10px]",
        tone
      )}
      title={dataQualityShort(finalLabel)}
    >
      {dataQualityShort(finalLabel)}
    </span>
  );
}

function toneFor(label?: string): string {
  const value = (label ?? "").toLowerCase();
  if (value.includes("fallback") || value.includes("zapas")) return "border-risk-orange/20 bg-[#fff7f2] text-risk-orange";
  if (value.includes("calibrated") || value.includes("demo")) return "border-air-teal/20 bg-[#f1fbfc] text-air-teal";
  if (value.includes("weather") || value.includes("pogod")) return "border-air-blue/20 bg-[#f3f8fe] text-ink-soft";
  if (value.includes("benchmark")) return "border-risk-green/20 bg-[#f4faf6] text-risk-green";
  return "border-line bg-white/80 text-ink-soft";
}
