# Roadkill · frontend con nombres de modelos y comparativas completas

La nueva MLP de presencia del capítulo 8 sustituye a la DNN anterior en la interfaz.
El score principal sigue siendo Random Forest + Platt + ajuste estacional; la LSTM
original conserva su función de comparación temporal.


## Comparación de todos los modelos

El laboratorio incluye 17 tablas con 66 resultados de modelos, extraídos de las
salidas de los dos notebooks ejecutados adjuntos. Se filtran por tarea, fase y modelo:

- Presencia: 14 candidatos tabulares en validación, etapas Random Forest + Platt +
  ajuste estacional, perceptrón, regresión logística, Random Forest, MLP, LSTM,
  SimpleRNN y regresión logística con retardos.
- Recuentos por celda: regresión lineal, Ridge, Lasso, SVR, Poisson, binomial negativa,
  red neuronal lineal, media y MLP; incluye selección de arquitectura y AIC/BIC.
- Intensidad: clase mayoritaria, regresión logística y MLP softmax.
- Recuentos mensuales: persistencia, naive estacional, Ridge, MLP y LSTM con ventana.

Los modelos clásicos del primer notebook se evaluaron principalmente en validación
2016. Solo se publican métricas de test donde el notebook las tiene. No se mezclan
validación y test ni se calcula un ranking global entre tareas y muestras diferentes.
Los modelos temporales de presencia conservan las métricas de los artefactos
originales: su notebook original no está incluido en los dos archivos nuevos.

La interfaz usa nombres de modelos en textos, leyendas y mensajes del backend.
Las referencias técnicas originales permanecen en los notebooks para conservar
su trazabilidad, pero los archivos se descargan desde la interfaz con nombres descriptivos.

Para regenerar las tablas desde las salidas, sin entrenar ni modificar resultados:

```bat
.venv\Scripts\python.exe scripts\extract_notebook_metrics.py
```

## Resultados de la MLP de presencia

Test 2017: 6.336 observaciones, 528 celdas y 1.148 positivos.
Train 2009–2015; validation 2016; umbral seleccionado en validation: 0,2822222222.
Arquitectura Dense 64 → Dense 32 → sigmoid, Dropout 0,15 y L2 1e-5. Sin Platt adicional.

| Métrica | Resultado |
|---|---:|
| ROC-AUC | 0,8441 |
| AP | 0,6026 |
| Brier | 0,1055 |
| F1 | 0,5560 |
| Precisión | 0,5252 |
| Recall | 0,5906 |
| Accuracy | 0,8291 |

TP 678, FP 613, TN 4.575, FN 470; 1.291 alertas.
Las cifras probabilísticas conservan los cuatro decimales de las salidas ejecutadas;
no se presenta precisión adicional inventada.

El laboratorio muestra también la ejecución del notebook comparativo sobre 6.312
filas comunes. Allí la MLP se reentrenó y obtuvo ROC-AUC 0,841542, AP 0,595816,
Brier 0,106472 y F1 0,553263. Se identifican como otra ejecución y muestra.
Los dos notebooks completos están incluidos en `evidencias/` y se descargan desde
los enlaces del laboratorio. No se han modificado sus pruebas ni sus resultados.

## Ejecutar en Windows

1. Descomprime este ZIP en una carpeta nueva.
2. Ejecuta `setup_windows.bat` (requiere Python 3.10+ y Node.js 20+).
3. Ejecuta `build_and_run_windows.bat`.
4. La aplicación se abre en http://127.0.0.1:8000.

El ZIP incluye el frontend compilado. Para arrancar solo el backend, tras instalar:

