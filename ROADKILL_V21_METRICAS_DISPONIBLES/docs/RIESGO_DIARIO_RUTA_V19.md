# Riesgo aproximado por pasada: acumulado / días / afluencia de la ruta

La nueva operación del frontend es:

$$A=\sum_i DVC_{i,mes},\qquad T=\frac{A}{d_{mes}\,F_{ruta}},\qquad Riesgo_{aprox}(\%)=100T.$$

Se acumulan los **conteos esperados mensuales del Poisson de todas las celdas disponibles**, una vez por celda. $F_{ruta}$ es una única media diaria de vehículos que realizan el recorrido completo. La afluencia debe aportarla el usuario: los archivos actuales no contienen ese dato y no se inventa ni se sustituye por el promedio de aforos por punto.

El cociente es una tasa media por paso de vehículo; aproxima una probabilidad para eventos raros. Se aplica al día elegido suponiendo que el riesgo y el tráfico son uniformes en el mes. **Todos los días de mayo producen la misma estimación si la afluencia introducida es la misma.**

Los conteos son de celdas de 10 × 10 km y pueden incluir otras carreteras. La correspondencia entre los incidentes y los vehículos que completan la ruta no está comprobada. Los tramos sin datos quedan sin evaluar; no tienen riesgo cero. El resultado es un escenario experimental para zonas con datos, no una probabilidad individual validada de la ruta completa.

Este notebook es independiente, necesita `numpy` y `pandas`, e incluye una referencia comprimida de los conteos y coordenadas publicados en la aplicación. No contiene los originales AADF/DVC ni un aforo real de recorridos completos. Ejecuta las celdas en orden y cambia la configuración de la siguiente celda.

## Usarlo en el frontend

1. Abre `Roadkill_Abrir_Frontend.ipynb` del paquete V19 y ejecuta sus celdas.
2. En la demo, selecciona carretera, mes y fecha histórica.
3. Introduce **Vehículos diarios · ruta completa**. Sin esa afluencia, las tarjetas mensual y diaria se calculan y el porcentaje queda pendiente.
4. La nueva tarjeta muestra el riesgo aproximado usando `acumulado / días / afluencia × 100`. Al cambiar de carretera o mes se borra la afluencia para evitar reutilizar un dato de otro escenario.

La tarjeta original «DVC esperados» sigue describiendo la celda seleccionada. La nueva tarjeta «DVC acumulados del mes» corresponde a todas las celdas disponibles de la ruta. Avanzar por el mapa no modifica el acumulado.

Una tasa superior a 1 se conserva como tasa en el informe, pero se bloquea su presentación como porcentaje de probabilidad; no se recorta artificialmente al 100 %. La distancia introducida escala la cobertura de la demo y no este cálculo por conteos. No cambia los modelos históricos ni las etiquetas de presencia del Random Forest.

## Verificación de la entrega

Se superaron las 59 pruebas del proyecto, incluidas las nuevas comprobaciones de
la operación, duplicados, conteos ausentes, afluencia inválida, sentido de la ruta
y fecha histórica. El frontend compiló y sus archivos se sirvieron desde la API.
El notebook se ejecutó con la referencia real de conteos publicada en la aplicación:
con afluencia vacía conserva el porcentaje pendiente; con una afluencia de prueba
explícita coincide con la API. También se ejecutó la nueva sección global de forma
independiente. Los aforos de prueba no son aforos medidos de la A82. Estas comprobaciones
verifican implementación y consistencia, no calibración del riesgo individual.
