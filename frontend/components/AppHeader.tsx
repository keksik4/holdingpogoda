import Link from "next/link";
import { cn } from "@/lib/cn";

interface AppHeaderProps {
  active?: "overview" | "forecasts" | "venues" | "how";
  compact?: boolean;
}

const navItems = [
  { href: "/", label: "Start", key: "overview" },
  { href: "/venues/aquapark_fala/calendar", label: "Prognozy", key: "forecasts" },
  { href: "/#venues", label: "Obiekty", key: "venues" },
  { href: "/#how-it-works", label: "Jak działa", key: "how" }
] as const;

export function AppHeader({ active = "overview", compact = false }: AppHeaderProps) {
  return (
    <header className={cn("mx-auto flex w-full max-w-[1440px] items-center justify-between gap-4 px-3 sm:gap-8 sm:px-6", compact ? "py-2 sm:py-3" : "py-3 sm:py-4")}>
      <Link href="/" className="group flex items-center gap-2.5 font-body text-[14px] font-extrabold tracking-[-0.03em] text-ink sm:gap-3 sm:text-[15px]">
        <span className={cn("flex items-center justify-center overflow-hidden rounded-[12px] bg-white", compact ? "h-9 w-9" : "h-10 w-10")}>
          <img
            src="/brand/pogoda-boat-storm.png"
            alt=""
            aria-hidden="true"
            className={cn("object-contain mix-blend-multiply transition-air group-hover:scale-105", compact ? "h-[50px] w-[50px]" : "h-[56px] w-[56px]")}
          />
        </span>
        <span>Pogoda w Łodzi</span>
      </Link>
      <nav className="hidden items-center gap-7 border-b border-line/70 pb-2.5 font-body text-[13px] text-ink-soft md:flex">
        {navItems.map((item) => (
          <Link key={item.key} href={item.href} className={cn("relative px-1 transition-air hover:text-ink", active === item.key && "font-semibold text-ink")}>
            {item.label}
            {active === item.key ? <span className="absolute -bottom-[11px] left-0 h-[2px] w-full rounded-full bg-air-blue" /> : null}
          </Link>
        ))}
      </nav>
    </header>
  );
}
