# V8 · Threshold Sensitivity

## Cambios

- Matriz de confusión exacta del sistema final con el umbral 0,2425809815683556:
  - TP 715
  - FP 709
  - TN 4.517
  - FN 431
- Barrido descriptivo de umbrales: 0,10; 0,15; 0,20; seleccionado; 0,30; 0,40; 0,50.
- Métricas añadidas por umbral: alertas, TP, FP, TN, FN, precision, recall, F1, accuracy, especificidad, FPR y FNR.
- Visualización del trade-off FP/FN en `TechnologyLab.jsx`.
- Export `data/strict_threshold_sensitivity_2017.csv`.
- El endpoint `/api/technology/strict-temporal-audit` expone `threshold_sensitivity` y `confusion_matrix_selected_threshold`.
- El barrido queda marcado como `post_hoc_descriptive_test_2017`: no cambia el umbral seleccionado en 2016.
- Tests ampliados a 14/14.
