"""GET /api/forecasts: read the existing frozen forecasting artefacts.

No training, no recomputation. Read-only.
"""
from __future__ import annotations
import csv
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import AppState, get_state
from ..schemas import ForecastInfo, ForecastMetric, ForecastSample

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])

VALID_TARGETS = {"load", "wind", "pv"}


def _forecasts_csv(path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def _comparison_csv(path) -> dict:
    return {r["Target"]: r for r in csv.DictReader(path.open(encoding="utf-8"))}


def _by_target_index(state: AppState) -> dict:
    """One info per target from the productization records."""
    return {r.target: r for r in state.records}


@router.get("", response_model=list[ForecastInfo],
            summary="Per-target forecast info (from the productization records)")
def list_forecasts(state: AppState = Depends(get_state)) -> list[ForecastInfo]:
    out = []
    by_target = _by_target_index(state)
    comparison_path = state.project_root / "artifacts/research_tables/final_model_comparison.csv"
    comparison = _comparison_csv(comparison_path)
    for target, rec in by_target.items():
        comp = comparison[target]
        out.append(ForecastInfo(
            target=target,
            model=rec.model,
            framework=rec.framework,
            feature_set=rec.feature_set,
            feature_count=rec.feature_count,
            horizon=rec.horizon,
            n_samples=1464,
            final_test_mae=rec.final_test_MAE,
            final_test_benchmark_mae=rec.final_test_benchmark_MAE,
            final_test_relative_difference_pct=rec.final_test_relative_difference_pct,
            final_test_status=rec.final_test_status,
            strongest_benchmark=rec.strongest_benchmark,
            development_mae=rec.development_MAE,
        ))
    return out


@router.get("/{target}", response_model=ForecastInfo,
            summary="Forecast info for a single target")
def get_forecast(target: str, state: AppState = Depends(get_state)) -> ForecastInfo:
    if target not in VALID_TARGETS:
        raise HTTPException(status_code=404, detail=f"Unknown target {target!r}; valid: {sorted(VALID_TARGETS)}")
    rec = _by_target_index(state).get(target)
    if rec is None:
        raise HTTPException(status_code=503, detail=f"Forecast for {target} not in productization state.")
    comp = _comparison_csv(state.project_root / "artifacts/research_tables/final_model_comparison.csv")[target]
    return ForecastInfo(
        target=target,
        model=rec.model,
        framework=rec.framework,
        feature_set=rec.feature_set,
        feature_count=rec.feature_count,
        horizon=rec.horizon,
        n_samples=1464,
        final_test_mae=rec.final_test_MAE,
        final_test_benchmark_mae=rec.final_test_benchmark_MAE,
        final_test_relative_difference_pct=rec.final_test_relative_difference_pct,
        final_test_status=rec.final_test_status,
        strongest_benchmark=rec.strongest_benchmark,
        development_mae=rec.development_MAE,
    )


@router.get("/{target}/metrics", response_model=ForecastMetric,
            summary="Per-target 5-metric result (MAE, RMSE, sMAPE, nMAE, nRMSE)")
def get_forecast_metrics(target: str, state: AppState = Depends(get_state)) -> ForecastMetric:
    if target not in VALID_TARGETS:
        raise HTTPException(status_code=404, detail=f"Unknown target {target!r}")
    rows = _forecasts_csv(state.project_root / "artifacts/research_tables/final_forecasting_results.csv")
    rec = _by_target_index(state)[target]
    row = next((r for r in rows if r["Target"] == target and r["Model"] == rec.model), None)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No metrics row for {target}/{rec.model}")
    return ForecastMetric(
        target=target, model=row["Model"], features=row["Features"],
        mae=float(row["MAE"]), rmse=float(row["RMSE"]),
        smape=float(row["sMAPE"]), nmae=float(row["nMAE"]), nrmse=float(row["nRMSE"]),
    )


@router.get("/{target}/predictions", response_model=list[ForecastSample],
            summary="Per-row frozen final-test predictions (frozen reference only; the benchmark rows are not predictions of any model)")
def get_forecast_predictions(target: str, limit: int = 1464,
                            state: AppState = Depends(get_state)) -> list[ForecastSample]:
    if target not in VALID_TARGETS:
        raise HTTPException(status_code=404, detail=f"Unknown target {target!r}")
    if limit < 1 or limit > 1464:
        raise HTTPException(status_code=400, detail="limit must be in [1, 1464]")
    rec = _by_target_index(state)[target]
    rows = list(csv.DictReader(
        (state.project_root / "artifacts/research_tables/final_predictions.csv").open(encoding="utf-8")))
    out = []
    for r in rows:
        if r["target"] != target or r["model"] != rec.model:
            continue
        out.append(ForecastSample(
            timestamp=r["timestamp"], target=r["target"], model=r["model"],
            prediction=float(r["prediction"]), actual=float(r["actual"]),
            absolute_error=float(r["absolute_error"])))
        if len(out) >= limit:
            break
    if not out:
        raise HTTPException(status_code=404, detail=f"No predictions for {target}/{rec.model}")
    return out
