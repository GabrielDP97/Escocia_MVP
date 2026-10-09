"""Experimental DVC risk restricted to observed 10 x 10 km BNG cells.

The synthetic polyline is clipped to the available cells. Unknown stretches
receive no rate and no probability; they never receive an assumed zero rate.
"""
from __future__ import annotations

from datetime import date
import math
from typing import Any

CELL_M = 10_000
GRID_COLUMNS = 80


def cell_for_xy(x: float, y: float) -> int:
    return math.floor(y / CELL_M) * GRID_COLUMNS + math.floor(x / CELL_M)


def segment_cell_lengths(a: tuple[float, float], b: tuple[float, float]) -> list[tuple[int, float]]:
    """Split a straight BNG segment at grid borders; return (cell, km)."""
    length_km = math.hypot(b[0] - a[0], b[1] - a[1]) / 1000
    if length_km == 0:
        return []
    cuts = {0.0, 1.0}
    for start, end in zip(a, b):
        if end == start:
            continue
        first = math.floor(min(start, end) / CELL_M) + 1
        last = math.ceil(max(start, end) / CELL_M)
        for border_index in range(first, last):
            fraction = (border_index * CELL_M - start) / (end - start)
            if 0 < fraction < 1:
                cuts.add(fraction)
    cuts = sorted(cuts)
    pieces = []
    for begin, end in zip(cuts, cuts[1:]):
        midpoint = (begin + end) / 2
        x = a[0] + midpoint * (b[0] - a[0])
        y = a[1] + midpoint * (b[1] - a[1])
        pieces.append((cell_for_xy(x, y), length_km * (end - begin)))
    return pieces


def estimate_trip_risk(
    points: list[dict[str, Any]],
    month: int,
    travel_date: str | None = None,
    distance_km: float | None = None,
) -> dict[str, Any]:
    selected_date = date.fromisoformat(travel_date) if travel_date else date(2017, month, 15)
    if selected_date.year != 2017 or selected_date.month != month:
        raise ValueError("La fecha debe pertenecer al mes seleccionado de 2017; no hay predicciones para otros años.")
    if distance_km is not None and (not math.isfinite(distance_km) or distance_km <= 0):
        raise ValueError("La distancia debe ser un número finito mayor que cero.")

    result: dict[str, Any] = {
        "status": "unavailable", "experimental": True,
        "travel_date": selected_date.isoformat(), "reference_year": 2017,
        "reference_month": month, "probability": None, "scope": "covered_cells_only",
        "full_route_probability": None, "expected_events_per_trip": None,
        "expected_events_covered": None, "distance_km": None,
        "covered_distance_km": None, "uncovered_distance_km": None,
        "coverage_fraction": None, "unknown_cells": [],
        "demo_distance_km": None,
        "distance_source": "user_scenario" if distance_km is not None else "demo_polyline",
        "nonadjacent_segments": 0,
        "method": "Monthly count / vehicle-km proxy; clip polyline to known BNG cells; 1-exp(-covered hazard)",
        "temporal_resolution": "monthly", "target": "recorded_deer_vehicle_collision",
        "formula": "r_i = DVC_esperados_i / vehiculos_km_i; H_datos = sum(km_dentro_celda_i * r_i); p_datos = 1-exp(-H_datos)",
        "assumptions": [
            "Cada punto representa una celda BNG de 10 x 10 km, no un radio de 10 km.",
            "Solo se aplica una tasa a la distancia dentro de celdas disponibles con recuento y exposición válidos.",
            "Las zonas sin datos quedan sin evaluar; no se interpola ni se asigna riesgo cero a los huecos.",
            "Conductor representativo; tasas homogéneas en cada celda y mes; sin validación individual.",
            "La polilínea une puntos con líneas rectas y no representa el asfalto real; la cobertura es de esa geometría.",
            "La acumulación usa Poisson. No se corrige subregistro ni el carácter aproximado de la exposición.",
            "Una distancia introducida escala la polilínea conservando su reparto entre zonas cubiertas y desconocidas.",
        ],
    }
    if len(points) < 2:
        result["reason"] = "Se necesitan al menos dos puntos para representar la geometría de un trayecto."
        return result

    locations: list[tuple[float, float]] = []
    rates: dict[int, float] = {}
    cells: list[int] = []
    for point in points:
        try:
            x, y = float(point["easting"]), float(point["northing"])
            cell = int(point["cell"])
        except (KeyError, TypeError, ValueError, OverflowError):
            result["reason"] = "Faltan coordenadas o identificadores válidos para delimitar las zonas."
            return result
        if not all(math.isfinite(v) for v in (x, y)) or not (0 <= x < 800_000 and 0 <= y < 1_300_000):
            result["reason"] = "Hay coordenadas fuera de la cuadrícula; no se puede delimitar la cobertura."
            return result
        if cell_for_xy(x, y) != cell or cell in cells:
            result["reason"] = "Hay celdas duplicadas o coordenadas incompatibles con su celda BNG."
            return result
        locations.append((x, y))
        cells.append(cell)
        try:
            count = float(point["pred_count_final"])
            exposure = float(point["exposure_vkm_proxy"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue  # Geometry exists, but its rate is unknown.
        if math.isfinite(count) and math.isfinite(exposure) and count >= 0 and exposure > 0:
            rate = count / exposure
            if math.isfinite(rate):
                rates[cell] = rate

    pieces = [piece for a, b in zip(locations, locations[1:]) for piece in segment_cell_lengths(a, b)]
    demo_distance = math.fsum(length for _, length in pieces)
    if not math.isfinite(demo_distance) or demo_distance <= 0:
        result["reason"] = "Los puntos no representan un trayecto de longitud positiva."
        return result
    used_distance = demo_distance if distance_km is None else distance_km
    scale = used_distance / demo_distance
    covered = math.fsum(length * scale for cell, length in pieces if cell in rates)
    unknown = math.fsum(length * scale for cell, length in pieces if cell not in rates)
    hazard = math.fsum(length * scale * rates[cell] for cell, length in pieces if cell in rates)
    if not math.isfinite(hazard):
        result["reason"] = "La combinación de recuentos y exposición no produce una tasa finita."
        return result
    complete = unknown <= max(1e-10, used_distance * 1e-12)
    probability = -math.expm1(-hazard) if covered > 0 else None
    result.update({
        "status": ("estimated" if complete else "partial") if covered > 0 else "unavailable",
        "probability": probability,
        "full_route_probability": probability if complete else None,
        "expected_events_per_trip": hazard if complete else None,
        "expected_events_covered": hazard if covered > 0 else None,
        "distance_km": used_distance, "demo_distance_km": demo_distance,
        "covered_distance_km": covered, "uncovered_distance_km": unknown,
        "coverage_fraction": covered / used_distance,
        "unknown_cells": sorted({cell for cell, _ in pieces if cell not in rates}),
        "points_used": len(points),
        "nonadjacent_segments": sum(
            max(abs(a % GRID_COLUMNS - b % GRID_COLUMNS), abs(a // GRID_COLUMNS - b // GRID_COLUMNS)) > 1
            for a, b in zip(cells, cells[1:])
        ),
    })
    if not complete:
        result["reason"] = "El porcentaje solo corresponde a zonas con datos. La probabilidad de toda la ruta queda sin estimar."
    return result
