"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, CalendarDays, Database } from "lucide-react";
import { CalendarMonth } from "@/components/CalendarMonth";
import { LoadingOverlay } from "@/components/LoadingOverlay";
import { RiskDot } from "@/components/RiskDot";
import { VenueSwitcher } from "@/components/VenueSwitcher";
import { WeatherIcon } from "@/components/WeatherIcon";
import { addMonths, formatDateLabel, formatVisitors, providerLabel, relationLabel, riskLabel, riskTone, translateBackendText } from "@/lib/formatting";
import { getCachedCalendar, loadCalendar, primeCalendar } from "@/lib/clientApi";
import type { CalendarDay, CalendarResponse, VenueSummary } from "@/lib/types";

interface CalendarWorkflowProps {
  calendar: CalendarResponse;
  venues: VenueSummary[];
  venueSlug: string;
  currentDate: string;
}

export function CalendarWorkflow({ calendar: initialCalendar, venues, venueSlug, currentDate }: CalendarWorkflowProps) {
  const router = useRouter();
  const [calendar, setCalendar] = useState<CalendarResponse>(initialCalendar);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | undefined>(() => pickInitialDate(initialCalendar.days, currentDate));
  const requestId = useRef(0);

  useEffect(() => {
    primeCalendar(venueSlug, initialCalendar.month, initialCalendar);
    setCalendar(initialCalendar);
    setSelectedDate(pickInitialDate(initialCalendar.days, currentDate));
  }, [initialCalendar, venueSlug, currentDate]);

  useEffect(() => {
    const adjacent = [addMonths(calendar.month, 1), addMonths(calendar.month, -1)];
    adjacent.forEach((month) => {
      if (getCachedCalendar(venueSlug, month)) return;
      void loadCalendar(venueSlug, month).catch(() => {});
    });
  }, [calendar.month, venueSlug]);

  const selectedDay = useMemo(
    () => calendar.days.find((day) => day.date === selectedDate) ?? pickSelectedDay(calendar.days, currentDate),
    [calendar.days, currentDate, selectedDate]
  );

  const changeMonth = async (target: string) => {
    if (target === calendar.month) return;
    const requestNumber = ++requestId.current;
    const cached = getCachedCalendar(venueSlug, target);
    const url = `/venues/${venueSlug}/calendar?month=${target}`;

    if (cached) {
      setCalendar(cached);
      setSelectedDate(pickInitialDate(cached.days, currentDate));
      router.replace(url, { scroll: false });
      return;
    }

    setLoading(true);
    try {
      const data = await loadCalendar(venueSlug, target);
      if (requestNumber !== requestId.current) return;
      setCalendar(data);
      setSelectedDate(pickInitialDate(data.days, currentDate));
      router.replace(url, { scroll: false });
    } catch {
      router.push(url);
    } finally {
      if (requestNumber === requestId.current) setLoading(false);
    }
  };

  return (
    <section className="mt-2">
      <LoadingOverlay visible={loading} />
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <VenueSwitcher venues={venues} selectedSlug={venueSlug} />
        <div className="flex shrink-0 items-center gap-2">
          <div className="metric-card flex items-center gap-2 px-2.5 py-1.5 font-body text-[11px] text-ink-soft sm:px-3 sm:py-2 sm:text-xs">
            <CalendarDays className="h-4 w-4 text-brand-blue" strokeWidth={1.45} />
            <span>Dziś: {formatDateLabel(currentDate, "short")}</span>
          </div>
          <div className="metric-card hidden items-center gap-3 px-3 py-2 font-body text-xs md:flex">
            <RiskDot risk="low" withLabel />
            <RiskDot risk="medium" withLabel />
            <RiskDot risk="high" withLabel />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 items-start gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(280px,300px)] 2xl:grid-cols-[minmax(0,1fr)_minmax(300px,320px)]">
        <div className="min-w-0">
          <div className="soft-panel w-[calc(100vw-0.9rem)] max-w-full px-1 py-2 sm:w-auto sm:px-3 sm:py-3">
            <CalendarMonth
              month={calendar.month}
              days={calendar.days}
              venueSlug={venueSlug}
              currentDate={currentDate}
              selectedDate={selectedDay?.date}
              onSelectDay={setSelectedDate}
              onChangeMonth={changeMonth}
            />
          </div>
        </div>

        <aside className="space-y-2.5 xl:space-y-3">
          <SelectedDayPanel day={selectedDay} venueSlug={venueSlug} currentDate={currentDate} />
          <BestDays days={calendar.days} onSelectDay={setSelectedDate} />
          <SourcesPanel summary={calendar.weather_consensus_summary} calibration={calendar.calibration_summary} />
        </aside>
      </div>
    </section>
  );
}

function pickInitialDate(days: CalendarDay[], currentDate: string): string | undefined {
  return days.find((day) => day.date === currentDate)?.date ?? days[0]?.date;
}

function pickSelectedDay(days: CalendarDay[], currentDate: string): CalendarDay | undefined {
  return days.find((day) => day.date === currentDate) ?? days.find((day) => day.date_relation === "today") ?? days[0];
}

