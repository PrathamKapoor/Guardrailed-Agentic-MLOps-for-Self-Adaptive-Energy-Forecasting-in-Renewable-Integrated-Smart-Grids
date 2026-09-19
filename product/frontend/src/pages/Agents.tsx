/** Agent assistant. Advisory only. Lifecycle action types are short-circuited
 *  to the "ACTION BLOCKED" notice; otherwise the request is forwarded to the
 *  existing bounded agent /api/agents/explain endpoint and the firewall
 *  decision is rendered.
 */
import { useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api/client";
import type { AgentExplanationResponse, AgentTypes, Recommendation } from "../api/types";
import { useAsync } from "../hooks/useApi";
import { Card, ErrorBanner, LoadingState, EmptyState, StatusPill } from "../components/common";
import { isLifecycleCommand, advisoryBlockedNotice } from "../api/agentSafety";

const EXAMPLE_QUESTIONS = [
  "Why was this model rejected?",
  "What caused the latest drift event?",
  "Why was this recommendation denied?",
  "What evidence supports this decision?",
];

function isAllowedRecommendation(r: string): r is Recommendation {
  return r === "INVESTIGATE" || r === "SUMMARIZE" || r === "EXPLAIN"
      || r === "REQUEST_HUMAN_REVIEW" || r === "CREATE_REPORT";
}

function Response({ response }: { response: AgentExplanationResponse }): ReactNode {
  return (
    <div className="agent-response">
      <div className="agent-response__head">
        <div>
          <div className="muted">Agent</div>
          <code>{response.agent_id} v{response.agent_version}</code>
        </div>
        <div>
          <div className="muted">Firewall</div>
          <StatusPill tone={response.firewall_decision === "allowed" ? "ok" : "bad"}>
            {response.firewall_decision}
          </StatusPill>
        </div>
        <div>
          <div className="muted">Confidence</div>
          {response.confidence.toFixed(2)}
        </div>
        <div>
          <div className="muted">Recommendation</div>
          {isAllowedRecommendation(response.recommendation)
            ? <StatusPill tone="ok">{response.recommendation}</StatusPill>
            : <StatusPill tone="bad">{response.recommendation}</StatusPill>}
        </div>
      </div>

      <div className="agent-response__panel">
        <div className="muted">Reasoning</div>
        <p>{response.reasoning_summary}</p>
      </div>

      <div className="agent-response__panel">
        <div className="muted">Limitations</div>
        <p>{response.limitations}</p>
      </div>

      <div className="agent-response__panel">
        <div className="muted">Evidence references</div>
        {response.input_evidence_refs.length === 0 ? (
          <div className="muted">None</div>
        ) : (
          <ul>{response.input_evidence_refs.map((e) => <li key={e}><code>{e}</code></li>)}</ul>
        )}
      </div>

      <div className="agent-response__panel">
        <div className="muted">Requires human review</div>
        <p>{response.requires_human_review ? "Yes" : "No"}</p>
      </div>
    </div>
  );
}

function ActionBlocked({ requested }: { requested: string }): ReactNode {
  const notice = advisoryBlockedNotice(requested as any);
  return (
    <div className="action-blocked" role="alert" aria-live="polite">
      <div className="action-blocked__title">{notice.title}</div>
      <p>{notice.body}</p>
      <p className="action-blocked__rec"><strong>Recommendation:</strong> {notice.recommendation}</p>
    </div>
  );
}

export function Agents(): ReactNode {
  const types = useAsync<AgentTypes>(() => api.getAgentTypes(), []);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState<string>("");
  const [response, setResponse] = useState<AgentExplanationResponse | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  const blocked = submitted ? isLifecycleCommand(submitted) : null;

  const submit = async (override?: string) => {
    const q = (override ?? query).trim();
    if (!q) return;
    setSubmitted(q);
    setSubmitting(true); setErr(null); setResponse(null);
    try {
      const r = await api.explain({ query: q, context: { target: "load", severity: "CRITICAL" } });
      setResponse(r);
    } catch (e) { setErr(e); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="page">
      <header className="page__head">
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h1 className="page__title" style={{ margin: 0 }}>Agent assistant</h1>
          <StatusPill tone="warn">ADVISORY ONLY</StatusPill>
        </div>
        <p className="page__lede">
          The agent can inspect evidence, compare alternatives, and produce
          recommendations. It cannot execute lifecycle actions. Every
          recommendation is forwarded to deterministic governance for evaluation.
        </p>
      </header>

      <Card title="Authority boundary" subtitle="The agent operates inside a governance firewall">
        <div className="authority">
          <div className="authority__agent">
            <div className="authority__agent-label">Agent — Allowed</div>
            <div className="authority__allow">
              <span className="authority__allow-item">✓ Analyze</span>
              <span className="authority__allow-item">✓ Advise</span>
              <span className="authority__allow-item">✓ Explain</span>
              <span className="authority__allow-item">✓ Summarize</span>
              <span className="authority__allow-item">✓ Request human review</span>
              <span className="authority__allow-item">✓ Create report</span>
            </div>
            <div className="authority__blocked">
              <span className="authority__blocked-item">✕ Promote</span>
              <span className="authority__blocked-item">✕ Deploy</span>
              <span className="authority__blocked-item">✕ Rollback</span>
              <span className="authority__blocked-item">✕ Retrain</span>
              <span className="authority__blocked-item">✕ Modify model</span>
              <span className="authority__blocked-item">✕ Modify features</span>
              <span className="authority__blocked-item">✕ Change policy</span>
            </div>
          </div>
          <div className="authority__divider">Recommendation → Governance evaluation</div>
          <div className="authority__gov">
            <div className="authority__gov-label">Governance — Authoritative</div>
            <div className="authority__gov-desc">
              The deterministic GovernanceEngine evaluates evidence against frozen
              policy. The agent cannot override, bypass, or execute the result.
            </div>
          </div>
        </div>
      </Card>

      <Card title="Bounded agent query types" subtitle="From the existing agent layer; advisory only">
        {types.loading ? <LoadingState label="Loading types…" rows={1} /> :
          types.error ? <ErrorBanner error={types.error} /> :
          types.data ? (
            <div className="agent-types">
              <div>
                <div className="muted">Allowed recommendation types</div>
                <ul className="chip-list">
                  {types.data.allowed_recommendation_types.map((r) => (
                    <li key={r}><code className="chip chip--ok">{r}</code></li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="muted">Query types</div>
                <ul className="chip-list">
                  {types.data.query_types.map((q) => <li key={q}><code>{q}</code></li>)}
                </ul>
              </div>
            </div>
          ) : <EmptyState title="No agent types" />}
      </Card>

      <Card title="Ask" subtitle="Type a question; lifecycle commands are short-circuited with the action-blocked notice">
        <div className="ask">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask the bounded agent…"
            onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
          />
          <button className="btn" onClick={() => submit()} disabled={submitting || !query.trim()}>
            {submitting ? "Asking…" : "Ask"}
          </button>
        </div>
        <div className="ask__examples">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button key={q} className="link link--example" onClick={() => { setQuery(q); submit(q); }}>
              {q}
            </button>
          ))}
        </div>
      </Card>

      {blocked ? (
        <Card title="Agent response">
          <ActionBlocked requested={blocked} />
        </Card>
      ) : response ? (
        <Card title="Agent response" subtitle={`Query: ${submitted}`}>
          <Response response={response} />
        </Card>
      ) : err ? (
        <Card title="Agent response">
          <ErrorBanner error={err} />
        </Card>
      ) : null}
    </div>
  );
}
