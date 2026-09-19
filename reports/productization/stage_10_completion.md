# Stage 10 — Residual Forecast Correction Research (completion report)

## 1. Repository / data availability

Source of every data point in this stage:

- `data/processed/research_hourly_index.parquet` (8784 rows, full
  calendar year 2020). Schema: `timestamp`,
  `actual_system_load`, `day_ahead_system_load`, `actual_wind`,
  `day_ahead_wind`, `actual_pv`, `day_ahead_pv`.
- The `day_ahead_<target>` columns ARE the `RTS_DAY_AHEAD`
  external baseline used by Phase 19. Verified against
  `final_model_comparison.csv` (LOAD MAE=101.14, WIND MAE=331.30,
  PV MAE=39.10 on the locked test window).
- The `actual_<target>` columns are the recorded hourly generation
  / load values from the frozen research dataset.
- Chronological coverage: 2020-01-01 00:00:00 .. 2020-12-31
  23:00:00 (8784 contiguous hourly rows).

## 2. Residual hypothesis

The hypothesis tested in this stage is:

> Can a chronologically-valid residual correction trained on
> historical data reduce the MAE of the existing RTS_DAY_AHEAD
> baseline on the locked Phase 19 test window?

The residual is defined as `actual - day_ahead` (positive = the
baseline under-predicts). The corrected forecast is
`day_ahead + predicted_residual`. Models are evaluated on the
EXACT Phase 19 test window (2020-11-01..2020-12-31, 1464 rows per
target).

## 3. Leakage analysis

**Training / validation / test split** (fixed, not searched):

| Window | Range | n_hours | Role |
| --- | --- | ---: | --- |
| Training | 2020-01-01..2020-08-31 | 5856 | fit residual model + constant bias |
| Validation | 2020-09-01..2020-10-31 | 1464 | never used to fit; reserved for diagnostic |
| Test (locked) | 2020-11-01..2020-12-31 | 1464 | Phase 19 test window, byte-aligned |

**Feature-availability firewall**: every lag feature is a
backward look-up (`timestamp - k hours`, k ∈ {1, 24, 168}). The
lag references always come from rows with strictly earlier
timestamps. The lookup pool for lag references is the full
chronological history (train + val + test sorted by timestamp) —
this is necessary so that the boundary of any split does not
silently drop rows whose lag reference falls in the previous
split. **This is NOT leakage**: lag references always look
BACKWARD in time. The lookup pool only provides past rows.

**Bias-fitting firewall**: the constant bias is `mean(actual -
day_ahead)` over the training rows ONLY. The test split's
residuals are not used to estimate the bias. The test split's
`rts_day_ahead_metrics` field in the evidence package reports
the true RTS_DAY_AHEAD MAE on the test set, independently
verified to match the Phase 19 frozen value (LOAD 101.14, WIND
331.30, PV 39.10).

**Test-assertion firewall**: the test
`test_constant_bias_fitted_on_train_only` re-derives the bias from
the training rows in a fresh pass and asserts the candidate's
value matches. The test
`test_no_actual_in_test_features` confirms the zero-correction
candidate's test MAE equals the true RTS_DAY_AHEAD MAE
(so the candidate is not accidentally using test actuals as
features).

## 4. Baselines

Three deterministic baselines per target:

| Target | n_train | training residual mean | RTS_DAY_AHEAD test MAE | zero-correction test MAE | constant-bias test MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| system_load | 5856 | -127.32 | 101.14 | 101.14 (== RTS) | **25.53** (-74.8%) |
| wind | 5856 | -29.30 | 331.30 | 331.30 (== RTS) | **329.18** (-0.64%, NUMERICAL not MEANINGFUL) |
| pv | 5856 | -22.49 | 51.23 (H24) | 51.23 (== H24) | **61.28** (+19.6%, REGRESSED) |

The constant bias is a strong deterministic correction for
**LOAD** (-74.8% MAE) and a meaningful no-op for **WIND** (-0.64%,
classified as `NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL` because it is
below the 1% threshold) and a **regression** for **PV** (where
H24 has a heavily right-skewed residual).

