# Cambios · Reto 09 LSTM

Se añade al Laboratorio Tecnológico un bloque específico para las métricas oficiales del notebook `09_Prediccion_Espacio_Temporal_RNN_LSTM_Escocia(2).ipynb`.

## Resultado oficial · test 2017

- 6.348 secuencias
- 529 celdas
- ventana seleccionada: 12 meses
- modelo seleccionado: LSTM + Platt
- ROC-AUC: 0.8464966488254952
- PR-AUC: 0.6092131142547675
- Brier: 0.10384728110083574
- Precision: 0.547923322683706
- Recall: 0.5986038394415357
- F1: 0.5721434528773979
- Lift top 1%: 5.1930628272251305
- Lift top 5%: 4.476703217096381
- umbral elegido en validation: 0.26632536663997347
- mejor época por PR-AUC: 30
- épocas ejecutadas: 38

Se muestra por separado la comparación oficial LSTM / SimpleRNN / Logistic con lags, el efecto de Platt sobre Brier, el bootstrap por celda y la comparación de horizonte t+1 / t+3.

La tabla comparativa Reto 05 / 08 / 09 se conserva como benchmark homogéneo.
