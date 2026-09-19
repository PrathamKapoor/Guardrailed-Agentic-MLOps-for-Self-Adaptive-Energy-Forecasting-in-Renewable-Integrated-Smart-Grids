/** Demo Mode. Read-only and deterministic. Two scenarios:
 *    1. PRIMARY: Forecasting → drift detection → agent analysis → governance → audit
 *    2. SAFETY: agent recommends a lifecycle action, governance blocks it
 *
 *  Step navigation is local UI state; the demo does not mutate the backend.
 *  Real API data is referenced (forecast / governance / monitoring / audit) via
 *  api_refs and rendered from the live Stage 2 service.
 */
import { useState, useMemo } from "react";
import type { ReactNode } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { Card, DataTable, ErrorBanner, LoadingState, EmptyState, StatusPill, SeverityBadge } from "../components/common";
import { useAsync } from "../hooks/useApi";
import { api } from "../api/client";
import { PRIMARY_SCENARIO, SAFETY_SCENARIO, FINAL_INTERPRETATION } from "../demo/demoData";
import type { DemoStep } from "../demo/demoData";

const SCENARIOS = [PRIMARY_SCENARIO, SAFETY_SCENARIO];

function StepKindBadge({ kind }: { kind: DemoStep["kind"] }): ReactNode {
  const tone = (
    kind === "forecast" ? "info"
    : kind === "monitoring" ? "warn"
    : kind === "agent" ? "info"
    : kind === "governance" ? "bad"
    : kind === "audit" ? "ok"
    : kind === "safety" ? "bad"
    : "info"
  ) as "ok" | "warn" | "bad" | "info";
  return <StatusPill tone={tone}>{kind.toUpperCase()}</StatusPill>;
}

function StepBody({ step }: { step: DemoStep }): ReactNode {
  // Pull live data from the existing API where the step references it.
  if (!step.api_refs) {
    return (
      <div className="demo-step__body">
        <p>{step.body}</p>
        {step.highlight ? <p className="demo-step__highlight"><strong>{step.highlight}</strong></p> : null}
      </div>
    );
  }
  return <StepWithApiRefs step={step} />;
}

function StepWithApiRefs({ step }: { step: DemoStep }): ReactNode {
  const ref = step.api_refs!;
  if (ref.kind === "forecast") {
    return <ForecastStep step={step} />;
  }
  if (ref.kind === "monitoring") {
    return <MonitoringStep step={step} />;
  }
  if (ref.kind === "governance") {
    return <GovernanceStep step={step} />;
  }
  if (ref.kind === "audit") {
    return <AuditStep step={step} />;
  }
  // agent: nothing extra to render
  return <AgentStep step={step} />;
}

function ForecastStep({ step }: { step: DemoStep }): ReactNode {
  const f = useAsync(() => api.listForecasts(), []);
  return (
    <div className="demo-step__body">
      <p>{step.body}</p>
      {f.loading ? <LoadingState label="Loading forecast info…" rows={1} /> :
        f.error ? <ErrorBanner error={f.error} /> :
        f.data && f.data.length > 0 ? (
          <DataTable
            rows={f.data}
            keyFn={(r) => r.target}
            columns={[
              { key: "t", label: "Target", render: (r) => r.target.toUpperCase() },
              { key: "m", label: "Model", render: (r) => <code>{r.model}</code> },
              { key: "mae", label: "MAE", render: (r) => r.final_test_mae.toFixed(2), align: "right" },
              { key: "b", label: "Benchmark", render: (r) => r.strongest_benchmark },
              { key: "bmae", label: "Bench MAE", render: (r) => r.final_test_benchmark_mae.toFixed(2), align: "right" },
              { key: "d", label: "Δ", render: (r) => (r.final_test_relative_difference_pct >= 0 ? "+" : "") + r.final_test_relative_difference_pct.toFixed(2) + "%" },
            ]}
          />
        ) : <EmptyState title="No forecast info" />}
      {step.highlight ? <p className="demo-step__highlight"><strong>{step.highlight}</strong></p> : null}
    </div>
  );
}

