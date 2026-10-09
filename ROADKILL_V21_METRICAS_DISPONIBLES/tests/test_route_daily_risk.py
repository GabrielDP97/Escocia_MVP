"""Scenario arithmetic and integration tests; not individual calibration."""
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.route_daily_risk import estimate_route_daily_risk


def points():
    return [dict(cell=1, easting=15000, northing=5000, pred_count_final=2),
            dict(cell=2, easting=25000, northing=5000, pred_count_final=3)]


def test_monthly_sum_daily_mean_and_single_route_flow():
    r=estimate_route_daily_risk(points(),5,'2017-05-15',5000)
    assert r['monthly_expected_dvc']==5
    assert r['daily_expected_dvc']==pytest.approx(5/31)
    assert r['monthly_vehicle_passes']==155000
    assert r['events_per_vehicle_pass']==pytest.approx(5/31/5000)
    assert r['probability_approx']==r['events_per_vehicle_pass']
    assert r['full_route_probability'] is None
    assert not r['validated_individual_probability']


def test_daily_flow_is_required_but_monthly_and_daily_counts_remain_available():
    r=estimate_route_daily_risk(points(),5)
    assert r['status']=='needs_traffic'
    assert r['probability_approx'] is None
    assert r['monthly_expected_dvc']==5
    assert r['traffic_source']=='missing'


def test_day_direction_and_distance_do_not_change_count_based_rate():
    first=estimate_route_daily_risk(points(),5,'2017-05-01',5000)
    last=estimate_route_daily_risk(points()[::-1],5,'2017-05-31',5000,20)
    assert first['probability_approx']==last['probability_approx']
    assert first['covered_distance_km']==10 and last['covered_distance_km']==20
    assert estimate_route_daily_risk(points(),5,daily_route_vehicles=10000)['probability_approx']==first['probability_approx']/2
    feb=estimate_route_daily_risk(points(),2,daily_route_vehicles=5000)
    assert feb['days_in_month']==28 and feb['probability_approx']==pytest.approx(5/28/5000)


def test_missing_values_and_geometry_gaps_are_not_risk_zero():
    p=points();p[1].update(cell=3,easting=35000)
    r=estimate_route_daily_risk(p,5,daily_route_vehicles=5000)
    assert r['unknown_geometry_cells']==[2]
    assert r['coverage_fraction']==.5
    assert r['full_route_probability'] is None
    p[0]['pred_count_final']=None
    r=estimate_route_daily_risk(p,5,daily_route_vehicles=5000)
    assert r['monthly_expected_dvc']==3 and r['missing_count_cells']==[1]
    assert r['coverage_fraction']==.25
    for row in p:row['pred_count_final']=None
    assert estimate_route_daily_risk(p,5,daily_route_vehicles=5000)['probability_approx'] is None


def test_duplicates_are_counted_once_and_conflicts_block_result():
    p=points();p.append(p[0].copy())
    r=estimate_route_daily_risk(p,5,daily_route_vehicles=5000)
    assert r['monthly_expected_dvc']==5 and r['duplicate_rows_ignored']==1
    p[-1]['pred_count_final']=99
    assert estimate_route_daily_risk(p,5,daily_route_vehicles=5000)['monthly_expected_dvc'] is None


def test_zero_counts_are_distinct_from_missing_and_impossible_percent_is_not_clipped():
    p=points()
    for row in p:row['pred_count_final']=0
    assert estimate_route_daily_risk(p,5,daily_route_vehicles=5000)['probability_approx']==0
    r=estimate_route_daily_risk(points(),5,daily_route_vehicles=.001)
    assert r['events_per_vehicle_pass']>1 and r['probability_approx'] is None
    assert r['status']=='incompatible_traffic'


@pytest.mark.parametrize('traffic',[0,-1,float('nan'),float('inf')])
def test_invalid_daily_flow_rejected(traffic):
    with pytest.raises(ValueError):estimate_route_daily_risk(points(),5,daily_route_vehicles=traffic)


def test_api_real_a82_sum_matches_all_unique_cells_and_date_validation():
    client=TestClient(app)
    params=dict(road_name='A82',month=5,travel_date='2017-05-15')
    data=client.get('/api/route',params={**params, 'traffic_mode':'aadf_2017'}).json()
    assert data['daily_route_risk']['probability_approx'] is None
    params['daily_route_vehicles']=5000  # Explicit test scenario; not a measured A82 flow.
    data=client.get('/api/route',params=params).json()
    r=data['daily_route_risk']
    expected=sum(p['pred_count_final'] for p in data['points'])
    assert r['monthly_expected_dvc']==pytest.approx(expected)
    assert r['probability_approx']==pytest.approx(expected/31/5000)
    assert len(r['available_cells'])==17 and r['coverage_fraction']<1
    reverse=client.get('/api/route',params={**params,'reverse':True}).json()['daily_route_risk']
    assert reverse['probability_approx']==r['probability_approx']
    for change in [dict(daily_route_vehicles=0),dict(daily_route_vehicles=-3),dict(daily_route_vehicles=100000001),dict(travel_date='2026-05-15'),dict(travel_date='2017-06-15')]:
        assert client.get('/api/route',params={**params,**change}).status_code==422
