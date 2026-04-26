import { CheckCircle2, ShieldCheck } from "lucide-react";
import { RiskDot } from "@/components/RiskDot";
import type { RiskAndReadiness } from "@/lib/types";

interface RiskReadinessCardProps {
  readiness: RiskAndReadiness;
}

export function RiskReadinessCard({ readiness }: RiskReadinessCardProps) {
  return (
    <section className="soft-panel p-6 md:p-7">
      <div className="flex items-center gap-4">
        <ShieldCheck className="h-8 w-8 text-ink" strokeWidth={1.3} />
        <h2 className="font-display text-[24px] leading-none tracking-[-0.04em] text-ink">Ryzyko i gotowość</h2>
      </div>
      <div className="mt-5 space-y-4 border-b border-line pb-5 font-body text-sm">
        <div className="flex items-center justify-between gap-4">
          <span className="text-ink">Ryzyko pogodowe</span>
          <RiskDot risk={readiness.weather_risk ?? readiness.risk_level ?? "unknown"} withLabel />
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-ink">Ryzyko frekwencji</span>
          <RiskDot risk={readiness.crowd_risk ?? readiness.risk_level ?? "unknown"} withLabel />
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-ink">Gotowość operacyjna</span>
          <span className="text-risk-green">{readiness.operational_readiness ?? "Dobra"}</span>
        </div>
      </div>
      <div className="mt-5">
        <p className="font-body text-sm font-medium text-ink">Lista gotowości</p>
        <div className="mt-4 space-y-3">
          {(readiness.readiness_checklist ?? []).slice(0, 7).map((item) => (
            <div key={item} className="flex items-center gap-3 font-body text-sm text-ink-soft">
              <CheckCircle2 className="h-4 w-4 text-air-teal" strokeWidth={1.5} />
              <span>{sentenceCase(item)}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function sentenceCase(value: string): string {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
}
