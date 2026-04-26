# Architecture

## Pipeline

```text
Weather APIs + holiday API + business CSVs
  -> ingestion services
  -> raw file storage
  -> normalized SQLite tables
  -> weather consensus and confidence
  -> feature engineering
  -> forecasting models
  -> low/base/high scenarios
  -> deterministic recommendations
  -> FastAPI JSON endpoints
  -> Streamlit inspection preview
```

## Main Components

- `backend/main.py`: FastAPI application and route registration.
- `backend/config.py`: local settings, default Lodz location, MET Norway User-Agent.
- `backend/database.py`: SQLite engine and SQLAlchemy session setup.
- `backend/models`: database tables.
- `backend/services`: business logic for weather, data import, features, forecasting, and recommendations.
- `backend/api`: endpoint layer.
- `local_preview/app.py`: simple Streamlit inspector.

## Data Layers

The project keeps data types separate:

- Real weather API responses: `data/raw/weather`.
- Imported or demo business CSV copies: `data/raw/business`.
- Sample fake CSVs: `data/sample`.
- Processed feature exports: `data/processed`.
- Local database: `data/airlines.db`.

## Reliability Choices

- Weather provider errors are captured in provider status instead of crashing the whole pipeline.
- Real CSV imports remove old demo rows for the same table.
- Forecasting falls back to an explainable similar-day baseline if ML dependencies or data volume are insufficient.
- Forecast confidence combines model agreement and weather-provider agreement.

## Current Boundary

This is a local proof of concept. It is designed to be explainable, inspectable, and Windows-friendly. Production scheduling, authentication, migrations, monitoring, and frontend polish are intentionally future phases.