function MonitoringStep({ step }: { step: DemoStep }): ReactNode {
  const m = useAsync(() => api.listMonitoringEvents({}), []);
  return (
    <div className="demo-step__body">
      <p>{step.body}</p>
      {m.loading ? <LoadingState label="Loading monitoring events…" rows={1} /> :
        m.error ? <ErrorBanner error={m.error} /> :
        m.data ? (
          <DataTable
            rows={m.data}
            keyFn={(e) => e.event_id}
            columns={[
              { key: "ts", label: "Time", render: (e) => <span className="muted">{e.timestamp}</span> },
              { key: "t", label: "Type", render: (e) => <code>{e.event_type}</code> },
              { key: "g", label: "Target", render: (e) => e.target },
              { key: "m", label: "Model", render: (e) => e.model },
              { key: "s", label: "Status",
                render: (e) => {
                  const s = String((e.extra as { final_test_status?: string })?.final_test_status ?? "");
                  return s ? <SeverityBadge severity={s} /> : <span className="muted">—</span>;
                } },
            ]}
          />
        ) : <EmptyState title="No events" />}
      {step.highlight ? <p className="demo-step__highlight"><strong>{step.highlight}</strong></p> : null}
    </div>
  );
}

function GovernanceStep({ step }: { step: DemoStep }): ReactNode {
  // Use the real /api/governance/decisions evaluator for one well-known deny:
  // (subject = MLOPS-REF-LOAD-H24-V1, current=PROMOTION_ELIGIBLE, proposed=APPROVAL_PENDING,
  //  benchmark_gate=BENCHMARK_GATE_FAIL) deterministically returns DENY.
  const r = useAsync(
    () => api.evaluateGovernance({
      subject_id: "MLOPS-REF-LOAD-H24-V1", current_state: "PROMOTION_ELIGIBLE",
      proposed_state: "APPROVAL_PENDING", actor_type: "AGENT", simulation: true,
      benchmark_gate: "BENCHMARK_GATE_FAIL",
    }),
    [],
  );
  return (
    <div className="demo-step__body">
      <p>{step.body}</p>
      {r.loading ? <LoadingState label="Evaluating through the frozen Phase 13 policy…" rows={1} /> :
        r.error ? <ErrorBanner error={r.error} /> :
        r.data ? (
          <div className="gov-card">
            <div className="gov-card__head">
              <div>
                <div className="muted">Governance decision</div>
                <StatusPill tone={r.data.decision === "ALLOW" ? "ok" : "bad"}>{r.data.decision}</StatusPill>
              </div>
              <div>
                <div className="muted">Subject</div>
                <code>{r.data.subject_id}</code>
              </div>
              <div>
                <div className="muted">Transition</div>
                <code>{r.data.current_state} → {r.data.proposed_state}</code>
              </div>
            </div>
            <div className="gov-card__row">
              <div className="muted">Reason codes</div>
              <div>{r.data.reason_codes.length === 0 ? <span className="muted">—</span> :
                r.data.reason_codes.map((c) => <code key={c} className="chip chip--bad">{c}</code>)}</div>
            </div>
            <div className="gov-card__row">
              <div className="muted">Policy</div>
              <code>{r.data.policy_id} v{r.data.policy_version}</code>
            </div>
            <div className="gov-card__row">
              <div className="muted">Decision fingerprint</div>
              <code title={r.data.decision_content_fingerprint}>
                {r.data.decision_content_fingerprint.slice(0, 16)}…
              </code>
            </div>
            <div className="gov-card__row">
              <div className="muted">Explanation</div>
              <div>{r.data.explanation}</div>
            </div>
          </div>
        ) : <EmptyState title="No governance decision" />}
      {step.highlight ? <p className="demo-step__highlight"><strong>{step.highlight}</strong></p> : null}
    </div>
  );
}

