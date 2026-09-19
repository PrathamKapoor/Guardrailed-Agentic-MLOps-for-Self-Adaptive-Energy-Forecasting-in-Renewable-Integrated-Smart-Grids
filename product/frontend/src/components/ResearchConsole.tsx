/** Live research console: add a dataset, run a chronological forecasting
 *  experiment, inspect honest metrics, renewable-utilization ratios, and the
 *  bounded agent's advisory (recommendation only; governance is untouched).
 *
 *  All computation happens in the local backend over the uploaded CSV.
 *  Results are research evidence only — they never mutate the lifecycle
 *  registry and never bypass the deterministic governance engine.
 */
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api, APIRequestError } from "../api/client";
import type { ResearchDataset, ResearchRunResult } from "../api/types";
import { Card, ErrorBanner, LoadingState, StatusPill } from "./common";

function asMessage(err: unknown): string {
  if (err instanceof APIRequestError) return err.detail;
  return String((err as Error)?.message ?? err);
}

function RunChart({ run }: { run: ResearchRunResult }): ReactNode {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || run.series.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = canvas.clientWidth * 2;
    canvas.height = 260;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const w = canvas.width, h = canvas.height;
    const padL = 56, padR = 16, padT = 12, padB = 26;
    const ys = run.series.flatMap((d) => [d.actual, d.prediction]);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const sx = (i: number) => padL + (w - padL - padR) * (i / (run.series.length - 1 || 1));
    const sy = (y: number) => padT + (h - padT - padB) * (1 - (y - minY) / (maxY - minY || 1));
    ctx.strokeStyle = "#c9beac"; ctx.lineWidth = 1; ctx.beginPath();
    for (let i = 0; i <= 4; i++) {
      const y = padT + (h - padT - padB) * (i / 4);
      ctx.moveTo(padL, y); ctx.lineTo(w - padR, y);
      ctx.fillStyle = "#8a7f6d"; ctx.font = "18px monospace";
      ctx.fillText((maxY - (maxY - minY) * (i / 4)).toFixed(1), 4, y + 6);
    }
    ctx.stroke();
    const line = (get: (d: typeof run.series[number]) => number, color: string, width: number) => {
      ctx.strokeStyle = color; ctx.lineWidth = width; ctx.beginPath();
      run.series.forEach((d, i) => {
        const x = sx(i), y = sy(get(d));
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
    };
    line((d) => d.actual, "#8a7f6d", 2.5);
    line((d) => d.prediction, "#b3542e", 2.5);
    ctx.fillStyle = "#8a7f6d"; ctx.font = "18px monospace";
    ctx.fillText(run.series[0]?.timestamp ?? "", padL, h - 6);
    const last = run.series[run.series.length - 1]?.timestamp ?? "";
    ctx.fillText(last, w - padR - ctx.measureText(last).width, h - 6);
  }, [run]);
  return (
    <div className="chart">
      <canvas ref={canvasRef} style={{ width: "100%", height: 130 }} aria-label="Actual vs predicted on the test window" />
      <div className="chart__legend">
        <span><span className="swatch swatch--muted" />actual (test window)</span>
        <span><span className="swatch swatch--accent" />prediction</span>
      </div>
    </div>
  );
}

