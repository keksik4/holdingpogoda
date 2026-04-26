"use client";

import { useState } from "react";
import { VenueCard } from "@/components/VenueCard";
import type { ApiSource, VenueAsset, VenueSummary } from "@/lib/types";

interface VenueCardsProps {
  venues: VenueSummary[];
  assetsByVenue: Record<string, VenueAsset | null>;
  source: ApiSource;
}

export function VenueCards({ venues, assetsByVenue, source }: VenueCardsProps) {
  const [activeSlug, setActiveSlug] = useState(venues[0]?.slug);

  return (
    <div className="relative grid grid-cols-2 gap-2 sm:gap-5">
      {venues.map((venue) => (
        <VenueCard
          key={venue.slug}
          venue={venue}
          asset={assetsByVenue[venue.slug]}
          source={source}
          active={venue.slug === activeSlug}
          onActivate={() => setActiveSlug(venue.slug)}
        />
      ))}
    </div>
  );
}
