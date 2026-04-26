import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pogoda w Łodzi - prognoza frekwencji",
  description: "Prognoza frekwencji dla miejskich atrakcji w Łodzi na podstawie pogody i sygnałów operacyjnych."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pl">
      <body>{children}</body>
    </html>
  );
}
