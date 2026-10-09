# Auditoría temporal estricta de calibración · Reto 05

## Objetivo

Comprobar la pregunta pendiente de V6: **¿qué ocurre si la calibración se decide sin tocar 2017 y después se evalúa una sola vez en 2017?**

V7 integra el experimento ya ejecutado en el proyecto `Reto5_Clasificacion_Regresion_Atropellos_TEMPORAL_ESTRICTO_2017(3).ipynb` y vuelve a calcular de forma independiente las métricas finales a partir de `data/predicciones_test_2017.csv`.

> Importante: el ZIP de la web no contiene los 36 GB de datos crudos necesarios para volver a entrenar de cero. Por eso V7 distingue dos procedencias: los resultados de *validation 2016* se recuperan del notebook ejecutado del proyecto; el *test 2017* sí se recalcula fila a fila con el CSV que viaja dentro de la aplicación.

## Protocolo comprobado

- Subtrain: **2008–2015**.
- Validation para selección: **2016**.
- Development final: **2008–2016**.
- Test final: **2017**.
- 2018 queda fuera del modelado y se conserva solo para auditoría.
- La calibración final usa predicciones **out-of-fold temporales**:
  - 2008–2012 → 2013
  - 2008–2013 → 2014
  - 2008–2014 → 2015
  - 2008–2015 → 2016
- Platt se ajusta sobre el `logit(p)` de esas predicciones OOF.
- Familia, calibración, Nivel 1/Nivel 2 y umbral se deciden antes de abrir 2017.

Este protocolo es más estricto que calibrar directamente sobre 2016 y reutilizarlo como evaluación: el calibrador aprende de probabilidades que siempre proceden de un modelo que no ha visto el año sobre el que predice.

## Resultado de la calibración en validation 2016

| Etapa | ROC-AUC | PR-AUC | Brier |
|---|---:|---:|---:|
| Random Forest raw | 0,847381 | 0,546662 | **0,159051** |
| Nivel 1 + Platt OOF temporal | 0,847381 | 0,546662 | **0,102692** |
| Nivel 2 + modulador estacional | 0,853704 | 0,572252 | **0,100471** |

La calibración Platt reduce el Brier en **0,056359 puntos**, equivalente a aproximadamente **35,43 %** respecto al Random Forest raw. La transformación mantiene el ranking prácticamente igual, como corresponde a una calibración monotónica, pero hace que las probabilidades sean mucho más coherentes con la frecuencia observada.

Después, el Nivel 2 estacional aporta una mejora adicional: Brier **0,102692 → 0,100471** y PR-AUC **0,546662 → 0,572252**. Por ello se seleccionó `Nivel2_validation`. El umbral F1 se congeló en **0,2425809815683556**.

## Resultado final en test 2017

V7 vuelve a calcular estas métricas sobre las **6.372 filas** de `predicciones_test_2017.csv`:

| Etapa | ROC-AUC | PR-AUC | Brier | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Nivel 1 | 0,846317 | 0,598075 | 0,105321 | 0,491120 | 0,627400 | 0,550958 |
| Nivel 2 / Sistema final | **0,852175** | **0,616802** | **0,103348** | **0,502107** | 0,623909 | **0,556420** |

La comprobación automática da **PASS**: las métricas recalculadas desde el CSV coinciden numéricamente con el notebook ejecutado.



## Sensibilidad del umbral y matriz de confusión

V8 añade una prueba descriptiva sobre el test 2017 para visualizar el coste de bajar o subir el umbral. **No se vuelve a elegir el umbral usando 2017**: el valor válido del experimento continúa siendo **0,2425809815683556**, fijado en validation 2016.

Con ese umbral congelado, la matriz de confusión es:

| Resultado | Casos |
|---|---:|
| Verdaderos positivos (TP) | **715** |
| Falsos positivos (FP) | **709** |
| Verdaderos negativos (TN) | **4.517** |
| Falsos negativos (FN) | **431** |

Esto corresponde a precisión **50,21 %**, recall **62,39 %**, especificidad **86,43 %**, tasa de falsos positivos **13,57 %** y tasa de falsos negativos **37,61 %**.

El barrido descriptivo produce:

| Umbral | Alertas | TP | FP | FN | Precisión | Recall | F1 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0,10 | 3.153 | 1.019 | 2.134 | 127 | 32,32 % | 88,92 % | 47,41 % |
| 0,15 | 2.469 | 928 | 1.541 | 218 | 37,59 % | 80,98 % | 51,34 % |
| 0,20 | 1.823 | 818 | 1.005 | 328 | 44,87 % | 71,38 % | 55,10 % |
| **0,242581** | **1.424** | **715** | **709** | **431** | **50,21 %** | **62,39 %** | **55,64 %** |
| 0,30 | 1.062 | 611 | 451 | 535 | 57,53 % | 53,32 % | 55,34 % |
| 0,40 | 690 | 486 | 204 | 660 | 70,43 % | 42,41 % | 52,94 % |
| 0,50 | 499 | 379 | 120 | 767 | 75,95 % | 33,07 % | 46,08 % |

La lectura es directa: bajar el umbral captura más eventos reales y reduce falsos negativos, pero genera muchas más falsas alarmas. Subirlo reduce las falsas alarmas, pero deja escapar más eventos. Por ejemplo, pasar de **0,242581 a 0,20** habría capturado **103 eventos reales adicionales**, a costa de **296 falsos positivos adicionales**. Pasar a **0,15** habría capturado **213 eventos adicionales**, pero con **832 falsos positivos adicionales**.

Sin una función de coste de negocio —por ejemplo, coste de una falsa alarma frente al coste de no detectar un atropello— no existe un umbral universalmente mejor. Por eso este barrido queda marcado como **post-hoc descriptivo** y no modifica el umbral seleccionado en 2016.

## ¿Se reproduce el Brier 0,0175 del documento global?

**No bajo este protocolo temporal estricto del Reto 05.**

El documento global cita una reducción `0,0799 → 0,0175`, pero el experimento corregido y ejecutado produce:

- Brier raw validation 2016: **0,159051**.
- Brier tras Platt temporal: **0,102692**.
- Brier Nivel 2 validation 2016: **0,100471**.
- Brier final test 2017: **0,103348**.

Esto **no demuestra que 0,0175 sea inventado**: puede proceder de otro modelo, otra muestra o un protocolo anterior. Lo que sí demuestra es que no debe presentarse como el resultado del Reto 05 temporal estricto 2008–2017.

El resultado científicamente defendible en esta versión es: **la calibración sí mejora de forma importante el Brier, pero no hasta 0,0175**.

## Qué añade V7

- Endpoint `/api/technology/strict-temporal-audit`.
- Sección visual en **Laboratorio tecnológico**.
- `data/strict_temporal_audit.json`.
- `data/strict_validation_2016_summary.csv`.
- `data/strict_test_2017_summary.csv`.
- Tests automáticos que impiden que futuras modificaciones vuelvan a atribuir `0,0175` al protocolo estricto sin evidencia.
