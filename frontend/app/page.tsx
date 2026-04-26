import {
  BarChart3,
  Building2,
  CalendarDays,
  CloudSun,
  Database,
  Megaphone,
  ShieldCheck,
  ThermometerSun,
  UserRound,
  UsersRound
} from "lucide-react";
import { AppHeader } from "@/components/AppHeader";
import { FallbackBanner } from "@/components/FallbackBanner";
import { LodzLineArt } from "@/components/LodzLineArt";
import { VenueCards } from "@/components/VenueCards";
import { getVenueAssets, getVenues } from "@/lib/api";
import type { VenueAsset } from "@/lib/types";

const workflow = [
  { icon: CloudSun, title: "Pogoda", text: "Temperatura, opady, zachmurzenie, wiatr i pewność dostawców.", flow: true },
  { icon: CalendarDays, title: "Kalendarz", text: "Święta, weekendy, sezonowość, wydarzenia i ferie.", flow: true },
  { icon: Building2, title: "Profil obiektu", text: "Inna reakcja aquaparku, inna reakcja zoo i Orientarium.", flow: true },
  { icon: Database, title: "Dane historyczne", text: "Publiczne benchmarki oraz skalibrowana historia demonstracyjna.", flow: false },
  { icon: BarChart3, title: "Prognoza", text: "Frekwencja, zakres niepewności, ryzyko i godziny szczytu.", flow: false },
  { icon: ShieldCheck, title: "Rekomendacje", text: "Sugestie dla operacji, marketingu i zarządzania obiektem.", flow: true }
];

const audiences = [
  { icon: Building2, title: "Zarządca obiektu", text: "Planowanie dnia, budżetu i gotowości operacyjnej." },
  { icon: Megaphone, title: "Marketing", text: "Kampanie uruchamiane wtedy, gdy popyt ma sens." },
  { icon: UsersRound, title: "Operacje", text: "Obsada, kolejki, gastronomia, parking i czystość." },
  { icon: ThermometerSun, title: "Miasto", text: "Lepsza widoczność ruchu w miejskich atrakcjach." }
];

const reasons = [
  { title: "Szybsza reakcja na pogodę", text: "Mniej ręcznego sprawdzania prognoz i więcej decyzji w jednym miejscu." },
  { title: "Lepsze decyzje operacyjne", text: "Obsada, kolejki i strefy obiektu mogą być planowane z wyprzedzeniem." },
  { title: "Mniej zmarnowanego budżetu", text: "Marketing może reagować na realne warunki i popyt." },
  { title: "Gotowość do rozbudowy", text: "Backend jest źródłem danych dla kolejnych ekranów i integracji." }
];

