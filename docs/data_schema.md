# Data Schema

## Business CSVs

### attendance_sample.csv

Required columns:

- `date`: YYYY-MM-DD
- `hour`: 0 to 23
- `visitors`: whole number
- `tickets_online`: whole number
- `tickets_offline`: whole number
- `revenue_tickets`: PLN value
- `revenue_gastro`: PLN value
- `revenue_parking`: PLN value
- `facility_zone`: text, for example outdoor, indoor, mixed
- `notes`: optional text

### events_sample.csv

- `date`
- `event_name`
- `expected_impact`
- `event_type`
- `indoor_or_outdoor`
- `notes`

### campaigns_sample.csv

- `date_start`
- `date_end`
- `campaign_name`
- `channel`
- `budget_pln`
- `target_segment`
- `message_type`
- `expected_impact`
- `notes`

## Validation

The importer validates required columns, date formats, numeric fields, non-empty required text, attendance hour range, and campaign date windows. Error messages include bad CSV row numbers.

## Main Database Tables

- `raw_weather_payloads`: saved raw provider responses and errors.
- `normalized_weather_records`: common weather schema across providers.
- `weather_provider_status`: provider health, missing fields, and last fetch status.
- `weather_consensus_records`: consensus weather and confidence.
- `attendance_records`: imported or demo attendance.
- `event_records`: imported or demo events.
- `campaign_records`: imported or demo campaigns.
- `feature_records`: model-ready feature rows.
- `forecast_records`: low/base/high forecast output.
- `model_evaluation_records`: MAE, RMSE, MAPE, ranking, and notes.
- `recommendation_records`: saved business recommendations.

## Demo Flags

Business records include `is_demo`. Forecast and recommendation responses include `demo_mode` or `is_demo`. `/data/status` reports whether attendance is demo, real, mixed, or empty.
