from __future__ import annotations

from typing import Any
import math

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

# Evidence copied from the user's executed strict-temporal Reto 05 notebook.
# This is deliberately separated from metrics recomputed from the current ZIP so
# provenance is explicit and no value is silently inferred.
STRICT_PROTOCOL = {
    "subtrain": "2008-2015",
    "validation": 2016,
    "development_final": "2008-2016",
    "test_final": 2017,
    "excluded_from_model_selection": [2018],
    "temporal_oof_folds_for_final_platt": [
        {"train": "2008-2012", "validation": 2013},
        {"train": "2008-2013", "validation": 2014},
        {"train": "2008-2014", "validation": 2015},
        {"train": "2008-2015", "validation": 2016},
    ],
    "rule": (
        "2017 no participa en selección de familia, hiperparámetros, calibración, "
        "estacionalidad ni umbral; se abre una sola vez después del refit 2008-2016."
    ),
}

VALIDATION_2016_EVIDENCE = {
    "base_model": "RandomForest",
    "raw": {
        "roc_auc": 0.847381,
        "pr_auc": 0.5466616982427334,
        "brier": 0.15905102158391862,
    },
    "level1_temporal_platt": {
        "roc_auc": 0.847381,
        "pr_auc": 0.546662,
        "brier": 0.10269160831611107,
        "lift_top_1pct": 5.086447,
        "lift_top_10pct": 3.694510,
        "oof_rows_used": 25404,
        "calibration_mode": "temporal_platt_oof",
    },
    "level2_seasonal": {
        "roc_auc": 0.853704,
        "pr_auc": 0.572252,
        "brier": 0.100471,
        "lift_top_1pct": 5.369028,
        "lift_top_10pct": 3.855141,
    },
    "selected_output": "Nivel2_validation",
    "selected_threshold_f1": 0.2425809815683556,
}

EXPECTED_TEST_2017 = {
    "level1": {
        "roc_auc": 0.8463171456451131,
        "pr_auc": 0.59807521094528,
        "brier": 0.105321289494774,
        "precision": 0.491120218579235,
        "recall": 0.6273996509598604,
        "f1": 0.5509578544061303,
    },
    "level2_final": {
        "roc_auc": 0.8521750557188551,
        "pr_auc": 0.6168015809402023,
        "brier": 0.10334811797516444,
        "precision": 0.5021067415730337,
        "recall": 0.6239092495636999,
        "f1": 0.556420233463035,
    },
}

GLOBAL_PDF_CLAIM = {
    "reto05_brier_before": 0.0799,
    "reto05_brier_after": 0.0175,
    "note": (
        "El documento global atribuye 0,0799→0,0175 a la calibración sigmoide/Stacking. "
        "Ese par no coincide con el Reto 05 temporal estricto ejecutado."
    ),
}