export default async function HomePage() {
  const venuesResult = await getVenues();
  const assetResults = await Promise.all(
    venuesResult.data.venues.map(async (venue) => [venue.slug, await getVenueAssets(venue.slug)] as const)
  );
  const assetsByVenue = Object.fromEntries(assetResults.map(([slug, result]) => [slug, result.data.assets[0] ?? null])) as Record<
    string,
    VenueAsset | null
  >;
  const isFallback = venuesResult.source === "demo_fallback";

  return (
    <>
      <AppHeader active="overview" />
      <main className="page-shell pb-8">
        <FallbackBanner visible={isFallback} message={venuesResult.error} />

        <section className="relative overflow-hidden pt-0 sm:pt-1">
          <div className="pointer-events-none absolute right-[-70px] top-[-64px] hidden w-[455px] opacity-85 lg:block xl:right-[-40px]">
            <LodzLineArt variant="city" />
          </div>
          <div className="relative max-w-2xl">
            <div className="mb-2 flex h-12 w-12 items-center justify-center overflow-hidden rounded-[14px] bg-white/80 shadow-soft ring-1 ring-line sm:mb-3 sm:h-14 sm:w-14">
              <img src="/brand/pogoda-boat-storm.png" alt="" aria-hidden="true" className="h-[70px] w-[70px] object-contain mix-blend-multiply sm:h-[78px] sm:w-[78px]" />
            </div>
            <h1 className="font-display text-[31px] font-extrabold leading-[1.02] tracking-[-0.055em] text-ink sm:text-[40px] md:text-[52px]">
              Prognoza frekwencji dla miejskich atrakcji
            </h1>
            <div className="mt-3 h-[3px] w-12 rounded-full bg-brand-blue sm:mt-4 sm:w-14" />
          </div>
        </section>

        <section id="venues" className="mt-4 sm:mt-5">
          <div className="mb-3 flex items-end justify-between gap-4">
            <div>
              <p className="font-body text-[11px] font-semibold uppercase tracking-[0.08em] text-brand-blue sm:text-xs">Wybierz obiekt</p>
              <h2 className="mt-1 font-display text-[21px] font-extrabold leading-none tracking-[-0.05em] text-ink sm:text-[26px]">
                Dwa główne moduły miejskie
              </h2>
            </div>
          </div>
          <VenueCards venues={venuesResult.data.venues} assetsByVenue={assetsByVenue} source={venuesResult.source} />
        </section>

        <section id="how-it-works" className="mt-12 border-t border-line pt-9 sm:mt-14 sm:pt-10">
          <h2 className="text-center font-display text-[24px] font-extrabold tracking-[-0.05em] text-ink sm:text-[26px]">Jak działa system</h2>
          <div className="workflow-flow mt-7 grid grid-cols-2 gap-x-3 gap-y-6 md:grid-cols-3 xl:grid-cols-6">
            {workflow.map((item, index) => (
              <FlowStep key={item.title} icon={item.icon} title={item.title} text={item.text} showFlow={index < workflow.length - 1} />
            ))}
          </div>

          <div className="mt-16 grid gap-12 lg:grid-cols-[0.9fr_1.45fr]">
            <section>
              <h2 className="font-display text-[27px] font-extrabold tracking-[-0.05em] text-ink sm:text-[28px]">Dla kogo to jest</h2>
              <div className="mt-6 grid gap-x-8 gap-y-6 sm:grid-cols-2">
                {audiences.map((item) => (
                  <InfoItem key={item.title} icon={item.icon} title={item.title} text={item.text} />
                ))}
              </div>
            </section>

            <section>
              <h2 className="font-display text-[27px] font-extrabold tracking-[-0.05em] text-ink sm:text-[28px]">Dlaczego to ma sens dla Łodzi</h2>
              <div className="mt-6 grid gap-x-10 gap-y-6 border-line lg:grid-cols-2 lg:border-l lg:pl-8">
                {reasons.map((item) => (
                  <div key={item.title}>
                    <h3 className="font-body text-sm font-extrabold text-ink">{item.title}</h3>
                    <p className="mt-2 font-body text-sm leading-6 text-ink-soft">{item.text}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </section>

        <LodzLineArt variant="footer" className="mx-auto -mt-1 max-w-7xl opacity-75 mix-blend-multiply sm:mt-2" />
      </main>
    </>
  );
}

function FlowStep({ icon: Icon, title, text, showFlow }: { icon: typeof CloudSun; title: string; text: string; showFlow: boolean }) {
  return (
    <div className="workflow-step relative text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-[14px] text-brand-blue">
        <Icon className="h-9 w-9" strokeWidth={1.25} />
      </div>
      {showFlow ? <span className="workflow-connector" aria-hidden="true" /> : null}
      <h3 className="mt-3 font-body text-sm font-extrabold text-ink">{title}</h3>
      <p className="mx-auto mt-1.5 max-w-[10rem] font-body text-xs leading-5 text-ink-soft">{text}</p>
    </div>
  );
}

function InfoItem({ icon: Icon, title, text }: { icon: typeof UserRound; title: string; text: string }) {
  return (
    <div className="grid grid-cols-[42px_1fr] gap-4">
      <Icon className="mt-1 h-8 w-8 text-brand-blue" strokeWidth={1.35} />
      <div>
        <h3 className="font-body text-sm font-extrabold text-ink">{title}</h3>
        <p className="mt-2 font-body text-sm leading-6 text-ink-soft">{text}</p>
      </div>
    </div>
  );
}