function SelectedDayPanel({ day, venueSlug, currentDate }: { day?: CalendarDay; venueSlug: string; currentDate: string }) {
  if (!day) {
    return (
      <div className="soft-panel p-4">
        <p className="font-body text-xs text-ink-soft">Brak dni dla wybranego miesiąca.</p>
      </div>
    );
  }

  const isToday = day.date === currentDate || day.date_relation === "today";
  const confidence = typeof day.confidence_score === "number" ? Math.round(day.confidence_score * 100) : null;

  return (
    <div className="soft-panel p-3 sm:p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-body text-sm font-semibold text-ink">Wybrany dzień</p>
          <p className="mt-1 font-body text-xs text-ink-soft">{formatDateLabel(day.date)}</p>
        </div>
        {isToday ? <span className="rounded-[8px] bg-brand-blue px-2.5 py-1 font-body text-[11px] font-semibold text-white">Dziś</span> : null}
      </div>
      <div className="mt-3 flex items-end gap-3">
        <WeatherIcon icon={day.weather_icon} tone={day.risk_level === "high" ? "orange" : "teal"} className="h-8 w-8" />
        <div>
          <p className="font-body text-[30px] font-semibold leading-none tracking-[-0.05em] text-brand-blue sm:text-[34px]">{formatVisitors(day.expected_visitors)}</p>
          <p className="mt-1 font-body text-[11px] text-ink-soft">prognozowana frekwencja</p>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 border-y border-line py-3">
        <PanelMetric label="Zakres" value={`${formatVisitors(day.visitors_low)}-${formatVisitors(day.visitors_high)}`} />
        <PanelMetric label="Ryzyko" value={riskLabel(day.risk_level)} valueClass={riskTone(day.risk_level)} />
        <PanelMetric label="Pewność" value={confidence == null ? "Niska pewność" : `${confidence}%`} />
        <PanelMetric label="Relacja" value={relationLabel(day.date_relation)} />
      </div>
      <p className="mt-2 hidden font-body text-[11px] leading-4 text-ink-soft 2xl:line-clamp-2 2xl:block">{translateBackendText(day.explanation)}</p>
      <Link
        href={`/venues/${venueSlug}/days/${day.date}`}
        className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-[10px] bg-brand-blue px-3 py-2.5 font-body text-xs font-semibold text-white transition-air hover:-translate-y-0.5 hover:shadow-soft"
      >
        Szczegóły dnia
        <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.6} />
      </Link>
    </div>
  );
}

function PanelMetric({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div>
      <p className="font-body text-[10px] text-ink-soft">{label}</p>
      <p className={`mt-0.5 truncate font-body text-xs font-semibold ${valueClass ?? "text-ink"}`}>{value}</p>
    </div>
  );
}

function BestDays({ days, onSelectDay }: { days: CalendarDay[]; onSelectDay: (date: string) => void }) {
  const bestDays = [...days].filter((day) => day.best_day).sort((a, b) => b.expected_visitors - a.expected_visitors).slice(0, 3);

  return (
    <div className="soft-panel p-3">
      <p className="font-body text-sm font-semibold text-ink">Najlepsze dni</p>
      <div className="mt-2 space-y-1">
        {bestDays.map((day) => (
          <button
            key={day.date}
            type="button"
            onClick={() => onSelectDay(day.date)}
            className="flex w-full items-center justify-between rounded-[9px] px-2 py-1 text-left transition-air hover:bg-[#f7fbff]"
          >
            <span className="flex min-w-0 items-center gap-2">
              <WeatherIcon icon={day.weather_icon} className="h-4 w-4" tone="teal" />
              <span className="truncate font-body text-[11px] text-ink">{formatDateLabel(day.date, "short")}</span>
            </span>
            <span className="font-body text-xs font-semibold text-ink">{formatVisitors(day.expected_visitors)}</span>
          </button>
        ))}
        {!bestDays.length ? <p className="font-body text-[11px] leading-4 text-ink-soft">Brak oznaczonych dni.</p> : null}
      </div>
    </div>
  );
}

function SourcesPanel({ summary, calibration }: { summary: unknown; calibration: unknown }) {
  const weatherObj = summary as { providers_used_this_month?: string[]; incomplete_days?: string[] } | undefined;
  const calibrationObj = calibration as { status?: string } | undefined;
  const providers = weatherObj?.providers_used_this_month ?? [];
  const incomplete = weatherObj?.incomplete_days?.length ?? 0;
  const calibrationLabel = calibrationObj?.status ? translateBackendText(calibrationObj.status) : "kalibracja frekwencji";

  return (
    <div className="soft-panel p-3">
      <div className="flex items-center gap-2">
        <Database className="h-4 w-4 text-brand-blue" strokeWidth={1.45} />
        <p className="font-body text-xs font-semibold text-ink">Źródła pogody</p>
      </div>
      {providers.length ? (
        <ul className="mt-2 divide-y divide-line rounded-[10px] border border-line">
          {providers.map((provider) => (
            <li key={provider} className="flex items-center justify-between gap-2 px-2 py-1.5 font-body text-[11px]">
              <span className="truncate text-ink">{providerLabel(provider)}</span>
              <span className="rounded-[6px] bg-[#eef4ff] px-1.5 py-0.5 font-semibold uppercase tracking-wide text-brand-blue">live</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 font-body text-[11px] leading-4 text-ink-soft">Brak danych pogodowych w tym miesiącu.</p>
      )}
      <p className="mt-2 font-body text-[11px] leading-4 text-ink-soft">
        {providers.length > 1 ? `Konsensus uśrednia ${providers.length} źródła.` : "Pojedyncze źródło pogody."} {incomplete > 0 ? `Dane częściowe dla ${incomplete} dni. ` : ""}
        Frekwencja: {calibrationLabel}.
      </p>
    </div>
  );
}
