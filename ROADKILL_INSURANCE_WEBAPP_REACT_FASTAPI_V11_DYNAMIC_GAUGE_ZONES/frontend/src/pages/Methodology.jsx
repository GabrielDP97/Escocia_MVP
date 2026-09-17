import { useEffect, useState } from "react";
import { CheckCircle2, Database, Layers3, ShieldCheck } from "lucide-react";
import { api, pct } from "../lib/api";
import MetricCard from "../components/MetricCard";

export default function Methodology() {
  const [meta, setMeta] = useState(null);
  useEffect(() => { api("/api/metadata").then(setMeta); }, []);
  return <div>
    <header className="page-header"><div><span className="eyebrow">TRANSPARENCY & EVIDENCE</span><h1>Qué está viendo la aseguradora</h1><p>La interfaz separa probabilidad científica, contexto, simulación de producto y auditoría histórica.</p></div></header>
    {meta && <div className="metric-grid"><MetricCard label="PR-AUC" value={meta.metrics.pr_auc?.toFixed(3)} sub="Reto 05 · test 2017" tone="teal"/><MetricCard label="ROC-AUC" value={meta.metrics.roc_auc?.toFixed(3)} sub="Reto 05 · test 2017"/><MetricCard label="Brier" value={meta.metrics.brier?.toFixed(3)} sub="probabilidad calibrada"/><MetricCard label="Prevalencia" value={pct(meta.base_rate)} sub="positivos test" tone="orange"/></div>}
    <div className="method-grid"><section className="panel method-card"><Database size={25}/><h3>Datos</h3><p>AADF + DVC Scotland. El test mostrado corresponde a 2017. 2018 se excluyó del modelado por cobertura DVC incompleta.</p></section><section className="panel method-card"><Layers3 size={25}/><h3>Score principal</h3><p>Reto 05: Random Forest calibrado + modulador estacional. La LSTM y la DNN aparecen como corroboración, no como promedio automático.</p></section><section className="panel method-card"><ShieldCheck size={25}/><h3>Uso responsable</h3><p>El MVP prioriza riesgo y explora prevención. No decide automáticamente una prima, no sustituye límites legales y no demuestra ahorro económico.</p></section><section className="panel method-card"><CheckCircle2 size={25}/><h3>Qué es simulado</h3><p>El movimiento del vehículo, la regla de velocidad preventiva y el impacto económico. Las predicciones y métricas de 2017 sí proceden de los artefactos del proyecto.</p></section></div>
    <section className="panel"><h3>Arquitectura del MVP</h3><div className="architecture"><div><b>React</b><span>Experiencia conductor + dashboard + escenario económico</span></div><span>→</span><div><b>FastAPI</b><span>API de rutas, métricas, contexto OSM y datos</span></div><span>→</span><div><b>Artefactos 2017</b><span>Reto 05 + Reto 08 + Reto 09 + coordenadas BNG</span></div></div></section>
    <section className="panel"><h3>Siguiente evolución a producto</h3><ol className="roadmap-list"><li>Empaquetar el modelo final para inferencia online, no solo predicciones históricas.</li><li>Ingerir GPS/telemática y features actuales de forma controlada.</li><li>Incorporar geometría exacta de la vía y no solo centros BNG.</li><li>Añadir SHAP/explicabilidad por predicción.</li><li>Ejecutar validación espacial, temporal y stress testing final.</li><li>Integrar autenticación, logging, monitoring y reglas de compliance.</li></ol></section>
  </div>;
}
