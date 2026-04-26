import json
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.models.business_models import AttendanceRecord
from backend.models.forecast_models import ForecastRecord, ModelEvaluationRecord
from backend.services.feature_engineering import build_features, feature_records_to_frame

try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    SKLEARN_AVAILABLE = True
except Exception:  # noqa: BLE001
    SKLEARN_AVAILABLE = False

try:
    import xgboost  # noqa: F401

    XGBOOST_AVAILABLE = True
except Exception:  # noqa: BLE001
    XGBOOST_AVAILABLE = False

try:
    import prophet  # noqa: F401

    PROPHET_AVAILABLE = True
except Exception:  # noqa: BLE001
    PROPHET_AVAILABLE = False


HORIZONS = {
    "operational": {"start": 1, "end": 7, "grain": "hourly"},
    "tactical": {"start": 8, "end": 30, "grain": "daily"},
    "strategic": {"start": 31, "end": 180, "grain": "daily"},
}


FEATURE_COLUMNS = [
    "day_of_week",
    "is_weekend",
    "is_public_holiday",
    "month",
    "season_code",
    "is_school_holiday_placeholder",
    "is_long_weekend_placeholder",
    "temperature",
    "apparent_temperature",
    "precipitation",
    "rain",
    "snowfall",
    "cloud_cover",
    "humidity",
    "wind_speed",
    "weather_score",
    "outdoor_comfort_score",
    "indoor_preference_score",
    "provider_disagreement_score",
    "forecast_confidence_score",
    "campaign_active",
    "campaign_budget",
    "event_active",
    "event_expected_impact",
    "lag_visitors_1_day",
    "lag_visitors_7_days",
    "rolling_avg_7_days",
    "rolling_avg_30_days",
]


SEASON_CODES = {"winter": 0, "spring": 1, "summer": 2, "autumn": 3}


def build_forecast(db: Session, horizon: str = "operational", facility_profile: str = "mixed") -> dict[str, Any]:
    horizon = horizon if horizon in HORIZONS else "operational"
    facility_profile = facility_profile if facility_profile in {"outdoor", "indoor", "mixed"} else "mixed"
    if feature_records_to_frame(db, facility_profile).empty:
        build_features(db, facility_profile=facility_profile)
    df = feature_records_to_frame(db, facility_profile)
    if df.empty:
        raise ValueError("Feature table is empty. Import data or enable demo mode first.")
    df = _prepare_frame(df)
    history = df[(df["is_future"] == False) & df["visitors"].notna()].copy()  # noqa: E712
    future = _future_slice(df, horizon).copy()
    if history.empty or future.empty:
        raise ValueError(f"Cannot build {horizon} forecast because history or future features are missing.")
    revenue_per_visitor = _revenue_per_visitor(db)
    models, evaluation = _train_and_evaluate(history, facility_profile)
    _store_evaluation(db, evaluation, facility_profile, bool(history["is_demo"].all()))
    predicted = _predict_future(history, future, models)
    forecast_rows = _shape_forecast_rows(predicted, horizon, facility_profile, revenue_per_visitor)
    db.query(ForecastRecord).filter(
        ForecastRecord.horizon == horizon,
        ForecastRecord.facility_profile == facility_profile,
    ).delete()
    db.add_all([ForecastRecord(**row) for row in forecast_rows])
    db.commit()
    return {
        "status": "ok",
        "horizon": horizon,
        "facility_profile": facility_profile,
        "records": len(forecast_rows),
        "demo_mode": bool(history["is_demo"].all()),
        "business_data_mode": "demo" if bool(history["is_demo"].all()) else "real_or_mixed",
        "weather_data_mode": _weather_data_mode(predicted),
        "available_models": _available_model_status(),
        "model_evaluation": evaluation,
        "items": _serialize_forecast_rows(forecast_rows),
    }


def get_latest_forecast(db: Session, horizon: str = "operational", facility_profile: str = "mixed") -> list[dict[str, Any]]:
    rows = (
        db.query(ForecastRecord)
        .filter(ForecastRecord.horizon == horizon, ForecastRecord.facility_profile == facility_profile)
        .order_by(ForecastRecord.target_date, ForecastRecord.hour)
        .all()
    )
    return [
        {
            "target_date": row.target_date.isoformat(),
            "hour": row.hour,
            "expected_visitors": round(row.expected_visitors, 2),
            "low_scenario": round(row.low_scenario, 2),
            "high_scenario": round(row.high_scenario, 2),
            "expected_revenue": round(row.expected_revenue, 2),
            "model_name": row.model_name,
            "confidence_score": round(row.confidence_score, 3),
            "provider_disagreement_score": round(row.provider_disagreement_score, 3),
            "forecast_confidence_score": round(row.forecast_confidence_score, 3),
            "weather_summary": row.weather_summary,
            "is_demo": row.is_demo,
        }
        for row in rows
    ]


