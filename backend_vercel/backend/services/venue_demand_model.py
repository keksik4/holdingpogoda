from datetime import date
from typing import Any


def weather_adjustment(venue_slug: str, consensus: dict[str, Any]) -> tuple[float, str, float]:
    icon = consensus.get("weather_icon_key") or consensus.get("weather_icon_consensus") or "partly_cloudy"
    interpreted_risk = consensus.get("weather_risk_level") or "unknown"
    temp = consensus.get("temperature_avg")
    rain_prob = consensus.get("precipitation_probability_avg") or 0
    precipitation = consensus.get("precipitation_avg") or 0
    cloud = consensus.get("cloud_cover_avg") or 50
    wind = consensus.get("wind_speed_avg") or 0
    if venue_slug == "aquapark_fala":
        score = 1.0
        if temp is not None:
            if 26 <= temp <= 34:
                score += 0.08
            elif 21 <= temp < 26:
                score += 0.04
            elif temp < 10:
                score += 0.01
        if icon == "storm" or precipitation >= 6 or rain_prob >= 82:
            score -= 0.08
        elif icon == "rain":
            if temp is not None and temp >= 25:
                score += 0.02
            else:
                score -= 0.03
        if cloud < 35 and rain_prob < 35:
            score += 0.02
        if wind >= 45:
            score -= 0.03
    else:
        score = 1.0
        if temp is not None:
            if 15 <= temp <= 27:
                score += 0.05
            elif temp < 3:
                score -= 0.05
        if icon == "storm" or precipitation >= 5 or rain_prob >= 78:
            score -= 0.13
        elif icon == "rain":
            score -= 0.03
        if cloud < 50 and rain_prob < 35:
            score += 0.02
        if wind >= 42:
            score -= 0.03
    risk = interpreted_risk if interpreted_risk in {"low", "medium", "high"} else "low"
    confidence_penalty = (consensus.get("provider_disagreement_score") or 0) * 0.08
    return max(0.88, min(1.12, score - confidence_penalty)), risk, round((score - 1.0) * 100, 2)


def explanation_for_forecast(
    venue_slug: str,
    target_date: date,
    date_relation: str,
    row: dict[str, Any],
    consensus: dict[str, Any],
) -> str:
    pieces = []
    if date_relation == "today":
        pieces.append("Dzisiejsza prognoza opiera się na najnowszym konsensusie pogodowym")
    elif date_relation == "historical":
        pieces.append("Szacunek historyczny łączy pogodę historyczną lub pamięć cache z kalibracją frekwencji")
    else:
        pieces.append("Prognoza korzysta z dostępnych prognoz pogody i skalibrowanych wzorców popytu")
    pieces.append("publiczne benchmarki rocznej frekwencji")
    pieces.append("profil operacyjny Holding Łódź")
    if target_date.weekday() >= 5:
        pieces.append("efekt weekendu")
    if row.get("seasonality_score", 0) >= 70:
        pieces.append("silną sezonowość")
    if consensus.get("provider_disagreement_score", 0) > 0.25:
        pieces.append("umiarkowaną rozbieżność dostawców pogody")
    weather_text = consensus.get("weather_explanation") or consensus.get("weather_description_consensus")
    if weather_text:
        pieces.append(str(weather_text))
    return ", ".join(pieces) + ". Wartość jest skalibrowaną estymacją demonstracyjną do czasu podłączenia danych bramkowych."
