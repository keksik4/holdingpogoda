"use client";

import { Loader2 } from "lucide-react";

interface LoadingOverlayProps {
  visible: boolean;
  label?: string;
}

export function LoadingOverlay({ visible, label = "Ładowanie miesiąca…" }: LoadingOverlayProps) {
  if (!visible) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="loading-overlay fixed inset-0 z-50 flex items-center justify-center bg-ink/15 backdrop-blur-[2px]"
    >
      <div className="flex items-center gap-3 rounded-[14px] border border-line bg-white px-5 py-3 shadow-soft">
        <Loader2 className="h-5 w-5 animate-spin text-brand-blue" strokeWidth={1.6} />
        <span className="font-body text-sm font-semibold text-ink">{label}</span>
      </div>
    </div>
  );
}
