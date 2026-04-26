# Weather Consensus

The weather layer is designed around multiple weather inputs, normalized into one shared schema and then combined into a venue-level consensus.

## Supported Inputs

- Open-Meteo Forecast: near-term forecast.
- Open-Meteo Historical Weather: historical actual weather.
- Open-Meteo Historical Forecast: archived forecasts from 2022 onward.
- MET Norway Locationforecast: independent forecast comparison.
- IMGW public synop data: Polish official observation where available.
- Seasonal calibration proxy: fallback only when provider data is not applicable or unavailable.

## Normalized Fields

Each input is normalized to fields such as:

- `target_datetime`
- `provider`
- `temperature`
- `apparent_temperature`
- `precipitation`
- `precipitation_probability`
- `rain`
- `snowfall`
- `cloud_cover`
- `humidity`
- `wind_speed`
- `wind_gusts`
- `pressure`
- `uv_index`
- `weather_code`
- `weather_description`
- `weather_icon`
- `provider_confidence`
- `fetched_at`

## Consensus Strategy

Numeric fields use robust averaging. With small samples the backend uses the median; with more values it trims extremes before averaging. This prevents one provider from distorting the result.

Weather interpretation is centralized in `backend/services/weather_interpretation.py`. Missing data never defaults to rain. Clouds do not become rain unless precipitation probability, rain amount, snowfall, showers or weather codes provide enough evidence.

The frontend-ready weather summary includes:

- `weather_icon_key`
- `weather_label_pl`
- `weather_risk_level`
- `weather_explanation`
- `weather_confidence_note`
- `source_count`
- `is_weather_fallback`

Weather icons use a conservative risk-priority strategy:

- storm and severe rain outrank all other conditions
- rain appears only when precipitation probability or precipitation amount is meaningful
- cloud and mixed conditions outrank clear sky
- sun/clear is only used when cloud and rain signals are low
- incomplete data becomes `unknown`, `brak danych pogodowych`, or `zmienne warunki`

## Disagreement And Confidence

`provider_disagreement_score` compares key fields such as temperature, precipitation, cloud cover, humidity and wind. Higher disagreement reduces `forecast_confidence_score`.

Confidence also reflects provider coverage and provider confidence. A forecast based on multiple active providers receives stronger confidence than one based only on the seasonal proxy.

## Caching

Weather consensus is cached in `data/processed/weather_cache`.

Current/near-term weather refreshes roughly every 45 minutes. Daily forecast values refresh every few hours. Historical and archived weather are cached longer. Provider failures are cached briefly to avoid retry loops.

Each response includes `cache_metadata` with:

- `cache_hit`
- `cached_at`
- `expires_at`
- `refresh_reason`
