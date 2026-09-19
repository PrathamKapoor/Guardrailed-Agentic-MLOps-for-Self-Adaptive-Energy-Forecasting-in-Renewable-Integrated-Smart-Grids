# scripts/ — phase pipeline entry points

Each script is a standalone, recorded step of the research lifecycle; the

authoritative command lines and outputs are documented in the matching

`reports/phase_*_completion.md`.



## Conventions

- `run_*` — executes an experiment or pipeline stage

- `build_*` — constructs derived artifacts (features, OPSD external set, dashboard data)

- `finalize_*` — freezes/exports a phase's research artifacts

- `select_*` — model selection under resource constraints

- `evaluate_*` / `report_*` / `rebuild_*` / `regenerate_*` — post-hoc analysis or regeneration

- `smoke_test_*` / `bootstrap_*` / `replay_*` / `import_*` — utilities



All scripts log to stderr via the standard `LOGGER` (level INFO by default);

machine-readable protocol lines (e.g. `THRESHOLD_SHA256=...`, JSON summaries)

are printed to stdout and must stay parseable. Do not convert those to logging.



## Index

- `_scriptlog.py`
- `analyze_classical_errors.py`
- `audit_phase09_feature_integrity.py`
- `audit_rts_gmlc.py`
- `bootstrap_rts_gmlc.py`
- `build_canonical_dataset.py`
- `build_dashboard.py`
- `build_experimental_splits.py`
- `build_features.py`
- `build_opsd_external.py`
- `build_phase12_mlops_foundation.py`
- `build_phase13_governance_foundation.py`
- `evaluate_phase09_post_hpo.py`
- `finalize_phase09_pytorch.py`
- `finalize_phase12_research_artifacts.py`
- `finalize_phase13_research_artifacts.py`
- `finalize_phase14_artifacts.py`
- `finalize_phase15_artifacts.py`
- `finalize_phase16_artifacts.py`
- `finalize_phase19_artifacts.py`
- `import_historical_experiments_to_mlflow.py`
- `rebuild_phase09_feature_integrity.py`
- `regenerate_phase09_reports.py`
- `replay_telemetry.py`
- `report_phase10_ablation.py`
- `run_agent_scenarios.py`
- `run_agentic_comparison.py`
- `run_baseline_experiments.py`
- `run_champion_challenger_simulation.py`
- `run_classical_experiments.py`
- `run_drift_monitoring.py`
- `run_external_validation.py`
- `run_feature_ablation.py`
- `run_governance_candidate_packaging.py`
- `run_governance_evaluation.py`
- `run_governance_re_evaluation.py`
- `run_governance_simulation.py`
- `run_governed_retraining.py`
- `run_hpo_experiments.py`
- `run_incremental_monitoring.py`
- `run_neural_experiments.py`
- `run_phase12_mlflow_smoke.py`
- `run_phase19_final_evaluation.py`
- `run_pytorch_mlp_hpo.py`
- `select_phase11_finalists.py`
- `smoke_test_deployment.py`
