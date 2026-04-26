import { Cloud, CloudRain, CloudSun, HelpCircle, Snowflake, Sun, Wind } from "lucide-react";
import { cn } from "@/lib/cn";

interface WeatherIconProps {
  icon?: string;
  className?: string;
  tone?: "navy" | "teal" | "orange" | "muted";
}

export function WeatherIcon({ icon, className, tone = "navy" }: WeatherIconProps) {
  const normalized = (icon ?? "").toLowerCase();
  const Icon =
    normalized.includes("rain") || normalized.includes("shower")
      ? CloudRain
      : normalized.includes("snow")
        ? Snowflake
        : normalized.includes("partly")
          ? CloudSun
          : normalized.includes("sun")
            ? Sun
            : normalized.includes("wind")
              ? Wind
              : normalized.includes("cloud")
                ? Cloud
                : HelpCircle;
  return (
    <Icon
      strokeWidth={1.45}
      className={cn(
        "h-8 w-8",
        tone === "teal" && "text-air-teal",
        tone === "orange" && "text-risk-orange",
        tone === "muted" && "text-ink-soft",
        tone === "navy" && "text-ink",
        className
      )}
      aria-hidden="true"
    />
  );
}
