from __future__ import annotations

from typing import Any
import math

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold


EPS = 1e-9


def _clip(values: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)


def _ece_and_bins(y: np.ndarray, score: np.ndarray, n_bins: int = 10) -> tuple[float, float, list[dict[str, float | int]]]:
    """Quantile-bin reliability diagnostic.

    Quantile bins are used because the project is imbalanced and most probabilities
    live close to zero. ECE/MCE here are descriptive calibration diagnostics, not
    replacements for the proper scoring rule (Brier/log-loss).
    """
    y = np.asarray(y, dtype=int)
    score = _clip(score)
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    edges = np.unique(np.quantile(score, quantiles))
    if len(edges) < 3:
        edges = np.linspace(float(score.min()), float(score.max()) + EPS, n_bins + 1)
    bin_id = np.digitize(score, edges[1:-1], right=True)

    rows: list[dict[str, float | int]] = []
    ece = 0.0
    mce = 0.0
    for i in range(len(edges) - 1):
        mask = bin_id == i
        if not np.any(mask):
            continue
        mean_pred = float(np.mean(score[mask]))
        observed = float(np.mean(y[mask]))
        gap = abs(mean_pred - observed)
        weight = float(np.mean(mask))
        ece += weight * gap
        mce = max(mce, gap)
        rows.append({
            "bin": int(len(rows) + 1),
            "n": int(mask.sum()),
            "score_min": float(np.min(score[mask])),
            "score_max": float(np.max(score[mask])),
            "mean_predicted": mean_pred,
            "observed_rate": observed,
            "abs_gap": float(gap),
        })
    return float(ece), float(mce), rows


def calibration_metrics(y: np.ndarray, score: np.ndarray) -> dict[str, Any]:
    score = _clip(score)
    ece, mce, bins = _ece_and_bins(y, score)
    return {
        "brier": float(brier_score_loss(y, score)),
        "log_loss": float(log_loss(y, score)),
        "roc_auc": float(roc_auc_score(y, score)),
        "pr_auc": float(average_precision_score(y, score)),
        "ece_q10": ece,
        "mce_q10": mce,
        "reliability_bins": bins,
    }


def _cluster_bootstrap_brier_delta(
    df: pd.DataFrame,
    before_col: str,
    after_col: str,
    samples: int = 400,
    seed: int = 42,
) -> dict[str, Any]:
    cells = df["cell"].to_numpy()
    unique_cells = np.unique(cells)
    groups = {cell: np.flatnonzero(cells == cell) for cell in unique_cells}
    y = df["target_presence"].to_numpy(dtype=int)
    before = _clip(df[before_col].to_numpy(dtype=float))
    after = _clip(df[after_col].to_numpy(dtype=float))
    rng = np.random.default_rng(seed)
    deltas: list[float] = []

    for _ in range(samples):
        sampled = rng.choice(unique_cells, size=len(unique_cells), replace=True)
        idx = np.concatenate([groups[cell] for cell in sampled])
        deltas.append(brier_score_loss(y[idx], after[idx]) - brier_score_loss(y[idx], before[idx]))

    arr = np.asarray(deltas, dtype=float)
    return {
        "samples": int(len(arr)),
        "cluster": "cell",
        "mean_delta_brier": float(np.mean(arr)),
        "ci95_low": float(np.quantile(arr, 0.025)),
        "ci95_high": float(np.quantile(arr, 0.975)),
    }


def _existing_pair(
    df: pd.DataFrame,
    raw_col: str,
    calibrated_col: str,
    label: str,
    bootstrap_samples: int,
    seed: int,
) -> dict[str, Any]:
    y = df["target_presence"].to_numpy(dtype=int)
    before = calibration_metrics(y, df[raw_col].to_numpy(dtype=float))
    after = calibration_metrics(y, df[calibrated_col].to_numpy(dtype=float))
    reduction = (before["brier"] - after["brier"]) / before["brier"] if before["brier"] else 0.0
    return {
        "label": label,
        "rows": int(len(df)),
        "cells": int(df["cell"].nunique()),
        "prevalence": float(y.mean()),
        "raw_column": raw_col,
        "calibrated_column": calibrated_col,
        "before": before,
        "after": after,
        "brier_absolute_improvement": float(before["brier"] - after["brier"]),
        "brier_relative_reduction": float(reduction),
        "bootstrap": _cluster_bootstrap_brier_delta(df, raw_col, calibrated_col, samples=bootstrap_samples, seed=seed),
    }


