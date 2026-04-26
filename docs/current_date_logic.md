# Current Date Logic

Airlines uses `Europe/Warsaw` as the product timezone. The backend is the source of truth for the current date so the frontend, calendar, and day details all agree on what “today” means.

## Endpoint

```text
GET /app/context
```

Returns:

- `current_date`
- `current_datetime`
- `timezone`
- `default_month`
- `default_selected_date`
- `available_history_start`
- `available_forecast_end`
- `data_freshness`
- `weather_refresh_status`

## Calendar Defaults

When `/venues/{venue_slug}/calendar` is opened without a `month` query, the backend uses `default_month` from `/app/context`.

The frontend also calls `/app/context` first and uses `default_month` when the route has no month query.

## Date Relation

Every calendar/day output can label a date as:

- `historical`: before today in Warsaw
- `today`: equal to today in Warsaw
- `forecast`: after today in Warsaw

This lets the UI distinguish actual/past calibrated history, the current operating day, and future forecast days.

## Today Handling

Today is highlighted on the calendar. Day details for today use the latest cached or refreshed weather consensus when available. Past and future days remain available through calendar navigation.
