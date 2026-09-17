# V4 - Respuesta preventiva dinámica

La respuesta preventiva ya no cambia por saltos fijos de 10/20 mph.

## Nueva lógica

1. La intervención solo se activa cuando `p_final` supera el umbral seleccionado en validation (`~0.2426` en Reto 05).
2. Una vez activa, la intensidad depende de forma continua del **Risk Response Score**.
3. Entre score 60 y 100, la reducción objetivo crece linealmente entre 0 y 20 mph.
4. El sistema recalcula en cada punto de la ruta:
   - intensidad de respuesta;
   - velocidad objetivo preventiva;
   - distancia de parada actual;
   - distancia de parada con respuesta;
   - reducción aproximada en metros.
5. Nunca se recomienda acelerar: si la velocidad simulada ya es inferior al objetivo preventivo, se conserva la velocidad actual.

## Ejemplo con límite de 60 mph

- Score 60 -> 60 mph
- Score 70 -> 55 mph
- Score 80 -> 50 mph
- Score 90 -> 45 mph
- Score 100 -> 40 mph

La velocidad concreta sigue siendo una **regla de demostración**, no una recomendación legal ni una salida entrenada por el modelo.
