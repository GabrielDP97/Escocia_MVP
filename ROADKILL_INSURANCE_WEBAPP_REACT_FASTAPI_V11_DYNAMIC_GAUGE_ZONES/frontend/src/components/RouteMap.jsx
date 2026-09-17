import { useEffect } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import { pct } from "../lib/api";
import { riskVisualLegend, riskVisualState } from "../lib/riskVisuals";

function Follow({ point }) {
  const map = useMap();
  useEffect(() => {
    if (point?.lat && point?.lon) map.flyTo([point.lat, point.lon], Math.max(map.getZoom(), 8), { duration: 0.5 });
  }, [point?.lat, point?.lon, map]);
  return null;
}

export default function RouteMap({ points, currentIndex, threshold }) {
  const current = points?.[currentIndex];
  const legend = riskVisualLegend(threshold);
  if (!current) return <div className="map-placeholder">Sin geometría disponible.</div>;

  return (
    <div className="route-map-wrap">
      <MapContainer center={[current.lat, current.lon]} zoom={8} className="leaflet-map" scrollWheelZoom>
        <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

        {(points || []).slice(1).map((p, idx) => {
          const previous = points[idx];
          const state = riskVisualState(p.p_final, threshold);
          return (
            <Polyline
              key={`segment-${previous.cell}-${p.cell}-${idx}`}
              positions={[[previous.lat, previous.lon], [p.lat, p.lon]]}
              pathOptions={{ color: state.color, weight: 4, opacity: 0.74 }}
            />
          );
        })}

        {(points || []).map((p, idx) => {
          const state = riskVisualState(p.p_final, threshold);
          return (
            <CircleMarker
              key={`${p.cell}-${idx}`}
              center={[p.lat, p.lon]}
              radius={idx === currentIndex ? 11 : 5 + p.p_final * 5}
              pathOptions={{
                color: idx === currentIndex ? "#ffffff" : state.color,
                fillColor: state.color,
                fillOpacity: idx === currentIndex ? 1 : 0.78,
                weight: idx === currentIndex ? 4 : 1.4,
              }}
            >
              <Popup>
                <b>{p.road_name} · celda {p.cell}</b><br />
                Riesgo: {pct(p.p_final)}<br />
                Percentil: {p.risk_percentile.toFixed(1)}<br />
                Estado: <b style={{ color: state.color }}>{state.label}</b><br />
                Umbral seleccionado: {Number(threshold).toFixed(3)}
              </Popup>
            </CircleMarker>
          );
        })}
        <Follow point={current} />
      </MapContainer>

      <div className="map-risk-legend" aria-label="Leyenda de riesgo según el umbral seleccionado">
        {legend.map((item) => (
          <span key={item.key}><i style={{ background: item.color }} />{item.label}</span>
        ))}
      </div>
    </div>
  );
}
