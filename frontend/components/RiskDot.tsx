import { cn } from "@/lib/cn";
import { riskLabel } from "@/lib/formatting";
import type { RiskLevel } from "@/lib/types";

interface RiskDotProps {
  risk: RiskLevel;
  withLabel?: boolean;
}

export function RiskDot({ risk, withLabel = false }: RiskDotProps) {
  const color =
    risk === "low" ? "bg-risk-green" : risk === "medium" ? "bg-risk-amber" : risk === "high" ? "bg-risk-orange" : "bg-line";
  return (
    <span className="inline-flex items-center gap-1.5 font-body text-xs text-ink-soft sm:gap-2">
      <span className={cn("h-1.5 w-1.5 rounded-full sm:h-2 sm:w-2", color)} aria-hidden="true" />
      {withLabel ? <span className="hidden sm:inline">{riskLabel(risk)}</span> : null}
    </span>
  );
}
