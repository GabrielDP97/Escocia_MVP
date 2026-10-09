from backend.reto9_lstm import get_reto9_lstm_metrics


def test_reto9_lstm_metrics_match_executed_notebook():
    report = get_reto9_lstm_metrics()
    assert report["reto"] == 9
    assert report["scope"]["test_year"] == 2017
    assert report["scope"]["test_rows"] == 6348
    assert report["scope"]["test_cells"] == 529
    assert report["temporal_design"]["selected_window_months"] == 12
    assert report["selected_model"]["name"] == "LSTM + Platt"
    assert report["selected_model"]["best_epoch_by_pr"] == 30
    assert report["selected_model"]["epochs_run"] == 38

    final = report["test_2017"]["calibrated_lstm"]
    assert abs(final["roc_auc"] - 0.8464966488254952) < 1e-12
    assert abs(final["pr_auc"] - 0.6092131142547675) < 1e-12
    assert abs(final["brier"] - 0.10384728110083574) < 1e-12
    assert abs(final["precision"] - 0.547923322683706) < 1e-12
    assert abs(final["recall"] - 0.5986038394415357) < 1e-12
    assert abs(final["f1"] - 0.5721434528773979) < 1e-12
    assert abs(final["lift_top_1pct"] - 5.1930628272251305) < 1e-12
    assert abs(final["lift_top_5pct"] - 4.476703217096381) < 1e-12

    raw = report["test_2017"]["raw_lstm"]
    assert abs(raw["brier"] - 0.16554153508220168) < 1e-12
    assert abs(report["test_2017"]["calibration_effect"]["relative_brier_reduction"] - 0.3726814176921272) < 1e-12
