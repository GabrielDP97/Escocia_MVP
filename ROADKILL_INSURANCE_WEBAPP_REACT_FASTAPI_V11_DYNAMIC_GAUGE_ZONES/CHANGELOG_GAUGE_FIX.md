# Corrección del Risk Response Score gauge

Se ha corregido el indicador semicircular de la pantalla **Demo conductor**.

## Problema anterior

La aguja usaba:

```js
const deg = -90 + (bounded / 100) * 180;
```

pero la aguja estaba construida apuntando inicialmente hacia la izquierda. Por eso un score
cercano a 100 terminaba casi vertical y no alcanzaba visualmente la zona derecha.

## Corrección

El gauge se ha redibujado como SVG y ahora el recorrido es exacto:

- **0/100** → extremo izquierdo.
- **50/100** → parte superior.
- **80/100** → comienzo de la zona roja.
- **100/100** → extremo derecho.

Zonas visuales:

- **0–50**: azul.
- **50–80**: naranja.
- **80–100**: rojo.

Ejemplo: con **98/100**, la aguja queda casi en el extremo derecho de la zona roja.

> El Risk Response Score sigue siendo un **percentil relativo**, no una probabilidad.
> La probabilidad DVC aparece debajo como una cifra independiente.
