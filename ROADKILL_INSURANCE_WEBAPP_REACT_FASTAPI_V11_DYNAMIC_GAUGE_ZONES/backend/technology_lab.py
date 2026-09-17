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
    base = store.pred[["cell", "month", "target_presence", "p_level1", "p_level2", "p_final"]].copy()
    dnn = store.r8[["cell", "month", "p_dnn_calibrated"]].copy()
    lstm = store.r9[["cell", "target_month", "p_lstm_calibrated"]].rename(columns={"target_month": "month"})
    df = base.merge(dnn, on=["cell", "month"], how="inner").merge(lstm, on=["cell", "month"], how="inner")
    df["deep_mean"] = (df["p_dnn_calibrated"] + df["p_lstm_calibrated"]) / 2.0
    df["ensemble_equal"] = (df["p_final"] + df["p_dnn_calibrated"] + df["p_lstm_calibrated"]) / 3.0
    # Candidato exploratorio: el modelo principal conserva la mitad del peso y los dos
    # comparadores comparten la otra mitad. No se promueve a producción porque su peso
    # se inspecciona sobre test 2017 y necesitaría validarse en un periodo independiente.
    df["ensemble_balanced"] = 0.50 * df["p_final"] + 0.25 * df["p_dnn_calibrated"] + 0.25 * df["p_lstm_calibrated"]
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
    d = df["p_dnn_calibrated"].to_numpy(dtype=float)
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
    variants = {
        "level1_no_seasonal": ("Nivel 1 sin modulador estacional", "p_level1"),
        "current_final": ("Actual · Reto 05 + ajuste estacional", "p_final"),
        "dnn": ("Reto 08 · DNN calibrada", "p_dnn_calibrated"),
        "lstm": ("Reto 09 · LSTM calibrada", "p_lstm_calibrated"),
        "ensemble_equal": ("Ensemble igualitario 1/3 + 1/3 + 1/3", "ensemble_equal"),
        "ensemble_balanced": ("Ensemble exploratorio 50% + 25% + 25%", "ensemble_balanced"),
    }
    metrics: dict[str, Any] = {}
    for key, (label, col) in variants.items():
        metrics[key] = {"label": label, "metrics": score_metrics(y, df[col].to_numpy(dtype=float))}

    baseline = metrics["current_final"]["metrics"]
    for key in metrics:
        metrics[key]["delta_vs_current"] = _delta(metrics[key]["metrics"], baseline)

    # Sensibilidad del peso del modelo actual frente a la media DNN/LSTM.
    sweep = []
    for alpha in np.linspace(0.0, 1.0, 11):
        score = alpha * df["p_final"].to_numpy(dtype=float) + (1 - alpha) * df["deep_mean"].to_numpy(dtype=float)
        sweep.append({"current_weight": float(round(alpha, 1)), "deep_mean_weight": float(round(1 - alpha, 1)), **score_metrics(y, score)})

    seasonal_bootstrap = _cluster_bootstrap(df, "p_level1", "p_final", samples=bootstrap_samples, seed=43)
    ensemble_bootstrap = _cluster_bootstrap(df, "p_final", "ensemble_balanced", samples=bootstrap_samples, seed=42)

    return {
        "scope": {
            "evaluation_year": 2017,
            "rows_common": int(len(df)),
            "cells": int(df["cell"].nunique()),
            "prevalence": float(y.mean()),
            "warning": "Diagnóstico sobre test histórico. El barrido de pesos es exploratorio y no debe utilizarse para seleccionar un modelo final sin un conjunto temporal independiente.",
        },
        "models": metrics,
        "parameter_sweeps": {
            "ensemble_weight": sweep,
            "threshold_current": _threshold_sweep(y, df["p_final"].to_numpy(dtype=float)),
            "threshold_ensemble_balanced": _threshold_sweep(y, df["ensemble_balanced"].to_numpy(dtype=float)),
        },
        "bootstrap": {
            "seasonal_layer_vs_level1": seasonal_bootstrap,
            "ensemble_balanced_vs_current": ensemble_bootstrap,
        },
        "runtime": _runtime_microbenchmark(df),
        "interpretation": {
            "seasonal_layer": "Aporta señal incremental reproducible en este test: mejora ranking y calibración frente a p_level1.",
            "dnn_lstm_alone": "No superan de forma consistente al score actual del Reto 05 cuando se evalúan por separado.",
            "ensemble": "La fusión exploratoria mejora modestamente PR-AUC/ROC-AUC/Brier, pero el peso se ha inspeccionado en test y no debe promocionarse todavía a producción.",
            "lift": "El ensemble no domina todas las métricas de Lift; por eso no se declara una mejora universal.",
        },
    }


def technology_capabilities() -> list[dict[str, str]]:
    return [
        {"technology": "pandas / NumPy", "status": "aplicado", "evidence": "Carga, joins, ranking, histogramas y benchmark vectorizado sobre los artefactos 2017."},
        {"technology": "scikit-learn", "status": "aplicado", "evidence": "ROC-AUC, PR-AUC, Brier, log-loss, Lift y bootstrap comparativo agrupado por cell."},
        {"technology": "Calibración temporal Platt", "status": "aplicado-auditado", "evidence": "Se integra el protocolo temporal estricto de Reto 05: Platt con OOF temporal, selección en 2016 y test 2017 abierto una sola vez. El ZIP recalcula y verifica el test final; DNN/SimpleRNN/LSTM mantienen además su auditoría raw→calibrated."},
        {"technology": "OSM / triaje vial", "status": "aplicado-parcial", "evidence": "Contexto de carretera, iluminación, velocidad y bosque próximo mediante caché/tabla offline; no se usa para alterar el score histórico."},
        {"technology": "astral", "status": "integrado-operativo", "evidence": "Endpoint de contexto solar preparado para coordenadas + timestamp; no entra en métricas 2017 porque los artefactos no contienen hora exacta del evento."},
        {"technology": "GeoPandas / Shapely · red 1D 250 m", "status": "no-reproducible-con-este-zip", "evidence": "El ZIP aporta centros de celdas BNG de 10 km, no geometría vial segmentada de 250 m ni proyecciones de eventos."},
        {"technology": "Edge effect forestal <50 m", "status": "no-reproducible-con-este-zip", "evidence": "Existe un indicador contextual forest_within_200m, pero no distancias métricas a linde forestal por observación."},
        {"technology": "Modelo Hurdle 1D", "status": "no-reentrenable-con-este-zip", "evidence": "Hay predicciones históricas y niveles del Reto 05, pero no el dataset/estimadores serializados necesarios para reconstruir el Hurdle del capítulo 7."},
        {"technology": "K-Means / clustering", "status": "aplicado-descriptivo", "evidence": "cluster del Reto 06 se conserva en la ruta y se usa como contexto; no se introduce post-hoc en el score para evitar leakage."},
        {"technology": "SHAP", "status": "pendiente-de-estimador", "evidence": "No se generan explicaciones falsas: hacen falta el modelo serializado y exactamente las features con las que fue entrenado."},
    ]
