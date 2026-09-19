# Hackathon judge FAQ

Every answer below is grounded in a recorded artefact in the repository. The "Evidence" column points to the file or the page that proves the claim.

## What exactly did you build?

A 20-phase, governance-first MLOps research system for electricity forecasting on the RTS-GMLC 2020 dataset, plus a frozen Phase 19 final evaluation on a held-out 2-month test partition, plus a read-only Phase 20 evidence dashboard, plus a bounded agentic decision-support layer with a governance firewall.

**Evidence:** `AGENTS.md`, `README.md`, the 20 phase completion reports under `reports/`, `hackathon/index.html`, `dashboard/index.html`.

## Why a governance firewall for the agent layer?

Because in MLOps the highest-leverage action (retrain, promote, change features) is also the most dangerous. Most "agentic MLOps" projects give the agent real authority; we built the inverse. The firewall allows only advisory types and blocks lifecycle action types. The blocked audit events (`AGENT_MODEL_PROMOTED`, `AGENT_RETRAINING_STARTED`) cannot be emitted by construction — the audit module rejects them at the schema level, not just at runtime.

**Evidence:** `src/smartgrid_mlops/agents/firewall.py`, `src/smartgrid_mlops/agents/audit.py`, `tests/test_phase17_agents.py`.

## Why graphs? (Or: did you use a graph neural network?)

**No.** The repository does not contain a graph representation or a graph neural network. The frozen feature set is **B_lags_only** for the three finalist references (lag_1, lag_24, lag_168) and **E_full** for the MLP challenger. There is no graph-native component. The hackathon layer is honest about this and does not invent one.

**Evidence:** `config/ablation/phase_10.yaml`, `docs/research_methodology/feature_engineering.md`, `docs/research_methodology/forecasting_finalist_selection.md`.

## Why quantum computing?

**Not used.** The project is classical machine learning on commodity hardware. There is no QPU, no qiskit, no pennylane, no variational quantum circuit anywhere in the repository. The hackathon layer is honest about this. If a judge expects a quantum demo, they should know that this project does not claim one.

**Evidence:** `pyproject.toml` (only `pyarrow`, `scikit-learn`, `torch`, `optuna`, `mlflow`); `grep -rilE "qubit|qiskit|pennylane|cirq|qml"` over `src/ scripts/ tests/ docs/ config/ reports/ artifacts/` returns zero hits.

## Did quantum / graph / agentic components outperform classical ML?

The agentic layer does not affect lifecycle outcomes — Phase 18 measured **0 lifecycle differences** and **14 of 14 unsafe recommendations blocked** (the firewall is exact). The system does not claim universal superiority over external benchmarks: PV's frozen random forest beats H24 daily persistence by **7.61%**; LOAD and WIND do not beat the published RTS_DAY_AHEAD forecast on this 2-month window. We report both outcomes.

**Evidence:** `artifacts/research_tables/final_model_comparison.csv`, `reports/phase_18_completion.md`, `reports/phase_19_completion.md`.

## Which benchmarks did you use?

Frozen from the start of the project and never changed:

- **LOAD:** RTS_DAY_AHEAD (`day_ahead_system_load` column of the source dataset)
- **WIND:** RTS_DAY_AHEAD (`day_ahead_wind` column)
- **PV:** H24 daily persistence (forecast at hour t = observed actual value at hour t − 24 hours)

**Evidence:** `artifacts/experimental_design/final_test_comparison_plan.yaml`, `artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml`, `src/smartgrid_mlops/final_evaluation/engine.py`.

## What were the strongest results?

- **PV frozen random forest (B_lags_only): MAE 36.12** vs H24 daily persistence 39.09 → **−7.61%** (the frozen model wins on PV).
- **LOAD frozen random forest (B_lags_only): MAE 174.26** vs RTS_DAY_AHEAD 101.14 → **+72.29%** (the frozen model loses on LOAD).
- **WIND frozen hist gradient boosting (B_lags_only): MAE 778.84** vs RTS_DAY_AHEAD 331.30 → **+135.08%** (the frozen model loses on WIND).

**Evidence:** `artifacts/research_tables/final_model_comparison.csv`, `dashboard/index.html` "Benchmark comparison" section, `dashboard/data/results.json`.

## What failed?

1. **LOAD and WIND frozen models lost to RTS_DAY_AHEAD on the 2-month test partition.** We did not retrain, did not re-tune, did not pick a different benchmark. We report the result as recorded.
2. **MLP challenger lost to the frozen reference on all three targets.** The champion-challenger + rollback layer would have blocked the swap. Phase 16 metrics: 18 registered challengers, 0 promotions, 0 governance state changes.
3. **The agentic layer does not improve the forecasting results** — by design. It reduces explanation effort (Phase 18 measured ~72% reduction under a frozen cost model) but cannot touch the model. That is the point.

**Evidence:** `artifacts/research_tables/final_forecasting_results.csv`, `reports/phase_16_completion.md`, `reports/phase_18_completion.md`.

## What makes the project unique?

