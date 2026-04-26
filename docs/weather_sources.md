# Weather Sources And Consensus

The backend uses multiple weather providers because attendance decisions depend on the forecast available before the operating day, not only on measured weather afterward.

## Provider Roles

| Provider | Role | Strength | Limitation |
|---|---|---|---|
| Open-Meteo Forecast | Main short-term forecast | Broad hourly variables, no API key | Still one model/provider view |
| Open-Meteo Historical Weather | Historical actual weather | Useful for backtesting and features | Not the forecast managers saw before decisions |
| Open-Meteo Historical Forecast | Archived forecast context | Better decision-time analysis | More careful alignment needed later |
| MET Norway Locationforecast | Independent forecast comparison | Strong second opinion | Some fields are missing versus Open-Meteo |
| IMGW public data | Polish official reference | Local official observation source | Public endpoint may not include all needed fields |

## Raw And Normalized Storage

Each provider response is saved in `data/raw/weather` before normalization. The normalized database schema uses common fields such as temperature, precipitation, cloud cover, humidity, wind, pressure, UV index, weather code, description, and raw payload path.

## Provider Status

`GET /weather/providers/status` returns every expected provider, including providers that have not been attempted yet. It shows:

- status: `not_attempted`, `ok`, or `error`
- last successful fetch
- last attempt
- last error
- records from the last fetch
- missing fields
- MET Norway User-Agent configuration hint

## Consensus Method

For every target hour:

1. Take the latest normalized record from each provider.
2. Use median values for numeric weather fields.
3. Use the most common condition description/code where available.
4. Count providers used and missing fields.
5. Calculate provider disagreement across temperature, precipitation, cloud cover, humidity, wind, gusts, and pressure.
6. Calculate forecast confidence.

## Confidence Logic

Forecast confidence rises when there are more providers, better field completeness, and lower disagreement. It falls when providers disagree, because the business should shift to scenario planning and conservative staffing.

## Fallback Behavior

If no weather consensus exists, feature engineering uses seasonal placeholder weather so the demo pipeline still works. Forecast responses label this as `seasonal_placeholder_weather`.

## MET Norway User-Agent

MET Norway requires a useful User-Agent. Configure `.env`:

```text
MET_NO_USER_AGENT=welcome-to-airlines-local-demo/0.1 your-email@example.com
```
