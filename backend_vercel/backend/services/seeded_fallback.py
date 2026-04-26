from __future__ import annotations

import hashlib
from datetime import date
from typing import TypeVar


T = TypeVar("T")


def stable_unit_interval(*parts: object) -> float:
    key = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def stable_choice(items: list[T], *parts: object) -> T:
    if not items:
        raise ValueError("stable_choice requires at least one item.")
    index = int(stable_unit_interval(*parts) * len(items)) % len(items)
    return items[index]


def deterministic_weather_variation(target_date: date, latitude: float, longitude: float) -> float:
    return stable_unit_interval("weather", target_date.isoformat(), round(latitude, 3), round(longitude, 3))
