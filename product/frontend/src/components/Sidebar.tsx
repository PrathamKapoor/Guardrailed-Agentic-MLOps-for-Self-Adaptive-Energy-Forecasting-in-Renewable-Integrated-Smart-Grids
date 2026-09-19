/** Sidebar → LatentForge-style sticky top header: brand, nav pills, status badges. */
import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";

interface SidebarProps { apiOnline: boolean }

const NAV = [
  { to: "/", label: "Dashboard" },
  { to: "/forecasts", label: "Forecasts" },
  { to: "/models", label: "Models" },
  { to: "/monitoring", label: "Monitoring" },
  { to: "/governance", label: "Governance" },
  { to: "/agents", label: "Agents" },
  { to: "/audit", label: "Audit" },
  { to: "/demo", label: "Demo" },
];

function Link({ to, label }: { to: string; label: string }): ReactNode {
  return (
    <NavLink to={to} end={to === "/"}
      className={({ isActive }) => `sidebar__link${isActive ? " sidebar__link--active" : ""}`}>
      <span className="sidebar__link-label">{label}</span>
    </NavLink>
  );
}

export function Sidebar({ apiOnline }: SidebarProps): ReactNode {
  return (
    <header className="sidebar" aria-label="Primary navigation">
      <div className="sidebar__inner">
        <a className="sidebar__brand" href="/" aria-label="SmartGrid MLOps home">
          <svg className="sidebar__brand-mark" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
            <path fill="currentColor" d="M12 1.5 21.5 7v10L12 22.5 2.5 17V7L12 1.5zm0 5.1L7.1 9.5v5L12 17.4l4.9-2.9v-5L12 6.6z" />
          </svg>
          <span className="sidebar__brand-title">SmartGrid MLOps</span>
          <span className="brand-tag">Lab</span>
        </a>

        <nav className="sidebar__nav" aria-label="Sections">
          {NAV.map((x) => <Link key={x.to} to={x.to} label={x.label} />)}
        </nav>

        <div className="sidebar__status">
          <span className="sidebar__status-row">
            <span className={`sidebar__status-dot ${apiOnline ? "online" : "offline"}`} />
            <span>{apiOnline ? "Connected" : "Offline"}</span>
          </span>
          <span className="sidebar__status-mode">OFFLINE EVALUATION</span>
          <span className="sidebar__authority muted">
            Agent <strong>advisory</strong> · Governance <strong>authoritative</strong>
          </span>
        </div>

        <div className="sidebar__foot">
          <span className="sidebar__foot-q">Quantum/QML: NOT PART OF PROJECT</span>
        </div>
      </div>
    </header>
  );
}
