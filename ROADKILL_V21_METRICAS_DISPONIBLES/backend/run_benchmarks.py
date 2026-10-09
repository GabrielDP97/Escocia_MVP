from __future__ import annotations
import json
from pathlib import Path

import pandas as pd

from backend.app import get_store
from backend.technology_lab import build_technology_benchmark, technology_capabilities
from backend.calibration_lab import build_calibration_audit
from backend.strict_temporal_audit import build_strict_temporal_audit


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    store = get_store()

    report = build_technology_benchmark(store, bootstrap_samples=500)
    report["capabilities"] = technology_capabilities()
    benchmark_out = data_dir / "benchmark_technology_lab.json"
    benchmark_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    calibration = build_calibration_audit(store, bootstrap_samples=500)
    calibration_out = data_dir / "calibration_audit.json"
    calibration_out.write_text(json.dumps(calibration, indent=2, ensure_ascii=False), encoding="utf-8")

    rows = []
    for key, item in calibration["existing_saved_calibration"].items():
        rows.append({
            "key": key,
            "label": item["label"],
            "rows": item["rows"],
            "brier_raw": item["before"]["brier"],
            "brier_calibrated": item["after"]["brier"],
            "brier_absolute_improvement": item["brier_absolute_improvement"],
            "brier_relative_reduction": item["brier_relative_reduction"],
            "ece_raw": item["before"]["ece_q10"],
            "ece_calibrated": item["after"]["ece_q10"],
            "bootstrap_delta_brier_mean": item["bootstrap"]["mean_delta_brier"],
            "bootstrap_ci95_low": item["bootstrap"]["ci95_low"],
            "bootstrap_ci95_high": item["bootstrap"]["ci95_high"],
        })
    calibration_csv = data_dir / "calibration_comparison.csv"
    pd.DataFrame(rows).to_csv(calibration_csv, index=False)

    strict = build_strict_temporal_audit(store)
    strict_out = data_dir / "strict_temporal_audit.json"
    strict_out.write_text(json.dumps(strict, indent=2, ensure_ascii=False), encoding="utf-8")

    val = strict["validation_2016"]
    strict_validation_rows = [
        {"stage": "raw_random_forest", **val["raw"]},
        {"stage": "level1_temporal_platt", **{k: v for k, v in val["level1_temporal_platt"].items() if isinstance(v, (int, float))}},
        {"stage": "level2_seasonal", **{k: v for k, v in val["level2_seasonal"].items() if isinstance(v, (int, float))}},
    ]
    strict_validation_csv = data_dir / "strict_validation_2016_summary.csv"
    pd.DataFrame(strict_validation_rows).to_csv(strict_validation_csv, index=False)

    strict_test_csv = data_dir / "strict_test_2017_summary.csv"
    pd.DataFrame([
        {"stage": "level1", **strict["test_2017"]["recomputed_level1"]},
        {"stage": "level2", **strict["test_2017"]["recomputed_level2"]},
        {"stage": "final", **strict["test_2017"]["recomputed_final"]},
    ]).to_csv(strict_test_csv, index=False)

    threshold_sensitivity_csv = data_dir / "strict_threshold_sensitivity_2017.csv"
    pd.DataFrame(strict["test_2017"]["threshold_sensitivity"]["rows"]).to_csv(
        threshold_sensitivity_csv,
        index=False,
    )

    print(benchmark_out)
    print(calibration_out)
    print(calibration_csv)
    print(strict_out)
    print(strict_validation_csv)
    print(strict_test_csv)
    print(threshold_sensitivity_csv)


if __name__ == "__main__":
    main()
