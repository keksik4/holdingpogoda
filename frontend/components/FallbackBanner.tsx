import { AlertCircle } from "lucide-react";

interface FallbackBannerProps {
  visible: boolean;
  message?: string;
}

export function FallbackBanner({ visible, message }: FallbackBannerProps) {
  if (!visible) return null;
  return (
    <div className="fixed bottom-5 left-5 z-20 flex max-w-[calc(100vw-2.5rem)] items-center gap-3 rounded-full border border-risk-orange/20 bg-[#fff8f4]/95 px-4 py-2 font-body text-xs text-ink shadow-soft backdrop-blur-sm">
      <AlertCircle className="h-4 w-4 flex-none text-risk-orange" strokeWidth={1.5} />
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <p className="font-semibold text-risk-orange">Tryb zapasowy</p>
        <p className="text-ink-soft">{message ?? "Backend jest niedostępny. Widok używa danych szacunkowych."}</p>
      </div>
    </div>
  );
}
