# Paper to Code Traceability Map

This document provides exact, bidirectional traceability between the research manuscript:
**"MLOps-Driven Energy Forecasting for Smart Grids with Renewable Energy Integration"**
and the underlying source code, configurations, test suites, and empirical research artifacts.

---

## 1. Traceability Matrix

| Paper Section | Topic | Source Code | Configuration | Execution Script | Output Artifact (Tables / Figures) | Tests |
|---|---|---|---|---|---|---|
| **Section I: Introduction** | Smart grid forecasting challenge, deterministic vs agentic MLOps | `src/smartgrid_mlops/agents/firewall.py`<br>`src/smartgrid_mlops/governance/policy_engine.py` | `config/governance/phase_13_policy.yaml` | `scripts/run_agent_scenarios.py` | `artifacts/mlops/audit/events.jsonl` | `tests/test_phase13_governance.py`<br>`tests/test_adversarial_firewall.py` |
| **Section II: Related Work** | Time series forecasting & MLOps governance | `src/smartgrid_mlops/baselines/` | `config/baselines/phase_06_baselines.yaml` | `scripts/run_baseline_experiments.py` | `artifacts/research_tables/final_model_comparison.csv` | `tests/test_baselines.py` |
| **Section III: System Architecture** | 5-layer guardrailed MLOps architecture | `src/smartgrid_mlops/` | `pyproject.toml` | `reproduce_paper.py` | `hackathon/architecture.svg`<br>`artifacts/research_figures/mlops_lifecycle_comparison.png` | `tests/test_deployment.py`<br>`tests/test_api_service.py` |
| **Section IV: Experimental Setup** | RTS-GMLC 2020 dataset, zero-leakage chronological split | `src/smartgrid_mlops/data/`<br>`src/smartgrid_mlops/features/pipeline.py` | `data/manifests/processed_dataset_manifest.yaml`<br>`data/manifests/feature_manifest.yaml` | `scripts/build_canonical_dataset.py`<br>`scripts/build_features.py` | `data/processed/research_hourly_index.parquet`<br>`artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml` | `tests/test_features.py`<br>`tests/test_canonical_dataset.py` |
| **Section V: Multi-Horizon Forecasting** | H1, H6, H12, H24 forecast evaluation on Load, Wind, PV | `src/smartgrid_mlops/models/classical.py`<br>`src/smartgrid_mlops/models/neural/base.py` | `config/models/classical_untuned_v1.yaml` | `scripts/run_multi_horizon_experiments.py` | `artifacts/research_tables/multi_horizon_comparison.csv`<br>`artifacts/research_figures/multi_horizon_performance.png` | `tests/test_classical_models.py` |
| **Section VI: Renewable Energy Integration** | Net load, surplus/deficit classification, matching ratio | `scripts/run_renewable_integration_evaluation.py` | `config/experiments/metrics.yaml` | `scripts/run_renewable_integration_evaluation.py` | `artifacts/research_tables/renewable_integration_metrics.csv`<br>`artifacts/research_figures/renewable_integration_analysis.png` | `tests/test_experimental_design.py` |
| **Section VII: Residual Forecast Correction** | External day-ahead baseline correction (1.54 MW MAE) | `src/smartgrid_mlops/research_v2/residual/` | `artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml` | `scripts/evaluate_phase09_post_hpo.py` | `artifacts/v2/residual_forecasting/` | `tests/test_stage_10_residual.py` |
| **Section VIII: Drift Monitoring & Adaptation** | 6 controlled shift scenarios, severity classification | `src/smartgrid_mlops/monitoring/`<br>`src/smartgrid_mlops/retraining/` | `config/monitoring/phase_14_drift.yaml`<br>`config/retraining/phase_15_policy.yaml` | `scripts/run_controlled_drift_experiments.py` | `artifacts/research_tables/controlled_drift_scenarios.csv`<br>`artifacts/research_figures/drift_detection_and_degradation.png`<br>`artifacts/research_figures/adaptation_recovery.png` | `tests/test_phase14_monitoring.py`<br>`tests/test_phase15_retraining.py` |
| **Section IX: MLOps Baseline vs Guarded MLOps** | Unguarded automation vs guarded governance comparison | `src/smartgrid_mlops/champion_challenger/`<br>`src/smartgrid_mlops/governance/` | `config/governance/phase_16_promotion_policy.yaml` | `scripts/run_mlops_baseline_comparison.py` | `artifacts/research_tables/mlops_baseline_vs_guarded.csv`<br>`artifacts/research_figures/mlops_lifecycle_comparison.png` | `tests/test_phase16_champion_challenger.py`<br>`tests/test_phase18_agentic_ablation.py` |
| **Section X: Champion-Challenger & Rollback** | Canary deployment, artifact-level verification of rollback | `src/smartgrid_mlops/champion_challenger/rollback.py` | `config/governance/phase_16_promotion_policy.yaml` | `scripts/run_champion_challenger_lifecycle.py` | `artifacts/research_tables/champion_challenger_lifecycle_outcomes.csv`<br>`artifacts/research_figures/champion_challenger_lifecycle.png` | `tests/test_phase16_champion_challenger.py` |
| **Section XI: Governance Evaluation & Ablation** | 13-gate policy evaluation, ALLOW path, 7-gate ablation | `src/smartgrid_mlops/governance/validators.py`<br>`src/smartgrid_mlops/governance/policy_engine.py` | `config/governance/phase_13_policy.yaml` | `scripts/run_governance_lifecycle_and_ablation.py` | `artifacts/research_tables/governance_outcomes.csv`<br>`artifacts/research_tables/governance_ablation_results.csv`<br>`artifacts/research_figures/governance_ablation.png` | `tests/test_phase13_governance.py`<br>`tests/test_stage_12_governance_evaluation.py` |
| **Section XII: Adversarial Agent Firewall** | Safety firewall blocking 7 lifecycle action types | `src/smartgrid_mlops/agents/firewall.py`<br>`src/smartgrid_mlops/agents/orchestrator.py` | `src/smartgrid_mlops/agents/schemas.py` | `scripts/run_agent_scenarios.py` | `artifacts/mlops/audit/events.jsonl` | `tests/test_adversarial_firewall.py`<br>`tests/test_phase17_agents.py` |
| **Section XIII: Statistical Significance** | Block bootstrap 95% CIs, Diebold-Mariano tests | `scripts/run_statistical_analysis.py` | `config/experiments/statistical_tests.yaml` | `scripts/run_statistical_analysis.py` | `artifacts/research_tables/statistical_significance_results.csv`<br>`artifacts/research_figures/error_distributions_and_confidence_intervals.png` | `tests/test_experimental_design.py` |
| **Section XIV: Cross-Dataset Validation** | Evaluation on OPSD (Germany) dataset | `src/smartgrid_mlops/external_validation/` | `data/manifests/opsd_time_series_manifest.yaml` | `scripts/run_external_validation.py` | `artifacts/research_tables/external_validation_results.csv` | `tests/test_external_validation.py` |

