# Governed retraining and challenger generation

## Research Objective

Phase 15 designs and evaluates a deterministic, governance-controlled retraining workflow that converts eligible drift evidence into bounded retraining jobs and reproducible challenger models without permitting drift events, retraining requests, or newly trained challengers to bypass lifecycle governance (RQ-RET-1..RQ-RET-5). The secondary objective measures whether retraining on newly available post-drift development data improves future post-drift forecasting performance relative to the unchanged reference model under controlled adaptation scenarios. Pre-registered hypotheses H-RET-1..H-RET-4 predict, respectively: not every alert satisfies eligibility; critical data-quality failures block retraining; bounded refitting improves post-drift MAE in at least some target/scenario combinations; and every successful job yields a lineage-complete challenger whose state remains distinct from promotion eligibility.

## Architecture

`DRIFT EVENT → RETRAINING REQUEST → DETERMINISTIC RETRAINING POLICY → ALLOW / DENY / DEFER → BOUNDED RETRAINING JOB → RETRAINED CANDIDATE → VALIDATION → REGISTERED CHALLENGER → STOP.`

The forbidden path `DRIFT → RETRAIN → DEPLOY` is structurally impossible: monitoring code emits evidence only, the policy engine is the sole decision authority, and no promotion path exists in Phase 15. Everything is deterministic; no agent or LLM is involved.

## Retraining Request

Every request records request/target identity, the reference registry ID and model fingerprint, triggering drift event IDs, severity, detectors, request timestamp, data cutoff, label availability cutoff, proposed training window, policy version, monitoring and governance policy fingerprints, evidence references, origin (`MONITORING_POLICY`, `MANUAL_SIMULATION`, or `SYSTEM_TEST`; `AGENT` is not an allowed origin in Phase 15), and an optional simulation scenario ID. A deterministic `retraining_request_fingerprint` (canonical-JSON SHA-256 over target, reference identity, sorted event IDs, cutoffs, retraining policy fingerprint, and scenario) makes duplicate requests detectable.

## Eligibility Policy

`config/retraining/phase_15_policy.yaml` (policy 15.0.0) declares seventeen ordered gates: policy version, request origin, drift evidence, drift severity, drift persistence, performance signal, data quality, label availability, minimum new data, cooldown, reference state, lineage, model fingerprint, feature fingerprint, protocol, final-test policy, and job concurrency. Decisions are structured `ALLOW`/`DENY`/`DEFER` records with per-gate outcomes and ordered reason codes — never bare booleans. Hard safety failures DENY; premature-but-potentially-valid conditions (insufficient persistence, missing labels, insufficient new data, cooldown, job already running) DEFER.

## Drift Requirements

Severity policy: NONE and WATCH DENY; WARNING is eligible only with persistence and performance criteria; CRITICAL is eligible unless a safety gate blocks it. Feature drift alone and prediction drift alone never authorize retraining. Eligibility requires one frozen condition: (A) persistent PERFORMANCE_DRIFT; (B) persistent ERROR_DISTRIBUTION_DRIFT at WARNING/CRITICAL; (C) compound feature/prediction drift plus performance deterioration; or (D) an explicit controlled adaptation scenario under simulation policy. Persistence requires 2 consecutive eligible 168-hour monitoring windows.

## Data-Quality Gate

Critical data-quality failures (schema corruption, missing required features, NaN/Inf contamination, unresolved missingness) DENY with `DATA_QUALITY_BLOCK`: the correct response to corrupt data is not to train on it.

## Label Availability

Only labels observable at or before `label_availability_cutoff` may enter training. For H24, a row's label is observed at its target timestamp, so any row whose target is unobserved at retraining time is excluded. A label cutoff earlier than the data cutoff is rejected as inconsistent.

## Minimum New Data

At least 336 newly observed labeled post-onset hourly observations (14 days) are required before retraining, preventing reflexive refits on thin evidence.

## Cooldown

A 168-hour cooldown between successful jobs applies per target within one simulation stream; independent adaptation scenarios are independent simulation universes. Requests inside cooldown DEFER (`RETRAINING_COOLDOWN_ACTIVE`) rather than silently launching.

## Training-Data Construction

The retraining dataset is an expanding window over a development-only view: all rows with `target_timestamp <= retraining_cutoff` whose labels are observable at the label cutoff (historical pre-onset rows plus newly observed post-drift rows). Evaluation rows (target timestamps after the cutoff) can never enter training. Each dataset records a deterministic `retraining-dataset-v1` logical fingerprint (target, feature fingerprint, first/last timestamps, row count, cutoff, ordered content hash).

## Expanding-Window Refit

Expanding-window refitting preserves historical information while incorporating newly available post-drift data and avoids introducing an additional retraining-window hyperparameter search. The frozen reference instance is reconstructed for INFERENCE ONLY on its pre-onset training window (2020-01-01 to 2020-08-01, the F05 training boundary) and is never refit on post-drift data (`REFERENCE_INFERENCE`).

## Frozen Model Specification

