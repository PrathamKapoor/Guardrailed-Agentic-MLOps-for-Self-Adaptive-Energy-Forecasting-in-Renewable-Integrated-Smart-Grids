/** Audit: existing evidence-ledger events + JSONL well-formedness verification.
 *  Wording is intentionally honest: "VALID JSONL" not "cryptographically verified".
 */
import { useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api/client";
import type { AuditChainVerification, AuditEvent } from "../api/types";
import { useAsync } from "../hooks/useApi";
import { Card, DataTable, ErrorBanner, LoadingState, EmptyState, StatusPill } from "../components/common";

function integrityLabel(v: AuditChainVerification | null): { tone: "ok" | "bad"; label: string } {
  if (!v) return { tone: "bad", label: "UNKNOWN" };
  if (v.chain_ok) return { tone: "ok", label: "VALID JSONL" };
  return { tone: "bad", label: "INVALID" };
}

export function Audit(): ReactNode {
  const [eventType, setEventType] = useState<string>("");
  const [subject, setSubject] = useState<string>("");
  const list = useAsync<AuditEvent[]>(() => api.listAuditEvents({ limit: 200 }), []);
  const verify = useAsync<AuditChainVerification>(() => api.verifyAudit(), []);

  const events = Array.isArray(list.data) ? (list.data as AuditEvent[]) : [];

  const intg = integrityLabel(verify.data ?? null);

  return (
    <div className="page">
      <header className="page__head">
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h1 className="page__title" style={{ margin: 0 }}>Audit</h1>
          <StatusPill tone="info">APPEND-ONLY JSONL</StatusPill>
        </div>
        <p className="page__lede">
          The existing evidence ledger is an append-only JSONL file. The
          verification endpoint validates that every line is well-formed JSON;
          it does not claim a cryptographic hash-chain guarantee. Every
          governance decision, agent query, and system event is recorded here.
        </p>
      </header>

      <Card title="Audit structure" subtitle="From /api/audit/verify (Stage 2 FastAPI)">
        {verify.loading ? <LoadingState label="Verifying…" rows={1} /> :
          verify.error ? <ErrorBanner error={verify.error} /> :
          verify.data ? (
            <div className="integrity">
              <div>
                <div className="muted">Status</div>
                <StatusPill tone={intg.tone}>{intg.label}</StatusPill>
              </div>
              <div>
                <div className="muted">Head</div>
                <code>{verify.data.head || "—"}</code>
              </div>
              <div>
                <div className="muted">Message</div>
                <code>{verify.data.message || "—"}</code>
              </div>
              <p className="integrity__note">
                Honest wording: the existing implementation verifies JSONL well-formedness
                only. It does not claim cryptographic verification.
              </p>
            </div>
          ) : <EmptyState title="No verification result" />}
      </Card>

      <Card title="Audit events" subtitle="From the existing evidence-ledger JSONL">
        <div className="filter-row">
          <label>Event type
            <input value={eventType} onChange={(e) => setEventType(e.target.value)} placeholder="e.g. AGENT_QUERY_RECEIVED" />
          </label>
          <label>Subject
            <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="subject_id" />
          </label>
        </div>
        {list.loading ? <LoadingState label="Loading events…" rows={3} /> :
          list.error ? <ErrorBanner error={list.error} /> :
          <DataTable
            rows={events}
            keyFn={(a) => String(a.seq ?? a.timestamp) + a.type}
            columns={[
              { key: "ts", label: "Time", render: (a) => <span className="muted">{a.timestamp}</span> },
              { key: "type", label: "Type", render: (a) => <code>{a.type}</code> },
              { key: "subject", label: "Subject", render: (a) => <code>{String(a.record["subject_id"] ?? "—")}</code> },
              { key: "details", label: "Details", render: (a) => <code>{JSON.stringify(a.record).slice(0, 60)}…</code> },
            ]}
          />}
      </Card>
    </div>
  );
}
