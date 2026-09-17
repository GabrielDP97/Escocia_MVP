import { RISK_VISUAL_STATES, riskVisualState } from "../lib/riskVisuals";

function polarPoint(cx, cy, radius, degrees) {
  const radians = (degrees * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians),
  };
}

function arcPath(cx, cy, radius, startDegrees, endDegrees) {
  const start = polarPoint(cx, cy, radius, startDegrees);
  const end = polarPoint(cx, cy, radius, endDegrees);
  const largeArcFlag = endDegrees - startDegrees > 180 ? 1 : 0;

  return [
    "M", start.x, start.y,
    "A", radius, radius, 0, largeArcFlag, 1, end.x, end.y,
  ].join(" ");
}

function clampScore(value) {
  return Math.max(0, Math.min(100, Number(value) || 0));
}

function scoreDegrees(score) {
  return 180 + (clampScore(score) / 100) * 180;
}

export default function RiskGauge({
  percentile = 0,
  probability = 0,
  threshold = 0.2425809815683556,
  thresholdPercentile = null,
  zonePercentiles = null,
}) {
  const bounded = clampScore(percentile);
  const state = riskVisualState(probability, threshold);

  // 0/100 = extremo izquierdo (180º)
  // 50/100 = vertical (270º)
  // 100/100 = extremo derecho (360º)
  const needleDegrees = scoreDegrees(bounded);

  const cx = 120;
  const cy = 116;
  const radius = 92;
  const needleRadius = 78;
  const needleEnd = polarPoint(cx, cy, needleRadius, needleDegrees);

  const thresholdScore = thresholdPercentile == null
    ? null
    : clampScore(thresholdPercentile);

  // Las zonas del arco se reciben ya convertidas desde probabilidad al mismo
  // percentil empírico 0-100 del Risk Response Score. De este modo el color
  // bajo la aguja representa exactamente la misma lógica que el estado textual.
  const normalToWatch = zonePercentiles?.normalToWatch == null
    ? Math.max(0, (thresholdScore ?? 70) - 10)
    : clampScore(zonePercentiles.normalToWatch);
  const watchToAlert = zonePercentiles?.watchToAlert == null
    ? (thresholdScore ?? 80)
    : clampScore(zonePercentiles.watchToAlert);
  const alertToCritical = zonePercentiles?.alertToCritical == null
    ? Math.min(100, (thresholdScore ?? 80) + 10)
    : clampScore(zonePercentiles.alertToCritical);

  const boundaries = [normalToWatch, watchToAlert, alertToCritical]
    .map(clampScore)
    .sort((a, b) => a - b);

  const [normalEnd, watchEnd, alertEnd] = boundaries;

  const arcSegments = [
    { key: "normal", from: 0, to: normalEnd, color: RISK_VISUAL_STATES.normal.color },
    { key: "watch", from: normalEnd, to: watchEnd, color: RISK_VISUAL_STATES.watch.color },
    { key: "alert", from: watchEnd, to: alertEnd, color: RISK_VISUAL_STATES.alert.color },
    { key: "critical", from: alertEnd, to: 100, color: RISK_VISUAL_STATES.critical.color },
  ];

  const thresholdDegrees = thresholdScore == null ? null : scoreDegrees(thresholdScore);
  const thresholdInner = thresholdDegrees == null ? null : polarPoint(cx, cy, 74, thresholdDegrees);
  const thresholdOuter = thresholdDegrees == null ? null : polarPoint(cx, cy, 105, thresholdDegrees);

  return (
    <div className={`gauge-wrap gauge-state-${state.key}`} style={{ "--risk-state-color": state.color }}>
      <div className="gauge">
        <svg
          className="gauge-svg"
          viewBox="0 0 240 132"
          role="img"
          aria-label={`Risk Response Score ${Math.round(bounded)} de 100. Estado ${state.label}.`}
        >
          <path d={arcPath(cx, cy, radius, 180, 360)} className="gauge-arc gauge-arc-background" />

          {arcSegments.map((segment) => {
            if (segment.to - segment.from < 0.001) return null;
            return (
              <path
                key={segment.key}
                d={arcPath(cx, cy, radius, scoreDegrees(segment.from), scoreDegrees(segment.to))}
                className={`gauge-arc gauge-arc-${segment.key}`}
                style={{ stroke: segment.color }}
              />
            );
          })}

          {thresholdInner && thresholdOuter && (
            <g className="gauge-threshold-marker">
              <line
                x1={thresholdInner.x}
                y1={thresholdInner.y}
                x2={thresholdOuter.x}
                y2={thresholdOuter.y}
                className="gauge-threshold-line"
              />
              <circle cx={thresholdOuter.x} cy={thresholdOuter.y} r="3.5" className="gauge-threshold-dot" />
            </g>
          )}

          <line
            x1={cx}
            y1={cy}
            x2={needleEnd.x}
            y2={needleEnd.y}
            className="gauge-needle-svg"
          />
          <circle cx={cx} cy={cy} r="8" className="gauge-center-svg" />
        </svg>
      </div>

      <div className="gauge-score">
        {Math.round(bounded)}<span>/100</span>
      </div>
      <div className="gauge-caption">Risk Response Score</div>
      <div className="gauge-probability">
        {(Number(probability || 0) * 100).toFixed(1)}% probabilidad DVC
      </div>
      <div className="gauge-state-label">
        <span className="gauge-state-dot" />{state.label}
        {thresholdScore != null && <small>Umbral ≈ score {Math.round(thresholdScore)}/100</small>}
      </div>
    </div>
  );
}
