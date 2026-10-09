# Auditoría de tráfico y comparación del Poisson

Este notebook audita el AADF original de **Scotland, 2008–2017**, calcula una exposición candidata por tramo y compara dos nuevos ajustes Poisson sobre la misma muestra. Los resultados históricos y los CSV utilizados por el frontend se conservan.

**Estado de esta entrega:** no se ha auditado aquí el dataset original ni reentrenado con él. Las pruebas del código usan datos sintéticos separados, que no están incorporados como resultados de este notebook.

1. Guarda este notebook en `IA/notebooks/escocia/` de tu repositorio (o en `notebooks/escocia/` si la raíz ya es `IA`).
2. Selecciona el kernel del proyecto, con `numpy`, `pandas`, `scikit-learn >= 1.5` y `joblib`. Estas dependencias están incluidas en los requisitos de la aplicación.
3. Ejecuta las celdas en orden. Busca los resultados en la carpeta impresa al ejecutar la auditoría.

Necesita los archivos originales:
- `Datos/trafico/aadf_data/dft_traffic_counts_aadf.csv`.
- `Datos/dvc/DVC_SCOTLAND_GEOJSON_4326/DVC_SCOTLAND.geojson`, `Datos/dvc/DVC_SCOTLAND.geojson` o `Datos/dvc/DVC_SCOTLAND_GEOJSON_4326.zip`.

Si faltan, se informa de ello; no se descargan datos ni se sustituyen por ejemplos. Si falta solo DVC, la auditoría del tráfico queda guardada.

## Qué cambia en la exposición

Para el mes $m$ de una celda, el cálculo anterior era:

$$E_{anterior}=\operatorname{media}(AADF_i)\times\sum_i L_i\times d_m.$$

La candidata, después de retirar duplicados exactos, es:

$$E_{candidata}=\sum_i(AADF_i\times L_i)\times d_m.$$

$AADF_i$ son vehículos diarios medios anuales del tramo, $L_i$ su longitud en km y $d_m$ los días del mes. El resultado es **vehículos-km**, una medida de exposición de muchos vehículos. No son los kilómetros mensuales que recorre un usuario.

Ejemplo: dos tramos con `(1000 vehículos/día, 1 km)` y `(100 vehículos/día, 9 km)` dan **5500** vehículos-km/día con el cálculo anterior y **1900** con la suma por tramo. El cambio puede aumentar o disminuir la exposición según los datos.

La documentación del [DfT](https://roadtraffic.dft.gov.uk/about) explica el AADF y su cobertura. La suma por enlace se describe en sus [notas y definiciones](https://www.gov.uk/government/statistics/road-traffic-estimates-in-great-britain-2024/notes-and-definitions).

**Todavía no es una exposición geográfica validada:** falta recortar las geometrías de los tramos al borde de cada celda y comprobar qué vías cubren los DVC y los aforos. Las vías menores están muestreadas. Una celda de 10 × 10 km no es un círculo de 10 km de radio.

## Reentrenamiento emparejado

Se usa la misma muestra de celdas/años elegibles, las mismas variables y el mismo protocolo para las dos exposiciones:

| Evaluación | Entrenamiento | Evaluación fuera del entrenamiento |
|---|---|---|
| Validación | 2008–2015 | 2016 |
| Test | 2008–2016 | 2017 |

No se usa una partición aleatoria ni se ajustan parámetros usando test. El preprocesamiento se aprende solo con entrenamiento. Se utiliza Poisson sin regularización, con frecuencia `DVC/exposición` y pesos de exposición; es una reparametrización del objetivo Poisson con offset `log(exposición)`. El escalado del objetivo mejora la estabilidad numérica y se deshace al predecir. Véase el método de frecuencia y exposición de [scikit-learn](https://scikit-learn.org/stable/auto_examples/linear_model/plot_tweedie_regression_insurance_claims.html).

Esto compara **dos nuevos ajustes en una muestra común**. No reproduce exactamente los resultados históricos: pueden cambiar la muestra, el preprocesamiento o el optimizador respecto al entrenamiento original.

Un cero de DVC significa «ningún incidente registrado» en una celda/año con tráfico disponible. Los incidentes fuera de las celdas/años elegibles se cuentan y se excluyen; no se añaden celdas sin tráfico como ceros. Los conflictos, longitudes ausentes y formatos direccionales ambiguos bloquean la celda/año correspondiente. La fuente prevista es AADF anual combinado para ambos sentidos; un archivo direccional exige otra preparación explícita.

## Leer los resultados

- `resumen_auditoria.json`: estado de la ejecución, duplicados/conflictos, exclusiones, hashes de los originales y limitaciones.
- `comparacion_exposicion_celda_anio.csv`: comparación de denominadores y elegibilidad. Un valor ausente no significa cero.
- `filas_a_revisar.csv`: duplicados exactos y registros bloqueados; `source_row` es el índice, desde cero, de las filas filtradas de Scotland.
- `calidad_estimaciones_trafico.csv`: conteos según el método del DfT, si está disponible.
- `metricas_poisson.csv`: MAE, RMSE, R² y devianza Poisson; menores errores/devianza indican mejor ajuste de conteos en esta muestra. `observed_over_predicted` compara los totales; cerca de 1 no prueba calibración individual.
- `predicciones_poisson_experimento.csv`: conteos esperados y tasas de ambos experimentos, con las exposiciones de evaluación.
- `modelos/*.joblib`: cuatro modelos con sus preprocesadores y escalados. Para predecir un conteo: `model.predict(preprocessor.transform(X)) / target_scale * exposición`.

La revisión geométrica y la correspondencia entre incidentes y vías siguen pendientes aunque el Poisson termine. No se promueve automáticamente ningún resultado al frontend. Para valorar el porcentaje por trayecto se necesitan, además, tramos reales, cobertura consistente y evaluación del modelo de riesgo individual. El tráfico anual tampoco permite distinguir dos días concretos del mismo mes.

## Verificación de esta entrega

Las pruebas del cálculo por tramo, duplicados, datos desconocidos y particiones temporales se han superado con datos sintéticos aislados. El notebook también se ejecutó completo con una fuente de prueba y generó cuatro modelos; se verificaron los avisos si faltan originales. Estas comprobaciones no son resultados del dataset real ni validan probabilidades individuales. Las pruebas de regresión del cálculo se incluyen en `tests/test_traffic_exposure_audit.py`.
