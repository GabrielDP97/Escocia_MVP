from backend.app import get_store
from backend.technology_lab import build_technology_benchmark, technology_capabilities


def test_benchmark_runs_and_has_common_rows():
    report = build_technology_benchmark(get_store(), bootstrap_samples=30)
    assert report["scope"]["rows_common"] > 6000
    assert 0 < report["scope"]["prevalence"] < 1


def test_existing_seasonal_layer_beats_level1_on_pr_auc_and_brier():
    report = build_technology_benchmark(get_store(), bootstrap_samples=30)
    level1 = report["models"]["level1_no_seasonal"]["metrics"]
    current = report["models"]["current_final"]["metrics"]
    assert current["pr_auc"] > level1["pr_auc"]
    assert current["brier"] < level1["brier"]


def test_exploratory_ensemble_is_only_research_candidate():
    report = build_technology_benchmark(get_store(), bootstrap_samples=30)
    current = report["models"]["current_final"]["metrics"]
    candidate = report["models"]["ensemble_balanced"]["metrics"]
    assert candidate["pr_auc"] > current["pr_auc"]
    assert candidate["brier"] < current["brier"]
    assert "exploratorio" in report["scope"]["warning"].lower()


def test_capabilities_are_honest_about_missing_high_resolution_inputs():
    caps = {c["technology"]: c["status"] for c in technology_capabilities()}
    assert caps["GeoPandas / Shapely · red 1D 250 m"] == "no-reproducible-con-este-zip"
    assert caps["SHAP"] == "pendiente-de-estimador"
