"""Reproducible traffic audit and paired Poisson exposure experiment.

Candidate exposure uses sum(AADF_i * link_km_i), after exact deduplication.
Whole links are still assigned to their count-point cell. This does NOT verify
road geometry, coverage of minor roads, or individual collision probabilities.
"""
from __future__ import annotations

from pathlib import Path
import calendar
import hashlib
import json
import math
import warnings
import zipfile

import numpy as np
import pandas as pd

REQUIRED = ["count_point_id", "year", "region_name", "local_authority_name", "road_name",
            "road_category", "easting", "northing", "link_length_km", "all_motor_vehicles"]
OPTIONAL = ["direction_of_travel", "direction", "estimation_method", "estimation_method_detailed"]
NUMERIC_FEATURES = ["year", "count_points", "easting_mean", "northing_mean", "month_sin", "month_cos"]
CATEGORICAL_FEATURES = ["road_category", "local_authority_name"]


def detect_project_root(start: Path) -> Path:
    start = start.resolve()
    for root in [start, *start.parents]:
        if (root / "Datos/trafico/aadf_data/dft_traffic_counts_aadf.csv").is_file():
            return root
    raise FileNotFoundError(
        "Falta el CSV original de tráfico. Coloca el notebook en IA/notebooks/escocia "
        "y el CSV en IA/Datos/trafico/aadf_data/dft_traffic_counts_aadf.csv. "
        "No se descargan datos ni se usan datos sintéticos automáticamente."
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_traffic(path: Path, start_year: int = 2008, end_year: int = 2017) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns
    missing = sorted(set(REQUIRED) - set(header))
    if missing:
        raise ValueError(f"Faltan columnas del AADF: {missing}")
    parts = []
    for chunk in pd.read_csv(path, usecols=[c for c in REQUIRED + OPTIONAL if c in header],
                             dtype={"count_point_id": "string"}, chunksize=100000):
        years = pd.to_numeric(chunk["year"], errors="coerce")
        keep = chunk["region_name"].astype(str).str.strip().eq("Scotland") & years.between(start_year, end_year)
        if keep.any():
            parts.append(chunk.loc[keep].copy())
    if not parts:
        raise ValueError("No hay registros de Scotland en los años solicitados.")
    return pd.concat(parts, ignore_index=True)


def mode_or_missing(series):
    values = series.dropna().mode()
    return values.iloc[0] if len(values) else np.nan


def audit_traffic(raw: pd.DataFrame) -> dict:
    missing = set(REQUIRED) - set(raw.columns)
    if missing:
        raise ValueError(f"Faltan columnas: {sorted(missing)}")
    frame = raw.copy()
    frame["source_row"] = np.arange(len(frame))
    for col in ["year", "easting", "northing", "link_length_km", "all_motor_vehicles"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    point_ids = pd.to_numeric(frame["count_point_id"], errors="coerce")
    valid_id = (point_ids.notna() & np.isfinite(point_ids) & point_ids.ge(0)
                & point_ids.lt(2**63) & point_ids.eq(np.floor(point_ids)))
    frame["count_point_id"] = point_ids.where(valid_id).astype("Int64")
    valid_xy = (np.isfinite(frame["easting"]) & np.isfinite(frame["northing"])
                & frame["easting"].between(0, 799999.999) & frame["northing"].between(0, 1299999.999))
    frame["cell"] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    frame.loc[valid_xy, "cell"] = (
        np.floor(frame.loc[valid_xy, "northing"] / 10000).astype(int) * 80
        + np.floor(frame.loc[valid_xy, "easting"] / 10000).astype(int)
    ).astype("int64")
    good_year = frame["year"].notna() & np.isfinite(frame["year"]) & frame["year"].eq(np.floor(frame["year"]))
    frame["valid_key"] = valid_id & good_year & valid_xy
    frame["valid_exposure"] = (np.isfinite(frame["all_motor_vehicles"]) & frame["all_motor_vehicles"].ge(0)
                                & np.isfinite(frame["link_length_km"]) & frame["link_length_km"].gt(0))
    direction_columns = [c for c in ["direction_of_travel", "direction"] if c in frame]
    directional = pd.Series(False, index=frame.index)
    for col in direction_columns:
        directional |= frame[col].notna() & frame[col].astype(str).str.strip().ne("")
    frame["directional_format"] = directional
    # A duplicate is exact only when the statistical fields and direction agree.
    fingerprint = REQUIRED + direction_columns
    exact_rows = frame.duplicated(fingerprint, keep="first")
    deduplicated = frame.loc[~exact_rows].copy()
    valid = deduplicated[deduplicated["valid_key"]].copy()
    group_sizes = valid.groupby(["count_point_id", "year"], dropna=False)["source_row"].transform("size")
    conflict_indices = valid.index[group_sizes > 1]
    frame["conflicting_key"] = False
    conflict_keys = valid.loc[conflict_indices, ["count_point_id", "year"]].drop_duplicates()
    if len(conflict_keys):
        keyed = pd.MultiIndex.from_frame(frame[["count_point_id", "year"]])
        frame["conflicting_key"] = keyed.isin(pd.MultiIndex.from_frame(conflict_keys))
    frame["blocked_row"] = ~frame["valid_key"] | ~frame["valid_exposure"] | frame["conflicting_key"] | directional
    clean = deduplicated.loc[~frame.loc[deduplicated.index, "blocked_row"]].copy()
    grouped = frame.dropna(subset=["cell", "year"]).groupby(["cell", "year"], as_index=False).agg(
        traffic_mean=("all_motor_vehicles", "mean"), link_length_km=("link_length_km", "sum"),
        count_points=("count_point_id", "nunique"), easting_mean=("easting", "mean"), northing_mean=("northing", "mean"),
        road_category=("road_category", mode_or_missing), local_authority_name=("local_authority_name", mode_or_missing),
        road_name=("road_name", mode_or_missing), raw_rows=("source_row", "size"), blocked_rows=("blocked_row", "sum"),
    )
    grouped["legacy_daily_vkm"] = grouped["traffic_mean"].clip(lower=0) * grouped["link_length_km"].clip(lower=0)
    clean["daily_vkm"] = clean["all_motor_vehicles"] * clean["link_length_km"]
    candidate = clean.groupby(["cell", "year"], as_index=False).agg(
        candidate_daily_vkm=("daily_vkm", "sum"), unique_rows=("source_row", "size"),
    )
    comparison = grouped.merge(candidate, on=["cell", "year"], how="left", validate="one_to_one")
    comparison["eligible"] = comparison["blocked_rows"].eq(0) & comparison["candidate_daily_vkm"].gt(0) & comparison["legacy_daily_vkm"].gt(0)
    # Partial known totals must not masquerade as a complete cell denominator.
    comparison.loc[~comparison["eligible"], "candidate_daily_vkm"] = np.nan
    comparison["candidate_over_legacy"] = comparison["candidate_daily_vkm"] / comparison["legacy_daily_vkm"].replace(0, np.nan)
    comparison["change_percent"] = (comparison["candidate_over_legacy"] - 1) * 100
    ratio = comparison.loc[comparison["eligible"], "candidate_over_legacy"]
    metadata = {
        "status": "audit_calculated_geometry_pending", "raw_rows": len(frame),
        "exact_duplicate_rows": int(exact_rows.sum()), "conflicting_keys": len(conflict_keys),
        "invalid_key_or_coordinates_rows": int((~frame["valid_key"]).sum()),
        "invalid_exposure_rows": int((~frame["valid_exposure"]).sum()), "directional_rows": int(directional.sum()),
        "cell_years": len(comparison), "eligible_cell_years": int(comparison["eligible"].sum()),
        "excluded_cell_years": int((~comparison["eligible"]).sum()),
        "candidate_over_legacy_median": float(ratio.median()) if len(ratio) else None,
        "geographic_coverage_verified": False, "individual_probability_validated": False, "adopted_in_frontend": False,
        "limitations": [
            "Las longitudes completas siguen asignadas a la celda del punto de conteo: falta recortar la geometría vial por celda.",
            "AADF cubre la red principal y una muestra de vías menores; los DVC pueden abarcar otras vías de la celda.",
            "Las duplicidades por tramo con identificadores diferentes requieren geometría o identificadores de enlace; no quedan descartadas por esta auditoría.",
            "Los datos anuales se distribuyen según días del mes; no se observa tráfico diario individual.",
            "Las celdas con datos incompletos o contradictorios se excluyen del experimento, no se convierten en riesgo cero.",
        ],
    }
    quality = frame.groupby("estimation_method", dropna=False).size().rename("rows").reset_index() if "estimation_method" in frame else pd.DataFrame(columns=["estimation_method", "rows"])
    issues = frame.loc[frame["blocked_row"] | exact_rows].copy()
    issues["exact_duplicate"] = exact_rows.loc[issues.index]
    return {"summary": metadata, "comparison": comparison, "issues": issues, "quality": quality, "clean": clean}


def save_audit(report: dict, output: Path, source_path: Path | None = None):
    output.mkdir(parents=True, exist_ok=True)
    meta = dict(report["summary"])
    if source_path:
        meta["source_filename"] = source_path.name
        meta["source_sha256"] = sha256_file(source_path)
    for key, name in [("comparison", "comparacion_exposicion_celda_anio.csv"), ("issues", "filas_a_revisar.csv"), ("quality", "calidad_estimaciones_trafico.csv")]:
        report[key].to_csv(output / name, index=False)
    (output / "resumen_auditoria.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def read_dvc_local(root: Path) -> tuple[pd.DataFrame, dict]:
    candidates = [root / "Datos/dvc/DVC_SCOTLAND_GEOJSON_4326/DVC_SCOTLAND.geojson",
                  root / "Datos/dvc/DVC_SCOTLAND.geojson", root / "Datos/dvc/DVC_SCOTLAND_GEOJSON_4326.zip"]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        raise FileNotFoundError("La auditoría del tráfico ya está guardada. Para reentrenar falta el GeoJSON/ZIP original de DVC en Datos/dvc/.")
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith('.geojson')]
            if len(names) != 1:
                raise ValueError("Se requiere un único GeoJSON en el ZIP DVC.")
            content = json.loads(archive.read(names[0]))
    else:
        content = json.loads(path.read_text(encoding='utf-8-sig'))
    records = []
    rejected = 0
    for feature in content.get('features', []):
        p = feature.get('properties') or {}
        try:
            x, y = float(p['OS_EASTING']), float(p['OS_NORTHIN'])
            raw_year, raw_month = float(p['YEAR']), float(p['MONTH'])
            year, month = int(raw_year), int(raw_month)
            if year != raw_year or month != raw_month:
                raise ValueError()
            if not (math.isfinite(x) and math.isfinite(y) and 0 <= x < 800000 and 0 <= y < 1300000 and 1 <= month <= 12):
                raise ValueError()
        except (KeyError, TypeError, ValueError, OverflowError):
            rejected += 1
            continue
        if 2008 <= year <= 2017:
            records.append({'cell': math.floor(y / 10000) * 80 + math.floor(x / 10000), 'year': year, 'month': month})
    if not records:
        raise ValueError("No hay DVC válidos en 2008–2017.")
    counts = pd.DataFrame(records).groupby(['cell', 'year', 'month']).size().rename('dvc_count').reset_index()
    return counts, {'source_sha256': sha256_file(path), 'rejected_dvc_records': rejected,
                    'deduplication': 'No se deduplican accidentes por coordenada/mes: pueden ser eventos distintos.'}


def build_count_panel(comparison: pd.DataFrame, dvc_counts: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    eligible = comparison.loc[comparison['eligible']].copy()
    if eligible.empty:
        raise ValueError('No hay celdas/años con denominadores válidos para comparar.')
    months = pd.DataFrame({'month': range(1, 13)})
    panel = eligible.merge(months, how='cross').merge(dvc_counts, on=['cell', 'year', 'month'], how='left', validate='one_to_one')
    panel['dvc_count'] = panel['dvc_count'].fillna(0).astype(int)  # No registro, no ausencia comprobada.
    panel['days_in_month'] = [calendar.monthrange(int(y), int(m))[1] for y, m in zip(panel.year, panel.month)]
    panel['legacy_exposure_vkm'] = panel['legacy_daily_vkm'] * panel['days_in_month']
    panel['candidate_exposure_vkm'] = panel['candidate_daily_vkm'] * panel['days_in_month']
    panel['month_sin'] = np.sin(2 * np.pi * panel['month'] / 12)
    panel['month_cos'] = np.cos(2 * np.pi * panel['month'] / 12)
    all_keys = pd.MultiIndex.from_frame(dvc_counts[['cell', 'year', 'month']])
    eligible_keys = pd.MultiIndex.from_frame(panel[['cell', 'year', 'month']])
    excluded = dvc_counts.loc[~all_keys.isin(eligible_keys), 'dvc_count'].sum()
    return panel, {'included_dvc_records': int(panel.dvc_count.sum()), 'outside_eligible_cell_years_dvc_records': int(excluded),
                   'negative_label': 'Sin DVC registrado; no significa ausencia verificada.'}


def paired_poisson_experiment(panel: pd.DataFrame, model_directory: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.linear_model import PoissonRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_poisson_deviance, r2_score
    from sklearn.exceptions import ConvergenceWarning
    metrics, predictions = [], []
    panel = panel.copy()
    for column in CATEGORICAL_FEATURES:
        panel[column] = panel[column].fillna('__missing__').astype(str)
    for evaluation, end_year, target_year in [('validation_2016', 2015, 2016), ('test_2017', 2016, 2017)]:
        train = panel[panel.year <= end_year].copy()
        test = panel[panel.year.eq(target_year)].copy()
        if train.empty or test.empty or train.dvc_count.sum() == 0:
            raise ValueError(f'Faltan datos para {evaluation}: no se cambia a una partición aleatoria.')
        if train.year.max() > end_year or test.year.nunique() != 1:
            raise AssertionError('Partición temporal inválida.')
        for label, exposure_col in [('legacy_mean_times_lengths', 'legacy_exposure_vkm'), ('candidate_sum_link_products', 'candidate_exposure_vkm')]:
            prep = ColumnTransformer([
                ('numeric', Pipeline([('imputer', SimpleImputer(strategy='median')), ('scale', StandardScaler())]), NUMERIC_FEATURES),
                ('category', Pipeline([('imputer', SimpleImputer(strategy='most_frequent')), ('encode', OneHotEncoder(handle_unknown='ignore', drop='first', sparse_output=False))]), CATEGORICAL_FEATURES),
            ])
            x_train = prep.fit_transform(train[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
            x_test = prep.transform(test[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
            exposure = train[exposure_col].to_numpy(float)
            frequency = train.dvc_count.to_numpy(float) / exposure
            # Scaling the target avoids a tiny numerical optimization scale.
            # alpha=0 makes this exactly a reparameterized unpenalized Poisson offset objective.
            scale = exposure.sum() / train.dvc_count.sum()
            model = PoissonRegressor(alpha=0, max_iter=5000, tol=1e-9)
            with warnings.catch_warnings():
                warnings.simplefilter('error', ConvergenceWarning)
                model.fit(x_train, frequency * scale, sample_weight=exposure / exposure.mean())
            if model_directory is not None:
                import joblib
                model_directory.mkdir(parents=True, exist_ok=True)
                joblib.dump({'preprocessor': prep, 'model': model, 'target_scale': scale,
                             'exposure_column': exposure_col, 'train_end_year': end_year,
                             'numeric_features': NUMERIC_FEATURES, 'categorical_features': CATEGORICAL_FEATURES,
                             'adopted_in_frontend': False}, model_directory / f'{evaluation}_{label}.joblib')
            rate = model.predict(x_test) / scale
            predicted = rate * test[exposure_col].to_numpy(float)
            if not np.isfinite(predicted).all() or (predicted <= 0).any():
                raise ValueError('Predicciones Poisson inválidas.')
            y = test.dvc_count.to_numpy(float)
            metrics.append({'model': label, 'evaluation': evaluation, 'train_end_year': end_year,
                            'target_year': target_year, 'rows': len(test), 'train_rows': len(train),
                            'MAE': float(mean_absolute_error(y, predicted)),
                            'RMSE': float(np.sqrt(mean_squared_error(y, predicted))), 'R2': float(r2_score(y, predicted)),
                            'PoissonDeviance': float(mean_poisson_deviance(y, predicted)),
                            'observed_dvc': float(y.sum()), 'predicted_dvc': float(predicted.sum()),
                            'observed_over_predicted': float(y.sum() / predicted.sum()),
                            'experiment': 'Paired retraining on common eligible sample; not historical reproduction',
                            'adopted_in_frontend': False})
            out = test[['cell', 'year', 'month', 'dvc_count', exposure_col]].copy()
            out['evaluation'] = evaluation
            out['model'] = label
            out['pred_count_experiment'] = predicted
            out['rate_per_vehicle_km_experiment'] = rate
            predictions.append(out)
    return pd.DataFrame(metrics), pd.concat(predictions, ignore_index=True)
