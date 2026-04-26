from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from backend.models.business_models import AttendanceRecord, CampaignRecord, EventRecord
from backend.models.forecast_models import FeatureRecord
from backend.models.weather_models import WeatherConsensusRecord
from backend.services.data_importer import ensure_demo_business_data
from backend.services.holidays_nager import get_polish_public_holiday_dates


PROFILE_WEIGHTS = {
    "outdoor": {"outdoor": 0.85, "indoor": 0.15},
    "indoor": {"outdoor": 0.25, "indoor": 0.75},
    "mixed": {"outdoor": 0.55, "indoor": 0.45},
}


def build_features(db: Session, facility_profile: str = "mixed", days_forward: int = 180) -> dict[str, Any]:
    facility_profile = _normalize_profile(facility_profile)
    ensure_demo_business_data(db)
    attendance_df = _attendance_df(db)
    events_df = _events_df(db)
    campaigns_df = _campaigns_df(db)
    weather_df = _weather_consensus_df(db)
    weather_data_mode = "real_weather_consensus" if not weather_df.empty else "seasonal_placeholder_weather"
    history_features = _build_history_features(attendance_df, events_df, campaigns_df, weather_df, facility_profile)
    future_features = _build_future_features(attendance_df, events_df, campaigns_df, weather_df, facility_profile, days_forward)
    combined = pd.concat([history_features, future_features], ignore_index=True)
    _upsert_feature_records(db, combined, facility_profile)
    processed_path = _save_processed_features(combined, facility_profile)
    return {
        "status": "ok",
        "facility_profile": facility_profile,
        "records": len(combined),
        "history_records": int((~combined["is_future"]).sum()),
        "future_records": int(combined["is_future"].sum()),
        "processed_path": processed_path,
        "demo_mode": bool(combined["is_demo"].any()),
        "business_data_mode": "demo" if bool(combined["is_demo"].all()) else "real_or_mixed",
        "weather_data_mode": weather_data_mode,
        "weather_consensus_records": len(weather_df),
        "sample": combined.head(10).to_dict(orient="records"),
    }


def feature_records_to_frame(db: Session, facility_profile: str = "mixed") -> pd.DataFrame:
    rows = (
        db.query(FeatureRecord)
        .filter(FeatureRecord.facility_profile == _normalize_profile(facility_profile))
        .order_by(FeatureRecord.date, FeatureRecord.hour)
        .all()
    )
    return pd.DataFrame([{column.name: getattr(row, column.name) for column in row.__table__.columns} for row in rows])


def _attendance_df(db: Session) -> pd.DataFrame:
    rows = db.query(AttendanceRecord).order_by(AttendanceRecord.date, AttendanceRecord.hour).all()
    return pd.DataFrame(
        [
            {
                "date": row.date,
                "hour": row.hour,
                "visitors": row.visitors,
                "tickets_online": row.tickets_online,
                "tickets_offline": row.tickets_offline,
                "revenue_tickets": row.revenue_tickets,
                "revenue_gastro": row.revenue_gastro,
                "revenue_parking": row.revenue_parking,
                "facility_zone": row.facility_zone,
                "is_demo": row.is_demo,
            }
            for row in rows
        ]
    )


def _events_df(db: Session) -> pd.DataFrame:
    rows = db.query(EventRecord).all()
    return pd.DataFrame(
        [{"date": row.date, "expected_impact": row.expected_impact, "indoor_or_outdoor": row.indoor_or_outdoor, "is_demo": row.is_demo} for row in rows]
    )


def _campaigns_df(db: Session) -> pd.DataFrame:
    rows = db.query(CampaignRecord).all()
    return pd.DataFrame(
        [
            {
                "date_start": row.date_start,
                "date_end": row.date_end,
                "budget_pln": row.budget_pln,
                "expected_impact": row.expected_impact,
                "target_segment": row.target_segment,
                "message_type": row.message_type,
                "is_demo": row.is_demo,
            }
            for row in rows
        ]
    )


