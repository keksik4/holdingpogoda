# Holding Łódź Forecasting Knowledge Base

Backend now loads the operational report package from:

```text
backend/data/holding_lodz
```

The package contains CSV/JSON priors for:

- public baseline attendance anchors
- month and weekday multipliers
- hourly occupancy profiles
- weather impact rules
- bottleneck windows
- calendar and event overlays
- source references and confidence notes

The loader is implemented in:

```text
backend/services/holding_lodz_knowledge.py
```

If a file is missing, the backend logs a warning and falls back to the previous deterministic calibrated logic instead of breaking the frontend.

## Daily Forecast Formula

The daily estimate uses:

```text
estimated_visitors =
base_daily_visitors
* weekday_multiplier
* seasonal_multiplier
* weather_multiplier
* holiday_multiplier
* event_multiplier
* trend_multiplier
* venue_specific_adjustment
```

Aquapark Fala uses stronger summer and hot-weather demand logic. Rain or cold reduces outdoor-zone demand, but indoor pools and sauna behavior preserve part of demand.

Orientarium uses stronger school-trip, weekend, summer and August logic. Rain does not automatically reduce demand because indoor pavilions can become relatively more attractive, while storms still reduce confidence and comfort.

## Hourly Forecast

The daily total is distributed using venue-specific hourly profiles from `hourly_profiles.csv`.

Each hourly point can include:

- `estimated_visitors`
- `occupancy_percent`
- `load_level`
- `weather_impact`
- `operational_note`
- `profile_id`
- `data_source`

Hourly totals are reconciled back to the daily total before returning the response.

## Weather Providers

The backend supports:

- OpenWeather forecast, when `OPENWEATHER_API_KEY` is configured
- Open-Meteo forecast and historical APIs
- MET Norway where applicable
- IMGW where available
- deterministic seasonal fallback only when real providers are unavailable or intentionally skipped

OpenWeather and Open-Meteo are normalized into a frontend-ready source shape under `weather_consensus.sources`.

## Validation

Run:

```bat
cd C:\AI\welcome-to-airlines
.venv\Scripts\python.exe -m backend.scripts.validate_holding_forecasts
```

The script prints sample scenarios for:

- hot summer weekend at Aquapark Fala
- cold weekday pattern at Aquapark Fala
- rainy weekday at Orientarium
- sunny spring school-trip day at Orientarium