def get_model_evaluation(db: Session, facility_profile: str = "mixed") -> dict[str, Any]:
    rows = (
        db.query(ModelEvaluationRecord)
        .filter(ModelEvaluationRecord.facility_profile == facility_profile)
        .order_by(ModelEvaluationRecord.rank, ModelEvaluationRecord.evaluated_at.desc())
        .all()
    )
    if not rows:
        if feature_records_to_frame(db, facility_profile).empty:
            build_features(db, facility_profile=facility_profile)
        build_forecast(db, horizon="operational", facility_profile=facility_profile)
        rows = (
            db.query(ModelEvaluationRecord)
            .filter(ModelEvaluationRecord.facility_profile == facility_profile)
            .order_by(ModelEvaluationRecord.rank, ModelEvaluationRecord.evaluated_at.desc())
            .all()
        )
    latest_by_model = {}
    for row in rows:
        latest_by_model.setdefault(row.model_name, row)
    items = sorted(latest_by_model.values(), key=lambda row: row.rank)
    return {
        "facility_profile": facility_profile,
        "items": [
            {
                "model_name": row.model_name,
                "mae": round(row.mae, 2),
                "rmse": round(row.rmse, 2),
                "mape": round(row.mape, 2),
                "rank": row.rank,
                "notes": row.notes,
                "is_demo": row.is_demo,
            }
            for row in items
        ],
    }


def _prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["season_code"] = df["season"].map(SEASON_CODES).fillna(1)
    for column in FEATURE_COLUMNS:
        if column not in df:
            df[column] = 0
        df[column] = df[column].fillna(0)
        if df[column].dtype == bool:
            df[column] = df[column].astype(int)
    return df


