"""Regression checks of arithmetic and exclusion rules, not scientific validation."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location('traffic_audit', Path(__file__).resolve().parents[1] / 'scripts/audit_traffic_exposure.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

def row(point, flow, length):
    return dict(count_point_id=point, year=2010, region_name='Scotland',
                local_authority_name='A', road_name='A1', road_category='MA',
                easting=100001, northing=600001, link_length_km=length,
                all_motor_vehicles=flow)

@pytest.mark.parametrize('lengths,expected', [((1,9),1900), ((9,1),9100)])
def test_exposure_is_sum_of_link_products(lengths, expected):
    report=audit.audit_traffic(pd.DataFrame([row(1,1000,lengths[0]),row(2,100,lengths[1])]))
    comparison=report['comparison'].iloc[0]
    assert comparison.legacy_daily_vkm == 5500
    assert comparison.candidate_daily_vkm == expected
    assert comparison.eligible

def test_exact_duplicate_removed_once():
    first=row(1,1000,1)
    report=audit.audit_traffic(pd.DataFrame([first,first,row(2,100,9)]))
    assert report['summary']['exact_duplicate_rows']==1
    assert report['comparison'].iloc[0].candidate_daily_vkm==1900

@pytest.mark.parametrize('change', [dict(all_motor_vehicles=999),dict(link_length_km=np.nan),dict(direction='N')])
def test_ambiguous_or_missing_rows_block_cell(change):
    changed=row(1,1000,1);changed.update(change)
    records=[row(1,1000,1),changed,row(2,100,9)] if 'all_motor_vehicles' in change else [changed,row(2,100,9)]
    comparison=audit.audit_traffic(pd.DataFrame(records))['comparison'].iloc[0]
    assert not comparison.eligible
    assert pd.isna(comparison.candidate_daily_vkm)

def test_zero_flow_is_valid_but_not_a_usable_denominator():
    report=audit.audit_traffic(pd.DataFrame([row(1,0,2)]))
    assert report['summary']['invalid_exposure_rows']==0
    assert not report['comparison'].iloc[0].eligible
