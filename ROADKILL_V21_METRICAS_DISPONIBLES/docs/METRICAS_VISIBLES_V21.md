# Riesgo aproximado: acumulado / días / media de tráfico de los puntos

$$\overline F_{ruta}=\frac{1}{N}\sum_iF_i,\qquad Riesgo_{aprox}(\%)=100\frac{\sum_iDVC_{i,mes}}{d_{mes}\overline F_{ruta}}.$$

El modo **automático** usa los aforos AADF 2017 de la carretera cuando existe su exportación. Si falta esa exportación, la demo usa el **perfil histórico de tráfico por celda incluido en el proyecto**, sin necesitar datos brutos. El origen aparece en la pantalla y en el informe.

El perfil histórico se obtiene con `expm1(log_traffic_mean)`: el notebook original de clustering aplica `log1p` al promedio de tráfico de los años disponibles entre **2008 y 2017**. Es una media de **todas las vías de cada celda**, no un aforo de la A82 en 2017 ni el tráfico observado en mayo. El escenario combina los conteos esperados de 2017 con esta afluencia histórica aproximada. Se usa la media aritmética de los valores de los puntos del mapa, con igual peso por celda.

La referencia comprimida contiene los conteos, las coordenadas y el perfil histórico publicados en el proyecto. Estos valores no son datos sintéticos. No se inventan aforos de 2017 ni se reconstruyen a partir de vehículos-km. Para usar aforos específicos de 2017, prepara `data/route_traffic_2017.csv` desde el AADF original.

Los DVC de una celda pueden pertenecer a otras carreteras. La media de tráfico no identifica vehículos que completan toda la ruta. El cociente aproxima una probabilidad para eventos raros y no está validado a nivel individual. Los huecos quedan sin evaluar. Los días del mismo mes comparten la estimación.

Se necesita `numpy` y `pandas`. Ejecuta las celdas en orden. En `AFLUENCIA` puedes elegir `auto`, `aadf_2017` o `historical_profile`. El modo estricto `aadf_2017` conserva el porcentaje pendiente si falta su fuente o el aforo de algún punto; no sustituye registros contradictorios por medias históricas.

## Abrir la demo V21

Descomprime el paquete y ejecuta `Roadkill_Abrir_Frontend.ipynb`. La demo muestra las métricas usando la media histórica de las celdas cuando no está disponible el AADF 2017. En «Origen de afluencia» puedes seleccionar la fuente; el modo automático prioriza AADF 2017 si existe su exportación.

Para A82 en mayo, la referencia histórica incluida da unos **6426,45 vehículos diarios medios**, un acumulado de **10,79 DVC esperados** y un riesgo aproximado de **0,00542 %** bajo estos supuestos. La afluencia es histórica por celda, no un aforo medido de A82 en mayo de 2017.

Para usar AADF 2017 específico de la carretera, coloca el original en `Datos/trafico/aadf_data/dft_traffic_counts_aadf.csv` del repositorio, o indica su ruta en `AADF_CSV_OVERRIDE` del launcher. La exportación bloquea duplicados contradictorios, tráfico ausente y formatos direccionales ambiguos. Si la exportación existe pero tiene datos incompletos, el modo automático mantiene AADF 2017 y el porcentaje pendiente; no cambia de fuente silenciosamente.

La cobertura sigue correspondiendo a la polilínea de la demo. La distancia no cambia el acumulado ni la media. Una media de tráfico cero no permite dividir y una tasa superior a 1 no se muestra como probabilidad.

## Verificación

Se superaron las 73 pruebas del proyecto y la compilación del frontend. El notebook de cálculo se ejecutó en carpetas aisladas con los modos automático, histórico y AADF 2017 estricto: sus resultados coinciden con los de la API y el modo estricto mantiene el porcentaje pendiente sin su fuente.

También se ejecutó la celda real de arranque: inicia el backend actualizado, reutiliza el proceso cuando los archivos no cambian y reinicia su propio proceso cuando detecta una versión diferente. Se comprobó la respuesta de las métricas servidas por ese proceso.

La procedencia del perfil histórico está documentada en `HISTORICAL_TRAFFIC_PROVENANCE.json`, con el código del notebook original y las huellas de sus archivos. Estas comprobaciones verifican la implementación y la fuente histórica; no validan el cociente como probabilidad individual ni aportan aforos mensuales de la A82.