export function ResearchConsole(): ReactNode {
  const [datasetList, setDatasetList] = useState<ResearchDataset[] | null>(null);
  const [dsError, setDsError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);

  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [target, setTarget] = useState<string>("");
  const [model, setModel] = useState<"ridge" | "hist_gradient_boosting" | "seasonal_naive">("ridge");
  const [testFraction, setTestFraction] = useState(0.2);
  const [running, setRunning] = useState(false);
  const [run, setRun] = useState<ResearchRunResult | null>(null);
  const [runError, setRunError] = useState<unknown>(null);

  const refreshDatasets = () => {
    api.listResearchDatasets()
      .then((d) => { setDatasetList(d); setDsError(null); })
      .catch((e) => setDsError(asMessage(e)));
  };
  useEffect(refreshDatasets, []);

  const current = (datasetList ?? []).find((d) => d.dataset_id === selectedDataset);
  useEffect(() => {
    if (current && !current.numeric_columns.includes(target)) setTarget(current.numeric_columns[0] ?? "");
  }, [current, target]);

  const onUpload = async (file: File) => {
    setUploading(true); setUploadMsg(null); setDsError(null);
    try {
      const ds = await api.uploadResearchDataset(file);
      setUploadMsg(`Registered ${ds.dataset_id} — ${ds.rows} rows × ${ds.numeric_columns.length} numeric columns (${ds.start} → ${ds.end}). Manifest recorded.`);
      refreshDatasets();
      setSelectedDataset(ds.dataset_id);
    } catch (e) {
      setDsError(asMessage(e));
    } finally {
      setUploading(false);
    }
  };

  const onRun = async () => {
    if (!selectedDataset || !target) return;
    setRunning(true); setRunError(null); setRun(null);
    try {
      const r = await api.runResearch({ dataset_id: selectedDataset, target, model, test_fraction: testFraction });
      setRun(r);
    } catch (e) {
      setRunError(e);
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card title="Live research console" subtitle="Add a dataset, run a chronological forecasting experiment, inspect honest metrics and renewable-utilization ratios. Local CPU; research evidence only.">
      {/* Step 1 — dataset */}
      <div className="research-step">
        <div className="section-label">Step 1 — Add dataset</div>
        <div className="ask">
          <input
            type="file" accept=".csv,text/csv" aria-label="Dataset CSV file"
            disabled={uploading}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) void onUpload(f); e.target.value = ""; }}
          />
          <button className="btn" type="button" disabled={uploading}>
            {uploading ? "Registering…" : "Upload CSV"}
          </button>
        </div>
        {uploadMsg ? <p className="field-ok">{uploadMsg}</p> : null}
        {dsError ? <ErrorBanner error={dsError} title="DATASET ERROR" /> : null}
        {datasetList === null ? <LoadingState label="Loading datasets…" rows={1} /> :
          datasetList.length === 0 ? <p className="muted">No datasets registered yet. Upload a CSV with a timestamp column and numeric measurements (e.g. load, wind, pv).</p> : (
            <ul className="dataset-list">
              {datasetList.slice(0, 5).map((d) => (
                <li key={d.dataset_id}>
                  <code>{d.dataset_id}</code> <strong>{d.name}</strong> — {d.rows} rows, {d.start} → {d.end}
                  <span className="muted"> ({d.numeric_columns.join(", ")})</span>
                </li>
              ))}
            </ul>
          )}
      </div>

      {/* Step 2 — run */}
      <div className="research-step">
        <div className="section-label">Step 2 — Run MLOps forecast</div>
        <div className="evaluator__row">
          <label>Dataset
            <select value={selectedDataset} onChange={(e) => setSelectedDataset(e.target.value)}>
              <option value="">— select —</option>
              {(datasetList ?? []).map((d) => (
                <option key={d.dataset_id} value={d.dataset_id}>{d.name} ({d.dataset_id})</option>
              ))}
            </select>
          </label>
          <label>Target
            <select value={target} onChange={(e) => setTarget(e.target.value)} disabled={!current}>
              <option value="">— select —</option>
              {(current?.numeric_columns ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <label>Model
            <select value={model} onChange={(e) => setModel(e.target.value as typeof model)}>
              <option value="ridge">Ridge (linear)</option>
              <option value="hist_gradient_boosting">HistGradientBoosting</option>
              <option value="seasonal_naive">Seasonal naive (benchmark)</option>
            </select>
          </label>
          <label>Test fraction
            <input type="number" min={0.05} max={0.5} step={0.05} value={testFraction}
                   onChange={(e) => setTestFraction(Number(e.target.value) || 0.2)} />
          </label>
          <button className="btn" type="button" onClick={() => void onRun()}
                  disabled={!selectedDataset || !target || running}>
            {running ? "Running…" : "Run experiment →"}
          </button>
        </div>
        <p className="muted">Strict chronological holdout: the model trains on the earliest rows and is
          evaluated on the latest rows only. Lag features (1 h / 24 h / 168 h) never read the future.</p>
        {runError ? <ErrorBanner error={runError} title="RUN ERROR" /> : null}
        {running ? <LoadingState label="Training on CPU (this can take ~10–60 s)…" rows={2} /> : null}
      </div>

      {/* Step 3 — results */}
      {run ? (
        <div className="research-step">
          <div className="section-label">Step 3 — Evidence</div>
          <div className="run-head">
            <StatusPill tone={run.metrics.improvement_pct > 0 ? "ok" : "bad"}>
              {run.metrics.improvement_pct > 0 ? "Beats seasonal baseline" : "Worse than seasonal baseline"}
            </StatusPill>
            <span className="muted mono">{run.run_id}</span>
          </div>
          <div className="result-grid-3">
            <div className="target-card">
              <div className="target-card__name">MAE</div>
              <div className="delta-pill">{run.metrics.mae.toFixed(3)}</div>
              <p>vs {run.metrics.benchmark}: {run.metrics.benchmark_mae.toFixed(3)}</p>
            </div>
            <div className="target-card">
              <div className="target-card__name">Improvement</div>
              <div className="delta-pill">{run.metrics.improvement_pct >= 0 ? "+" : ""}{run.metrics.improvement_pct.toFixed(1)}%</div>
              <p>on the final {run.metrics.n_test} rows; trained on {run.metrics.n_train}</p>
            </div>
            <div className="target-card">
              <div className="target-card__name">Renewable matching</div>
              <div className="delta-pill">
                {run.renewable.available ? `${((run.renewable.load_matching_ratio ?? 0) * 100).toFixed(0)}%` : "n/a"}
              </div>
              <p>{run.renewable.available
                ? `renewable share ${((run.renewable.renewable_share ?? 0) * 100).toFixed(0)}% · surplus ${run.renewable.surplus_hours} h`
                : "needs wind/pv/solar + load columns"}</p>
            </div>
          </div>
          <RunChart run={run} />
          <p className="muted">{run.split}</p>
          {run.renewable.available ? <p className="muted">{run.renewable.note}</p> : null}
          <div className="section-label">Bounded agent advisory (recommendation only)</div>
          <ul className="advisory-list">
            {run.advisory.map((a, i) => (
              <li key={i}>
                <StatusPill tone={a.recommendation_type === "INVESTIGATE" ? "warn" : "info"}>{a.recommendation_type}</StatusPill>
                <span>{a.text}</span>
              </li>
            ))}
          </ul>
          <p className="muted">Run artifacts are stored under artifacts/research_ui/runs/. These results are
            local research evidence; they do not register models and never bypass governance.</p>
        </div>
      ) : null}
    </Card>
  );
}
