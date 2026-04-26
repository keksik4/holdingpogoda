# Real Data Sources

This backend separates exact public facts, real API data, relative signals, and calibrated demo attendance.

## Venue Profiles

### Aquapark Fala

- Official source: https://aquapark.lodz.pl/cennik/kontakt/
- Tourism profile: https://lodz.travel/en/tourism/what-to-see/green-lodz/sports-and-recreation/aquapark-fala/
- Provides: official address, venue identity, public description, indoor/outdoor attraction profile.
- Confidence: high for address and descriptive venue profile.

### Orientarium Zoo Łódź

- Official source: https://zoo.lodz.pl/
- Provides: official address, venue identity, public description.
- Confidence: high for address and venue profile.

## Visitor Benchmarks

### Aquapark Fala

- 2024 annual benchmark: approximately 1.5M visitors.
- Source: https://lodz.pl/artykul/rekordy-w-orientarium-zoo-lodz-i-aquaparku-fala-ile-osob-odwiedzilo-zdrowie-66002/
- Confidence: high as public benchmark, but still approximate.
- Summer 2025 benchmark: more than 0.5M visitors.
- Source status: encoded from product brief and marked as needing manual source confirmation.
- Confidence: medium.

### Orientarium Zoo Łódź

- 2024 annual benchmark: close to 1M visitors.
- Source: https://lodz.pl/artykul/rekordy-w-orientarium-zoo-lodz-i-aquaparku-fala-ile-osob-odwiedzilo-zdrowie-66002/
- Confidence: high as public benchmark, but still approximate.
- August 2025 benchmark: more than 200k visitors assumption, calibrated against a public article reporting a record month above 190k.
- Source: https://radiolodz.pl/rekordowy-miesiac-lodzkiego-zoo-prawie-200-tysiecy-odwiedzajacych%2C546350/
- Confidence: medium.

## Weather Sources

- Open-Meteo Forecast API: real forecast data.
- Open-Meteo Historical Weather API: real historical weather data.
- Open-Meteo Historical Forecast API: archived forecast context.
- MET Norway Locationforecast API: independent forecast comparison.
- IMGW public data API: official Polish observations where available.

Weather source confidence is high for API availability and lower for individual missing fields. Provider disagreement reduces forecast confidence.

## Holiday Source

- Nager.Date: https://date.nager.at/Api
- Provides Polish public holidays.
- Confidence: high.

## Google Trends

Google Trends is optional through `pytrends`. It is only a relative demand signal. It is never used as direct attendance.

If `pytrends` is unavailable, the backend returns safe seasonal fallback values and labels the source as missing.

## What Is Exact

- Venue names and addresses from official/public profiles.
- API weather records when fetched successfully.
- Public holiday dates.

## What Is Estimated

- Annual/monthly benchmark values described as approximate by public sources.
- Weather impact assumptions by venue.
- Seasonality, event, and campaign weighting.

## What Is Demo

- Daily attendance.
- Hourly attendance.
- Low/base/high visitor scenarios.
- Event impact scores where source URLs are missing or manual.

All generated attendance is labeled `is_calibrated_demo`.
