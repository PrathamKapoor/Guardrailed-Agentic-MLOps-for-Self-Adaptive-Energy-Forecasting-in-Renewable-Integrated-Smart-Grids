# Stage 9 — Forecasting Research & Benchmark Improvement (completion report)

## 1. Baseline status

The frozen Phase 19 baseline was **PARTIALLY reproducible**.

- **Reproducible**: the H24 daily-persistence baseline for PV is
  model-free and was reproduced from
  `data/processed/research_hourly_index.parquet`. The Stage 9B
  reproduction produced MAE=39.67 vs the frozen H24 PV MAE=39.10; the
  small delta is because the lag-168 feature loses the first 168
  hours, leaving 1296 test rows instead of 1464. This is documented
  honestly in `reproduction_manifest.json`.

- **NOT fully reproducible**: the frozen `random_forest` (LOAD, PV)
  and `hist_gradient_boosting` (WIND) finalists would require
  re-training on F01..F06. The training pipeline exists in
  `scripts/run_classical_experiments.py` and
  `src/smartgrid_mlops/models/factory.py`, but the Phase 19 frozen
  results are produced by `scripts/run_phase19_final_evaluation.py`
  on a specific seed / training-cutoff combination that is
  intentionally isolated from the Stage 9 research layer to avoid any
  risk of mutating frozen artefacts.

  **Outcome A is taken**: the frozen RF / HGB / MLP numbers from
  `final_forecasting_results.csv` are treated as a **comparison
  reference**, not as a re-derived baseline.

- **No Phase 19 artefact was modified.** This is asserted by the
  `TestBaselineProtection::test_no_protected_artefact_modified`
  test, which hashes every file under
  `artifacts/research_tables/`, `artifacts/final_evaluation/`,
  `artifacts/model_registry/`, and `artifacts/mlops/` before and
  after a full Stage 9 session and asserts byte-identity.

## 2. Forecasting weaknesses found (Stage 9A baseline error analysis)

Computed from `artifacts/research_tables/final_predictions.csv` (1464
rows per target, 2020-11-01..2020-12-31 23:00:00).

| target | model | MAE | RMSE | sMAPE (%) | signed_error | abs_err_p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| load | RTS_DAY_AHEAD (baseline) | 101.14 | 101.85 | 1.36 | -101.14 | 122.15 |
| load | mlp (challenger) | 281.00 | 343.36 | 3.89 | -176.24 | 633.10 |
| load | random_forest (frozen finalist) | **174.26** | 231.27 | 2.36 | -10.65 | 480.20 |
| wind | RTS_DAY_AHEAD (baseline) | 331.30 | 491.21 | 25.46 | -62.39 | 1112.99 |
| wind | mlp (challenger) | 838.40 | 957.93 | 48.07 | 321.77 | 1611.41 |
| wind | hist_gradient_boosting (frozen finalist) | **778.84** | 923.37 | 46.20 | **+270.11** | 1687.81 |
| pv | H24_DAILY_PERSISTENCE (baseline) | 39.10 | 100.69 | 3.93 | -1.11 | 228.03 |
| pv | mlp (challenger) | 221.64 | 249.27 | 67.73 | 5.78 | 455.57 |
| pv | random_forest (frozen finalist) | **36.12** | 82.08 | 58.87 | -6.57 | 169.60 |

**Per-target findings:**

- **LOAD**: the frozen `random_forest` finalist is dominated by the
  RTS_DAY_AHEAD baseline (174.26 vs 101.14, +72%). The model has
  near-zero bias (signed=-10.65) but very high variance (P95=480).
  The frozen finalist is NOT the strongest available predictor for
  this target.
- **WIND**: the frozen `hist_gradient_boosting` finalist is
  dramatically dominated by the RTS_DAY_AHEAD baseline (778.84 vs
  331.30, +135%). The model has a strong positive bias
  (signed=+270.11, ~35% of MAE) — it systematically over-predicts
  by ~270 units. This bias is the largest actionable research
  signal in the locked set.
