# Data Calibration

## Principle

Public benchmarks are not internal daily attendance. The backend never claims generated daily or hourly values are real ticketing data.

## Calibration Anchors

The generator uses public or provided benchmark anchors:

- Aquapark Fala: approximately 1.5M visitors in 2024.
- Aquapark Fala: more than 0.5M visitors during summer 2025. The current calibration target is 540k for June-August, marked as a product benchmark assumption needing manual confirmation.
- Orientarium Zoo Łódź: close to 1M visitors in 2024.
- Orientarium Zoo Łódź: August 2025 record demand calibrated around the public report of a month above 190k visitors.

## Daily Generation

Daily values are shaped by:

- annual/monthly/seasonal benchmark anchors
- month and season
- weekday/weekend effect
- public holidays
- school holiday placeholders
- weather profile and weather risk
- event/news signals from `events_realistic.csv`
- optional Google Trends relative signal

## Hourly Generation

Hourly values are distributed from the daily total by venue-specific opening-hour curves. The hourly sum reconciles exactly to the daily base visitors for the same date and venue.

## Google Trends

Google Trends is optional and relative. It can help detect demand interest, but it cannot tell the backend how many people will visit. If `pytrends` is missing, the backend uses neutral seasonal fallback scores and labels the source as missing.

## Replacing Demo With Real Data

Real internal attendance can later replace calibrated demo attendance by adding a venue-aware import layer. The current output files are:

- `data/processed/attendance_calibrated_daily.csv`
- `data/processed/attendance_calibrated_hourly.csv`

All generated rows include:

```text
is_calibrated_demo = true
```
