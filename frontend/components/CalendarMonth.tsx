"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { CalendarDayCell } from "@/components/CalendarDayCell";
import { addMonths, formatMonthTitle } from "@/lib/formatting";
import type { CalendarDay } from "@/lib/types";

interface CalendarMonthProps {
  month: string;
  days: CalendarDay[];
  venueSlug: string;
  currentDate?: string;
  selectedDate?: string;
  onSelectDay?: (date: string) => void;
}

const weekdays = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nd"];

export function CalendarMonth({ month, days, venueSlug, currentDate, selectedDate, onSelectDay }: CalendarMonthProps) {
  const cells = buildCalendarCells(month, days);
  return (
    <section className="mobile-calendar-scale">
      <div className="mb-2 grid grid-cols-[34px_1fr_34px] items-center sm:grid-cols-[38px_1fr_38px]">
        <Link
          href={`/venues/${venueSlug}/calendar?month=${addMonths(month, -1)}`}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-line bg-white text-ink transition-air hover:-translate-y-0.5 hover:border-air-blue"
          aria-label="Poprzedni miesiąc"
        >
          <ChevronLeft className="h-4 w-4" strokeWidth={1.5} />
        </Link>
        <h2 className="text-center font-display text-[20px] font-extrabold leading-none tracking-[-0.04em] text-ink sm:text-[24px]">{formatMonthTitle(month)}</h2>
        <Link
          href={`/venues/${venueSlug}/calendar?month=${addMonths(month, 1)}`}
          className="flex h-8 w-8 items-center justify-center justify-self-end rounded-full border border-line bg-white text-ink transition-air hover:-translate-y-0.5 hover:border-air-blue"
          aria-label="Następny miesiąc"
        >
          <ChevronRight className="h-4 w-4" strokeWidth={1.5} />
        </Link>
      </div>
      <div className="overflow-x-hidden pb-0 sm:overflow-x-auto sm:pb-1">
        <div className="min-w-0 sm:min-w-[760px]">
          <div className="mb-1 grid grid-cols-7 gap-px px-px sm:gap-1 sm:px-1">
            {weekdays.map((weekday) => (
              <div key={weekday} className="py-0.5 text-center font-body text-[10px] font-semibold text-ink-soft sm:text-[11px]">
                {weekday}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-px sm:gap-1">
            {cells.map((cell, index) => (
              <CalendarDayCell
                key={cell.day?.date ?? `${cell.dayNumber}-${index}`}
                day={cell.day}
                dayNumber={cell.dayNumber}
                venueSlug={venueSlug}
                currentDate={currentDate}
                selected={Boolean(cell.day && cell.day.date === selectedDate)}
                onSelect={onSelectDay}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function buildCalendarCells(month: string, days: CalendarDay[]) {
  const [year, monthNumber] = month.split("-").map(Number);
  const first = new Date(year, monthNumber - 1, 1);
  const startOffset = (first.getDay() + 6) % 7;
  const daysInMonth = new Date(year, monthNumber, 0).getDate();
  const previousMonthDays = new Date(year, monthNumber - 1, 0).getDate();
  const dayMap = new Map(days.map((day) => [day.day_number, day]));
  const cells: Array<{ day?: CalendarDay; dayNumber?: number }> = [];

  for (let index = startOffset - 1; index >= 0; index -= 1) cells.push({ dayNumber: previousMonthDays - index });
  for (let dayNumber = 1; dayNumber <= daysInMonth; dayNumber += 1) cells.push({ day: dayMap.get(dayNumber), dayNumber });
  while (cells.length % 7 !== 0) cells.push({ dayNumber: cells.length - startOffset - daysInMonth + 1 });
  return cells;
}
