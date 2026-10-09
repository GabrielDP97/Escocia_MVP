import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.app import app, get_store
from backend.reto8_mlp import load_mlp_predictions
from backend.technology_lab import build_technology_benchmark


def test_api_does_not_relabel_legacy_probabilities():
    client = TestClient(app)
    report = client.get('/api/technology/reto8-mlp').json()
    assert report['predictions_available'] is False
    road = client.get('/api/roads').json()['roads'][0]['road_name']
    response = client.get('/api/route', params={'road_name': road, 'month': 5})
    assert response.status_code == 200
    for point in response.json()['points']:
        assert 'p_dnn' not in point
        assert point['p_mlp'] is None
        assert point['p_ensemble_exploratory'] is None
    benchmark = build_technology_benchmark(get_store(), 30)
    assert set(benchmark['models']) == {'level1_no_seasonal', 'current_final', 'lstm'}
    assert benchmark['runtime'] is None
    assert benchmark['parameter_sweeps']['ensemble_weight'] == []


def test_bundled_notebooks_support_displayed_experiments():
    client = TestClient(app)
    for name, cell, expected in [('capitulo8', 129, '0.8441'), ('comparacion', 23, '0.841542')]:
        response = client.get('/api/evidence/' + name)
        assert response.status_code == 200
        notebook = json.loads(response.content)
        outputs = json.dumps(notebook['cells'][cell]['outputs'])
        assert expected in outputs


def test_import_rejects_legacy_dnn_and_different_execution(tmp_path):
    path = tmp_path / 'wrong.csv'
    pd.DataFrame({'cell': [1], 'year': [2017], 'month': [1], 'target_presence': [0],
                  'dvc_count': [0], 'p_dnn_calibrated': [.1]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match='CSV MLP'):
        load_mlp_predictions(path)
    pd.DataFrame({'cell': [1], 'year': [2017], 'month': [1], 'target_presence': [0],
                  'dvc_count': [0], 'p_mlp': [.1]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match='muestra distinta'):
        load_mlp_predictions(path)
