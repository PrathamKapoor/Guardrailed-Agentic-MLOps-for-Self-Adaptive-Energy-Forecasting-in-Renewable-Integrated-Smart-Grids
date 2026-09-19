# Final Scientific Research Audit Report

**Repository:** `guardrailed-agentic-mlops-smart-grid`  
**Date:** September 2026  
**Verification Status:** All defined automated verification checks pass; limitations and non-goals explicitly recorded.  
**Canonical Test Suite:** 513 backend pytest tests (100% pass) | 27 frontend vitest tests (100% pass)  
**Reproduction Tooling:** `reproduce_paper.py` (`--quick` for artifact/protocol verification; `--full` for experimental reproduction)

---

## 1. Research Artifact Status

- **Implementation:** VERIFIED against automated test suite (513 backend tests; 27 frontend tests).
- **Governance Architecture:** 13 deterministic promotion/lifecycle gates + 17 deterministic retraining eligibility gates implemented as two distinct policy sets.
- **Quantitative Claims Audit:** 57 total claims audited in `docs/QUANTITATIVE_CLAIMS_AUDIT.md` (40 VERIFIED, 17 QUALIFIED, 0 PARTIALLY VERIFIED, 0 UNSUPPORTED, 0 REFUTED).
- **Reproducibility:** Protocol-frozen artifacts and executable reproduction workflows provided (`reproduce_paper.py`).
- **Statistical Analysis:** Autocorrelation-aware Diebold-Mariano tests (24-step Harvey-Leybourne-Newbold correction) and block-bootstrap analyses implemented.
- **Forecasting Results:** Final frozen-test results reproduced from generated artifacts; negative benchmark outcomes on Load and Wind reported transparently.
- **External Validation:** OPSD zero-shot transfer evaluated and qualified as a cross-dataset domain/scale stress test under unscaled preprocessing.
- **Operational Scenarios:** Controlled lifecycle simulations (SC01–SC10), not empirical utility outage incidents.
- **Human Factors:** Scenario-based analytical workload model only; no human-subject user study was conducted.
- **External Validity:** Limited by single primary calendar year (2020) and evaluated datasets.
- **Real-World Deployment:** Not demonstrated; offline evaluation only.

---

## 2. Scope & Dataset Provenance

- **Primary Dataset:** RTS-GMLC (Reliability Test System - Grid Modernization Lab Consortium), National Renewable Energy Laboratory. Acquired 2026-08-13; archive checksum recorded in `data/manifests/rts_gmlc_manifest.yaml`.
- **Coverage:** 8,784 matched hourly observations per target for calendar year 2020. Targets: system load, aggregate wind, and utility-scale PV generation. Zero missing values; PV nighttime zeros (46.4%) retained as valid physical observations.
- **External Dataset:** Open Power System Data (OPSD) German national grid (`time_series_60min_singleindex.csv`, CC BY 4.0), comprising 49,983 hourly observations.
- **Limitation:** RTS-GMLC is a synthetic test grid model; OPSD is a national transmission system. Direct zero-shot transfer represents a cross-dataset stress test across differing geographical and electrical capacities (~60 GW peak load vs ~3 GW).

---

## 3. Experimental Protocol & Test-Set Discipline

- **Chronological Splitting:** Strictly forward-chained splits. Training period: Jan 1 – Aug 31, 2020. Validation period: Sep 1 – Oct 31, 2020. Sealed final-test partition: Nov 1 – Dec 31, 2020 (1,464 hourly rows).
- **Zero-Leakage Guarantee:** Feature transformations, lag construction, scaling, and imputations fit strictly on training partitions and projected forward. 97,747 individual feature cell / timestamp assertions checked with 0 future-data violations.
- **Test-Set Discipline:** Final-test partition was sealed by `artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml` and accessed only in frozen evaluation mode. No hyperparameter optimization, model family search, feature selection, or early stopping accessed final-test targets.

---

## 4. Forecasting Results & Benchmark Outcomes

