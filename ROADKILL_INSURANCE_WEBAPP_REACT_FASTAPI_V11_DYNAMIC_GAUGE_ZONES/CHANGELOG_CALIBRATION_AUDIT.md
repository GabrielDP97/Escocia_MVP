# V6 · Auditoría de calibración y verificación de afirmaciones

## Añadido

- `backend/calibration_lab.py`
  - Brier, log-loss, ROC-AUC, PR-AUC.
  - ECE/MCE con bins por cuantiles.
  - reliability bins para gráfica.
  - bootstrap agrupado por `cell`.
  - auditoría raw → calibrated para DNN, SimpleRNN y LSTM.
  - cross-fit agrupado para sigmoide, Platt sobre logit e isotónica.
- `GET /api/technology/calibration-audit`.
- Nueva sección de calibración dentro de **Laboratorio tecnológico**.
- `data/calibration_audit.json`.
- `data/calibration_comparison.csv`.
- `docs/CALIBRACION_VERIFICADA.md`.
- 3 tests nuevos de calibración; suite total: 7 tests.

## Resultado principal

La calibración guardada reduce Brier de forma clara en los modelos profundos:

- DNN: 0,17871 → 0,10725 (-39,99%).
- SimpleRNN: 0,16536 → 0,10434 (-36,90%).
- LSTM: 0,16554 → 0,10385 (-37,27%).

Los IC95% bootstrap por `cell` de Δ Brier son completamente negativos en los tres casos.

## Hallazgo metodológico

No se debe aplicar calibración de forma automática a cualquier score. `p_final` ya está razonablemente calibrado y una sigmoide adicional directamente sobre `p` empeora Brier en el cross-fit diagnóstico. Platt sobre `logit(p)` mejora ligeramente el Brier.

## Límites de reproducibilidad

No se reconstruyen ni se dan por demostradas las cifras exactas del documento `0,0799 → 0,0175` (Reto 05) ni `0,0018` (Reto 07) porque faltan los artefactos 2016/estimadores y la geometría/features del Hurdle 1D. La UI las marca explícitamente como no reproducibles con el ZIP actual.
