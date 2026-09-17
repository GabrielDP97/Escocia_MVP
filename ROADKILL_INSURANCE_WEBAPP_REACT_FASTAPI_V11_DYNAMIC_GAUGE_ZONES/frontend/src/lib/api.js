const configured = import.meta.env.VITE_API_BASE;
export const API_BASE = configured || "";

export async function api(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try { const body = await response.json(); detail = body.detail || detail; } catch {}
    throw new Error(detail);
  }
  return response.json();
}

export const pct = (value, digits = 1) =>
  value == null || Number.isNaN(Number(value)) ? "—" : `${(Number(value) * 100).toFixed(digits)}%`;

export const num = (value, digits = 2) =>
  value == null || Number.isNaN(Number(value)) ? "—" : Number(value).toFixed(digits);

export const compact = (value) =>
  new Intl.NumberFormat("es-ES", { notation: "compact", maximumFractionDigits: 1 }).format(value ?? 0);
