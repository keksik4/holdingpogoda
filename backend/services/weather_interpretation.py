from __future__ import annotations

from typing import Any


RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
STORM_CODES = {95, 96, 99}
FOG_CODES = {45, 48}
CLOUD_CODES = {3}
PARTLY_CLOUDY_CODES = {1, 2}
CLEAR_CODES = {0}


def interpret_weather(
    *,
    weather_code: str | int | float | None = None,
    precipitation_probability: float | None = None,
    precipitation: float | None = None,
    rain: float | None = None,
    showers: float | None = None,
    snowfall: float | None = None,
    cloud_cover: float | None = None,
    temperature: float | None = None,
    wind_speed: float | None = None,
    source_count: int = 0,
    confidence: float | None = None,
    is_fallback: bool = False,
    provider_disagreement_score: float | None = None,
) -> dict[str, Any]:
    code = _numeric_code(weather_code)
    amount = max(_safe(precipitation), _safe(rain), _safe(showers))
    snow_amount = _safe(snowfall)
    probability = precipitation_probability
    cloud = cloud_cover
    wind = _safe(wind_speed)
    confidence_value = 0.45 if confidence is None else max(0.0, min(1.0, confidence))
    missing_weather_core = code is None and probability is None and precipitation is None and rain is None and showers is None and snowfall is None and cloud is None

    if missing_weather_core:
        return _result(
            icon_key="unknown",
            label_pl="brak danych pogodowych",
            risk_level="unknown",
            explanation="Brak wystarczających danych pogodowych dla tej daty.",
            confidence_note="Niska pewność, ponieważ brakuje podstawowych pól pogodowych.",
            confidence=max(0.25, min(confidence_value, 0.45)),
            source_count=source_count,
            is_fallback=True,
        )

    rain_evidence = _rain_is_meaningful(code, probability, amount)
    snow_evidence = code in SNOW_CODES or _is_openweather_group(code, 600, 699) or snow_amount >= 0.3
    storm_evidence = code in STORM_CODES or _is_openweather_group(code, 200, 299)
    cloud_value = 50 if cloud is None else cloud
    fallback_note = " Użyto deterministycznego przybliżenia sezonowego." if is_fallback else ""

    if storm_evidence:
        return _result(
            icon_key="storm",
            label_pl="burza",
            risk_level="high",
            explanation=f"Prognoza wskazuje ryzyko burz lub gwałtownych opadów.{fallback_note}",
            confidence_note=_confidence_note(confidence_value, source_count, provider_disagreement_score, is_fallback),
            confidence=confidence_value,
            source_count=source_count,
            is_fallback=is_fallback,
        )
    if snow_evidence:
        risk = "high" if snow_amount >= 2.0 or wind >= 35 else "medium"
        return _result(
            icon_key="snow",
            label_pl="śnieg",
            risk_level=risk,
            explanation=f"Warunki wskazują na opady śniegu lub śnieg z deszczem.{fallback_note}",
            confidence_note=_confidence_note(confidence_value, source_count, provider_disagreement_score, is_fallback),
            confidence=confidence_value,
            source_count=source_count,
            is_fallback=is_fallback,
        )
    if rain_evidence:
        risk = "high" if amount >= 5.0 or _safe(probability) >= 78 or wind >= 40 else "medium"
        return _result(
            icon_key="rain",
            label_pl="deszcz",
            risk_level=risk,
            explanation=f"Opad jest oznaczony jako istotny: prawdopodobieństwo { _format_probability(probability) }, opad {amount:.1f} mm.{fallback_note}",
            confidence_note=_confidence_note(confidence_value, source_count, provider_disagreement_score, is_fallback),
            confidence=confidence_value,
            source_count=source_count,
            is_fallback=is_fallback,
        )
    if wind >= 45:
        return _result(
            icon_key="wind",
            label_pl="silny wiatr",
            risk_level="medium",
            explanation=f"Brak istotnych opadów, ale wiatr może wpływać na komfort i operacje.{fallback_note}",
            confidence_note=_confidence_note(confidence_value, source_count, provider_disagreement_score, is_fallback),
            confidence=confidence_value,
            source_count=source_count,
            is_fallback=is_fallback,
        )
    if code in FOG_CODES or _is_openweather_group(code, 700, 799):
        return _result(
            icon_key="fog",
            label_pl="mgła",
            risk_level="medium",
            explanation=f"Mgła lub zamglenie może utrudniać dojazd i komfort gości.{fallback_note}",
            confidence_note=_confidence_note(confidence_value, source_count, provider_disagreement_score, is_fallback),
            confidence=confidence_value,
            source_count=source_count,
            is_fallback=is_fallback,
        )
    if cloud_value >= 82 or code in CLOUD_CODES or code in {803, 804}:
        return _result(
            icon_key="cloud",
            label_pl="pochmurno",
            risk_level="low",
            explanation=f"Zachmurzenie jest wysokie, ale brak istotnego sygnału opadów.{fallback_note}",
            confidence_note=_confidence_note(confidence_value, source_count, provider_disagreement_score, is_fallback),
            confidence=confidence_value,
            source_count=source_count,
            is_fallback=is_fallback,
        )
    if cloud_value >= 35 or code in PARTLY_CLOUDY_CODES or code in {801, 802}:
        return _result(
            icon_key="partly_cloudy",
            label_pl="zmienne warunki",
            risk_level="low",
            explanation=f"Warunki są mieszane lub częściowo zachmurzone, bez istotnego sygnału opadów.{fallback_note}",
            confidence_note=_confidence_note(confidence_value, source_count, provider_disagreement_score, is_fallback),
            confidence=confidence_value,
            source_count=source_count,
            is_fallback=is_fallback,
        )
    if code in CLEAR_CODES or code == 800 or cloud_value < 35:
        comfort = " i ciepło" if temperature is not None and temperature >= 24 else ""
        return _result(
            icon_key="sun",
            label_pl="słonecznie",
            risk_level="low",
            explanation=f"Pogoda wygląda stabilnie{comfort}; brak istotnych opadów.{fallback_note}",
            confidence_note=_confidence_note(confidence_value, source_count, provider_disagreement_score, is_fallback),
            confidence=confidence_value,
            source_count=source_count,
            is_fallback=is_fallback,
        )

    return _result(
        icon_key="partly_cloudy",
        label_pl="zmienne warunki",
        risk_level="low",
        explanation=f"Dane wskazują na neutralne lub zmienne warunki bez mocnego sygnału ryzyka.{fallback_note}",
        confidence_note=_confidence_note(confidence_value, source_count, provider_disagreement_score, is_fallback),
        confidence=confidence_value,
        source_count=source_count,
        is_fallback=is_fallback,
    )


