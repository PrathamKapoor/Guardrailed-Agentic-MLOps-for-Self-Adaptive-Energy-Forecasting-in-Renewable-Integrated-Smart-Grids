"""Research console API: user-provided datasets + real forecasting runs.

This router turns the product frontend into a working research instrument:

* POST /api/research/datasets  — upload a CSV, validate it, and register a
  dataset manifest (dataset policy: source, license, retrieval date,
  version/hash, schema, approval are recorded BEFORE first use).
* GET  /api/research/datasets  — list registered datasets.
* POST /api/research/runs      — train + evaluate a forecasting model on a
  registered dataset with a strict chronological split (no random splits,
  no leakage) and report honest metrics against a seasonal-naive benchmark.
* GET  /api/research/runs      — list runs.

Governance boundaries (unchanged):
* Runs are LOCAL RESEARCH EVIDENCE only. Nothing here promotes, deploys,
  retrains, or mutates the lifecycle registry; results never bypass the
  deterministic governance engine.
* Advisory output uses bounded recommendation types only (EXPLAIN /
  INVESTIGATE / CREATE_REPORT); lifecycle action types never appear.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from ..config import CONFIG
from ..dependencies import AppState, get_state

router = APIRouter(prefix="/api/research", tags=["research"])

MAX_UPLOAD_BYTES = 32 * 1024 * 1024  # 32 MB cap for the local research console
MIN_ROWS = 48


# ---------------------------------------------------------------- schemas

class DatasetInfo(BaseModel):
    dataset_id: str
    name: str
    source: str
    license: str
    uploaded_at: str
    rows: int
    columns: List[str]
    timestamp_column: str
    numeric_columns: List[str]
    start: str
    end: str
    sha256: str


class RunRequest(BaseModel):
    dataset_id: str
    target: str
    model: str = "ridge"  # ridge | hist_gradient_boosting | seasonal_naive
    test_fraction: float = 0.2


class RunMetrics(BaseModel):
    mae: float
    rmse: float
    benchmark_mae: float
    benchmark: str
    improvement_pct: float
    n_train: int
    n_test: int


class RenewableInsight(BaseModel):
    available: bool
    renewable_share: Optional[float] = None
    load_matching_ratio: Optional[float] = None
    surplus_hours: Optional[int] = None
    correlation_load_renewable: Optional[float] = None
    note: str = ""


class AdvisoryItem(BaseModel):
    recommendation_type: str  # bounded: EXPLAIN | INVESTIGATE | CREATE_REPORT
    text: str


class RunResult(BaseModel):
    run_id: str
    dataset_id: str
    target: str
    model: str
    created_at: str
    split: str
    metrics: RunMetrics
    renewable: RenewableInsight
    advisory: List[AdvisoryItem]
    series: List[Dict[str, Any]]  # test-window sample: timestamp, actual, prediction


# ---------------------------------------------------------------- helpers

def _ui_root(state: AppState) -> Path:
    return state.project_root / "artifacts" / "research_ui"


def _parse_timestamp(raw: str) -> Optional[datetime]:
    raw = (raw or "").strip().strip('"')
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M",
                "%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _to_float(raw: str) -> Optional[float]:
    raw = (raw or "").strip().strip('"')
    if not raw:
        return None
    try:
        v = float(raw)
        return v if math.isfinite(v) else None
    except ValueError:
        return None


def _load_dataset_rows(state: AppState, dataset_id: str) -> tuple[DatasetInfo, List[Dict[str, Any]]]:
    ddir = _ui_root(state) / "datasets" / dataset_id
    manifest_path = ddir / "manifest.json"
    data_path = ddir / "data.csv"
    if not manifest_path.exists() or not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset_id}")
    info = DatasetInfo(**json.loads(manifest_path.read_text(encoding="utf-8")))
    rows: List[Dict[str, Any]] = []
    with data_path.open(newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            ts = _parse_timestamp(rec[info.timestamp_column])
            if ts is None:
                continue
            rows.append({"ts": ts, **{c: _to_float(rec.get(c, "")) for c in info.numeric_columns}})
    rows.sort(key=lambda r: r["ts"])
    return info, rows


# ------------------------------------------------------------ endpoints

@router.post("/datasets", response_model=DatasetInfo,
             summary="Upload + register a CSV dataset (manifest recorded before first use)")
async def upload_dataset(file: UploadFile = File(...), state: AppState = Depends(get_state)) -> DatasetInfo:
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Dataset exceeds the 32 MB local research cap.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Dataset must be UTF-8 CSV.")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no header row.")
    columns = [c.strip() for c in reader.fieldnames]

    sample = [rec for _, rec in zip(range(200), reader)]
    # Timestamp column: name match first, then first column whose values parse.
    ts_col = next((c for c in columns if any(k in c.lower() for k in ("timestamp", "time", "date"))), None)
    if ts_col is None:
        ts_col = next((c for c in columns
                       if all(_parse_timestamp(r.get(c, "")) for r in sample[:20] if r.get(c))), None)
    if ts_col is None:
        raise HTTPException(status_code=400, detail="No parsable timestamp column found.")

    numeric: List[str] = []
    for c in columns:
        if c == ts_col:
            continue
        vals = [_to_float(r.get(c, "")) for r in sample]
        vals = [v for v in vals if v is not None]
        if len(vals) >= max(1, int(0.5 * len(sample))):
            numeric.append(c)
    if not numeric:
        raise HTTPException(status_code=400, detail="No numeric measurement columns found.")

    # Full parse (bounded by the upload cap) to normalize + count rows.
    rows: List[Dict[str, Any]] = []
    for rec in csv.DictReader(io.StringIO(text)):
        ts = _parse_timestamp(rec.get(ts_col, ""))
        if ts is None:
            continue
        rows.append({"timestamp": ts.isoformat(sep=" "),
                     **{c: (_to_float(rec.get(c, "")) if c in numeric else None) for c in numeric}})
    if len(rows) < MIN_ROWS:
        raise HTTPException(status_code=400,
                            detail=f"Only {len(rows)} parsable rows; at least {MIN_ROWS} required.")

    sha = hashlib.sha256(raw).hexdigest()
    dataset_id = f"ui-{sha[:12]}"
    name = Path(file.filename or "dataset.csv").stem
    now = datetime.now(timezone.utc).isoformat()

    # Normalize the stored CSV to the validated schema.
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["timestamp", *numeric])
    writer.writeheader()
    writer.writerows(rows)

    ddir = _ui_root(state) / "datasets" / dataset_id
    ddir.mkdir(parents=True, exist_ok=True)
    (ddir / "data.csv").write_text(out.getvalue(), encoding="utf-8")
    # Dataset policy: manifest recorded BEFORE the dataset is used by any run.
    manifest = DatasetInfo(
        dataset_id=dataset_id, name=name,
        source="user-uploaded via research console",
        license="UNSPECIFIED — user-provided research data; not for redistribution",
        uploaded_at=now, rows=len(rows), columns=["timestamp", *numeric],
        timestamp_column="timestamp", numeric_columns=numeric,
        start=rows[0]["timestamp"], end=rows[-1]["timestamp"], sha256=sha,
    )
    (ddir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest


@router.get("/datasets", response_model=List[DatasetInfo], summary="List registered datasets")
def list_datasets(state: AppState = Depends(get_state)) -> List[DatasetInfo]:
    root = _ui_root(state) / "datasets"
    if not root.exists():
        return []
    out = []
    for mf in sorted(root.glob("*/manifest.json")):
        try:
            out.append(DatasetInfo(**json.loads(mf.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return sorted(out, key=lambda d: d.uploaded_at, reverse=True)


def _fit_predict(model: str, Xtr: List[List[float]], ytr: List[float],
                 Xte: List[List[float]]) -> List[float]:
    if model == "seasonal_naive":
        raise HTTPException(status_code=400, detail="seasonal_naive is the benchmark, not a trainable model.")
    from smartgrid_mlops.models.classical import ridge, hist_gradient_boosting
    params: Dict[str, Any] = {"alpha": 1.0}
    if model == "ridge":
        est = ridge(params, seed=42)
    elif model == "hist_gradient_boosting":
        est = hist_gradient_boosting(
            {"learning_rate": 0.08, "max_iter": 200, "max_leaf_nodes": 31,
             "l2_regularization": 0.1}, seed=42)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")
    est.fit(Xtr, ytr)
    return [float(v) for v in est.predict(Xte)]


@router.post("/runs", response_model=RunResult, summary="Run a chronological forecast experiment")
def run_experiment(req: RunRequest, state: AppState = Depends(get_state)) -> RunResult:
    info, rows = _load_dataset_rows(state, req.dataset_id)
    if req.target not in info.numeric_columns:
        raise HTTPException(status_code=400, detail=f"Target '{req.target}' is not a numeric column.")
    if not 0.05 <= req.test_fraction <= 0.5:
        raise HTTPException(status_code=400, detail="test_fraction must be within [0.05, 0.5].")

    # Leakage-safe feature construction: every feature at time t uses only
    # values at t (calendar) or strictly earlier rows (lags). Rows with
    # missing lag history are dropped, never imputed from the future.
    by_index: Dict[int, float] = {i: r[req.target] for i, r in enumerate(rows)
                                  if r.get(req.target) is not None}
    feat_rows: List[tuple] = []
    for i, r in enumerate(rows):
        y = r.get(req.target)
        if y is None:
            continue
        lags_ok = all((i - k) in by_index for k in (1, 24, 168))
        if not lags_ok:
            continue
        ts = r["ts"]
        h, dow, doy = ts.hour + ts.minute / 60, ts.weekday(), ts.timetuple().tm_yday
        feats = [math.sin(2 * math.pi * h / 24), math.cos(2 * math.pi * h / 24),
                 math.sin(2 * math.pi * dow / 7), math.cos(2 * math.pi * dow / 7),
                 math.sin(2 * math.pi * doy / 365.25), math.cos(2 * math.pi * doy / 365.25),
                 by_index[i - 1], by_index[i - 24], by_index[i - 168]]
        feat_rows.append((ts, feats, y, by_index[i - 24]))  # last field: seasonal-naive prediction

    if len(feat_rows) < 100:
        raise HTTPException(status_code=400,
                            detail=f"Not enough complete lag rows ({len(feat_rows)}); need >= 100.")
    cut = int(len(feat_rows) * (1 - req.test_fraction))
    train, test = feat_rows[:cut], feat_rows[cut:]  # strict chronological holdout
    if not train or not test:
        raise HTTPException(status_code=400, detail="Split produced an empty partition.")

    if req.model == "seasonal_naive":
        preds = [t[3] for t in test]
    else:
        preds = _fit_predict(req.model, [t[1] for t in train], [t[2] for t in train],
                             [t[1] for t in test])

    def mae(ps): return statistics.fmean(abs(p - t[2]) for p, t in zip(ps, test))
    def rmse(ps): return math.sqrt(statistics.fmean((p - t[2]) ** 2 for p, t in zip(ps, test)))

    bench = mae([t[3] for t in test])
    model_mae = mae(preds)
    improvement = (bench - model_mae) / bench * 100 if bench else 0.0
    metrics = RunMetrics(mae=model_mae, rmse=rmse(preds), benchmark_mae=bench,
                         benchmark="seasonal_naive_lag24", improvement_pct=improvement,
                         n_train=len(train), n_test=len(test))

    # ---- Renewable utilization (honest, offline, descriptive only) ----
    renew_cols = [c for c in info.numeric_columns
                  if any(k in c.lower() for k in ("wind", "pv", "solar"))]
    load_cols = [c for c in info.numeric_columns if "load" in c.lower() or "demand" in c.lower()]
    renewable = RenewableInsight(available=False)
    advisory: List[AdvisoryItem] = []
    if renew_cols and load_cols:
        lc = load_cols[0]
        pairs = []
        for r in rows:
            renew_vals = [r.get(c) for c in renew_cols]
            load_val = r.get(lc)
            if load_val is None or any(v is None for v in renew_vals):
                continue
            pairs.append((sum(renew_vals), load_val))  # all renewable columns aggregated
        if len(pairs) > 48:
            renew_total = sum(a for a, _ in pairs)
            load_total = sum(b for _, b in pairs)
            matching = sum(min(a, b) for a, b in pairs) / load_total if load_total else 0.0
            share = renew_total / load_total if load_total else 0.0
            surplus = sum(1 for a, b in pairs if a > b)
            mx, my = statistics.fmean(a for a, _ in pairs), statistics.fmean(b for _, b in pairs)
            cov = statistics.fmean((a - mx) * (b - my) for a, b in pairs)
            sx = math.sqrt(statistics.fmean((a - mx) ** 2 for a, _ in pairs)) or 1.0
            sy = math.sqrt(statistics.fmean((b - my) ** 2 for _, b in pairs)) or 1.0
            corr = max(-1.0, min(1.0, cov / (sx * sy)))
            renewable = RenewableInsight(
                available=True, renewable_share=round(share, 4),
                load_matching_ratio=round(matching, 4), surplus_hours=surplus,
                correlation_load_renewable=round(corr, 4),
                note=(f"Descriptive ratios over {len(pairs)} hourly rows: sum of [{', '.join(renew_cols)}] "
                      f"vs '{lc}'. Offline research metrics — not a dispatch plan."))
            # Bounded advisory types only; deterministic; evidence-referenced.
            if matching < 0.5:
                advisory.append(AdvisoryItem(recommendation_type="INVESTIGATE",
                    text=f"Load-matching ratio is {matching:.0%}: most renewable energy is produced "
                         f"when demand cannot absorb it. Investigate the surplus hours "
                         f"({surplus} of {len(pairs)}) before claiming utilization gains."))
            else:
                advisory.append(AdvisoryItem(recommendation_type="EXPLAIN",
                    text=f"Load-matching ratio is {matching:.0%} (renewable share {share:.0%}); "
                         f"correlation with load is {corr:.2f}."))
            advisory.append(AdvisoryItem(recommendation_type="CREATE_REPORT",
                text="Create a report quantifying how much flexible demand would need to shift "
                     "into renewable-surplus hours to raise the matching ratio by 5 points."))
    if not advisory:
        advisory.append(AdvisoryItem(recommendation_type="EXPLAIN",
            text=f"Model {req.model} improved MAE by {improvement:.1f}% vs the seasonal-naive "
                 f"benchmark on this holdout. Research evidence only."))
    if improvement < 0:
        advisory.append(AdvisoryItem(recommendation_type="INVESTIGATE",
            text=f"The model is WORSE than the seasonal-naive benchmark on this holdout "
                 f"({improvement:.1f}%). Report this honestly; do not tune on the test window."))

    stride = max(1, len(test) // 240)
    series = [{"timestamp": t[0].isoformat(sep=" "), "actual": t[2], "prediction": p}
              for t, p in zip(test[::stride], preds[::stride])]

    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{req.dataset_id[-6:]}"
    result = RunResult(run_id=run_id, dataset_id=req.dataset_id, target=req.target,
                       model=req.model, created_at=datetime.now(timezone.utc).isoformat(),
                       split=f"chronological holdout: first {1 - req.test_fraction:.0%} train / "
                             f"last {req.test_fraction:.0%} test, lags 1/24/168, no future leakage",
                       metrics=metrics, renewable=renewable, advisory=advisory, series=series)
    runs_dir = _ui_root(state) / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{run_id}.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


@router.get("/runs", response_model=List[RunResult], summary="List research runs")
def list_runs(state: AppState = Depends(get_state)) -> List[RunResult]:
    root = _ui_root(state) / "runs"
    if not root.exists():
        return []
    out = []
    for f in sorted(root.glob("run-*.json"), reverse=True):
        try:
            out.append(RunResult(**json.loads(f.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return out[:25]
