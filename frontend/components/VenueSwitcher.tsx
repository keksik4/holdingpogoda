import Link from "next/link";
import { PawPrint, Waves } from "lucide-react";
import { cn } from "@/lib/cn";
import type { VenueSummary } from "@/lib/types";

interface VenueSwitcherProps {
  venues: VenueSummary[];
  selectedSlug: string;
}

export function VenueSwitcher({ venues, selectedSlug }: VenueSwitcherProps) {
  return (
    <div className="flex w-full gap-2 overflow-x-auto pb-1 sm:flex-wrap sm:overflow-visible sm:pb-0">
      {venues.map((venue) => {
        const active = venue.slug === selectedSlug;
        const Icon = venue.slug === "orientarium_zoo_lodz" ? PawPrint : Waves;
        return (
          <Link
            key={venue.slug}
            href={`/venues/${venue.slug}/calendar`}
            className={cn(
              "flex min-w-[152px] items-center gap-2 rounded-[11px] border bg-white px-2.5 py-2 transition-air hover:-translate-y-0.5 hover:shadow-soft sm:min-w-[170px] sm:px-3",
              active ? "border-brand-blue/40 shadow-soft" : "border-line/80"
            )}
          >
            <span className={cn("flex h-8 w-8 items-center justify-center rounded-full border", active ? "border-ink bg-ink text-white" : "border-air-blue/40 bg-white text-air-blue")}>
              <Icon className="h-4 w-4" strokeWidth={1.3} />
            </span>
            <span className="min-w-0">
              <span className="block truncate font-body text-sm font-extrabold leading-none text-ink">{venue.name}</span>
              <span className="mt-1 block font-body text-[11px] text-ink-soft">{venue.city}</span>
            </span>
          </Link>
        );
      })}
    </div>
  );
}
