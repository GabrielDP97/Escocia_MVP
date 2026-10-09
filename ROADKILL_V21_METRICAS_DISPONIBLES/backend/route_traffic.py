"""AADF mean for each displayed route cell, then an equal-weight route mean.

No raw AADF is bundled. Missing, conflicting or directional records block the
corresponding cell mean rather than silently turning it into zero traffic.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import math
import pandas as pd
import numpy as np

TRAFFIC_FILE = 'route_traffic_2017.csv'
TRAFFIC_COLUMNS = ['cell','year','road_name','daily_vehicle_mean','aadf_count_points','traffic_status']
RAW_COLUMNS = ['count_point_id','year','region_name','road_name','easting','northing','all_motor_vehicles']


def find_aadf(start: Path) -> Path | None:
    for root in [start.resolve(), *start.resolve().parents]:
        path = root / 'Datos/trafico/aadf_data/dft_traffic_counts_aadf.csv'
        if path.is_file():
            return path
    return None


def aggregate_route_traffic(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if not set(RAW_COLUMNS).issubset(raw.columns):
        raise ValueError(f'Faltan columnas AADF: {sorted(set(RAW_COLUMNS) - set(raw.columns))}')
    frame=raw.loc[raw.region_name.astype(str).str.strip().eq('Scotland')].copy()
    for col in ['year','easting','northing','all_motor_vehicles','count_point_id']:
        frame[col]=pd.to_numeric(frame[col],errors='coerce')
    frame=frame[frame.year.eq(2017)].copy()
    if frame.empty:
        raise ValueError('No hay aforos AADF de Scotland para 2017.')
    frame['road_name']=frame.road_name.astype('string').str.strip().str.upper()
    xy=np.isfinite(frame.easting)&np.isfinite(frame.northing)&frame.easting.between(0,799999.999)&frame.northing.between(0,1299999.999)
    frame['cell']=pd.Series(pd.NA,index=frame.index,dtype='Int64')
    frame.loc[xy,'cell']=(np.floor(frame.loc[xy,'northing']/10000)*80+np.floor(frame.loc[xy,'easting']/10000)).astype('int64')
    valid_id=np.isfinite(frame.count_point_id)&frame.count_point_id.ge(0)&frame.count_point_id.eq(np.floor(frame.count_point_id))
    good_flow=np.isfinite(frame.all_motor_vehicles)&frame.all_motor_vehicles.ge(0)
    direction_cols=[c for c in ['direction_of_travel','direction'] if c in frame]
    directional=pd.Series(False,index=frame.index)
    for col in direction_cols:
        directional |= frame[col].notna()&frame[col].astype(str).str.strip().ne('')
    frame['blocked']=~valid_id|~good_flow|~xy|frame.road_name.isna()|frame.road_name.eq('')|directional
    fingerprint=RAW_COLUMNS+direction_cols
    duplicates=frame.duplicated(fingerprint,keep='first')
    unique=frame.loc[~duplicates].copy()
    groups=unique.loc[valid_id.loc[unique.index]].groupby('count_point_id',dropna=False).size()
    conflicts=set(groups[groups>1].index)
    unique['blocked'] |= unique.count_point_id.isin(conflicts)
    table=unique.dropna(subset=['cell','road_name']).groupby(['cell','year','road_name'],as_index=False).agg(
        daily_vehicle_mean=('all_motor_vehicles','mean'), aadf_count_points=('count_point_id','nunique'),
        blocked=('blocked','any'))
    table['traffic_status']=np.where(table.blocked,'blocked','valid')
    table.loc[table.blocked,'daily_vehicle_mean']=np.nan
    table=table[TRAFFIC_COLUMNS].sort_values(['road_name','cell']).reset_index(drop=True)
    metadata=dict(source='AADF 2017 Scotland', exact_duplicate_rows=int(duplicates.sum()),
                  conflicting_count_points=len(conflicts), invalid_coordinates_rows=int((~xy).sum()),
                  directional_rows=int(directional.sum()), exported_cell_road_rows=len(table),
                  blocked_cell_road_rows=int(table.traffic_status.eq('blocked').sum()),
                  route_mean_method='Arithmetic mean of the displayed cells; each cell is the mean of unique AADF count points of that road in 2017.',
                  complete_route_trips_observed=False,
                  limitations=['La media por celda se limita a la carretera seleccionada; los DVC de la celda pueden incluir otras vías.',
                               'La media de los puntos aproxima afluencia y no mide cuántos vehículos completan la ruta.',
                               'Una media diaria anual se mantiene igual todos los meses; el volumen mensual estimado es media por días.',
                               'Las filas sin coordenadas válidas no pueden asociarse a una celda; requieren revisión en el original.'])
    return table,metadata


def prepare_route_traffic(app_root: Path, source_path: Path | None = None) -> dict:
    source_path=source_path or find_aadf(app_root)
    if source_path is None:
        return {'status':'missing_original','message':'Falta el AADF original de 2017. El modo automático de la demo puede usar el perfil histórico 2008–2017 incluido; el modo AADF 2017 queda pendiente. Se busca Datos/trafico/aadf_data/dft_traffic_counts_aadf.csv en la aplicación y sus carpetas superiores.'}
    header=pd.read_csv(source_path,nrows=0).columns
    missing=set(RAW_COLUMNS)-set(header)
    if missing:raise ValueError(f'Faltan columnas AADF: {sorted(missing)}')
    columns=RAW_COLUMNS+[c for c in ['direction_of_travel','direction'] if c in header]
    parts=[]
    for chunk in pd.read_csv(source_path,usecols=columns,chunksize=100000):
        keep=chunk.region_name.astype(str).str.strip().eq('Scotland')&pd.to_numeric(chunk.year,errors='coerce').eq(2017)
        if keep.any():parts.append(chunk.loc[keep].copy())
    if not parts:raise ValueError('No hay registros Scotland 2017 en el AADF original.')
    table,metadata=aggregate_route_traffic(pd.concat(parts,ignore_index=True))
    digest=hashlib.sha256()
    with source_path.open('rb') as file:
        for block in iter(lambda:file.read(1024*1024),b''):digest.update(block)
    metadata.update(status='prepared',source_filename=source_path.name,source_sha256=digest.hexdigest())
    output=app_root/'data';output.mkdir(parents=True,exist_ok=True)
    # Build first; atomically replace each completed output. Never changes model predictions.
    temporary=output/(TRAFFIC_FILE+'.tmp')
    table.to_csv(temporary,index=False);temporary.replace(output/TRAFFIC_FILE)
    report=output/'route_traffic_2017_metadata.json'
    temporary=report.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(metadata,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8');temporary.replace(report)
    return metadata


def load_route_traffic(app_root: Path) -> pd.DataFrame:
    path=app_root/'data'/TRAFFIC_FILE
    if not path.is_file():
        prepare_route_traffic(app_root)
    if not path.is_file():
        return pd.DataFrame(columns=TRAFFIC_COLUMNS)
    table=pd.read_csv(path)
    if not set(TRAFFIC_COLUMNS).issubset(table.columns):
        raise ValueError('El CSV de afluencia exportado no tiene el formato esperado.')
    if table.duplicated(['cell','year','road_name']).any():
        raise ValueError('Hay duplicados en el CSV de afluencia; vuelve a exportarlo desde AADF.')
    return table


def historical_daily_mean(value):
    """Invert the documented log1p of the 2008–2017 cell traffic mean.

    This is a cell-wide historical average over available years, including all
    roads; it is not an AADF 2017 count for the selected road.
    """
    try:
        value=float(value)
        if not math.isfinite(value) or value<0:
            return None
        recovered=math.expm1(value)
        return recovered if math.isfinite(recovered) else None
    except (TypeError,ValueError,OverflowError):
        return None


def select_route_traffic(frame: pd.DataFrame, mode: str='auto', aadf_available: bool=False):
    if mode not in {'auto','aadf_2017','historical_profile'}:
        raise ValueError('Origen de afluencia no válido.')
    chosen='historical_profile' if mode=='historical_profile' or (mode=='auto' and not aadf_available) else 'aadf_2017'
    result=frame.copy()
    if chosen=='historical_profile':
        values=result['log_traffic_mean'] if 'log_traffic_mean' in result else pd.Series(None,index=result.index)
        result['daily_vehicle_mean']=values.map(historical_daily_mean)
    else:
        values=result['aadf_daily_vehicle_mean'] if 'aadf_daily_vehicle_mean' in result else pd.Series(None,index=result.index)
        status=result['traffic_status'] if 'traffic_status' in result else pd.Series('missing',index=result.index)
        result['daily_vehicle_mean']=values.where(status.eq('valid'))
    return result,chosen
