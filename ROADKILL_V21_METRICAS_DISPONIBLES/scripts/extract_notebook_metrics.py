"""Regenera el catálogo desde salidas ejecutadas; no entrena ni inventa métricas."""
from html.parser import HTMLParser
from pathlib import Path
import ast
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidencias'
RF_FILE = 'Reto5_Trazabilidad_Completa_Frontend_2017_REGENERADO(3).ipynb'
NN_FILE = 'RetoRoadkill_cap08_U1_U2_U3(3).ipynb'
NAMES = {
    'RandomForest': 'Random Forest', 'XGBoost': 'XGBoost', 'GradientBoosting': 'Gradient Boosting',
    'Stacking_temporal': 'Stacking temporal', 'Voting_soft': 'Voting soft', 'DecisionTree': 'Árbol de decisión',
    'KNN_conditional': 'KNN', 'GaussianNB_conditional': 'Gaussian Naive Bayes', 'SVC_candidate': 'SVC',
    'Logistic_L1': 'Regresión logística L1', 'Logistic_L2': 'Regresión logística L2',
    'Logistic_ElasticNet': 'Regresión logística Elastic Net', 'GridSearch_Logistic': 'Regresión logística optimizada',
    'RandomForest_raw_validation': 'Random Forest sin calibrar', 'Nivel1_Platt_validation': 'Random Forest + Platt',
    'Nivel2_validation': 'Random Forest + Platt + ajuste estacional',
    'Nivel1_test_2017': 'Random Forest + Platt', 'Nivel2_test_2017': 'Random Forest + Platt + ajuste estacional',
    'LinearRegression': 'Regresión lineal', 'SVR_candidate': 'SVR', 'Poisson_offset': 'Poisson con offset',
    'NegativeBinomial_offset': 'Binomial negativa con offset', 'Poisson_offset_development': 'Poisson con offset', 'NegativeBinomial_offset_development': 'Binomial negativa con offset', 'Poisson_offset_test_2017': 'Poisson con offset',
    'NegativeBinomial_offset_test_2017_posthoc': 'Binomial negativa con offset · exploratorio',
    'Media': 'Media de entrenamiento', 'Poisson': 'Regresión Poisson sin offset', 'Keras lineal': 'Red neuronal lineal', 'MLP': 'MLP',
    'Mayoritaria': 'Clase mayoritaria', 'Logistic': 'Regresión logística', 'Prevalencia': 'Prevalencia de entrenamiento',
    'Naive': 'Persistencia', 'Estacional': 'Naive estacional', 'Ridge-window': 'Ridge con ventana',
    'MLP-window': 'MLP con ventana',
}
FIELDS = {'ROC_AUC': 'roc_auc', 'AP': 'pr_auc', 'Brier': 'brier', 'F1': 'f1',
          'precision_050': 'precision', 'recall_050': 'recall', 'f1_050': 'f1', 'alertas': 'alerts'}


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.tables = []; self.rows = []; self.row = []; self.cell = None
    def handle_starttag(self, tag, attrs):
        if tag == 'table': self.rows = []
        if tag == 'tr': self.row = []
        if tag in ('td', 'th'): self.cell = ''
    def handle_data(self, data):
        if self.cell is not None: self.cell += data
    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(self.cell.strip()); self.cell = None
        if tag == 'tr': self.rows.append(self.row)
        if tag == 'table': self.tables.append(self.rows)


def tables(notebook, cell):
    result = []
    for output in notebook['cells'][cell].get('outputs', []):
        html = ''.join(output.get('data', {}).get('text/html', []))
        if html:
            parser = TableParser(); parser.feed(html); result.extend(parser.tables)
    return result


def numeric(value):
    if value in ('NaN', 'nan', '—', ''): return None
    if value == '...': raise ValueError('Tabla truncada: faltan datos')
    try: return float(value)
    except ValueError: return value


def records(table):
    header = table[0][1:]
    return [{FIELDS.get(key, key): numeric(value) for key, value in zip(header, row[1:])}
            for row in table[1:]]


def stream(notebook, cell):
    return ''.join(''.join(output.get('text', [])) for output in notebook['cells'][cell].get('outputs', []))


