# Phase 15 completion report

## Phase status

**PHASE 15 COMPLETE — governed retraining, adaptation, and challenger generation (deterministic, development/simulation).** Phase 16 was not begun. No promotion, champion status, agent, LLM, deployment, HPO, feature selection, or final-test access occurred.

Repository note: this phase was executed in the verified working repository `C:\Projects\guardrailed-agentic-mlops-smart-grid\guardrailed-agentic-mlops-smart-grid` (Windows migration validated through Phase 14). The `_trial` sibling copy is a stale Phase-5-era Linux snapshot and was not used.

## Research objective and questions

Primary: design and evaluate a deterministic, governance-controlled retraining workflow that converts eligible drift evidence into bounded retraining jobs and reproducible challenger models without permitting drift events, retraining requests, or newly trained challengers to bypass lifecycle governance. Secondary: measure whether retraining on newly available post-drift development data improves future post-drift forecasting performance relative to the unchanged reference model under controlled adaptation scenarios.

RQ-RET-1 (drift→action without alert=retrain), RQ-RET-2 (deterministic blocking), RQ-RET-3 (post-drift improvement), RQ-RET-4 (reproducible challenger registration without promotion), RQ-RET-5 (how often retraining helps/fails/degrades) are recorded in the frozen protocol. Within the controlled development/simulation scope, the evidence supports H-RET-1 (WATCH/NONE/feature-only alerts denied; 6/6 unnecessary attempts prevented), H-RET-2 (data-quality failure denied), H-RET-3 (14/18 scenarios improved), and H-RET-4 (18/18 lineage-complete challengers, promotion_eligible=false).

## Retraining architecture

`DRIFT EVENT → RETRAINING REQUEST → DETERMINISTIC RETRAINING POLICY (17 gates) → ALLOW/DENY/DEFER → BOUNDED EXPANDING-WINDOW REFIT → RETRAINED CANDIDATE → VALIDATION → REGISTERED_CHALLENGER → STOP`. Implementation: `src/smartgrid_mlops/retraining/` (schemas, policy, requests, eligibility, dataset, refit, evaluation, challenger, registry, events, simulation, aggregation, validation, queries), reusing Phase 12 tracking/lineage/audit, Phase 13 governance identities, and Phase 14 detector/threshold logic without duplication.

## Retraining policy identity

- Policy ID: `SMARTGRID_DETERMINISTIC_RETRAINING`, version **15.0.0**
- Policy SHA-256: `28a05242ab56efb90e82a004e657610b04f9ad35d3756e304bab2429798bc03e`
- Retraining policy fingerprint: `retraining-policy-v1:sha256:f934b780eaedeec97a6aa226586d9b77b5861765aac4fbfd86cacad50b8aea22`
- Phase 15 protocol freeze SHA-256: `5b0cc29d67f6c3475ba9935b41972c3f1c32fafef8abcc9147f8af8d1b5a1dad` (FROZEN)
- Adaptation scenario freeze SHA-256: `c179ef2acb878f4a754f0ba666765a8d136bfea364ad7d8b2a4414aef7852f47` (FROZEN)

## Eligibility rules (frozen)

Eligible drift conditions: persistent PERFORMANCE_DRIFT; persistent ERROR_DISTRIBUTION_DRIFT at WARNING/CRITICAL; compound feature/prediction drift plus performance deterioration; explicit controlled adaptation scenario (condition D). Blocked: NONE and WATCH severity, feature-only drift, prediction-only drift, missing/invalid/non-evidence drift events. Data-quality: critical failures DENY (`DATA_QUALITY_BLOCK`). Labels: only labels observable at the H24 label cutoff; label cutoff earlier than data cutoff rejected. Minimum new data: 336 labeled post-onset observations. Cooldown: 168 hours per target per simulation stream (`DEFER_COOLDOWN`). Reference state: only `REGISTERED_REFERENCE` may be a retraining source. Lineage, model-fingerprint, feature-fingerprint, protocol, final-test, and job-concurrency gates DENY on mismatch. Duplicates return the existing decision with `DUPLICATE_REQUEST`.

## Training strategy and reference specifications

EXPANDING-WINDOW REFIT over development rows with `target_timestamp <= 2020-08-15` (cutoff = onset + 336 h; onset 2020-08-01). The frozen reference is reconstructed for INFERENCE ONLY on its pre-onset window (2020-01-01–2020-08-01, the F05 training boundary). Targets/specifications: LOAD RandomForest B_lags_only (n_estimators=191, seed 42), WIND HistGradientBoosting B_lags_only (max_iter=111, seed 42), PV RandomForest B_lags_only (n_estimators=209, seed 42). No HPO, no feature selection, no family change; preprocessing unchanged (no scaling for tree estimators). Challenger `model_spec_fingerprint` equals the parent's; a new `model-instance-v1` fingerprint (spec + training-dataset fingerprint + cutoff + seed) identifies the instance.

## Deviation P15-DEV-001 (documented, prior evidence unchanged)

The Phase 12 research registry stored LOAD's model-spec fingerprint computed from PV hyperparameters (`classical={x["model"]:x ...}` family-key collision). Phase 10 actually trained LOAD with the correct per-target hyperparameters, so no forecasting result or governance decision is affected. Phase 15 recomputes identities from the correct per-target Phase 10 freeze, and did not modify any prior frozen artifact. Full analysis: `reports/phase_15_p12_fingerprint_deviation.md`.

## Request-policy simulation (official)

