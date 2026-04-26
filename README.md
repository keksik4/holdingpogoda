# Pogoda w Łodzi

Operational attendance forecasting system for municipal attractions in Łódź, Poland.

The project forecasts daily and hourly visitor demand for:

- Aquapark Fala
- Orientarium Zoo Łódź

The backend is the source of truth for venue metadata, calendar forecasts, day details, weather interpretation, attendance calibration, recommendations and data-quality labels. The frontend is a Next.js interface that consumes the backend API.

Production demo:

- Frontend: https://pogoda-w-lodzi.vercel.app
- Backend API: https://pogoda-w-lodzi-api.vercel.app

## What This Project Contains

- FastAPI backend with deterministic venue/date forecasts.
- Next.js frontend with:
  - home page / venue selection,
  - monthly calendar forecast,
  - day details dashboard.
- Europe/Warsaw current-date logic.
- Multi-source weather handling with explicit confidence and partial-data states.
- Attendance calibration based on public benchmarks and object-specific operational profiles.
- Holding Łódź raw profile package integration for hourly load, seasonality, weekday patterns, weather rules, bottlenecks and venue behavior.
- Polish UI copy and data-quality labels.

## Local Backend Setup

Requirements:

- Python 3.11 or newer
- Windows PowerShell or Command Prompt

From the project root:

```bat
run_backend_windows.bat
```

The backend will run at:

```text
http://127.0.0.1:8000
```

Useful local URLs:

- Health: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs

## Local Frontend Setup

Requirements:

- Node.js 18 or newer
- Backend running locally, or a configured production API URL

From the project root:

```bat
run_frontend_windows.bat
```

The frontend will run at:

```text
http://localhost:3000
```

The frontend reads the API base URL from:

```text
frontend/.env.local
```

Default local value:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Environment Variables

Root `.env.example` contains backend settings:

```text
APP_NAME=Pogoda w Łodzi
APP_ENV=local
DEMO_MODE=true
DATABASE_URL=sqlite:///./data/airlines.db
DEFAULT_TIMEZONE=Europe/Warsaw
MET_NO_USER_AGENT=pogoda-w-lodzi-local/0.1 contact@example.com
OPENWEATHER_API_KEY=
OPENMETEO_BASE_URL=https://api.open-meteo.com/v1/forecast
METEOSOURCE_API_KEY=
METEOSOURCE_BASE_URL=https://www.meteosource.com/api/v1/free/point
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Frontend `.env.example`:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Do not commit real API keys. Use local `.env` / `.env.local` files or Vercel environment variables.

## Main API Contract

Core routes used by the frontend:

- `GET /app/context`
- `GET /venues`
- `GET /venues/{venue_slug}`
- `GET /venues/{venue_slug}/calendar`
- `GET /venues/{venue_slug}/days/{date}`
- `GET /venues/{venue_slug}/assets`
- `GET /venues/{venue_slug}/benchmarks`
- `GET /venues/{venue_slug}/data-quality`

Supported venue slugs:

- `aquapark_fala`
- `orientarium_zoo_lodz`

## Forecasting Notes

The system uses calibrated estimates, not private gate-entry data.

Calibration anchors:

- Aquapark Fala: roughly 1.5M annual visitors.
- Orientarium Zoo Łódź: roughly 1M annual visitors.

Forecast factors include:

- venue profile,
- weekday/weekend pattern,
- seasonality,
- holidays and school-break placeholders,
- weather interpretation,
- provider disagreement,
- confidence,
- hourly load profile,
- bottleneck windows,
- operational recommendations.

## Weather Notes

The backend normalizes weather inputs into a common structure and returns frontend-ready weather summaries. If two real providers are available for a day, the backend can expose a weather consensus. If only one provider is available, it marks the day as partial data instead of faking a second source.

For wider 30-day two-provider coverage, configure a long-range provider key such as:

```text
METEOSOURCE_API_KEY=
```

## Venue Images

Real or manually approved venue images live in:

```text
frontend/public/venues/aquapark-fala.jpg
frontend/public/venues/orientarium.jpg
```

Generated line-art and decorative assets live under:

```text
frontend/public/brand
frontend/public/illustrations
```

The generated illustration assets are not treated as real venue photos.

## Vercel Deployment

Current deployment strategy uses two Vercel projects:

- `pogoda-w-lodzi` for the Next.js frontend.
- `pogoda-w-lodzi-api` for the FastAPI backend.

Frontend production variable:

```text
NEXT_PUBLIC_API_BASE_URL=https://pogoda-w-lodzi-api.vercel.app
```

Backend production notes:

- Vercel backend package is in `backend_vercel`.
- SQLite in `/tmp` is not durable production storage.
- Weather cache is best-effort in serverless runtime.
- A production version should use durable database/storage and scheduled refresh jobs.

## Development Checks

Frontend:

```bat
cd frontend
npm install
npm run typecheck
npm run build
```

Backend smoke check:

```bat
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/health
```

## Data Status

This proof of concept clearly separates:

- real weather API data,
- public benchmarks,
- calibrated demo attendance,
- fallback/demo mode,
- manually managed assets.

Real internal attendance data can replace calibrated demo attendance later through the backend import/data pipeline.