```bat
.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

## Incorporar las probabilidades MLP reales

Los notebooks adjuntos contienen métricas y matrices, pero sus CSV exportados
están en el equipo donde se ejecutaron. Este paquete no contiene probabilidades
MLP por celda. La demo muestra «—» para ellas y no calcula ensembles con la DNN vieja.
Los benchmarks con predicciones disponibles comparan principal y LSTM; las tablas
de los notebooks se muestran por separado, con su propia muestra y procedencia.

Para incorporar exactamente la ejecución del capítulo 8, ejecuta desde esta carpeta:

```bat
.venv\Scripts\python.exe -m backend.import_mlp "C:\Users\Gabriel\Documents\GitHub\IA\artifacts\reto08_capitulo8_completo"
```

El importador lee `configuracion.json` y `predicciones_test_2017_cap8.csv`.
Comprueba umbral, ausencia de modo breve, muestra, etiquetas y métricas antes de
copiar las probabilidades. Rechaza otras ejecuciones o una DNN renombrada.
Reinicia el backend después de importar. La demo incorporará las probabilidades
MLP y se recalcularán los ensembles exploratorios con la intersección real.
No se modifica el modelo principal ni se seleccionan pesos mirando test 2017.

## Verificación

```bat
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
```

Los resultados de calibración de la DNN anterior y sus ensembles se han retirado.
La auditoría raw → calibrado sigue correspondiendo a SimpleRNN y LSTM originales.
Las métricas del principal corresponden a su ejecución archivada y su umbral
0,2425809815683556; no se mezclan con el nuevo umbral de la réplica de Reto5.

## Inicio desde Jupyter

Abre `Roadkill_Abrir_Frontend.ipynb` en la carpeta principal y ejecuta todas sus celdas.
La primera vez instala las dependencias de Python; luego abre la aplicación en el
navegador sin usar los `.bat`. No requiere Node.js para utilizar el frontend compilado.
Consulta `LEEME_INICIO_JUPYTER.md`.

## Estimación experimental solo en zonas con datos

La demo muestra una probabilidad restringida a kilómetros dentro de celdas BNG
con datos. Cada punto representa una celda de 10 × 10 km. Se recorta la polilínea
por la cuadrícula y no se extrapolan tasas a los huecos. Se muestran kilómetros
con datos, kilómetros sin evaluar y cobertura. Con cobertura parcial, la
probabilidad del recorrido completo queda sin estimar: lo desconocido no es cero.

Las tasas son mensuales y corresponden a 2017. El trazado, la exposición y el
riesgo individual siguen siendo aproximados y experimentales. Una distancia
introducida escala el escenario sin inventar cobertura. El notebook global
incluye el cálculo y las comprobaciones de cobertura.

Consulta `docs/ESTIMACION_TRAYECTO_EXPERIMENTAL.md`.



## Métricas disponibles en la demo — V21

Descomprime esta versión en una carpeta nueva y ejecuta `Roadkill_Abrir_Frontend.ipynb`.
El modo automático usa aforos específicos AADF 2017 si existe su exportación.
Si falta, usa la media histórica 2008–2017 de las celdas incluida en el ZIP.
La tarjeta y los supuestos muestran explícitamente el origen. El selector
«Origen de afluencia» permite elegir automáticamente, AADF 2017 o perfil histórico.

El perfil histórico se recupera con `expm1(log_traffic_mean)`, inversa del `log1p`
documentado en el notebook original de clustering. Incluye todas las vías de
cada celda y los años disponibles entre 2008 y 2017; no es un aforo de la carretera
seleccionada en 2017. La operación conserva `acumulado / días / media diaria × 100`
como aproximación experimental. No mide viajes completos ni valida riesgo individual.

Para A82 en mayo, el perfil incluido da 10,79 DVC mensuales acumulados, 0,348 diarios,
6426,45 vehículos diarios medios históricos y aproximadamente 0,00542 %.
Para datos específicos de 2017, indica el AADF original en `AADF_CSV_OVERRIDE` del
launcher o usa `Roadkill_Preparar_Afluencia_Ruta.ipynb`. El modo estricto mantiene
el resultado pendiente si sus aforos faltan. La cobertura no interpreta los huecos
como riesgo cero. El launcher reinicia su propio servidor al detectar cambios de
código o datos para evitar resultados de una versión anterior.

Véase `docs/METRICAS_VISIBLES_V21.md` y `docs/HISTORICAL_TRAFFIC_PROVENANCE.json`.