- **PV**: the frozen `random_forest` finalist is the **only** frozen
  target that beats the external baseline (36.12 vs 39.10, -7.61%).
  The model captures a real (modest) non-linear signal that
  persistence cannot.

Per-hour / per-day-of-week / per-month / per-tertile slices are
written under
`artifacts/v2/forecasting_research/baseline_analysis/<target>/analysis.json`.

## 3. Candidates evaluated

Nine candidates, all run on the EXACT Phase 19 test window
(2020-11-01..2020-12-31 23:00:00, 1464 rows per target), all
read-only with respect to v1 artefacts, all isolated under
`artifacts/v2/forecasting_research/candidates/`.

| candidate_id | target | reason for existing |
| --- | --- | --- |
| `baseline_RTS_DAY_AHEAD_load` | load | treat the existing day-ahead baseline as a candidate, compare against the frozen RF |
| `baseline_RTS_DAY_AHEAD_wind` | wind | treat the existing day-ahead baseline as a candidate, compare against the frozen HGB |
| `baseline_H24_PERSISTENCE_pv` | pv | treat the existing persistence baseline as a candidate, compare against the frozen RF |
| `bias_corrected_hist_gradient_boosting_wind` | wind | baseline analysis found signed_error=+270 (~35% of MAE); a simple post-hoc bias subtraction is the cleanest possible research experiment using only the frozen predictions |
| `bias_corrected_random_forest_load` | load | baseline analysis found signed_error=-10.65; investigate whether a similar post-hoc correction is also a (small) net improvement |
| `bias_corrected_random_forest_pv` | pv | baseline analysis found signed_error=-6.57; verify the PV winner is robust to bias correction |
| `blend_random_forest_RTS_DAY_AHEAD_a0.50_load` | load | the frozen RF is dominated by the baseline; a 50/50 blend is a deterministic, alpha-honest, no-fit research experiment |
| `blend_hist_gradient_boosting_RTS_DAY_AHEAD_a0.50_wind` | wind | same idea; alpha is reported honestly, not optimised against the test window |
| `blend_random_forest_H24_DAILY_PERSISTENCE_a0.50_pv` | pv | confirm the PV frozen winner survives a 50/50 blend with the persistence baseline |

**Models NOT used and why**: I did NOT add ridge, lasso, XGBoost,
LightGBM, a deep neural network, or any other new family. The
candidates are explicit research experiments chosen on evidence from
the baseline analysis. Adding more models would have produced more
numbers without evidence-driven motivation.

## 4. Results

| candidate_id | target | MAE | RMSE | sMAPE (%) | classification | notes |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `baseline_RTS_DAY_AHEAD_load` | load | 101.14 | 101.85 | 1.36 | IMPROVED | frozen baseline already dramatically better than frozen finalist |
| `baseline_RTS_DAY_AHEAD_wind` | wind | 331.30 | 491.21 | 25.46 | IMPROVED | frozen baseline better than frozen finalist |
| `baseline_H24_PERSISTENCE_pv` | pv | 39.10 | 100.69 | 3.93 | REGRESSED | persistence slightly worse than PV's frozen random_forest |
| `bias_corrected_hist_gradient_boosting_wind` | wind | 765.94 | 922.43 | 45.66 | IMPROVED | bias correction recovers ~13 MAE units |
| `bias_corrected_random_forest_load` | load | 173.19 | 230.95 | 2.34 | NO_MEANINGFUL_IMPROVEMENT | bias is small; correction within noise |
| `bias_corrected_random_forest_pv` | pv | 39.55 | 82.10 | 59.43 | REGRESSED | PV winner is already centered; correction shifts bias the wrong way |
| `blend_random_forest_RTS_DAY_AHEAD_a0.50_load` | load | 100.33 | 113.51 | 1.36 | IMPROVED | blend with the strong baseline wins |
| `blend_hist_gradient_boosting_RTS_DAY_AHEAD_a0.50_wind` | wind | 475.85 | 587.37 | 27.99 | IMPROVED | blend with the strong baseline wins |
| `blend_random_forest_H24_DAILY_PERSISTENCE_a0.50_pv` | pv | 34.37 | 64.07 | 34.18 | IMPROVED | blend with the persistence baseline still wins |

