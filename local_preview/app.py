import os
from typing import Any

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st


DEFAULT_API_BASE = os.getenv("AIRLINES_API_BASE", "http://127.0.0.1:8000")


st.set_page_config(page_title="Welcome to AIrlines", page_icon="WA", layout="wide")


def api_get(path: str, **params: Any) -> dict[str, Any]:
    base_url = st.session_state.get("api_base", DEFAULT_API_BASE).rstrip("/")
    with httpx.Client(timeout=60) as client:
        response = client.get(f"{base_url}{path}", params={key: value for key, value in params.items() if value is not None})
        response.raise_for_status()
        return response.json()


def api_post(path: str, **params: Any) -> dict[str, Any]:
    base_url = st.session_state.get("api_base", DEFAULT_API_BASE).rstrip("/")
    with httpx.Client(timeout=60) as client:
        response = client.post(f"{base_url}{path}", data=params)
        response.raise_for_status()
        return response.json()


def show_json(label: str, payload: dict[str, Any]) -> None:
    with st.expander(label, expanded=False):
        st.json(payload)


def items_frame(payload: dict[str, Any], key: str = "items") -> pd.DataFrame:
    items = payload.get(key, [])
    return pd.DataFrame(items) if items else pd.DataFrame()


def flatten_provider_comparison(payload: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in payload.get("comparison", {}).get("items", []):
        for provider, values in item.get("providers", {}).items():
            rows.append({"target_datetime": item["target_datetime"], "provider": provider, **values})
    return pd.DataFrame(rows)


st.title("Welcome to AIrlines")
st.caption("Backend-first attendance forecasting MVP for weather-dependent recreation and entertainment operations.")

with st.sidebar:
    st.header("Controls")
    st.session_state["api_base"] = st.text_input("Backend URL", DEFAULT_API_BASE)
    facility_profile = st.selectbox("Facility profile", ["mixed", "outdoor", "indoor"], index=0)
    horizon = st.selectbox("Planning horizon", ["operational", "tactical", "strategic"], index=0)
    st.divider()
    st.write("Run the backend first:")
    st.code("run_backend_windows.bat", language="text")


health_col, data_col, source_col = st.columns(3)
try:
    health = api_get("/health")
    with health_col:
        st.metric("Backend", health["status"])
        st.caption(health["default_location"]["city"])
    with data_col:
        business = health["business_data"]
        st.metric("Attendance rows", business["attendance_records"])
        st.caption(f"Business data: {business.get('data_mode', 'unknown')}")
    with source_col:
        sources = api_get("/sources")
        st.metric("Weather sources", len(sources["weather_sources"]))
        st.caption("Open-Meteo, MET Norway, IMGW, Nager.Date")
except Exception as exc:  # noqa: BLE001
    st.error(f"Backend is not reachable at {st.session_state['api_base']}. Start run_backend_windows.bat first.")
    st.exception(exc)
    st.stop()


st.subheader("Pipeline Actions")
action_cols = st.columns(7)
if action_cols[0].button("Run demo pipeline", use_container_width=True):
    with st.spinner("Fetching weather, calculating consensus, building features and forecast..."):
        st.session_state["consensus"] = api_get("/weather/consensus", fetch_first=True)
        st.session_state["features"] = api_get("/features/build", facility_profile=facility_profile)
        st.session_state[f"forecast_{horizon}_{facility_profile}"] = api_get(f"/forecast/{horizon}", facility_profile=facility_profile)
        st.session_state["pipeline_done"] = True
if action_cols[1].button("Fetch Open-Meteo", use_container_width=True):
    st.session_state["open_meteo"] = api_get("/weather/forecast/open-meteo", days=7)
if action_cols[2].button("Fetch MET Norway", use_container_width=True):
    st.session_state["met_no"] = api_get("/weather/forecast/met-no")
if action_cols[3].button("Fetch IMGW", use_container_width=True):
    st.session_state["imgw"] = api_get("/weather/current/imgw")
if action_cols[4].button("Weather consensus", use_container_width=True):
    st.session_state["consensus"] = api_get("/weather/consensus")
if action_cols[5].button("Build features", use_container_width=True):
    st.session_state["features"] = api_get("/features/build", facility_profile=facility_profile)
if action_cols[6].button("Build forecast", use_container_width=True):
    st.session_state[f"forecast_{horizon}_{facility_profile}"] = api_get(f"/forecast/{horizon}", facility_profile=facility_profile)

for key, label in [
    ("open_meteo", "Open-Meteo result"),
    ("met_no", "MET Norway result"),
    ("imgw", "IMGW result"),
    ("features", "Feature build result"),
]:
    if key in st.session_state:
        show_json(label, st.session_state[key])

if st.session_state.get("pipeline_done"):
    st.success("Demo pipeline completed. Forecasts and recommendations below are ready to inspect.")


st.subheader("Weather Provider Comparison")
try:
    consensus_payload = st.session_state.get("consensus") or api_get("/weather/consensus")
    comparison_df = flatten_provider_comparison(consensus_payload)
    consensus_df = items_frame(consensus_payload)
    status_df = pd.DataFrame(api_get("/weather/providers/status").get("providers", []))
    weather_tabs = st.tabs(["Consensus", "Provider status", "Provider comparison"])
    with weather_tabs[0]:
        if consensus_df.empty:
            st.info("No weather consensus records yet. Fetch weather providers, then calculate consensus.")
        else:
            visible = consensus_df[[
                "target_datetime",
                "temperature",
                "precipitation",
                "cloud_cover",
                "humidity",
                "wind_speed",
                "provider_count",
                "provider_disagreement_score",
                "forecast_confidence_score",
            ]].head(96)
            st.dataframe(visible, use_container_width=True, hide_index=True)
            chart_df = visible.copy()
            chart_df["target_datetime"] = pd.to_datetime(chart_df["target_datetime"])
            st.plotly_chart(px.line(chart_df, x="target_datetime", y=["temperature", "precipitation"], title="Consensus weather signals"), use_container_width=True)
    with weather_tabs[1]:
        if not status_df.empty:
            display_cols = [
                "provider",
                "status",
                "is_available",
                "records_last_fetch",
                "last_successful_fetch",
                "missing_fields",
                "last_error",
                "configuration_hint",
            ]
            st.dataframe(status_df[[column for column in display_cols if column in status_df.columns]], use_container_width=True, hide_index=True)
        else:
            st.info("No provider status records yet.")
    with weather_tabs[2]:
        if comparison_df.empty:
            st.info("No provider comparison rows yet.")
        else:
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
except Exception as exc:  # noqa: BLE001
    st.warning(f"Weather comparison is not ready yet: {exc}")


st.subheader("Forecast")
forecast_key = f"forecast_{horizon}_{facility_profile}"
forecast_payload = st.session_state.get(forecast_key)
if forecast_payload is None:
    try:
        forecast_payload = api_get(f"/forecast/{horizon}", facility_profile=facility_profile)
    except Exception as exc:  # noqa: BLE001
        st.info(f"Build a forecast to see the table. Detail: {exc}")
        forecast_payload = None

if forecast_payload:
    forecast_df = items_frame(forecast_payload)
    st.caption(
        f"{'Demo output' if forecast_payload.get('demo_mode') else 'Output based on imported data'} | "
        f"Weather: {forecast_payload.get('weather_data_mode', 'unknown')}"
    )
    if not forecast_df.empty:
        metric_cols = st.columns(4)
        metric_cols[0].metric("Forecast rows", len(forecast_df))
        metric_cols[1].metric("Expected visitors", f"{forecast_df['expected_visitors'].sum():,.0f}")
        metric_cols[2].metric("Expected revenue PLN", f"{forecast_df['expected_revenue'].sum():,.0f}")
        metric_cols[3].metric("Avg confidence", f"{forecast_df['confidence_score'].mean():.2f}")
        st.dataframe(forecast_df, use_container_width=True, hide_index=True)
        chart_df = forecast_df.copy()
        chart_df["target"] = chart_df.apply(lambda row: f"{row['target_date']} {'' if pd.isna(row.get('hour')) else int(row['hour'])}", axis=1)
        st.plotly_chart(
            px.line(chart_df, x="target", y=["low_scenario", "expected_visitors", "high_scenario"], title="Low / base / high visitor scenarios"),
            use_container_width=True,
        )
    show_json("Model evaluation from latest forecast", {"items": forecast_payload.get("model_evaluation", [])})


st.subheader("Recommendations")
rec_tabs = st.tabs(["Management", "Operations", "Marketing", "Model evaluation"])
with rec_tabs[0]:
    try:
        management = api_get("/recommendations/management", horizon=horizon, facility_profile=facility_profile)
        st.write(management["executive_summary"])
        st.json(management)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Management recommendations are not ready: {exc}")
with rec_tabs[1]:
    try:
        operations = api_get("/recommendations/operations", horizon=horizon, facility_profile=facility_profile)
        st.write(operations["summary"])
        st.json(operations)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Operations recommendations are not ready: {exc}")
with rec_tabs[2]:
    try:
        marketing = api_get("/recommendations/marketing", horizon=horizon, facility_profile=facility_profile)
        st.write(marketing["summary"])
        st.json(marketing)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Marketing recommendations are not ready: {exc}")
with rec_tabs[3]:
    evaluation = api_get("/model/evaluation", facility_profile=facility_profile)
    st.dataframe(pd.DataFrame(evaluation.get("items", [])), use_container_width=True, hide_index=True)


st.subheader("Backend Venue Data Contracts")
try:
    venues_payload = api_get("/venues")
    venues_df = pd.DataFrame(venues_payload.get("venues", []))
    if venues_df.empty:
        st.info("No venue profiles are available.")
    else:
        venue_options = {row["name"]: row["slug"] for _, row in venues_df.iterrows()}
        selected_venue_name = st.selectbox("Venue data preview", list(venue_options.keys()))
        selected_venue_slug = venue_options[selected_venue_name]
        selected_month = st.text_input("Calendar month", "2025-05")
        selected_day = st.text_input("Day details date", "2025-05-01")
        venue_tabs = st.tabs(["Venues", "Benchmarks", "Assets", "Trends", "Calendar JSON", "Day JSON", "Data quality"])
        with venue_tabs[0]:
            st.dataframe(venues_df[["name", "slug", "type", "city", "weather_sensitivity_label", "data_quality_label"]], use_container_width=True, hide_index=True)
        with venue_tabs[1]:
            st.json(api_get(f"/venues/{selected_venue_slug}/benchmarks"))
        with venue_tabs[2]:
            st.json(api_get(f"/venues/{selected_venue_slug}/assets"))
        with venue_tabs[3]:
            st.json(api_get(f"/venues/{selected_venue_slug}/trend-signals", start_date="2025-05-01", end_date="2025-05-31"))
        with venue_tabs[4]:
            calendar_json = api_get(f"/venues/{selected_venue_slug}/calendar", month=selected_month)
            st.json(calendar_json)
        with venue_tabs[5]:
            st.json(api_get(f"/venues/{selected_venue_slug}/days/{selected_day}"))
        with venue_tabs[6]:
            st.json(api_get(f"/venues/{selected_venue_slug}/data-quality"))
except Exception as exc:  # noqa: BLE001
    st.warning(f"Venue data contract preview is not ready: {exc}")
