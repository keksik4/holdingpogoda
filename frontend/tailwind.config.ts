import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#082a57",
        "ink-soft": "#58719a",
        "brand-blue": "#1264f5",
        "air-blue": "#1264f5",
        "air-teal": "#138fa0",
        "risk-orange": "#ec7844",
        "risk-amber": "#efb950",
        "risk-green": "#59ad78",
        paper: "#fbfdff",
        porcelain: "#ffffff",
        line: "#dbe8f5"
      },
      boxShadow: {
        air: "0 24px 74px -44px rgba(15, 62, 112, 0.32)",
        soft: "0 16px 52px -42px rgba(13, 43, 87, 0.36)"
      },
      fontFamily: {
        display: ["Georgia", "Times New Roman", "serif"],
        body: ["Aptos", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["Cascadia Mono", "SFMono-Regular", "Consolas", "monospace"]
      }
    }
  },
  plugins: []
};

export default config;
