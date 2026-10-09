import hashlib
import importlib.util
import json
import re
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app
from backend.model_catalog import get_model_catalog

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_can_be_regenerated_from_executed_outputs():
    path = ROOT / 'scripts/extract_notebook_metrics.py'
    spec = importlib.util.spec_from_file_location('metrics_extract', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.build_catalog() == get_model_catalog()
    for source in get_model_catalog()['sources']:
        assert hashlib.sha256((ROOT / 'evidencias' / source['file']).read_bytes()).hexdigest() == source['sha256']


def test_evaluation_phases_and_tasks_are_not_mixed():
    groups = {group['id']: group for group in get_model_catalog()['groups']}
    classical = groups['classical-validation']
    assert len(classical['rows']) == 14
    assert classical['phase'] == 'validation'
    assert all(row['threshold'] == .5 for row in classical['rows'])
    assert {row['model'] for row in classical['rows']} >= {'XGBoost', 'SVC', 'KNN', 'Gaussian Naive Bayes', 'Stacking temporal', 'Voting soft'}
    assert groups['monthly-test']['n'] == 12
    assert groups['neural-binary-test']['n'] == 6336
    assert groups['monthly-test']['task'] != groups['neural-binary-test']['task']
    assert groups['count-fit']['phase'] == 'fit'
    assert len(groups['count-validation']['rows']) == 6


def test_rf_archived_and_latest_execution_keep_their_own_thresholds():
    groups = {group['id']: group for group in get_model_catalog()['groups']}
    archived = groups['rf-deployed']['rows'][0]
    latest = groups['rf-test-stages']['rows'][1]
    assert archived['threshold'] != latest['threshold']
    assert abs(archived['f1'] - .556420233463035) < 1e-12
    assert latest['f1'] == .558177


def test_no_challenge_labels_in_frontend_or_rendered_api_texts():
    for file in (ROOT / 'frontend/src').rglob('*'):
        if file.is_file():
            assert not re.search(r'\breto', file.read_text(encoding='utf-8'), re.I), file
    client = TestClient(app)
    paths = ['/api/technology/benchmark?bootstrap_samples=30', '/api/technology/calibration-audit?bootstrap_samples=30',
             '/api/technology/capabilities', '/api/technology/lstm', '/api/technology/nlp']
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        def visible_strings(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key not in ['source', 'provenance', 'file']:
                        yield from visible_strings(child)
            elif isinstance(value, list):
                for child in value: yield from visible_strings(child)
            elif isinstance(value, str): yield value
        for value in visible_strings(response.json()):
            assert not re.search(r'\bretos?\s*\d', value, re.I), (path, value)


def test_generic_evidence_links_download_the_correct_notebook():
    client = TestClient(app)
    for name, marker in [('random-forest', 'classification_results'), ('mlp-lstm', 'binary_test_rows')]:
        response = client.get('/api/evidence/' + name)
        assert response.status_code == 200
        assert marker in response.text
        assert 'reto' not in response.headers['content-disposition'].lower()
