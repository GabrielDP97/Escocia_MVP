# Riesgo aproximado: acumulado / días / media de aforos de la ruta

$$\overline F_{ruta}=\frac{1}{N}\sum_{i=1}^{N}F_i,\qquad A=\sum_i DVC_{i,mes},\qquad Riesgo_{aprox}(\%)=100\frac{A}{d_{mes}\overline F_{ruta}}.$$

Cada punto del mapa representa una celda de 10 × 10 km. Su valor $F_i$ se obtiene como la media de los aforos AADF únicos de **esa carretera, celda y año 2017**. Después se calcula la **media aritmética de los valores de todos los puntos del mapa**, con igual peso por punto y sin ponderar por longitud. Esta es la afluencia diaria aproximada usada automáticamente en el frontend.

Se acumulan los conteos esperados mensuales del Poisson de todas las celdas con datos, una vez por celda. Los días del mismo mes comparten la estimación. El volumen mensual aproximado de tráfico es la media diaria multiplicada por los días del mes.

**La media de aforos aproxima afluencia; no cuenta vehículos que completan toda la ruta.** Los DVC pertenecen a celdas y pueden incluir otras carreteras. El cociente aproxima una probabilidad para eventos raros y no está validado a nivel individual. Los huecos quedan sin evaluar; no tienen riesgo cero.

Necesita `numpy` y `pandas`. Contiene una referencia comprimida de conteos y coordenadas del frontend, pero **no los aforos originales**. Para calcular la afluencia necesitas el CSV AADF original o su exportación `data/route_traffic_2017.csv`. Si faltan aforos de algún punto, el porcentaje queda pendiente; no se calcula una media parcial.

En el paquete V20, `Roadkill_Abrir_Frontend.ipynb` prepara automáticamente los aforos antes de abrir la aplicación cuando encuentra `Datos/trafico/aadf_data/dft_traffic_counts_aadf.csv` en la aplicación o sus carpetas superiores. También permite indicar `AADF_CSV_OVERRIDE` si está en otra ubicación.

## Usarlo en el frontend V20

1. Coloca el AADF original en `Datos/trafico/aadf_data/dft_traffic_counts_aadf.csv` de tu repositorio y la aplicación dentro de ese repositorio, o indica su ruta en `AADF_CSV_OVERRIDE` del launcher.
2. Ejecuta `Roadkill_Abrir_Frontend.ipynb`. Preparará `data/route_traffic_2017.csv` antes de abrir el frontend.
3. Selecciona carretera, mes y fecha. La tarjeta **Vehículos diarios medios · ruta** calcula la media de los puntos automáticamente. No hay que introducir un aforo manual.
4. Consulta la operación en «Ver operación y supuestos».

Si el archivo AADF falta, la aplicación abre pero conserva el porcentaje pendiente. Si un punto tiene aforo ausente, contradictorio o direccional ambiguo, su media queda bloqueada. Los ceros reales se conservan; si toda la media es cero no se divide entre cero.

La tarjeta «DVC esperados» sigue describiendo la celda seleccionada. «DVC acumulados del mes» suma las celdas disponibles. Avanzar por el mapa o invertir el sentido mantiene el acumulado y la media. La fecha no distingue días dentro del mes. Una tasa superior a 1 se conserva como tasa pero no se muestra como porcentaje de probabilidad.

Para actualizar el original, indica `AADF_CSV_OVERRIDE` y vuelve a ejecutar el launcher; reemplaza solo la exportación de aforos y no los resultados de modelos. Después reinicia el servidor. El notebook independiente guarda su informe en `artifacts/riesgo_diario_ruta/`; si se ejecuta fuera de la carpeta de la aplicación, indica `CARPETA_APP_OVERRIDE` para escribir la exportación donde el frontend pueda cargarla.

## Verificación de esta entrega

Las 67 pruebas del proyecto pasaron. El frontend compiló. El cálculo automático,
la exportación desde AADF, el notebook independiente, la sección global y la celda
de preparación del launcher se comprobaron con aforos sintéticos aislados y los
conteos publicados de referencia. Los aforos de prueba no se entregan ni se presentan
como aforos medidos. Los datos AADF originales no están disponibles aquí: la ejecución
sobre esos originales y los valores reales de afluencia quedan pendientes de ejecutarse
en el repositorio que los contiene. Esto verifica el código, no el riesgo individual.