def _weather_consensus_df(db: Session) -> pd.DataFrame:
    rows = db.query(WeatherConsensusRecord).order_by(WeatherConsensusRecord.target_datetime).all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "target_datetime": row.target_datetime,
                "date": row.target_datetime.date(),
                "hour": row.target_datetime.hour,
                "temperature": row.temperature,
                "apparent_temperature": row.apparent_temperature,
                "precipitation": row.precipitation,
                "rain": row.rain,
                "snowfall": row.snowfall,
                "cloud_cover": row.cloud_cover,
                "humidity": row.humidity,
                "wind_speed": row.wind_speed,
                "provider_disagreement_score": row.provider_disagreement_score,
                "forecast_confidence_score": row.forecast_confidence_score,
            }
            for row in rows
        ]
    )


def _build_history_features(
    attendance_df: pd.DataFrame,
    events_df: pd.DataFrame,
    campaigns_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    facility_profile: str,
) -> pd.DataFrame:
    df = attendance_df.copy()
    df = _add_calendar_features(df)
    df = _add_weather_features(df, weather_df)
    df = _add_business_features(df, events_df, campaigns_df)
    df = _add_lag_features(df)
    df["facility_profile"] = facility_profile
    df["is_future"] = False
    return df


def _build_future_features(
    attendance_df: pd.DataFrame,
    events_df: pd.DataFrame,
    campaigns_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    facility_profile: str,
    days_forward: int,
) -> pd.DataFrame:
    last_date = date.today()
    historical_hours = sorted(attendance_df["hour"].unique().tolist()) if not attendance_df.empty else list(range(9, 21))
    rows = []
    for offset in range(1, days_forward + 1):
        target_date = last_date + timedelta(days=offset)
        for hour in historical_hours:
            rows.append({"date": target_date, "hour": int(hour), "visitors": None, "is_demo": bool(attendance_df["is_demo"].all()) if not attendance_df.empty else True})
    df = pd.DataFrame(rows)
    df = _add_calendar_features(df)
    df = _add_weather_features(df, weather_df)
    df = _add_business_features(df, events_df, campaigns_df)
    df = _add_future_lag_estimates(df, attendance_df)
    df["facility_profile"] = facility_profile
    df["is_future"] = True
    return df


def _add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    years = set(pd.to_datetime(df["date"]).dt.year.unique().tolist())
    holidays = get_polish_public_holiday_dates(years)
    df["day_of_week"] = pd.to_datetime(df["date"]).dt.weekday
    df["is_weekend"] = df["day_of_week"] >= 5
    df["is_public_holiday"] = df["date"].isin(holidays)
    df["month"] = pd.to_datetime(df["date"]).dt.month
    df["season"] = df["month"].apply(_season)
    df["is_school_holiday_placeholder"] = df["month"].isin([7, 8])
    df["is_long_weekend_placeholder"] = df.apply(
        lambda row: bool(row["is_public_holiday"] and row["day_of_week"] in {0, 3, 4}),
        axis=1,
    )
    return df


