from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "Pogoda w Łodzi"
    app_env: str = "local"
    demo_mode: bool = True
    database_url: str = "sqlite:///./data/airlines.db"
    default_city: str = "Lodz"
    default_latitude: float = 51.7592
    default_longitude: float = 19.4560
    default_timezone: str = "Europe/Warsaw"
    met_no_user_agent: str = Field(
        "pogoda-w-lodzi/0.1 contact@example.com",
        description="MET Norway requires a descriptive User-Agent.",
    )
    api_timeout_seconds: int = 20
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_origin_regex: str | None = None
    openweather_api_key: str | None = None
    openmeteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    meteosource_api_key: str | None = None
    meteosource_base_url: str = "https://www.meteosource.com/api/v1/free/point"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_project_directories() -> None:
    for path in [
        PROJECT_ROOT / "data" / "sample",
        PROJECT_ROOT / "data" / "raw" / "weather",
        PROJECT_ROOT / "data" / "raw" / "business",
        PROJECT_ROOT / "data" / "processed",
        PROJECT_ROOT / "data" / "processed" / "weather_cache",
    ]:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Serverless bundles are read-only. Runtime code should still import
            # and rely on graceful cache fallbacks when writes are unavailable.
            continue


def configured_cors_origins() -> list[str]:
    value = get_settings().cors_origins.strip()
    if value == "*":
        return ["*"]
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return origins or ["http://localhost:3000", "http://127.0.0.1:3000"]


def configured_cors_origin_regex() -> str | None:
    value = get_settings().cors_origin_regex
    return value.strip() if value and value.strip() else None