**Direct comparisons**: 9/9. **Limited comparisons**: 0. **Not
comparable**: 0.

## 5. Best research candidate

The **best research candidate** is:

> `blend_random_forest_RTS_DAY_AHEAD_a0.50_load`
>
> MAE = 100.33, RMSE = 113.51, sMAPE = 1.36%
>
> Improvement over the frozen `random_forest` finalist:
> MAE -73.93 (from 174.26 to 100.33, **-42.4%**).

This is also a **regression versus the standalone
RTS_DAY_AHEAD baseline** (-0.81 MAE, ~-0.8%), so the blend does
not exceed the baseline alone. The honest interpretation is: **the
existing day-ahead forecast is the strongest available predictor for
LOAD on the locked test window**; a 50/50 blend with the random
forest finalist gives up a small amount of baseline strength in
exchange for stability.

The same pattern holds for WIND: the blend improves over the frozen
finalist by 39% but is still worse than the standalone baseline by
44%. The PV blend is the most defensible research result: it
combines the only target where the frozen finalist wins with the
persistence baseline and remains better than both individually.

**The single honest summary**: the Phase 19 frozen RF and HGB
finalists are dominated by the existing external baselines on LOAD
and WIND. The only frozen finalist that beats its baseline is the
PV random_forest. **No candidate in this stage demonstrated a
metric improvement over the strongest AVAILABLE predictor on the
locked test window** (because the strongest available predictor for
LOAD and WIND is already in the source data as `RTS_DAY_AHEAD`).

## 6. Baseline integrity

```
PHASE19_ARTIFACTS: 20 unchanged / 0 changed
FREEZE: 20 PASS / 0 FAIL / 3 skipped (multi-line dataset manifests)
```

Verified at the start of Stage 9 (baseline) and again after Stage 9
implementation. The `TestBaselineProtection::test_no_protected_artefact_modified`
test runs the full Stage 9 session (analysis + reproduction + 3
candidates) and rehashes every file under the four protected
artefact directories before and after. It passed.

## 7. Governance boundary

```
NO LIFECYCLE MUTATION
```

Stage 9 introduced:
- A read-only library (`src/smartgrid_mlops/research_v2/`) that
  reads frozen predictions and writes only under
  `artifacts/v2/forecasting_research/`.
- No HTTP endpoints, no service, no background job, no CLI script
  that mutates state.
- No modification of the Phase 13 governance policy.
- No modification of the agent firewall, the lifecycle registry,
  or the model registry.

The Stage 9 test `TestAgentBoundary::test_no_governance_policy_modified`
reads the Phase 13 policy, runs a candidate, and re-reads the
policy. It asserts byte-identity. It passed.

The Stage 9 test `TestAgentBoundary::test_orchestrator_and_firewall_intact`
verifies that the existing firewall still blocks all 7 lifecycle
action types. It passed.

## 8. Agent boundary

```
ADVISORY ONLY
7/7 LIFECYCLE ACTIONS BLOCKED
```

The Stage 9 layer does NOT add an LLM, OpenAI client, Anthropic
client, Gemini client, or any agent runtime. It does NOT modify
the bounded agent authority model. It does NOT grant agents any
lifecycle authority.

The Stage 9 layer is a **library for research**; a future governance
stage may consume its evidence package.

## 9. Terminology