function AgentStep({ step }: { step: DemoStep }): ReactNode {
  // Use the real /api/agents/types endpoint to display the bounded query set
  // (the advisory contract). No LLM is invoked at runtime.
  const t = useAsync(() => api.getAgentTypes(), []);
  return (
    <div className="demo-step__body">
      <p>{step.body}</p>
      {t.loading ? <LoadingState label="Loading agent types…" rows={1} /> :
        t.error ? <ErrorBanner error={t.error} /> :
        t.data ? (
          <div className="agent-card">
            <div>
              <div className="muted">Allowed recommendation types</div>
              <ul className="chip-list">
                {t.data.allowed_recommendation_types.map((r) => (
                  <li key={r}><code className="chip chip--ok">{r}</code></li>
                ))}
              </ul>
            </div>
            <p className="muted">{t.data.notes}</p>
          </div>
        ) : <EmptyState title="No agent types" />}
      {step.highlight ? <p className="demo-step__highlight"><strong>{step.highlight}</strong></p> : null}
    </div>
  );
}

function AuditStep({ step }: { step: DemoStep }): ReactNode {
  const v = useAsync(() => api.verifyAudit(), []);
  return (
    <div className="demo-step__body">
      <p>{step.body}</p>
      {v.loading ? <LoadingState label="Verifying audit…" rows={1} /> :
        v.error ? <ErrorBanner error={v.error} /> :
        v.data ? (
          <div className="audit-card">
            <div><span className="muted">Status</span>
              <StatusPill tone={v.data.chain_ok ? "ok" : "bad"}>
                {v.data.chain_ok ? "VALID JSONL" : "INVALID"}
              </StatusPill>
            </div>
            <div><span className="muted">Head</span> <code>{v.data.head || "—"}</code></div>
            <div><span className="muted">Message</span> <code>{v.data.message || "—"}</code></div>
            <p className="muted">
              Honest wording: the existing implementation verifies JSONL
              well-formedness only. It does not claim cryptographic verification.
            </p>
          </div>
        ) : <EmptyState title="No verification result" />}
      {step.highlight ? <p className="demo-step__highlight"><strong>{step.highlight}</strong></p> : null}
    </div>
  );
}

