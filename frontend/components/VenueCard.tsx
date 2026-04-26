"use client";

import { KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowRight, MapPin, PawPrint, Waves } from "lucide-react";
import { VenueHoverPreview } from "@/components/VenueHoverPreview";
import { VenueImage } from "@/components/VenueImage";
import { cn } from "@/lib/cn";
import { venueDescription, venueKindLabel, weatherSensitivityLabel, weatherSensitivityTone } from "@/lib/formatting";
import type { ApiSource, VenueAsset, VenueSummary } from "@/lib/types";

interface VenueCardProps {
  venue: VenueSummary;
  asset?: VenueAsset | null;
  active: boolean;
  source: ApiSource;
  onActivate: () => void;
}

export function VenueCard({ venue, asset, active, source, onActivate }: VenueCardProps) {
  const router = useRouter();
  const isZoo = venue.slug === "orientarium_zoo_lodz";
  const Icon = isZoo ? PawPrint : Waves;
  const sensitivityTone = weatherSensitivityTone(venue.weather_sensitivity_label);

  const openVenue = () => router.push(`/venues/${venue.slug}/calendar`);
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openVenue();
    }
  };

  return (
    <motion.article
      tabIndex={0}
      role="button"
      aria-label={`Otwórz prognozę dla ${venue.name}`}
      onClick={openVenue}
      onKeyDown={onKeyDown}
      onMouseEnter={onActivate}
      onFocus={onActivate}
      layout
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 180, damping: 22 }}
      className={cn(
        "group relative min-w-0 cursor-pointer overflow-hidden rounded-[16px] border bg-white shadow-soft outline-none transition-air focus-visible:ring-2 focus-visible:ring-air-blue/50",
        active ? "border-brand-blue/70 shadow-air" : "border-line hover:border-brand-blue/40"
      )}
    >
      <VenueImage venueSlug={venue.slug} asset={asset ?? venue.image_asset_status} className="h-[74px] sm:h-[178px]" />
      <div className="absolute left-2 top-2 flex h-8 w-8 items-center justify-center rounded-full bg-white text-brand-blue shadow-soft ring-1 ring-line sm:left-5 sm:top-5 sm:h-12 sm:w-12">
        <Icon className="h-4.5 w-4.5 sm:h-6 sm:w-6" strokeWidth={1.25} />
      </div>
      <div className="px-2.5 pb-2 pt-2.5 sm:px-6 sm:pb-5 sm:pt-5">
        <p className="font-body text-[10px] font-semibold text-brand-blue sm:text-xs">{venueKindLabel(venue.type)}</p>
        <h2 className="mt-0.5 line-clamp-2 font-display text-[17px] font-extrabold leading-[1.02] tracking-[-0.055em] text-ink sm:mt-1 sm:text-[28px]">{venue.name}</h2>
        <div className="mt-1.5 flex items-center gap-1.5 font-body text-[11px] text-ink-soft sm:mt-3 sm:gap-2 sm:text-[14px]">
          <MapPin className="h-3.5 w-3.5 sm:h-4 sm:w-4" strokeWidth={1.45} />
          <span>{venue.city}</span>
        </div>
        <p className="mt-2 hidden max-w-[34rem] font-body text-[14px] leading-6 text-ink sm:block sm:min-h-[48px]">
          {venueDescription(venue.slug, venue.short_description)}
        </p>
        <div className="mt-2 border-t border-line pt-2 sm:mt-4 sm:pt-3">
          <div className={cn("flex items-center gap-1.5 font-body text-[10px] sm:gap-3 sm:text-xs", sensitivityTone === "orange" ? "text-risk-orange" : "text-brand-blue")}>
            <Icon className="h-5 w-5" strokeWidth={1.2} />
            <span className="line-clamp-1">{weatherSensitivityLabel(venue.weather_sensitivity_label)}</span>
          </div>
        </div>
      </div>
      <VenueHoverPreview preview={venue.hover_preview} source={source} />
      <div className="flex items-center justify-center border-t border-line px-2 py-2 font-body text-xs font-semibold text-brand-blue sm:px-6 sm:py-3 sm:text-sm">
        Otwórz moduł
        <ArrowRight className="ml-2 h-4 w-4" strokeWidth={1.6} />
      </div>
    </motion.article>
  );
}