def _future_slice(df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    config = HORIZONS[horizon]
    start = date.today() + timedelta(days=config["start"])
    end = date.today() + timedelta(days=config["end"])
    return df[(df["is_future"] == True) & (df["date"] >= start) & (df["date"] <= end)]  # noqa: E712


def _train_and_evaluate(history: pd.DataFrame, facility_profile: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    history = history.sort_values(["date", "hour"]).copy()
    split_index = max(int(len(history) * 0.8), min(len(history) - 1, 1))
    train = history.iloc[:split_index].copy()
    test = history.iloc[split_index:].copy()
    if test.empty:
        test = history.tail(min(24, len(history))).copy()
        train = history.drop(test.index)
    evaluation: list[dict[str, Any]] = []
    models: dict[str, Any] = {"similar_day_baseline": None}
    baseline_predictions = _similar_day_predictions(train, test)
    evaluation.append(_metrics("similar_day_baseline", test["visitors"].to_numpy(), baseline_predictions, facility_profile))
    if SKLEARN_AVAILABLE and len(train) >= 80:
        x_train = train[FEATURE_COLUMNS]
        y_train = train["visitors"].astype(float)
        x_test = test[FEATURE_COLUMNS]
        rf = RandomForestRegressor(n_estimators=120, random_state=42, min_samples_leaf=3)
        rf.fit(x_train, y_train)
        models["random_forest"] = rf
        evaluation.append(_metrics("random_forest", test["visitors"].to_numpy(), rf.predict(x_test), facility_profile))
        gb = GradientBoostingRegressor(random_state=42, max_depth=3, learning_rate=0.05, n_estimators=160)
        gb.fit(x_train, y_train)
        models["gradient_boosting"] = gb
        evaluation.append(_metrics("gradient_boosting", test["visitors"].to_numpy(), gb.predict(x_test), facility_profile))
    else:
        reason = "Skipped because scikit-learn is not installed or the training set is too small."
        evaluation.append(_skipped_metric("random_forest", reason))
        evaluation.append(_skipped_metric("gradient_boosting", reason))
    if not XGBOOST_AVAILABLE:
        evaluation.append(_skipped_metric("optional_xgboost", "Optional XGBoost is not installed by default for Windows simplicity."))
    if not PROPHET_AVAILABLE:
        evaluation.append(_skipped_metric("optional_prophet", "Optional Prophet is not installed by default for Windows simplicity."))
    valid = [item for item in evaluation if item["mae"] > 0]
    ranked = sorted(valid, key=lambda item: item["mae"])
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    skipped = [item for item in evaluation if item["mae"] == 0]
    for item in skipped:
        item["rank"] = len(ranked) + 1
    return models, ranked + skipped


def _predict_future(history: pd.DataFrame, future: pd.DataFrame, models: dict[str, Any]) -> pd.DataFrame:
    future = future.copy()
    baseline = _similar_day_predictions(history, future)
    output_columns = {"similar_day_baseline": baseline}
    if models.get("random_forest") is not None:
        output_columns["random_forest"] = models["random_forest"].predict(future[FEATURE_COLUMNS])
    if models.get("gradient_boosting") is not None:
        output_columns["gradient_boosting"] = models["gradient_boosting"].predict(future[FEATURE_COLUMNS])
    for name, values in output_columns.items():
        future[f"pred_{name}"] = np.maximum(values, 0)
    prediction_cols = [column for column in future.columns if column.startswith("pred_")]
    future["expected_visitors"] = future[prediction_cols].mean(axis=1)
    future["model_agreement"] = future.apply(lambda row: _model_agreement([row[column] for column in prediction_cols]), axis=1)
    future["model_outputs_json"] = future.apply(
        lambda row: json.dumps({column.replace("pred_", ""): round(float(row[column]), 2) for column in prediction_cols}),
        axis=1,
    )
    future["confidence_score"] = future.apply(
        lambda row: max(
            0.1,
            min(
                0.98,
                float(row["model_agreement"]) * 0.55
                + float(row["forecast_confidence_score"]) * 0.35
                + (1 - float(row["provider_disagreement_score"])) * 0.10,
            ),
        ),
        axis=1,
    )
    return future


def _shape_forecast_rows(
    predicted: pd.DataFrame,
    horizon: str,
    facility_profile: str,
    revenue_per_visitor: float,
) -> list[dict[str, Any]]:
    config = HORIZONS[horizon]
    rows: list[dict[str, Any]] = []
    if config["grain"] == "hourly":
        for _, row in predicted.iterrows():
            uncertainty = 0.12 + (1 - float(row["confidence_score"])) * 0.35
            expected = float(row["expected_visitors"])
            rows.append(_forecast_payload(row, horizon, facility_profile, expected, uncertainty, revenue_per_visitor, int(row["hour"])))
        return rows
    grouped = predicted.groupby("date")
    for target_date, group in grouped:
        expected = float(group["expected_visitors"].sum())
        confidence = float(group["confidence_score"].mean())
        row = group.iloc[0].copy()
        row["confidence_score"] = confidence
        row["provider_disagreement_score"] = float(group["provider_disagreement_score"].mean())
        row["forecast_confidence_score"] = float(group["forecast_confidence_score"].mean())
        row["model_outputs_json"] = json.dumps(_aggregate_model_outputs(group))
        row["weather_summary"] = _daily_weather_summary(group)
        uncertainty = 0.14 + (1 - confidence) * 0.38
        rows.append(_forecast_payload(row, horizon, facility_profile, expected, uncertainty, revenue_per_visitor, None, target_date=target_date))
    return rows


def _forecast_payload(
    row: pd.Series,
    horizon: str,
    facility_profile: str,
    expected: float,
    uncertainty: float,
    revenue_per_visitor: float,
    hour: int | None,
    target_date: date | None = None,
) -> dict[str, Any]:
    target_date = target_date or row["date"]
    if isinstance(target_date, pd.Timestamp):
        target_date = target_date.date()
    return {
        "horizon": horizon,
        "facility_profile": facility_profile,
        "target_date": target_date,
        "hour": hour,
        "expected_visitors": round(expected, 2),
        "low_scenario": round(max(0, expected * (1 - uncertainty)), 2),
        "high_scenario": round(expected * (1 + uncertainty), 2),
        "expected_revenue": round(expected * revenue_per_visitor, 2),
        "model_name": "ensemble_available_models",
        "model_outputs_json": str(row.get("model_outputs_json", "{}")),
        "confidence_score": round(float(row["confidence_score"]), 4),
        "provider_disagreement_score": round(float(row["provider_disagreement_score"]), 4),
        "forecast_confidence_score": round(float(row["forecast_confidence_score"]), 4),
        "weather_summary": row.get("weather_summary") or _hourly_weather_summary(row),
        "is_demo": bool(row.get("is_demo", False)),
    }


def _similar_day_predictions(train: pd.DataFrame, target: pd.DataFrame) -> np.ndarray:
    predictions = []
    fallback = float(train["visitors"].mean()) if not train.empty else 25.0
    for _, row in target.iterrows():
        # This baseline is intentionally explainable: find past days that look like the future day.
        candidates = train[
            (train["day_of_week"] == row["day_of_week"])
            & (train["month"].sub(row["month"]).abs() <= 1)
            & (train["is_public_holiday"] == row["is_public_holiday"])
        ]
        if "event_active" in candidates and row.get("event_active") is not None:
            candidates = candidates[candidates["event_active"] == row["event_active"]]
        weather_candidates = candidates[candidates["weather_score"].sub(row["weather_score"]).abs() <= 18]
        if len(weather_candidates) >= 5:
            value = weather_candidates["visitors"].mean()
        elif len(candidates) >= 3:
            value = candidates["visitors"].mean()
        else:
            value = fallback
        campaign_boost = 1 + min(float(row.get("campaign_budget", 0)) / 50000, 0.10)
        event_boost = 1 + float(row.get("event_expected_impact", 0) or 0)
        predictions.append(float(value) * campaign_boost * event_boost)
    return np.asarray(predictions)


def _metrics(model_name: str, actual: np.ndarray, predicted: np.ndarray, facility_profile: str) -> dict[str, Any]:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mae = float(mean_absolute_error(actual, predicted)) if SKLEARN_AVAILABLE else float(np.mean(np.abs(actual - predicted)))
    rmse = float(mean_squared_error(actual, predicted) ** 0.5) if SKLEARN_AVAILABLE else float(np.sqrt(np.mean((actual - predicted) ** 2)))
    safe_actual = np.where(actual == 0, 1, actual)
    mape = float(np.mean(np.abs((actual - predicted) / safe_actual)) * 100)
    return {
        "model_name": model_name,
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "notes": f"Holdout evaluation for {facility_profile} profile using latest feature build.",
    }


def _skipped_metric(model_name: str, notes: str) -> dict[str, Any]:
    return {
        "model_name": model_name,
        "mae": 0.0,
        "rmse": 0.0,
        "mape": 0.0,
        "notes": notes,
    }


def _store_evaluation(db: Session, evaluation: list[dict[str, Any]], facility_profile: str, is_demo: bool) -> None:
    db.query(ModelEvaluationRecord).filter(ModelEvaluationRecord.facility_profile == facility_profile).delete()
    rows = []
    for item in evaluation:
        rows.append(
            ModelEvaluationRecord(
                model_name=item["model_name"],
                facility_profile=facility_profile,
                mae=float(item["mae"]),
                rmse=float(item["rmse"]),
                mape=float(item["mape"]),
                rank=int(item.get("rank", 99)),
                notes=item.get("notes"),
                is_demo=is_demo,
            )
        )
    db.add_all(rows)
    db.commit()


def _aggregate_model_outputs(group: pd.DataFrame) -> dict[str, float]:
    output: dict[str, float] = {}
    for _, row in group.iterrows():
        values = json.loads(row["model_outputs_json"])
        for key, value in values.items():
            output[key] = output.get(key, 0.0) + float(value)
    return {key: round(value, 2) for key, value in output.items()}


def _hourly_weather_summary(row: pd.Series) -> str:
    return (
        f"{round(float(row['temperature']), 1)} C, precipitation {round(float(row['precipitation']), 1)} mm, "
        f"cloud cover {round(float(row['cloud_cover']), 0)}%, confidence {round(float(row['forecast_confidence_score']), 2)}, "
        f"{_weather_source_label(row)}"
    )


def _daily_weather_summary(group: pd.DataFrame) -> str:
    return (
        f"avg {round(float(group['temperature'].mean()), 1)} C, precipitation {round(float(group['precipitation'].sum()), 1)} mm, "
        f"cloud cover {round(float(group['cloud_cover'].mean()), 0)}%, {_weather_source_label(group.iloc[0])}"
    )


def _model_agreement(values: list[float]) -> float:
    cleaned = [float(value) for value in values if value is not None]
    if len(cleaned) < 2:
        return 0.72
    mean_value = max(float(np.mean(cleaned)), 1.0)
    spread = float(np.std(cleaned))
    return max(0.25, min(0.98, 1 - spread / mean_value))


def _revenue_per_visitor(db: Session) -> float:
    rows = db.query(AttendanceRecord).all()
    if not rows:
        return 58.0
    revenue = sum(row.revenue_tickets + row.revenue_gastro + row.revenue_parking for row in rows)
    visitors = sum(row.visitors for row in rows)
    return float(revenue / max(visitors, 1))


def _serialize_forecast_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    serialized = []
    for row in rows:
        item = row.copy()
        if hasattr(item["target_date"], "isoformat"):
            item["target_date"] = item["target_date"].isoformat()
        serialized.append(item)
    return serialized


def _available_model_status() -> dict[str, bool]:
    return {
        "similar_day_baseline": True,
        "random_forest": SKLEARN_AVAILABLE,
        "gradient_boosting": SKLEARN_AVAILABLE,
        "optional_xgboost": XGBOOST_AVAILABLE,
        "optional_prophet": PROPHET_AVAILABLE,
    }


def _weather_data_mode(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "unknown"
    placeholder_like = (
        frame["forecast_confidence_score"].fillna(0).mean() <= 0.46
        and frame["provider_disagreement_score"].fillna(0).mean() >= 0.54
    )
    return "seasonal_placeholder_weather" if placeholder_like else "real_weather_consensus_or_mixed"


def _weather_source_label(row: pd.Series) -> str:
    if float(row.get("forecast_confidence_score", 0) or 0) <= 0.46 and float(row.get("provider_disagreement_score", 0) or 0) >= 0.54:
        return "seasonal placeholder weather"
    return "weather consensus"
