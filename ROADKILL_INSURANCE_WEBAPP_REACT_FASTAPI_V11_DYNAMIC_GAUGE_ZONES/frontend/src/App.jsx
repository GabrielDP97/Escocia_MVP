import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { CarFront, ChartNoAxesCombined, Calculator, FlaskConical, ShieldCheck, Beaker } from "lucide-react";
import DriverDemo from "./pages/DriverDemo";
import Portfolio from "./pages/Portfolio";
import Economics from "./pages/Economics";
import Methodology from "./pages/Methodology";
import TechnologyLab from "./pages/TechnologyLab";

const nav = [
  { to: "/driver", label: "Demo conductor", icon: CarFront },
  { to: "/portfolio", label: "Dashboard aseguradora", icon: ChartNoAxesCombined },
  { to: "/economics", label: "Simulador económico", icon: Calculator },
  { to: "/methodology", label: "Metodología", icon: FlaskConical },
  { to: "/technology-lab", label: "Laboratorio tecnológico", icon: Beaker },
];

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><ShieldCheck size={24} /></div>
          <div><strong>Roadkill</strong><span>Risk Engine</span></div>
        </div>
        <div className="historic-badge">HISTORICAL MVP · 2017</div>
        <nav>
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              <Icon size={18} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-note">
          <b>Demo para aseguradoras</b>
          <span>Predicciones reales del test 2017. El movimiento del vehículo y el escenario económico son simulados.</span>
        </div>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/driver" element={<DriverDemo />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/economics" element={<Economics />} />
          <Route path="/methodology" element={<Methodology />} />
          <Route path="/technology-lab" element={<TechnologyLab />} />
          <Route path="*" element={<Navigate to="/driver" replace />} />
        </Routes>
      </main>
    </div>
  );
}
