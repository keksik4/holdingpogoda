import { Megaphone, Settings, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/cn";

type RecommendationKind = "operations" | "marketing" | "risk";

interface RecommendationCardProps {
  title: string;
  items: string[];
  kind?: RecommendationKind;
}

export function RecommendationCard({ title, items, kind = "operations" }: RecommendationCardProps) {
  const Icon = kind === "marketing" ? Megaphone : kind === "risk" ? ShieldCheck : Settings;
  return (
    <section className="soft-panel p-6 md:p-7">
      <div className="flex items-center gap-4">
        <Icon className="h-8 w-8 text-ink" strokeWidth={1.3} />
        <h2 className="font-display text-[24px] leading-none tracking-[-0.04em] text-ink">{title}</h2>
      </div>
      <div className="mt-5 divide-y divide-line">
        {items.length ? (
          items.map((item, index) => (
            <div key={`${item}-${index}`} className="flex gap-4 py-3.5 first:pt-0 last:pb-0">
              <span
                className={cn(
                  "mt-1 h-2 w-2 flex-none rounded-full",
                  kind === "marketing" ? "bg-air-teal" : kind === "risk" ? "bg-risk-orange" : "bg-air-blue"
                )}
              />
              <p className="font-body text-sm leading-6 text-ink">{item}</p>
            </div>
          ))
        ) : (
          <p className="font-body text-sm text-ink-soft">Backend nie zwrócił rekomendacji dla tego dnia.</p>
        )}
      </div>
    </section>
  );
}
