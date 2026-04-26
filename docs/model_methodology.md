# Model Methodology

## Forecasting Goal

Estimate visitor attendance for planning, not to produce a perfect scientific forecast. The system turns expected demand into staffing, queue, parking, gastronomy, management, and marketing guidance.

## Features Used

- Calendar: hour, weekday, weekend, month, season.
- Holidays: Polish public holidays from Nager.Date or fallback holiday rules.
- Weather: temperature, apparent temperature, precipitation, rain, snow, cloud cover, humidity, wind.
- Consensus: provider disagreement and forecast confidence.
- Business context: campaigns, campaign budget, events, expected event impact.
- History: lag visitors for 1 day and 7 days, rolling 7-day and 30-day averages.
- Facility profile: outdoor, indoor, or mixed weighting.

## Similar-Day Baseline

This baseline finds past periods that resemble the forecast period: weekday, month, holiday status, event status, and weather score. It is intentionally explainable and useful as a first business benchmark.

## Random Forest

Random Forest averages many decision trees. It is useful for structured data where attendance depends on interacting factors such as weekends, weather, events, and campaigns.

## Gradient Boosting

Gradient Boosting builds trees sequentially to correct earlier errors. It often performs well on tabular business forecasting problems.

## Ensemble

The ensemble averages available model outputs. If scikit-learn is unavailable or the dataset is too small, the ensemble falls back to the similar-day baseline.

## Optional XGBoost And Prophet

XGBoost and Prophet are not installed by default. The model evaluation endpoint reports them as skipped so the fallback is explicit. They are good candidates after the MVP has real data and a stable environment.

## Scenarios

- Base: ensemble forecast.
- Low: base reduced by uncertainty.
- High: base increased by uncertainty.

Uncertainty grows when model agreement is weak or weather confidence is low.

## Evaluation

The holdout evaluation reports:

- MAE: average absolute visitor error.
- RMSE: error measure that penalizes large misses.
- MAPE: average percentage error.
- Rank: model order by MAE.

The goal is not only accuracy. The goal is a repeatable process that management can understand and improve with better data.
