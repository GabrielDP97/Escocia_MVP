from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = BASE_DIR / "data" / "reto07_nlp_metrics.json"

@lru_cache(maxsize=1)
def get_reto7_nlp_metrics() -> dict[str, Any]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"No se encontró el artefacto del Reto 07: {DATA_FILE}")
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))
