from backend.app import get_store
from backend.calibration_lab import build_calibration_audit


def test_saved_deep_calibration_reduces_brier_without_changing_ranking_metrics():
    report = build_calibration_audit(get_store(), bootstrap_samples=30)
    for key in ("dnn", "simple_rnn", "lstm"):
        item = report["existing_saved_calibration"][key]
        assert item["after"]["brier"] < item["before"]["brier"]
        assert abs(item["after"]["roc_auc"] - item["before"]["roc_auc"]) < 1e-12
        assert abs(item["after"]["pr_auc"] - item["before"]["pr_auc"]) < 1e-12
        assert item["bootstrap"]["ci95_high"] < 0


def test_extra_sigmoid_is_not_assumed_to_help_an_already_calibrated_score():
    report = build_calibration_audit(get_store(), bootstrap_samples=30)
    current = report["crossfit_diagnostic"]["current_final"]
    # With the available 2017 artifacts, an extra sigmoid applied directly to
    # p_final worsens Brier. This protects us from claiming calibration is automatic magic.
    assert current["methods"]["sigmoid_score"]["delta_brier"] > 0


def test_document_claims_are_marked_by_reproducibility():
    report = build_calibration_audit(get_store(), bootstrap_samples=30)
    statuses = {c["claim"]: c["status"] for c in report["claims"]}
    assert any(status == "verificado-con-los-artefactos-2017" for status in statuses.values())
    assert any(status == "no-reproducido-en-protocolo-temporal-estricto" for status in statuses.values())
    assert any(status == "no-reproducible-con-este-zip" for status in statuses.values())
