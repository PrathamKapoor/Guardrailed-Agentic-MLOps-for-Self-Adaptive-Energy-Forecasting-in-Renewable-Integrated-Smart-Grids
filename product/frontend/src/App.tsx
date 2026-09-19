/** App router: persistent sidebar + 7 route components. */
import { Routes, Route, Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { Sidebar } from "./components/Sidebar";
import { PageErrorBoundary } from "./components/ErrorBoundary";
import { useApiHealth } from "./hooks/useApi";
import { Dashboard } from "./pages/Dashboard";
import { Forecasts } from "./pages/Forecasts";
import { Models } from "./pages/Models";
import { Monitoring } from "./pages/Monitoring";
import { Governance } from "./pages/Governance";
import { Agents } from "./pages/Agents";
import { Audit } from "./pages/Audit";
import { Demo } from "./pages/Demo";
import Grainient from "./components/Grainient";

export function App(): ReactNode {
  const { online } = useApiHealth();
  return (
    <div className="shell">
      <div className="bg-grainient" aria-hidden="true">
        <Grainient
          color1="#F6F1E7"
          color2="#DCE5D6"
          color3="#E7DEC9"
          timeSpeed={0.12}
          warpStrength={0.7}
          warpFrequency={4.0}
          warpSpeed={1.2}
          warpAmplitude={40}
          rotationAmount={320}
          noiseScale={2.4}
          grainAmount={0.10}
          grainScale={1.6}
          contrast={1.05}
          saturation={0.55}
          zoom={0.85}
        />
      </div>
      <Sidebar apiOnline={online} />
      <main className="content" id="main" tabIndex={-1}>
        <PageErrorBoundary>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/forecasts" element={<Forecasts />} />
            <Route path="/models" element={<Models />} />
            <Route path="/models/:model_id" element={<Models />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/governance" element={<Governance />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/demo" element={<Demo />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </PageErrorBoundary>
      </main>
    </div>
  );
}
