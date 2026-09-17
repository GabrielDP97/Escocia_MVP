# Roadkill Risk Engine · Web MVP

Aplicación web real para presentar el proyecto a una aseguradora.

## Arquitectura

- **Frontend:** React + Vite
- **Backend:** Python + FastAPI
- **Mapa:** Leaflet / OpenStreetMap
- **Gráficas:** Recharts
- **Datos:** artefactos reales del test 2017 de Retos 05, 08 y 09 + coordenadas BNG + caché OSM

La aplicación **no vuelve a entrenar los modelos durante la demo**. Consume las predicciones históricas ya generadas para construir una experiencia de producto.

## Pantallas

### 1. Demo conductor
- carretera y mes seleccionables;
- mapa con coordenadas WGS84 convertidas desde BNG;
- vehículo simulado recorriendo las celdas;
- `p_final` del Reto 05;
- Risk Response Score 0–100 basado en percentil de cartera, con arco, aguja y zonas de color recalculadas dinámicamente según el umbral seleccionado;
- comparación LSTM / DNN;
- triaje y contexto OSM;
- alerta según el umbral validado;
- distancia de frenado y respuesta preventiva simulada;
- modo auditoría para revelar el resultado histórico.

### 2. Dashboard aseguradora
- métricas PR-AUC / ROC-AUC / Brier / Lift;
- riesgo por mes;
- distribución del score;
- ranking histórico de carreteras;
- KPIs de test.

### 3. Simulador económico
- vehículos asegurados;
- frecuencia DVC por cada 1.000 vehículos/año;
- coste medio por claim;
- reducción hipotética;
- claims esperados, coste anual e impacto potencial.

Incluye tres presets:
- **Referencia UK reciente:** frecuencia proxy ~0,48/1.000 (Zurich 2021 + DfT 2021) y coste medio £4.317,24 (Zurich 2024).
- **Referencia histórica Fortis 2004–2005:** ~0,36/1.000 y coste medio histórico £1.320.
- **Datos propios:** tasa y coste editables para una cartera concreta.

El número de vehículos **sí forma parte del cálculo**: `claims esperados = vehículos / 1.000 × frecuencia`.

La pantalla deja explícito que **no es una predicción actuarial** y que la reducción preventiva sigue siendo hipotética.

### 4. Metodología
- qué es real;
- qué es simulado;
- modelo principal y comparadores;
- pasos para evolucionar el MVP a producto.

---

# Instalación en Windows

Necesitas:
- Python 3.10+
- Node.js 20+

## Opción A · desarrollo

Abre dos terminales.

### Backend

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.app:app --reload --port 8000
```

### Frontend

```bat
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`.

## Opción B · una sola URL para presentar

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Abre `http://127.0.0.1:8000`.

FastAPI detecta `frontend/dist` y sirve la aplicación React compilada.

## Scripts incluidos

- `setup_windows.bat`
- `start_dev_windows.bat`
- `build_and_run_windows.bat`
- equivalentes `.sh` para Linux/macOS

---

# Importante para la demo

1. Las predicciones son del **test histórico 2017**.
2. La ruta dibujada une centros BNG asociados a cada carretera; no es todavía la geometría exacta del asfalto.
3. Los tiles del mapa son OpenStreetMap y necesitan conexión a Internet. Los datos de riesgo y la API funcionan localmente.
4. La velocidad preventiva es una regla de demostración.
5. Los resultados históricos (`target_presence`, `dvc_count`) están ocultos salvo en modo auditoría.
6. El simulador económico es un escenario de negocio, no una reducción demostrada.

## API

- `GET /api/health`
- `GET /api/metadata`
- `GET /api/roads`
- `GET /api/route?road_name=A82&month=5`
- `GET /api/dashboard`
- `GET /api/cases`

Swagger: `http://127.0.0.1:8000/docs`

---

## V5 · Laboratorio tecnológico y pruebas de rendimiento

Se ha añadido una quinta pantalla, **Laboratorio tecnológico**, para comprobar con métricas si las capas propuestas aportan señal o no.

Incluye:

- comparación homogénea entre Reto 05, DNN y LSTM sobre 6.348 observaciones comunes;
- ROC-AUC, PR-AUC, Brier, log-loss y Lift;
- ensemble igualitario y variante exploratoria 50/25/25;
- bootstrap agrupado por `cell`;
- barrido de pesos del ensemble;
- barrido de umbrales de alerta;
- matriz de tecnologías aplicadas / parciales / no reproducibles;
- endpoint `astral` para contexto solar cuando exista un timestamp exacto.

El score principal **no se sustituye automáticamente** por el ensemble. Los pesos del ensemble se analizan en el test 2017 y, por tanto, necesitan una validación temporal independiente antes de convertirse en modelo de producción.

### Ejecutar pruebas

En Windows, después de `setup_windows.bat`:

```bat
run_benchmarks_windows.bat
```

O manualmente:

```bat
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m backend.run_benchmarks
```

El informe detallado está en `docs/TECNOLOGIAS_APLICADAS_Y_BENCHMARK.md` y los resultados machine-readable en `data/benchmark_technology_lab.json`.

### Nota sobre la compilación React

La página nueva vive en `frontend/src`. En Windows, `build_and_run_windows.bat` ejecuta `npm run build` y genera el `frontend/dist` actualizado antes de arrancar FastAPI. Si se copia el proyecto entre sistemas operativos, conviene ejecutar `npm install` de nuevo porque Rollup/Vite incluye dependencias nativas específicas de plataforma.

---

## V6 · Auditoría de calibración probabilística

Se amplía el Laboratorio tecnológico para comprobar específicamente las afirmaciones de calibración del documento.

