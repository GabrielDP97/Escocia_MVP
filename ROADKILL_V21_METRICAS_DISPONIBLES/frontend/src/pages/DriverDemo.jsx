import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, CarFront, ChevronLeft, ChevronRight, Lightbulb, Pause, Play, ShieldAlert, Trees } from "lucide-react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, num, pct } from "../lib/api";
import { riskVisualState } from "../lib/riskVisuals";
import MetricCard from "../components/MetricCard";
import RiskBadge from "../components/RiskBadge";
import RiskGauge from "../components/RiskGauge";
import RouteMap from "../components/RouteMap";

const months = [[1,"Enero"],[2,"Febrero"],[3,"Marzo"],[4,"Abril"],[5,"Mayo"],[6,"Junio"],[7,"Julio"],[8,"Agosto"],[9,"Septiembre"],[10,"Octubre"],[11,"Noviembre"],[12,"Diciembre"]];

function tripPercent(value) {
  if (value == null || !Number.isFinite(value)) return "—";
  if (value === 0) return "0 %";
  const percentage = value * 100;
  return `≈ ${new Intl.NumberFormat("es-ES", { maximumSignificantDigits: 3 }).format(percentage)} %`;
}

function dateInMonth(date, month) {
  const day = Math.min(Number(date.slice(8, 10)) || 15, new Date(2017, month, 0).getDate());
  return `2017-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function stoppingDistance(speedMph) {
  const v = speedMph * 0.44704;
  return v * 1.2 + (v * v) / (2 * 9.81 * 0.55);
}

function preventiveResponse(limit, percentile, probability, threshold, currentSpeed) {
  const legal = Number(limit || 60);
  const score = Math.max(0, Math.min(100, Number(percentile) || 0));
  const p = Number(probability || 0);
  const cut = Number(threshold || 0);

  // La intervención solo se activa si la probabilidad supera el umbral
  // elegido en validation. A partir de ahí, la intensidad crece de forma
  // continua con el Risk Response Score (percentil relativo).
  if (p < cut) {
    return {
      active: false,
      intensity: 0,
      reductionMph: 0,
      targetSpeed: legal,
      appliedSpeed: Math.min(Number(currentSpeed), legal),
    };
  }

  // Entre score 60 y 100, la reducción crece linealmente de 0 a 20 mph.
  // Por debajo de 60, aunque se haya superado el umbral probabilístico,
  // mantenemos una respuesta mínima de aviso sin reducción de velocidad.
  const intensity = Math.max(0, Math.min(1, (score - 60) / 40));
  const reductionMph = intensity * 20;
  const targetSpeed = Math.max(25, legal - reductionMph);

  // Nunca sugerimos acelerar: si el conductor ya va por debajo del objetivo
  // preventivo, se conserva su velocidad actual.
  const appliedSpeed = Math.min(Number(currentSpeed), targetSpeed);

  return {
    active: true,
    intensity,
    reductionMph,
    targetSpeed,
    appliedSpeed,
  };
}

export default function DriverDemo() {
  const [roads, setRoads] = useState([]);
  const [road, setRoad] = useState("A82");
  const [month, setMonth] = useState(5);
  const [travelDate, setTravelDate] = useState("2017-05-15");
  const [distanceInput, setDistanceInput] = useState("");
  const [trafficMode, setTrafficMode] = useState("auto");
  const [reverse, setReverse] = useState(false);
  const [route, setRoute] = useState(null);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(60);
  const [audit, setAudit] = useState(false);
  const [selectedThreshold, setSelectedThreshold] = useState(null);
  const [thresholdRows, setThresholdRows] = useState([]);
  const [error, setError] = useState("");
  const timer = useRef(null);

  useEffect(() => {
    api("/api/roads?min_cells=4").then((d) => {
      setRoads(d.roads);
      if (!d.roads.some((r) => r.road_name === "A82") && d.roads.length) setRoad(d.roads[0].road_name);
    }).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    setPlaying(false); setIndex(0); setError("");
    setRoute(null);
    let current = true;
    const distance = distanceInput.trim() === "" ? null : Number(distanceInput);
    if (distance != null && (!Number.isFinite(distance) || distance <= 0 || distance > 10000)) {
      setError("La distancia del escenario debe estar entre 0 y 10.000 km, sin incluir cero.");
      return;
    }
    const distanceQuery = distance == null ? "" : `&distance_km=${distance}`;
    api(`/api/route?road_name=${encodeURIComponent(road)}&month=${month}&reverse=${reverse}&travel_date=${encodeURIComponent(travelDate)}${distanceQuery}&traffic_mode=${trafficMode}`)
      .then((data) => { if (current) setRoute(data); })
      .catch((e) => { if (current) { setRoute(null); setError(e.message); } });
    return () => { current = false; };
  }, [road, month, reverse, travelDate, distanceInput, trafficMode]);


  useEffect(() => {
    api("/api/technology/strict-temporal-audit")
      .then((d) => {
        const rows = d?.test_2017?.threshold_sensitivity?.rows || [];
        setThresholdRows(rows);
      })
      .catch(() => {
        // El selector sigue funcionando con los valores de respaldo aunque
        // la auditoría tecnológica no esté disponible.
        setThresholdRows([]);
      });
  }, []);

  useEffect(() => {
    if (!playing || !route?.points?.length) return;
    timer.current = window.setInterval(() => {
      setIndex((prev) => {
        if (prev >= route.points.length - 1) { setPlaying(false); return prev; }
        return prev + 1;
      });
    }, 1100);
    return () => window.clearInterval(timer.current);
  }, [playing, route]);

  const point = route?.points?.[index];
  const osm = route?.context?.osm || {};
  const triage = route?.context?.triage || {};
  const officialThreshold = Number(route?.threshold ?? 0.2425809815683556);
  const activeThreshold = selectedThreshold == null ? officialThreshold : Number(selectedThreshold);
  const isOfficialThreshold = Math.abs(activeThreshold - officialThreshold) < 1e-9;
  const thresholdAlertActive = Boolean(point && Number(point.p_final) >= activeThreshold);
  const visualState = point ? riskVisualState(point.p_final, activeThreshold) : null;

  const activeThresholdMapping = useMemo(() => {
    const rows = route?.threshold_score_map || [];
    return rows.find((row) => Math.abs(Number(row.threshold) - activeThreshold) < 1e-9) || null;
  }, [route?.threshold_score_map, activeThreshold]);

  const activeThresholdScore = activeThresholdMapping
    ? Number(activeThresholdMapping.risk_percentile)
    : null;

  const activeGaugeZones = useMemo(() => {
    const zones = activeThresholdMapping?.gauge_boundaries;
    if (!zones) return null;
    return {
      normalToWatch: Number(zones.normal_to_watch),
      watchToAlert: Number(zones.watch_to_alert),
      alertToCritical: Number(zones.alert_to_critical),
    };
  }, [activeThresholdMapping]);

  const thresholdOptions = useMemo(() => {
    const fallback = [0.10, 0.15, 0.20, officialThreshold, 0.30, 0.40, 0.50];
    const values = thresholdRows.length ? thresholdRows.map((row) => Number(row.threshold)) : fallback;
    if (!values.some((value) => Math.abs(value - officialThreshold) < 1e-9)) values.push(officialThreshold);
    return [...new Set(values.map((value) => Number(value.toFixed(12))))].sort((a, b) => a - b);
  }, [thresholdRows, officialThreshold]);

  const activeThresholdStats = useMemo(() => {
    if (!thresholdRows.length) return null;
    return thresholdRows.find((row) => Math.abs(Number(row.threshold) - activeThreshold) < 1e-9) || null;
  }, [thresholdRows, activeThreshold]);
  const braking = useMemo(() => {
    if (!point || !route) return null;

    const response = preventiveResponse(
      Number(osm.maxspeed_mph || 60),
      point.risk_percentile,
      point.p_final,
      activeThreshold,
      speed,
    );

    const currentDistance = stoppingDistance(speed);
    const preventiveDistance = stoppingDistance(response.appliedSpeed);

    return {
      ...response,
      current: currentDistance,
      reduced: preventiveDistance,
      saved: Math.max(0, currentDistance - preventiveDistance),
    };
  }, [point, route, osm.maxspeed_mph, speed, activeThreshold]);

  const seasonalMessage = point && route
    ? `En ${route.month_name}, el riesgo relativo aprendido es ${route.relative_risk_month.toFixed(2)}x. ${point.seasonal_delta == null ? "" : `El ajuste estacional cambia la probabilidad ${point.seasonal_delta >= 0 ? "+" : ""}${(point.seasonal_delta * 100).toFixed(1)} puntos porcentuales frente al Nivel 1.`}`
    : "";

  const chartData = (route?.points || []).map((p) => ({ step: p.step + 1, RandomForest: p.p_final, LSTM: p.p_lstm, MLP: p.p_mlp, Ensemble: p.p_ensemble_exploratory }));

  return (
    <div>
      <header className="page-header">
        <div><span className="eyebrow">DRIVER EXPERIENCE</span><h1>Simulación preventiva en carretera</h1><p>El vehículo avanza por celdas reales del test 2017 y el riesgo cambia con las predicciones del proyecto.</p></div>
        {point && <RiskBadge band={point.risk_band} />}
      </header>

      <section className="control-bar">
        <label>Carretera<select value={road} onChange={(e) => { setRoad(e.target.value); setDistanceInput(""); }}>{roads.map((r) => <option key={r.road_name}>{r.road_name}</option>)}</select></label>
        <label>Mes<select value={month} onChange={(e) => { const next = Number(e.target.value); setMonth(next); setTravelDate(dateInMonth(travelDate, next)); }}>{months.map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label>Fecha histórica · 2017<input type="date" min="2017-01-01" max="2017-12-31" value={travelDate}
          onChange={(e) => { const value = e.target.value; if (/^2017-\d{2}-\d{2}$/.test(value)) { setTravelDate(value); const nextMonth = Number(value.slice(5, 7)); setMonth(nextMonth); } }}/></label>
        <label>Distancia del escenario · km<input className="trip-distance" type="number" min="0.01" max="10000" step="any" value={distanceInput} placeholder="Automática · demo"
          onChange={(e) => setDistanceInput(e.target.value)} title="Vacío: longitud de la polilínea de la demo. Un valor introducido escala los kilómetros y conserva la proporción de zonas con datos y sin datos; no reconstruye el trazado real."/></label>
        <label>Origen de afluencia<select value={trafficMode} onChange={(e) => setTrafficMode(e.target.value)}>
          <option value="auto">Automático · demo disponible</option>
          <option value="aadf_2017">AADF 2017 · carretera</option>
          <option value="historical_profile">Media histórica · celdas</option>
        </select></label>
        <label>Umbral de alerta
          <select
            value={activeThreshold}
            onChange={(e) => setSelectedThreshold(Number(e.target.value))}
            title="Los valores distintos del umbral oficial son simulaciones post-hoc sobre 2017"
          >
            {thresholdOptions.map((value) => {
              const official = Math.abs(value - officialThreshold) < 1e-9;
              return <option key={value} value={value}>{value.toFixed(3)}{official ? " · oficial" : " · exploratorio"}</option>;
            })}
          </select>
        </label>
        <label className="check-label"><input type="checkbox" checked={reverse} onChange={(e) => setReverse(e.target.checked)} />Invertir sentido</label>
        <label className="check-label audit"><input type="checkbox" checked={audit} onChange={(e) => setAudit(e.target.checked)} />Auditoría histórica</label>
      </section>

      {error && <div className="notice danger">{error}</div>}

      {route && (
        <div className={`threshold-strip ${isOfficialThreshold ? "official" : "exploratory"}`}>
          <div>
            <b>{isOfficialThreshold ? "Umbral validado en 2016" : "Simulación de umbral sobre 2017"}</b>
            <span>{activeThreshold.toFixed(3)}{isOfficialThreshold ? " · selección oficial por F1 en validation 2016" : " · no sustituye al umbral oficial 0,243"}</span>
          </div>
          {activeThresholdStats && (
            <div className="threshold-strip-metrics">
              <span>Precision <b>{pct(activeThresholdStats.precision)}</b></span>
              <span>Recall <b>{pct(activeThresholdStats.recall)}</b></span>
              <span>F1 <b>{Number(activeThresholdStats.f1).toFixed(3)}</b></span>
              <span>FP <b>{activeThresholdStats.false_positives}</b></span>
              <span>FN <b>{activeThresholdStats.false_negatives}</b></span>
            </div>
          )}
          {!isOfficialThreshold && <button type="button" className="threshold-reset" onClick={() => setSelectedThreshold(officialThreshold)}>Restablecer 0,243</button>}
        </div>
      )}

      {point && <>
        <div className="hero-grid">
          <div className="panel gauge-panel">
            <div className="road-title"><CarFront size={21}/><div><b>{point.road_name} · {route.month_name} 2017</b><span>{point.local_authority_name} · celda BNG {point.cell}</span></div></div>
            <RiskGauge
              percentile={point.risk_percentile}
              probability={point.p_final}
              threshold={activeThreshold}
              thresholdPercentile={activeThresholdScore}
              zonePercentiles={activeGaugeZones}
            />
            <div className={`alert-state ${visualState?.key || "normal"}`}>
              {thresholdAlertActive ? <ShieldAlert size={18}/> : <Lightbulb size={18}/>}
              {visualState?.key === "critical"
                ? (isOfficialThreshold ? "ALERTA ALTA" : "ALERTA ALTA · SIMULADA")
                : visualState?.key === "alert"
                  ? (isOfficialThreshold ? "ALERTA MODELO ACTIVA" : "ALERTA SIMULADA ACTIVA")
                  : visualState?.key === "watch"
                    ? "VIGILANCIA · CERCA DEL UMBRAL"
                    : "RIESGO BAJO EL UMBRAL"}
              <small>Umbral: {activeThreshold.toFixed(3)}{isOfficialThreshold ? " · oficial" : " · simulado"}</small>
            </div>
          </div>
          <div className="panel map-panel"><RouteMap points={route.points} currentIndex={index} threshold={activeThreshold}/><div className="map-note">{route.route_note} Los colores se recalculan con el umbral seleccionado.</div></div>
        </div>

        <div className="playback">
          <button className="icon-button" onClick={() => setIndex((i) => Math.max(0, i - 1))}><ChevronLeft/></button>
          <button className="play-button" onClick={() => setPlaying((v) => !v)}>{playing ? <Pause size={20}/> : <Play size={20}/>} {playing ? "Pausar" : "Recorrer ruta"}</button>
          <button className="icon-button" onClick={() => setIndex((i) => Math.min(route.points.length - 1, i + 1))}><ChevronRight/></button>
          <input className="route-slider" type="range" min="0" max={route.points.length - 1} value={index} onChange={(e) => setIndex(Number(e.target.value))}/>
          <span className="step-counter">{index + 1} / {route.points.length}</span>
        </div>

        <div className="metric-grid">
          <MetricCard label="Probabilidad Random Forest" value={pct(point.p_final)} sub="Al menos un DVC en la celda durante el mes" tone="teal"/>
          <MetricCard label="DVC esperados" value={num(point.pred_count_final, 2)} sub="Toda la celda y el mes · Poisson con offset" tone="orange"/>
          <MetricCard label="Riesgo aprox. · zonas con datos" value={tripPercent(route.daily_route_risk?.probability_approx)}
            sub={route.daily_route_risk?.probability_approx == null ? route.daily_route_risk?.reason || "Afluencia pendiente: prepara los datos AADF" : `${route.daily_route_risk?.traffic_basis === "historical_profile" ? "Media histórica 2008–2017" : "AADF 2017"} · ${travelDate.split("-").reverse().join("/")}`} tone="blue"/>
          <MetricCard label="Cobertura del recorrido de la demo" value={route.daily_route_risk?.coverage_fraction == null ? "—" : pct(route.daily_route_risk.coverage_fraction)}
            sub={route.daily_route_risk?.covered_distance_km == null ? "No disponible" : `${num(route.daily_route_risk.covered_distance_km, 1)} km con datos · ${num(route.daily_route_risk.uncovered_distance_km, 1)} km sin evaluar`}/>
        </div>

        <div className="metric-grid route-daily-inputs">
          <MetricCard label="DVC acumulados del mes · zonas con datos" value={num(route.daily_route_risk?.monthly_expected_dvc, 2)} sub={`${route.daily_route_risk?.available_cells?.length ?? 0} celdas únicas · suma de conteos Poisson`} tone="orange"/>
          <MetricCard label="DVC diarios medios · zonas con datos" value={num(route.daily_route_risk?.daily_expected_dvc, 3)} sub={`Acumulado mensual / ${route.daily_route_risk?.days_in_month ?? "—"} días`}/>
          <MetricCard label="Vehículos diarios medios · ruta" value={route.daily_route_risk?.daily_route_vehicles == null ? "—" : num(route.daily_route_risk.daily_route_vehicles, 2)} sub={`${route.daily_route_risk?.traffic_basis === "historical_profile" ? "Media histórica 2008–2017" : "AADF 2017"} · ${route.daily_route_risk?.traffic_points_used ?? 0} celdas`}/>
        </div>

        <div className="notice warning trip-risk-notice"><AlertTriangle size={18}/><div>
          <b>Estimación experimental para una pasada por las zonas con datos.</b>
          <p>{route.daily_route_risk?.reason || "No hay datos suficientes para calcular el escenario."}</p>
          <p><b>Origen de afluencia:</b> {route.daily_route_risk?.traffic_note}</p>
          <p><b>Probabilidad validada de la ruta completa: no disponible.</b> Los huecos quedan sin evaluar; su riesgo es desconocido. Los conteos son de celdas de 10 × 10 km y pueden incluir otras carreteras.</p>
          <p>Todos los días del mismo mes tienen la misma estimación: se suponen riesgo y tráfico uniformes. La afluencia se aproxima con la media diaria de los puntos. Ese promedio no mide cuántos vehículos completan la ruta.</p>
          <details className="trip-risk-details"><summary>Ver operación y supuestos</summary>
            <p>Riesgo aproximado (%) = DVC esperados acumulados del mes / días del mes / media de vehículos diarios de los puntos de la ruta × 100. Cada celda se suma una sola vez. La suma permanece igual al avanzar por los puntos o invertir el sentido.</p>
            {route.daily_route_risk?.monthly_expected_dvc != null && <p>
              Operación: {num(route.daily_route_risk.monthly_expected_dvc, 4)} / {route.daily_route_risk.days_in_month} / {route.daily_route_risk.daily_route_vehicles == null ? "afluencia pendiente" : num(route.daily_route_risk.daily_route_vehicles, 2)} × 100
              {route.daily_route_risk?.probability_approx != null ? ` = ${tripPercent(route.daily_route_risk.probability_approx)}` : " · porcentaje pendiente"}.
            </p>}
            <p>{route.daily_route_risk?.traffic_basis === "historical_profile"
              ? "La demo recupera el tráfico medio histórico de cada celda con expm1(log_traffic_mean). El perfil resume años disponibles entre 2008 y 2017 e incluye todas las vías de la celda. Se combinan conteos de 2017 con esta afluencia histórica aproximada."
              : "Para cada punto del mapa se obtiene la media de aforos AADF de esa carretera y celda en 2017."} Después se hace la media aritmética de los puntos, con igual peso por punto. El cociente aproxima una probabilidad para eventos raros, sin validación individual.</p>
            <p>La fecha selecciona el mes histórico de 2017. El resultado no utiliza las probabilidades mensuales del Random Forest. Cambiar la distancia de la demo no cambia esta suma ni la media de aforos; para otro recorrido se necesitan sus propios puntos y tráfico.</p>
            <p>La cobertura mostrada corresponde a la polilínea de la demo, no a la geometría real del asfalto. Los kilómetros sin datos no reciben un riesgo cero.</p>
          </details>
        </div></div>

        <div className="content-grid">
          <div className="panel">
            <h3>Perfil de riesgo de la ruta</h3>
            <div className="chart-box"><ResponsiveContainer width="100%" height={260}><LineChart data={chartData}><CartesianGrid strokeDasharray="3 3" stroke="#dfe8eb"/><XAxis dataKey="step"/><YAxis domain={[0,1]} tickFormatter={(v) => `${Math.round(v*100)}%`}/><Tooltip formatter={(v) => pct(v)}/><ReferenceLine x={index+1} stroke="#ef8e2f" strokeDasharray="4 4"/><ReferenceLine y={activeThreshold} stroke="#c34d45" strokeDasharray="4 4"/><Line type="monotone" dataKey="RandomForest" stroke="#13a89e" strokeWidth={3} dot={false}/><Line type="monotone" dataKey="LSTM" stroke="#2c7793" strokeWidth={2} dot={false} connectNulls/>{route.points.some((p) => p.p_mlp != null) && <Line type="monotone" dataKey="MLP" stroke="#8b5cf6" strokeWidth={2} dot={false}/>}
{route.points.some((p) => p.p_ensemble_exploratory != null) && <Line type="monotone" dataKey="Ensemble" stroke="#ef8e2f" strokeWidth={2} strokeDasharray="5 4" dot={false}/>}</LineChart></ResponsiveContainer></div>
          </div>
          <div className="panel">
            <h3>Contexto vial</h3>
            <div className="context-list">
              <div><span>Triaje</span><b>{triage.triage_level || "No disponible"}</b></div><div><span>Especie dominante</span><b>{triage.dominant_species || "No disponible"}</b></div><div><span>Severidad</span><b>{triage.severity_risk || "No disponible"}</b></div><div><span>Tipo OSM</span><b>{osm.highway || "unknown"}</b></div><div><span>Carriles</span><b>{osm.lanes ?? "—"}</b></div><div><span>Iluminada</span><b>{osm.is_lit ? "Sí" : "No"}</b></div><div><span>Bosque próximo</span><b>{osm.forest_within_200m ? "Sí" : "No"}</b></div>
            </div>
            <div className="notice info"><Trees size={18}/>El contexto OSM ayuda a explicar la situación, pero no se presenta como causa directa del score.</div>
          </div>
        </div>

        <div className="content-grid">
          <div className="panel"><h3>¿Por qué cambia el riesgo?</h3><p>{seasonalMessage}</p><p>El percentil <b>{point.risk_percentile.toFixed(1)}</b> sitúa esta observación frente al resto del test 2017. El score 0–100 comunica posición relativa en cartera.</p><div className="notice info"><Lightbulb size={18}/>La explicación disponible ahora es estacional y contextual. SHAP se incorporará cuando el modelo final se empaquete para inferencia online.</div></div>
          <div className="panel">
            <h3>Respuesta preventiva simulada</h3>
            <label className="range-label">
              <span>Velocidad simulada <b>{speed} mph</b></span>
              <input type="range" min="20" max="70" step="5" value={speed} onChange={(e) => setSpeed(Number(e.target.value))}/>
            </label>

            <div className="preventive-status">
              <div>
                <span>Intensidad de respuesta</span>
                <b>{Math.round(braking.intensity * 100)}%</b>
              </div>
              <div className="preventive-meter">
                <div style={{ width: `${Math.round(braking.intensity * 100)}%` }} />
              </div>
              <small>
                {braking.active
                  ? `La respuesta cambia automáticamente con el Risk Response Score (${point.risk_percentile.toFixed(1)}/100).`
                  : `No se aplica reducción: la probabilidad DVC (${pct(point.p_final)}) está por debajo del umbral (${activeThreshold.toFixed(3)}).`}
              </small>
            </div>

            <div className="braking-grid">
              <div><span>Distancia actual</span><b>{braking.current.toFixed(1)} m</b></div>
              <div><span>Objetivo preventivo</span><b>{braking.targetSpeed.toFixed(1)} mph</b></div>
              <div><span>Distancia con respuesta</span><b>{braking.reduced.toFixed(1)} m</b></div>
              <div><span>Reducción aproximada</span><b>{braking.saved.toFixed(1)} m</b></div>
            </div>

            <div className="notice warning">
              <AlertTriangle size={18}/>
              {isOfficialThreshold
                ? "La respuesta se activa con el umbral validado en 2016 y aumenta de forma continua con el Risk Response Score."
                : `La respuesta usa temporalmente el umbral ${activeThreshold.toFixed(3)} para explorar su efecto. Es una simulación post-hoc sobre 2017 y no un nuevo umbral validado.`}
              {" "}Sigue siendo una regla de demostración: nunca sustituye señalización, límite legal ni criterio del conductor.
            </div>
          </div>
        </div>

        {audit && <div className="notice danger audit-box"><AlertTriangle size={18}/><div><b>Resultado histórico · solo auditoría</b><p>target_presence = {point.target_presence} · DVC registrados = {point.dvc_count}. Esta información no existiría en el momento de una predicción real.</p></div></div>}
      </>}
    </div>
  );
}
