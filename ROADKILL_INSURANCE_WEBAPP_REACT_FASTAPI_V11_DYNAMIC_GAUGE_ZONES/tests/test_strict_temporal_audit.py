from backend.app import get_store
from backend.strict_temporal_audit import build_strict_temporal_audit


def test_strict_validation_confirms_platt_reduces_brier_without_using_2017():
    report = build_strict_temporal_audit(get_store())
    val = report["validation_2016"]
    assert val["raw"]["brier"] > val["level1_temporal_platt"]["brier"]
    assert val["calibration_effect"]["relative_brier_reduction"] > 0.35
    assert val["level1_temporal_platt"]["oof_rows_used"] == 25404
    assert report["protocol"]["test_final"] == 2017


def test_level2_was_selected_on_2016_before_opening_2017():
    report = build_strict_temporal_audit(get_store())
    val = report["validation_2016"]
    assert val["selected_output"] == "Nivel2_validation"
    assert val["level2_seasonal"]["pr_auc"] > val["level1_temporal_platt"]["pr_auc"]
    assert val["level2_seasonal"]["brier"] < val["level1_temporal_platt"]["brier"]


def test_current_zip_reproduces_final_2017_metrics_from_executed_notebook():
    report = build_strict_temporal_audit(get_store())
    ver = report["test_2017"]["verification"]
    assert ver["level1_matches"] is True
    assert ver["final_matches"] is True
    assert ver["p_level2_equals_p_final"] is True
    assert abs(report["test_2017"]["recomputed_final"]["brier"] - 0.10334811797516444) < 1e-12


def test_global_pdf_00175_is_not_claimed_as_reproduced_by_strict_reto5():
    report = build_strict_temporal_audit(get_store())
    rec = report["claim_reconciliation"]
    assert rec["status"] == "not_reproduced_under_strict_temporal_reto05"
    assert rec["strict_temporal_reto05_result"]["final_test_2017_brier"] > 0.0175


def test_selected_threshold_confusion_matrix_is_recomputed_exactly():
    report = build_strict_temporal_audit(get_store())
    cm = report["test_2017"]["confusion_matrix_selected_threshold"]
    assert cm["true_positives"] == 715
    assert cm["false_positives"] == 709
    assert cm["true_negatives"] == 4517
    assert cm["false_negatives"] == 431
    assert sum([
        cm["true_positives"],
        cm["false_positives"],
        cm["true_negatives"],
        cm["false_negatives"],
    ]) == 6372


def test_threshold_sensitivity_shows_expected_fp_fn_tradeoff():
    report = build_strict_temporal_audit(get_store())
    sweep = report["test_2017"]["threshold_sensitivity"]["rows"]
    by_threshold = {round(row["threshold"], 2): row for row in sweep}

    assert by_threshold[0.15]["false_negatives"] == 218
    assert by_threshold[0.15]["false_positives"] == 1541
    assert by_threshold[0.20]["false_negatives"] == 328
    assert by_threshold[0.20]["false_positives"] == 1005
    assert by_threshold[0.30]["false_negatives"] == 535
    assert by_threshold[0.30]["false_positives"] == 451
    assert by_threshold[0.40]["false_negatives"] == 660
    assert by_threshold[0.40]["false_positives"] == 204


def test_threshold_sweep_keeps_2016_threshold_as_selected_and_diagnostic_only():
    report = build_strict_temporal_audit(get_store())
    sensitivity = report["test_2017"]["threshold_sensitivity"]
    selected = sensitivity["selected_row"]

    assert sensitivity["status"] == "post_hoc_descriptive_test_2017"
    assert selected["is_selected_2016"] is True
    assert abs(selected["threshold"] - 0.2425809815683556) < 1e-10
    assert selected["true_positives"] == 715
    assert selected["false_positives"] == 709
    assert selected["false_negatives"] == 431
    assert "No debe usarse" in sensitivity["warning"]
