import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";

const columns = [
  ["roc_auc", "ROC-AUC ↑"], ["pr_auc", "AP ↑"], ["brier", "Brier ↓"], ["f1", "F1 ↑"],
  ["precision", "Precisión ↑"], ["recall", "Recall ↑"], ["accuracy", "Accuracy ↑"], ["macro_f1", "Macro-F1 ↑"],
  ["MAE", "MAE ↓"], ["RMSE", "RMSE ↓"], ["R2", "R² ↑"], ["PoissonDeviance", "Deviance Poisson ↓"],
  ["lift_top_1pct", "Lift 1% ↑"], ["lift_top_10pct", "Lift 10% ↑"],
  ["threshold", "Umbral"], ["alerts", "Alertas"], ["AIC", "AIC ↓"], ["BIC", "BIC ↓"], ["logLik", "Log-verosimilitud ↑"],
];
const phases = { validation: "Validación 2016", test: "Test 2017", fit: "Ajuste 2008–2016" };
const tasks = { presence: "Presencia de atropellos", count: "Recuentos por celda", intensity: "Intensidad · tres clases", monthly: "Recuentos mensuales" };
const number = (value, digits) => value == null ? "—" : Number(value).toLocaleString("es-ES", {minimumFractionDigits: digits, maximumFractionDigits: digits});

export default function ModelComparisonCatalog() {
  const [catalog, setCatalog] = useState(null);
  const [error, setError] = useState("");
  const [task, setTask] = useState("all");
  const [phase, setPhase] = useState("all");
  const [search, setSearch] = useState("");
  useEffect(() => { api("/api/technology/model-comparison").then(setCatalog).catch((err) => setError(err.message)); }, []);
  const groups = useMemo(() => (catalog?.groups || []).filter((group) =>
    (task === "all" || task === group.task) && (phase === "all" || phase === group.phase)
  ).map((group) => ({ ...group, rows: group.rows.filter((row) =>
    row.model.toLocaleLowerCase("es-ES").includes(search.trim().toLocaleLowerCase("es-ES"))
  ) })).filter((group) => group.rows.length), [catalog, task, phase, search]);
  return <section className="model-catalog" aria-label="Comparación de todos los modelos">
    <div className="panel catalog-intro">
      <span className="eyebrow">COMPARACIÓN DE MODELOS</span>
      <h2>Todos los modelos estudiados</h2>
      <p>Clasificación, regresión y predicción temporal. Cada tabla identifica la tarea, la muestra y la fase de evaluación.</p>
      {catalog && <p>{catalog.rows} resultados publicados en {catalog.groups.length} comparativas. {catalog.note}</p>}
      <div className="catalog-controls">
        <label>Tarea<select value={task} onChange={(event) => setTask(event.target.value)}><option value="all">Todas las tareas</option>{Object.entries(tasks).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label>Evaluación<select value={phase} onChange={(event) => setPhase(event.target.value)}><option value="all">Todas las fases</option>{Object.entries(phases).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label>Modelo<input type="search" placeholder="Buscar Random Forest, MLP, LSTM…" value={search} onChange={(event) => setSearch(event.target.value)}/></label>
      </div>
      <p className="catalog-legend">↑ Mayor es mejor · ↓ Menor es mejor · — Métrica no publicada. AP se calcula como average precision.</p>
    </div>
    {error && <div className="notice danger">{error}</div>}
    {!catalog && !error && <div className="notice info">Cargando comparativas…</div>}
    {catalog && !groups.length && <div className="notice info">No hay modelos que coincidan con los filtros.</div>}
    {groups.map((group) => {
      const available = columns.filter(([key]) => group.rows.some((row) => row[key] != null));
      return <section className="panel catalog-table" key={group.id}>
        <div className="section-heading"><div><span className="catalog-phase">{phases[group.phase]} · {tasks[group.task]} · {group.n == null ? "Tamaño no publicado" : `${group.n.toLocaleString("es-ES")} observaciones`}</span>
          <h3>{group.title}</h3><p>{group.note}</p>
        </div></div>
        <div className="table-scroll"><table><thead><tr><th>Modelo</th>{available.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead><tbody>
          {group.rows.map((row) => <tr key={row.model}><td><b>{row.model}</b></td>{available.map(([key]) => <td key={key}>{number(row[key], ["alerts"].includes(key) ? 0 : key === "threshold" ? 6 : group.digits)}</td>)}</tr>)}
        </tbody></table></div>
        <div className="catalog-source">{group.evidence ? <a href={`/api/evidence/${group.evidence}`} download>Ver evaluación ejecutada</a> : <span>Fuente: artefactos de los modelos temporales de la aplicación.</span>}</div>
      </section>;
    })}
  </section>;
}
