import { useMemo, useState } from "react";
import {
  AlertTriangle,
  Banknote,
  Calculator,
  Car,
  ExternalLink,
  Landmark,
  TrendingDown,
} from "lucide-react";
import MetricCard from "../components/MetricCard";

const money = (v, decimals = 0) =>
  new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  }).format(v);

const REFERENCE_PRESETS = {
  uk_recent: {
    label: "Referencia UK reciente · Zurich + DfT",
    frequency: 0.4843672456575682,
    cost: 4317.24,
    sourceTitle: "Zurich UK 2021/2025 + DfT 2021",
    sourceText:
      "Frecuencia proxy calculada a partir de ~32.000 claims anuales por colisiones con animales estimados por Zurich, 61% asociados a ciervos, y 40,3 millones de vehículos licenciados en UK. Coste medio DVC: £4.317,24 según claims Zurich 2024.",
    links: [
      {
        label: "Zurich UK · coste medio DVC 2024",
        url: "https://www.zurich.co.uk/media-centre/oh-deer-motorists-warned-spring-time-deer-collisions",
      },
      {
        label: "Zurich UK · claims animales 2021",
        url: "https://www.zurich.co.uk/media-centre/staycation-boom-drives-54-percent-increase-in-wildlife-fatalities-on-uk-roads",
      },
      {
        label: "DfT / DVLA · 40,3 M vehículos 2021",
        url: "https://www.gov.uk/government/statistics/vehicle-licensing-statistics-2021/vehicle-licensing-statistics-2021",
      },
    ],
  },
  fortis_historical: {
    label: "Referencia histórica · Fortis 2004–2005",
    frequency: 428 / 1200000 * 1000,
    cost: 1320,
    sourceTitle: "National Deer-Vehicle Collisions Project · Fortis Insurance",
    sourceText:
      "Referencia histórica: 428 claims DVC identificados en 2005 sobre unas 1,2 millones de pólizas privadas de motor de Fortis (~0,36/1.000). El informe indica un coste medio por claim DVC de £1.320 en 2004.",
    links: [
      {
        label: "Informe DVC England 2003–2005",
        url: "https://www.deercollisions.co.uk/web-content/ftp/DVC_England_FinalAs.pdf",
      },
    ],
  },
  custom: {
    label: "Datos propios / escenario personalizado",
    frequency: 0.48,
    cost: 4317.24,
    sourceTitle: "Valores introducidos por el usuario",
    sourceText:
      "Introduce una tasa anual DVC por cada 1.000 vehículos y un coste medio por claim. Si la aseguradora conoce sus claims reales: tasa = claims anuales / vehículos asegurados × 1.000.",
    links: [],
  },
};

