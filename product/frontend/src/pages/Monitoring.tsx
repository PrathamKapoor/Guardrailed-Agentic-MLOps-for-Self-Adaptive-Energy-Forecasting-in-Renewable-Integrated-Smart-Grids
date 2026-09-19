/** Monitoring: historical replay + incremental monitoring over frozen evidence.
 *  NOT live telemetry. All data is derived from the locked test partition. */
import { useState, useMemo } from "react";
import type { ReactNode } from "react";
import { api } from "../api/client";
import type { MonitoringEvent } from "../api/types";
import { useAsync } from "../hooks/useApi";
import { Card, DataTable, ErrorBanner, LoadingState, EmptyState, SeverityBadge, StatusPill } from "../components/common";

export function Monitoring(): ReactNode {
  const [eventType, setEventType] = useState<string>("");
  const [target, setTarget] = useState<string>("");
  const all = useAsync<MonitoringEvent[]>(() => api.listMonitoringEvents({}), []);
  const drift = useAsync<MonitoringEvent[]>(() => api.listDrift(), []);
  const events = useMemo(() => {
    const src = all.data ?? [];
    return src.filter((e) => !eventType || e.event_type === eventType)
                 .filter((e) => !target || e.target === target);
  }, [all.data, eventType, target]);

  if (all.error) return <ErrorBanner error={all.error} />;

  return (
    <div className="page">
      <header className="page__head">
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h1 className="page__title" style={{ margin: 0 }}>Monitoring</h1>
          <StatusPill tone="warn">HISTORICAL REPLAY</StatusPill>
          <StatusPill tone="info">NOT LIVE TELEMETRY</StatusPill>
        </div>
        <p className="page__lede">
          Drift, performance, and model-health events derived from the frozen
          final-test evidence via incremental evaluation over replayed historical
          data. Not live monitoring — no streaming, no real-time ingestion.
        </p>
      </header>

      <div>
        <div className="section-label">Drift timeline — productization monitoring events</div>
        <Card title="Drift timeline" subtitle="Derived from frozen final-test evidence; one-shot read">
          {drift.loading ? <LoadingState label="Loading drift events…" rows={3} /> :
            drift.data && drift.data.length > 0 ? (
              <ul className="timeline" aria-label="Drift event timeline">
                {drift.data.map((e) => (
                  <li key={e.event_id} className="timeline__item">
                    <div className="timeline__time">{e.timestamp}</div>
                    <div className="timeline__body">
                      <code>{e.event_type}</code> on <strong>{e.target}</strong> ({e.model})
                      {e.extra["final_test_status"] ? <SeverityBadge severity={String(e.extra["final_test_status"])} /> : null}
                    </div>
                  </li>
                ))}
              </ul>
            ) : <EmptyState title="No drift events" />}
        </Card>
      </div>

      <div>
        <div className="section-label">All monitoring events — filter by type and target</div>
        <Card title="All monitoring events">
          <div className="filter-row">
            <label>Event type
              <select value={eventType} onChange={(e) => setEventType(e.target.value)}>
                <option value="">All</option>
                <option value="performance_evaluation">performance_evaluation</option>
                <option value="prediction_distribution">prediction_distribution</option>
                <option value="model_health">model_health</option>
              </select>
            </label>
            <label>Target
              <select value={target} onChange={(e) => setTarget(e.target.value)}>
                <option value="">All</option>
                <option value="load">LOAD</option>
                <option value="wind">WIND</option>
                <option value="pv">PV</option>
              </select>
            </label>
          </div>
          {all.loading ? <LoadingState label="Loading events…" rows={3} /> :
            <DataTable
              rows={events}
              keyFn={(e) => e.event_id}
              columns={[
                { key: "ts", label: "Time", render: (e) => <span className="muted">{e.timestamp}</span> },
                { key: "type", label: "Type", render: (e) => <code>{e.event_type}</code> },
                { key: "target", label: "Target", render: (e) => e.target },
                { key: "model", label: "Model", render: (e) => e.model },
                { key: "sev", label: "Severity",
                  render: (e) => {
                    const s = String((e.extra as { final_test_status?: string })?.final_test_status ?? "");
                    return s ? <SeverityBadge severity={s} /> : <span className="muted">—</span>;
                  } },
              ]}
            />}
        </Card>
      </div>
    </div>
  );
}
