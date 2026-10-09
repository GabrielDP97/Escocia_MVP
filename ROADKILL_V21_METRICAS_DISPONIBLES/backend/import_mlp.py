"""Importa los artefactos de la ejecución MLP del capítulo 8 mostrado."""
import argparse
import json
import shutil
from pathlib import Path
from backend.reto8_mlp import DATA_DIR, load_mlp_predictions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path, help='Carpeta artifacts/reto08_capitulo8_completo')
    args = parser.parse_args()
    config = json.loads((args.artifacts / 'configuracion.json').read_text(encoding='utf-8'))
    reference = json.loads((DATA_DIR / 'reto08_mlp_metrics.json').read_text())
    if config.get('quick_run') is not False or config.get('test') != 2017:
        raise ValueError('Se requiere la ejecución completa del capítulo 8 sobre test 2017.')
    if abs(float(config['binary_thresholds']['MLP']) - reference['threshold']) > 1e-10:
        raise ValueError('El umbral del CSV no coincide con la ejecución mostrada.')
    source = args.artifacts / 'predicciones_test_2017_cap8.csv'
    frame = load_mlp_predictions(source)
    # Check targets before publishing the probabilities to the demo/benchmark.
    import pandas as pd
    main = pd.read_csv(DATA_DIR / 'predicciones_test_2017.csv')
    common = main.merge(frame, on=['cell', 'year', 'month'], suffixes=('_main', '_mlp'), validate='one_to_one')
    for col in ['target_presence', 'dvc_count']:
        if not (common[col + '_main'] == common[col + '_mlp']).all():
            raise ValueError('Las etiquetas del principal y MLP no coinciden en las filas comunes.')
    shutil.copyfile(source, DATA_DIR / 'predicciones_test_2017_mlp.csv')
    print(f'Importadas {len(frame)} predicciones MLP verificadas. Reinicia el backend.')


if __name__ == '__main__':
    main()
