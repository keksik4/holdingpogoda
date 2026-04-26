import { cn } from "@/lib/cn";

interface LodzLineArtProps {
  variant?: "city" | "aquapark" | "zoo" | "footer";
  className?: string;
}

const srcByVariant = {
  city: "/brand/lodz-hero-generated-v2.png",
  aquapark: "/illustrations/aquapark-line.svg",
  zoo: "/illustrations/orientarium-line.svg",
  footer: "/brand/lodz-footer-generated.png"
} satisfies Record<NonNullable<LodzLineArtProps["variant"]>, string>;

export function LodzLineArt({ variant = "city", className }: LodzLineArtProps) {
  return (
    <img
      src={srcByVariant[variant]}
      alt=""
      aria-hidden="true"
      className={cn("block h-auto w-full select-none", className)}
      draggable={false}
    />
  );
}
