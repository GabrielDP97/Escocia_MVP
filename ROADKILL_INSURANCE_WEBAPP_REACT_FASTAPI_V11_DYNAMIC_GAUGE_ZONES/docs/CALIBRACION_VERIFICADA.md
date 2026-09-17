# Auditoría de calibración probabilística · Roadkill Risk Engine

## Objetivo

Comprobar con los artefactos incluidos en el proyecto si la calibración de probabilidades realmente reduce el error probabilístico medido por Brier, y separar claramente lo verificable de las cifras que requieren datos/modelos no incluidos.

## Resultados verificables en 2017

| Modelo | Brier raw | Brier calibrado | Reducción relativa | IC95% Δ Brier por cell |
|---|---:|---:|---:|---:|
| DNN | 0,17871 | 0,10725 | 39,99% | [-0,08019, -0,06265] |
| SimpleRNN | 0,16536 | 0,10434 | 36,90% | [-0,06639, -0,05552] |
| LSTM | 0,16554 | 0,10385 | 37,27% | [-0,06753, -0,05492] |

En los tres modelos profundos la calibración guardada en el ZIP reduce de forma clara el Brier. ROC-AUC y PR-AUC permanecen esencialmente iguales, coherente con una transformación monotónica que modifica la escala probabilística pero no el ranking de los casos.

## Recalibración diagnóstica de `p_final`

`p_final` ya parte de un Brier de **0,10374** sobre la intersección común de 6.348 observaciones.

| Método cross-fit | Brier | Δ Brier vs p_final | ECE q10 | PR-AUC |
|---|---:|---:|---:|---:|
| Sin recalibrar | 0,10374 | — | 0,01912 | 0,61681 |
| Sigmoide sobre `p` | 0,10417 | +0,00043 | 0,02782 | 0,61471 |
| Platt sobre `logit(p)` | 0,10323 | -0,00050 | 0,01592 | 0,61584 |
| Isotónica | 0,10332 | -0,00042 | 0,00686 | 0,60031 |

Conclusión: **calibrar no mejora automáticamente**. La sigmoide aplicada directamente a una probabilidad ya razonablemente calibrada empeora el Brier en este diagnóstico. El remapeo logit-Platt mejora ligeramente Brier/ECE, mientras que la isotónica mejora calibración pero deteriora el ranking global al recombinar folds.

## Ensemble 50/25/25

Brier base del ensemble: **0,10311**.

- Sigmoide sobre `p`: 0,10338 (empeora +0,00027).
- Platt sobre `logit(p)`: 0,10208 (mejora -0,00103).
- Isotónica: 0,10193 (mejora -0,00118, pero con pérdida de PR-AUC al mezclar transformaciones por fold).

Estas cifras son diagnósticas porque los calibradores se ajustan por cross-fit agrupado dentro de 2017. No deben presentarse como test temporal independiente.

## Afirmaciones del documento

### Reto 05 · Brier 0,0799 → 0,0175 con calibración sigmoide

**No reproducible exactamente con este ZIP.** Faltan las predicciones pre-calibración del conjunto de validación 2016 y el estimador original del Stacking/Reto 05. Sí queda demostrado con los artefactos DNN/RNN/LSTM que una calibración post-hoc puede reducir mucho Brier cuando la salida cruda está descalibrada.

### Reto 07 · Hurdle 1D con Brier 0,0018 y ROC/PR-AUC >0,990

**No reproducible con este ZIP.** Faltan la geometría vial 1D a 250 m, los eventos proyectados, las variables métricas de borde forestal/iluminación y el estimador Hurdle serializado.

## Protocolo correcto para cerrar la verificación

Para verificar exactamente las cifras del documento se necesita incorporar los artefactos de 2016 y/o el modelo serializado original. El flujo correcto sería:

1. Entrenar el estimador solo con el periodo de entrenamiento.
2. Ajustar `CalibratedClassifierCV(method='sigmoid')` o el calibrador definido originalmente **solo sobre 2016**.
3. Congelar modelo y calibrador.
4. Evaluar una única vez en 2017.
5. Comparar Brier, log-loss, reliability curve, ECE, PR-AUC y Lift con bootstrap agrupado por `cell`.

La V6 deja ya implementada la infraestructura de auditoría para hacer esa última comprobación cuando se incorporen esos artefactos.
