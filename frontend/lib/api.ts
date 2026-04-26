import {
  fallbackAppContext,
  fallbackAssets,
  fallbackCalendar,
  fallbackDayDetails,
  fallbackVenue,
  fallbackVenues
} from "@/lib/fallback";
import type {
  ApiResult,
  AppContext,
  AssetsResponse,
  CalendarResponse,
  DayDetailsResponse,
  VenueProfile,
  VenuesResponse
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function apiBaseUrl(): string {
  return API_BASE;
}

export async function getAppContext(): Promise<ApiResult<AppContext>> {
  return getJson("/app/context", fallbackAppContext);
}

export async function getVenues(): Promise<ApiResult<VenuesResponse>> {
  return getJson("/venues", fallbackVenues);
}

export async function getVenue(slug: string): Promise<ApiResult<VenueProfile>> {
  return getJson(`/venues/${slug}`, () => fallbackVenue(slug));
}

export async function getVenueAssets(slug: string): Promise<ApiResult<AssetsResponse>> {
  return getJson(`/venues/${slug}/assets`, () => fallbackAssets(slug));
}

export async function getCalendar(slug: string, month?: string): Promise<ApiResult<CalendarResponse>> {
  const query = month ? `?month=${encodeURIComponent(month)}` : "";
  return getJson(`/venues/${slug}/calendar${query}`, () => fallbackCalendar(slug, month));
}

export async function getDayDetails(slug: string, date: string): Promise<ApiResult<DayDetailsResponse>> {
  return getJson(`/venues/${slug}/days/${date}`, () => fallbackDayDetails(slug, date));
}

async function getJson<T>(path: string, fallback: () => T): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: 900 },
      headers: { Accept: "application/json" }
    });
    if (!response.ok) throw new Error(`Backend zwrócił status ${response.status}`);
    return { data: (await response.json()) as T, source: "backend" };
  } catch (error) {
    return {
      data: fallback(),
      source: "demo_fallback",
      error: error instanceof Error ? error.message : "Nie udało się połączyć z backendem"
    };
  }
}