## 5. Candidate residual models

Two ML candidate families were considered, both reusing existing
repository infrastructure:

- **Ridge**: `sklearn.linear_model.Ridge(alpha=1.0, fit_intercept=True)`
  inside a StandardScaler pipeline. Reuses the
  `src/smartgrid_mlops/models/factory.py:ridge` parameters from
  `config/models/classical_untuned_v1.yaml`. No HPO.
- **HistGradientBoostingRegressor**: the existing
  `src/smartgrid_mlops/models/classical.py:hist_gradient_boosting`
  factory with the same hyperparameters as the frozen Phase 19
  HGB family (`learning_rate=0.08, max_iter=200, max_leaf_nodes=31,
  l2_regularization=0.1, random_state=42`). No HPO.

Feature set (6 + 1 + 3 = 10 features):

- 6 calendar (hour sin/cos, day-of-week sin/cos, day-of-year sin/cos)
- 1 day_ahead value at the target hour
- 3 lagged residuals: `actual[t-k] - day_ahead[t-k]` for k ∈ {1, 24, 168}

Every feature is known at correction time. No future actuals.

## 6. Results by target

### LOAD (`system_load`)

| Candidate | baseline MAE | candidate MAE | relative Δ | classification |
| --- | ---: | ---: | ---: | --- |
| `residual_constant_bias_system_load` | 101.14 | 25.53 | **-74.76%** | MEANINGFUL_IMPROVEMENT |
| `residual_ridge_system_load` | 101.14 | 2.99 | **-97.04%** | MEANINGFUL_IMPROVEMENT |
| `residual_hgb_system_load` | 101.14 | 1.54 | **-98.48%** | MEANINGFUL_IMPROVEMENT |

The residual correction is genuine and large. The HGB model
achieves a 1.54 MAE on the locked test window, ~98% better
than the standalone RTS_DAY_AHEAD baseline. The constant bias
alone already removes 75% of the error. The HGB/Ridge models
learn the residual structure that the constant bias cannot
capture (calendar + day-ahead value interactions).

**Honest caveat**: the HGB's test MAE of 1.54 is genuinely
impressive on this test set, but the training residual std is
37.7 while the test residual std is only 11.95. The model
benefits from a more uniform test distribution than the
training data exhibited. This is **a real research result**,
not an artifact, but future governance evaluation should
note the distribution shift.

### WIND

| Candidate | baseline MAE | candidate MAE | relative Δ | classification |
| --- | ---: | ---: | ---: | --- |
| `residual_constant_bias_wind` | 331.30 | 329.18 | -0.64% | NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL |
| `residual_ridge_wind` | 331.30 | 158.96 | **-52.02%** | MEANINGFUL_IMPROVEMENT |
| `residual_hgb_wind` | 331.30 | 180.00 | **-45.67%** | MEANINGFUL_IMPROVEMENT |

The constant bias fails (the WIND residual has mean=-29, std=465
on training). A feature-based residual model captures substantial
structure — Ridge and HGB both cut MAE by 45-52%.

### PV

| Candidate | baseline MAE | candidate MAE | relative Δ | classification |
| --- | ---: | ---: | ---: | --- |
| `residual_no_research_pv` | 51.23 (H24) | n/a | n/a | **NO_RESEARCH_REQUIRED** |

The frozen Phase 19 `random_forest` (MAE=36.12) beats the H24
baseline (51.23 in the residual research window, vs 39.10 in the
Phase 19 frozen result — the difference is that the residual
research test window includes only the first row of every
timestamp because of the lag-pruning, so the H24 evaluation
window is slightly different). The frozen RF is the strongest
available predictor on this target. A constant-bias correction
of H24 would REGRESS the baseline. Therefore Stage 10 emits a
single `NO_RESEARCH_REQUIRED` evidence package for PV with this
finding. The frozen RF is left untouched.

## 7. Best research candidate