def _add_weather_features(df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if not weather_df.empty:
        df = df.merge(weather_df.drop(columns=["target_datetime"], errors="ignore"), on=["date", "hour"], how="left")
    for field in [
        "temperature",
        "apparent_temperature",
        "precipitation",
        "rain",
        "snowfall",
        "cloud_cover",
        "humidity",
        "wind_speed",
        "provider_disagreement_score",
        "forecast_confidence_score",
    ]:
        if field not in df:
            df[field] = None
    synthetic = df["temperature"].isna()
    defaults = df.apply(lambda row: _seasonal_weather_defaults(row["date"], row["hour"]), axis=1, result_type="expand")
    for field in ["temperature", "apparent_temperature", "precipitation", "rain", "snowfall", "cloud_cover", "humidity", "wind_speed"]:
        df[field] = df[field].fillna(defaults[field])
    df["provider_disagreement_score"] = df["provider_disagreement_score"].fillna(0.55)
    df["forecast_confidence_score"] = df["forecast_confidence_score"].fillna(0.45)
    df.loc[~synthetic, "forecast_confidence_score"] = df.loc[~synthetic, "forecast_confidence_score"].fillna(0.72)
    df["outdoor_comfort_score"] = df.apply(_outdoor_comfort_score, axis=1)
    df["indoor_preference_score"] = df.apply(_indoor_preference_score, axis=1)
    return df


def _add_business_features(df: pd.DataFrame, events_df: pd.DataFrame, campaigns_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if events_df.empty:
        df["event_active"] = False
        df["event_expected_impact"] = 0.0
    else:
        event_daily = events_df.groupby("date", as_index=False)["expected_impact"].sum()
        df = df.merge(event_daily.rename(columns={"expected_impact": "event_expected_impact"}), on="date", how="left")
        df["event_expected_impact"] = df["event_expected_impact"].fillna(0.0)
        df["event_active"] = df["event_expected_impact"] > 0
    if campaigns_df.empty:
        df["campaign_active"] = False
        df["campaign_budget"] = 0.0
    else:
        budgets = []
        for target_date in df["date"]:
            active = campaigns_df[(campaigns_df["date_start"] <= target_date) & (campaigns_df["date_end"] >= target_date)]
            budgets.append(float(active["budget_pln"].sum() / 30) if not active.empty else 0.0)
        df["campaign_budget"] = budgets
        df["campaign_active"] = df["campaign_budget"] > 0
    return df


def _add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values(["hour", "date"])
    daily = df.groupby("date", as_index=False)["visitors"].sum().sort_values("date")
    daily["lag_visitors_1_day"] = daily["visitors"].shift(1)
    daily["lag_visitors_7_days"] = daily["visitors"].shift(7)
    daily["rolling_avg_7_days"] = daily["visitors"].shift(1).rolling(7, min_periods=1).mean()
    daily["rolling_avg_30_days"] = daily["visitors"].shift(1).rolling(30, min_periods=1).mean()
    df = df.merge(daily[["date", "lag_visitors_1_day", "lag_visitors_7_days", "rolling_avg_7_days", "rolling_avg_30_days"]], on="date", how="left")
    for field in ["lag_visitors_1_day", "lag_visitors_7_days", "rolling_avg_7_days", "rolling_avg_30_days"]:
        df[field] = df[field].fillna(df["visitors"].mean())
    return df


def _add_future_lag_estimates(df: pd.DataFrame, attendance_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    daily = attendance_df.groupby("date", as_index=False)["visitors"].sum().sort_values("date")
    if daily.empty:
        estimate = 350.0
    else:
        estimate = float(daily.tail(30)["visitors"].mean())
    df["lag_visitors_1_day"] = estimate
    df["lag_visitors_7_days"] = estimate
    df["rolling_avg_7_days"] = estimate
    df["rolling_avg_30_days"] = estimate
    return df


def _upsert_feature_records(db: Session, df: pd.DataFrame, facility_profile: str) -> None:
    db.query(FeatureRecord).filter(FeatureRecord.facility_profile == facility_profile).delete()
    records = []
    weights = PROFILE_WEIGHTS[facility_profile]
    for _, row in df.iterrows():
        # Facility profile changes how the same weather affects demand: outdoor parks like sun, indoor venues can benefit from rain.
        weather_score = row["outdoor_comfort_score"] * weights["outdoor"] + row["indoor_preference_score"] * weights["indoor"]
        records.append(
            FeatureRecord(
                date=row["date"],
                hour=int(row["hour"]),
                facility_profile=facility_profile,
                day_of_week=int(row["day_of_week"]),
                is_weekend=bool(row["is_weekend"]),
                is_public_holiday=bool(row["is_public_holiday"]),
                month=int(row["month"]),
                season=str(row["season"]),
                is_school_holiday_placeholder=bool(row["is_school_holiday_placeholder"]),
                is_long_weekend_placeholder=bool(row["is_long_weekend_placeholder"]),
                temperature=_float(row["temperature"]),
                apparent_temperature=_float(row["apparent_temperature"]),
                precipitation=_float(row["precipitation"]),
                rain=_float(row["rain"]),
                snowfall=_float(row["snowfall"]),
                cloud_cover=_float(row["cloud_cover"]),
                humidity=_float(row["humidity"]),
                wind_speed=_float(row["wind_speed"]),
                weather_score=float(weather_score),
                outdoor_comfort_score=float(row["outdoor_comfort_score"]),
                indoor_preference_score=float(row["indoor_preference_score"]),
                provider_disagreement_score=float(row["provider_disagreement_score"]),
                forecast_confidence_score=float(row["forecast_confidence_score"]),
                campaign_active=bool(row["campaign_active"]),
                campaign_budget=float(row["campaign_budget"]),
                event_active=bool(row["event_active"]),
                event_expected_impact=float(row["event_expected_impact"]),
                lag_visitors_1_day=_float(row["lag_visitors_1_day"]),
                lag_visitors_7_days=_float(row["lag_visitors_7_days"]),
                rolling_avg_7_days=_float(row["rolling_avg_7_days"]),
                rolling_avg_30_days=_float(row["rolling_avg_30_days"]),
                visitors=_float(row.get("visitors")),
                is_future=bool(row["is_future"]),
                is_demo=bool(row.get("is_demo", False)),
            )
        )
    db.add_all(records)
    db.commit()


def _save_processed_features(df: pd.DataFrame, facility_profile: str) -> str:
    path = f"data/processed/features_{facility_profile}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    full_path = Path(__file__).resolve().parents[2] / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(full_path, index=False)
    return str(full_path)


def _seasonal_weather_defaults(target_date: date, hour: int) -> dict[str, float]:
    month = target_date.month
    base_temp = {
        1: -1,
        2: 1,
        3: 6,
        4: 12,
        5: 18,
        6: 22,
        7: 24,
        8: 23,
        9: 18,
        10: 11,
        11: 5,
        12: 1,
    }[month]
    diurnal = 4 * (1 if 12 <= hour <= 16 else -0.5 if hour < 10 or hour > 19 else 0.2)
    precipitation = 0.4 if month in {4, 5, 6, 7, 8} else 0.25
    snowfall = 0.15 if month in {1, 2, 12} else 0.0
    return {
        "temperature": base_temp + diurnal,
        "apparent_temperature": base_temp + diurnal - (1 if month in {11, 12, 1, 2} else 0),
        "precipitation": precipitation,
        "rain": precipitation if snowfall == 0 else 0.05,
        "snowfall": snowfall,
        "cloud_cover": 62 if month in {11, 12, 1, 2} else 42,
        "humidity": 74 if month in {10, 11, 12, 1, 2} else 58,
        "wind_speed": 12 if month in {11, 12, 1, 2, 3} else 8,
    }


def _outdoor_comfort_score(row: pd.Series) -> float:
    score = 100
    score -= abs(float(row["temperature"]) - 23) * 2.2
    score -= float(row["precipitation"]) * 18
    score -= float(row["snowfall"]) * 25
    score -= float(row["cloud_cover"]) * 0.22
    score -= max(0.0, float(row["wind_speed"]) - 10) * 1.4
    score += 6 if row["is_weekend"] else 0
    return max(0.0, min(100.0, round(score, 2)))


def _indoor_preference_score(row: pd.Series) -> float:
    score = 34
    score += float(row["precipitation"]) * 13
    score += float(row["snowfall"]) * 18
    score += float(row["cloud_cover"]) * 0.24
    score += abs(float(row["temperature"]) - 21) * 0.8
    score += max(0.0, float(row["wind_speed"]) - 12) * 1.2
    return max(0.0, min(100.0, round(score, 2)))


def _season(month: int) -> str:
    if month in {12, 1, 2}:
        return "winter"
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    return "autumn"


def _normalize_profile(profile: str) -> str:
    return profile if profile in PROFILE_WEIGHTS else "mixed"


def _float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
