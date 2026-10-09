import math

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.trip_risk import estimate_trip_risk


def example():
    # Two adjacent zones, 10 km apart, each at 2 DVC / 100,000 vehicle-km.
    return [
        {"cell": 1, "easting": 15000, "northing": 5000, "pred_count_final": 2, "exposure_vkm_proxy": 100000},
        {"cell": 2, "easting": 25000, "northing": 5000, "pred_count_final": 2, "exposure_vkm_proxy": 100000},
    ]


def test_normalizes_exposure_and_accumulates_one_trip():
    report = estimate_trip_risk(example(), 5, "2017-05-01")
    assert report["distance_km"] == 10
    assert report["expected_events_per_trip"] == pytest.approx(0.0002)
    assert report["probability"] == pytest.approx(1 - math.exp(-0.0002))
    assert report["temporal_resolution"] == "monthly"
    higher_traffic = example()
    for point in higher_traffic:
        point["exposure_vkm_proxy"] *= 2
    assert estimate_trip_risk(higher_traffic, 5)["expected_events_per_trip"] == pytest.approx(0.0001)


def test_full_route_does_not_change_with_direction_or_day_within_month():
    points = example()
    points[1]["pred_count_final"] = 5
    first = estimate_trip_risk(points, 5, "2017-05-01")
    reverse = estimate_trip_risk(points[::-1], 5, "2017-05-31")
    assert first["probability"] == reverse["probability"]
    longer = estimate_trip_risk(points, 5, distance_km=20)
    assert longer["expected_events_per_trip"] == pytest.approx(first["expected_events_per_trip"] * 2)
    assert longer["probability"] > first["probability"]


@pytest.mark.parametrize("field,value", [("pred_count_final", None), ("exposure_vkm_proxy", 0), ("exposure_vkm_proxy", float("nan")), ("pred_count_final", -1)])
def test_missing_or_invalid_data_never_becomes_zero_risk(field, value):
    points = example()
    points[0][field] = value
    report = estimate_trip_risk(points, 5)
    assert report["status"] == "partial"
    assert report["full_route_probability"] is None
    assert report["covered_distance_km"] == pytest.approx(5)
    assert report["uncovered_distance_km"] == pytest.approx(5)


def test_no_traversable_route_no_estimate_and_gap_reported():
    assert estimate_trip_risk(example()[:1], 5)["probability"] is None
    points = example()
    points[1]["cell"] = 5
    points[1]["easting"] = 55000
    assert estimate_trip_risk(points, 5)["nonadjacent_segments"] == 1
    points[1]["cell"] = points[0]["cell"]
    assert estimate_trip_risk(points, 5)["probability"] is None


def test_true_zero_counts_are_distinguished_from_missing_counts():
    points = example()
    for point in points:
        point["pred_count_final"] = 0
    assert estimate_trip_risk(points, 5)["probability"] == 0


def test_api_real_routes_historical_date_validation_and_direction():
    client = TestClient(app)
    params = {"road_name": "A82", "month": 5, "travel_date": "2017-05-15"}
    forward = client.get("/api/route", params=params)
    assert forward.status_code == 200
    report = forward.json()["trip_risk"]
    assert report["status"] == "partial"
    assert 0 < report["probability"] < 1
    assert report["full_route_probability"] is None
    assert report["uncovered_distance_km"] > 0
    backward = client.get("/api/route", params={**params, "reverse": True}).json()["trip_risk"]
    assert report["probability"] == pytest.approx(backward["probability"])
    for extra in [{"travel_date": "2026-05-15"}, {"travel_date": "2017-06-15"}, {"travel_date": "invalid"}, {"distance_km": 0}]:
        assert client.get("/api/route", params={**params, **extra}).status_code == 422


def test_missing_middle_cell_is_unobserved_not_interpolated():
    points = example()
    points[1]["cell"] = 3
    points[1]["easting"] = 35000
    report = estimate_trip_risk(points, 5)
    assert report["distance_km"] == 20
    assert report["covered_distance_km"] == 10
    assert report["uncovered_distance_km"] == 10
    assert report["coverage_fraction"] == .5
    assert report["unknown_cells"] == [2]
    assert report["expected_events_covered"] == pytest.approx(.0002)
    assert report["expected_events_per_trip"] is None
    assert report["full_route_probability"] is None
    # Supplying valid data for the middle cell increases coverage and hazard.
    middle = {**points[0], "cell": 2, "easting": 25000}
    complete = estimate_trip_risk([points[0], middle, points[1]], 5)
    assert complete["coverage_fraction"] == 1
    assert complete["full_route_probability"] == complete["probability"]
    assert complete["expected_events_covered"] == pytest.approx(.0004)


def test_diagonal_clip_preserves_lengths_and_excludes_missing_cell():
    from backend.trip_risk import segment_cell_lengths
    pieces = segment_cell_lengths((15000, 5000), (35000, 25000))
    assert sum(km for _, km in pieces) == pytest.approx(math.sqrt(800) )
    assert [cell for cell, _ in pieces] == [1, 82, 163]


def test_invalid_coordinates_and_all_missing_rates_produce_no_estimate():
    points = example()
    points[0]["easting"] = float("inf")
    assert estimate_trip_risk(points, 5)["probability"] is None
    points = example()
    for point in points:
        point["pred_count_final"] = None
    report = estimate_trip_risk(points, 5)
    assert report["probability"] is None
    assert report["covered_distance_km"] == 0
    assert report["uncovered_distance_km"] == 10
