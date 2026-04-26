import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.routes_app import router as app_context_router  # noqa: E402
from backend.api.routes_venues import router as venues_router  # noqa: E402
from backend.config import (  # noqa: E402
    configured_cors_origin_regex,
    configured_cors_origins,
    get_settings,
)


settings = get_settings()


app = FastAPI(
    title="Pogoda w Łodzi",
    description="Public API for venue attendance forecasting in Łódź.",
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

app.include_router(app_context_router)
app.include_router(venues_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "mode": "vercel-serverless",
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Pogoda w Łodzi backend is running.",
        "docs": "/docs",
        "health": "/health",
    }