def _crossfit_calibration(
    y: np.ndarray,
    score: np.ndarray,
    groups: np.ndarray,
    method: str,
    n_splits: int = 5,
    seed: int = 42,
) -> np.ndarray:
    y = np.asarray(y, dtype=int)
    score = _clip(score)
    groups = np.asarray(groups)
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    out = np.zeros(len(score), dtype=float)

    if method == "sigmoid_logit":
        x = np.log(score / (1.0 - score))
    else:
        x = score

    for train_idx, test_idx in cv.split(np.zeros(len(y)), y, groups=groups):
        if method in {"sigmoid_score", "sigmoid_logit"}:
            # Near-unregularized 1D logistic calibration. `sigmoid_score` is the
            # closest reproducible analogue to CalibratedClassifierCV(method='sigmoid')
            # when only probabilities (not the original estimator decision scores)
            # are available. `sigmoid_logit` is classic Platt-style log-odds remapping.
            model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=2000)
            model.fit(x[train_idx].reshape(-1, 1), y[train_idx])
            out[test_idx] = model.predict_proba(x[test_idx].reshape(-1, 1))[:, 1]
        elif method == "isotonic":
            model = IsotonicRegression(out_of_bounds="clip")
            model.fit(score[train_idx], y[train_idx])
            out[test_idx] = model.predict(score[test_idx])
        else:
            raise ValueError(f"Método de calibración desconocido: {method}")
    return _clip(out)


def _current_common_frame(store: Any) -> pd.DataFrame:
    base = store.pred[["cell", "month", "target_presence", "p_final"]].copy()
    dnn = store.r8[["cell", "month", "p_dnn_calibrated"]].copy()
    lstm = store.r9[["cell", "target_month", "p_lstm_calibrated"]].rename(columns={"target_month": "month"})
    df = base.merge(dnn, on=["cell", "month"], how="inner").merge(lstm, on=["cell", "month"], how="inner")
    df["ensemble_balanced"] = 0.50 * df["p_final"] + 0.25 * df["p_dnn_calibrated"] + 0.25 * df["p_lstm_calibrated"]
    return df


def _crossfit_audit(df: pd.DataFrame, score_col: str, label: str) -> dict[str, Any]:
    y = df["target_presence"].to_numpy(dtype=int)
    groups = df["cell"].to_numpy()
    raw_score = df[score_col].to_numpy(dtype=float)
    baseline = calibration_metrics(y, raw_score)
    methods: dict[str, Any] = {}
    for method, method_label in [
        ("sigmoid_score", "Sigmoide sobre probabilidad (aprox. sklearn con artefactos disponibles)"),
        ("sigmoid_logit", "Platt sobre logit(probabilidad)"),
        ("isotonic", "Isotónica"),
    ]:
        calibrated = _crossfit_calibration(y, raw_score, groups, method=method)
        metrics = calibration_metrics(y, calibrated)
        methods[method] = {
            "label": method_label,
            "metrics": metrics,
            "delta_brier": float(metrics["brier"] - baseline["brier"]),
            "delta_log_loss": float(metrics["log_loss"] - baseline["log_loss"]),
            "delta_ece_q10": float(metrics["ece_q10"] - baseline["ece_q10"]),
        }
    return {
        "label": label,
        "rows": int(len(df)),
        "cells": int(df["cell"].nunique()),
        "protocol": "5-fold StratifiedGroupKFold por cell dentro de 2017; diagnóstico, no test temporal independiente",
        "baseline": baseline,
        "methods": methods,
    }


