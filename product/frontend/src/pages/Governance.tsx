/** Governance: frozen policy + decision log + evaluator (read-only).
 *  Agent recommendation vs governance decision must be visually unmistakable.
 */
import { useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api/client";
import type { GovernanceDecisionRecord, GovernanceEvaluateRequest, PolicyInfo } from "../api/types";
import { useAsync } from "../hooks/useApi";
import { Card, DataTable, ErrorBanner, LoadingState, EmptyState, StatusPill } from "../components/common";

function DecisionDetail({ decision }: { decision: GovernanceDecisionRecord }): ReactNode {
  const isDeny = decision.decision === "DENY";
  return (
    <div className={`decision ${isDeny ? "decision--deny" : "decision--allow"}`}>
      <div className="decision__row">
        <div className="decision__label">Recommendation</div>
        <div className="decision__value"><code>{decision.requested_transition}</code></div>
      </div>
      <div className="decision__row">
        <div className="decision__label">Subject</div>
        <div className="decision__value"><code>{decision.subject_id}</code></div>
      </div>
      <div className="decision__row">
        <div className="decision__label">Governance decision</div>
        <div className="decision__value">
          <StatusPill tone={isDeny ? "bad" : "ok"}>{decision.decision}</StatusPill>
        </div>
      </div>
      <div className="decision__row">
        <div className="decision__label">Reason</div>
        <div className="decision__value">
          {decision.reason_codes && decision.reason_codes.length > 0
            ? decision.reason_codes.map((r) => <code key={r} className="chip">{r}</code>)
            : <span className="muted">—</span>}
        </div>
      </div>
      <div className="decision__row">
        <div className="decision__label">Policy</div>
        <div className="decision__value">
          <code>{decision.policy_id} v{decision.policy_version}</code>
        </div>
      </div>
      <div className="decision__row">
        <div className="decision__label">Decision fingerprint</div>
        <div className="decision__value">
          <code title={decision.decision_content_fingerprint}>
            {decision.decision_content_fingerprint.slice(0, 16)}…
          </code>
        </div>
      </div>
      <div className="decision__row">
        <div className="decision__label">Explanation</div>
        <div className="decision__value">{decision.explanation}</div>
      </div>
      {isDeny ? (
        <div className="decision__conclusion">
          <strong>Conclusion:</strong> the agent recommendation was not authorized by
          the deterministic governance layer. No lifecycle state was mutated.
        </div>
      ) : null}
    </div>
  );
}

function EvaluatorForm({ onResult }: { onResult: (r: GovernanceDecisionRecord) => void }): ReactNode {
  const [subject, setSubject] = useState("MLOPS-REF-PV-H24-V1");
  const [current, setCurrent] = useState("PROMOTION_ELIGIBLE");
  const [proposed, setProposed] = useState("APPROVAL_PENDING");
  const [actor, setActor] = useState("AGENT");
  const [benchmarkGate, setBenchmarkGate] = useState("BENCHMARK_GATE_FAIL");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<unknown>(null);

  const submit = async () => {
    setSubmitting(true); setErr(null);
    try {
      const body: GovernanceEvaluateRequest = {
        subject_id: subject, current_state: current, proposed_state: proposed,
        actor_type: actor, simulation: true, benchmark_gate: benchmarkGate,
      };
      const r = await api.evaluateGovernance(body);
      onResult(r);
    } catch (e) { setErr(e); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="evaluator">
      <div className="evaluator__row">
        <label>Subject <input value={subject} onChange={(e) => setSubject(e.target.value)} /></label>
        <label>From <input value={current} onChange={(e) => setCurrent(e.target.value)} /></label>
        <label>To <input value={proposed} onChange={(e) => setProposed(e.target.value)} /></label>
        <label>Actor <input value={actor} onChange={(e) => setActor(e.target.value)} /></label>
        <label>Benchmark gate
          <select value={benchmarkGate} onChange={(e) => setBenchmarkGate(e.target.value)}>
            <option value="BENCHMARK_GATE_PASS">BENCHMARK_GATE_PASS</option>
            <option value="BENCHMARK_GATE_FAIL">BENCHMARK_GATE_FAIL</option>
          </select>
        </label>
        <button className="btn" onClick={submit} disabled={submitting}>
          {submitting ? "Evaluating…" : "Evaluate through GovernanceEngine"}
        </button>
      </div>
      {err ? <ErrorBanner error={err} /> : null}
    </div>
  );
}

export function Governance(): ReactNode {
  const policy = useAsync<PolicyInfo>(() => api.getPolicy(), []);
  const list = useAsync<Array<Record<string, unknown>>>(() => api.listDecisions(20), []);
  const [selected, setSelected] = useState<GovernanceDecisionRecord | null>(null);

  return (
    <div className="page">
      <header className="page__head">
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h1 className="page__title" style={{ margin: 0 }}>Governance</h1>
          <StatusPill tone="warn">AUTHORITATIVE</StatusPill>
        </div>
        <p className="page__lede">
          Research metrics do not bypass lifecycle policy. The deterministic
          governance layer evaluates evidence against frozen criteria and produces
          ALLOW / DENY / REQUIRE_APPROVAL decisions. The agent cannot override
          the result.
        </p>
      </header>

      <Card title="Frozen policy" subtitle={policy.data ? `${policy.data.policy_id} v${policy.data.policy_version}` : "—"}>
        {policy.loading ? <LoadingState label="Loading policy…" rows={1} /> :
          policy.error ? <ErrorBanner error={policy.error} /> :
          policy.data ? (
            <div className="policy-grid">
              <div><span className="muted">Policy ID</span> <code>{policy.data.policy_id}</code></div>
              <div><span className="muted">Version</span> {policy.data.policy_version}</div>
              <div><span className="muted">Checksum</span> <code title={policy.data.policy_checksum}>{policy.data.policy_checksum.slice(0, 16)}…</code></div>
              <div><span className="muted">Fingerprint</span> <code title={policy.data.governance_policy_fingerprint}>{policy.data.governance_policy_fingerprint.slice(0, 24)}…</code></div>
              <div><span className="muted">Source</span> <code>{policy.data.source_path}</code></div>
            </div>
          ) : <EmptyState title="No policy" />}
      </Card>

      <Card title="Try a decision" subtitle="Submit a request; the existing GovernanceEngine returns ALLOW or DENY">
        <EvaluatorForm onResult={(r) => setSelected(r)} />
        {selected ? <div className="evaluator__result"><DecisionDetail decision={selected} /></div> : null}
      </Card>

      <Card title="Recent decisions" subtitle="From the existing Phase 13 evidence ledger (JSONL)">
        {list.loading ? <LoadingState label="Loading decisions…" rows={3} /> :
          list.error ? <ErrorBanner error={list.error} /> :
          list.data && list.data.length > 0 ? (
            <DataTable
              rows={list.data}
              keyFn={(r) => String(r["decision_id"] || r["timestamp"] || Math.random())}
              columns={[
                { key: "ts", label: "Time", render: (r) => <span className="muted">{String(r["timestamp"] || "")}</span> },
                { key: "subject", label: "Subject", render: (r) => <code>{String(r["subject_id"] || r["model_id"] || "")}</code> },
                { key: "decision", label: "Decision", render: (r) => <StatusPill tone={r["decision"] === "DENY" ? "bad" : (r["decision"] === "ALLOW" ? "ok" : "info")}>{String(r["decision"] || "")}</StatusPill> },
                { key: "reason", label: "Reason", render: (r) => Array.isArray(r["reason_codes"]) ? r["reason_codes"].join(", ") : "—" },
              ]}
            />
          ) : <EmptyState title="No decisions" />}
      </Card>
    </div>
  );
}