| Target | Model | MAE (MW) | RMSE (MW) | Baseline | Baseline MAE | Relative Diff (%) | Benchmark Gate |
|---|---|---|---|---|---|---|---|
| **PV** | Random Forest | **36.12** | 82.08 | H24 Daily Persistence | 39.09 | **−7.61%** | **PASS** |
| **PV** | MLP | 221.64 | 249.27 | H24 Daily Persistence | 39.09 | +466.97% | FAIL |
| **Load** | Random Forest | 174.26 | 231.27 | RTS Day-Ahead | 101.14 | +72.29% | FAIL |
| **Load** | MLP | 281.00 | 343.36 | RTS Day-Ahead | 101.14 | +177.83% | FAIL |
| **Wind** | Hist. Gradient Boosting | 778.84 | 923.37 | RTS Day-Ahead | 331.30 | +135.08% | FAIL |
| **Wind** | MLP | 838.40 | 957.93 | RTS Day-Ahead | 331.30 | +153.06% | FAIL |

- **Major Conclusion:** Only PV Random Forest satisfies the benchmark gate (-7.61% relative MAE). Autoregressive Load (+72.3%) and Wind (+135.1%) models underperform the published RTS Day-Ahead operational forecast because they lack numerical weather predictions and market commitment data. These negative results are reported without post-hoc tuning.

---

## 5. Statistical Validation & Autocorrelation Correction

- **Block Bootstrap:** 1,000 block bootstrap replications (24h block size) generate 95% confidence intervals:
  - PV RF MAE: 36.12 MW [29.60, 44.00] vs Persistence: 39.09 MW [29.18, 49.19]
  - Load RF MAE: 174.26 MW [154.78, 193.53] vs Day-Ahead: 101.14 MW [99.64, 102.66]
  - Wind HistGB MAE: 778.84 MW [699.87, 867.02] vs Day-Ahead: 331.30 MW [281.09, 386.20]
- **Diebold-Mariano vs Wilcoxon Tests:**
  - Wilcoxon signed-rank test yields $p = 3.42 \times 10^{-37}$ for PV RF vs Persistence.
  - Diebold-Mariano test with 24-step Harvey-Leybourne-Newbold (HLN) autocorrelation correction yields $DM = -0.7955$ and $p = 0.4265$.
  - **Reason for Difference:** Wilcoxon assumes independent, identically distributed observations. Multi-step forecasting errors exhibit strong 24-hour serial autocorrelation. The HLN adjustment corrects the variance estimator for serial dependence, showing that the PV outperformance is **not statistically significant** at $\alpha = 0.05$. Both tests confirm statistically definitive underperformance for Load and Wind ($p < 10^{-10}$).

---

## 6. Multi-Horizon Forecasting Evaluation

Evaluated across operational dispatch horizons (`artifacts/research_tables/multi_horizon_comparison.csv`):

- **Load:** H1 65.20 MW (vs Seasonal Naive 197.92 MW, -67.06%); H6 134.12 MW (vs 545.30 MW, -75.40%); H12 157.49 MW (vs Persistence 596.06 MW, -73.58%); H24 91.48 MW (vs Persistence 197.92 MW, -53.78%).
- **Wind:** H1 93.63 MW (vs Persistence 172.38 MW, -45.69%); H6 400.94 MW (vs 420.82 MW, -4.72%); H12 599.41 MW (vs 609.96 MW, -1.73%); H24 782.39 MW (vs 792.12 MW, -1.23%).
- **PV:** H1 23.21 MW (vs Seasonal Naive 105.66 MW, -78.04%); H6 47.95 MW (vs 499.95 MW, -90.41%); H12 48.19 MW (vs Persistence 668.22 MW, -92.79%); H24 40.46 MW (vs Seasonal Naive 40.96 MW, -1.23%).
- **Diurnal Dynamics:** PV H12 error (48.19 MW) exceeds H24 error (40.46 MW) due to diurnal solar geometry: a 12-hour lag shifts noon peak to midnight trough (out-of-phase), whereas a 24-hour lag aligns in-phase with the daily solar cycle.

---

## 7. Governance Architecture & Deterministic Policies

The repository implements two distinct, deterministic policy sets:
1. **13 Lifecycle & Promotion Governance Gates:** Enforced by `GovernanceEngine` (`src/smartgrid_mlops/governance/validators.py`) and `PromotionPolicy` (`src/smartgrid_mlops/champion_challenger/promotion.py`):
   - `REGISTRATION_RECORD_GATE`, `LINEAGE_COMPLETENESS_GATE`, `MODEL_SPEC_FINGERPRINT_GATE`, `FEATURE_SPEC_FINGERPRINT_GATE`, `TRAINING_PROTOCOL_GATE`, `ARTIFACT_INTEGRITY_GATE`, `EVIDENCE_VALIDITY_GATE`, `PERFORMANCE_COMPLIANCE_GATE`, `BENCHMARK_GATE`, `STATISTICAL_EVIDENCE_GATE`, `FINAL_TEST_POLICY_GATE`, `APPROVAL_PREREQUISITE_GATE`, `GOVERNANCE_METADATA_GATE`.
