from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.weather_common import provider_status_payload


router = APIRouter(tags=["sources"])


@router.get("/sources")
def sources(db: Session = Depends(get_db)):
    return {
        "weather_sources": [
            {
                "name": "Open-Meteo Forecast API",
                "url": "https://open-meteo.com/en/docs",
                "role": "Current and future weather forecast; strongest default broad coverage provider.",
            },
            {
                "name": "Open-Meteo Historical Weather API",
                "url": "https://open-meteo.com/en/docs/historical-weather-api",
                "role": "Historical actual weather for model backtesting and feature enrichment.",
            },
            {
                "name": "Open-Meteo Historical Forecast API",
                "url": "https://open-meteo.com/en/docs/historical-forecast-api",
                "role": "Archived forecasts from 2022 onward for decision-time weather context.",
            },
            {
                "name": "MET Norway Locationforecast API",
                "url": "https://api.met.no/weatherapi/locationforecast/2.0/documentation",
                "role": "Independent forecast provider for comparison and consensus.",
            },
            {
                "name": "IMGW public data API",
                "url": "https://danepubliczne.imgw.pl/pl/apiinfo",
                "role": "Official Polish public weather observation source where local data is available.",
            },
            {
                "name": "Nager.Date public holidays API",
                "url": "https://date.nager.at/Api",
                "role": "Polish public holidays for attendance features.",
            },
        ],
        "provider_status": provider_status_payload(db),
    }
