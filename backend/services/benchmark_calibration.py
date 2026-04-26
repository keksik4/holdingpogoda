from calendar import monthrange
from datetime import date
from typing import Any

import pandas as pd

from backend.services.public_source_research import load_public_benchmarks


MONTH_WEIGHTS = {
    "aquapark_fala": {
        1: 0.06,
        2: 0.065,
        3: 0.06,
        4: 0.065,
        5: 0.08,
        6: 0.12,
        7: 0.16,
        8: 0.155,
        9: 0.075,
        10: 0.06,
        11: 0.045,
        12: 0.055,
    },
    "orientarium_zoo_lodz": {
        1: 0.03,
        2: 0.035,
        3: 0.055,
        4: 0.095,
        5: 0.115,
        6: 0.105,
        7: 0.125,
        8: 0.20,
        9: 0.085,
        10: 0.065,
        11: 0.04,
        12: 0.05,
    },
}


DAY_OF_WEEK_FACTORS = {
    "aquapark_fala": {0: 0.78, 1: 0.78, 2: 0.82, 3: 0.88, 4: 1.04, 5: 1.45, 6: 1.58},
    "orientarium_zoo_lodz": {0: 0.62, 1: 0.66, 2: 0.76, 3: 0.84, 4: 1.02, 5: 1.62, 6: 1.72},
}


def annual_anchor_for_venue(venue_slug: str, year: int) -> float:
    annual_rows = [row for row in load_public_benchmarks(venue_slug) if row["benchmark_type"] == "annual"]
    if not annual_rows:
        return 600000.0
    base = float(annual_rows[0]["visitors"])
    base_year = pd.to_datetime(annual_rows[0]["period_start"]).year
    growth = 1 + max(0, year - base_year) * 0.025
    return base * growth


def benchmark_rows_for_generated_range(venue_slug: str, start_date: date, end_date: date) -> list[dict[str, Any]]:
    rows = []
    for row in load_public_benchmarks(venue_slug):
        period_start = pd.to_datetime(row["period_start"]).date()
        period_end = pd.to_datetime(row["period_end"]).date()
        if period_end >= start_date and period_start <= end_date and row["benchmark_type"] != "annual":
            rows.append(row)
    return rows


def apply_period_benchmark_scaling(df: pd.DataFrame, venue_slug: str) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df
    start_date = df["date"].min()
    end_date = df["date"].max()
    for row in benchmark_rows_for_generated_range(venue_slug, start_date, end_date):
        period_start = pd.to_datetime(row["period_start"]).date()
        period_end = pd.to_datetime(row["period_end"]).date()
        mask = (df["date"] >= period_start) & (df["date"] <= period_end)
        current_sum = df.loc[mask, "raw_visitors"].sum()
        if current_sum <= 0:
            continue
        target_sum = float(row["visitors"])
        if row["benchmark_label"].lower().startswith("more than") and current_sum >= target_sum:
            continue
        factor = target_sum / current_sum
        df.loc[mask, "raw_visitors"] *= factor
        df.loc[mask, "notes"] = df.loc[mask, "notes"] + f" Period scaled to benchmark: {row['benchmark_label']}."
    return df


def apply_benchmark_calibration(df: pd.DataFrame, venue_slug: str) -> pd.DataFrame:
    """Scale generated demo values to public annual anchors while preserving specific period anchors."""
    df = apply_period_benchmark_scaling(df, venue_slug)
    df = df.copy()
    if df.empty:
        return df
    df["benchmark_locked"] = False
    non_annual_rows = [row for row in load_public_benchmarks(venue_slug) if row["benchmark_type"] != "annual"]
    for row in non_annual_rows:
        period_start = pd.to_datetime(row["period_start"]).date()
        period_end = pd.to_datetime(row["period_end"]).date()
        mask = (df["date"] >= period_start) & (df["date"] <= period_end)
        df.loc[mask, "benchmark_locked"] = True
    for year in sorted({item.year for item in df["date"]}):
        annual_target = annual_anchor_for_venue(venue_slug, year)
        year_mask = df["date"].apply(lambda value: value.year == year)
        locked_mask = year_mask & df["benchmark_locked"]
        unlocked_mask = year_mask & ~df["benchmark_locked"]
        locked_sum = df.loc[locked_mask, "raw_visitors"].sum()
        unlocked_sum = df.loc[unlocked_mask, "raw_visitors"].sum()
        residual_target = max(0, annual_target - locked_sum)
        if unlocked_sum > 0 and residual_target > 0:
            df.loc[unlocked_mask, "raw_visitors"] *= residual_target / unlocked_sum
            df.loc[unlocked_mask, "notes"] = (
                df.loc[unlocked_mask, "notes"]
                + f" Non-anchored days scaled toward annual benchmark {annual_target:,.0f}."
            )
        elif locked_sum > 0:
            df.loc[locked_mask, "raw_visitors"] *= annual_target / locked_sum
    return df.drop(columns=["benchmark_locked"])


def month_weight(venue_slug: str, month: int) -> float:
    return MONTH_WEIGHTS[venue_slug][month]


def base_daily_from_annual(venue_slug: str, target_date: date) -> float:
    annual = annual_anchor_for_venue(venue_slug, target_date.year)
    days_in_month = monthrange(target_date.year, target_date.month)[1]
    return annual * month_weight(venue_slug, target_date.month) / days_in_month


def day_of_week_factor(venue_slug: str, target_date: date) -> float:
    return DAY_OF_WEEK_FACTORS[venue_slug][target_date.weekday()]


def seasonality_score(venue_slug: str, month: int) -> float:
    weights = MONTH_WEIGHTS[venue_slug]
    minimum = min(weights.values())
    maximum = max(weights.values())
    return round((weights[month] - minimum) / (maximum - minimum) * 100, 2)