2. **17 Retraining Eligibility Gates:** Enforced by `RetrainingPolicy` (`src/smartgrid_mlops/retraining/policy.py`).
3. **Genuine ALLOW Path:** Demonstrated in scenario `CASE_01_GENUINE_ALLOW` and verified by regression test `test_genuine_allow_path_with_all_thirteen_gates_passed`. This demonstrates that a compliant candidate can pass the implemented deterministic policy; it does not constitute a proof of physical grid safety.
4. **Governance Ablation:** Across 100 synthetically flawed candidate packages (seed=42), the full 13-gate policy admitted 0 flawed candidates (0.0% breach rate). Disabling the benchmark gate admitted 13 benchmark-losing models (13.0% breach rate); disabling the evidence validity gate admitted corrupted models directly.

---

## 8. Agentic AI & Capability Firewall Boundaries

- **Bounded Decision Support:** Agents operate on structured JSON evidence summaries only. No live Large Language Model (LLM) is used; the LLM interface is an abstract contract.
- **Firewall Enforcement:** Allows 5 advisory action types (`INVESTIGATE`, `SUMMARIZE`, `EXPLAIN`, `REQUEST_HUMAN_REVIEW`, `CREATE_REPORT`) and structurally blocks 7 canonical lifecycle mutation types (`PROMOTE`, `DEPLOY`, `ROLLBACK`, `RETRAIN`, `CHANGE_POLICY`, `MODIFY_MODEL`, `MODIFY_FEATURES`, along with implementation synonyms and any unrecognized actions via deny-by-default).
- **Test Evidence:** Dedicated pytest tests in `tests/test_adversarial_firewall.py` and `tests/test_api_service.py` verify that all enumerated forbidden lifecycle mutations are deterministically intercepted and audited in the tested execution paths. This provides implementation-level enforcement for the defined action set, not a mathematical proof of security against arbitrary external attackers.

---

## 9. Controlled Distribution Shift & Adaptation

Six controlled drift scenarios evaluated through the monitoring and governance lifecycle (`artifacts/research_tables/controlled_drift_scenarios.csv`):
- **D01 (Mean Shift +15%):** Rel Deg: +109.50% (+94.39 MW); Governed decision: ALLOW; Post-adapt MAE: 160.98 MW; Lost Acc Rec: 20.78%; Rel Gain: 10.86%.
- **D02 (Variance Shock 1.8x):** Rel Deg: +156.15% (+134.60 MW); Governed decision: ALLOW; Post-adapt MAE: 252.73 MW; Adapting to noise degraded MAE (Lost Acc Rec: 0.0%, Rel Gain: -14.46%).
- **D03 (Peak Shift 3h):** Rel Deg: -0.37%; Governed decision: DEFER (`INSUFFICIENT_PERSISTENCE`); Post-adapt MAE: 85.89 MW.
- **D04 (Ramp Drop -30%):** Rel Deg: +475.55% (+409.94 MW); Governed decision: ALLOW; Post-adapt MAE: 148.02 MW; Lost Acc Rec: 84.92%; Rel Gain: 70.17%.
- **D05 (Regime Shock):** Rel Deg: +82.31%; Governed decision: DEFER (`INSUFFICIENT_PERSISTENCE`); Post-adapt MAE: 157.16 MW.
- **D06 (Sensor Fault Zero-Stuck):** Rel Deg: +2204.25%; Governed decision: **DENY** (`DATA_QUALITY_BLOCK`); Retraining blocked, corrupted model prevented from entering registry.

---

## 10. Renewable Integration & Potential Surplus Analysis

- **Mathematical Balance Definition:** Potential renewable surplus is defined as $P_{\text{surplus}} = \max(0, P_{\text{Wind}} + P_{\text{PV}} - L)$. This represents forecast-derived potential surplus and does not represent observed or simulated grid curtailment, as RTS-GMLC does not model transmission flow limits or economic redispatch constraints.
- **Quantification:** Potential surplus occurred in 16 hours (2,944.36 MWh) of the test partition and 21 hours (3,380.00 MWh) annually.
- **Class Imbalance & Classification Metrics:** In the test partition, surplus is absent in 1,448 of 1,464 hours (98.91% negative class). A trivial classifier that always predicts zero achieves 98.91% accuracy. Standalone ML models predicted 0 surplus hours (Recall = 0.00%, F1 = 0.0000); the external day-ahead baseline detected 5 of 16 surplus events (Recall = 31.25%, F1 = 0.4762).

