/** Forecasts page: per-target research evaluation with benchmark comparison.
 *  HISTORICAL DATA — locked test partition, not live inference. */
import { useState, useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { api } from "../api/client";
import type { ForecastInfo, ForecastMetric, ForecastSample, Target } from "../api/types";
import { TARGETS } from "../api/types";
import { useAsync } from "../hooks/useApi";
import { Card, DataTable, ErrorBanner, LoadingState, EmptyState, StatusPill } from "../components/common";
import { Chart, registerables } from "chart.js";
Chart.register(...registerables);

function MetricsTable({ target }: { target: Target }): ReactNode {
  const m = useAsync<ForecastMetric | null>(() => api.getForecastMetrics(target), [target]);
  if (m.loading) return <LoadingState label="Loading metrics…" rows={2} />;
  if (m.error) return <ErrorBanner error={m.error} />;
  if (!m.data) return <EmptyState title="No metrics" />;
  const row = m.data;
  return (
    <DataTable
      rows={[row]}
      keyFn={(r) => `${r.target}-${r.model}`}
      columns={[
        { key: "mae", label: "MAE", render: (r) => r.mae.toFixed(3), align: "right" },
        { key: "rmse", label: "RMSE", render: (r) => r.rmse.toFixed(3), align: "right" },
        { key: "smape", label: "sMAPE", render: (r) => r.smape.toFixed(3), align: "right" },
        { key: "nmae", label: "nMAE", render: (r) => r.nmae.toFixed(4), align: "right" },
        { key: "nrmse", label: "nRMSE", render: (r) => r.nrmse.toFixed(4), align: "right" },
      ]}
    />
  );
}

function PredictionsChart({ target }: { target: Target }): ReactNode {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const p = useAsync<ForecastSample[]>(() => api.getForecastPredictions(target, 1464), [target]);
  useEffect(() => {
    if (!p.data || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx2d = canvas.getContext("2d");
    if (!ctx2d) return;
    const ctx = ctx2d;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const w = canvas.width, h = canvas.height;
    const padL = 50, padR = 20, padT = 14, padB = 28;
    const xs = p.data.map((d) => new Date(d.timestamp).getTime());
    const ys = p.data.flatMap((d) => [d.prediction, d.actual]);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const sx = (x: number) => padL + (w - padL - padR) * (x - minX) / (maxX - minX || 1);
    const sy = (y: number) => padT + (h - padT - padB) * (1 - (y - minY) / (maxY - minY || 1));
    ctx.strokeStyle = "#444"; ctx.lineWidth = 1; ctx.beginPath();
    for (let i = 0; i <= 4; i++) {
      const y = padT + (h - padT - padB) * (i / 4);
      ctx.moveTo(padL, y); ctx.lineTo(w - padR, y);
      const v = maxY - (maxY - minY) * (i / 4);
      ctx.fillStyle = "#888"; ctx.font = "10px sans-serif"; ctx.fillText(v.toFixed(0), 4, y + 3);
    }
    ctx.stroke();
    function line(values: Array<(_: ForecastSample, i: number) => number>, color: string) {
      ctx.strokeStyle = color; ctx.lineWidth = 1.4; ctx.beginPath();
      p.data!.forEach((d, i) => {
        const x = sx(xs[i]); const y = sy(values[0](d, i));
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }
    line([(d) => d.actual], "#9aa6b2");
    line([(d) => d.prediction], "#38BDF8");
    ctx.fillStyle = "#bbb"; ctx.font = "10px sans-serif";
    ctx.fillText(p.data[0]?.timestamp ?? "", padL, h - 8);
    ctx.fillText(p.data[p.data.length - 1]?.timestamp ?? "", w - padR - 110, h - 8);
  }, [p.data]);
  if (p.loading) return <LoadingState label="Loading predictions…" rows={1} />;
  if (p.error) return <ErrorBanner error={p.error} />;
  if (!p.data || p.data.length === 0) return <EmptyState title="No predictions" />;
  return (
    <div className="chart">
      <canvas ref={canvasRef} width={1100} height={260} role="img"
              aria-label={`Actual vs prediction chart for ${target} (1464 hourly points)`} />
      <div className="chart__legend">
        <span><span className="swatch swatch--muted" /> Actual</span>
        <span><span className="swatch swatch--accent" /> Frozen-model prediction</span>
      </div>
    </div>
  );
}
export function Forecasts(): ReactNode {
  const [target, setTarget] = useState<Target>("load");
  const list = useAsync<ForecastInfo[]>(() => api.listForecasts(), []);
  return (
    <div className="page">
      <header className="page__head">
        <h1 className="page__title">Forecasts</h1>
        <p className="page__lede">
          Per-target forecast performance on the locked test partition
          (November–December 2020, 1,464 hourly rows per target). Historical
          data — not live inference.
        </p>
        <StatusPill tone="info">OFFLINE EVALUATION · LOCKED TEST PARTITION</StatusPill>
      </header>

      <div className="target-tabs" role="tablist" aria-label="Targets">
        {TARGETS.map((t) => (
          <button key={t} role="tab" aria-selected={t === target} className={`target-tab ${t === target ? "target-tab--active" : ""}`} onClick={() => setTarget(t)}>
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      {list.error ? <ErrorBanner error={list.error} /> : null}

      <Card title={`${target.toUpperCase()} — Forecast identity`}
            subtitle={Array.isArray(list.data) && list.data.length > 0
                       ? (list.data.find((r) => r.target === target)?.model ?? "—")
                       : "—"}
            aside={<StatusPill tone="info">read-only</StatusPill>}>
        {list.loading ? <LoadingState label="Loading forecast info…" rows={1} /> :
          Array.isArray(list.data) && list.data.length > 0 ? (() => {
            const r = list.data.find((x) => x.target === target);
            if (!r) return <EmptyState title="No forecast info" />;
            return (
              <DataTable
                rows={[r]}
                keyFn={(x) => x.target}
                columns={[
                  { key: "horizon", label: "Horizon", render: (x) => `${x.horizon} h` },
                  { key: "n_samples", label: "Final-test rows", render: (x) => x.n_samples },
                  { key: "framework", label: "Framework", render: (x) => <code>{x.framework}</code> },
                  { key: "feature_set", label: "Features", render: (x) => x.feature_set },
                  { key: "fcount", label: "Feature count", render: (x) => x.feature_count, align: "right" },
                  { key: "status", label: "Status", render: (x) => x.final_test_status },
                ]}
              />
            );
          })() : <EmptyState title="No forecasts" />}
      </Card>

      <Card title={`${target.toUpperCase()} — 5-metric result`}
            subtitle="MAE / RMSE / sMAPE / nMAE / nRMSE on the locked final test">
        <MetricsTable target={target} />
      </Card>

      <Card title={`${target.toUpperCase()} — Actual vs Prediction`}
            subtitle="1,464 hourly points on the locked final test window (Nov-Dec 2020)">
        <PredictionsChart target={target} />
      </Card>
    </div>
  );
}
