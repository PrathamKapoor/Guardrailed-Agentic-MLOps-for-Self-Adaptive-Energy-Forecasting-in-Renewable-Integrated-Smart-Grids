/** Command center. Shows the system at a glance: forecast evidence,
 *  pipeline state, authority model, and research-to-governance outcomes. */
import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { api } from "../api/client";
import type { ForecastInfo, MonitoringEvent, GovernanceDecisionRecord, AuditEvent } from "../api/types";
import { useAsync } from "../hooks/useApi";
import { Card, DataTable, EmptyState, ErrorBanner, LoadingState, StatusPill, SeverityBadge } from "../components/common";
import MaskedHeading from "../components/MaskedHeading";
import { ResearchConsole } from "../components/ResearchConsole";
import { TARGETS } from "../api/types";

// Light→deep green gradient fill shown through the masked hero heading letters.
const HERO_FILL = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1600' height='600'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0' stop-color='%234ADE80'/%3E%3Cstop offset='1' stop-color='%2315803D'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='1600' height='600' fill='url(%23g)'/%3E%3C/svg%3E";

const PIPELINE = [
  { num: "01", label: "FORECAST", desc: "Frozen model evaluation" },
  { num: "02", label: "MONITOR", desc: "Historical replay" },
  { num: "03", label: "ANALYZE", desc: "Bounded agent, advisory" },
  { num: "04", label: "GOVERN", desc: "Deterministic policy" },
  { num: "05", label: "DECIDE", desc: "ALLOW / DENY / REQUIRE APPROVAL" },
  { num: "06", label: "AUDIT", desc: "Append-only evidence" },
] as const;

const RESEARCH = [
  { stage: "07", label: "Historical Telemetry Replay", desc: "Simulated replay; not live", status: "Complete", denied: false },
  { stage: "08", label: "Incremental Monitoring", desc: "Chronological, warm-up aware", status: "Complete", denied: false },
  { stage: "09", label: "Forecasting Research", desc: "Honest baseline comparison", status: "Complete", denied: false },
  { stage: "10", label: "Residual Correction", desc: "Best LOAD candidate MAE 1.54", status: "Strong result", denied: false },
  { stage: "11", label: "Robustness Validation", desc: "5-fold validation, 0 leakage", status: "Complete", denied: false },
  { stage: "12", label: "Governance Evaluation", desc: "Formal evidence gaps found", status: "7/7 DENY", denied: true },
  { stage: "13", label: "Candidate Packaging", desc: "Formal evidence prepared", status: "Complete", denied: false },
  { stage: "14", label: "Governance Re-Evaluation", desc: "Authoritative engine re-evaluated", status: "7/7 DENY", denied: true },
] as const;

function Pipeline() {
  return (
    <div className="pipeline">
      {PIPELINE.map((s, i) => (
        <div key={s.num}>
          <div className={`pipeline__stage${i < 2 ? " pipeline__stage--active" : ""}`}>
            <span className="pipeline__num">{s.num}</span>
            <div>
              <div className="pipeline__label">{s.label}</div>
              <div className="pipeline__desc">{s.desc}</div>
            </div>
          </div>
          {i < PIPELINE.length - 1 && <div className="pipeline__arrow">↓</div>}
        </div>
      ))}
    </div>
  );
}

