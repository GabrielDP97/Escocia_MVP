from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any


def solar_context(lat: float, lon: float, timestamp_iso: str, timezone: str = "Europe/London") -> dict[str, Any]:
    """Calcula la ventana crepuscular del documento con astral.

    La ventana activa es [-60 min, +120 min] alrededor del ocaso. Se mantiene
    separada del score histórico porque los artefactos 2017 del ZIP no incluyen
    timestamps horarios por observación.
    """
    try:
        from astral import Observer
        from astral.sun import sun
    except Exception as exc:  # pragma: no cover - depende del entorno instalado
        raise RuntimeError("astral no está instalado; ejecuta pip install -r requirements.txt") from exc

    tz = ZoneInfo(timezone)
    ts = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=tz)
    ts = ts.astimezone(tz)

    observer = Observer(latitude=float(lat), longitude=float(lon))
    values = sun(observer, date=ts.date(), tzinfo=tz)
    sunset = values["sunset"]
    start = sunset - timedelta(minutes=60)
    end = sunset + timedelta(minutes=120)
    delta_minutes = (ts - sunset).total_seconds() / 60.0
    return {
        "timestamp": ts.isoformat(),
        "sunset": sunset.isoformat(),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "delta_to_sunset_minutes": float(delta_minutes),
        "active_twilight_window": bool(start <= ts <= end),
        "window_definition": "[-60 min, +120 min] respecto al ocaso astronómico",
        "timezone": timezone,
    }