function FinalInterpretation(): ReactNode {
  return (
    <Card title="Final result interpretation" subtitle="Honest mixed outcome from the locked final test">
      <div className="final-interpretation">
        {(["pv", "load", "wind"] as const).map((t) => {
          const r = FINAL_INTERPRETATION[t];
          const cls = r.verdict === "Better than benchmark" ? "target-card--better" : "target-card--worse";
          return (
            <div key={t} className={`target-card ${cls}`}>
              <div className="target-card__head">
                <div className="target-card__name">{t.toUpperCase()}</div>
                <StatusPill tone={r.verdict === "Better than benchmark" ? "ok" : "bad"}>
                  {r.verdict}
                </StatusPill>
              </div>
              <p>{r.text}</p>
              <div className="delta-pill">
                Δ {r.relative_difference_pct >= 0 ? "+" : ""}{r.relative_difference_pct.toFixed(2)}%
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export function Demo(): ReactNode {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const initialScenario = params.get("scenario") === "safety" ? "safety" : "primary";
  const initialStep = Math.max(0, parseInt(params.get("step") || "0", 10) || 0);
  const [scenarioId, setScenarioId] = useState<"primary" | "safety">(initialScenario);
  const [stepIndex, setStepIndex] = useState<number>(initialStep);
  const [presentation, setPresentation] = useState<boolean>(params.get("present") === "1");

  const scenario = useMemo(
    () => (scenarioId === "safety" ? SAFETY_SCENARIO : PRIMARY_SCENARIO),
    [scenarioId],
  );

  const updateUrl = (s: "primary" | "safety", i: number, p: boolean) => {
    const next = new URLSearchParams();
    next.set("scenario", s);
    next.set("step", String(i));
    if (p) next.set("present", "1");
    setParams(next, { replace: true });
  };

  const setStep = (i: number) => {
    const clamped = Math.max(0, Math.min(scenario.steps.length - 1, i));
    setStepIndex(clamped);
    updateUrl(scenarioId, clamped, presentation);
  };
  const setScn = (s: "primary" | "safety") => {
    setScenarioId(s);
    setStepIndex(0);
    updateUrl(s, 0, presentation);
  };
  const setPres = (p: boolean) => {
    setPresentation(p);
    updateUrl(scenarioId, stepIndex, p);
  };

  const step = scenario.steps[stepIndex];

  return (
    <div className={`page demo-page ${presentation ? "demo-page--presentation" : ""}`}>
      <header className="page__head">
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h1 className="page__title" style={{ margin: 0 }}>Demo Mode</h1>
          <StatusPill tone="info">DETERMINISTIC WALKTHROUGH</StatusPill>
        </div>
        <p className="page__lede">
          Every value below is sourced from the Stage 2 FastAPI service or the
          frozen Phase 11/13/19 artefacts. The agent recommends; governance
          decides. Reset is a no-op; the demo does not mutate the backend.
        </p>
      </header>

      <div className="demo-controls">
        <div className="demo-controls__scenarios" role="tablist" aria-label="Demo scenario">
          {SCENARIOS.map((s) => (
            <button key={s.id} role="tab" aria-selected={scenario.id === s.id}
                    className={`target-btn ${scenario.id === s.id ? "target-btn--active" : ""}`}
                    onClick={() => setScn(s.id === SAFETY_SCENARIO.id ? "safety" : "primary")}>
              {s.title}
            </button>
          ))}
        </div>
        <div className="demo-controls__pres">
          <button className="link" onClick={() => setPres(!presentation)}>
            {presentation ? "Exit presentation mode" : "Enter presentation mode"}
          </button>
          <Link to="/" className="link">Back to dashboard</Link>
        </div>
      </div>

      <Card title={scenario.title} subtitle={`Step ${stepIndex + 1} of ${scenario.steps.length}`}>
        <div className="step-indicator" aria-label="Step progress">
          {scenario.steps.map((s, i) => (
            <button key={s.id}
                    className={`step-indicator__dot ${i === stepIndex ? "step-indicator__dot--active" : i < stepIndex ? "step-indicator__dot--past" : ""}`}
                    onClick={() => setStep(i)}
                    aria-label={`Step ${i + 1}: ${s.title}`}>
              <span className="step-indicator__label">{i + 1}</span>
              <span className="step-indicator__name">{s.title}</span>
            </button>
          ))}
        </div>
        <div className="demo-step">
          <div className="demo-step__head">
            <h3 className="demo-step__title">
              <StepKindBadge kind={step.kind} /> {step.title}
            </h3>
          </div>
          <StepBody step={step} />
        </div>
        <div className="demo-step__nav">
          <button className="btn" onClick={() => setStep(stepIndex - 1)} disabled={stepIndex === 0}>
            ← Previous
          </button>
          <button className="link" onClick={() => { setScn(scenarioId); setStep(0); }}>
            Restart
          </button>
          <button className="btn" onClick={() => setStep(stepIndex + 1)}
                  disabled={stepIndex === scenario.steps.length - 1}>
            Next →
          </button>
        </div>
      </Card>

      <FinalInterpretation />

      <Card title="Non-goals" subtitle="What the demo does NOT do">
        <ul className="limitations">
          <li>The demo does <strong>not</strong> retrain models, modify datasets, or regenerate research metrics.</li>
          <li>The demo does <strong>not</strong> claim cryptographic audit verification — only JSONL well-formedness is verified by the existing implementation.</li>
          <li>The demo does <strong>not</strong> add a fake real-time inference path, a fake LLM, or any quantum / QML / GNN component.</li>
          <li>Reset is a no-op: the demo state is a read-only snapshot, not a mutation surface.</li>
        </ul>
      </Card>

      <div className="demo-exit">
        <button className="link" onClick={() => navigate("/")}>← Back to operations console</button>
      </div>
    </div>
  );
}