def _classification_metrics(y: np.ndarray, score: np.ndarray, threshold: float) -> dict[str, float | int]:
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    pred = (score >= threshold).astype(int)

    tp = int(np.sum((pred == 1) & (y == 1)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))

    n = int(len(y))
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    alerts = int(np.sum(pred == 1))

    return {
        "roc_auc": float(roc_auc_score(y, score)),
        "pr_auc": float(average_precision_score(y, score)),
        "brier": float(brier_score_loss(y, score)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "accuracy": float((tp + tn) / n) if n else 0.0,
        "specificity": float(tn / negatives) if negatives else 0.0,
        "false_positive_rate": float(fp / negatives) if negatives else 0.0,
        "false_negative_rate": float(fn / positives) if positives else 0.0,
        "alert_rate": float(alerts / n) if n else 0.0,
        "alerts": alerts,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "positives": positives,
        "negatives": negatives,
        "rows": n,
    }


def _threshold_sensitivity(
    y: np.ndarray,
    score: np.ndarray,
    selected_threshold: float,
) -> dict[str, Any]:
    """Describe the FP/FN trade-off on the untouched 2017 test.

    This is deliberately post-hoc and descriptive. It must not be used to
    retroactively choose a new production threshold from the 2017 test.
    """
    presets = [0.10, 0.15, 0.20, float(selected_threshold), 0.30, 0.40, 0.50]
    thresholds = sorted({round(float(t), 12) for t in presets})

    rows = []
    selected_row = None
    for threshold in thresholds:
        metrics = _classification_metrics(y, score, threshold)
        row = {
            "threshold": float(threshold),
            "is_selected_2016": bool(abs(threshold - selected_threshold) < 1e-10),
            **metrics,
        }
        rows.append(row)
        if row["is_selected_2016"]:
            selected_row = row

    if selected_row is None:
        raise RuntimeError("No se pudo localizar el umbral seleccionado de 2016 en el barrido.")

    for row in rows:
        row["delta_true_positives_vs_selected"] = int(
            row["true_positives"] - selected_row["true_positives"]
        )
        row["delta_false_positives_vs_selected"] = int(
            row["false_positives"] - selected_row["false_positives"]
        )
        row["delta_false_negatives_vs_selected"] = int(
            row["false_negatives"] - selected_row["false_negatives"]
        )
        row["delta_alerts_vs_selected"] = int(row["alerts"] - selected_row["alerts"])

    return {
        "status": "post_hoc_descriptive_test_2017",
        "warning": (
            "Este barrido muestra qué habría ocurrido en 2017 con distintos umbrales. "
            "No debe usarse para elegir retrospectivamente un nuevo umbral: el umbral válido "
            "del experimento sigue siendo 0,242581, elegido en validation 2016."
        ),
        "selected_threshold_from_2016": float(selected_threshold),
        "selected_row": selected_row,
        "rows": rows,
        "interpretation": (
            "Bajar el umbral reduce falsos negativos y aumenta el número de eventos detectados, "
            "pero genera más falsas alarmas. Subirlo hace lo contrario. Sin una función de coste "
            "de negocio no existe un umbral universalmente mejor."
        ),
    }


def _diffs(actual: dict[str, float], expected: dict[str, float]) -> dict[str, float]:
    return {key: float(actual[key] - expected[key]) for key in expected}


def _all_close(diffs: dict[str, float], tol: float = 5e-10) -> bool:
    return all(math.isfinite(v) and abs(v) <= tol for v in diffs.values())


def build_strict_temporal_audit(store: Any) -> dict[str, Any]:
    """Reconcile the strict 2016→2017 experiment with the current application artefact.

    Validation metrics come from the user's already executed strict-temporal notebook.
    The final 2017 metrics are independently recomputed from the row-level CSV bundled
    in this ZIP, so the final test result is not merely copied from a report.
    """
    df = store.pred.dropna(subset=["target_presence", "p_level1", "p_level2", "p_final"]).copy()
    y = df["target_presence"].to_numpy(dtype=int)
    threshold = float(store.threshold)

    recomputed_level1 = _classification_metrics(y, df["p_level1"].to_numpy(dtype=float), threshold)
    recomputed_level2 = _classification_metrics(y, df["p_level2"].to_numpy(dtype=float), threshold)
    final_scores = df["p_final"].to_numpy(dtype=float)
    recomputed_final = _classification_metrics(y, final_scores, threshold)
    threshold_sensitivity = _threshold_sensitivity(y, final_scores, threshold)

    d1 = _diffs(recomputed_level1, EXPECTED_TEST_2017["level1"])
    d2 = _diffs(recomputed_final, EXPECTED_TEST_2017["level2_final"])

    raw_brier = VALIDATION_2016_EVIDENCE["raw"]["brier"]
    calibrated_brier = VALIDATION_2016_EVIDENCE["level1_temporal_platt"]["brier"]
    level2_brier = VALIDATION_2016_EVIDENCE["level2_seasonal"]["brier"]

    calibration_abs = raw_brier - calibrated_brier
    calibration_rel = calibration_abs / raw_brier
    seasonal_abs = calibrated_brier - level2_brier
    seasonal_rel = seasonal_abs / calibrated_brier

    pdf_after = GLOBAL_PDF_CLAIM["reto05_brier_after"]
    final_brier = recomputed_final["brier"]

    return {
        "protocol": STRICT_PROTOCOL,
        "validation_2016": {
            **VALIDATION_2016_EVIDENCE,
            "calibration_effect": {
                "absolute_brier_reduction": float(calibration_abs),
                "relative_brier_reduction": float(calibration_rel),
                "conclusion": (
                    "Temporal Platt sí mejora claramente la calidad probabilística en validation 2016: "
                    "Brier 0,159051 → 0,102692 sin usar 2017."
                ),
            },
            "seasonal_effect_after_calibration": {
                "absolute_brier_reduction": float(seasonal_abs),
                "relative_brier_reduction": float(seasonal_rel),
                "conclusion": (
                    "Después de calibrar, el Nivel 2 estacional todavía reduce Brier y mejora PR-AUC; "
                    "por eso fue seleccionado antes de abrir 2017."
                ),
            },
            "provenance": "verified_from_user_executed_strict_temporal_notebook",
        },
        "test_2017": {
            "rows": int(len(df)),
            "cells": int(df["cell"].nunique()),
            "threshold_frozen_from_2016": threshold,
            "recomputed_level1": recomputed_level1,
            "recomputed_level2": recomputed_level2,
            "recomputed_final": recomputed_final,
            "confusion_matrix_selected_threshold": {
                "threshold": threshold,
                "true_positives": recomputed_final["true_positives"],
                "false_positives": recomputed_final["false_positives"],
                "true_negatives": recomputed_final["true_negatives"],
                "false_negatives": recomputed_final["false_negatives"],
            },
            "threshold_sensitivity": threshold_sensitivity,
            "expected_from_executed_notebook": EXPECTED_TEST_2017,
            "verification": {
                "level1_deltas": d1,
                "final_deltas": d2,
                "level1_matches": _all_close(d1),
                "final_matches": _all_close(d2),
                "p_level2_equals_p_final": bool(np.allclose(df["p_level2"], df["p_final"], rtol=0, atol=0)),
            },
            "provenance": "recomputed_from_row_level_predictions_in_current_zip",
        },
        "claim_reconciliation": {
            "global_pdf_claim": GLOBAL_PDF_CLAIM,
            "strict_temporal_reto05_result": {
                "raw_validation_brier": raw_brier,
                "platt_validation_brier": calibrated_brier,
                "level2_validation_brier": level2_brier,
                "final_test_2017_brier": final_brier,
            },
            "status": "not_reproduced_under_strict_temporal_reto05",
            "difference_pdf_after_vs_strict_test": float(final_brier - pdf_after),
            "interpretation": (
                "La afirmación 0,0799→0,0175 no queda reproducida por el Reto 05 temporal estricto. "
                "No se etiqueta automáticamente como falsa: puede proceder de otro protocolo, muestra o modelo. "
                "Para este protocolo corregido, la evidencia auditable es 0,159051→0,102692 en validation 2016 "
                "y 0,103348 en el test final 2017."
            ),
        },
        "bottom_line": (
            "Sí se confirma la tesis cualitativa de que la calibración mejora las probabilidades, pero no la cifra 0,0175 "
            "para el Reto 05 temporal estricto. El test 2017 del ZIP reproduce el resultado ejecutado con precisión numérica."
        ),
    }
