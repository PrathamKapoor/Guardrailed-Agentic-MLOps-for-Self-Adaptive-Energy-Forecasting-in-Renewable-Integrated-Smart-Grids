/** Model registry: read-only list + detail view. NO mutation UI. */
import { useState, useMemo } from "react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { ModelRecord } from "../api/types";
import { useAsync } from "../hooks/useApi";
import { Card, DataTable, ErrorBanner, LoadingState, EmptyState, StatusPill } from "../components/common";

function ListView({ onSelect }: { onSelect: (id: string) => void }): ReactNode {
  const list = useAsync<ModelRecord[]>(() => api.listModels(), []);
  if (list.loading) return <LoadingState label="Loading models…" rows={3} />;
  if (list.error) return <ErrorBanner error={list.error} />;
  if (!list.data || list.data.length === 0) return <EmptyState title="No models" />;
  return (
    <DataTable
      rows={list.data}
      keyFn={(m) => m.registry_id}
      columns={[
        { key: "id", label: "Registry ID",
          render: (m) => <button className="link" onClick={() => onSelect(m.registry_id)}><code>{m.registry_id}</code></button> },
        { key: "target", label: "Target", render: (m) => m.target.toUpperCase() },
        { key: "model", label: "Model", render: (m) => <code>{m.model_family}</code> },
        { key: "features", label: "Features", render: (m) => m.feature_set_id },
        { key: "state", label: "Lifecycle",
          render: (m) => <StatusPill tone={m.lifecycle_state === "ACTIVE" ? "ok" : "info"}>{m.lifecycle_state}</StatusPill> },
        { key: "gate", label: "Benchmark gate",
          render: (m) => <StatusPill tone={m.development_benchmark_gate === "BENCHMARK_GATE_PASS" ? "ok" : "warn"}>{m.development_benchmark_gate}</StatusPill> },
        { key: "dev_mae", label: "Dev MAE", render: (m) => m.development_mae.toFixed(2), align: "right" },
        { key: "final_mae", label: "Final-test MAE", render: (m) => m.benchmark_mae.toFixed(2), align: "right" },
      ]}
    />
  );
}

function DetailView({ modelId }: { modelId: string }): ReactNode {
  const detail = useAsync<ModelRecord>(() => api.getModel(modelId), [modelId]);
  if (detail.loading) return <LoadingState label="Loading model…" rows={4} />;
  if (detail.error) return <ErrorBanner error={detail.error} />;
  if (!detail.data) return <EmptyState title="Model not found" />;
  const m = detail.data;
  return (
    <div className="model-detail">
      <DataTable
        rows={[m]}
        keyFn={() => m.registry_id}
        columns={[
          { key: "k", label: "Model", render: (x) => <code>{x.model_family}</code> },
          { key: "t", label: "Target", render: (x) => x.target.toUpperCase() },
          { key: "v", label: "Fingerprint", render: (x) => <code title={x.model_spec_fingerprint}>{x.model_spec_fingerprint.slice(0, 16)}…</code> },
          { key: "f", label: "Features", render: (x) => x.feature_set_id },
          { key: "l", label: "Lifecycle", render: (x) => <StatusPill tone="info">{x.lifecycle_state}</StatusPill> },
          { key: "g", label: "Governance", render: (x) => x.development_benchmark_gate },
        ]}
      />
      <div className="model-detail__metrics">
        <DataTable
          rows={[m]}
          keyFn={() => m.registry_id + "-m"}
          columns={[
            { key: "d", label: "Dev MAE", render: (x) => x.development_mae.toFixed(4), align: "right" },
            { key: "b", label: "Final-test benchmark MAE", render: (x) => x.benchmark_mae.toFixed(4), align: "right" },
            { key: "f", label: "Final-test status", render: (x) => x.final_test_performance_status },
          ]}
        />
      </div>
    </div>
  );
}

export function Models(): ReactNode {
  const [selected, setSelected] = useState<string | null>(null);
  const params = useParams<{ model_id?: string }>();
  const idFromUrl = params.model_id;
  const active = useMemo(() => idFromUrl ?? selected, [idFromUrl, selected]);
  return (
    <div className="page">
      <header className="page__head">
        <h1 className="page__title">Model registry</h1>
        <p className="page__lede">
          Read-only view of the existing Phase 11 / Phase 13 research registry.
          No Promote / Deploy / Rollback / Retrain buttons are exposed; lifecycle
          operations remain the responsibility of the deterministic governance layer.
        </p>
      </header>

      <Card title="Models" subtitle={`${active ?? "select a model to inspect"}`} aside={
        <StatusPill tone="info">read-only</StatusPill>
      }>
        <ListView onSelect={(id) => setSelected(id)} />
      </Card>

      {active ? (
        <Card title={`Model detail — ${active}`} subtitle="Live from the Stage 2 API">
          <DetailView modelId={active} />
          <div className="model-detail__back">
            <Link to="/models" className="link">← Back to model list</Link>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
