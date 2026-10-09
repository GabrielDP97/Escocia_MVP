from __future__ import annotations

from functools import lru_cache
from time import perf_counter
from typing import Any
import math

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score


def _safe_probability(values: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), 1e-12, 1 - 1e-12)


def _lift(y: np.ndarray, score: np.ndarray, fraction: float) -> float | None:
    base = float(np.mean(y))
    if base <= 0:
        return None
    n = max(1, int(math.ceil(len(score) * fraction)))
    idx = np.argsort(-score)[:n]
    return float(np.mean(y[idx]) / base)


def score_metrics(y: np.ndarray, score: np.ndarray) -> dict[str, float | None]:
    score = _safe_probability(score)
    return {
        "roc_auc": float(roc_auc_score(y, score)),
        "pr_auc": float(average_precision_score(y, score)),
        "brier": float(brier_score_loss(y, score)),
        "log_loss": float(log_loss(y, score)),
        "lift_top_1pct": _lift(y, score, 0.01),
        "lift_top_5pct": _lift(y, score, 0.05),
        "lift_top_10pct": _lift(y, score, 0.10),
    }


def _common_frame(store: Any) -> pd.DataFrame:
    base = store.pred[["cell", "year", "month", "target_presence", "dvc_count", "p_level1", "p_level2", "p_final"]].copy()
    lstm = store.r9[["cell", "target_year", "target_month", "target_presence", "dvc_count_target", "p_lstm_calibrated"]].rename(
        columns={"target_year": "year", "target_month": "month", "target_presence": "y_lstm", "dvc_count_target": "count_lstm"})
    keys = ["cell", "year", "month"]
    df = base.merge(lstm, on=keys, validate="one_to_one")
    if not (df.target_presence == df.y_lstm).all() or not (df.dvc_count == df.count_lstm).all():
        raise ValueError("Las etiquetas principal/LSTM no coinciden.")
    if not store.mlp.empty:
        mlp = store.mlp.rename(columns={"target_presence": "y_mlp", "dvc_count": "count_mlp"})
        df = df.merge(mlp, on=keys, validate="one_to_one")
        if not (df.target_presence == df.y_mlp).all() or not (df.dvc_count == df.count_mlp).all():
            raise ValueError("Las etiquetas principal/MLP no coinciden.")
        df["deep_mean"] = (df.p_mlp + df.p_lstm_calibrated) / 2
        df["ensemble_equal"] = (df.p_final + df.p_mlp + df.p_lstm_calibrated) / 3
        df["ensemble_balanced"] = .50 * df.p_final + .25 * df.p_mlp + .25 * df.p_lstm_calibrated
    return df


