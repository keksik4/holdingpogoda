from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_app import router as app_context_router
from backend.api.routes_data import router as data_router
from backend.api.routes_features import router as features_router
from backend.api.routes_forecast import router as forecast_router
from backend.api.routes_health import router as health_router
from backend.api.routes_model import router as model_router
from backend.api.routes_public_data import router as public_data_router
from backend.api.routes_recommendations import router as recommendations_router
from backend.api.routes_sources import router as sources_router
from backend.api.routes_venues import router as venues_router
from backend.api.routes_weather import router as weather_router
from backend.config import configured_cors_origin_regex, configured_cors_origins, get_settings
from backend.database import init_db
from backend.services.demo_data_generator import create_sample_csv_files


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="Backend API for weather-aware attendance forecasting for municipal attractions in Lodz.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_cors_origins(),
    allow_origin_regex=configured_cors_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    create_sample_csv_files()


app.include_router(health_router)
app.include_router(app_context_router)
app.include_router(sources_router)
app.include_router(weather_router)
app.include_router(data_router)
app.include_router(features_router)
app.include_router(forecast_router)
app.include_router(recommendations_router)
app.include_router(model_router)
app.include_router(venues_router)
app.include_router(public_data_router)


@app.get("/")
def root():
    return {
        "message": "Pogoda w Łodzi backend is running.",
        "docs_url": "/docs",
        "health_url": "/health",
    }
