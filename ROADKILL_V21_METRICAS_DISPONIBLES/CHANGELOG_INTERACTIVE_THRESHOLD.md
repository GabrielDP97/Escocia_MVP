# V9 · Umbral interactivo en Driver Experience

- Añade un selector de **Umbral de alerta** directamente en la barra superior del frontend.
- Opciones: 0,10 · 0,15 · 0,20 · 0,242581 oficial · 0,30 · 0,40 · 0,50, obtenidas del endpoint de auditoría cuando está disponible.
- El umbral seleccionado actualiza en tiempo real:
  - estado de alerta de la celda;
  - línea horizontal del gráfico de riesgo;
  - activación de la respuesta preventiva;
  - métricas descriptivas de 2017: precision, recall, F1, FP y FN.
- El umbral 0,242581 se identifica como **oficial / validado en 2016**.
- Cualquier otro umbral queda marcado como **simulación exploratoria post-hoc sobre 2017** y puede restablecerse con un botón.
- No se modifica el umbral oficial almacenado en backend ni se reoptimiza sobre el test.
