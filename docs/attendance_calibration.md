# Attendance Calibration

Attendance values are calibrated demo estimates, not internal gate or ticketing data.

The backend uses public benchmarks as anchors and generates realistic daily/hourly values for product demonstration until a real venue attendance feed is connected.

## Public Anchors

Aquapark Fala:

- about 1.5M annual visitors
- over 0.5M summer visitors
- mixed indoor/outdoor aquapark
- strong weekend, holiday, school break and summer demand

Orientarium Zoo Lodz:

- close to 1M annual visitors
- August can exceed 200k visitors
- zoo and indoor/outdoor attraction
- strong weekend, tourism, school trip and holiday demand

## Forecast Ingredients

Daily estimates combine:

- annual/monthly public benchmark calibration
- month and seasonality
- day of week
- holidays and school holiday placeholders
- local events where available
- Google Trends as a relative demand signal only
- weather consensus and weather risk
- provider disagreement and forecast confidence
- venue-specific weather profile

Weather risk and visitor demand are intentionally separate concepts. A high-attendance summer day can still have low weather risk, and a higher-risk weather day can still produce strong demand if the venue has indoor resilience.

The backend applies weather as a modest final adjustment because the calibrated baseline already contains seasonality and proxy weather assumptions. This avoids double-counting heat and summer effects.

Venue-specific logic:

- Aquapark Fala: heat and stable summer weather can lift demand; light rain does not automatically suppress demand because indoor areas provide resilience.
- Orientarium Zoo Lodz: rain and storms reduce outdoor comfort more strongly, while good spring/summer weekends can lift attendance.

## Output Values

Each day returns:

- `visitors_low`
- `visitors_base`
- `visitors_high`
- `expected_visitors`
- `confidence_score`
- `weather_risk`
- demand, trend, event, holiday, seasonality and weather impact scores
- plain-language forecast explanation

Hourly curves are generated from the daily total and reconciled so the hourly sum matches the daily expected visitors.

## Limitations

The estimates are credible for a proof of concept and interview presentation, but should be replaced or recalibrated with internal gate data, ticket sales, POS data, staffing logs and campaign performance before production use.