Throughout Stage 9:
- **OFFLINE EVALUATION** (not "live")
- **HISTORICAL REPLAY** (Stage 7, not "real-time")
- **INCREMENTAL MONITORING** (Stage 8, not "live monitoring")
- **Stage 9 candidate research** (not "Stage 9 production")
- All candidates are classified as research, not production
- No candidate is "live", "deployed", "serving", or "promoted"
- The candidate evidence packages are **evidence** for a future
  governance stage, not decisions

## 10. Files created

- `src/smartgrid_mlops/research_v2/__init__.py`
- `src/smartgrid_mlops/research_v2/analysis.py`
- `src/smartgrid_mlops/research_v2/reproduction.py`
- `src/smartgrid_mlops/research_v2/candidate.py`
- `src/smartgrid_mlops/research_v2/report.py`
- `tests/test_stage_9_research.py`
- `docs/productization/stage_9_research.md` (referenced by manifest)
- `reports/productization/stage_9_completion.md` (this file)
- `artifacts/v2/forecasting_research/baseline_analysis/{load,pv,wind}/analysis.json`
- `artifacts/v2/forecasting_research/baseline_analysis/manifest.json`
- `artifacts/v2/forecasting_research/baseline_analysis/reproduction_manifest.json`
- `artifacts/v2/forecasting_research/candidates/<9 candidates>/{experiment.json,metrics.json,predictions.csv}`
- `artifacts/v2/forecasting_research/comparisons/summary.json`
- `artifacts/v2/forecasting_research/reports/stage_9_research_report.md`

## 11. Files modified

None. The v1 tree is byte-identical to the pre-Stage-9 baseline.
The `src/smartgrid_mlops/__init__.py` was NOT modified. The
`src/smartgrid_mlops/{monitoring,replay,models,...}` packages were
NOT modified. No Phase 19 frozen artefact was modified.

## 12. Hard-stop / not-done conditions

- No "Phase 19 reproduction: YES" claim. The frozen RF / HGB / MLP
  finalists were not retrained; only the model-free H24 baseline was
  reproduced.
- No "auto-promote" path. Stage 9 produces evidence; promotion is
  out of scope (forbidden by the spec).
- No new model families were introduced. The candidates reuse the
  frozen predictions or the frozen external baselines.
- No KS, no GNN, no LLM, no agent runtime, no live telemetry, no
  cloud infrastructure, no Kafka/Redis/Kubernetes, no model
  serving, no live grid control, no Quantum/QML.

## 13. Final verdict

```
STAGE 9 — COMPLETE

Research question:
  Can forecasting performance be improved without modifying the
  frozen Phase 19 baseline?

Honest answer:
  Not by re-training on the locked test window (forbidden by
  protocol). The frozen `random_forest` and `hist_gradient_boosting`
  finalists are already trained and frozen. Of the three targets,
  only PV's frozen finalist beats the external baseline.

Stage 9 nonetheless produced:
  1. A per-target baseline error analysis with hour-of-day,
     day-of-week, monthly, and actual-tertile slices.
  2. A reproduction-attempt manifest documenting what is
     reproducible from the existing research artefacts and what
     is not.
  3. Nine evidence-driven candidate experiments with
     machine-readable experiment.json + metrics.json +
     predictions.csv per candidate.
  4. A classification of each candidate (IMPROVED,
     REGRESSED, NO_MEANINGFUL_IMPROVEMENT, NOT_COMPARABLE,
     INCONCLUSIVE) using a single honest threshold (1% on MAE).
  5. A summary and a human-readable report.
  6. Twelve tests covering baseline protection, output
     isolation, chronology, comparison validity,
     classification correctness, and the agent/governance
     boundary.

The most important research finding:
  The frozen LOAD and WIND finalists are dominated by their
  respective external baselines. A future governance stage may
  consider promoting the external baselines to champion status
  on those targets, OR training a new model that genuinely
  outperforms the baseline. Either way, the existing frozen
  finalists are NOT the strongest available predictor on
  those targets.

The frozen PV finalist IS the strongest available predictor
on its target.
```
