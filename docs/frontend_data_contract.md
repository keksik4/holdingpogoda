# Frontend Data Contract

These contracts support the current Next.js frontend and future frontend iterations.

All attendance values in these venue contracts are calibrated demo estimates unless explicitly replaced later by internal ticketing data. The frontend should display the provided data quality labels.

## Venue Selection Screen

Endpoint:

```text
GET /venues
```

Shape:

```json
{
  "venues": [
    {
      "name": "Aquapark Fala",
      "slug": "aquapark_fala",
      "type": "mixed indoor/outdoor aquapark",
      "city": "Lodz",
      "address": "al. Unii Lubelskiej 4, 94-208 Lodz",
      "short_description": "Large aquapark and recreation venue...",
      "weather_sensitivity_label": "Mixed weather sensitivity",
      "image_asset_status": {
        "usage_status": "missing_manual_asset",
        "local_path": "public/venues/aquapark-fala.jpg",
        "source_name": "Aquapark Fala official website",
        "license_notes": "Confirm permission/license before use in a public frontend."
      },
      "data_quality_label": "public benchmarks plus calibrated demo attendance",
      "hover_preview": {
        "today_expected_visitors": 4200,
        "tomorrow_expected_visitors": 5100,
        "day_after_tomorrow_expected_visitors": 6100,
        "weather_icon": "sun",
        "risk_label": "low",
        "data_quality_label": "Calibrated demo attendance",
        "value_quality": {
          "expected_visitors": "Calibrated demo attendance",
          "weather_icon": "Seasonal weather proxy unless refreshed with real weather consensus",
          "risk_label": "Calibrated demo attendance"
        },
        "is_calibrated_demo": true
      }
    }
  ],
  "data_quality_label": "Calibrated demo attendance"
}
```

## Single Venue

Endpoint:

```text
GET /venues/{venue_slug}
```

Returns the full venue profile from `data/sources/venue_profiles.json`.

Required venue slugs:

- `aquapark_fala`
- `orientarium_zoo_lodz`

## Monthly Calendar Forecast Screen

Endpoint:

```text
GET /venues/{venue_slug}/calendar?month=2025-05
```

Shape:

```json
{
  "venue_info": {},
  "month": "2025-05",
  "days": [
    {
      "date": "2025-05-01",
      "day_number": 1,
      "weather_icon": "sun",
      "expected_visitors": 6800,
      "visitors_low": 6120,
      "visitors_base": 6800,
      "visitors_high": 7480,
      "risk_level": "low",
      "best_day": true,
      "data_quality_label": "Calibrated demo attendance",
      "value_quality": {
        "expected_visitors": "Calibrated demo attendance",
        "low_base_high": "Calibrated demo attendance",
        "weather_icon": "Seasonal weather proxy unless refreshed with real weather consensus",
        "risk_level": "Calibrated demo attendance"
      },
      "is_calibrated_demo": true
    }
  ],
  "data_quality": {}
}
```

Calendar rule: `expected_visitors` equals `visitors_base`.

## Day Details Screen

Endpoint:

```text
GET /venues/{venue_slug}/days/{date}
```

Shape:

```json
{
  "venue_info": {},
  "selected_date": "2025-05-01",
  "expected_visitors": 6800,
  "low_base_high": {
    "low": 6120,
    "base": 6800,
    "high": 7480
  },
  "weather_risk": "low",
  "weather_details": {
    "weather_icon": "sun",
    "weather_impact_score": 12.0,
    "forecast_confidence": 0.82,
    "note": "Weather details are seasonal/calibrated unless a real weather refresh is joined later.",
    "data_quality_label": "Seasonal weather proxy unless refreshed with real weather consensus"
  },
  "hourly_visitor_curve": [
    {
      "datetime": "2025-05-01T10:00:00",
      "hour": 10,
      "expected_visitors": 420,
      "typical_visitors": 390,
      "confidence_score": 0.82,
      "peak_hour_flag": false,
      "data_quality_label": "Calibrated demo attendance",
      "is_calibrated_demo": true
    }
  ],
  "peak_hours": [],
  "operations_recommendations": [],
  "marketing_recommendations": [],
  "risk_and_readiness": {},
  "comparison_to_typical_day": {},
  "data_quality_labels": [
    "Official public benchmark",
    "Real weather API",
    "Calibrated demo attendance",
    "Source missing"
  ],
  "value_quality": {
    "expected_visitors": "Calibrated demo attendance",
    "low_base_high": "Calibrated demo attendance",
    "hourly_visitor_curve": "Calibrated demo attendance",
    "weather_details": "Seasonal weather proxy unless refreshed with real weather consensus",
    "recommendations": "Calibrated demo attendance",
    "comparison_to_typical_day": "Calibrated demo attendance"
  },
  "is_calibrated_demo": true
}
```

Reconciliation rule: the sum of `hourly_visitor_curve[].expected_visitors` equals `expected_visitors` for that venue and date.

## Supporting Endpoints

- `GET /venues/{venue_slug}/assets`
- `GET /venues/{venue_slug}/benchmarks`
- `GET /venues/{venue_slug}/trend-signals`
- `GET /venues/{venue_slug}/data-quality`
- `POST /data/refresh-public-sources`
- `POST /data/generate-calibrated-attendance`
- `GET /data/sources`

## Asset Rule

Real venue photos must come from manual approved assets listed in `asset_manifest.json`. The backend must not treat AI-generated imagery as real venue photos. Until approved photos are placed at the expected local paths, asset status is `missing_manual_asset`.

## Google Trends Rule

Google Trends is a relative demand signal only. It must not be displayed as a visitor number or treated as internal attendance.

## Current Time-Aware Contracts

The frontend should now call `GET /app/context` on load. The backend returns the Warsaw product date and the default current month.

```json
{
  "current_date": "2026-04-24",
  "current_datetime": "2026-04-24T10:30:00+02:00",
  "timezone": "Europe/Warsaw",
  "default_month": "2026-04",
  "default_selected_date": "2026-04-24",
  "available_history_start": "2022-01-01",
  "available_forecast_end": "2026-10-21",
  "data_freshness": {},
  "weather_refresh_status": {}
}
```

`GET /venues/{venue_slug}/calendar` now accepts an optional `month`. If omitted, the backend uses `/app/context.default_month`.

Calendar responses include:

- `current_date`
- `selected_date`
- `month`
- `venue_info`
- `venue`
- `days`
- `data_freshness`
- `weather_consensus_summary`
- `calibration_summary`
- `data_quality`

Each calendar day may include:

- `date_relation`: `historical`, `today` or `forecast`
- `weather_risk`
- `confidence_score`
- `explanation`

`GET /venues/{venue_slug}/days/{date}` now includes weather consensus and forecast explanation fields:

- `date_relation`
- `weather_consensus`
- `providers_used`
- `forecast_explanation`
- `calibration_confidence`

Weather consensus can be fetched directly:

```text
GET /venues/{venue_slug}/weather/consensus?date=YYYY-MM-DD
GET /venues/{venue_slug}/weather/consensus-range?start=YYYY-MM-DD&end=YYYY-MM-DD
```

Validation can be fetched through:

```text
GET /venues/{venue_slug}/forecast/validation?month=YYYY-MM
```

Refresh/recalculation endpoints:

```text
POST /data/refresh-weather?venue_slug=aquapark_fala&date=YYYY-MM-DD&force=true
POST /data/recalculate-forecasts?venue_slug=aquapark_fala&month=YYYY-MM
```
