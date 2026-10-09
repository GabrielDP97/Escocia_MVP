# V7 · Auditoría temporal estricta de calibración

- Integrado el protocolo ejecutado de Reto 05: subtrain 2008–2015, selection/validation 2016, refit 2008–2016 y test final 2017.
- Documentada e integrada la calibración Platt sobre predicciones OOF temporales 2013–2016.
- Verificada la reducción de Brier en validation: `0.159051 → 0.102692` (≈35,43%).
- Verificado el aporte adicional del Nivel 2 estacional: Brier `0.102692 → 0.100471`, PR-AUC `0.546662 → 0.572252`.
- Recalculado desde el CSV del ZIP el test final 2017: ROC-AUC `0.852175`, PR-AUC `0.616802`, Brier `0.103348`.
- Añadida reconciliación explícita con la cifra `0.0799 → 0.0175` del documento global: no se reproduce bajo el protocolo temporal estricto de Reto 05.
- Nuevo endpoint `/api/technology/strict-temporal-audit` y nueva sección en la interfaz.
- Nuevos artefactos JSON/CSV y tests de regresión metodológica.