def build_catalog():
    rf = json.loads((EVIDENCE / RF_FILE).read_text(encoding='utf-8'))
    nn = json.loads((EVIDENCE / NN_FILE).read_text(encoding='utf-8'))
    groups = []
    def group(id, task, title, phase, n, note, file, cell, table_index=0, threshold=None, digits=6):
        rows = records(tables(rf if file == RF_FILE else nn, cell)[table_index])
        for row in rows:
            original = row.pop('model', row.pop('modelo', ''))
            row['model'] = NAMES.get(original, original)
            if threshold is not None: row['threshold'] = threshold
        item = {'id': id, 'task': task, 'title': title, 'phase': phase, 'n': n, 'note': note,
                'digits': digits, 'evidence': 'random-forest' if file == RF_FILE else 'mlp-lstm',
                'source': {'file': file, 'cell': cell, 'table': table_index}, 'rows': rows}
        groups.append(item); return item
    rf_threshold = float(re.search(r'Umbral F1 congelado en validation 2016:\s*([\d.e+-]+)', stream(rf, 37)).group(1))
    group('classical-validation', 'presence', 'Clasificadores tabulares · selección de modelos', 'validation', 6372,
          'Validación 2016; train 2008–2015. Umbral 0,50. Gaussian Naive Bayes, KNN y SVC se entrenan con muestras limitadas; las métricas se evalúan en el conjunto completo de validación.', RF_FILE, 31, threshold=.5)
    group('rf-validation-stages', 'presence', 'Random Forest · calibración y estacionalidad', 'validation', 6372,
          'Validación 2016 de la nueva ejecución. Umbral 0,50 para esta tabla; no es el umbral elegido posteriormente para test.', RF_FILE, 37, 0, .5)
    group('rf-test-stages', 'presence', 'Random Forest · evaluación final del notebook', 'test', 6372,
          'Test 2017; refit 2008–2016. Esta ejecución usa umbral 0,250055. La demo conserva la ejecución archivada, con umbral 0,242581.', RF_FILE, 37, 1, rf_threshold)
    rf_audit = json.loads((ROOT / 'data/strict_temporal_audit.json').read_text())
    rf_live = {**rf_audit['test_2017']['recomputed_final'], 'threshold': rf_audit['validation_2016']['selected_threshold_f1']}
    groups.append({'id': 'rf-deployed', 'task': 'presence', 'title': 'Random Forest · ejecución usada en la demo', 'phase': 'test', 'n': 6372,
                   'note': 'Resultados archivados y recalculables desde las predicciones de la aplicación. Se distinguen del nuevo entrenamiento del notebook.', 'digits': 6,
                   'evidence': 'random-forest', 'rows': [{'model': 'Random Forest + Platt + ajuste estacional · demo',
                   **{key: rf_live[key] for key in ['roc_auc', 'pr_auc', 'brier', 'precision', 'recall', 'f1', 'accuracy', 'threshold']}}]})
    group('count-validation', 'count', 'Regresión y modelos de recuento · selección', 'validation', 6372,
          'Validación 2016; train 2008–2015. SVR entrenado con 30.000 filas. Poisson se seleccionó por deviance, no por MAE.', RF_FILE, 48, 0)
    group('count-test', 'count', 'Poisson y binomial negativa · evaluación final', 'test', 6372,
          'Test 2017; refit 2008–2016. Binomial negativa es una evaluación exploratoria.', RF_FILE, 48, 2)
    group('count-fit', 'count', 'Poisson y binomial negativa · ajuste estadístico', 'fit', 57120,
          'AIC, BIC y log-verosimilitud del ajuste en 2008–2016. No son errores de test.', RF_FILE, 48, 3)
    binary = group('neural-binary-test', 'presence', 'MLP, Random Forest y regresión logística · presencia', 'test', 6336,
                   'Test 2017; train 2009–2015, validación 2016. 528 celdas; tráfico del año anterior. Sin refit posterior a validación.', NN_FILE, 129, digits=4)
    thresholds = {row[0]: numeric(row[1]) for row in tables(nn, 125)[0][1:]}
    for row in binary['rows']:
        reverse = {'Regresión logística': 'Logistic', 'Random Forest': 'RandomForest', 'MLP': 'MLP', 'Prevalencia de entrenamiento': 'Prevalencia'}
        row['threshold'] = thresholds[reverse[row['model']]]
    nn_val = stream(nn, 122) + stream(nn, 123)
    val_rows = [
        {'model': 'Regresión logística', 'roc_auc': float(re.search(r'Logistic VAL ROC-AUC:\s*([\d.]+)', nn_val).group(1)),
         'pr_auc': float(re.search(r'Logistic VAL ROC-AUC:[^\n]+AP:\s*([\d.]+)', nn_val).group(1))},
        {'model': 'Random Forest', 'pr_auc': float(re.search(r'RandomForest VAL AP:\s*([\d.]+)', nn_val).group(1))},
        {'model': 'MLP', 'roc_auc': float(re.search(r'MLP VAL AUC:\s*([\d.]+)', nn_val).group(1)),
         'pr_auc': float(re.search(r'MLP VAL AUC:[^\n]+AP:\s*([\d.]+)', nn_val).group(1))},
    ]
    val_f1 = {row[0]: numeric(row[2]) for row in tables(nn, 125)[0][1:]}
    for row, key in zip(val_rows, ['Logistic', 'RandomForest', 'MLP']):
        row.update({'f1': val_f1[key], 'threshold': thresholds[key]})
    groups.append({'id': 'neural-binary-validation', 'task': 'presence', 'title': 'MLP y baselines · selección del umbral', 'phase': 'validation', 'n': 6336, 'digits': 6,
                   'note': 'Validación 2016. Se conservan solo las métricas publicadas en las salidas; F1 y umbrales proceden de la tabla de selección.', 'evidence': 'mlp-lstm',
                   'source': {'file': NN_FILE, 'cells': [122, 123, 125]}, 'rows': val_rows})
    group('neural-count-test', 'count', 'Redes neuronales y baselines · recuentos por celda', 'test', 6336,
          'Test 2017; train 2009–2015 y validación 2016. Recuentos por celda y mes; salidas negativas recortadas a cero. MLP seleccionada: 256/128/64.', NN_FILE, 113, digits=4)
    group('intensity-test', 'intensity', 'MLP softmax y baselines · intensidad de atropellos', 'test', 6336,
          'Test 2017. Tres clases: sin registros, moderado y alto; cortes fijados usando entrenamiento.', NN_FILE, 119, digits=4)
    group('monthly-test', 'monthly', 'LSTM, MLP y baselines · recuento mensual agregado', 'test', 12,
          'Doce meses de 2017, ámbito fijo de 528 celdas. Ventana de 12 meses, pronóstico móvil a un mes. Esta LSTM predice recuentos; es distinta de la LSTM de presencia.', NN_FILE, 148, digits=4)
    monthly_val = ast.literal_eval(re.search(r'VAL MAE:\s*(\{.*?\})', stream(nn, 148)).group(1))
    groups.append({'id': 'monthly-validation', 'task': 'monthly', 'title': 'Modelos temporales · selección en validación', 'phase': 'validation', 'n': 12, 'digits': 6,
                   'note': 'Doce meses de 2016; la referencia seleccionada fue el naive estacional.', 'evidence': 'mlp-lstm', 'source': {'file': NN_FILE, 'cell': 148},
                   'rows': [{'model': NAMES.get(k, k), 'MAE': v} for k, v in monthly_val.items()]})
    arch = ast.literal_eval(re.search(r'Red de regresión congelada:\s*\w+\s*(\{.*?\})', stream(nn, 111)).group(1))
    groups.append({'id': 'mlp-architecture', 'task': 'count', 'title': 'MLP de recuentos · selección de arquitectura', 'phase': 'validation', 'n': 6336, 'digits': 6,
                   'note': 'MAE con predicciones recortadas a cero en validación 2016. Se seleccionó la arquitectura 256/128/64.', 'evidence': 'mlp-lstm', 'source': {'file': NN_FILE, 'cell': 111},
                   'rows': [{'model': {'MLP': 'MLP 64/32', 'small': 'MLP 16', 'large': 'MLP 256/128/64', 'regularized': 'MLP 128/64 regularizada'}[k], 'MAE': v} for k, v in arch.items()]})
    perc = stream(nn, 28)
    groups.append({'id': 'perceptron', 'task': 'presence', 'title': 'Perceptrón · prueba con dos variables', 'phase': 'validation', 'n': 6336, 'digits': 6,
                   'note': 'Validación 2016; utiliza log-tráfico y log-exposición. Solo se publicaron accuracy y F1; no se inventan métricas probabilísticas.', 'evidence': 'mlp-lstm', 'source': {'file': NN_FILE, 'cell': 28},
                   'rows': [{'model': 'Perceptrón', 'accuracy': float(re.search(r'Accuracy validation:\s*([\d.]+)', perc).group(1)), 'f1': float(re.search(r'F1 validation:\s*([\d.]+)', perc).group(1))}]})
    temporal = json.loads((ROOT / 'data/reto09_lstm_metrics.json').read_text())
    for phase in ['validation', 'test']:
        rows = []
        for model in temporal['model_comparison']:
            fields = {'roc_auc': 'val_roc_auc', 'pr_auc': 'val_pr_auc', 'brier': 'val_brier'} if phase == 'validation' else {
                'roc_auc': 'test_roc_auc', 'pr_auc': 'test_pr_auc', 'brier': 'test_brier', 'precision': 'test_precision', 'recall': 'test_recall', 'f1': 'test_f1', 'lift_top_1pct': 'lift_top_1pct'}
            rows.append({'model': model['model'], **{k: model[v] for k,v in fields.items()}, 'threshold': model['threshold_from_val']})
        groups.append({'id': 'temporal-presence-' + phase, 'task': 'presence', 'title': 'LSTM, SimpleRNN y regresión logística con retardos', 'phase': phase,
                       'n': 6348 if phase == 'test' else None, 'digits': 6, 'note': 'Clasificación de presencia con secuencias por celda. Resultados de los artefactos originales de la aplicación; el notebook original de entrenamiento no está entre los dos archivos adjuntos.',
                       'rows': rows, 'source': {'file': 'reto09_lstm_metrics.json'}})
    sources = [{'file': name, 'sha256': hashlib.sha256((EVIDENCE/name).read_bytes()).hexdigest()} for name in [RF_FILE, NN_FILE]]
    return {'groups': groups, 'sources': sources, 'rows': sum(len(g['rows']) for g in groups),
            'note': 'Comparar dentro de cada tabla: cambian tareas, muestras, entrenamiento y fases. No se usa validación como test ni se completan métricas ausentes.'}


if __name__ == '__main__':
    catalog = build_catalog()
    (ROOT / 'data/model_comparison_catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(f"Catálogo: {len(catalog['groups'])} tablas y {catalog['rows']} resultados de modelos")
