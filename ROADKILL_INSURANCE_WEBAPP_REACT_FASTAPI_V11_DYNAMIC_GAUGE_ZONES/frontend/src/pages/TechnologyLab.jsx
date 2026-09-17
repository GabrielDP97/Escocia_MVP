import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Beaker, CheckCircle2, CircleDashed, FlaskConical } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import MetricCard from "../components/MetricCard";

const fmt = (v, d = 4) => v == null ? "—" : Number(v).toFixed(d);
const delta = (v, d = 4) => v == null ? "—" : `${v >= 0 ? "+" : ""}${Number(v).toFixed(d)}`;
const pct = (v, d = 1) => v == null ? "—" : `${(Number(v) * 100).toFixed(d)}%`;

function StatusIcon({ status }) {
  if (status.startsWith("aplicado") || status === "integrado-operativo" || status.startsWith("verificado")) return <CheckCircle2 size={18} />;
  if (status.includes("no-") || status.includes("pendiente") || status.startsWith("falso")) return <AlertTriangle size={18} />;
  return <CircleDashed size={18} />;
}

export default function TechnologyLab() {
  const [report, setReport] = useState(null);
  const [calibration, setCalibration] = useState(null);
  const [strict, setStrict] = useState(null);
  const [caps, setCaps] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api("/api/technology/benchmark?bootstrap_samples=250"),
      api("/api/technology/calibration-audit?bootstrap_samples=250"),
      api("/api/technology/strict-temporal-audit"),
      api("/api/technology/capabilities"),
    ]).then(([r, cal, st, c]) => {
      setReport(r);
      setCalibration(cal);
      setStrict(st);
      setCaps(c.capabilities || []);
    }).catch((e) => setError(e.message));
  }, []);

  const rows = useMemo(() => report ? Object.entries(report.models).map(([key, value]) => ({ key, ...value })) : [], [report]);
  const calibrationPairs = useMemo(() => calibration ? Object.entries(calibration.existing_saved_calibration).map(([key, value]) => ({ key, ...value })) : [], [calibration]);
  const current = report?.models?.current_final?.metrics;
  const candidate = report?.models?.ensemble_balanced?.metrics;
  const seasonal = report?.bootstrap?.seasonal_layer_vs_level1?.metrics;
  const ensemble = report?.bootstrap?.ensemble_balanced_vs_current?.metrics;
  const dnnReliability = calibration?.existing_saved_calibration?.dnn?.after?.reliability_bins || [];
  const thresholdSweep = strict?.test_2017?.threshold_sensitivity?.rows || [];
  const selectedConf = strict?.test_2017?.threshold_sensitivity?.selected_row;

  return <div>
    <header className="page-header">
      <div>
        <span className="eyebrow">TECHNOLOGY VALIDATION LAB</span>
        <h1>Pruebas de rendimiento y calibración</h1>
        <p>Compara el score actual con las capas tecnológicas y audita si la calibración probabilística realmente mejora los artefactos incluidos en el proyecto.</p>
      </div>
      <Beaker size={36} />
    </header>

    {error && <div className="notice danger">{error}</div>}
    {(!report || !calibration || !strict) && !error && <div className="notice info">Calculando métricas, calibración y auditoría temporal estricta…</div>}

    {report && calibration && strict && <>
      <div className="notice warning big-notice">
        <AlertTriangle size={22}/>
        <div><b>LABORATORIO SOBRE TEST HISTÓRICO 2017</b><p>{report.scope.warning}</p><p>{calibration.scope.warning}</p><p><b>Protocolo estricto:</b> {strict.protocol.rule}</p></div>
      </div>

      <div className="metric-grid">
        <MetricCard label="PR-AUC actual" value={fmt(current.pr_auc)} sub="Reto 05 + estacional" tone="teal" />
        <MetricCard label="PR-AUC ensemble" value={fmt(candidate.pr_auc)} sub={`Δ ${delta(candidate.pr_auc - current.pr_auc)}`} tone="teal" />
        <MetricCard label="Brier actual" value={fmt(current.brier)} sub="menor es mejor" />
        <MetricCard label="Brier ensemble" value={fmt(candidate.brier)} sub={`Δ ${delta(candidate.brier - current.brier)}`} tone="orange" />
      </div>

      <section className="panel">
        <div className="section-heading"><div><h3>Comparativa de modelos y capas</h3><p>Misma intersección de {report.scope.rows_common.toLocaleString("es-ES")} observaciones para hacer la comparación justa.</p></div></div>
        <div className="table-scroll"><table><thead><tr><th>Variante</th><th>ROC-AUC</th><th>PR-AUC</th><th>Brier</th><th>Log-loss</th><th>Lift 1%</th><th>Lift 5%</th><th>Δ PR vs actual</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.key} className={r.key === "current_final" ? "benchmark-current" : r.key === "ensemble_balanced" ? "benchmark-candidate" : ""}>
            <td><b>{r.label}</b></td><td>{fmt(r.metrics.roc_auc)}</td><td>{fmt(r.metrics.pr_auc)}</td><td>{fmt(r.metrics.brier)}</td><td>{fmt(r.metrics.log_loss)}</td><td>{fmt(r.metrics.lift_top_1pct, 2)}x</td><td>{fmt(r.metrics.lift_top_5pct, 2)}x</td><td>{delta(r.delta_vs_current.pr_auc)}</td>
          </tr>)}</tbody>
        </table></div>
      </section>

      <section className="panel">
        <div className="section-heading"><div><h3>Auditoría de calibración guardada</h3><p>Aquí sí tenemos probabilidad cruda y calibrada en el ZIP, por lo que podemos comprobar directamente si la calibración redujo el Brier.</p></div></div>
        <div className="table-scroll"><table><thead><tr><th>Modelo</th><th>Brier raw</th><th>Brier calibrado</th><th>Reducción</th><th>ECE raw</th><th>ECE calibrado</th><th>IC95% Δ Brier</th></tr></thead>
          <tbody>{calibrationPairs.map((r) => <tr key={r.key}>
            <td><b>{r.label}</b></td>
            <td>{fmt(r.before.brier, 5)}</td>
            <td>{fmt(r.after.brier, 5)}</td>
            <td>{pct(r.brier_relative_reduction, 1)}</td>
            <td>{fmt(r.before.ece_q10, 4)}</td>
            <td>{fmt(r.after.ece_q10, 4)}</td>
            <td>{fmt(r.bootstrap.ci95_low, 5)} a {fmt(r.bootstrap.ci95_high, 5)}</td>
          </tr>)}</tbody>
        </table></div>
        <div className="notice info">Un Δ Brier negativo significa mejora. El bootstrap se remuestrea por <b>cell</b>, no por fila individual.</div>
      </section>

      <section className="panel">
        <div className="section-heading"><div><h3>Experimento temporal estricto · selección 2016 → test 2017</h3><p>Este bloque ya no es un cross-fit sobre el test: integra el Reto 05 temporal estricto ejecutado y vuelve a calcular el test 2017 desde las {strict.test_2017.rows.toLocaleString("es-ES")} predicciones fila a fila del ZIP.</p></div></div>
        <div className="metric-grid">
          <MetricCard label="Brier RF raw · 2016" value={fmt(strict.validation_2016.raw.brier, 6)} sub="antes de Platt" />
          <MetricCard label="Brier Platt · 2016" value={fmt(strict.validation_2016.level1_temporal_platt.brier, 6)} sub={`reducción ${pct(strict.validation_2016.calibration_effect.relative_brier_reduction, 1)}`} tone="teal" />
          <MetricCard label="Brier Nivel 2 · 2016" value={fmt(strict.validation_2016.level2_seasonal.brier, 6)} sub="seleccionado antes de 2017" tone="teal" />
          <MetricCard label="Brier final · 2017" value={fmt(strict.test_2017.recomputed_final.brier, 6)} sub="recalculado desde CSV" tone="orange" />
        </div>
        <div className="table-scroll"><table><thead><tr><th>Etapa</th><th>ROC-AUC</th><th>PR-AUC</th><th>Brier</th><th>Lift 1%</th><th>Qué se decide</th></tr></thead><tbody>
          <tr><td><b>RF raw · validation 2016</b></td><td>{fmt(strict.validation_2016.raw.roc_auc)}</td><td>{fmt(strict.validation_2016.raw.pr_auc)}</td><td>{fmt(strict.validation_2016.raw.brier, 6)}</td><td>—</td><td>Modelo base</td></tr>
          <tr><td><b>Nivel 1 + Platt OOF temporal · 2016</b></td><td>{fmt(strict.validation_2016.level1_temporal_platt.roc_auc)}</td><td>{fmt(strict.validation_2016.level1_temporal_platt.pr_auc)}</td><td>{fmt(strict.validation_2016.level1_temporal_platt.brier, 6)}</td><td>{fmt(strict.validation_2016.level1_temporal_platt.lift_top_1pct, 2)}x</td><td>Calibración</td></tr>
          <tr><td><b>Nivel 2 estacional · 2016</b></td><td>{fmt(strict.validation_2016.level2_seasonal.roc_auc)}</td><td>{fmt(strict.validation_2016.level2_seasonal.pr_auc)}</td><td>{fmt(strict.validation_2016.level2_seasonal.brier, 6)}</td><td>{fmt(strict.validation_2016.level2_seasonal.lift_top_1pct, 2)}x</td><td>Salida final + umbral {fmt(strict.validation_2016.selected_threshold_f1, 4)}</td></tr>
          <tr className="benchmark-current"><td><b>Test final 2017</b></td><td>{fmt(strict.test_2017.recomputed_final.roc_auc)}</td><td>{fmt(strict.test_2017.recomputed_final.pr_auc)}</td><td>{fmt(strict.test_2017.recomputed_final.brier, 6)}</td><td>—</td><td>Solo evaluación; ninguna decisión</td></tr>
        </tbody></table></div>
        <div className="notice info"><b>Verificación:</b> el resultado recalculado desde <code>predicciones_test_2017.csv</code> coincide con el notebook ejecutado: {strict.test_2017.verification.final_matches ? "PASS" : "REVISAR"}. Platt se ajustó con {strict.validation_2016.level1_temporal_platt.oof_rows_used.toLocaleString("es-ES")} predicciones OOF temporales.</div>

        {selectedConf && <>
          <div className="section-heading threshold-heading"><div><h3>Matriz de confusión · umbral congelado en 2016</h3><p>El umbral válido del experimento es {fmt(selectedConf.threshold, 6)}. Estos conteos salen de las 6.372 observaciones reales de 2017.</p></div></div>
          <div className="metric-grid">
            <MetricCard label="Verdaderos positivos" value={selectedConf.true_positives.toLocaleString("es-ES")} sub={`Recall ${pct(selectedConf.recall, 1)}`} tone="teal" />
            <MetricCard label="Falsos positivos" value={selectedConf.false_positives.toLocaleString("es-ES")} sub={`FPR ${pct(selectedConf.false_positive_rate, 1)}`} tone="orange" />
            <MetricCard label="Verdaderos negativos" value={selectedConf.true_negatives.toLocaleString("es-ES")} sub={`Especificidad ${pct(selectedConf.specificity, 1)}`} />
            <MetricCard label="Falsos negativos" value={selectedConf.false_negatives.toLocaleString("es-ES")} sub={`FNR ${pct(selectedConf.false_negative_rate, 1)}`} tone="orange" />
          </div>

          <div className="content-grid threshold-grid">
            <section className="panel threshold-panel">
              <h3>Sensibilidad del umbral · falsos positivos vs falsos negativos</h3>
              <p>Solo describe qué habría ocurrido en el test 2017. No vuelve a seleccionar el umbral.</p>
              <div className="chart-box"><ResponsiveContainer width="100%" height={300}><LineChart data={thresholdSweep}><CartesianGrid strokeDasharray="3 3" stroke="#dfe8eb"/><XAxis dataKey="threshold" tickFormatter={(v) => Number(v).toFixed(2)}/><YAxis/><Tooltip labelFormatter={(v) => `Umbral ${Number(v).toFixed(4)}`} formatter={(v, name) => [Number(v).toLocaleString("es-ES"), name]}/><Line dataKey="false_positives" name="Falsos positivos" stroke="#d97706" strokeWidth={3}/><Line dataKey="false_negatives" name="Falsos negativos" stroke="#b91c1c" strokeWidth={3}/><Line dataKey="true_positives" name="Verdaderos positivos" stroke="#0f766e" strokeWidth={2} strokeDasharray="5 4"/></LineChart></ResponsiveContainer></div>
            </section>
            <section className="panel threshold-panel">
              <h3>Trade-off operativo</h3>
              <p>{strict.test_2017.threshold_sensitivity.interpretation}</p>
              <div className="table-scroll"><table><thead><tr><th>Umbral</th><th>Alertas</th><th>TP</th><th>FP</th><th>FN</th><th>Precisión</th><th>Recall</th><th>F1</th></tr></thead><tbody>
                {thresholdSweep.map((r) => <tr key={r.threshold} className={r.is_selected_2016 ? "benchmark-current" : ""}>
                  <td><b>{fmt(r.threshold, r.is_selected_2016 ? 6 : 2)}{r.is_selected_2016 ? " · seleccionado" : ""}</b></td>
                  <td>{r.alerts.toLocaleString("es-ES")}</td>
                  <td>{r.true_positives.toLocaleString("es-ES")}</td>
                  <td>{r.false_positives.toLocaleString("es-ES")}</td>
                  <td>{r.false_negatives.toLocaleString("es-ES")}</td>
                  <td>{pct(r.precision, 1)}</td>
                  <td>{pct(r.recall, 1)}</td>
                  <td>{pct(r.f1, 1)}</td>
                </tr>)}
              </tbody></table></div>
            </section>
          </div>
          <div className="notice warning"><b>No usar este barrido para optimizar sobre 2017:</b> {strict.test_2017.threshold_sensitivity.warning}</div>
        </>}

        <div className="notice warning"><b>Resultado de la comprobación del 0,0175:</b> {strict.claim_reconciliation.interpretation}</div>
      </section>

      <div className="content-grid">
        <section className="panel">
          <h3>Reliability plot · DNN calibrada</h3>
          <p>Si la probabilidad fuese perfecta, la tasa observada seguiría la diagonal.</p>
          <div className="chart-box"><ResponsiveContainer width="100%" height={280}><LineChart data={dnnReliability}><CartesianGrid strokeDasharray="3 3" stroke="#dfe8eb"/><XAxis dataKey="mean_predicted" type="number" domain={[0, 1]}/><YAxis domain={[0, 1]}/><Tooltip formatter={(v) => fmt(v, 4)}/><Line dataKey="mean_predicted" name="Ideal" stroke="#7f8c8d" strokeDasharray="5 5" dot={false}/><Line dataKey="observed_rate" name="Observado" stroke="#13a89e" strokeWidth={3}/></LineChart></ResponsiveContainer></div>
        </section>
        <section className="panel">
          <h3>¿Recalibrar p_final ayuda?</h3>
          <p>{calibration.crossfit_diagnostic.current_final.protocol}</p>
          <div className="table-scroll"><table><thead><tr><th>Método</th><th>Brier</th><th>Δ Brier</th><th>ECE</th><th>PR-AUC</th></tr></thead><tbody>
            <tr><td><b>Sin recalibrar</b></td><td>{fmt(calibration.crossfit_diagnostic.current_final.baseline.brier, 5)}</td><td>—</td><td>{fmt(calibration.crossfit_diagnostic.current_final.baseline.ece_q10, 4)}</td><td>{fmt(calibration.crossfit_diagnostic.current_final.baseline.pr_auc, 4)}</td></tr>
            {Object.entries(calibration.crossfit_diagnostic.current_final.methods).map(([key, value]) => <tr key={key}><td>{value.label}</td><td>{fmt(value.metrics.brier, 5)}</td><td>{delta(value.delta_brier, 5)}</td><td>{fmt(value.metrics.ece_q10, 4)}</td><td>{fmt(value.metrics.pr_auc, 4)}</td></tr>)}
          </tbody></table></div>
          <div className="notice warning">Este cross-fit queda como diagnóstico complementario. La prueba principal válida es el protocolo temporal estricto mostrado arriba.</div>
        </section>
      </div>

      <section className="panel">
        <h3>Comprobación de afirmaciones del documento</h3>
        <div className="capability-grid">{calibration.claims.map((c) => <div className={`capability-card status-${c.status}`} key={c.claim}><div><StatusIcon status={c.status}/><b>{c.claim}</b></div><span className="status-pill">{c.status}</span><p>{c.reason}</p></div>)}</div>
      </section>

      <div className="content-grid">
        <section className="panel">
          <h3>Sensibilidad del peso del modelo actual</h3>
          <p>0 = solo media DNN/LSTM; 1 = solo score actual. Es un barrido exploratorio, no selección válida de hiperparámetros.</p>
          <div className="chart-box"><ResponsiveContainer width="100%" height={280}><LineChart data={report.parameter_sweeps.ensemble_weight}><CartesianGrid strokeDasharray="3 3" stroke="#dfe8eb"/><XAxis dataKey="current_weight"/><YAxis domain={[0.58,0.64]}/><Tooltip formatter={(v) => fmt(v, 4)}/><Line dataKey="pr_auc" name="PR-AUC" stroke="#13a89e" strokeWidth={3}/></LineChart></ResponsiveContainer></div>
        </section>
        <section className="panel">
          <h3>Bootstrap agrupado por celda</h3>
          <div className="bootstrap-list">
            <div><span>Capa estacional · Δ PR-AUC</span><b>{delta(seasonal.pr_auc.mean_delta)} [{fmt(seasonal.pr_auc.ci95_low)}, {fmt(seasonal.pr_auc.ci95_high)}]</b></div>
            <div><span>Capa estacional · Δ Brier</span><b>{delta(seasonal.brier.mean_delta)} [{fmt(seasonal.brier.ci95_low)}, {fmt(seasonal.brier.ci95_high)}]</b></div>
            <div><span>Ensemble · Δ PR-AUC</span><b>{delta(ensemble.pr_auc.mean_delta)} [{fmt(ensemble.pr_auc.ci95_low)}, {fmt(ensemble.pr_auc.ci95_high)}]</b></div>
            <div><span>Ensemble · Δ Brier</span><b>{delta(ensemble.brier.mean_delta)} [{fmt(ensemble.brier.ci95_low)}, {fmt(ensemble.brier.ci95_high)}]</b></div>
          </div>
          <div className="notice info">El remuestreo se hace por <b>cell</b>, para no tratar los meses de una misma celda como observaciones completamente independientes.</div>
        </section>
      </div>

      <section className="panel">
        <h3>Qué tecnologías del documento se han podido aplicar de verdad</h3>
        <div className="capability-grid">{caps.map((c) => <div className={`capability-card status-${c.status}`} key={c.technology}><div><StatusIcon status={c.status}/><b>{c.technology}</b></div><span className="status-pill">{c.status}</span><p>{c.evidence}</p></div>)}</div>
      </section>

      <section className="panel">
        <h3>Lectura de los resultados</h3>
        <div className="interpretation-grid">
          <div><FlaskConical size={20}/><b>Estacionalidad</b><p>{report.interpretation.seasonal_layer}</p></div>
          <div><FlaskConical size={20}/><b>DNN / LSTM</b><p>{report.interpretation.dnn_lstm_alone}</p></div>
          <div><FlaskConical size={20}/><b>Ensemble</b><p>{report.interpretation.ensemble}</p></div>
          <div><FlaskConical size={20}/><b>Calibración</b><p>{calibration.methodology_note}</p></div>
        </div>
      </section>

      <div className="notice info">Microbenchmark de fusión: mediana {fmt(report.runtime.median_ms, 3)} ms para {report.runtime.rows.toLocaleString("es-ES")} filas. {report.runtime.operation}.</div>
    </>}
  </div>;
}
