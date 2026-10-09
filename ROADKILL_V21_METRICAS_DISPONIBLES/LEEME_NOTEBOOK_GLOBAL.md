# Notebook global de evaluación

El archivo `evidencias/Roadkill_Evaluacion_Global_Frontend.ipynb` reúne el código de las
pruebas del frontend. También se descarga desde el Laboratorio tecnológico de la aplicación.

## Ejecutarlo

1. Guarda el notebook en `notebooks/escocia/` de tu copia del repositorio compartido.
   Cada compañero lo guarda en la misma carpeta relativa de su propia copia. El nombre
   de usuario y la ubicación del repositorio pueden ser distintos.
2. Ábrelo con Jupyter o con VS Code y selecciona el kernel de tu proyecto.
3. Instala las dependencias indicadas en el propio notebook si faltan.
4. Ejecuta las celdas en orden. El acceso usa las funciones habituales
   `cargar_dataset` / `cargar_archivo`, con prioridad local, servidor configurado y caché.
   No requiere rutas personales ni otro notebook. Si falta la URL compartida del servidor,
   la pide al descargar el primer dataset. Si hace falta un token, lo solicita con entrada
   privada, sin guardarlo en una celda ni imprimirlo.

Desde `notebooks/escocia/`, el cargador encuentra la raíz subiendo dos niveles y busca
los datasets en `Datos/` de esa raíz. También reconoce el repositorio si el kernel arranca
en su raíz o en `notebooks/`. La celda de acceso imprime la raíz detectada y la carpeta
de datos para poder comprobarlas. No añadas `os.chdir(...)` ni una ruta personal.

La URL puede indicarse en `DATA_SERVER_URL_OVERRIDE` o configurarse fuera del notebook con
`IA_DATA_SERVER_URL`. El token se toma de `IA_DATA_API_TOKEN`, la configuración del proyecto
o la entrada privada. Quien reciba el notebook necesita acceso al servidor del proyecto
o una copia de los datasets. El cuaderno no contiene las credenciales.

Por defecto se repiten los entrenamientos. Si quieres comprobar únicamente las métricas
de los CSV archivados, cambia `REENTRENAR = False`. Este modo no necesita los datasets
brutos ni TensorFlow. Los flags `EJECUTAR_RF`, `EJECUTAR_NEURONALES`,
`EJECUTAR_COMPARACION` y `EJECUTAR_NLP` permiten ejecutar una sección cada vez.

La demostración de etiquetas aleatorias incluye su celda de preparación original antes
de usar `demo_random`. Esta demostración es independiente de los datasets y métricas
de Roadkill. Tras sustituir una versión anterior, reinicia el kernel y ejecuta todas las celdas.

La entrega incluye salidas de la auditoría real de los artefactos de la aplicación:
332 comprobaciones coincidentes. Los entrenamientos completos no se han ejecutado en
esta entrega porque los datasets brutos y las credenciales del proyecto no están disponibles
en el entorno de comprobación. No se han sustituido por datos sintéticos.

## Resultados y límites

El informe final distingue resultados recalculados, nuevos entrenamientos y resultados
históricos pendientes. No modifica los CSV de la aplicación automáticamente.
Los nuevos resultados se guardan en `artifacts/evaluacion_global_frontend/` de tu proyecto.

La referencia comprimida del notebook contiene predicciones históricas y resúmenes del
frontend, no datasets brutos AADF/DVC. Cada referencia tiene su hash SHA-256.

- La MLP publicada requiere su CSV de predicciones para comprobar ROC-AUC, AP y Brier.
  Su matriz de confusión permite verificar F1, precision, recall y accuracy.
- La comparación reducida de 6.312 observaciones requiere sus predicciones comunes
  originales para comprobar exactamente aquella ejecución; se incluye el código para repetirla.
- LSTM y SimpleRNN de presencia se evalúan con sus probabilidades originales de test.
  No se dispone del entrenamiento original de esa LSTM: la reconstrucción está identificada
  como otro experimento. Sus predicciones de validation y horizonte t+3 pueden indicarse
  en la configuración. No se conoce el procedimiento y semilla exactos de los IC históricos.
- NLP necesita conservar el corpus/caché y las particiones originales para reproducir
  las mismas cifras. Se incluye el código del notebook NLP entregado.
- Los campos `precision_050`, `recall_050` y `f1_050` del CSV principal tienen nombres
  heredados: sus valores corresponden al umbral seleccionado. El notebook demuestra
  la diferencia respecto a calcularlos realmente con umbral 0,50.
- Los valores económicos son cálculos de escenario con reducción hipotética, no pruebas
  de ahorro conseguido por el modelo.

## Cambio en el frontend

Se han retirado de la demo las tarjetas «LSTM temporal» y «MLP de presencia» indicadas
en la imagen. Los modelos siguen disponibles en las comparativas del Laboratorio.
Se ha añadido un enlace para descargar el notebook global.

## Arrancar la aplicación en Windows

Ejecuta `setup_windows.bat`, después `build_and_run_windows.bat` y abre
`http://127.0.0.1:8000`. Conserva abierta la terminal del servidor.

Validación de la aplicación: 29 pruebas del backend superadas y frontend compilado con Vite.

## Auditoría del tráfico (V18)

El notebook independiente `Roadkill_Auditoria_Trafico_Poisson.ipynb` audita los originales locales y compara dos nuevos Poisson con exposición anterior y suma por tramo. Guarda resultados y modelos aparte; no actualiza automáticamente el frontend. Véase `docs/AUDITORIA_EXPOSICION_POISSON.md`. El notebook global incluye la misma sección al final.



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