---

## 2. Table-to-Code Mapping

1. **Table 1 (Final Test Forecasting Results):** Generated by `scripts/run_phase19_final_evaluation.py`, recorded in `artifacts/research_tables/final_forecasting_results.csv`.
2. **Table 2 (Benchmark Comparison):** Generated by `scripts/run_phase19_final_evaluation.py`, recorded in `artifacts/research_tables/final_model_comparison.csv`.
3. **Table 3 (Multi-Horizon Performance):** Generated by `scripts/run_multi_horizon_experiments.py`, recorded in `artifacts/research_tables/multi_horizon_comparison.csv`.
4. **Table 4 (Renewable Integration & Net Load):** Generated by `scripts/run_renewable_integration_evaluation.py`, recorded in `artifacts/research_tables/renewable_integration_metrics.csv`.
5. **Table 5 (Controlled Drift Scenarios):** Generated by `scripts/run_controlled_drift_experiments.py`, recorded in `artifacts/research_tables/controlled_drift_scenarios.csv`.
6. **Table 6 (MLOps Baseline vs Guarded Comparison):** Generated by `scripts/run_mlops_baseline_comparison.py`, recorded in `artifacts/research_tables/mlops_baseline_vs_guarded.csv`.
7. **Table 7 (Champion-Challenger Lifecycle):** Generated by `scripts/run_champion_challenger_lifecycle.py`, recorded in `artifacts/research_tables/champion_challenger_lifecycle_outcomes.csv`.
8. **Table 8 (Governance Outcomes & Ablation):** Generated by `scripts/run_governance_lifecycle_and_ablation.py`, recorded in `artifacts/research_tables/governance_ablation_results.csv`.
9. **Table 9 (Statistical Significance & CIs):** Generated by `scripts/run_statistical_analysis.py`, recorded in `artifacts/research_tables/statistical_significance_results.csv`.
10. **Table 10 (External Validation on OPSD):** Generated by `scripts/run_external_validation.py`, recorded in `artifacts/research_tables/external_validation_results.csv`.

---

## 3. Figure-to-Code Mapping

1. **Figure 1 (System Architecture):** `hackathon/architecture.svg` and `artifacts/final_release/architecture_diagram.svg`.
2. **Figure 2 (Multi-Horizon Performance):** Generated by `scripts/run_multi_horizon_experiments.py`, saved to `artifacts/research_figures/multi_horizon_performance.png` and `.svg`.
3. **Figure 3 (Renewable Integration Analysis):** Generated by `scripts/run_renewable_integration_evaluation.py`, saved to `artifacts/research_figures/renewable_integration_analysis.png` and `.svg`.
4. **Figure 4 (Drift Detection & Degradation):** Generated by `scripts/run_controlled_drift_experiments.py`, saved to `artifacts/research_figures/drift_detection_and_degradation.png` and `.svg`.
5. **Figure 5 (Adaptation & Recovery):** Generated by `scripts/run_controlled_drift_experiments.py`, saved to `artifacts/research_figures/adaptation_recovery.png` and `.svg`.
6. **Figure 6 (MLOps Lifecycle Comparison):** Generated by `scripts/run_mlops_baseline_comparison.py`, saved to `artifacts/research_figures/mlops_lifecycle_comparison.png` and `.svg`.
7. **Figure 7 (Champion-Challenger Flow):** Generated by `scripts/run_champion_challenger_lifecycle.py`, saved to `artifacts/research_figures/champion_challenger_lifecycle.png` and `.svg`.
8. **Figure 8 (Governance Ablation):** Generated by `scripts/run_governance_lifecycle_and_ablation.py`, saved to `artifacts/research_figures/governance_ablation.png` and `.svg`.
9. **Figure 9 (Statistical Error Distributions & 95% CIs):** Generated by `scripts/run_statistical_analysis.py`, saved to `artifacts/research_figures/error_distributions_and_confidence_intervals.png` and `.svg`.
