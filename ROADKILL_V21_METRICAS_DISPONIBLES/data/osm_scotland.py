# -*- coding: utf-8 -*-
"""Módulo de Integración con OpenStreetMap (OSM) y Triaje de Siniestralidad Vial para Escocia / UK.

Proporciona soporte Online (Overpass API) y Offline (Caché local + Fallback heurístico),
junto con la base de datos de triaje empírico de 16.383 siniestros DVC en carreteras escocesas
(especies dominantes, severidad actuarial, picos estacionales y atributos físicos viales).
"""

from __future__ import annotations
import os
import json
import math
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd
import numpy as np

# Bounding box aproximado de Escocia
SCOTLAND_BBOX = {
    "south": 54.6,
    "west": -8.7,
    "north": 60.9,
    "east": -0.7
}

# Servidores públicos Overpass con rotación de fallback
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
]

# Base de datos empírica de Triaje de Carreteras en Escocia (DVC Scotland + DfT)
SCOTLAND_ROAD_TRIAGE: Dict[str, Dict[str, Any]] = {
    # --- NIVEL 1: ALERTA ROJA (Highlands & Ciervo Rojo / Máxima Severidad) ---
    "A9": {
        "triage_level": "NIVEL 1 - ALERTA ROJA",
        "category_name": "Corredor Troncal Highlands Central",
        "dominant_species": "Ciervo Rojo (Red Deer) y Corzo",
        "severity_risk": "CRÍTICA (Siniestro Total ADAS / Riesgo Lesiones)",
        "dvc_count": 1344,
        "peak_months": [5, 6, 10, 11],
        "primary_region": "Highland / Perthshire",
        "highway": "trunk",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Eje Perth-Inverness-Thurso. Gran masa de Ciervo Rojo cruzando en pasos de montaña."
    },
    "A82": {
        "triage_level": "NIVEL 1 - ALERTA ROJA",
        "category_name": "Corredor Glencoe / Loch Ness",
        "dominant_species": "Ciervo Rojo (Red Deer)",
        "severity_risk": "CRÍTICA (Impactos de alta masa corporal hasta 200 kg)",
        "dvc_count": 650,
        "peak_months": [1, 5, 6, 11, 12],
        "primary_region": "Highland",
        "highway": "primary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Vía sinuosa entre valles y lagos, sin iluminación, densas masas de bosque pegadas a la calzada."
    },
    "A85": {
        "triage_level": "NIVEL 1 - ALERTA ROJA",
        "category_name": "Corredor Perth - Oban",
        "dominant_species": "Ciervo Rojo y Corzo",
        "severity_risk": "ALTA",
        "dvc_count": 290,
        "peak_months": [4, 5, 10],
        "primary_region": "Perth and Kinross / Argyll",
        "highway": "primary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Paso este-oeste montañoso con forrajeo activo en cunetas."
    },
    "A835": {
        "triage_level": "NIVEL 1 - ALERTA ROJA",
        "category_name": "Corredor Ullapool / Highlands Norte",
        "dominant_species": "Ciervo Rojo (Red Deer)",
        "severity_risk": "CRÍTICA (75+ casos verificados de Ciervo Rojo)",
        "dvc_count": 249,
        "peak_months": [10, 11, 12, 1],
        "primary_region": "Highland",
        "highway": "trunk",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Vía rápida remota, altísima vulnerabilidad en invierno por bajada de manadas a la calzada."
    },
    "A83": {
        "triage_level": "NIVEL 1 - ALERTA ROJA",
        "category_name": "Paso Rest and Be Thankful",
        "dominant_species": "Ciervo Rojo y Sika",
        "severity_risk": "ALTA",
        "dvc_count": 180,
        "peak_months": [5, 6, 12],
        "primary_region": "Argyll and Bute",
        "highway": "primary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Ruta escarpada con nieblas frecuentes y visibilidad reducida."
    },
    "A87": {
        "triage_level": "NIVEL 1 - ALERTA ROJA",
        "category_name": "Acceso a Isle of Skye (Kyle of Lochalsh)",
        "dominant_species": "Ciervo Rojo (Red Deer)",
        "severity_risk": "CRÍTICA (50+ casos de Ciervo Rojo)",
        "dvc_count": 105,
        "peak_months": [4, 6, 11],
        "primary_region": "Highland",
        "highway": "primary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Carretera solitaria de alta velocidad en invierno, cruces repentinos de manadas."
    },
    "A887": {
        "triage_level": "NIVEL 1 - ALERTA ROJA",
        "category_name": "Enlace Glenmoriston - Skye",
        "dominant_species": "Ciervo Rojo (Red Deer)",
        "severity_risk": "ALTA",
        "dvc_count": 51,
        "peak_months": [5, 10, 11],
        "primary_region": "Highland",
        "highway": "trunk",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Corredor forestal angosto."
    },

    # --- NIVEL 2: ALERTA NARANJA (Este y Noreste / Alta Frecuencia & Corzo) ---
    "A90": {
        "triage_level": "NIVEL 2 - ALERTA NARANJA",
        "category_name": "Autovía Oriental Dundee - Aberdeen",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "ALTA (Por velocidad de 70 mph)",
        "dvc_count": 579,
        "peak_months": [5, 6, 7],
        "primary_region": "Angus / Aberdeenshire",
        "highway": "trunk",
        "maxspeed_mph": 70,
        "is_lit": False,
        "lanes": 4,
        "forest_within_200m": True,
        "description": "Dual carriageway con alto flujo. Saltos rápidos de corzos desde franjas de cultivo."
    },
    "A92": {
        "triage_level": "NIVEL 2 - ALERTA NARANJA",
        "category_name": "Arteria Costera Fife - Dundee",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MEDIA-ALTA",
        "dvc_count": 395,
        "peak_months": [4, 5, 6],
        "primary_region": "Fife",
        "highway": "primary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Intenso tráfico pendular periurbano en horas crepusculares."
    },
    "A1": {
        "triage_level": "NIVEL 2 - ALERTA NARANJA",
        "category_name": "Corredor Sur East Lothian - Borders",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MEDIA-ALTA",
        "dvc_count": 337,
        "peak_months": [4, 5, 6],
        "primary_region": "East Lothian",
        "highway": "trunk",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Conexión con Inglaterra a través de mosaicos agroforestales."
    },
    "A96": {
        "triage_level": "NIVEL 2 - ALERTA NARANJA",
        "category_name": "Eje Aberdeen - Inverness",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "ALTA (43+ casos de Corzo)",
        "dvc_count": 233,
        "peak_months": [5, 6, 7],
        "primary_region": "Aberdeenshire / Moray",
        "highway": "trunk",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Carretera interurbana de un solo carril flanqueada por setos y pinares."
    },
    "A75": {
        "triage_level": "NIVEL 2 - ALERTA NARANJA",
        "category_name": "Corredor Stranraer / Ferry Link",
        "dominant_species": "Corzo y Ciervo Rojo",
        "severity_risk": "ALTA",
        "dvc_count": 210,
        "peak_months": [5, 6, 8],
        "primary_region": "Dumfries and Galloway",
        "highway": "trunk",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Tráfico pesado continuo hacia terminales portuarias cruzando Galloway Forest."
    },
    "A78": {
        "triage_level": "NIVEL 2 - ALERTA NARANJA",
        "category_name": "Carretera Costera Ayrshire",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MEDIA-ALTA",
        "dvc_count": 188,
        "peak_months": [5, 6, 12],
        "primary_region": "North Ayrshire",
        "highway": "primary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Vía rápida con taludes de vegetación densa."
    },
    "A77": {
        "triage_level": "NIVEL 2 - ALERTA NARANJA",
        "category_name": "Eje Glasgow - Ayr - Stranraer",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MEDIA-ALTA",
        "dvc_count": 173,
        "peak_months": [4, 5, 6],
        "primary_region": "South Ayrshire",
        "highway": "trunk",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Tramos rurales oscuros con límites de 60 mph."
    },
    "A701": {
        "triage_level": "NIVEL 2 - ALERTA NARANJA",
        "category_name": "Eje Dumfries - Edinburgh",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "ALTA",
        "dvc_count": 152,
        "peak_months": [3, 10, 11],
        "primary_region": "Dumfries and Galloway",
        "highway": "primary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Cruce de las colinas de Southern Uplands, fuerte pico en celo de otoño."
    },

    # --- NIVEL 3: ALERTA AMARILLA (Carreteras Secundarias B-Roads Críticas) ---
    "B979": {
        "triage_level": "NIVEL 3 - ALERTA AMARILLA",
        "category_name": "B-Road Periurbana de Aberdeen (Blackburn-Stonehaven)",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MEDIA (Poco tiempo de reacción por calzada estrecha)",
        "dvc_count": 21,
        "peak_months": [5, 10, 11],
        "primary_region": "Aberdeenshire",
        "highway": "secondary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Vía secundaria sin farolas, curvas ciegas y árboles a borde de asfalto."
    },
    "B9157": {
        "triage_level": "NIVEL 3 - ALERTA AMARILLA",
        "category_name": "Conector Rural Kirkcaldy",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MEDIA",
        "dvc_count": 14,
        "peak_months": [1, 5, 10],
        "primary_region": "Fife",
        "highway": "secondary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Sin arcén, visibilidad reducida."
    },
    "B977": {
        "triage_level": "NIVEL 3 - ALERTA AMARILLA",
        "category_name": "Corredor Forestal Kintore",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MEDIA",
        "dvc_count": 13,
        "peak_months": [7, 9, 12],
        "primary_region": "Aberdeenshire",
        "highway": "secondary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Pasa junto a bosques de producción maderera."
    },
    "B9077": {
        "triage_level": "NIVEL 3 - ALERTA AMARILLA",
        "category_name": "Ruta Sur Deeside",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MEDIA",
        "dvc_count": 11,
        "peak_months": [1, 5, 10],
        "primary_region": "Aberdeenshire",
        "highway": "secondary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Márgenes del río Dee, forrajeo en cunetas al amanecer."
    },
    "B993": {
        "triage_level": "NIVEL 3 - ALERTA AMARILLA",
        "category_name": "Enlace Inverurie - Torphins",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MEDIA",
        "dvc_count": 11,
        "peak_months": [5, 6, 8],
        "primary_region": "Aberdeenshire",
        "highway": "secondary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 2,
        "forest_within_200m": True,
        "description": "Carretera estrecha rural con setos altos."
    },
    "B862": {
        "triage_level": "NIVEL 3 - ALERTA AMARILLA",
        "category_name": "Ruta Este de Loch Ness (Fort Augustus)",
        "dominant_species": "Ciervo Rojo y Sika",
        "severity_risk": "ALTA (Calzada de carril único con passing places)",
        "dvc_count": 10,
        "peak_months": [1, 6, 8],
        "primary_region": "Highland",
        "highway": "secondary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 1,
        "forest_within_200m": True,
        "description": "Vía de un solo carril, tramos salvajes sin farolas."
    },
    "B852": {
        "triage_level": "NIVEL 3 - ALERTA AMARILLA",
        "category_name": "Ruta Dores - Foyers (Loch Ness)",
        "dominant_species": "Sika Deer y Ciervo Rojo",
        "severity_risk": "ALTA (Presencia de Ciervo Sika)",
        "dvc_count": 8,
        "peak_months": [2, 3, 12],
        "primary_region": "Highland",
        "highway": "secondary",
        "maxspeed_mph": 60,
        "is_lit": False,
        "lanes": 1,
        "forest_within_200m": True,
        "description": "Masa de coníferas pegada al arcén."
    },

    # --- NIVEL 4: ALERTA AZUL (Autopistas M / Alto Flujo con Vallado Parcial) ---
    "M90": {
        "triage_level": "NIVEL 4 - ALERTA AZUL",
        "category_name": "Autopista Perth - Edinburgh",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MODERADA",
        "dvc_count": 334,
        "peak_months": [5, 6, 7],
        "primary_region": "Perth and Kinross / Fife",
        "highway": "motorway",
        "maxspeed_mph": 70,
        "is_lit": False,
        "lanes": 4,
        "forest_within_200m": True,
        "description": "Pasa junto a Loch Leven; colisiones en enlaces y desmontes boscosos."
    },
    "M8": {
        "triage_level": "NIVEL 4 - ALERTA AZUL",
        "category_name": "Autopista Central Glasgow - Edinburgh",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MODERADA",
        "dvc_count": 287,
        "peak_months": [5, 6, 7],
        "primary_region": "Glasgow / Lanarkshire / Lothian",
        "highway": "motorway",
        "maxspeed_mph": 70,
        "is_lit": True,
        "lanes": 6,
        "forest_within_200m": False,
        "description": "Vía muy iluminada; siniestros concentrados en enlaces periurbanos."
    },
    "M9": {
        "triage_level": "NIVEL 4 - ALERTA AZUL",
        "category_name": "Autopista Edinburgh - Stirling",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MODERADA",
        "dvc_count": 268,
        "peak_months": [4, 5, 6],
        "primary_region": "Stirling / Falkirk",
        "highway": "motorway",
        "maxspeed_mph": 70,
        "is_lit": True,
        "lanes": 4,
        "forest_within_200m": False,
        "description": "Cruces esporádicos en taludes vegetales."
    },
    "M74": {
        "triage_level": "NIVEL 4 - ALERTA AZUL",
        "category_name": "Autopista Sur hacia frontera inglesa",
        "dominant_species": "Corzo (Roe Deer)",
        "severity_risk": "MODERADA",
        "dvc_count": 263,
        "peak_months": [1, 5, 6],
        "primary_region": "South Lanarkshire / Dumfries",
        "highway": "motorway",
        "maxspeed_mph": 70,
        "is_lit": False,
        "lanes": 6,
        "forest_within_200m": True,
        "description": "Tramos abiertos de alta velocidad."
    }
}


