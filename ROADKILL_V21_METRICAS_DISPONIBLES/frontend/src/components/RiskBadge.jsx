const config = {
  "BAJO": ["risk-low", "Bajo"],
  "MODERADO": ["risk-medium", "Moderado"],
  "ALTO": ["risk-high", "Alto"],
  "MUY ALTO": ["risk-critical", "Muy alto"],
};
export default function RiskBadge({ band }) {
  const [css, label] = config[band] || config.BAJO;
  return <span className={`risk-badge ${css}`}>{label}</span>;
}
