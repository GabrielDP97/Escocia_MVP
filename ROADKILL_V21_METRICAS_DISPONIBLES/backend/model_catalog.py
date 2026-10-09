from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def get_model_catalog():
    return json.loads((Path(__file__).resolve().parents[1] / 'data/model_comparison_catalog.json').read_text(encoding='utf-8'))
