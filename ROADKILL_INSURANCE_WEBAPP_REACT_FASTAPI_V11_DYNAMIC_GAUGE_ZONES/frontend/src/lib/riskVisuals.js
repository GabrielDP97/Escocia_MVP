export const RISK_VISUAL_STATES = {
  normal: {
    key: "normal",
    label: "Normal",
    banner: "RIESGO BAJO EL UMBRAL",
    color: "#2b7a8f",
    soft: "#e8f7f5",
    border: "#bde7e2",
  },
  watch: {
    key: "watch",
    label: "Vigilancia",
    banner: "VIGILANCIA · CERCA DEL UMBRAL",
    color: "#d99a28",
    soft: "#fff6df",
    border: "#efd79a",
  },
  alert: {
    key: "alert",
    label: "Alerta",
    banner: "ALERTA MODELO ACTIVA",
    color: "#d26342",
    soft: "#fff0e9",
    border: "#f0c5b5",
  },
  critical: {
    key: "critical",
    label: "Alerta alta",
    banner: "ALERTA ALTA",
    color: "#9c3040",
    soft: "#fbeaec",
    border: "#edbcc4",
  },
};

export function riskVisualState(probability, threshold) {
  const p = Math.max(0, Math.min(1, Number(probability) || 0));
  const cut = Math.max(0, Math.min(1, Number(threshold) || 0));
  const watchStart = Math.max(0, cut - 0.05);
  const criticalStart = Math.min(1, cut + 0.10);

  if (p < watchStart) return RISK_VISUAL_STATES.normal;
  if (p < cut) return RISK_VISUAL_STATES.watch;
  if (p < criticalStart) return RISK_VISUAL_STATES.alert;
  return RISK_VISUAL_STATES.critical;
}

export function riskVisualLegend(threshold) {
  const cut = Math.max(0, Math.min(1, Number(threshold) || 0));
  return [
    { ...RISK_VISUAL_STATES.normal, rule: `< ${(Math.max(0, cut - 0.05) * 100).toFixed(0)}%` },
    { ...RISK_VISUAL_STATES.watch, rule: `${(Math.max(0, cut - 0.05) * 100).toFixed(0)}–${(cut * 100).toFixed(0)}%` },
    { ...RISK_VISUAL_STATES.alert, rule: `${(cut * 100).toFixed(0)}–${(Math.min(1, cut + 0.10) * 100).toFixed(0)}%` },
    { ...RISK_VISUAL_STATES.critical, rule: `≥ ${(Math.min(1, cut + 0.10) * 100).toFixed(0)}%` },
  ];
}
