import { Star } from "lucide-react";
import { RiskDot } from "@/components/RiskDot";
import { WeatherIcon } from "@/components/WeatherIcon";
import { cn } from "@/lib/cn";
import { formatVisitors } from "@/lib/formatting";
import type { CalendarDay } from "@/lib/types";

interface CalendarDayCellProps {
  day?: CalendarDay;
  dayNumber?: number;
  venueSlug: string;
  currentDate?: string;
  selected?: boolean;
  onSelect?: (date: string) => void;
}

export function CalendarDayCell({ day, dayNumber, currentDate, selected, onSelect }: CalendarDayCellProps) {
  if (!day) {
    return (
      <div className="h-[42px] rounded-[7px] border border-line/45 bg-white/35 p-0.5 text-ink-soft/35 sm:h-[92px] sm:rounded-[8px] sm:p-2 2xl:h-[98px]">
        <span className="font-body text-[10px] sm:text-xs">{dayNumber}</span>
      </div>
    );
  }

  const isToday = day.date === currentDate || day.date_relation === "today";
  const isHistorical = day.date_relation === "historical";

  return (
    <button
      type="button"
      onClick={() => onSelect?.(day.date)}
      className={cn(
        "group relative flex h-[42px] w-full min-w-0 flex-col overflow-hidden rounded-[7px] border border-line bg-white p-0.5 text-left transition-air hover:-translate-y-0.5 hover:border-air-blue/55 hover:shadow-soft sm:h-[92px] sm:rounded-[8px] sm:p-2 2xl:h-[98px]",
        isHistorical && "bg-white/65 text-ink-soft",
        day.best_day && "bg-[#f7fbf6] ring-1 ring-risk-green/20",
        isToday && "border-air-blue bg-[#f8fcff] shadow-soft ring-1 ring-air-blue/40",
        selected && "border-brand-blue bg-[#f7fbff] ring-2 ring-brand-blue/45"
      )}
      aria-label={`Wybierz dzień ${day.day_number}`}
    >
      <div className="flex items-start justify-between gap-1">
        <span className="font-body text-[9px] font-semibold leading-none text-ink sm:text-xs">{day.day_number}</span>
        {isToday ? (
          <span className="hidden rounded-full bg-air-blue/10 px-1.5 py-0.5 font-body text-[9px] font-semibold text-air-blue sm:block">Dziś</span>
        ) : day.best_day ? (
          <Star className="hidden h-3 w-3 fill-ink text-ink sm:block" strokeWidth={1.2} />
        ) : null}
      </div>
      <div className="flex flex-1 flex-col items-center justify-center text-center sm:mt-0.5">
        <WeatherIcon icon={day.weather_icon} className="h-3 w-3 sm:h-5 sm:w-5 2xl:h-6 2xl:w-6" tone={day.risk_level === "high" ? "orange" : "navy"} />
        <p className="mt-px max-w-full truncate font-body text-[8px] leading-none tracking-[-0.03em] text-ink sm:mt-1 sm:text-[14px] 2xl:text-[15px]">
          {formatVisitors(day.expected_visitors)}
        </p>
      </div>
      <div className="mt-px flex justify-center">
        <RiskDot risk={day.risk_level} />
      </div>
    </button>
  );
}