def _delta(candidate: dict[str, float | None], baseline: dict[str, float | None]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for key in baseline:
        if baseline[key] is None or candidate[key] is None:
            out[key] = None
        else:
            out[key] = float(candidate[key] - baseline[key])
    return out


def _cluster_bootstrap(
    df: pd.DataFrame,
    baseline_col: str,
    candidate_col: str,
    samples: int = 400,
    seed: int = 42,
) -> dict[str, Any]:
    cells = df["cell"].unique()
    cell_values = df["cell"].to_numpy()
    groups = {cell: np.flatnonzero(cell_values == cell) for cell in cells}
    y_all = df["target_presence"].to_numpy(dtype=int)
    base_all = df[baseline_col].to_numpy(dtype=float)
    cand_all = df[candidate_col].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    deltas: list[list[float]] = []

    for _ in range(samples):
        sampled_cells = rng.choice(cells, size=len(cells), replace=True)
        idx = np.concatenate([groups[cell] for cell in sampled_cells])
        y = y_all[idx]
        if y.min() == y.max():
            continue
        base = base_all[idx]
        cand = cand_all[idx]
        deltas.append([
            average_precision_score(y, cand) - average_precision_score(y, base),
            roc_auc_score(y, cand) - roc_auc_score(y, base),
            brier_score_loss(y, cand) - brier_score_loss(y, base),
        ])

    arr = np.asarray(deltas, dtype=float)
    names = ["pr_auc", "roc_auc", "brier"]
    result: dict[str, Any] = {"samples_requested": samples, "samples_used": int(len(arr)), "cluster": "cell", "seed": seed, "metrics": {}}
    for i, name in enumerate(names):
        vals = arr[:, i]
        result["metrics"][name] = {
            "mean_delta": float(np.mean(vals)),
            "ci95_low": float(np.quantile(vals, 0.025)),
            "ci95_high": float(np.quantile(vals, 0.975)),
        }
    return result


def _threshold_sweep(y: np.ndarray, score: np.ndarray) -> list[dict[str, float | int]]:
    out: list[dict[str, float | int]] = []
    for threshold in np.arange(0.05, 0.51, 0.05):
        pred = score >= threshold
        tp = int(np.sum((pred == 1) & (y == 1)))
        fp = int(np.sum((pred == 1) & (y == 0)))
        fn = int(np.sum((pred == 0) & (y == 1)))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        out.append({
            "threshold": float(round(threshold, 2)),
            "alerts": int(pred.sum()),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
        })
    return out


def _runtime_microbenchmark(df: pd.DataFrame, iterations: int = 300) -> dict[str, float | int | str]:
    p = df["p_final"].to_numpy(dtype=float)
    d = df["p_mlp"].to_numpy(dtype=float)
    l = df["p_lstm_calibrated"].to_numpy(dtype=float)
    timings = []
    for _ in range(iterations):
        start = perf_counter()
        _ = 0.50 * p + 0.25 * d + 0.25 * l
        timings.append((perf_counter() - start) * 1000.0)
    return {
        "operation": "vectorized score fusion only; NOT end-to-end model inference",
        "rows": int(len(df)),
        "iterations": iterations,
        "median_ms": float(np.median(timings)),
        "p95_ms": float(np.quantile(timings, 0.95)),
        "per_row_median_us": float(np.median(timings) * 1000.0 / len(df)),
    }


def build_technology_benchmark(store: Any, bootstrap_samples: int = 400) -> dict[str, Any]:
    df = _common_frame(store)
    y = df["target_presence"].to_numpy(dtype=int)
    available = "p_mlp" in df
    variants = {
        "level1_no_seasonal": ("Nivel 1 sin modulador estacional", "p_level1"),
        "current_final": ("Principal · Reto 05 + ajuste estacional", "p_final"),
        "lstm": ("Reto 09 · LSTM calibrada", "p_lstm_calibrated"),
    }
    if available:
        variants.update({
            "mlp": ("Capítulo 8 · MLP de presencia", "p_mlp"),
            "ensemble_equal": ("Ensemble exploratorio 1/3 + 1/3 + 1/3", "ensemble_equal"),
            "ensemble_balanced": ("Ensemble exploratorio 50% + 25% + 25%", "ensemble_balanced"),
        })
    metrics = {key: {"label": label, "metrics": score_metrics(y, df[col].to_numpy(dtype=float))}
               for key, (label, col) in variants.items()}
    baseline = metrics["current_final"]["metrics"]
    for value in metrics.values():
        value["delta_vs_current"] = _delta(value["metrics"], baseline)
    sweep = []
    if available:
        for alpha in np.linspace(0, 1, 11):
            score = alpha * df.p_final + (1-alpha) * df.deep_mean
            sweep.append({"current_weight": float(round(alpha, 1)), "deep_mean_weight": float(round(1-alpha, 1)), **score_metrics(y, score)})
    bootstrap = {"seasonal_layer_vs_level1": _cluster_bootstrap(df, "p_level1", "p_final", samples=bootstrap_samples, seed=43)}
    if available:
        bootstrap["ensemble_balanced_vs_current"] = _cluster_bootstrap(df, "p_final", "ensemble_balanced", samples=bootstrap_samples, seed=42)
    return {
        "scope": {"evaluation_year": 2017, "rows_common": len(df), "cells": int(df.cell.nunique()),
                  "prevalence": float(y.mean()), "mlp_predictions_available": available,
                  "warning": "Diagnóstico sobre test histórico. Los ensembles y barridos son exploratorios y requieren validación temporal independiente."},
        "models": metrics,
        "parameter_sweeps": {"ensemble_weight": sweep, "threshold_current": _threshold_sweep(y, df.p_final.to_numpy()),
                             "threshold_ensemble_balanced": _threshold_sweep(y, df.ensemble_balanced.to_numpy()) if available else []},
        "bootstrap": bootstrap,
        "runtime": _runtime_microbenchmark(df) if available else None,
        "interpretation": {
            "seasonal_layer": "Las diferencias de AP, ROC-AUC y Brier se recalculan desde las predicciones guardadas.",
            "mlp_lstm_alone": "La MLP se muestra con los resultados de los notebooks ejecutados. La tabla de muestra común identifica cada entrenamiento.",
            "ensemble": "Los resultados se recalculan con las predicciones reales de MLP; el barrido sigue siendo exploratorio." if available else "Pendiente de las predicciones por celda de la MLP. Se han retirado los resultados de la DNN anterior.",
            "lift": "El Lift se calcula únicamente para modelos con predicciones disponibles.",
        },
    }


def technology_capabilities() -> list[dict[str, str]]:
    return [
        {"technology": "pandas / NumPy", "status": "aplicado", "evidence": "Carga, joins, ranking, histogramas y benchmark vectorizado sobre los artefactos 2017."},
        {"technology": "scikit-learn", "status": "aplicado", "evidence": "ROC-AUC, PR-AUC, Brier, log-loss, Lift y bootstrap comparativo agrupado por cell."},
        {"technology": "Calibración temporal Platt", "status": "aplicado-auditado", "evidence": "Se integra el protocolo temporal estricto de Reto 05: Platt con OOF temporal, selección en 2016 y test 2017 abierto una sola vez. El ZIP recalcula y verifica el test final; SimpleRNN/LSTM mantienen además su auditoría raw→calibrated."},
        {"technology": "OSM / triaje vial", "status": "aplicado-parcial", "evidence": "Contexto de carretera, iluminación, velocidad y bosque próximo mediante caché/tabla offline; no se usa para alterar el score histórico."},
        {"technology": "astral", "status": "integrado-operativo", "evidence": "Endpoint de contexto solar preparado para coordenadas + timestamp; no entra en métricas 2017 porque los artefactos no contienen hora exacta del evento."},
        {"technology": "GeoPandas / Shapely · red 1D 250 m", "status": "no-reproducible-con-este-zip", "evidence": "El ZIP aporta centros de celdas BNG de 10 km, no geometría vial segmentada de 250 m ni proyecciones de eventos."},
        {"technology": "Edge effect forestal <50 m", "status": "no-reproducible-con-este-zip", "evidence": "Existe un indicador contextual forest_within_200m, pero no distancias métricas a linde forestal por observación."},
        {"technology": "NLP / Text Mining · Reto 07", "status": "aplicado-auditado", "evidence": "Clasificación documental V3 con split por documento padre. MultinomialNB fue seleccionado en validation y alcanza Accuracy 0,920 y Macro-F1 0,922969 en test; el clustering documental selecciona K-Means k=6 con Silhouette 0,453931."},
        {"technology": "MLP de presencia", "status": "verificado-desde-notebook-ejecutado", "evidence": "Dense 64/32, Dropout 0,15 y L2 1e-5. Test 2017: ROC-AUC 0,8441, AP 0,6026, Brier 0,1055 y F1 0,5560; 6.336 observaciones. Sin Platt adicional."},
        {"technology": "LSTM + Platt · Reto 09", "status": "aplicado-auditado", "evidence": "Predicción espacio-temporal con ventana de 12 meses, selección en validation 2016 y test final 2017 sobre 6.348 secuencias. LSTM + Platt alcanza ROC-AUC 0,846497, PR-AUC 0,609213 y Brier 0,103847."},
        {"technology": "K-Means / clustering", "status": "aplicado-descriptivo", "evidence": "cluster del Reto 06 se conserva en la ruta y se usa como contexto; no se introduce post-hoc en el score para evitar leakage."},
        {"technology": "SHAP", "status": "pendiente-de-estimador", "evidence": "No se generan explicaciones falsas: hacen falta el modelo serializado y exactamente las features con las que fue entrenado."},
    ]
