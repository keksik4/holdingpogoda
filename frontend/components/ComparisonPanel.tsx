import { BarChart3 } from "lucide-react";
import { formatPercent, formatVisitors } from "@/lib/formatting";
import type { ComparisonToTypicalDay } from "@/lib/types";

interface ComparisonPanelProps {
  comparison: ComparisonToTypicalDay;
  venueName: string;
}

export function ComparisonPanel({ comparison, venueName }: ComparisonPanelProps) {
  const difference = comparison.difference ?? 0;
  const differencePercent = comparison.difference_percent ?? 0;
  return (
    <section className="soft-panel p-6 md:p-7">
      <div className="flex items-center gap-4">
        <BarChart3 className="h-8 w-8 text-ink" strokeWidth={1.3} />
        <div>
          <h2 className="font-display text-[26px] leading-none tracking-[-0.04em] text-ink">Porównanie z typowym dniem</h2>
          <p className="mt-2 font-body text-sm text-ink-soft">Na tle podobnych dni dla obiektu {venueName}</p>
        </div>
      </div>
      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-[1fr_1fr_1.4fr]">
        <Metric label="Frekwencja" value={formatPercent(differencePercent)} helper="wobec typowego dnia" />
        <Metric label="Różnica liczby osób" value={formatVisitors(difference)} helper="odwiedzających więcej / mniej" />
        <div className="rounded-[13px] bg-[#f3f8fc] px-6 py-5 font-body text-sm leading-7 text-ink-soft">
          {difference >= 0
            ? "Ten dzień zapowiada się na bardziej obciążony niż zwykle. Warto utrzymać widoczne plany obsady i kolejek."
            : "Ten dzień wygląda spokojniej niż zwykle. Zachowaj ostrożny budżet komunikacji i obserwuj aktualizacje pogody."}
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value, helper }: { label: string; value: string; helper: string }) {
  return (
    <div className="border-r border-line pr-6 last:border-r-0">
      <p className="font-body text-sm text-ink">{label}</p>
      <p className="mt-4 font-body text-[32px] leading-none tracking-[-0.04em] text-air-teal">{value}</p>
      <p className="mt-2 font-body text-xs text-ink-soft">{helper}</p>
    </div>
  );
}
