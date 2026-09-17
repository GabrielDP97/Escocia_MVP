import numpy as np

from backend.app import (
    empirical_threshold_percentile,
    get_store,
    route,
    threshold_score_map,
)


def test_threshold_score_map_is_monotonic_and_marks_official_cut():
    store = get_store()
    rows = threshold_score_map(store)

    assert len(rows) == 7
    assert sum(bool(row["is_official"]) for row in rows) == 1

    thresholds = [float(row["threshold"]) for row in rows]
    percentiles = [float(row["risk_percentile"]) for row in rows]

    assert thresholds == sorted(thresholds)
    assert percentiles == sorted(percentiles)
    assert all(0.0 <= value <= 100.0 for value in percentiles)

    official = next(row for row in rows if row["is_official"])
    assert abs(float(official["threshold"]) - store.threshold) < 1e-10


def test_threshold_percentile_matches_empirical_cdf_of_2017_scores():
    store = get_store()
    threshold = 0.20
    expected = float(np.mean(store.demo["p_final"].astype(float).to_numpy() <= threshold) * 100.0)
    actual = empirical_threshold_percentile(store, threshold)
    assert abs(actual - expected) < 1e-12


def test_route_exposes_threshold_to_risk_score_mapping_for_frontend_gauge():
    payload = route("A82", month=5, reverse=False)
    assert "threshold_score_map" in payload
    rows = payload["threshold_score_map"]
    assert any(abs(float(row["threshold"]) - 0.20) < 1e-12 for row in rows)
    assert any(bool(row["is_official"]) for row in rows)


def test_threshold_score_map_exposes_dynamic_gauge_boundaries():
    store = get_store()
    rows = threshold_score_map(store)

    for row in rows:
        probability = row["probability_boundaries"]
        gauge = row["gauge_boundaries"]

        assert 0.0 <= float(probability["normal_to_watch"]) <= float(probability["watch_to_alert"]) <= float(probability["alert_to_critical"]) <= 1.0
        assert 0.0 <= float(gauge["normal_to_watch"]) <= float(gauge["watch_to_alert"]) <= float(gauge["alert_to_critical"]) <= 100.0
        assert abs(float(gauge["watch_to_alert"]) - float(row["risk_percentile"])) < 1e-12


def test_dynamic_gauge_zones_match_probability_state_for_every_2017_row():
    store = get_store()
    rows = threshold_score_map(store)
    frame = store.demo[["p_final", "risk_percentile"]].dropna().copy()

    for row in rows:
        cut = float(row["threshold"])
        watch_start = max(0.0, cut - 0.05)
        critical_start = min(1.0, cut + 0.10)
        gauge = row["gauge_boundaries"]
        normal_end = float(gauge["normal_to_watch"])
        watch_end = float(gauge["watch_to_alert"])
        alert_end = float(gauge["alert_to_critical"])

        for rec in frame.itertuples(index=False):
            p = float(rec.p_final)
            score = float(rec.risk_percentile)

            probability_state = (
                0 if p < watch_start else
                1 if p < cut else
                2 if p < critical_start else
                3
            )
            # Boundary scores are empirical cut positions. Points exactly on a
            # boundary belong to the segment ending at that position.
            gauge_state = (
                0 if score <= normal_end else
                1 if score <= watch_end else
                2 if score <= alert_end else
                3
            )
            assert gauge_state == probability_state


def test_route_exposes_dynamic_gauge_zone_boundaries():
    payload = route("A82", month=5, reverse=False)
    row = next(item for item in payload["threshold_score_map"] if item["is_official"])
    assert "gauge_boundaries" in row
    assert "probability_boundaries" in row
    assert set(row["gauge_boundaries"]) == {
        "normal_to_watch",
        "watch_to_alert",
        "alert_to_critical",
    }
