# V10 · Visualización dinámica del riesgo según umbral

La pantalla **Driver Experience** ya no cambia únicamente el texto de alerta al seleccionar un umbral. La representación visual completa responde al corte activo.

## Cambios

- Los puntos del mapa cambian de color según `p_final` frente al umbral seleccionado.
- Los tramos de la polilínea adoptan el estado del punto de destino para visualizar dónde aumenta o disminuye el riesgo.
- Se usan cuatro estados coherentes en toda la pantalla:
  - **Normal:** `p < umbral - 0,05`
  - **Vigilancia:** `umbral - 0,05 <= p < umbral`
  - **Alerta:** `umbral <= p < umbral + 0,10`
  - **Alerta alta:** `p >= umbral + 0,10`
- La aguja del **Risk Response Score**, su centro y el número grande cambian de color con el estado actual.
- El banner inferior del gauge usa esos mismos cuatro estados.
- Se añade una leyenda al mapa.
- El gauge incorpora una marca del umbral en la escala del Risk Response Score.

## Importante: probabilidad y Risk Response Score no son la misma unidad

El umbral se define sobre `p_final` (probabilidad), mientras que el Risk Response Score es el percentil 0–100 de `p_final` dentro del test 2017. Para poder situar el corte en el gauge sin mezclar unidades, el backend calcula el **percentil empírico equivalente** del umbral sobre la distribución 2017.

Ejemplo: el umbral oficial `0,242581` se sitúa aproximadamente en el percentil **77,65/100** de la distribución del test. Esta marca es una traducción empírica para visualización, no significa que `0,242581 = 24,26/100` en el gauge.

## Validación

- Suite Python: **17 tests superados**.
- Los cuatro ficheros frontend modificados se han validado sintácticamente con `@babel/parser` y JSX.
- En este entorno no se ha completado el build Vite porque las dependencias opcionales nativas de Rollup disponibles son de Windows y no del contenedor Linux. El ZIP no incluye `node_modules`; en Windows, `npm install`/`npm run build` instalará las dependencias correctas para la plataforma.