function AuthorityModel() {
  return (
    <div className="authority">
      <div className="authority__agent">
        <div className="authority__agent-label">Agent</div>
        <div className="authority__allow">
          <span className="authority__allow-item">Analyze</span>
          <span className="authority__allow-item">Advise</span>
          <span className="authority__allow-item">Explain</span>
          <span className="authority__allow-item">Summarize</span>
        </div>
        <div className="authority__blocked">
          <span className="authority__blocked-item">Promote</span>
          <span className="authority__blocked-item">Deploy</span>
          <span className="authority__blocked-item">Rollback</span>
          <span className="authority__blocked-item">Retrain</span>
          <span className="authority__blocked-item">Modify model</span>
          <span className="authority__blocked-item">Modify features</span>
          <span className="authority__blocked-item">Change policy</span>
        </div>
      </div>
      <div className="authority__divider">Recommendation only</div>
      <div className="authority__gov">
        <div className="authority__gov-label">Governance</div>
        <div className="authority__gov-desc">Deterministic policy engine. Evaluates evidence against frozen criteria.</div>
        <div className="authority__gov-decision">
          <span className="allow">ALLOW</span>
          <span className="deny">DENY</span>
          <span className="req">REQUIRE APPROVAL</span>
        </div>
      </div>
    </div>
  );
}

function SysStatus() {
  return (
    <div className="sys-status">
      <div className="sys-status__item"><div className="sys-status__label">Forecasting</div><div className="sys-status__value sys-status__value--ok">Active</div></div>
      <div className="sys-status__item"><div className="sys-status__label">Monitoring</div><div className="sys-status__value sys-status__value--info">Historical replay</div></div>
      <div className="sys-status__item"><div className="sys-status__label">Agent</div><div className="sys-status__value sys-status__value--ok">Advisory</div></div>
      <div className="sys-status__item"><div className="sys-status__label">Governance</div><div className="sys-status__value sys-status__value--ok">Authoritative</div></div>
      <div className="sys-status__item"><div className="sys-status__label">Lifecycle</div><div className="sys-status__value sys-status__value--protected">Protected</div></div>
      <div className="sys-status__item"><div className="sys-status__label">Audit</div><div className="sys-status__value sys-status__value--ok">Append-only</div></div>
    </div>
  );
}

