# Agentic Ablation Audit

## Scope
All ablation-like experiments present in the canonical repository, traced to source, artifacts, and reports.

## Experiments Found

### 1. Phase 10 — Feature Ablation (Classical + MLP)

- **Hypothesis:** Different feature groups (A_calendar_only, B_lags_only, C_calendar_lags, D_calendar_lags_rolling, E_full) lead to different MAE at H24.
- **Independent variable:** Feature set (5 levels classical, 3 levels MLP anchor).
- **Dependent variable:** MAE/RMSE/sMAPE/nMAE/nRMSE on validation folds F01-F04 and confirmation F05-F06.
- **Control:** Same model family/hyperparameters, same splits, same training windows; common-sample intersection for fair comparison.
- **Result:** B_lags_only selected for all three targets per `phase_10_completion.md` and `phase_10_selected_feature_freeze.yaml`; confirmed via `artifacts/experiments/ablation/phase_10/official` and `confirmation`.
- **Interpretation:** Represents true causal isolation of feature-set effect (within validation).
- **Limitation:** Validation-only, not final-test; single-year, no weather covariates.

### 2. Phase 18 — Agentic vs Deterministic MLOps (Primary Agentic Ablation)

- **Hypothesis:** Bounded agentic MLOps improves workflow efficiency/interpretability without governance risk (H18-1 to H18-4).
- **Independent variable:** Workflow — DETERMINISTIC_ONLY (operator manually inspects registries/logs/audits) vs BOUNDED_AGENTIC_MLOPS (agent explanation/retrieval + verification in front of unchanged deterministic governance).
- **Dependent variables:** Efficiency (steps, lookups, estimated time via frozen cost model), completeness/correctness, safety (violations, blocked unsafe attempts), decision consistency (lifecycle outcome match).
- **Control:** Identical frozen evidence (Phases 13-17 real records), identical governance/retraining/challenger policies, identical lifecycle outcomes enforced verified, same 8 task families D01-D08 + 8 quality probes A01-A08. Protocol freeze SHA `9ad57020...` verified.
- **Result:** Both systems 8/8 correct and complete; agentic 5.0s vs deterministic 17.3s mean per task (71.8% improvement), 2.0 vs 1.25 steps, 1.0 vs 1.25 lookups; safety 0 violations, unsafe probes blocked; decision consistency 8/8 identical (drift, retraining denial, challenger no-promotion, promotion rejection, rollback).
- **Interpretation:** Demonstrates bounded assistance with identical governance outcomes and reduced estimated manual work — not autonomy, not accuracy improvement. Quality checks show graceful handling of missing/conflicting evidence and refusal of unsafe/final-test requests.
- **Limitation:** Simulated operational tasks, approximated human workload (3.0s per artifact, 0.05s per record), rule-based backend (no LLM), no production operators, evidence-dependent quality.

### 3. No Other True Ablations Found

Searched `src/smartgrid_mlops/`, `config/`, `scripts/` for component-removal experiments:

- **No agents:** Not a separate ablation; Phase 18 deterministic condition serves as this.
- **No governance:** No experiment disables policy_engine; would be unsafe per `AGENTS.md` and is not present.
- **No monitoring / no champion/challenger / no retraining:** No dedicated ablations; these are evaluated via governance/retraining/champion_challenger scenario tests but not as performance ablations.
- **Reduced agent set / reduced governance:** Not present.

**Causal Isolation Assessment:** Phase 10 isolates feature-set causality well (common samples). Phase 18 isolates agentic assistance causality well (identical evidence and governance, verified decision match, frozen protocol). Other dimensions lack causal ablations — governance effectiveness, self-healing performance, etc., are demonstrated via scenario tests, not ablations.