class OSMScotlandService:
    """Servicio híbrido (Online/Offline) de consulta, triaje y enriquecimiento vial con OpenStreetMap."""

    def __init__(
        self,
        mode: str = "auto",
        cache_dir: Optional[Union[str, Path]] = None,
        timeout: int = 25,
        verbose: bool = True
    ):
        """Inicializa el servicio OSM con catálogo de triaje escocés."""
        self.mode = mode.lower()
        self.timeout = timeout
        self.verbose = verbose

        if cache_dir is None:
            raiz = Path(__file__).resolve().parents[2]
            self.cache_dir = raiz / "Datos" / "entorno" / "osm_cache"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "osm_roads_cache.json"
        self.local_cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Carga la caché local desde disco."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                if self.verbose:
                    print(f"[OSM Cache] Aviso al leer caché: {e}")
        return {}

    def _save_cache(self) -> None:
        """Persiste la caché en disco."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.local_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.verbose:
                print(f"[OSM Cache] No se pudo guardar caché: {e}")

    def _query_overpass(self, query: str) -> Optional[Dict[str, Any]]:
        """Ejecuta una consulta Overpass QL con rotación de servidores."""
        data = urllib.parse.urlencode({"data": query}).encode("utf-8")
        headers = {"User-Agent": "RoadkillUK-PredictiveModel/1.0 (Research)"}

        for endpoint in OVERPASS_ENDPOINTS:
            try:
                req = urllib.request.Request(endpoint, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        content = resp.read().decode("utf-8")
                        return json.loads(content)
            except Exception:
                continue
        return None

    def get_road_triage(self, road_name: str) -> Dict[str, Any]:
        """Obtiene la clasificación de triaje empírico y severidad biológica de una carretera en Escocia.

        Args:
            road_name: Nombre o código de la vía (ej. 'A82', 'A9', 'B979', 'M8').

        Returns:
            Diccionario con nivel de alerta, especie dominante, severidad y estadísticas.
        """
        clean_road = str(road_name).strip().upper()
        if clean_road in SCOTLAND_ROAD_TRIAGE:
            res = SCOTLAND_ROAD_TRIAGE[clean_road].copy()
            res["road_name"] = clean_road
            res["in_triage_db"] = True
            return res

        # Heurística para vías no catalogadas explícitamente
        is_m = clean_road.startswith("M")
        is_a = clean_road.startswith("A")
        is_b = clean_road.startswith("B")

        if is_m:
            level = "NIVEL 4 - ALERTA AZUL"
            desc = "Autopista no catalogada de flujo rápido."
            severity = "MODERADA"
            species = "Corzo (Roe Deer)"
            peaks = [5, 6, 7]
        elif is_a:
            level = "NIVEL 2 - ALERTA NARANJA"
            desc = "Carretera principal 'A' comarcal."
            severity = "MEDIA-ALTA"
            species = "Corzo / Ciervo Rojo"
            peaks = [5, 6, 10, 11]
        elif is_b:
            level = "NIVEL 3 - ALERTA AMARILLA"
            desc = "Carretera secundaria 'B' rural."
            severity = "MEDIA (Calzada estrecha sin farolas)"
            species = "Corzo (Roe Deer)"
            peaks = [5, 6, 10]
        else:
            level = "NIVEL 3 - ALERTA AMARILLA"
            desc = "Vía rural menor / Carretera C o U."
            severity = "LEVE-MEDIA"
            species = "Corzo (Roe Deer)"
            peaks = [5, 6]

        return {
            "road_name": clean_road,
            "triage_level": level,
            "category_name": desc,
            "dominant_species": species,
            "severity_risk": severity,
            "dvc_count": 0,
            "peak_months": peaks,
            "primary_region": "Scotland",
            "highway": "motorway" if is_m else ("primary" if is_a else "secondary"),
            "maxspeed_mph": 70 if is_m else 60,
            "is_lit": is_m,
            "lanes": 4 if is_m else 2,
            "forest_within_200m": not is_m,
            "in_triage_db": False
        }

    def get_road_attributes(
        self,
        road_name: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """Obtiene atributos de una carretera combinando Triaje y OpenStreetMap."""
        clean_road = str(road_name).strip().upper()
        cache_key = f"{clean_road}_{round(lat, 3) if lat else 'all'}_{round(lon, 3) if lon else 'all'}"

        # 1. Comprobar caché local
        if cache_key in self.local_cache:
            res = self.local_cache[cache_key].copy()
            res["source"] = "local_cache"
            return res

        # 2. Si el modo es online o auto, consultar Overpass API
        if self.mode in ["online", "auto"]:
            query_filter = f'["ref"="{clean_road}"]' if clean_road.startswith(("A", "B", "M")) else f'["name"~"{clean_road}",i]'
            if lat is not None and lon is not None:
                spatial_filter = f"(around:1500,{lat},{lon})"
            else:
                spatial_filter = f"({SCOTLAND_BBOX['south']},{SCOTLAND_BBOX['west']},{SCOTLAND_BBOX['north']},{SCOTLAND_BBOX['east']})"

            query = f"""
            [out:json][timeout:{self.timeout}];
            (
              way["highway"]{query_filter}{spatial_filter};
            );
            out tags 20;
            """
            data = self._query_overpass(query)
            if data and "elements" in data and len(data["elements"]) > 0:
                elements = data["elements"]
                tags_list = [el.get("tags", {}) for el in elements]
                
                maxspeeds = [t.get("maxspeed") for t in tags_list if "maxspeed" in t]
                maxspeed_val = 60
                if maxspeeds:
                    first_spd = str(maxspeeds[0]).lower().replace("mph", "").strip()
                    try:
                        maxspeed_val = int(first_spd)
                    except ValueError:
                        pass

                lit_tags = [t.get("lit", "").lower() for t in tags_list if "lit" in t]
                is_lit = any(l in ["yes", "24/7", "dusk-dawn", "operating"] for l in lit_tags)

                hw_types = [t.get("highway") for t in tags_list if "highway" in t]
                hw_type = hw_types[0] if hw_types else "primary"
                lanes_list = [int(t.get("lanes")) for t in tags_list if "lanes" in t and str(t.get("lanes")).isdigit()]
                lanes_val = max(lanes_list) if lanes_list else (4 if clean_road.startswith("M") else 2)

                triage_info = self.get_road_triage(clean_road)

                res = {
                    "road_name": clean_road,
                    "triage_level": triage_info["triage_level"],
                    "dominant_species": triage_info["dominant_species"],
                    "severity_risk": triage_info["severity_risk"],
                    "highway": hw_type,
                    "maxspeed_mph": maxspeed_val,
                    "is_lit": is_lit,
                    "lanes": lanes_val,
                    "forest_within_200m": not clean_road.startswith("M"),
                    "source": "overpass_api"
                }
                self.local_cache[cache_key] = res
                self._save_cache()
                return res

        # 3. Fallback Offline desde la base de datos de Triaje
        triage_info = self.get_road_triage(clean_road)
        res = {
            "road_name": clean_road,
            "triage_level": triage_info["triage_level"],
            "dominant_species": triage_info["dominant_species"],
            "severity_risk": triage_info["severity_risk"],
            "highway": triage_info.get("highway", "primary"),
            "maxspeed_mph": triage_info.get("maxspeed_mph", 60),
            "is_lit": triage_info.get("is_lit", False),
            "lanes": triage_info.get("lanes", 2),
            "forest_within_200m": triage_info.get("forest_within_200m", True),
            "source": "scotland_triage_db"
        }
        self.local_cache[cache_key] = res
        self._save_cache()
        return res

    def enrich_dataframe(
        self,
        df: pd.DataFrame,
        road_col: str = "road_name"
    ) -> pd.DataFrame:
        """Enriquece un DataFrame con triaje de riesgo y atributos OSM."""
        out_df = df.copy()
        if road_col not in out_df.columns:
            raise ValueError(f"Columna '{road_col}' no encontrada en el DataFrame.")

        unique_roads = out_df[road_col].dropna().unique()
        road_attr_map = {r: self.get_road_attributes(str(r)) for r in unique_roads}

        out_df["triage_level"] = out_df[road_col].map(lambda r: road_attr_map.get(r, {}).get("triage_level", "NIVEL 3 - ALERTA AMARILLA"))
        out_df["dominant_species"] = out_df[road_col].map(lambda r: road_attr_map.get(r, {}).get("dominant_species", "Corzo (Roe Deer)"))
        out_df["severity_risk"] = out_df[road_col].map(lambda r: road_attr_map.get(r, {}).get("severity_risk", "MEDIA"))
        out_df["osm_highway_type"] = out_df[road_col].map(lambda r: road_attr_map.get(r, {}).get("highway", "primary"))
        out_df["osm_maxspeed_mph"] = out_df[road_col].map(lambda r: road_attr_map.get(r, {}).get("maxspeed_mph", 60))
        out_df["osm_is_lit"] = out_df[road_col].map(lambda r: road_attr_map.get(r, {}).get("is_lit", False))
        out_df["osm_lanes"] = out_df[road_col].map(lambda r: road_attr_map.get(r, {}).get("lanes", 2))
        out_df["osm_forest_nearby"] = out_df[road_col].map(lambda r: road_attr_map.get(r, {}).get("forest_within_200m", True))

        return out_df

    def simulate_telematics_alert(
        self,
        road_name: str,
        month: int,
        hour: int,
        current_speed_mph: float,
        base_collision_prob: float = 0.05
    ) -> Dict[str, Any]:
        """Simula el diagnóstico y alerta de cabina telemática Insurtech con triaje y cinemática."""
        triage = self.get_road_triage(road_name)
        attrs = self.get_road_attributes(road_name)
        legal_limit = attrs.get("maxspeed_mph", 60)
        is_lit = attrs.get("is_lit", False)

        # 1. Modulador biológico estacional por especie
        is_red_deer_area = "Ciervo Rojo" in triage.get("dominant_species", "")
        if month in [10, 11, 12, 1]:
            season_mult = 3.2 if is_red_deer_area else 1.8
            season_desc = "Pico de Celo (Rutting) / Descenso invernal de manadas"
        elif month in [5, 6]:
            season_mult = 2.4  # Dispersión de corzos
            season_desc = "Dispersión juvenil y partos de hembras"
        else:
            season_mult = 0.8
            season_desc = "Actividad basal de forrajeo"

        # 2. Modulador horario (Crepúsculo)
        is_crepuscular = (6 <= hour <= 8) or (17 <= hour <= 21)
        hour_mult = 2.5 if is_crepuscular else 0.7

        # 3. Factor de iluminación vial OSM
        lighting_mult = 0.5 if is_lit else 1.9

        # 4. Cálculo de riesgo combinado
        risk_score_raw = base_collision_prob * season_mult * hour_mult * lighting_mult
        risk_tier = "ALTO" if risk_score_raw >= 0.15 else ("MEDIO" if risk_score_raw >= 0.05 else "BAJO")

        # 5. Cinemática de frenado (asfalto húmedo estándar UK, fricción mu=0.55)
        # Distancia de parada = Distancia de reacción (v * 1s) + Distancia de frenado (v^2 / (2 * g * mu))
        v_ms_current = current_speed_mph * 0.44704
        stopping_dist_current_m = (v_ms_current * 1.2) + ((v_ms_current ** 2) / (2 * 9.81 * 0.55))

        recommended_speed = 40.0 if risk_tier == "ALTO" else (50.0 if risk_tier == "MEDIO" else legal_limit)
        v_ms_rec = recommended_speed * 0.44704
        stopping_dist_rec_m = (v_ms_rec * 1.2) + ((v_ms_rec ** 2) / (2 * 9.81 * 0.55))

        speed_delta = max(0.0, current_speed_mph - recommended_speed)
        safety_points = min(25, int(speed_delta * 1.5)) if speed_delta > 0 else 5
        claim_avoidance_prob = min(0.40, speed_delta * 0.02) if speed_delta > 0 else 0.05

        # Coste medio actuarial (£5.191 en sistemas ADAS y hasta £15.000 con Ciervo Rojo)
        avg_claim_cost_gbp = 7500.0 if is_red_deer_area else 5191.0
        expected_savings_gbp = avg_claim_cost_gbp * claim_avoidance_prob

        return {
            "road": road_name.upper(),
            "triage_level": triage.get("triage_level"),
            "category_name": triage.get("category_name"),
            "dominant_species": triage.get("dominant_species"),
            "severity_risk": triage.get("severity_risk"),
            "historical_dvc_count": triage.get("dvc_count"),
            "primary_region": triage.get("primary_region"),
            "query_time": {
                "month": month,
                "hour": f"{hour:02d}:00",
                "is_crepuscular": is_crepuscular
            },
            "risk_assessment": {
                "risk_tier": risk_tier,
                "risk_index": round(risk_score_raw, 4),
                "season_context": season_desc
            },
            "road_attributes_osm": {
                "highway": attrs.get("highway"),
                "speed_limit_mph": legal_limit,
                "street_lighting": "Iluminada" if is_lit else "Sin Farolas (Vía Oscura)",
                "forest_proximity": "Bosque adyacente < 200m" if attrs.get("forest_within_200m") else "Campo abierto"
            },
            "vehicle_kinematics": {
                "current_speed_mph": current_speed_mph,
                "stopping_distance_current_m": round(stopping_dist_current_m, 1),
                "recommended_speed_mph": recommended_speed,
                "stopping_distance_rec_m": round(stopping_dist_rec_m, 1),
                "stopping_distance_saved_m": round(stopping_dist_current_m - stopping_dist_rec_m, 1),
                "reduction_suggested_mph": speed_delta
            },
            "insurtech_actuarial": {
                "safety_score_gain": safety_points,
                "monthly_premium_discount_pct": round(min(15.0, safety_points * 0.6), 1),
                "expected_claim_savings_gbp": round(expected_savings_gbp, 2)
            }
        }


# Instancia singleton preconfigurada
osm_service = OSMScotlandService(mode="auto")


if __name__ == "__main__":
    print("=== Probando Triaje y OpenStreetMap para Escocia ===")
    service = OSMScotlandService(mode="auto", verbose=True)

    # 1. Probar triaje de 4 niveles
    test_roads = ["A9", "A82", "A90", "B979", "M8"]
    for r in test_roads:
        tr = service.get_road_triage(r)
        print(f"\n[{r}] -> {tr['triage_level']} | Especie: {tr['dominant_species']} | Severidad: {tr['severity_risk']}")

    # 2. Simulación telemática interactiva en la A82
    alert = service.simulate_telematics_alert("A82", month=11, hour=18, current_speed_mph=60)
    print("\n--- Alerta Telemática Insurtech con Cinemática y Triaje ---")
    print(json.dumps(alert, indent=2, ensure_ascii=False))