### Qué se verifica con los artefactos reales del ZIP

- **DNN:** se compara `p_dnn_raw` frente a `p_dnn_calibrated`.
- **SimpleRNN:** se compara `p_simplernn_raw` frente a `p_simplernn_calibrated`.
- **LSTM:** se compara `p_lstm_raw` frente a `p_lstm_calibrated`.
- Se calculan Brier, log-loss, ROC-AUC, PR-AUC, ECE por deciles de probabilidad y reliability bins.
- Se añade bootstrap agrupado por `cell` para estimar IC95% del cambio en Brier.
- Se prueba una recalibración diagnóstica de `p_final` y del ensemble mediante:
  - sigmoide sobre la probabilidad disponible;
  - Platt sobre `logit(p)`;
  - regresión isotónica.

El cross-fit usa `StratifiedGroupKFold(5)` agrupado por `cell` dentro de 2017. **Es una prueba diagnóstica**, no sustituye el protocolo correcto de calibrar en 2016 y evaluar una sola vez en 2017.

### Qué no puede reproducirse exactamente

El ZIP no incluye las predicciones de validación 2016 ni los estimadores serializados de Reto 05 / Reto 07. Por eso no se puede reconstruir de forma rigurosa el número exacto `Brier 0,0799 → 0,0175` del Stacking ni el `Brier 0,0018` del Hurdle 1D. La interfaz los marca explícitamente como **no reproducibles con este ZIP** en vez de asumirlos como demostrados.

### Nuevos artefactos

- `GET /api/technology/calibration-audit`
- `data/calibration_audit.json`
- `data/calibration_comparison.csv`
- `docs/CALIBRACION_VERIFICADA.md`

`run_benchmarks_windows.bat` regenera tanto el benchmark general como la auditoría de calibración.

---

## V7 · Calibración temporal estricta 2016 → 2017

V7 resuelve la limitación indicada en V6 localizando e integrando la evidencia del **Reto 05 temporal estricto ya ejecutado** dentro del proyecto del usuario.

El protocolo auditable es:

- subtrain `2008–2015`;
- selección/validation `2016`;
- Platt sobre predicciones OOF de folds temporales expansivos;
- refit final `2008–2016`;
- apertura única del test `2017`.

Resultados comprobados:

- Random Forest raw validation 2016: **Brier 0,159051**;
- tras Platt temporal OOF: **0,102692** (**-35,43%**);
- tras Nivel 2 estacional: **0,100471**;
- test final 2017, recalculado desde las 6.372 predicciones del ZIP: **ROC-AUC 0,852175 · PR-AUC 0,616802 · Brier 0,103348**.

La cifra `0,0799 → 0,0175` del documento global **no se reproduce bajo este protocolo temporal estricto de Reto 05**. V7 no la etiqueta automáticamente como falsa: la separa como resultado de otro posible protocolo/modelo y evita atribuírsela al experimento corregido 2008–2017.

Nuevos artefactos:

- `GET /api/technology/strict-temporal-audit`
- `data/strict_temporal_audit.json`
- `data/strict_validation_2016_summary.csv`
- `data/strict_test_2017_summary.csv`
- `docs/CALIBRACION_TEMPORAL_ESTRICTA_2016_2017.md`
- `CHANGELOG_STRICT_TEMPORAL_CALIBRATION.md`

La suite pasa **11/11 tests** e incluye comprobaciones para impedir que futuras versiones vuelvan a presentar `0,0175` como el Brier del protocolo temporal estricto sin evidencia.


---

## V8 · Sensibilidad del umbral y matriz de confusión

V8 amplía la auditoría temporal estricta con una prueba descriptiva del trade-off entre **falsos positivos y falsos negativos** sobre las 6.372 observaciones de test 2017.

El umbral del experimento no cambia: sigue siendo **0,2425809815683556**, seleccionado en validation 2016.

Con ese umbral:

- TP: **715**
- FP: **709**
- TN: **4.517**
- FN: **431**
- Precision: **50,21 %**
- Recall: **62,39 %**
- Especificidad: **86,43 %**
- FPR: **13,57 %**
- FNR: **37,61 %**

La interfaz del **Laboratorio tecnológico** incorpora:

- cuatro tarjetas con TP / FP / TN / FN;
- gráfico de sensibilidad del umbral;
- tabla para `0,10 / 0,15 / 0,20 / 0,242581 / 0,30 / 0,40 / 0,50`;
- precisión, recall, F1, número total de alertas y conteos FP/FN para cada umbral;
- advertencia metodológica explícita para evitar elegir un nuevo umbral retrospectivamente con el test 2017.

Nuevo artefacto:

- `data/strict_threshold_sensitivity_2017.csv`

La suite pasa **14/14 tests**.

## V9 · selector de umbral interactivo
La pantalla Driver Experience permite cambiar temporalmente el umbral para visualizar el efecto sobre alertas y respuesta preventiva. Solo 0,242581 es el umbral validado en 2016; los demás son simulaciones descriptivas sobre 2017.

---

## V10 · Colores dinámicos según el umbral

En **Driver Experience**, el selector de umbral controla ahora también la representación visual:

- puntos y tramos de la ruta;
- color de la aguja del Risk Response Score;
- color del valor del score;
- estado inferior del gauge;
- leyenda dinámica del mapa;
- marca del umbral en la escala percentil del gauge.

Los estados son `Normal`, `Vigilancia`, `Alerta` y `Alerta alta`. El umbral sigue estando expresado en probabilidad (`p_final`). La marca del gauge se calcula mediante su percentil empírico equivalente sobre el test 2017 para no confundir probabilidad con Risk Response Score.