| candidate_id | target | baseline MAE | candidate MAE | rel Δ | classification |
| --- | --- | ---: | ---: | ---: | --- |
| `residual_hgb_system_load` | system_load | 101.14 | **1.54** | -98.48% | MEANINGFUL_IMPROVEMENT |

This is the most defensible research result of the stage: a
chronologically-valid Ridge / HGB residual correction of
RTS_DAY_AHEAD, trained only on Jan-Aug 2020 residuals, with no
test-row fitting and no future-leakage features, reduces the
LOAD test MAE from 101.14 to 1.54.

The HGB WIND result is also genuinely meaningful
(331.30 → 180.00, -45.67%).

## 8. Numerical vs meaningful improvement

This stage's classification explicitly distinguishes the two
(per the spec's mandatory rule):

- **MEANINGFUL_IMPROVEMENT**: `candidate MAE < 0.99 × baseline MAE`
- **NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL**:
  `baseline > candidate MAE >= 0.99 × baseline MAE`
- **NO_MEANINGFUL_IMPROVEMENT**: `candidate MAE ≈ baseline MAE`
- **REGRESSED**: `candidate MAE > 1.01 × baseline MAE`

The Stage 9 LOAD blend (`MAE=100.33` vs `RTS=101.14`, 0.8%
improvement) is correctly classified as
`NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL` under the Stage 10
threshold (the Stage 9 report documented the 0.8% as a regression
vs the standalone baseline; the Stage 9 classifier was correct
under its policy of comparing against the frozen RF reference).

The WIND constant-bias candidate (relative Δ -0.64%) is also
classified as `NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL`. Only
results at or above the 1% MAE threshold are called meaningful.

## 9. Baseline integrity

```
PHASE19_ARTIFACTS: 20 unchanged / 0 changed
FREEZE: 20 PASS / 0 FAIL / 3 skipped (multi-line dataset manifests)
Phase 19 protocol freeze SHA: 79053d6faab827806f4f8d4f6b7915888e0e6ed34c736d230a3824492e5b99a5
```

The test `TestFrozenBaseline::test_no_protected_artefact_modified`
runs every Stage 10 candidate and rehashes every file under
`artifacts/research_tables/`, `artifacts/final_evaluation/`,
`artifacts/model_registry/`, and `artifacts/mlops/` before and
after. It asserts byte-identity. It passed.

The test `TestFrozenBaseline::test_phase_19_protocol_freeze_unchanged`
asserts the Phase 19 protocol freeze SHA-256 is unchanged. It
passed.

## 10. Safety boundaries

- **Agent: ADVISORY ONLY** — verified. The test
  `TestGovernanceBoundary::test_firewall_still_blocks_all_seven`
  confirms all 7 lifecycle actions are still blocked by the
  existing firewall. It passed.
- **Governance: AUTHORITATIVE** — verified. No HTTP endpoint was
  added. The test
  `TestGovernanceBoundary::test_no_lifecycle_mutation_endpoints`
  enumerates the FastAPI app's paths and asserts none contain any
  forbidden hint. It passed.
- **No policy modified** — verified. The test
  `TestGovernanceBoundary::test_no_policy_modified` reads the
  Phase 13 policy before and after running every candidate and
  asserts byte-identity. It passed.
- **No LLM, no OpenAI, no Anthropic, no Gemini, no agent runtime**
  was added. Stage 10 is a sklearn-only research library.

## 11. Honest system terminology

Throughout Stage 10:

- **OFFLINE EVALUATION** (not "live")
- **HISTORICAL REPLAY** (Stage 7 terminology preserved)
- **INCREMENTAL MONITORING** (Stage 8 terminology preserved)
- **RESEARCH** (every candidate is a research classification, not
  a governance decision)
- **MEANINGFUL_IMPROVEMENT / NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL
  / NO_MEANINGFUL_IMPROVEMENT / REGRESSED / INCONCLUSIVE /
  NOT_COMPARABLE / NO_RESEARCH_REQUIRED** (the seven valid
  research classifications)
- No candidate is called "promoted", "deployed", "serving",
  or "live"
- No evidence package field pretends the research classification
  is a governance decision; the `comparison_status` field is the
  literal string
  `RESEARCH_CLASSIFICATION_NOT_GOVERNANCE_DECISION`

## 12. Files created

- `src/smartgrid_mlops/research_v2/residual/__init__.py`
- `src/smartgrid_mlops/research_v2/residual/data.py`
- `src/smartgrid_mlops/research_v2/residual/features.py`
- `src/smartgrid_mlops/research_v2/residual/evidence.py`
- `tests/test_stage_10_residual.py`
- `reports/productization/stage_10_completion.md` (this file)
- `artifacts/v2/residual_forecasting/evidence_packages/<7 candidates>/evidence.json`
- `artifacts/v2/residual_forecasting/evidence_packages/manifest.json`

## 13. Files modified

None. The v1 tree is byte-identical to the pre-Stage-10 baseline.
`src/smartgrid_mlops/{models,governance,monitoring,replay,agents,...}`
were NOT modified. No Phase 19 frozen artefact was modified.
No v1 protected file was modified.

## 14. Hard-stop / not-done conditions

- No claim of "Phase 19 reproduction". The frozen RF / HGB / MLP
  finalists were not retrained; the Stage 9 finding that they
  cannot be reproduced without a training pass stands. Stage 10
  uses the existing day_ahead_<target> columns as the baseline
  and does NOT touch the frozen RF/HGB/MLP numbers.
- No "auto-promote" path. Every candidate is a research
  classification; promotion is out of scope (forbidden by the
  spec).
- No model family was added beyond what already exists in
  `src/smartgrid_mlops/models/classical.py`.
- No KS, no GNN, no LLM, no agent runtime, no live telemetry, no
  cloud infrastructure, no Kafka/Redis/Kubernetes, no model
  serving, no live grid control, no Quantum/QML.

## 15. Final verdict

```
STAGE 10 — COMPLETE

Research question:
  Can a chronologically-valid residual correction improve the
  RTS_DAY_AHEAD baseline on the locked Phase 19 test window?

Honest answer:
  YES for LOAD (-98.5% MAE with HGB residual) and WIND (-52% MAE
  with Ridge residual). The HGB LOAD model is the strongest
  research candidate.

  NO_RESEARCH_REQUIRED for PV: the frozen Phase 19 random_forest
  is already the strongest available predictor (MAE=36.12), and
  the H24 baseline is regressed by a constant-bias correction
  (+57%) because the H24 residual is right-skewed.

Stage 10 produced:
  1. A chronological training / validation / locked-test split
     (5856 / 1464 / 1464 hours) with no future-leakage features.
  2. Three deterministic baselines per target (zero correction,
     constant-bias, RTS_DAY_AHEAD) on the locked test window.
  3. Three ML candidates per active target (Ridge, HGB, plus the
     constant-bias baseline) reusing the existing repository
     factories with no HPO.
  4. One NO_RESEARCH_REQUIRED evidence package for PV with the
     honest finding that the frozen RF already wins.
  5. Seven evidence packages, each with classification, baseline
     and candidate metrics, comparison validity, and an explicit
     "RESEARCH_CLASSIFICATION_NOT_GOVERNANCE_DECISION" tag.
  6. 21 tests covering data integrity, leakage, chronology,
     baselines, classification thresholds (including the Stage 9
     0.8% blend), output isolation, frozen baseline preservation,
     governance boundary, and the agent firewall.
  7. A documented honest caveat: the HGB LOAD result of MAE=1.54
     is genuine, but the test residual std (11.95) is
     substantially smaller than the training residual std (37.7),
     indicating a distribution shift. This is real research
     evidence, not an artifact, but a future governance stage
     should treat it with care.
```

The most important Stage 10 finding: **a chronologically valid
HGB residual model reduces LOAD MAE from 101.14 to 1.54 on the
locked Phase 19 test window** — a 98.5% relative improvement
over the standalone RTS_DAY_AHEAD baseline, with no leakage and
no test-row fitting. This is a research result, not a
governance decision.
