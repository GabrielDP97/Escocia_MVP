import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, compact, pct } from "../lib/api";
import MetricCard from "../components/MetricCard";

export default function Portfolio() {
  const [data, setData] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [minObs, setMinObs] = useState(24);
  const [error, setError] = useState("");

  useEffect(() => { api(`/api/dashboard?min_observations=${minObs}`).then(setData).catch((e) => setError(e.message)); }, [minObs]);
  useEffect(() => { api("/api/metadata").then(setMetadata).catch((e) => setError(e.message)); }, []);

  return (
    <div>
      <header className="page-header"><div><span className="eyebrow">INSURER PORTFOLIO VIEW</span><h1>Dashboard de riesgo histórico</h1><p>Vista agregada del test 2017 para enseñar cómo el motor podría priorizar una cartera o una red vial.</p></div></header>
      {error && <div className="notice danger">{error}</div>}
      {data && <>
        <div className="metric-grid"><MetricCard label="Observaciones" value={compact(data.summary.observations)} sub="test 2017"/><MetricCard label="Celdas" value={data.summary.cells} sub="BNG 10 km" tone="teal"/><MetricCard label="Carreteras" value={data.summary.roads} sub="con score"/><MetricCard label="Prevalencia" value={pct(data.summary.base_rate)} sub="positivos observados" tone="orange"/></div>
        {metadata && <div className="metric-grid"><MetricCard label="PR-AUC" value={metadata.metrics.pr_auc?.toFixed(3)} sub="ranking clase positiva" tone="teal"/><MetricCard label="ROC-AUC" value={metadata.metrics.roc_auc?.toFixed(3)} sub="separación global"/><MetricCard label="Brier" value={metadata.metrics.brier?.toFixed(3)} sub="calidad probabilística"/><MetricCard label="Lift top 1%" value={`${metadata.metrics.lift_top_1pct_reported?.toFixed(2)}x`} sub={`top 1% positivo: ${pct(metadata.metrics.top1_positive_rate)}`} tone="orange"/></div>}

        <div className="content-grid">
          <div className="panel"><h3>Predicción vs observado por mes</h3><div className="chart-box"><ResponsiveContainer width="100%" height={300}><LineChart data={data.monthly}><CartesianGrid strokeDasharray="3 3" stroke="#dfe8eb"/><XAxis dataKey="month_name"/><YAxis tickFormatter={(v) => `${Math.round(v*100)}%`}/><Tooltip formatter={(v,name) => name === "dvc" ? v : pct(v)}/><Line dataKey="predicted_risk" name="Riesgo predicho" stroke="#13a89e" strokeWidth={3}/><Line dataKey="observed_rate" name="Tasa observada" stroke="#2c7793" strokeWidth={2}/></LineChart></ResponsiveContainer></div></div>
          <div className="panel"><h3>Distribución del score</h3><div className="chart-box"><ResponsiveContainer width="100%" height={300}><BarChart data={data.histogram}><CartesianGrid strokeDasharray="3 3" stroke="#dfe8eb"/><XAxis dataKey="bin_mid" tickFormatter={(v) => `${Math.round(v*100)}%`}/><YAxis/><Tooltip labelFormatter={(v) => `Score ~ ${pct(v)}`}/><Bar dataKey="count" fill="#2c7793" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div></div>
        </div>

        <section className="panel"><div className="section-heading"><div><h3>Carreteras con mayor riesgo medio</h3><p>Evaluación histórica; no es una lista de carreteras “peligrosas” para uso legal.</p></div><label>Mínimo observaciones<select value={minObs} onChange={(e) => setMinObs(Number(e.target.value))}>{[12,24,36,48,60,96,120].map((v) => <option key={v}>{v}</option>)}</select></label></div><div className="table-scroll"><table><thead><tr><th>Carretera</th><th>Obs.</th><th>Celdas</th><th>Riesgo medio</th><th>Máximo</th><th>Tasa positiva</th><th>DVC</th></tr></thead><tbody>{data.top_roads.map((r) => <tr key={r.road_name}><td><b>{r.road_name}</b></td><td>{r.observations}</td><td>{r.cells}</td><td>{pct(r.mean_risk)}</td><td>{pct(r.max_risk)}</td><td>{pct(r.observed_positive_rate)}</td><td>{r.dvc_total}</td></tr>)}</tbody></table></div></section>
        <div className="notice info">El dashboard usa labels históricos de 2017 para evaluación. En una implantación real, los paneles operativos usarían scores actuales y los resultados llegarían después.</div>
      </>}
    </div>
  );
}