def build_calibration_audit(store: Any, bootstrap_samples: int = 400) -> dict[str, Any]:
    dnn = store.r8.dropna(subset=["target_presence", "p_dnn_raw", "p_dnn_calibrated"]).copy()
    r9 = store.r9.dropna(subset=["target_presence"]).copy()
    common = _current_common_frame(store)

    existing = {
        "dnn": _existing_pair(dnn, "p_dnn_raw", "p_dnn_calibrated", "Reto 08 · DNN", bootstrap_samples, 101),
        "simple_rnn": _existing_pair(r9, "p_simplernn_raw", "p_simplernn_calibrated", "Reto 09 · SimpleRNN", bootstrap_samples, 102),
        "lstm": _existing_pair(r9, "p_lstm_raw", "p_lstm_calibrated", "Reto 09 · LSTM", bootstrap_samples, 103),
    }

    current_crossfit = {
        "current_final": _crossfit_audit(common, "p_final", "Score actual p_final"),
        "ensemble_balanced": _crossfit_audit(common, "ensemble_balanced", "Ensemble exploratorio 50/25/25"),
    }

    return {
        "scope": {
            "evaluation_year": 2017,
            "warning": (
                "Además de esta auditoría 2017, V7 integra la evidencia del notebook temporal estricto ya ejecutado del Reto 05: "
                "Platt OOF temporal se ajustó sin usar 2017 y redujo Brier 0,159051→0,102692 en validation 2016. "
                "La cifra global 0,0799→0,0175 no se reproduce bajo ese protocolo estricto; el Hurdle 0,0018 de Reto 07 sigue requiriendo sus artefactos 1D."
            ),
        },
        "existing_saved_calibration": existing,
        "crossfit_diagnostic": current_crossfit,
        "claims": [
            {
                "claim": "Reto 05: la calibración sigmoide reduce Brier de 0,0799 a 0,0175.",
                "status": "no-reproducido-en-protocolo-temporal-estricto",
                "reason": (
                    "El notebook ejecutado con protocolo temporal estricto obtiene 0,159051→0,102692 en validation 2016 y 0,103348 en test 2017. "
                    "Por tanto, 0,0175 no es el resultado reproducible de ese experimento corregido; puede pertenecer a otro protocolo/modelo."
                ),
            },
            {
                "claim": "La calibración Platt/sigmoide puede mejorar mucho probabilidades profundas descalibradas.",
                "status": "verificado-con-los-artefactos-2017",
                "reason": (
                    "DNN, SimpleRNN y LSTM incluyen columnas raw y calibrated; en los tres casos el Brier baja de forma clara "
                    "sin cambiar ROC-AUC/PR-AUC, que es el patrón esperado de una transformación monótona de calibración."
                ),
            },
            {
                "claim": "Reto 07 Hurdle 1D: Brier 0,0018 y ROC/PR-AUC >0,990.",
                "status": "no-reproducible-con-este-zip",
                "reason": "Faltan la red vial 1D de 250 m, los eventos proyectados, features <50 m/iluminación y el estimador Hurdle serializado.",
            },
            {
                "claim": "Aplicar calibración adicional siempre mejora el Brier.",
                "status": "falso-como-regla-general",
                "reason": (
                    "El p_final ya está razonablemente calibrado: una sigmoide adicional sobre la probabilidad empeora su Brier en el cross-fit; "
                    "otras remapeadas pueden mejorar ligeramente. La calibración debe validarse, no aplicarse por defecto."
                ),
            },
        ],
        "methodology_note": (
            "El protocolo estricto real usa Platt sobre predicciones OOF de folds temporales expansivos (2013–2016), selecciona el sistema y el umbral con 2016, "
            "reentrena con 2008–2016 y abre 2017 una sola vez. El cross-fit por cell de esta pantalla sigue siendo solo un diagnóstico complementario."
        ),
    }
