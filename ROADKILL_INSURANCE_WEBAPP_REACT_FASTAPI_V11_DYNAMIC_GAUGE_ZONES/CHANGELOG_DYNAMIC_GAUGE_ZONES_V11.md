# V11 · Zonas dinámicas del Risk Response Gauge

## Problema corregido

En V10 la aguja, el número del score, el mapa y el estado textual respondían al umbral seleccionado, pero los tramos de color del arco del gauge seguían usando cortes visuales fijos. Eso podía hacer que la aguja indicase `Alerta` mientras visualmente caía sobre una zona de otro color.

## Solución

El backend convierte ahora los tres límites probabilísticos del estado visual al mismo percentil empírico 0–100 del `Risk Response Score`:

- `Normal → Vigilancia`: `threshold - 0.05`
- `Vigilancia → Alerta`: `threshold`
- `Alerta → Alerta alta`: `threshold + 0.10`

El frontend recibe esos tres percentiles y redibuja el arco completo cada vez que cambia el selector de umbral. Por tanto, la posición de la aguja, la marca del umbral y el color de fondo del gauge usan la misma escala.

## Colores

- Normal: azul petróleo
- Vigilancia: ámbar
- Alerta: naranja-rojo
- Alerta alta: granate

Los colores del mapa y los del gauge siguen la misma máquina de estados.

## Validación

Se añadieron pruebas que verifican que, para los siete umbrales disponibles y todas las observaciones 2017, la zona del gauge coincide con el estado calculado desde la probabilidad.
