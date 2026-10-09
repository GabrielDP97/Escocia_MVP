"""AADF point means and route aggregation; explicit synthetic test records."""
import copy
import pandas as pd
import pytest
from backend.route_traffic import aggregate_route_traffic, prepare_route_traffic, load_route_traffic
from backend.route_daily_risk import estimate_route_daily_risk
from backend.app import app, get_store
from fastapi.testclient import TestClient

def raw_row(point,flow,x=15000,road='A82'):
    return dict(count_point_id=point,year=2017,region_name='Scotland',road_name=road,
                easting=x,northing=5000,all_motor_vehicles=flow)

def route_points(table):
    return [dict(row,easting=15000 if row['cell']==1 else 25000,northing=5000,pred_count_final=2)
            for row in table[table.road_name.eq('A82')].to_dict('records')]

def test_mean_of_displayed_points_is_not_weighted_by_number_of_aforos_or_length():
    table,_=aggregate_route_traffic(pd.DataFrame([raw_row(1,1000),raw_row(2,3000),raw_row(3,5000,25000),raw_row(4,99999,15000,'A90')]))
    r=estimate_route_daily_risk(route_points(table),5)
    assert table.loc[(table.cell==1)&(table.road_name=='A82'),'daily_vehicle_mean'].iloc[0]==2000
    assert r['daily_route_vehicles']==3500  # (2000 + 5000)/2, not the pooled mean of raw aforos.
    assert r['traffic_points_used']==2 and r['traffic_source']=='mean_route_points'
    assert r['probability_approx']==pytest.approx(4/31/3500)
    assert estimate_route_daily_risk(route_points(table)[::-1],5)['daily_route_vehicles']==3500

def test_exact_duplicate_aforo_is_ignored_and_conflicting_aforo_blocks_cell():
    first=raw_row(1,1000)
    table,meta=aggregate_route_traffic(pd.DataFrame([first,first,raw_row(2,3000)]))
    assert meta['exact_duplicate_rows']==1 and table.daily_vehicle_mean.iloc[0]==2000
    table,meta=aggregate_route_traffic(pd.DataFrame([first,raw_row(1,1200),raw_row(2,3000),raw_row(3,5000,25000)]))
    assert meta['conflicting_count_points']==1
    r=estimate_route_daily_risk(route_points(table),5)
    assert r['probability_approx'] is None and r['missing_traffic_cells']==[1]

@pytest.mark.parametrize('value',[None,-1,float('inf')])
def test_invalid_flow_is_not_silently_removed_from_average(value):
    table,_=aggregate_route_traffic(pd.DataFrame([raw_row(1,value),raw_row(2,3000),raw_row(3,5000,25000)]))
    assert table.traffic_status.eq('blocked').sum()==1
    assert estimate_route_daily_risk(route_points(table),5)['probability_approx'] is None

def test_zero_aforo_is_included_and_all_zero_mean_is_not_divided():
    table,_=aggregate_route_traffic(pd.DataFrame([raw_row(1,0),raw_row(2,2000,25000)]))
    assert estimate_route_daily_risk(route_points(table),5)['daily_route_vehicles']==1000
    table,_=aggregate_route_traffic(pd.DataFrame([raw_row(1,0),raw_row(2,0,25000)]))
    r=estimate_route_daily_risk(route_points(table),5)
    assert r['status']=='zero_traffic' and r['probability_approx'] is None

def test_export_lookup_and_missing_original(tmp_path):
    app_root=tmp_path/'repo/app';app_root.mkdir(parents=True)
    assert prepare_route_traffic(app_root)['status']=='missing_original'
    assert load_route_traffic(app_root).empty
    source=tmp_path/'repo/Datos/trafico/aadf_data/dft_traffic_counts_aadf.csv'
    source.parent.mkdir(parents=True)
    pd.DataFrame([raw_row(1,1000),raw_row(2,3000),raw_row(3,5000,25000)]).to_csv(source,index=False)
    result=prepare_route_traffic(app_root)
    assert result['status']=='prepared' and len(result['source_sha256'])==64
    assert len(load_route_traffic(app_root))==2
    assert (app_root/'data/route_traffic_2017_metadata.json').is_file()

def test_api_automatic_mean_uses_all_route_points_and_no_manual_value(monkeypatch):
    store=copy.copy(get_store());store.demo=store.demo.copy()
    selected=store.demo.road_name.eq('A82')&store.demo.month.eq(5)
    count=int(selected.sum());values=[1000+100*i for i in range(count)]
    store.aadf_available=True
    store.demo.loc[selected,'aadf_daily_vehicle_mean']=values
    store.demo.loc[selected,'traffic_status']='valid'
    monkeypatch.setattr('backend.app.get_store',lambda:store)
    r=TestClient(app).get('/api/route',params=dict(road_name='A82',month=5)).json()['daily_route_risk']
    assert r['daily_route_vehicles']==sum(values)/count and r['traffic_source']=='mean_route_points'
    store.demo.loc[store.demo.index[selected][0],'aadf_daily_vehicle_mean']=None
    assert TestClient(app).get('/api/route',params=dict(road_name='A82',month=5)).json()['daily_route_risk']['probability_approx'] is None


@pytest.mark.parametrize('value',[None,-1,float('inf'),1000])
def test_invalid_historical_value_is_not_fabricated(value):
    from backend.route_traffic import historical_daily_mean
    assert historical_daily_mean(value) is None


def test_historical_inverse_is_expm1_and_auto_does_not_hide_incomplete_aadf():
    import math
    from backend.route_traffic import historical_daily_mean, select_route_traffic
    assert historical_daily_mean(math.log1p(2000))==pytest.approx(2000)
    frame=pd.DataFrame(dict(log_traffic_mean=[math.log1p(2000)],aadf_daily_vehicle_mean=[None],traffic_status=['blocked']))
    auto,basis=select_route_traffic(frame,'auto',True)
    assert basis=='aadf_2017' and auto.daily_vehicle_mean.isna().all()
    historical,basis=select_route_traffic(frame,'auto',False)
    assert basis=='historical_profile' and historical.daily_vehicle_mean.iloc[0]==pytest.approx(2000)


def test_real_api_metrics_are_visible_without_aadf_and_source_is_explicit():
    client=TestClient(app)
    r=client.get('/api/route',params=dict(road_name='A82',month=5)).json()['daily_route_risk']
    assert r['traffic_basis']=='historical_profile' and r['traffic_period']==[2008,2017]
    assert r['traffic_road_specific'] is False
    assert r['daily_route_vehicles']==pytest.approx(6426.445231729053)
    assert r['probability_approx']*100==pytest.approx(0.00541711916693256)
    assert r['traffic_points_used']==17 and r['full_route_probability'] is None
    strict=client.get('/api/route',params=dict(road_name='A82',month=5,traffic_mode='aadf_2017')).json()['daily_route_risk']
    assert strict['probability_approx'] is None
    assert client.get('/api/route',params=dict(road_name='A82',traffic_mode='invalid')).status_code==422