function ResearchPipeline() {
  return (
    <Card title="Research & Governance" subtitle="Strong research metrics did not automatically become production approval">
      <div className="research-headline">
        <div>
          <div className="research-headline__metric">MAE 1.54</div>
          <div className="research-headline__metric-sub">LOAD residual correction</div>
        </div>
        <div className="research-headline__vs">
          ≈98.5% reduction vs the referenced day-ahead baseline (RTS_DAY_AHEAD, MAE 101.14).
          Discovered in Stage 10 residual correction research.
        </div>
        <div className="research-headline__deny">
          <span className="research-headline__deny-label">DENY</span>
          <span className="research-headline__deny-note">
            Governance evaluated all 7 candidates across Stages 12 and 14.
            Research evidence did not bypass lifecycle policy.
          </span>
        </div>
      </div>
      <div className="research-timeline">
        {RESEARCH.map((s) => (
          <div key={s.stage} className={`research-stage ${s.denied ? "research-stage--denied" : "research-stage--complete"}`}>
            <div className="research-stage__num">{s.stage}</div>
            <div>
              <div className="research-stage__label">{s.label}</div>
              <div className="research-stage__desc">{s.desc}</div>
            </div>
            <div className={`research-stage__status ${s.denied ? "research-stage__status--denied" : "research-stage__status--complete"}`}>
              {s.denied ? "✕" : "✓"} {s.status}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function Dashboard(): ReactNode {
  const forecasts = useAsync<ForecastInfo[]>(() => api.listForecasts(), []);
  const events = useAsync<MonitoringEvent[]>(() => api.listMonitoringEvents({}), []);
  const decisions = useAsync<GovernanceDecisionRecord[]>(
    () => api.listDecisions(10) as unknown as Promise<GovernanceDecisionRecord[]>, [],
  );
  const audit = useAsync<AuditEvent[]>(() => api.listAuditEvents({ limit: 5 }), []);

  return (
    <div className="page">
      <h1 className="page__title" style={{ position: "absolute", left: "-9999px", overflow: "hidden" }}>Executive dashboard</h1>

      {/* Hero */}
      <div className="hero">
        <div>
          <div className="hero__eyebrow">SmartGrid MLOps · Offline Evaluation</div>
          <MaskedHeading
            tag="h2"
            className="hero__title"
            text="Forecasting research, bounded agent analysis, and deterministic lifecycle governance."
            src={HERO_FILL}
            align="left"
            textScale={0.042}
            reveal="rise"
            trigger="view"
            weight={600}
            tracking={-0.04}
            lineHeight={1.08}
            fillScale={1.3}
            parallax={18}
            drift={10}
          />
          <p className="hero__subtitle">
            The agent can analyze and advise. The governance engine makes the
            authoritative decision. Nothing is autonomously deployed.
          </p>
          <div className="hero__actions">
            <Link to="/demo" className="hero__btn hero__btn--primary">Enter Demo Mode</Link>
            <Link to="/governance" className="hero__btn hero__btn--secondary">View Governance</Link>
          </div>
        </div>
        <Pipeline />
      </div>

      {/* System status strip */}
      <SysStatus />

      {/* Forecast evidence */}
      <div className="section" style={{ marginTop: 32 }}>
        <div className="section-label">Fig. 01 · Forecast evidence — locked test partition</div>
        <Card>
          {forecasts.loading ? <LoadingState label="Loading…" rows={1} /> :
            forecasts.error ? <ErrorBanner error={forecasts.error} /> :
            forecasts.data ? (
              <div className="targets-row">
                {TARGETS.map((t) => {
                  const r = Array.isArray(forecasts.data) ? forecasts.data.find((x) => x.target === t) : undefined;
                  if (!r) return null;
                  const ok = r.final_test_relative_difference_pct < 0;
                  return (
                    <div key={t} className={`target-card ${ok ? "target-card--better" : "target-card--worse"}`}>
                      <div className="target-card__head">
                        <div className="target-card__name">{t}</div>
                        <div className="target-card__model">{r.model}</div>
                      </div>
                      <div className="target-card__metrics">
                        <div><span>MAE</span><span>{r.final_test_mae.toFixed(2)}</span></div>
                        <div><span>{r.strongest_benchmark}</span><span>{r.final_test_benchmark_mae.toFixed(2)}</span></div>
                        <div><span>Δ</span><span>{r.final_test_relative_difference_pct >= 0 ? "+" : ""}{r.final_test_relative_difference_pct.toFixed(2)}%</span></div>
                      </div>
                      <div className="target-card__verdict">
                        <StatusPill tone={ok ? "ok" : "bad"}>
                          {ok ? "Better" : "Worse"} than benchmark
                        </StatusPill>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : <EmptyState title="No forecasts" hint="The API returned no forecast records." />}
        </Card>
      </div>

      {/* Workflow */}
      <div className="section" style={{ marginTop: 32 }}>
        <div className="section-label">Fig. 02 · System workflow</div>
        <Card title="Primary workflow: DRIFT → AGENT → GOVERNANCE" subtitle="Read-only visual of the canonical pipeline; not a simulation.">
          <div className="flow">
            <div className="flow__step">
              <div className="flow__step-label">1. Drift / Degradation</div>
              <div className="flow__step-body">
                {events.loading ? <LoadingState label="Loading…" rows={1} /> :
                  events.data && events.data.length > 0 ? (
                    <ul className="flow__events">
                      {events.data.slice(0, 3).map((e) => (
                        <li key={e.event_id}>
                          <code>{e.event_type}</code> on <strong>{e.target}</strong> ({e.model})
                          <SeverityBadge severity={(e.extra as { final_test_status?: string })?.final_test_status as string
                                                  ?? e.event_type.split("_")[0]} />
                        </li>
                      ))}
                    </ul>
                  ) : <div className="muted">No monitoring events yet.</div>}
              </div>
            </div>
            <div className="flow__arrow" aria-hidden>→</div>
            <div className="flow__step">
              <div className="flow__step-label">2. Agent investigates</div>
              <div className="flow__step-body">
                Bounded agent layer reads monitoring events through the existing
                Orchestrator and proposes an advisory recommendation.
              </div>
            </div>
            <div className="flow__arrow" aria-hidden>→</div>
            <div className="flow__step">
              <div className="flow__step-label">3. Agent recommends</div>
              <div className="flow__step-body">
                The recommendation is one of INVESTIGATE / SUMMARIZE / EXPLAIN /
                REQUEST_HUMAN_REVIEW / CREATE_REPORT. Lifecycle action types
                are blocked by the governance firewall.
              </div>
            </div>
            <div className="flow__arrow" aria-hidden>→</div>
            <div className="flow__step">
              <div className="flow__step-label">4. Governance evaluates</div>
              <div className="flow__step-body">
                The deterministic <code>GovernanceEngine</code> (frozen Phase 13
                policy, 13-state machine) produces a <code>GovernanceDecision</code>
                with a SHA-256 decision fingerprint.
              </div>
            </div>
            <div className="flow__arrow" aria-hidden>→</div>
            <div className="flow__step">
              <div className="flow__step-label">5. ALLOW / DENY</div>
              <div className="flow__step-body">
                The decision is recorded in the evidence ledger. The lifecycle
                registry is mutated only by the research pipeline, never by the
                agent layer.
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Authority model */}
      <div className="section" style={{ marginTop: 32 }}>
        <div className="section-label">Fig. 03 · Authority model</div>
        <Card>
          <AuthorityModel />
        </Card>
      </div>

      {/* Research pipeline */}
      <div className="section" style={{ marginTop: 32 }}>
        <ResearchPipeline />
      </div>

      {/* Live research console */}
      <div className="section" style={{ marginTop: 32 }}>
        <div className="section-label">Fig. 06 · Live research console — dataset → MLOps forecast → agentic advisory</div>
        <ResearchConsole />
      </div>

      {/* Side panels */}
      <div className="section" style={{ marginTop: 32, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
        <div>
          <div className="section-label">Fig. 04 · Recent governance decisions</div>
          <Card aside={<Link to="/governance" className="card__link">View all →</Link>}>
            {decisions.loading ? <LoadingState label="Loading…" rows={3} /> :
              decisions.error ? <ErrorBanner error={decisions.error} /> :
              decisions.data && decisions.data.length > 0 ? (
                <DataTable
                  rows={decisions.data}
                  keyFn={(d: GovernanceDecisionRecord) => d.decision_id || d.timestamp}
                  columns={[
                    { key: "ts", label: "Time", render: (d) => <span className="muted">{d.timestamp}</span> },
                    { key: "subject", label: "Subject", render: (d) => <code>{d.subject_id}</code> },
                    { key: "decision", label: "Decision",
                      render: (d) => <StatusPill tone={d.decision === "ALLOW" ? "ok" : (d.decision === "DENY" ? "bad" : "info")}>{d.decision}</StatusPill> },
                    { key: "reason", label: "Reason", render: (d) => (d.reason_codes || []).join(", ") || "—" },
                  ]}
                />
              ) : <EmptyState title="No recent decisions" />}
          </Card>
        </div>
        <div>
          <div className="section-label">Fig. 05 · Recent audit events</div>
          <Card aside={<Link to="/audit" className="card__link">View all →</Link>}>
            {audit.loading ? <LoadingState label="Loading…" rows={3} /> :
              audit.error ? <ErrorBanner error={audit.error} /> :
              audit.data && audit.data.length > 0 ? (
                <DataTable
                  rows={audit.data}
                  keyFn={(a: AuditEvent) => String(a.seq ?? a.timestamp) + a.type}
                  columns={[
                    { key: "ts", label: "Time", render: (a) => <span className="muted">{a.timestamp}</span> },
                    { key: "type", label: "Type", render: (a) => <code>{a.type}</code> },
                  ]}
                />
              ) : <EmptyState title="No audit events" />}
          </Card>
        </div>
      </div>
    </div>
  );
}
