# Research Notes

## Business Question

How can visitor attendance planning be improved by automating the collection of weather, holiday, event, campaign, and attendance data, then turning those signals into forecasts and recommendations?

## Data Sources

| Source | Link | Purpose | MVP Suitability | Limitation |
|---|---|---|---|---|
| Open-Meteo Forecast | https://open-meteo.com/en/docs | Future hourly weather | Excellent, free, no key | One forecast provider |
| Open-Meteo Historical Weather | https://open-meteo.com/en/docs/historical-weather-api | Historical actual weather | Excellent for features/backtests | Not decision-time forecast |
| Open-Meteo Historical Forecast | https://open-meteo.com/en/docs/historical-forecast-api | Archived forecasts from 2022 onward | Strong for mature backtesting | Needs careful alignment |
| MET Norway Locationforecast | https://api.met.no/weatherapi/locationforecast/2.0/documentation | Independent forecast comparison | Good, free | Requires User-Agent, missing some fields |
| IMGW public API | https://danepubliczne.imgw.pl/pl/apiinfo | Polish official observations | Useful local reference | Station and field availability vary |
| Nager.Date | https://date.nager.at/Api | Polish public holidays | Excellent, simple | Does not cover school holidays or bridge days |

## MVP Conclusion

The chosen sources are enough to demonstrate a credible process transformation:

1. automate ingestion
2. normalize inconsistent source data
3. compare providers
4. turn uncertainty into planning confidence
5. combine external data with internal business data
6. generate forecasts and business recommendations

## Important Caveat

The sample attendance, event, and campaign files are fake. They prove the pipeline, not the business accuracy. Real company data is required before using forecasts for actual staffing or media spend.