Challengers reuse the exact Phase 10/11 frozen specification per target — LOAD: sklearn RandomForest (n_estimators=191, bootstrap=true, max_features=1.0, seed 42); WIND: HistGradientBoosting (learning_rate=0.016, max_iter=111, max_leaf_nodes=57, seed 42); PV: RandomForest (n_estimators=209, bootstrap=false, max_features=sqrt, max_depth=8, seed 42) — with the B_lags_only feature set (lag_1, lag_24, lag_168), no scaling for tree estimators, and the single deterministic seed 42 embedded in the frozen hyperparameters. No HPO, no feature selection, no model-family search. The challenger's `model_spec_fingerprint` equals its parent's; a distinct `model-instance-v1` fingerprint (spec fingerprint + training-dataset fingerprint + cutoff + seed, excluding volatile timestamps) identifies the new instance. P15-DEV-001 documents that the Phase 12 registry stored LOAD's fingerprint computed from PV hyperparameters; Phase 15 recomputes from the correct per-target freeze and leaves prior frozen evidence unchanged.

## Adaptation Scenarios

Phase 14 perturbed monitoring statistics on synthetic streams without a coherent retrainable data-generating process, so Phase 15 defines controlled adaptation scenarios: A15-01 (abrupt target-relationship shift) and A15-02 (gradual linear ramp over 336 hours), at LOW/MEDIUM/HIGH severity (0.5/1.0/2.0 × pre-onset standard deviation), for LOAD/WIND/PV — 18 primary cases. Perturbations are deterministic, applied to development-only copies with values clipped at zero, and features are rebuilt from the perturbed series so the synthetic world is coherently retrainable. Source datasets are never mutated. These are CONTROLLED ADAPTATION / CONCEPT-DRIFT PROXIES, not simulations of real grid drift. Drift onset is 2020-08-01; the retraining cutoff is 2020-08-15 (336 hours of new labels); the evaluation window is the following 336 hours; all within development data.

## Post-Retraining Evaluation

On exactly matched synthetic post-drift timestamps, the frozen reference and the retrained challenger are compared on MAE (primary) with RMSE, sMAPE, nMAE, and nRMSE (secondary). Adaptation Gain (%) = (Reference_MAE − Challenger_MAE)/Reference_MAE × 100; negative values are reported, never hidden. Clean counterfactual stability evaluates the same challenger on the unperturbed copy for identical future timestamps: Clean Stability Change (%) = (Clean_Reference_MAE − Clean_Challenger_MAE)/Clean_Reference_MAE × 100. No arbitrary success threshold was defined; raw relative changes are reported.

## Challenger Registration

A retrained candidate becomes REGISTERED_CHALLENGER only when training completed, evidence is VALID, lineage is COMPLETE, feature and model-specification fingerprints match the freeze, the training-dataset fingerprint is present, evaluation is complete, outputs are finite, no unresolved deviation exists, and the final-test policy was respected. Registration writes an additive `artifacts/model_registry/phase_15_challengers.yaml`; prior freezes are unchanged.

## MLflow Tracking

Every official job is a `NATIVE_MLFLOW` run (experiment `phase15/governed_retraining`) with tags for tracking origin, research phase 15, experiment type GOVERNED_RETRAINING, target, scenario family/severity, parent reference ID, retraining policy fingerprint, model-spec/instance fingerprints, training-dataset fingerprint, and evidence status VALID, plus parameters (seed, cutoffs, row counts, frozen hyperparameters) and metrics (reference/challenger MAE, adaptation gain, clean-stability metrics, runtime). The smoke run is tagged NON_EVIDENCE_SMOKE and excluded.

## Auditability

The append-oriented audit log is extended with RETRAINING_REQUEST_CREATED, RETRAINING_REQUEST_ALLOWED/DENIED/DEFERRED, RETRAINING_JOB_STARTED/COMPLETED/FAILED, RETRAINED_CANDIDATE_CREATED, and CHALLENGER_REGISTERED. MODEL_PROMOTED is never emitted in Phase 15. A per-scenario lineage graph connects canonical data → features → reference specification → drift evidence → request → decision → training dataset → job → model instance → evaluation → registered challenger.

## Governance Boundary

Drift must not directly cause retraining; retraining must not directly cause promotion; challenger creation must not replace the reference. Successful Phase 15 outputs terminate at REGISTERED_CHALLENGER with promotion_eligible=false. Champion–challenger evaluation, promotion simulation, and rollback are Phase 16 work.

## Final-Test Isolation

No Phase 15 code path reads November–December data: final-test training, HPO, model-selection, feature-selection, and performance-evaluation access are all NO, requests asking for them DENY with FINAL_TEST_POLICY_VIOLATION, and the historical P9-DEV-002 integrity-audit exception remains historical only. PHASE_15_NEW_FINAL_TEST_READS = 0.

## Limitations

Synthetic adaptation scenarios may not reproduce real grid concept drift; expanding-window refit is one strategy among several; hyperparameters are not retuned post-drift; severity design shapes observed gains; post-drift evaluation is development/simulation evidence; external benchmarks are semantically incoherent under synthetically modified targets; the dataset spans one year with a single onset window; no external operational stream or deployment cost is evaluated; and the Phase 12 LOAD fingerprint metadata defect (P15-DEV-001) is documented rather than silently repaired.
