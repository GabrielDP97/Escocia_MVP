# Actualización del simulador económico

## Cambios

- El número de vehículos asegurados entra ahora directamente en el cálculo.
- Fórmula principal:
  `claims DVC esperados = vehículos / 1.000 × frecuencia DVC por 1.000 vehículos/año`
- Se añaden tres modos:
  1. Referencia UK reciente (Zurich + DfT).
  2. Referencia histórica Fortis 2004-2005.
  3. Datos propios / escenario personalizado.
- Se muestran las fuentes dentro del propio frontend.
- La frecuencia de referencia UK reciente se marca como un **proxy derivado**, no como una tasa actuarial oficial de Zurich.
- La reducción preventiva sigue marcada como **hipótesis**, pendiente de validación mediante piloto.

## Preset UK reciente

- Frecuencia proxy: 0,4844 DVC claims / 1.000 vehículos/año.
- Derivación: 32.000 claims de animales/año × 61% ciervos ≈ 19.520 DVC claims; 19.520 / 40,3 M vehículos × 1.000.
- Coste medio DVC: £4.317,24 (Zurich UK, claims 2024).

## Preset Fortis histórico

- Frecuencia: 428 DVC claims / ~1,2 M pólizas privadas × 1.000 ≈ 0,3567 / 1.000.
- Coste medio por DVC claim: £1.320 (2004).

## Fuentes

- Zurich UK 2025: https://www.zurich.co.uk/media-centre/oh-deer-motorists-warned-spring-time-deer-collisions
- Zurich UK 2021: https://www.zurich.co.uk/media-centre/staycation-boom-drives-54-percent-increase-in-wildlife-fatalities-on-uk-roads
- DfT/DVLA 2021: https://www.gov.uk/government/statistics/vehicle-licensing-statistics-2021/vehicle-licensing-statistics-2021
- National Deer-Vehicle Collisions Project / Fortis: https://www.deercollisions.co.uk/web-content/ftp/DVC_England_FinalAs.pdf
