# Corrección Reto 07 · NLP & Text Mining

Esta versión sustituye en la aplicación las referencias del antiguo Hurdle 1D atribuidas al Reto 07 por los resultados del notebook vigente `07_NLP_Text_Mining_Escocia`.

## Métricas integradas

- Documentos padre: 37
- Chunks: 256
- Modelo seleccionado: MultinomialNB
- Accuracy validation: 0.980769
- Macro-F1 validation: 0.975758
- Accuracy test: 0.920000
- Macro-F1 test: 0.922969
- Balanced accuracy test: 0.937500
- Weighted-F1 test: 0.916527
- K-Means documental: k=6
- Silhouette: 0.453931
- ARI vs dominio documental: 0.7449

La interfaz incluye además la comparación con LogisticRegression, LinearSVC, CNN1D_LSTM, LSTM y DummyMostFrequent.

## Cambios técnicos

- Nuevo artefacto: `data/reto07_nlp_metrics.json`.
- Nuevo endpoint: `GET /api/technology/reto7-nlp`.
- Nuevo módulo: `backend/reto7_nlp.py`.
- `TechnologyLab.jsx` incorpora un bloque específico de Reto 07 NLP.
- Se elimina del backend operativo la afirmación de que Reto 07 es Hurdle 1D.
- Se actualizan capacidades, auditoría y documentación principal.
- Se añade `tests/test_reto7_nlp.py`.

## Verificación

- Backend: 21 tests superados.
- Endpoint Reto 07: HTTP 200 y métricas verificadas.
- Sintaxis JSX de `TechnologyLab.jsx`: validada con `@babel/parser`.

## Compilación del frontend

Este paquete no incluye un `frontend/dist` precompilado, para evitar servir el bundle antiguo del ZIP original. En Windows:

```bat
cd frontend
npm install
npm run build
```

O en modo desarrollo:

```bat
cd frontend
npm install
npm run dev
```
