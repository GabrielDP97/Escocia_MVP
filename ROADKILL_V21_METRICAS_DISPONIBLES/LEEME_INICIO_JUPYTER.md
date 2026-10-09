# Abrir la aplicación desde Jupyter

1. Descomprime este paquete conservando sus carpetas.
2. Abre `Roadkill_Abrir_Frontend.ipynb`, situado en la carpeta principal.
3. Usa un kernel local de Python 3.10 o superior y ejecuta todas las celdas.
4. La primera vez se instalan las dependencias de Python; después se reutilizan.
5. Se abre el navegador. Si no se abre, pulsa el enlace que muestra el notebook.

No necesitas los `.bat`, Node.js ni el servidor de datasets para este arranque.
El frontend compilado ya está incluido. Para cambiar y recompilar el código React,
sí necesitarás Node.js y las herramientas originales.

Deja Jupyter abierto durante la demostración. Para detener la aplicación, ejecuta
`detener_app()` o activa la celda opcional de cierre. Antes de reiniciar el kernel,
detenla para evitar dejar un proceso anterior en segundo plano.

El notebook detecta esta carpeta desde el directorio de trabajo y sus padres.
Si Jupyter trabaja desde otra ubicación, configura `CARPETA_APP` en su primera celda.
No es necesario cambiar el notebook global de entrenamiento ni las métricas.



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
