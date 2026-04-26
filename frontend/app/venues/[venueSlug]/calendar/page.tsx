import { AppHeader } from "@/components/AppHeader";
import { CalendarWorkflow } from "@/components/CalendarWorkflow";
import { FallbackBanner } from "@/components/FallbackBanner";
import { VenueImage } from "@/components/VenueImage";
import { getAppContext, getCalendar, getVenueAssets, getVenues } from "@/lib/api";

interface CalendarPageProps {
  params: { venueSlug: string };
  searchParams: { month?: string };
}

export default async function CalendarPage({ params, searchParams }: CalendarPageProps) {
  const contextResult = await getAppContext();
  const month = searchParams.month && /^\d{4}-\d{2}$/.test(searchParams.month) ? searchParams.month : contextResult.data.default_month;
  const [venuesResult, calendarResult, assetsResult] = await Promise.all([
    getVenues(),
    getCalendar(params.venueSlug, month),
    getVenueAssets(params.venueSlug)
  ]);
  const isFallback = [venuesResult.source, calendarResult.source, contextResult.source].includes("demo_fallback");
  const calendar = calendarResult.data;
  const venue = calendar.venue_info;
  const currentDate = calendar.current_date ?? contextResult.data.current_date;

  return (
    <>
      <AppHeader active="forecasts" compact />
      <main className="product-screen product-screen-fit overflow-hidden">
        <FallbackBanner visible={isFallback} message={calendarResult.error ?? venuesResult.error} />

        <section className="grid grid-cols-1 items-center gap-3 lg:grid-cols-[1fr_360px]">
          <div className="min-w-0">
            <p className="font-body text-[11px] font-semibold uppercase tracking-[0.08em] text-brand-blue sm:text-xs">Kalendarz operacyjny</p>
            <h1 className="mt-1 truncate font-display text-[31px] font-extrabold leading-none tracking-[-0.055em] text-ink sm:text-[40px]">
              {venue.name}
            </h1>
          </div>
          <div className="hidden h-[92px] overflow-hidden rounded-[14px] border border-line bg-white shadow-soft lg:block">
            <VenueImage venueSlug={params.venueSlug} asset={assetsResult.data.assets[0] ?? venue.image_asset_status} className="h-full rounded-[14px]" />
          </div>
        </section>

        <CalendarWorkflow calendar={calendar} venues={venuesResult.data.venues} venueSlug={params.venueSlug} currentDate={currentDate} />
      </main>
    </>
  );
}
