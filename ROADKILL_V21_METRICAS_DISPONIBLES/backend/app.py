from __future__ import annotations

from pathlib import Path
from functools import lru_cache
import importlib.util
import math
from typing import Any, Annotated, Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pyproj import Transformer

from backend.technology_lab import build_technology_benchmark, technology_capabilities
from backend.calibration_lab import build_calibration_audit
from backend.strict_temporal_audit import build_strict_temporal_audit
from backend.solar_context import solar_context
from backend.reto7_nlp import get_reto7_nlp_metrics
from backend.reto8_mlp import get_reto8_mlp_metrics, load_mlp_predictions
from backend.reto9_lstm import get_reto9_lstm_metrics
from backend.model_presentation import model_names
from backend.model_catalog import get_model_catalog
from backend.trip_risk import estimate_trip_risk
from backend.route_daily_risk import estimate_route_daily_risk
from backend.route_traffic import load_route_traffic, select_route_traffic, TRAFFIC_FILE

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _load_osm_service():
    module_path = DATA_DIR / "osm_scotland.py"
    if not module_path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("roadkill_osm_scotland", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.OSMScotlandService(mode="offline", cache_dir=DATA_DIR / "osm_cache", verbose=False)
    except Exception:
        return None


class DataStore:
    def __init__(self):
        self.pred = pd.read_csv(DATA_DIR / "predicciones_test_2017.csv")
        self.coords = pd.read_csv(DATA_DIR / "cell_coordinates_reto06.csv")
        self.r9 = pd.read_csv(DATA_DIR / "predicciones_test_2017_reto9.csv")
        self.mlp = load_mlp_predictions()
        self.metrics = pd.read_csv(DATA_DIR / "clasificacion_test_2017.csv")
        self.month_rr_df = pd.read_csv(DATA_DIR / "modulador_mensual_final_2008_2016.csv")

        for df in (self.pred, self.coords, self.r9, self.mlp):
            df["cell"] = pd.to_numeric(df["cell"], errors="coerce")

        coords = self.coords[["cell", "easting_mean", "northing_mean", "cluster", "log_traffic_mean", "years_available"]].copy()
        demo = self.pred.merge(coords, on="cell", how="left")

        r9_cmp = self.r9[["cell", "target_month", "p_lstm_calibrated"]].rename(columns={"target_month": "month"})
        demo = demo.merge(r9_cmp, on=["cell", "month"], how="left")
        demo = demo.merge(self.mlp[["cell", "year", "month", "p_mlp"]], on=["cell", "year", "month"], how="left")
        demo["risk_percentile"] = demo["p_final"].rank(method="average", pct=True) * 100.0

        transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
        valid = demo["easting_mean"].notna() & demo["northing_mean"].notna()
        demo["lat"] = np.nan
        demo["lon"] = np.nan
        if valid.any():
            xs = demo.loc[valid, "easting_mean"].astype(float).to_numpy()
            ys = demo.loc[valid, "northing_mean"].astype(float).to_numpy()
            lon, lat = transformer.transform(xs, ys)
            demo.loc[valid, "lat"] = lat
            demo.loc[valid, "lon"] = lon
        traffic = load_route_traffic(BASE_DIR).rename(columns={"daily_vehicle_mean": "aadf_daily_vehicle_mean"})
        self.aadf_available = (BASE_DIR / "data" / TRAFFIC_FILE).is_file()
        traffic["road_name"] = traffic["road_name"].astype(str).str.strip().str.upper()
        demo = demo.merge(traffic, on=["cell", "year", "road_name"], how="left", validate="many_to_one")
        demo.loc[demo["traffic_status"].ne("valid"), "aadf_daily_vehicle_mean"] = np.nan
        self.demo = demo

        self.month_rr = dict(zip(self.month_rr_df["month"].astype(int), self.month_rr_df["relative_risk"].astype(float)))
        self.threshold = float(self.pred["selected_threshold"].dropna().iloc[0])
        self.base_rate = float(self.pred["target_presence"].mean())
        final = self.metrics[self.metrics["model"].astype(str).str.contains("Sistema_final", na=False)]
        if final.empty:
            final = self.metrics.tail(1)
        self.final_metrics = final.iloc[0].to_dict()
        self.osm = _load_osm_service()

    def road_context(self, road_name: str) -> dict[str, Any]:
        if self.osm is None:
            return {
                "triage": {"triage_level": "No disponible", "dominant_species": "No disponible", "severity_risk": "No disponible"},
                "osm": {"highway": "unknown", "maxspeed_mph": 60, "is_lit": False, "lanes": None, "forest_within_200m": False, "source": "fallback"},
            }
        try:
            triage = self.osm.get_road_triage(road_name)
        except Exception:
            triage = {}
        try:
            attrs = self.osm.get_road_attributes(road_name)
        except Exception:
            attrs = {}
        return {"triage": triage, "osm": attrs}


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    return DataStore()


app = FastAPI(title="Roadkill Risk Engine API", description="Backend del MVP web para aseguradoras.", version="1.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def safe_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def safe_int(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
        return int(value)
    except Exception:
        return None


def risk_band(percentile: float) -> str:
    if percentile >= 95:
        return "MUY ALTO"
    if percentile >= 80:
        return "ALTO"
    if percentile >= 50:
        return "MODERADO"
    return "BAJO"


def empirical_threshold_percentile(store: DataStore, threshold: float) -> float:
    """Map a probability cut to the same empirical 0-100 scale as risk_percentile.

    risk_percentile is a rank of p_final across the 2017 test.  The gauge can
    therefore show an approximate marker for a probability threshold without
    pretending that probability and percentile are the same unit.
    """
    scores = store.demo["p_final"].dropna().astype(float).to_numpy()
    if len(scores) == 0:
        return 0.0
    return float(np.mean(scores <= float(threshold)) * 100.0)


def threshold_score_map(store: DataStore) -> list[dict[str, object]]:
    """Return probability cuts mapped to the empirical Risk Response Score scale.

    Besides the selected alert cut, each row exposes the three boundaries used
    by the frontend visual state machine:
      normal -> watch     at threshold - 0.05
      watch  -> alert     at threshold
      alert  -> critical  at threshold + 0.10

    Mapping all of them to the same 0-100 empirical percentile scale keeps the
    coloured gauge zones aligned with the needle and with the probability-based
    alert logic.
    """
    presets = [0.10, 0.15, 0.20, float(store.threshold), 0.30, 0.40, 0.50]
    values = sorted({round(float(value), 12) for value in presets})
    rows: list[dict[str, object]] = []

    for value in values:
        cut = float(value)
        watch_start = max(0.0, cut - 0.05)
        critical_start = min(1.0, cut + 0.10)
        watch_score = empirical_threshold_percentile(store, watch_start)
        alert_score = empirical_threshold_percentile(store, cut)
        critical_score = empirical_threshold_percentile(store, critical_start)

        rows.append({
            "threshold": cut,
            "risk_percentile": alert_score,
            "is_official": bool(abs(cut - float(store.threshold)) < 1e-10),
            "probability_boundaries": {
                "normal_to_watch": watch_start,
                "watch_to_alert": cut,
                "alert_to_critical": critical_start,
            },
            "gauge_boundaries": {
                "normal_to_watch": watch_score,
                "watch_to_alert": alert_score,
                "alert_to_critical": critical_score,
            },
        })

    return rows


def route_profile(store: DataStore, road_name: str, month: int, reverse: bool) -> pd.DataFrame:
    d = store.demo[
        store.demo["road_name"].astype(str).str.upper().eq(str(road_name).upper())
        & store.demo["month"].eq(int(month))
    ].dropna(subset=["easting_mean", "northing_mean", "lat", "lon"]).copy()
    if d.empty:
        return d
    xy = d[["easting_mean", "northing_mean"]].to_numpy(float)
    centered = xy - xy.mean(axis=0)
    if len(d) > 1:
        _, _, vt = np.linalg.svd(centered, full_matrices=False)
        d["route_axis"] = centered @ vt[0]
    else:
        d["route_axis"] = 0.0
    d = d.sort_values("route_axis", ascending=not reverse).reset_index(drop=True)
    d["route_step"] = np.arange(len(d))
    return d


@app.get("/api/health")
def health():
    store = get_store()
    return {"status": "ok", "test_year": 2017, "rows": len(store.pred), "roads": int(store.pred["road_name"].nunique()), "cells": int(store.pred["cell"].nunique())}


@app.get("/api/metadata")
def metadata():
    store = get_store()
    n_top1 = max(1, int(math.ceil(len(store.pred) * 0.01)))
    top1 = store.pred.nlargest(n_top1, "p_final")
    top1_rate = float(top1["target_presence"].mean())
    lift_calculated = top1_rate / store.base_rate if store.base_rate else None
    return {
        "project": "Roadkill Risk Engine",
        "mode": "Historical MVP / Insurance Demo",
        "test_year": 2017,
        "primary_model": "Random Forest + Platt + ajuste estacional",
        "temporal_comparator": "LSTM + Platt",
        "deep_comparator": "MLP de presencia",
        "threshold": store.threshold,
        "base_rate": store.base_rate,
        "metrics": {
            "pr_auc": safe_float(store.final_metrics.get("pr_auc")),
            "roc_auc": safe_float(store.final_metrics.get("roc_auc")),
            "brier": safe_float(store.final_metrics.get("brier")),
            "lift_top_1pct_reported": safe_float(store.final_metrics.get("lift_top_1pct")),
            "lift_top_10pct_reported": safe_float(store.final_metrics.get("lift_top_10pct")),
            "lift_top_1pct_calculated": lift_calculated,
            "top1_positive_rate": top1_rate,
        },
        "disclaimer": "El MVP utiliza predicciones históricas de 2017. No es un sistema de tarificación ni una recomendación legal de conducción.",
    }


@app.get("/api/roads")
def roads(min_cells: int = Query(default=4, ge=1, le=100)):
    store = get_store()
    d = store.demo.dropna(subset=["lat", "lon"]).groupby("road_name").agg(cells=("cell", "nunique"), observations=("p_final", "size"), mean_risk=("p_final", "mean"), max_risk=("p_final", "max")).reset_index()
    d = d[d["cells"] >= min_cells].sort_values(["cells", "mean_risk"], ascending=[False, False])
    preferred = ["A82", "A90", "A9", "A85", "A1", "M74", "A92"]
    rank = {name: i for i, name in enumerate(preferred)}
    records = d.to_dict("records")
    records.sort(key=lambda x: (rank.get(str(x["road_name"]), 999), -int(x["cells"])))
    return {"roads": records}


@app.get("/api/route")
def route(road_name: str, month: int = Query(default=5, ge=1, le=12), reverse: bool = False,
          travel_date: str | None = None, distance_km: Annotated[float | None, Query(gt=0, le=10000)] = None,
          daily_route_vehicles: Annotated[float | None, Query(gt=0, le=100000000)] = None,
          traffic_mode: Literal["auto", "aadf_2017", "historical_profile"] = "auto"):
    store = get_store()
    d = route_profile(store, road_name, month, reverse)
    d, traffic_basis = select_route_traffic(d, traffic_mode, store.aadf_available)
    if d.empty:
        raise HTTPException(status_code=404, detail=f"No hay ruta demo disponible para {road_name} en mes {month}.")
    context = store.road_context(road_name)
    rr = float(store.month_rr.get(int(month), 1.0))
    points = []
    for _, row in d.iterrows():
        p1 = safe_float(row.get("p_level1"))
        p2 = safe_float(row.get("p_level2"))
        delta = (p2 - p1) if p1 is not None and p2 is not None else None
        p_lstm = safe_float(row.get("p_lstm_calibrated"))
        p_mlp = safe_float(row.get("p_mlp"))
        p_final = safe_float(row["p_final"])
        p_ensemble = (0.50 * p_final + 0.25 * p_lstm + 0.25 * p_mlp) if None not in (p_final, p_lstm, p_mlp) else None
        points.append({
            "step": safe_int(row["route_step"]), "cell": safe_int(row["cell"]), "road_name": str(row["road_name"]),
            "local_authority_name": str(row["local_authority_name"]), "road_category": str(row["road_category"]),
            "lat": safe_float(row["lat"]), "lon": safe_float(row["lon"]), "easting": safe_float(row["easting_mean"]),
            "northing": safe_float(row["northing_mean"]), "cluster": safe_int(row.get("cluster")),
            "p_level1": p1, "p_level2": p2, "p_final": p_final, "p_ensemble_exploratory": p_ensemble,
            "risk_percentile": safe_float(row["risk_percentile"]), "risk_band": risk_band(float(row["risk_percentile"])),
            "alert_active": bool(float(row["p_final"]) >= store.threshold), "pred_count_final": safe_float(row.get("pred_count_final")),
            "p_lstm": p_lstm, "p_mlp": p_mlp,
            "target_presence": safe_int(row.get("target_presence")), "dvc_count": safe_int(row.get("dvc_count")),
            "exposure_vkm_proxy": safe_float(row.get("exposure_vkm_proxy")), "seasonal_delta": delta,
            "daily_vehicle_mean": safe_float(row.get("daily_vehicle_mean")),
            "aadf_count_points": safe_int(row.get("aadf_count_points")),
        })
    try:
        trip_risk = estimate_trip_risk(points, month, travel_date, distance_km)
        daily_risk = estimate_route_daily_risk(points, month, travel_date, daily_route_vehicles, distance_km, traffic_basis)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "road_name": road_name.upper(), "month": month, "month_name": MONTH_NAMES[month], "reverse": reverse,
        "threshold": store.threshold,
        "threshold_score_map": threshold_score_map(store),
        "relative_risk_month": rr, "context": context, "points": points,
        "trip_risk": trip_risk, "daily_route_risk": daily_risk, "traffic_mode": traffic_mode,
        "aadf_2017_available": store.aadf_available,
        "route_note": "La polilínea une centros de celdas BNG asociados a la carretera. No representa la geometría exacta del asfalto.",
    }


@app.get("/api/dashboard")
def dashboard(min_observations: int = Query(default=24, ge=12, le=240)):
    store = get_store()
    roads_df = store.pred.groupby("road_name").agg(observations=("p_final", "size"), cells=("cell", "nunique"), mean_risk=("p_final", "mean"), max_risk=("p_final", "max"), observed_positive_rate=("target_presence", "mean"), dvc_total=("dvc_count", "sum")).reset_index()
    top_roads = roads_df[roads_df["observations"] >= min_observations].sort_values(["mean_risk", "max_risk"], ascending=False).head(15).to_dict("records")
    monthly = store.pred.groupby("month").agg(predicted_risk=("p_final", "mean"), observed_rate=("target_presence", "mean"), dvc=("dvc_count", "sum"), observations=("p_final", "size")).reset_index()
    monthly["month_name"] = monthly["month"].map(MONTH_NAMES)
    counts, edges = np.histogram(store.pred["p_final"].astype(float), bins=24, range=(0, 1))
    histogram = [{"bin_start": float(edges[i]), "bin_end": float(edges[i+1]), "bin_mid": float((edges[i]+edges[i+1])/2), "count": int(counts[i])} for i in range(len(counts))]
    return {
        "summary": {"observations": len(store.pred), "cells": int(store.pred["cell"].nunique()), "roads": int(store.pred["road_name"].nunique()), "base_rate": store.base_rate, "dvc_total": int(store.pred["dvc_count"].sum()), "alerts_at_threshold": int((store.pred["p_final"] >= store.threshold).sum()), "threshold": store.threshold},
        "top_roads": top_roads, "monthly": monthly.to_dict("records"), "histogram": histogram,
    }


@app.get("/api/cases")
def cases():
    store = get_store()
    d = store.demo.dropna(subset=["lat", "lon"]).copy()
    targets = {"BAJO": 25.0, "MODERADO": 65.0, "ALTO": 88.0, "MUY ALTO": 98.0}
    out = []
    for band, target in targets.items():
        candidates = d[d["risk_percentile"].map(risk_band).eq(band)]
        if candidates.empty:
            continue
        idx = (candidates["risk_percentile"] - target).abs().idxmin()
        row = candidates.loc[idx]
        out.append({"band": band, "road_name": str(row["road_name"]), "cell": safe_int(row["cell"]), "month": safe_int(row["month"]), "month_name": MONTH_NAMES[int(row["month"])], "p_final": safe_float(row["p_final"]), "risk_percentile": safe_float(row["risk_percentile"]), "target_presence": safe_int(row["target_presence"]), "dvc_count": safe_int(row["dvc_count"])})
    return {"cases": out}


@app.get("/api/technology/capabilities")
def technology_status():
    return model_names({"capabilities": technology_capabilities()})


@lru_cache(maxsize=8)
def _cached_technology_benchmark(bootstrap_samples: int):
    return build_technology_benchmark(get_store(), bootstrap_samples=bootstrap_samples)


@app.get("/api/technology/benchmark")
def technology_benchmark(bootstrap_samples: int = Query(default=250, ge=30, le=1000)):
    return model_names(_cached_technology_benchmark(int(bootstrap_samples)))


@lru_cache(maxsize=8)
def _cached_calibration_audit(bootstrap_samples: int):
    return build_calibration_audit(get_store(), bootstrap_samples=bootstrap_samples)


@app.get("/api/technology/calibration-audit")
def technology_calibration_audit(bootstrap_samples: int = Query(default=250, ge=30, le=1000)):
    return model_names(_cached_calibration_audit(int(bootstrap_samples)))


@lru_cache(maxsize=1)
def _cached_strict_temporal_audit():
    return build_strict_temporal_audit(get_store())


@app.get("/api/technology/strict-temporal-audit")
def technology_strict_temporal_audit():
    return model_names(_cached_strict_temporal_audit())



@app.get("/api/technology/nlp")
@app.get("/api/technology/reto7-nlp", include_in_schema=False)
def technology_reto7_nlp():
    return model_names(get_reto7_nlp_metrics())


@app.get("/api/evidence/{name}")
def evidence(name: str):
    files = {
        "global": ("Roadkill_Evaluacion_Global_Frontend.ipynb", "Roadkill_Evaluacion_Global_Frontend.ipynb"),
        "random-forest": ("Reto5_Trazabilidad_Completa_Frontend_2017_REGENERADO(3).ipynb", "evaluacion_random_forest_y_baselines.ipynb"),
        "mlp-lstm": ("RetoRoadkill_cap08_U1_U2_U3(3).ipynb", "evaluacion_mlp_lstm_y_baselines.ipynb"),
        "capitulo8": ("RetoRoadkill_cap08_U1_U2_U3(3).ipynb", "evaluacion_mlp_lstm_y_baselines.ipynb"),
        "comparacion": ("Roadkill_Comparacion_Frontend_MLP_LSTM(1).ipynb", "comparacion_random_forest_mlp_lstm.ipynb"),
    }
    if name not in files:
        raise HTTPException(status_code=404, detail="Prueba no encontrada")
    source, download_name = files[name]
    return FileResponse(BASE_DIR / "evidencias" / source, filename=download_name, media_type="application/x-ipynb+json")



@app.get("/api/technology/mlp")
@app.get("/api/technology/reto8-mlp", include_in_schema=False)
def technology_reto8_mlp():
    return model_names(get_reto8_mlp_metrics())


@app.get("/api/technology/lstm")
@app.get("/api/technology/reto9-lstm", include_in_schema=False)
def technology_reto9_lstm():
    return model_names(get_reto9_lstm_metrics())


@app.get("/api/technology/model-comparison")
def technology_model_comparison():
    return model_names(get_model_catalog())


@app.get("/api/technology/solar-context")
def technology_solar_context(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    timestamp: str = Query(..., description="ISO-8601, por ejemplo 2017-05-15T20:00:00+01:00"),
    timezone: str = Query(default="Europe/London"),
):
    try:
        return solar_context(lat, lon, timestamp, timezone)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo calcular el contexto solar: {exc}") from exc


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