export default function Economics() {
  const [preset, setPreset] = useState("uk_recent");
  const [vehicles, setVehicles] = useState(100000);
  const [frequency, setFrequency] = useState(REFERENCE_PRESETS.uk_recent.frequency);
  const [cost, setCost] = useState(REFERENCE_PRESETS.uk_recent.cost);
  const [reduction, setReduction] = useState(10);

  const activeReference = REFERENCE_PRESETS[preset];

  const applyPreset = (key) => {
    const next = REFERENCE_PRESETS[key];
    setPreset(key);
    setFrequency(next.frequency);
    setCost(next.cost);
  };

  const result = useMemo(() => {
    const expectedClaims = (vehicles / 1000) * frequency;
    const baseline = expectedClaims * cost;
    const avoided = expectedClaims * (reduction / 100);
    const savings = avoided * cost;

    return {
      expectedClaims,
      baseline,
      avoided,
      savings,
      rate: frequency,
      costPer1000Vehicles: frequency * cost,
    };
  }, [vehicles, frequency, cost, reduction]);

  return (
    <div>
      <header className="page-header">
        <div>
          <span className="eyebrow">BUSINESS SCENARIO</span>
          <h1>Simulador económico</h1>
          <p>
            Estima exposición económica a partir del tamaño de la cartera, una frecuencia anual DVC y el coste medio por claim.
            Los presets incorporan referencias públicas de aseguradoras británicas.
          </p>
        </div>
      </header>

      <div className="notice warning big-notice">
        <AlertTriangle size={22} />
        <div>
          <b>SIMULACIÓN, NO PREDICCIÓN ACTUARIAL</b>
          <p>
            La frecuencia y el coste pueden partir de referencias externas, pero la reducción atribuible a Roadkill Risk Engine sigue siendo hipotética hasta validarla con un piloto real.
          </p>
        </div>
      </div>

      <section className="panel economic-source-panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">FUENTE DE REFERENCIA</span>
            <h3>Base para frecuencia y severidad</h3>
          </div>
          <label>
            Preset
            <select value={preset} onChange={(e) => applyPreset(e.target.value)}>
              {Object.entries(REFERENCE_PRESETS).map(([key, value]) => (
                <option key={key} value={key}>{value.label}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="economic-reference-grid">
          <div className="economic-reference-stat">
            <span>Frecuencia de referencia</span>
            <b>{frequency.toFixed(2)} claims / 1.000 vehículos / año</b>
          </div>
          <div className="economic-reference-stat">
            <span>Coste medio de referencia</span>
            <b>{money(cost, 2)} / claim</b>
          </div>
          <div className="economic-reference-copy">
            <Landmark size={19} />
            <div>
              <b>{activeReference.sourceTitle}</b>
              <p>{activeReference.sourceText}</p>
              {!!activeReference.links.length && (
                <div className="source-links">
                  {activeReference.links.map((link) => (
                    <a key={link.url} href={link.url} target="_blank" rel="noreferrer">
                      {link.label} <ExternalLink size={12} />
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {preset === "uk_recent" && (
          <div className="notice info source-formula">
            <Calculator size={18} />
            <span>
              <b>Cómo se obtiene el 0,48:</b> 32.000 claims animales/año × 61% ciervos ≈ 19.520 DVC claims; 19.520 / 40,3 M vehículos × 1.000 ≈ <b>0,48 DVC claims / 1.000 vehículos/año</b>. Es un proxy nacional, no una tasa actuarial publicada por Zurich.
            </span>
          </div>
        )}
      </section>

      <div className="economic-layout">
        <section className="panel sliders-panel">
          <h3>Supuestos de cartera</h3>

          <label className="range-label">
            <span><Car size={17} /> Vehículos asegurados <b>{vehicles.toLocaleString("es-ES")}</b></span>
            <input
              type="range"
              min="10000"
              max="1000000"
              step="10000"
              value={vehicles}
              onChange={(e) => setVehicles(Number(e.target.value))}
            />
          </label>

          <label className="range-label">
            <span>Frecuencia DVC / 1.000 vehículos / año <b>{frequency.toFixed(2)}</b></span>
            <div className="compound-input">
              <input
                type="range"
                min="0.05"
                max="5"
                step="0.01"
                value={frequency}
                onChange={(e) => {
                  setFrequency(Number(e.target.value));
                  if (preset !== "custom") setPreset("custom");
                }}
              />
              <input
                className="number-input"
                type="number"
                min="0"
                step="0.01"
                value={Number(frequency.toFixed(2))}
                onChange={(e) => {
                  setFrequency(Math.max(0, Number(e.target.value) || 0));
                  if (preset !== "custom") setPreset("custom");
                }}
              />
            </div>
          </label>

          <label className="range-label">
            <span><Banknote size={17} /> Coste medio por claim <b>{money(cost, 2)}</b></span>
            <div className="compound-input">
              <input
                type="range"
                min="500"
                max="15000"
                step="50"
                value={cost}
                onChange={(e) => {
                  setCost(Number(e.target.value));
                  if (preset !== "custom") setPreset("custom");
                }}
              />
              <input
                className="number-input"
                type="number"
                min="0"
                step="1"
                value={Number(cost.toFixed(2))}
                onChange={(e) => {
                  setCost(Math.max(0, Number(e.target.value) || 0));
                  if (preset !== "custom") setPreset("custom");
                }}
              />
            </div>
          </label>

          <label className="range-label">
            <span><TrendingDown size={17} /> Reducción hipotética <b>{reduction}%</b></span>
            <input
              type="range"
              min="1"
              max="40"
              step="1"
              value={reduction}
              onChange={(e) => setReduction(Number(e.target.value))}
            />
          </label>

          <div className="notice info">
            Al aumentar el número de vehículos, aumentan automáticamente los claims esperados y el coste anual porque la frecuencia se expresa por cada 1.000 vehículos.
          </div>
        </section>

        <section className="panel economics-summary">
          <span className="eyebrow">ESCENARIO RESULTANTE</span>
          <div className="economics-big">{money(result.savings)}</div>
          <p>impacto potencial anual bajo los supuestos introducidos</p>

          <div className="metric-grid two">
            <MetricCard
              label="Siniestros DVC esperados / año"
              value={result.expectedClaims.toFixed(1)}
              sub={`${frequency.toFixed(2)} / 1.000 vehículos`}
              tone="teal"
            />
            <MetricCard
              label="Coste anual base"
              value={money(result.baseline)}
              sub={`${result.expectedClaims.toFixed(1)} claims × ${money(cost, 0)}`}
            />
            <MetricCard
              label="Siniestros hipotéticamente evitados"
              value={result.avoided.toFixed(1)}
              sub={`${reduction}% del volumen esperado`}
              tone="teal"
            />
            <MetricCard
              label="Coste esperado / 1.000 vehículos"
              value={money(result.costPer1000Vehicles)}
              sub="frecuencia × coste medio"
            />
            <MetricCard
              label="Claims / 1.000 vehículos"
              value={result.rate.toFixed(2)}
              sub="frecuencia anual utilizada"
            />
            <MetricCard
              label="Reducción asumida"
              value={`${reduction}%`}
              sub="hipótesis, no rendimiento demostrado"
              tone="orange"
            />
          </div>
        </section>
      </div>

      <section className="panel">
        <h3>Cómo debe presentarse esta pantalla</h3>
        <p>
          Con el preset UK reciente, la frecuencia de <b>~0,48 DVC claims por 1.000 vehículos/año</b> es una estimación nuestra a partir de datos públicos Zurich + DfT, mientras que el <b>coste medio de £4.317,24</b> sí procede directamente de claims Zurich 2024.
        </p>
        <p>
          La referencia Fortis es histórica y sirve como comprobación de orden de magnitud. Para una conversación real, la mejor opción es seleccionar <b>Datos propios</b> e introducir la tasa y el coste medio de la cartera de la aseguradora.
        </p>
        <p>
          El único parámetro que debe mantenerse explícitamente como hipótesis es la <b>reducción preventiva</b>. El MVP todavía no demuestra que Roadkill Risk Engine reduzca un 5%, 10% o 20% los siniestros.
        </p>
      </section>
    </div>
  );
}