def _rain_is_meaningful(code: int | None, probability: float | None, amount: float) -> bool:
    probability_value = _safe(probability)
    if amount >= 1.0:
        return True
    if probability_value >= 55 and amount >= 0.1:
        return True
    if probability_value >= 65:
        return True
    if code in RAIN_CODES and (probability_value >= 45 or amount >= 0.3):
        return True
    if _is_openweather_group(code, 300, 599) and (probability_value >= 35 or amount >= 0.1):
        return True
    return False


def _is_openweather_group(code: int | None, start: int, end: int) -> bool:
    return code is not None and start <= code <= end


def _numeric_code(value: str | int | float | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        text = str(value).lower()
        if "thunder" in text or "storm" in text:
            return 95
        if "snow" in text or "sleet" in text:
            return 71
        if "rain" in text or "shower" in text or "drizzle" in text:
            return 61
        if "cloud" in text or "overcast" in text:
            return 3
        if "partly" in text or "fair" in text:
            return 2
        if "clear" in text or "sun" in text:
            return 0
        return None


def _safe(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _format_probability(value: float | None) -> str:
    if value is None:
        return "brak danych"
    return f"{round(value)}%"


def _confidence_note(confidence: float, source_count: int, disagreement: float | None, is_fallback: bool) -> str:
    if is_fallback:
        return "Pewność ograniczona: użyto deterministycznego przybliżenia sezonowego."
    if source_count >= 2 and confidence >= 0.72 and (disagreement or 0) < 0.2:
        return "Wysoka pewność: kilku dostawców daje spójny sygnał."
    if source_count >= 2:
        return "Umiarkowana pewność: dostępnych jest kilku dostawców, ale sygnały nie są idealnie zgodne."
    return "Umiarkowana pewność: prognoza opiera się na ograniczonej liczbie źródeł."


def _result(
    *,
    icon_key: str,
    label_pl: str,
    risk_level: str,
    explanation: str,
    confidence_note: str,
    confidence: float,
    source_count: int,
    is_fallback: bool,
) -> dict[str, Any]:
    return {
        "icon_key": icon_key,
        "label_pl": label_pl,
        "risk_level": risk_level,
        "explanation": explanation,
        "confidence_note": confidence_note,
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "source_count": source_count,
        "is_fallback": is_fallback,
    }