---

## 11. Cross-Dataset External Validation (OPSD Germany)

- **Result:** Evaluating frozen RTS-GMLC configurations on 49,983 hourly observations of the German OPSD dataset produced severe scale divergence:
  - Load reference MAE: 48,228.33 MW (nMAE: 86.90%) vs local persistence baseline 4,459.73 MW (nMAE: 8.04%).
  - Wind reference MAE: 10,140.74 MW (nMAE: 87.88%) vs local persistence baseline 5,944.00 MW (nMAE: 51.51%).
  - PV reference MAE: 4,038.89 MW (nMAE: 88.07%) vs local persistence baseline 1,060.89 MW (nMAE: 23.13%).
- **Scientific Limitation:** The zero-shot OPSD result demonstrates poor transfer under the evaluated cross-dataset preprocessing, but does not isolate whether the degradation arises from distribution shift, scale mismatch, feature mismatch, or their combination.

---

## 12. Reproducibility & Artifact Integrity

- **Reproduction Tooling:**
  - `python reproduce_paper.py --quick`: Rapid artifact and protocol verification (<20s). Validates file existence, SHA-256 protocol freeze hashes, table schemas, and figure generation consistency. Does not rerun full model training.
  - `python reproduce_paper.py --full`: Complete experimental reproduction (~10 min on CPU). Re-executes multi-horizon experiments, renewable analytics, drift simulations, MLOps baseline comparisons, champion-challenger lifecycles, governance ablations, and statistical tests.
- **Protocol Freezes:** 20 `.sha256` sidecars in `artifacts/experimental_design/` provide byte-level integrity checks for frozen protocol files.
- **Conceptual Distinction:** SHA-256 protocol freezes confirm artifact integrity (the files on disk match their frozen digests). They do not independently prove experimental reproducibility (which requires re-execution via `--full`) or scientific validity (which depends on peer review and external replication).

---

## 13. Unsupported Claims Removed or Qualified

1. **Removed:** Subjective self-evaluations ("9.7 / 10", "Production-Grade Research Artifact", "Top-Tier", "Flawless", "Exceptional").
2. **Removed:** Simulated peer-review verdicts ("Strong Accept", "Accept").
3. **Removed:** Claims of "publication ready" or "ready for publication" as an objective fact; replaced with "research artifact prepared for external review".
4. **Qualified:** "Physical rollback" replaced with "artifact-level rollback verification" (file existence, hash, loadability, prediction probe).
5. **Qualified:** "Renewable curtailment" replaced with "potential renewable surplus" ($P_{\text{Wind}} + P_{\text{PV}} > L$).
6. **Qualified:** MLOps outages and MTTR (48.2h vs 0.05h) labeled as controlled lifecycle simulations and analytical scenario parameters, not empirical utility outage logs.
7. **Qualified:** Operator workload reduction (~72%) labeled as a scenario-based analytical workload model, not an empirical human-subject finding.
8. **Qualified:** PV statistical significance corrected to reflect that Diebold-Mariano with 24-step HLN autocorrelation adjustment is not statistically significant at $\alpha = 0.05$ ($p = 0.4265$).
9. **Qualified:** OPSD zero-shot transfer explicitly noted as not isolating scale mismatch from distribution shift.

---

## 14. Remaining Limitations & Future Work

1. **Single-Year Primary Dataset:** Evaluation is conducted on calendar year 2020 of the RTS-GMLC dataset (8,784 hourly observations). Multi-year climate extremes, decadal weather patterns, and inter-annual variability are not represented.
2. **No Live Telemetry or Streaming:** The system operates entirely offline on historical parquet archives. There is no live SCADA integration or streaming ingestion pipeline.
3. **No Demonstrated Physical Grid Control:** The system is an implemented software artifact. It does not demonstrate real grid control, real-time dispatch execution, or physical grid safety.
4. **No Human Operator Study:** The estimated operator workload reduction is derived from an analytical workload model; formal human-in-the-loop trials remain future work.
5. **Foundation Time-Series Models:** Benchmarking foundation time-series architectures (e.g., Chronos, TimesFM) alongside classical ML in the challenger pool remains future work.
