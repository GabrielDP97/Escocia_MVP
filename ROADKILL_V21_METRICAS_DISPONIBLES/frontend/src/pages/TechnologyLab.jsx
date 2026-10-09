import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Beaker, CheckCircle2, CircleDashed, FlaskConical } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import MetricCard from "../components/MetricCard";
import ModelComparisonCatalog from "../components/ModelComparisonCatalog";

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
  const [nlp, setNlp] = useState(null);
  const [mlp, setMlp] = useState(null);
  const [lstm, setLstm] = useState(null);
  const [caps, setCaps] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api("/api/technology/benchmark?bootstrap_samples=250"),
      api("/api/technology/calibration-audit?bootstrap_samples=250"),
      api("/api/technology/strict-temporal-audit"),
      api("/api/technology/nlp"),
      api("/api/technology/mlp"),
      api("/api/technology/lstm"),
      api("/api/technology/capabilities"),
    ]).then(([r, cal, st, nlp7, mlp8, lstm9, c]) => {
      setReport(r);
      setCalibration(cal);
      setStrict(st);
      setNlp(nlp7);
      setMlp(mlp8);
      setLstm(lstm9);
      setCaps(c.capabilities || []);
    }).catch((e) => setError(e.message));
  }, []);

  const rows = useMemo(() => report ? Object.entries(report.models).map(([key, value]) => ({ key, ...value })) : [], [report]);
  const calibrationPairs = useMemo(() => calibration ? Object.entries(calibration.existing_saved_calibration).map(([key, value]) => ({ key, ...value })) : [], [calibration]);
  const current = report?.models?.current_final?.metrics;
  const seasonal = report?.bootstrap?.seasonal_layer_vs_level1?.metrics;
  const ensemble = report?.bootstrap?.ensemble_balanced_vs_current?.metrics;
  const lstmReliability = calibration?.existing_saved_calibration?.lstm?.after?.reliability_bins || [];
  const thresholdSweep = strict?.test_2017?.threshold_sensitivity?.rows || [];
  const selectedConf = strict?.test_2017?.threshold_sensitivity?.selected_row;
  const nlpModels = nlp?.model_comparison || [];
  const mlpMetrics = mlp?.test_metrics;
  const lstmModels = lstm?.model_comparison || [];
  const lstmRaw = lstm?.test_2017?.raw_lstm;
  const lstmCal = lstm?.test_2017?.calibrated_lstm;
  const lstmHorizons = lstm?.horizon_comparison || [];

  return <div>
    <header className="page-header">
      <div>
        <span className="eyebrow">TECHNOLOGY VALIDATION LAB</span>
        <h1>Pruebas de rendimiento y calibración</h1>
        <p>Compara el score actual con las capas tecnológicas y audita si la calibración probabilística realmente mejora los artefactos incluidos en el proyecto.</p>
      </div>
      <Beaker size={36} />
    </header>

    <section className="panel"><div className="section-heading"><div><h3>Notebook global de evaluación</h3><p>Reúne el código de las pruebas del frontend, el cálculo de métricas y el informe de concordancia. Identifica los resultados que requieren archivos originales adicionales.</p></div><a className="button secondary" href="/api/evidence/global" download>Descargar notebook global</a></div></section>

    <ModelComparisonCatalog />

    {error && <div className="notice danger">{error}</div>}
    {(!report || !calibration || !strict || !nlp || !mlp || !lstm) && !error && <div className="notice info">Calculando métricas, calibración y auditoría temporal estricta…</div>}

    {report && calibration && strict && nlp && mlp && lstm && <>
      <div className="notice warning big-notice">
        <AlertTriangle size={22}/>
        <div><b>LABORATORIO SOBRE TEST HISTÓRICO 2017</b><p>{report.scope.warning}</p><p>{calibration.scope.warning}</p><p><b>Protocolo estricto:</b> {strict.protocol.rule}</p></div>
      </div>

      <div className="metric-grid">
        <MetricCard label="PR-AUC actual" value={fmt(current.pr_auc)} sub="Random Forest + ajuste estacional" tone="teal" />
        <MetricCard label="AP · nueva MLP" value={fmt(mlpMetrics.pr_auc)} sub="MLP · muestra propia de 6.336 filas" tone="teal" />
        <MetricCard label="Brier actual" value={fmt(current.brier)} sub="menor es mejor" />
        <MetricCard label="Brier · nueva MLP" value={fmt(mlpMetrics.brier)} sub="MLP · sin Platt adicional" tone="orange" />
      </div>

      <section className="panel">
        <div className="section-heading"><div>
          <h3>MLP de presencia de atropellos</h3>
          <p>Test 2017: {mlp.scope.test_rows.toLocaleString("es-ES")} observaciones, {mlp.scope.test_cells} celdas y {mlp.scope.test_positives} positivos. Train {mlp.scope.train}; validation {mlp.scope.validation}.</p>
        </div></div>
        <div className="metric-grid">
          <MetricCard label="ROC-AUC · MLP" value={fmt(mlpMetrics.roc_auc)} sub="evaluación MLP" tone="teal" />
          <MetricCard label="AP · MLP" value={fmt(mlpMetrics.pr_auc)} sub="average precision" tone="teal" />
          <MetricCard label="Brier · MLP" value={fmt(mlpMetrics.brier)} sub="menor es mejor" />
          <MetricCard label="F1 · MLP" value={fmt(mlpMetrics.f1)} sub={`umbral validation ${fmt(mlp.threshold, 6)}`} />
        </div>
        <p>{mlp.architecture}. {mlp.calibration}.</p>
        <div className="table-scroll"><table><thead><tr><th>Precisión</th><th>Recall</th><th>Accuracy</th><th>Alertas</th><th>TP</th><th>FP</th><th>TN</th><th>FN</th></tr></thead><tbody><tr>
          <td>{fmt(mlpMetrics.precision)}</td><td>{fmt(mlpMetrics.recall)}</td><td>{fmt(mlpMetrics.accuracy)}</td><td>{mlpMetrics.alerts}</td>
          <td>{mlp.confusion.tp}</td><td>{mlp.confusion.fp}</td><td>{mlp.confusion.tn}</td><td>{mlp.confusion.fn}</td>
        </tr></tbody></table></div>
        <p>Resultados publicados con la precisión del notebook ejecutado: cuatro decimales. <a href="/api/evidence/mlp-lstm" download>Ver evaluación MLP</a>.</p>
        <div className="notice info">{mlp.predictions_available ? "Las predicciones MLP por celda están disponibles para la demo y para recalcular comparativas." : "Las métricas están documentadas en el notebook. Las probabilidades MLP por celda y los nuevos ensembles están pendientes del CSV exportado por esa ejecución."}</div>
      </section>

      <section className="panel">
        <div className="section-heading"><div><h3>Notebook comparativo ejecutado · misma muestra</h3>
          <p>{mlp.common_comparison.n.toLocaleString("es-ES")} observaciones, {mlp.common_comparison.cells} celdas. La MLP fue reentrenada en este notebook; sus cifras corresponden a esa ejecución y muestra.</p>
        </div></div>
        <div className="table-scroll"><table><thead><tr><th>Modelo</th><th>ROC-AUC</th><th>AP</th><th>Brier</th><th>F1</th><th>Precisión</th><th>Recall</th><th>Umbral</th></tr></thead><tbody>
          {mlp.common_comparison.models.map((r) => <tr key={r.model}><td><b>{r.model}</b></td><td>{fmt(r.roc_auc, 6)}</td><td>{fmt(r.pr_auc, 6)}</td><td>{fmt(r.brier, 6)}</td><td>{fmt(r.f1, 6)}</td><td>{fmt(r.precision, 6)}</td><td>{fmt(r.recall, 6)}</td><td>{fmt(r.threshold, 6)}</td></tr>)}
        </tbody></table></div>
        <p>La nueva MLP no supera al principal en esta comparación. <a href="/api/evidence/comparacion" download>Ver prueba comparativa</a>.</p>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h3>LSTM · clasificación de presencia</h3>
            <p>Test final 2017 sobre {lstm.scope.test_rows.toLocaleString("es-ES")} secuencias y {lstm.scope.test_cells.toLocaleString("es-ES")} celdas. Ventana temporal seleccionada: <b>{lstm.temporal_design.selected_window_months} meses</b>. Estas son las métricas oficiales del Jupyter.</p>
          </div>
        </div>

        <div className="metric-grid">
          <MetricCard label="ROC-AUC · LSTM" value={fmt(lstmCal.roc_auc, 6)} sub="test oficial 2017" tone="teal" />
          <MetricCard label="PR-AUC · LSTM" value={fmt(lstmCal.pr_auc, 6)} sub="test oficial 2017" tone="teal" />
          <MetricCard label="Brier calibrado" value={fmt(lstmCal.brier, 6)} sub={`raw ${fmt(lstmRaw.brier, 6)} · reducción ${pct(lstm.test_2017.calibration_effect.relative_brier_reduction, 1)}`} />
          <MetricCard label="F1 · umbral validation" value={fmt(lstmCal.f1, 6)} sub={`umbral ${fmt(lstm.selected_model.threshold_from_validation, 6)}`} />
        </div>

        <div className="table-scroll"><table><thead><tr><th>Modelo</th><th>PR-AUC validation</th><th>Brier validation</th><th>ROC-AUC test</th><th>PR-AUC test</th><th>Brier test</th><th>Precision</th><th>Recall</th><th>F1</th><th>Lift 1%</th></tr></thead><tbody>
          {lstmModels.map((r) => <tr key={r.model} className={r.model === lstm.selected_model.name ? "benchmark-current" : ""}>
            <td><b>{r.model}{r.model === lstm.selected_model.name ? " · seleccionado" : ""}</b></td>
            <td>{fmt(r.val_pr_auc, 6)}</td><td>{fmt(r.val_brier, 6)}</td><td>{fmt(r.test_roc_auc, 6)}</td><td>{fmt(r.test_pr_auc, 6)}</td><td>{fmt(r.test_brier, 6)}</td><td>{fmt(r.test_precision, 6)}</td><td>{fmt(r.test_recall, 6)}</td><td>{fmt(r.test_f1, 6)}</td><td>{fmt(r.lift_top_1pct, 3)}x</td>
          </tr>)}
        </tbody></table></div>

        <div className="content-grid">
          <section className="panel">
            <h3>Diseño temporal y calibración</h3>
            <div className="bootstrap-list">
              <div><span>Train</span><b>{lstm.scope.train_target_years}</b></div>
              <div><span>Validation</span><b>{lstm.scope.validation_year}</b></div>
              <div><span>Test final</span><b>{lstm.scope.test_year}</b></div>
              <div><span>Ventana</span><b>{lstm.temporal_design.selected_window_months} meses</b></div>
              <div><span>Horizonte principal</span><b>t+{lstm.temporal_design.primary_horizon_months}</b></div>
              <div><span>Época seleccionada</span><b>{lstm.selected_model.best_epoch_by_pr}</b></div>
              <div><span>Épocas ejecutadas</span><b>{lstm.selected_model.epochs_run}</b></div>
              <div><span>2018</span><b>excluido</b></div>
            </div>
            <div className="notice info"><b>Platt:</b> {lstm.selected_model.calibration}. El Brier pasa de {fmt(lstmRaw.brier, 6)} a {fmt(lstmCal.brier, 6)}.</div>
          </section>

          <section className="panel">
            <h3>Generalización · bootstrap por celda</h3>
            <div className="bootstrap-list">
              <div><span>ROC-AUC</span><b>{fmt(lstm.bootstrap_2017.roc_auc.estimate, 6)} [{fmt(lstm.bootstrap_2017.roc_auc.ci95_low, 6)}, {fmt(lstm.bootstrap_2017.roc_auc.ci95_high, 6)}]</b></div>
              <div><span>PR-AUC</span><b>{fmt(lstm.bootstrap_2017.pr_auc.estimate, 6)} [{fmt(lstm.bootstrap_2017.pr_auc.ci95_low, 6)}, {fmt(lstm.bootstrap_2017.pr_auc.ci95_high, 6)}]</b></div>
              <div><span>Brier</span><b>{fmt(lstm.bootstrap_2017.brier.estimate, 6)} [{fmt(lstm.bootstrap_2017.brier.ci95_low, 6)}, {fmt(lstm.bootstrap_2017.brier.ci95_high, 6)}]</b></div>
              <div><span>Réplicas</span><b>{lstm.bootstrap_2017.replicates}</b></div>
            </div>
          </section>
        </div>

        <div className="section-heading threshold-heading"><div><h3>Horizonte t+1 frente a t+3</h3><p>Resultados archivados de los modelos temporales al ampliar el horizonte de predicción.</p></div></div>
        <div className="table-scroll"><table><thead><tr><th>Modelo</th><th>Horizonte</th><th>ROC-AUC</th><th>PR-AUC</th><th>Brier</th></tr></thead><tbody>
          {lstmHorizons.map((r) => <tr key={`${r.model}-${r.horizon_months}`} className={r.model === "LSTM" && r.horizon_months === 1 ? "benchmark-current" : ""}><td><b>{r.model}</b></td><td>t+{r.horizon_months}</td><td>{fmt(r.test_roc_auc, 6)}</td><td>{fmt(r.test_pr_auc, 6)}</td><td>{fmt(r.test_brier, 6)}</td></tr>)}
        </tbody></table></div>

        <div className="notice info"><b>Comparación con los demás modelos:</b> {lstm.provenance.comparison_note} {lstm.provenance.ece_note}</div>
      </section>

      <section className="panel">
        <div className="section-heading"><div><h3>Comparación recalculada · modelos con predicciones disponibles</h3><p>Recalculada sobre la intersección común de {report.scope.rows_common.toLocaleString("es-ES")} observaciones. Sirve para comparar los modelos sobre exactamente las mismas filas y <b>no sustituye</b> las métricas oficiales de cada notebook.</p></div></div>
        <div className="table-scroll"><table><thead><tr><th>Variante</th><th>ROC-AUC</th><th>PR-AUC</th><th>Brier</th><th>Log-loss</th><th>Lift 1%</th><th>Lift 5%</th><th>Δ PR vs actual</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.key} className={r.key === "current_final" ? "benchmark-current" : r.key === "ensemble_balanced" ? "benchmark-candidate" : ""}>
            <td><b>{r.label}</b></td><td>{fmt(r.metrics.roc_auc)}</td><td>{fmt(r.metrics.pr_auc)}</td><td>{fmt(r.metrics.brier)}</td><td>{fmt(r.metrics.log_loss)}</td><td>{fmt(r.metrics.lift_top_1pct, 2)}x</td><td>{fmt(r.metrics.lift_top_5pct, 2)}x</td><td>{delta(r.delta_vs_current.pr_auc)}</td>
          </tr>)}</tbody>
        </table></div>
      </section>

      <section className="panel">
        <div className="section-heading"><div><h3>Auditoría de calibración guardada</h3><p>Aquí sí tenemos probabilidad cruda y calibrada en el ZIP, por lo que podemos comprobar directamente si la calibración redujo el Brier.</p></div></div>
        <div className="table-scroll"><table><thead><tr><th>Modelo</th><th>Brier raw</th><th>Brier calibrado</th><th>Reducción</th><th>ECE cuantílico raw (10 bins)</th><th>ECE cuantílico calibrado (10 bins)</th><th>IC95% Δ Brier</th></tr></thead>
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
        <div className="section-heading"><div><h3>Experimento temporal estricto · selección 2016 → test 2017</h3><p>Este bloque ya no es un cross-fit sobre el test: integra la evaluación temporal del Random Forest y vuelve a calcular el test 2017 desde las {strict.test_2017.rows.toLocaleString("es-ES")} predicciones fila a fila del ZIP.</p></div></div>
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
          <h3>Reliability plot · LSTM calibrada · bins cuantílicos</h3>
          <p>Diagnóstico del frontend con 10 grupos cuantílicos. Si la probabilidad fuese perfecta, la tasa observada seguiría la diagonal.</p>
          <div className="chart-box"><ResponsiveContainer width="100%" height={280}><LineChart data={lstmReliability}><CartesianGrid strokeDasharray="3 3" stroke="#dfe8eb"/><XAxis dataKey="mean_predicted" type="number" domain={[0, 1]}/><YAxis domain={[0, 1]}/><Tooltip formatter={(v) => fmt(v, 4)}/><Line dataKey="mean_predicted" name="Ideal" stroke="#7f8c8d" strokeDasharray="5 5" dot={false}/><Line dataKey="observed_rate" name="Observado" stroke="#13a89e" strokeWidth={3}/></LineChart></ResponsiveContainer></div>
        </section>
        <section className="panel">
          <h3>¿Recalibrar p_final ayuda?</h3>
          <p>{calibration.crossfit_diagnostic.current_final.protocol}</p>
          <div className="table-scroll"><table><thead><tr><th>Método</th><th>Brier</th><th>Δ Brier</th><th>ECE cuantílico (10 bins)</th><th>PR-AUC</th></tr></thead><tbody>
            <tr><td><b>Sin recalibrar</b></td><td>{fmt(calibration.crossfit_diagnostic.current_final.baseline.brier, 5)}</td><td>—</td><td>{fmt(calibration.crossfit_diagnostic.current_final.baseline.ece_q10, 4)}</td><td>{fmt(calibration.crossfit_diagnostic.current_final.baseline.pr_auc, 4)}</td></tr>
            {Object.entries(calibration.crossfit_diagnostic.current_final.methods).map(([key, value]) => <tr key={key}><td>{value.label}</td><td>{fmt(value.metrics.brier, 5)}</td><td>{delta(value.delta_brier, 5)}</td><td>{fmt(value.metrics.ece_q10, 4)}</td><td>{fmt(value.metrics.pr_auc, 4)}</td></tr>)}
          </tbody></table></div>
          <div className="notice warning">Este cross-fit queda como diagnóstico complementario. La prueba principal válida es el protocolo temporal estricto mostrado arriba.</div>
        </section>
      </div>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h3>Multinomial Naive Bayes · clasificación documental</h3>
            <p>
              Resultados reales del notebook V3. La selección se hace con validation y el test se reserva como examen final.
              Estas métricas describen clasificación documental; no se mezclan con Brier, ROC-AUC o PR-AUC de los modelos de atropellos.
            </p>
          </div>
        </div>

        <div className="metric-grid">
          <MetricCard label="Modelo seleccionado" value={nlp.selected_model.name} sub="seleccionado por Macro-F1 en validation" tone="teal" />
          <MetricCard label="Accuracy · test" value={fmt(nlp.selected_model.test_accuracy, 3)} sub={`${nlp.scope.test_chunks} chunks de test`} />
          <MetricCard label="Macro-F1 · test" value={fmt(nlp.selected_model.test_macro_f1, 6)} sub="métrica principal multiclase" tone="teal" />
          <MetricCard label="Corpus" value={nlp.scope.chunks.toLocaleString("es-ES")} sub={`${nlp.scope.parent_documents} documentos padre · 4 clases`} />
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Modelo</th>
                <th>Accuracy validation</th>
                <th>Macro-F1 validation</th>
                <th>Accuracy test</th>
                <th>Macro-F1 test</th>
              </tr>
            </thead>
            <tbody>
              {nlpModels.map((r) => (
                <tr key={r.model} className={r.model === nlp.selected_model.name ? "benchmark-current" : ""}>
                  <td><b>{r.model}{r.model === nlp.selected_model.name ? " · seleccionado" : ""}</b></td>
                  <td>{fmt(r.validation_accuracy, 6)}</td>
                  <td>{fmt(r.validation_macro_f1, 6)}</td>
                  <td>{fmt(r.test_accuracy, 6)}</td>
                  <td>{fmt(r.test_macro_f1, 6)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="content-grid">
          <section className="panel">
            <h3>Clustering documental</h3>
            <div className="bootstrap-list">
              <div><span>Algoritmo</span><b>{nlp.clustering.algorithm}</b></div>
              <div><span>k seleccionado</span><b>{nlp.clustering.selected_k}</b></div>
              <div><span>Silhouette</span><b>{fmt(nlp.clustering.silhouette, 6)}</b></div>
              <div><span>ARI vs dominio documental</span><b>{fmt(nlp.clustering.ari_vs_document_domain, 4)}</b></div>
            </div>
          </section>
          <section className="panel">
            <h3>Diseño de evaluación</h3>
            <div className="bootstrap-list">
              <div><span>Documentos padre</span><b>{nlp.scope.parent_documents}</b></div>
              <div><span>Chunks</span><b>{nlp.scope.chunks}</b></div>
              <div><span>Validation</span><b>{nlp.scope.validation_chunks} chunks</b></div>
              <div><span>Test final</span><b>{nlp.scope.test_chunks} chunks</b></div>
            </div>
            <div className="notice info">{nlp.scope.split_rule}</div>
          </section>
        </div>

        <div className="notice info">
          <b>Interpretación:</b> MultinomialNB supera claramente al baseline Dummy
          (Macro-F1 {fmt(nlp.selected_model.test_macro_f1, 3)} frente a {fmt(nlpModels.find((m) => m.model === "DummyMostFrequent")?.test_macro_f1, 3)}).
          
        </div>
      </section>

      <section className="panel">
        <h3>Comprobación de afirmaciones del documento</h3>
        <div className="capability-grid">{calibration.claims.map((c) => <div className={`capability-card status-${c.status}`} key={c.claim}><div><StatusIcon status={c.status}/><b>{c.claim}</b></div><span className="status-pill">{c.status}</span><p>{c.reason}</p></div>)}</div>
      </section>

      <div className="content-grid">
        {report.scope.mlp_predictions_available ? <section className="panel">
          <h3>Sensibilidad del peso del modelo actual</h3>
          <p>0 = solo media MLP/LSTM; 1 = solo score actual. Es un barrido exploratorio, no selección válida de hiperparámetros.</p>
          <div className="chart-box"><ResponsiveContainer width="100%" height={280}><LineChart data={report.parameter_sweeps.ensemble_weight}><CartesianGrid strokeDasharray="3 3" stroke="#dfe8eb"/><XAxis dataKey="current_weight"/><YAxis domain={[0.58,0.64]}/><Tooltip formatter={(v) => fmt(v, 4)}/><Line dataKey="pr_auc" name="PR-AUC" stroke="#13a89e" strokeWidth={3}/></LineChart></ResponsiveContainer></div>
        </section> : <section className="panel"><h3>Ensembles con MLP</h3><p>Pendientes de las predicciones MLP por celda. Se recalcularán al importar los resultados de la ejecución documentada.</p></section>}
        <section className="panel">
          <h3>Bootstrap agrupado por celda</h3>
          <div className="bootstrap-list">
            <div><span>Capa estacional · Δ PR-AUC</span><b>{delta(seasonal.pr_auc.mean_delta)} [{fmt(seasonal.pr_auc.ci95_low)}, {fmt(seasonal.pr_auc.ci95_high)}]</b></div>
            <div><span>Capa estacional · Δ Brier</span><b>{delta(seasonal.brier.mean_delta)} [{fmt(seasonal.brier.ci95_low)}, {fmt(seasonal.brier.ci95_high)}]</b></div>
            {ensemble && <div><span>Ensemble · Δ PR-AUC</span><b>{delta(ensemble.pr_auc.mean_delta)} [{fmt(ensemble.pr_auc.ci95_low)}, {fmt(ensemble.pr_auc.ci95_high)}]</b></div>}
            {ensemble && <div><span>Ensemble · Δ Brier</span><b>{delta(ensemble.brier.mean_delta)} [{fmt(ensemble.brier.ci95_low)}, {fmt(ensemble.brier.ci95_high)}]</b></div>}
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
          <div><FlaskConical size={20}/><b>MLP / LSTM</b><p>{report.interpretation.mlp_lstm_alone}</p></div>
          <div><FlaskConical size={20}/><b>Ensemble</b><p>{report.interpretation.ensemble}</p></div>
          <div><FlaskConical size={20}/><b>Calibración</b><p>{calibration.methodology_note}</p></div>
        </div>
      </section>

      {report.runtime && <div className="notice info">Microbenchmark de fusión: mediana {fmt(report.runtime.median_ms, 3)} ms para {report.runtime.rows.toLocaleString("es-ES")} filas. {report.runtime.operation}.</div>}
    </>}
  </div>;
}
