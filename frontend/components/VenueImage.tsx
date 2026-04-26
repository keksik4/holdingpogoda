"use client";

import { useState } from "react";
import { ImageOff } from "lucide-react";
import { LodzLineArt } from "@/components/LodzLineArt";
import { cn } from "@/lib/cn";
import { assetUrl } from "@/lib/formatting";
import type { VenueAsset, VenueAssetStatus } from "@/lib/types";

interface VenueImageProps {
  venueSlug: string;
  asset?: VenueAsset | VenueAssetStatus | null;
  className?: string;
}

export function VenueImage({ venueSlug, asset, className }: VenueImageProps) {
  const [failed, setFailed] = useState(false);
  const url = failed ? null : assetUrl(asset);
  const isZoo = venueSlug === "orientarium_zoo_lodz";
  const position = isZoo ? "object-[center_52%]" : "object-[center_72%]";

  if (url) {
    return (
      <div className={cn("relative overflow-hidden rounded-t-[15px] bg-[#eef6fc]", className)}>
        <img
          src={url}
          alt=""
          className={cn("h-full w-full object-cover saturate-[0.92] transition-air duration-700 group-hover:scale-[1.025]", position)}
          onError={() => setFailed(true)}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/5 to-white" />
      </div>
    );
  }

  return (
    <div className={cn("relative overflow-hidden rounded-t-[15px] bg-[#f5f9fd]", className)}>
      <div className="absolute inset-x-0 top-4 mx-auto flex w-max items-center gap-2 rounded-full border border-line bg-white/90 px-3 py-1 font-body text-[11px] text-ink-soft">
        <ImageOff className="h-3.5 w-3.5" strokeWidth={1.4} />
        Zdjęcie w przygotowaniu
      </div>
      <LodzLineArt variant={isZoo ? "zoo" : "aquapark"} className="absolute bottom-0 left-1/2 w-[122%] -translate-x-1/2 opacity-80" />
      <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-white to-white/0" />
    </div>
  );
}
