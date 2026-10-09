## Estimación experimental restringida a zonas con datos

Cada punto representa una **celda BNG de 10 × 10 km**, no un círculo de radio 10 km. Se recorta la polilínea de la demo por los límites exactos de la cuadrícula. Solo se calcula riesgo para los kilómetros dentro de celdas de la ruta con DVC esperados y exposición válidos. **No se interpola a través de huecos y no se asigna riesgo cero a zonas sin información.**

En cada celda conocida: `r_i = DVC_esperados_i / vehiculos_km_i`. En sus kilómetros representados: `H_datos = Σ km_i × r_i`. La probabilidad experimental para esas zonas es `p_datos = 1 − exp(−H_datos)`. Si hay distancia sin datos, `full_route_probability` queda en `None`: no tenemos una probabilidad para la ruta completa. Se informa de kilómetros cubiertos, kilómetros sin evaluar y porcentaje de cobertura.

Este código se usa también en el backend. Las comprobaciones verifican la aritmética, la delimitación y los artefactos; no validan el riesgo real de un conductor. Se asumen tasas homogéneas dentro de la celda y el mes, tráfico representativo y un proceso Poisson. No se corrige subregistro ni los sesgos de exposición. La cobertura corresponde a las líneas aproximadas de la demo y no al asfalto real. La fecha selecciona el mes histórico de 2017 y no incorpora información diaria.

Fuentes metodológicas: [FHWA: tasas y exposición](https://www.fhwa.dot.gov/publications/research/safety/17106/005.cfm), [NIST: distribución de Poisson](https://www.itl.nist.gov/div898/handbook/eda/section3/eda366j.htm). La combinación con los datos del proyecto es un modelo de escenario propio; estas fuentes no lo validan.

La tarjeta del frontend se llama «Probabilidad en zonas con datos · experimental». Su cobertura se muestra en kilómetros y porcentaje. Si falta cobertura, se indica expresamente que la ruta completa no es estimable.
