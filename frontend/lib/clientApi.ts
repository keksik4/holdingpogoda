import { cachedFetchJson, getCached, primeCache } from "@/lib/clientCache";
import type { CalendarResponse, DayDetailsResponse } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function calendarKey(slug: string, month: string): string {
  return `calendar:${slug}:${month}`;
}

function dayKey(slug: string, date: string): string {
  return `day:${slug}:${date}`;
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
    cache: "force-cache"
  });
  if (!response.ok) throw new Error(`Backend zwrócił status ${response.status}`);
  return (await response.json()) as T;
}

export function getCachedCalendar(slug: string, month: string): CalendarResponse | null {
  return getCached<CalendarResponse>(calendarKey(slug, month));
}

export function primeCalendar(slug: string, month: string, data: CalendarResponse): void {
  primeCache(calendarKey(slug, month), data);
}

export async function loadCalendar(slug: string, month: string): Promise<CalendarResponse> {
  return cachedFetchJson(calendarKey(slug, month), () =>
    fetchJson<CalendarResponse>(`/venues/${slug}/calendar?month=${encodeURIComponent(month)}`)
  );
}

export async function loadDayDetails(slug: string, date: string): Promise<DayDetailsResponse> {
  return cachedFetchJson(dayKey(slug, date), () =>
    fetchJson<DayDetailsResponse>(`/venues/${slug}/days/${date}`)
  );
}
