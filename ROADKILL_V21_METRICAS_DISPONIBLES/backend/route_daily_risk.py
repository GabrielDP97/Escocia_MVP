"""Experimental route-level count / days / common daily-flow scenario.

Daily flow defaults to the arithmetic mean of route-point AADF values; counts cannot identify
vehicles completing the entire route. Cell totals may include other roads.
"""
from __future__ import annotations

import calendar
from datetime import date
import math
from typing import Any

from backend.trip_risk import cell_for_xy, segment_cell_lengths


def estimate_route_daily_risk(
    points: list[dict[str, Any]], month: int, travel_date: str | None = None,
    daily_route_vehicles: float | None = None, distance_km: float | None = None,
    traffic_basis: str = "aadf_2017",
) -> dict[str, Any]:
    selected_date = date.fromisoformat(travel_date) if travel_date else date(2017, month, 15)
    if selected_date.year != 2017 or selected_date.month != month:
        raise ValueError('La fecha debe pertenecer al mes seleccionado de 2017.')
    if daily_route_vehicles is not None and (not math.isfinite(daily_route_vehicles) or daily_route_vehicles <= 0):
        raise ValueError('La afluencia diaria de la ruta debe ser un número finito mayor que cero.')
    if distance_km is not None and (not math.isfinite(distance_km) or distance_km <= 0):
        raise ValueError('La distancia debe ser un número finito mayor que cero.')
    if traffic_basis not in {"aadf_2017", "historical_profile"}:
        raise ValueError("Origen de afluencia no válido.")
    historical = traffic_basis == "historical_profile"
    traffic_note = ("Perfil histórico 2008–2017 · todas las vías de cada celda; aproximación para la demo."
                    if historical else "AADF 2017 · aforos de la carretera seleccionada por celda.")
    days = calendar.monthrange(selected_date.year, month)[1]
    result = {
        'status': 'unavailable', 'experimental': True, 'validated_individual_probability': False,
        'scope': 'available_cells_only', 'travel_date': selected_date.isoformat(),
        'reference_year': 2017, 'reference_month': month, 'temporal_resolution': 'monthly',
        'days_in_month': days, 'monthly_expected_dvc': None, 'daily_expected_dvc': None,
        'daily_route_vehicles': daily_route_vehicles, 'traffic_source': 'user_scenario' if daily_route_vehicles is not None else 'missing',
        'monthly_vehicle_passes': None, 'events_per_vehicle_pass': None,
        'traffic_basis': traffic_basis, 'traffic_period': [2008,2017] if historical else [2017,2017],
        'traffic_road_specific': not historical, 'traffic_note': traffic_note,
        'automatic_daily_route_vehicles': None, 'traffic_points_used': 0, 'missing_traffic_cells': [],
        'probability_approx': None, 'full_route_probability': None,
        'available_cells': [], 'missing_count_cells': [], 'duplicate_rows_ignored': 0,
        'coverage_fraction': None, 'unknown_geometry_cells': [], 'geometry_status': 'unavailable',
        'covered_distance_km': None, 'uncovered_distance_km': None,
        'formula': 'A = sum(DVC_esperados_mes_por_celda_unica); tasa = A / dias_mes / vehiculos_diarios_ruta; porcentaje_aproximado = 100 * tasa',
        'assumptions': [
            'La afluencia diaria común se aproxima con la media aritmética de los valores diarios de los puntos de la ruta, sin ponderar por longitud.',
            traffic_note,
            'El perfil histórico se recupera con expm1(log_traffic_mean), inversa del log1p documentado en el notebook de clustering. No reconstruye aforos de 2017.',
            'Este promedio no identifica los vehículos que completan la ruta y no verifica su correspondencia con los incidentes.',
            'Accidentes y tráfico se suponen referidos a los mismos recorridos; esta correspondencia no está verificada.',
            'Los DVC son conteos mensuales esperados del Poisson, no las probabilidades mensuales del Random Forest.',
            'Los conteos pertenecen a celdas de 10 x 10 km y pueden incluir otras carreteras; cada celda se suma una sola vez.',
            'Riesgo y tráfico uniformes dentro del mes; la fecha no aporta información diaria adicional.',
            'Solo se acumulan celdas disponibles; los huecos quedan sin evaluar, no con riesgo cero.',
            'El cociente es una tasa media por paso de vehículo y solo aproxima una probabilidad para eventos raros.',
            'La cobertura geométrica corresponde a la polilínea de la demo, no a la carretera real.',
        ],
    }
    if not points:
        result['reason'] = 'No hay puntos disponibles para acumular DVC.'
        return result
    unique = {}
    for point in points:
        try:
            raw_cell = float(point['cell'])
            if not math.isfinite(raw_cell) or raw_cell != math.floor(raw_cell) or raw_cell < 0:
                raise ValueError()
            cell = int(raw_cell)
        except (KeyError, TypeError, ValueError, OverflowError):
            result['reason'] = 'Hay puntos sin identificador de celda válido; no se puede evitar doble conteo.'
            return result
        try:
            count = float(point['pred_count_final'])
            if not math.isfinite(count) or count < 0:
                count = None
        except (KeyError, TypeError, ValueError, OverflowError):
            count = None
        if cell in unique:
            if unique[cell]['count'] != count:
                result['reason'] = 'Hay conteos contradictorios para una misma celda; el acumulado no está disponible.'
                return result
            result['duplicate_rows_ignored'] += 1
        else:
            unique[cell] = {'count': count, 'point': point}
    traffic_values = []
    for cell, entry in unique.items():
        try:
            flow = float(entry['point']['daily_vehicle_mean'])
            if not math.isfinite(flow) or flow < 0:
                raise ValueError()
        except (KeyError, TypeError, ValueError, OverflowError):
            result['missing_traffic_cells'].append(cell)
        else:
            traffic_values.append(flow)
    result['traffic_points_used'] = len(traffic_values)
    if traffic_values and not result['missing_traffic_cells']:
        result['automatic_daily_route_vehicles'] = math.fsum(traffic_values) / len(traffic_values)
    if daily_route_vehicles is None and result['automatic_daily_route_vehicles'] is not None:
        daily_route_vehicles = result['automatic_daily_route_vehicles']
        result.update(daily_route_vehicles=daily_route_vehicles, traffic_source='mean_route_points')
    known = {cell: entry['count'] for cell, entry in unique.items() if entry['count'] is not None}
    result['available_cells'] = sorted(known)
    result['missing_count_cells'] = sorted(set(unique) - set(known))
    if not known:
        result['reason'] = 'No hay conteos mensuales válidos; no se interpretan los valores ausentes como cero.'
        return result
    monthly = math.fsum(known.values())
    result.update(monthly_expected_dvc=monthly, daily_expected_dvc=monthly / days)

    # Coverage is calculated using count availability, independently of the old vehicle-km proxy.
    locations = []
    try:
        for cell, entry in unique.items():
            point = entry['point']
            x, y = float(point['easting']), float(point['northing'])
            if not (math.isfinite(x) and math.isfinite(y) and 0 <= x < 800000 and 0 <= y < 1300000 and cell_for_xy(x, y) == cell):
                raise ValueError()
            locations.append((x, y))
        pieces = [piece for a, b in zip(locations, locations[1:]) for piece in segment_cell_lengths(a, b)]
        distance = math.fsum(length for _, length in pieces)
        if distance > 0:
            covered = math.fsum(length for cell, length in pieces if cell in known)
            scale = 1 if distance_km is None else distance_km / distance
            result.update(coverage_fraction=covered / distance,
                          covered_distance_km=covered * scale,
                          uncovered_distance_km=(distance - covered) * scale,
                          unknown_geometry_cells=sorted({cell for cell, _ in pieces if cell not in known}),
                          geometry_status='complete_demo' if covered >= distance - 1e-9 else 'partial_demo')
    except (KeyError, TypeError, ValueError, OverflowError):
        pass  # Unknown geometry never turns into verified full-route coverage.

    if daily_route_vehicles is None:
        result.update(status='needs_traffic', reason='Falta afluencia válida en uno o más puntos para el origen seleccionado. No se calcula una media incompleta. Puedes usar el perfil histórico de la demo o preparar los aforos AADF 2017.')
        return result
    if daily_route_vehicles <= 0:
        result.update(status='zero_traffic', reason='La media de tráfico es cero; no se puede dividir entre cero ni estimar la probabilidad.')
        return result
    monthly_passes = days * daily_route_vehicles
    rate = monthly / days / daily_route_vehicles
    if not math.isfinite(rate) or not math.isfinite(monthly_passes):
        result['reason'] = 'El escenario no produce una tasa y un volumen de tráfico finitos.'
        return result
    result.update(monthly_vehicle_passes=monthly_passes, events_per_vehicle_pass=rate)
    if rate > 1:
        result.update(status='incompatible_traffic', reason='La tasa supera un atropello por paso de vehículo; no se muestra como probabilidad. Revisa la afluencia y la correspondencia de los conteos.')
        return result
    result.update(status='scenario_estimated', probability_approx=rate,
                  reason='Estimación media para una pasada usando la media de los puntos de la ruta.' if result['traffic_source'] == 'mean_route_points' else 'Escenario con afluencia alternativa introducida. El resultado solo acumula celdas disponibles y no valida el riesgo de la ruta completa.')
    return result