15/15 frozen cases correct (100.0%): expected 4 ALLOW / 7 DENY / 4 DEFER; 0 false allows, 0 false denies, 0 false defers. Unsafe retraining attempts 5/5 blocked — **Unsafe Retraining Prevention Rate 100%** (data-quality, lineage, fingerprint tampering, final-test request, invalid evidence). Unnecessary attempts 6/6 prevented (clean, WATCH-only, insufficient persistence, labels unavailable, insufficient data, cooldown). Data-quality blocks: 1. Final-test violations blocked: 1. Duplicate case R13 deterministically returned the original ALLOW with `DUPLICATE_REQUEST`.

## Adaptation experiments (official)

Controlled adaptation / concept-drift proxies on development-only copies: A15-01 abrupt and A15-02 gradual (336 h ramp) target-relationship shifts; LOW/MEDIUM/HIGH = 0.5/1.0/2.0 × pre-onset σ; values clipped at zero; features rebuilt from the perturbed series; source data untouched. 18 scenarios (2×3×3).

- Planned/started/completed jobs: **18/18/18**; failed: 0; mean runtime 0.817 s, median 0.557 s
- Challengers created: 18; registered: **18** (REGISTERED_CHALLENGER, promotion_eligible=false)
- Training rows: 94,626 total; new post-drift rows: 6,066 (337 per scenario ≥ 336 minimum)
- Evaluation: 336 matched post-cutoff timestamps per scenario; clean counterfactual on the unperturbed copy

### Adaptation performance

| Target | Mean reference post-drift MAE | Mean challenger post-drift MAE | Mean gain | Improved | Degraded |
| --- | ---: | ---: | ---: | ---: | ---: |
| LOAD | 411.09 | 345.58 | **+11.38%** | 5 | 1 |
| WIND | 419.00 | 403.78 | **+2.48%** | 3 | 3 |
| PV | 201.99 | 65.84 | **+60.05%** | 6 | 0 |

By severity (mean gain): LOW +13.32%, MEDIUM +20.34%, HIGH +40.25% (monotonic on average, not per case). Negative adaptation retained: A15-01-LOW-wind −4.99%, A15-01-MEDIUM-wind −1.08%, A15-02-HIGH-wind −1.02%, A15-02-LOW-load −0.47%. Clean-stability: adaptation usually cost a little on the unperturbed stream (worst −16.55%, abrupt-HIGH LOAD) with a few low-severity gains (best +5.91%, gradual-LOW PV); per-case table `reports/tables/retraining_clean_stability.md`. No arbitrary success threshold was applied; raw relative changes are reported.

Benchmark context: frozen references still fail the strongest development benchmarks (LOAD/WIND vs RTS DAY_AHEAD; PV vs H24 daily persistence), and external benchmark values are not coherent forecasts under synthetically modified targets, so no external-benchmark adaptation claim is made.

## Safety, lineage, MLflow, and audit

Automatic promotions 0; reference replacements 0; governance bypasses 0; ACTIVE/CHAMPION states absent; `MODEL_PROMOTED` never emitted. Phase 13 lifecycle registry byte-identical before/after (verified by tests). Per-scenario lineage graphs connect canonical data → features → reference spec → drift evidence → request → decision → training dataset → job → model instance → evaluation → registered challenger (`artifacts/retraining/phase_15/manifests/challenger_lineage.yaml`). MLflow: 18 VALID native runs + 1 excluded smoke run, all contract tags/params/metrics verified. Audit: 164 Phase-15 events appended (1,015 → 1,179 total), actors SYSTEM only. Idempotency: re-running the official suite yields 18 cached results, 0 duplicate jobs/challengers.

## Research outputs

Tables: `retraining_request_policy_results`, `retraining_job_summary`, `retraining_adaptation_results` (CSV+MD), `retraining_clean_stability.md`, `retraining_safety_metrics.md`. Figures: governed retraining architecture (SVG), adaptation gain by target (PNG, negatives included), reference vs challenger post-drift (PNG), policy outcomes (SVG), plus figure manifest. Methodology: `docs/research_methodology/governed_retraining.md`. Paper notes: `docs/paper_drafts/governed_retraining_results.md`. Evidence registry: `E-RET-001`–`E-RET-020`.

## Threats to validity (Phase 15 additions)

Synthetic adaptation proxies may not reproduce real grid concept drift; expanding-window refit is one strategy; hyperparameters are not retuned post-drift; severity design shapes observed gains; post-drift evaluation is development/simulation evidence; external benchmarks are semantically incoherent under synthetic targets; single-year data with one onset window; no operational stream or deployment cost; P15-DEV-01 metadata defect documented above.

## Repository verification

- `.venv\Scripts\python.exe -m pytest`: **137 passed, 0 failed, 0 skipped, 0 warnings** (113 pre-phase + 24 Phase 15)
- `.venv\Scripts\python.exe -m compileall -q src scripts tests`: **PASS**
- `.venv\Scripts\python.exe scripts/bootstrap_rts_gmlc.py --verify-only`: **RTS integrity PASS; manifest PASS; checksums PASS**
- All 14 previous freeze checksums unchanged: **PASS**; Phase 13 governance policy checksum: **PASS**
- Phase 15 protocol freeze + adaptation scenario freeze: **VALID** (sidecar SHA-256 verified)

## Final-test audit

FINAL_TEST_TRAINING_ACCESS = NO; FINAL_TEST_HPO_ACCESS = NO; FINAL_TEST_MODEL_SELECTION_ACCESS = NO; FINAL_TEST_FEATURE_SELECTION_ACCESS = NO; FINAL_TEST_PERFORMANCE_EVALUATION = NO; FINAL_TEST_INTEGRITY_AUDIT_ACCESS = YES — historical P9-DEV-002 only. **PHASE_15_NEW_FINAL_TEST_READS = 0.**

## Phase 16 readiness

**READY.** Phase 15 stops at REGISTERED_CHALLENGER. Champion–challenger evaluation, promotion simulation, and rollback are Phase 16 work; no challenger was promoted and no champion status exists.
