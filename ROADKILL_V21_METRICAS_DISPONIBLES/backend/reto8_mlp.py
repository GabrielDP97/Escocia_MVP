from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, roc_auc_score

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
KEYS = ['cell', 'year', 'month']


def load_mlp_predictions(path=None):
    path = Path(path) if path else DATA_DIR / 'predicciones_test_2017_mlp.csv'
    if not path.exists():
        return pd.DataFrame(columns=KEYS + ['target_presence', 'dvc_count', 'p_mlp'])
    frame = pd.read_csv(path)
    required = KEYS + ['target_presence', 'dvc_count', 'p_mlp']
    if not set(required).issubset(frame):
        raise ValueError('El CSV MLP debe ser predicciones_test_2017_cap8.csv del capítulo 8.')
    frame = frame[required].copy()
    if frame.isna().any().any() or frame.duplicated(KEYS).any():
        raise ValueError('MLP: datos ausentes o claves duplicadas.')
    if set(frame.year) != {2017} or not frame.month.between(1, 12).all():
        raise ValueError('MLP: se requieren exclusivamente predicciones de test 2017.')
    if not set(frame.target_presence).issubset({0, 1}) or not np.array_equal(frame.target_presence, (frame.dvc_count > 0).astype(int)):
        raise ValueError('MLP: etiquetas inconsistentes con los recuentos.')
    if not np.isfinite(frame.p_mlp).all() or not frame.p_mlp.between(0, 1).all():
        raise ValueError('MLP: probabilidades inválidas.')
    reference = json.loads((DATA_DIR / 'reto08_mlp_metrics.json').read_text())
    scope = reference['scope']
    if len(frame) != scope['test_rows'] or frame.cell.nunique() != scope['test_cells'] or frame.target_presence.sum() != scope['test_positives']:
        raise ValueError('El CSV pertenece a una muestra distinta de la ejecución del capítulo 8 mostrada.')
    y, p = frame.target_presence, frame.p_mlp
    scores = {'roc_auc': roc_auc_score(y, p), 'pr_auc': average_precision_score(y, p),
              'brier': brier_score_loss(y, p), 'f1': f1_score(y, p >= reference['threshold'])}
    for key, value in scores.items():
        if abs(value - reference['test_metrics'][key]) > 0.000051:
            raise ValueError(f'El CSV no reproduce {key} de la ejecución mostrada; no se mezclan entrenamientos.')
    return frame


def get_reto8_mlp_metrics():
    result = json.loads((DATA_DIR / 'reto08_mlp_metrics.json').read_text(encoding='utf-8'))
    result['predictions_available'] = not load_mlp_predictions().empty
    return result
