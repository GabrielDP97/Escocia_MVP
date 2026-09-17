# Tecnologías aplicadas y benchmark comparativo

## Objetivo

Esta versión incorpora al MVP un laboratorio reproducible para comprobar qué capas del documento tecnológico aportan señal con los artefactos que realmente contiene el ZIP. El objetivo no es forzar una mejora, sino separar:

1. mejoras medibles con el test histórico 2017;
2. integraciones operativas que se pueden preparar pero no medir con estos datos;
3. tecnologías que no se pueden reproducir honestamente porque faltan los datos o modelos originales.

## Conjunto de comparación

Para comparar Reto 05, Reto 08 y Reto 09 se usa la intersección común de **6.348 observaciones** y **529 celdas**, con prevalencia positiva de **18,0529%**. Todas las variantes se evalúan sobre exactamente las mismas filas.

El modelo de referencia sigue siendo `p_final` del Reto 05. No se sustituye automáticamente por un ensemble, porque el test 2017 debe mantenerse como test y no convertirse en conjunto de selección.

## Resultados principales

| Variante | ROC-AUC | PR-AUC | Brier | Lift 1% | Lift 5% |
|---|---:|---:|---:|---:|---:|
| Nivel 1 sin ajuste estacional | 0,8457 | 0,5981 | 0,10572 | 5,11x | 4,48x |
| **Actual · Reto 05 + ajuste estacional** | **0,8515** | **0,6168** | **0,10374** | **5,28x** | 4,60x |
| DNN calibrada | 0,8413 | 0,5945 | 0,10765 | 5,11x | 4,39x |
| LSTM calibrada | 0,8465 | 0,6092 | 0,10385 | 5,19x | 4,48x |
| Ensemble igualitario | 0,8546 | 0,6219 | 0,10313 | 5,19x | 4,63x |
| Ensemble exploratorio 50/25/25 | **0,8546** | **0,6223** | **0,10311** | 5,19x | **4,69x** |

### Qué sí mejora de forma clara

El ajuste estacional ya presente en el proyecto mejora frente a `p_level1`:

- Δ PR-AUC = **+0,0187** en la muestra completa.
- Δ ROC-AUC = **+0,0059**.
- Δ Brier = **-0,00198** (menor es mejor).

Bootstrap agrupado por `cell` (500 remuestreos):

- Δ PR-AUC medio = **+0,02082**, IC95% **[+0,01462, +0,02744]**.
- Δ ROC-AUC medio = **+0,00607**, IC95% **[+0,00313, +0,00881]**.
- Δ Brier medio = **-0,00199**, IC95% **[-0,00274, -0,00128]**.

La señal estacional, por tanto, no parece decorativa: aporta señal incremental en este test.

### Qué mejora solo de forma modesta

La fusión exploratoria 50% `p_final` + 25% DNN + 25% LSTM mejora ligeramente el resultado puntual:

- PR-AUC: **0,6168 → 0,6223**.
- ROC-AUC: **0,8515 → 0,8546**.
- Brier: **0,10374 → 0,10311**.
- Lift 5%: **4,60x → 4,69x**.
- Lift 1%: **5,28x → 5,19x** (empeora ligeramente).

Bootstrap agrupado por `cell` (500 remuestreos):

- Δ PR-AUC medio = **+0,00524**, IC95% **[+0,00036, +0,01040]**.
- Δ ROC-AUC medio = **+0,00306**, IC95% **[+0,00050, +0,00559]**.
- Δ Brier medio = **-0,00063**, IC95% **[-0,00114, -0,00004]**.

Es una señal prometedora, pero **no se promociona al modelo principal** porque el peso se ha inspeccionado sobre el propio test 2017. La validación correcta sería fijar el ensemble usando 2016 u otro conjunto de validación y medir una única vez en un periodo temporal posterior independiente.

## Barridos añadidos

El endpoint `/api/technology/benchmark` devuelve además:

- barrido del peso del score actual frente a la media DNN/LSTM (`0.0 ... 1.0`);
- barrido de umbrales operativos (`0.05 ... 0.50`) con precisión, recall, F1 y número de alertas;
- bootstrap agrupado por celda;
- microbenchmark de la operación de fusión vectorizada.

El microbenchmark mide únicamente la combinación de scores precomputados, **no inferencia end-to-end** del Random Forest, DNN o LSTM.

## Tecnologías del documento: estado real en este ZIP

### Aplicadas

- `pandas` / `NumPy`: joins, agregaciones, ranking, histogramas y benchmark.
- `scikit-learn`: ROC-AUC, PR-AUC, Brier, log-loss y evaluación comparativa.
- OSM / triaje offline: contexto vial, iluminación, velocidad máxima y proximidad forestal cualitativa.
- clustering del Reto 06: se conserva como contexto descriptivo.
- FastAPI: nuevos endpoints de laboratorio.

### Integrada para uso operativo, pero no evaluable con el test disponible

- `astral`: endpoint `/api/technology/solar-context` para calcular ocaso y la ventana `[-60, +120]` minutos con coordenadas y timestamp exactos.

No se incorpora esta señal a la PR-AUC 2017 porque el CSV de predicciones no contiene hora exacta por evento/observación; hacerlo inventando una hora sería metodológicamente incorrecto.

### No reproducibles con el ZIP actual

- GeoPandas/Shapely con red vial 1D segmentada a 250 m: faltan geometrías lineales y proyecciones de eventos.
- Edge effect forestal real `<50 m`: falta distancia métrica a linde forestal por fila; `forest_within_200m` no es equivalente.
- Hurdle 1D del capítulo 7: faltan datasets de entrenamiento y estimadores serializados.
- SHAP por predicción: falta el estimador exacto y su matriz de features de entrenamiento.

Estas capas se marcan como no reproducibles en la interfaz para evitar presentar como implementado algo que los artefactos actuales no permiten validar.

## Archivos añadidos

- `backend/technology_lab.py`
- `backend/solar_context.py`
- `backend/run_benchmarks.py`
- `frontend/src/pages/TechnologyLab.jsx`
- `tests/test_technology_lab.py`
- `data/benchmark_technology_lab.json`
- `requirements-dev.txt`

## Reproducir el benchmark

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m backend.run_benchmarks
```

El último comando regenera `data/benchmark_technology_lab.json` con 500 bootstrap agrupados por celda.