Six concrete differentiators (all evidenced):

1. **Governance firewall for agents** — `src/smartgrid_mlops/agents/firewall.py`. Allowed: INVESTIGATE / SUMMARIZE / EXPLAIN / REQUEST_HUMAN_REVIEW / CREATE_REPORT. Blocked: PROMOTE_MODEL / ROLLBACK_MODEL / CHANGE_POLICY / START_RETRAINING / CHANGE_FEATURES + unknown (deny-by-default).
2. **Honest mixed-outcome final evaluation** — PV wins, LOAD and WIND lose. Reported transparently.
3. **Frozen protocol cascade** — 20 protocol freezes with sidecar SHA-256s. The final test partition is excluded from phases 0–18 and read only once under `AccessMode.FINAL_EVALUATION` with `configuration_frozen=True`.
4. **Deterministic evidence pipeline** — hash-chained ledger, MLflow lineage, registry with provenance.
5. **Operational benefit measured by ablation, not user study** — Phase 18: 0 lifecycle differences, 14/14 unsafe blocked, ~72% effort reduction under a frozen cost model.
6. **Read-only evidence interface** — `dashboard/index.html` is the primary demo. The builder is verified to leave every Phase 19 artefact byte-identical.

**Evidence:** see each bullet's referenced file.

## What is reproducible?

- **The full test suite** — 231 backend tests + 18 dashboard tests, deterministic. Run `.venv\Scripts\python.exe -m pytest`.
- **The frozen evaluation** — every test-partition timestamp is checked by `authorize_final_evaluation`; the result is in `artifacts/experiments/final_evaluation/phase_19/official/`.
- **The dashboard data** — `scripts/build_dashboard.py` re-emits `dashboard/data/*.json` deterministically from the Phase 19 artefacts.
- **The integrity baseline** — `artifacts/ui_build/phase19_integrity_baseline.json` records the SHA-256 of 20 critical artefacts.

**Evidence:** `docs/phase_20_ui_architecture.md`, `tests/test_phase20_dashboard.py`.

## What is simulated?

- The 18 challengers from the governed retraining phase are trained on **synthetic adaptation scenarios** (A15-01 abrupt and A15-02 gradual target shifts at LOW/MEDIUM/HIGH severity). This is simulation, not real concept drift on the production data. The final evaluation uses real RTS-GMLC data, not synthetic.
- The agent operational benefit (Phase 18) is measured against a **frozen cost model** for human inspection, not a user study. The cost model is in the codebase.
- The drift monitoring uses real F01–F06 data but is evaluation-only — the system is not running in production.

**Evidence:** `artifacts/experimental_design/phase_15_adaptation_scenarios.yaml`, `docs/research_methodology/governed_retraining.md`, `reports/phase_18_completion.md`.

## What would be required for hardware deployment?

Nothing in the frozen system is hardware-bound. The ML stack (scikit-learn, PyTorch MLP, MLflow) runs on any commodity CPU. The deterministic governance and the agent layer are pure-Python. Production deployment would require:

- A live data feed (currently the system reads pre-extracted parquet files from RTS-GMLC).
- A serving layer that reuses the dashboard's frozen-model artifacts.
- A monitoring pipeline that emits the same `DriftEvent` / `RetrainingRequest` objects the offline system uses.
- An organizational process to act on `ESCALATE` decisions and the few remaining `BLOCK_DEPLOYMENT` cases.

None of this is implemented in the repository; the repository is an evaluation-only research artefact. We are not claiming production readiness.

## What are the limitations?

- One year (2020, leap year) of one dataset (RTS-GMLC). 8,784 hourly rows.
- Classical ML only: random forest, hist gradient boosting, MLP. No deep learning, no quantum, no GNN.
- Final test is a single 2-month window; no cross-year generalization.
- The agent layer is local rule-based, not LLM-backed. The LLM backend interface is documented as a contract only.
- The external benchmark (RTS_DAY_AHEAD) is a published operating artefact; beating it on LOAD/WIND is genuinely hard for short-horizon ML models.
- The agent operational benefit is approximated by a cost model, not measured against a real user study.

**Evidence:** `docs/research_methodology/threats_to_validity.md`, `dashboard/index.html` "Limitations" section, `docs/research_methodology/bounded_agentic_ai.md`.

## What would you do next?

In order of scientific priority, with the constraint that the frozen research layer stays frozen:

1. **Add a second dataset** (e.g. OPSD European solar) to test generalization across jurisdictions and years. This is non-trivial because the entire protocol cascade must be re-validated.
2. **Replace the rule-based agent with a real LLM backend** (the contract is already in `src/smartgrid_mlops/agents/base.py`) and measure whether LLM-generated explanations match the rule-based baseline.
3. **Add an end-to-end serving layer** that reuses the frozen model artifacts for live inference, with the same governance + audit guarantees.
4. **A user study** to measure whether the agent's 72% effort reduction under a cost model holds in real operations.

None of these are promised as capabilities in the current submission. The repository is an evaluation-only research artefact.
