# -*- coding: utf-8 -*-
"""Rewrite docs/paper/*.md honestly: remove quantum contamination, align with
the real artifacts (RTS-GMLC, frozen results, Phase 13 governance, 7/7 DENY)."""
import io, os

D = r"C:\Projects\guardrailed-agentic-mlops-smart-grid_trial\docs\paper"

FILES = {}

FILES["title.md"] = (
    "Guardrailed Agentic MLOps for Self-Adaptive Energy Forecasting in Renewable-Integrated Smart Grids"
)

FILES["abstract.md"] = """Renewable energy integration introduces variability and forecasting challenges that complicate grid operations. Traditional MLOps pipelines lack the governance required for safe operation in safety-critical smart grid applications. This work presents a guardrailed agentic MLOps system for energy forecasting in renewable-integrated smart grids, in which a bounded, deterministic agent layer assists lifecycle work while every lifecycle decision is made by a deterministic governance engine. The system is evaluated on the RTS-GMLC dataset (8,784 matched hourly observations per target for calendar year 2020; system load, aggregate wind, and utility-scale PV) under a strictly chronological, protocol-frozen partitioning with a sealed final-test window (November 1 to December 31, 2020; 1,464 hours). On the frozen final-test partition, the load random forest reached MAE 174.26 MW against the published day-ahead reference of 101.14 MW (+72.3%), the wind hist-gradient-boosting candidate reached 778.84 MW against 331.30 MW (+135.1%), and only the PV random forest beat its persistence benchmark (36.12 vs. 39.09 MW; -7.6%). A separately authorized residual-correction study reduced load MAE to 1.54 under five-fold chronological validation, yet the governance engine denied all seven packaged candidates for fingerprint, lineage, protocol, and evidence deficiencies - demonstrating that superior offline metrics alone do not confer promotion eligibility. All agent capabilities are advisory (five allowed recommendation types; seven lifecycle action types blocked and audited), drift monitoring is observational only, and the full evidence trail is recorded in an append-only JSONL ledger."""

FILES["introduction.md"] = """The integration of renewable energy sources into smart grids exacerbates forecasting challenges due to the inherent variability and uncertainty of generation from sources like wind and solar. Accurate forecasting is critical for grid stability, economic dispatch, and renewable energy curtailment reduction. However, operationalizing machine learning (ML) forecasting models in power systems introduces unique risks: model drift, data quality issues, and the potential for unsafe automated decisions that could compromise grid reliability.

Traditional MLOps pipelines focus on automation and scalability but often lack sufficient governance mechanisms for safety-critical domains. Agentic AI approaches, while promising for automation, may introduce uncontrolled behaviors if not properly bounded. This paper addresses the gap by proposing a guardrailed agentic MLOps framework that enforces deterministic governance over agentic actions, ensuring that automation enhances rather than endangers grid operations.

We contribute a governance-first MLOps platform specialized for energy forecasting, featuring: (1) a leakage-safe, strictly chronological evaluation protocol over the RTS-GMLC dataset, with checksummed data manifests and a protocol-frozen final-test partition that is sealed during all development decisions; (2) a bounded, deterministic agent layer in which five advisory recommendation types are permitted and seven lifecycle action types are structurally blocked and audited - no large language model is used, by design; (3) a deterministic governance engine that evaluates candidate evidence through 12 ordered gates of a 13-state lifecycle machine, producing ALLOW, DENY, or REQUIRE_APPROVAL decisions sealed with SHA-256 fingerprints; and (4) an honest empirical account in which negative benchmark outcomes (load and wind candidates losing to the published day-ahead forecasts) and a denied promotion of a strongly improving residual-correction candidate are reported as-is. The system is deliberately offline: there is no live telemetry, streaming, or production deployment, and no quantum, GNN, or LLM component is claimed.

The remainder of the paper is structured as follows: Section 2 reviews related work; Section 3 details the system architecture; Section 4 describes the experimental setup; Section 5 presents results; Section 6 discusses implications; Section 7 outlines limitations; Section 8 concludes."""

FILES["related_work.md"] = """Related work spans three areas: (1) MLOps for reliable ML deployment, (2) agentic AI for automation, and (3) energy forecasting in smart grids.

MLOps practices focus on automating the ML lifecycle, including data validation, model training, deployment, and monitoring [1]. However, traditional MLOps often lacks formal governance for safety-critical systems. Recent work introduces MLOps for healthcare [2] and autonomous vehicles [3], emphasizing model cards, provenance, and human-in-the-loop checks. Our work extends these principles to energy forecasting, adding a deterministic governance engine with ordered evaluation gates and a tamper-evident, append-only audit ledger.

Agentic AI systems frequently use LLM-based agents to automate complex tasks [4,5]. In ML, agents have been proposed for hyperparameter tuning [6] and pipeline orchestration [7]. However, unbounded agents risk unsafe actions in critical domains, and LLM-driven behavior is inherently non-deterministic. We therefore adopt a deliberately deterministic, rule-based agent implementation that realizes the bounded-agency paradigm [8]: the agent layer produces structured, evidence-referenced advisory outputs within strict policy constraints, and its memory holds structured summaries only - never reasoning traces. This is a design choice, not a limitation of integration: non-deterministic model backends are excluded so that every agent action remains reproducible and auditable.

Energy forecasting has evolved from statistical methods to ML and deep learning [9,10]. Renewable variability necessitates probabilistic and adaptive forecasts [11]. MLOps for energy forecasting remains underexplored; existing works focus on accuracy improvements rather than deployment safety [12]. Our system fills this gap by providing a governance-driven MLOps framework tailored to grid-integrated forecasting, where model integrity and action safety are paramount, and where published day-ahead forecasts serve as strong external benchmarks that internal candidates must honestly beat.

[1] Sculley et al., "Hidden technical debt in machine learning systems," NeurIPS, 2015.
[2] Rajkomar et al., "Scalable and accurate deep learning with electronic health records," PLOS Medicine, 2018.
[3] Bojarski et al., "End to end learning for self-driving cars," arXiv, 2016.
[4] Wang et al., "HuggingGPT: Solving AI tasks with chatGPT and its friends in huggingface," arXiv, 2023.
[5] Yao et al., "Tree of thoughts: Deliberate problem solving with large language models," NeurIPS, 2023.
[6] Feurer et al., "Efficient and robust automated machine learning," NeurIPS, 2019.
[7] Zeng et al., "AgentTuning: Enabling generalized agent abilities for LLMs," arXiv, 2023.
[8] Hadfield-Menell et al., "The off-switch game," arXiv, 2016.
[9] Hong and Fan, "Probabilistic electric load forecasting: A tutorial review," International Journal of Forecasting, 2016.
[10] Liu et al., "A review of deep learning applications in renewable energy forecasting," Renewable Energy, 2019.
[11] Noorollahi et al., "A review on wind power forecasting models," Renewable and Sustainable Energy Reviews, 2019.
[12] Zhang et al., "Optimizing short-term wind power forecasting using deep learning," Energy, 2020."""

FILES["system_architecture.md"] = """The system architecture consists of five layers.

1. **Data and Feature Layer** (foundation): Ingests approved datasets only - each dataset is registered in a manifest recording its source, license, retrieval date, version (SHA-256 checksums of every source file), schema, and approval status before first use. Feature construction is strictly backward-looking (lag blocks at 1, 24, and 168 hours; cyclic calendar encodings; rolling statistics), with scaling fitted inside training pipelines only.

2. **Forecasting Layer**: Frozen finalist models per target - random forest and multi-layer perceptron for load and PV, histogram gradient boosting for wind - trained with fixed random seeds under a resource-constrained model competition. Published day-ahead forecasts and persistence baselines are treated as external benchmarks and are never used as features except in an explicitly declared residual-correction experiment.

3. **Monitoring Layer**: Historical replay in weekly windows with a one-day stride computes the population stability index (PSI), a normalized Wasserstein distance, and a rolling MAE performance signal against reference blocks. Thresholds are calibrated as the 99th percentile of reference statistics and frozen. Severity is classified as NONE, WATCH, WARNING, or CRITICAL. Monitoring is observational evidence only: alerts never directly trigger retraining, promotion, or rollback.

4. **Bounded Agentic Layer**: A deterministic, rule-based agent layer (implemented by the LocalRuleBackend) produces evidence-referenced advisory findings across pipeline roles: data validation, performance analysis, security checks, governance review, and red-team style probes. A capability firewall permits exactly five advisory recommendation types (INVESTIGATE, SUMMARIZE, EXPLAIN, REQUEST_HUMAN_REVIEW, CREATE_REPORT) and structurally blocks seven lifecycle action types (PROMOTE, DEPLOY, ROLLBACK, RETRAIN, CHANGE_POLICY, MODIFY_MODEL, MODIFY_FEATURES); blocked actions are returned and audited rather than executed. Agent memory stores structured summaries and evidence references only - never chain-of-thought or private reasoning traces. No LLM component is used.

5. **Governance and Audit Layer**: A deterministic policy engine (frozen Phase 13 policy) evaluates candidate evidence through 12 ordered gates of a 13-state lifecycle machine - registration, lineage, model- and feature-specification fingerprints, protocol compatibility, metadata, evaluation, performance, benchmark comparison, statistical evidence, and approvals - yielding one of 16 reason codes per failed gate. Decisions are ALLOW, DENY, or REQUIRE_APPROVAL, each sealed with a SHA-256 decision fingerprint. Champion promotion additionally requires a passing canary stage, and rollback of the previous champion is mandatory, preserved, and verified. Every event is recorded in an append-only JSONL audit ledger.

**Authority model**: The agent can analyze and advise; the governance engine decides. Drift observations, agent recommendations, and superior offline metrics are all advisory inputs - none can bypass the deterministic policy. Human approval is a required gate for production-style champion replacement outside explicitly configured simulation environments."""

FILES["experimental_setup.md"] = """**Dataset**: We use the RTS-GMLC (Reliability Test System - Grid Modernization Lab Consortium) dataset published by the U.S. National Renewable Energy Laboratory. The archive was acquired by ZIP download on 2026-08-13 with its checksum recorded; six source time-series files (day-ahead and real-time regional load, wind, and PV) were ingested with per-file SHA-256 checksums verified before and after processing. Native-resolution series were aligned and aggregated to hourly resolution, yielding 8,784 matched hourly observations per target for calendar year 2020 with zero unmatched entries and zero missing values. PV nighttime zeros (46.4% of hours) are observed behavior and are retained.

**Targets**: Three forecasting targets are considered:
- Load (electricity demand)
- Wind (wind power generation)
- PV (utility-scale solar photovoltaic generation)

**Forecast Horizon**:
- Primary: H24 (24-hour ahead forecast)
- Secondary: H1 (1-hour ahead forecast) - for agentic adaptation studies

**Models**:
- Load: Random Forest with B_lags_only feature set (lagged load values)
- Wind: HistGradientBoosting with B_lags_only feature set (lagged wind values)
- PV: Random Forest with B_lags_only feature set (lagged PV values)
All models are frozen finalists from the Phase 11 finalist selection, representing the best-performing models under resource constraints.

**Features**:
- B_lags_only: contains only lagged values of the target variable (e.g., load(t-1), load(t-2), ..., load(t-168) for weekly seasonality).
- No exogenous features are used, to isolate the forecasting capability of the autoregressive structure. The published day-ahead series is an external benchmark, never a feature, except in the explicitly declared Stage 10 residual-correction experiment.

**Evaluation Metrics**:
- Primary: Mean Absolute Error (MAE)
- Secondary: RMSE, sMAPE, nMAE, nRMSE.
Metrics are computed on the locked final-test partition, November 1 to December 31, 2020 (1,464 hours) - a chronological holdout sealed behind the Phase 19 experimental-design protocol freeze, not a random 20% split.

**Experimental Protocol**:
1. Load frozen registered models for each target.
2. Load actual values and feature rows for the final-test partition from the artifact store.
3. Generate predictions using the frozen models on the feature rows.
4. Compute metrics by aligning predictions with actual values via timestamps.
5. Save predictions to artifacts/final_evaluation/ and aggregate metrics to artifacts/research_tables/.
6. Conduct integrity verification to confirm no modifications to models, features, or governance policies.

**Reproducibility**:
- Environment: Python (see requirements.txt); scikit-learn with fixed random seeds (seed 42 where stochastic).
- Execution: the final-evaluation entry point at the repository root (run_final_evaluation.py), which is inference-only.
- Data and model fingerprints are recorded in the lineage report (reports/phase_19_final_lineage_report.md)."""

FILES["results.md"] = """The final evaluation executed successfully, generating forecasts and metrics for all three targets using the frozen registered models. No retraining, hyperparameter optimization, feature selection, or model selection occurred during evaluation, per the inference-only final-test protocol.

**Forecasting Results** (frozen final-test partition, Nov 1 - Dec 31, 2020):

| Target | Model | MAE | RMSE | sMAPE | nMAE |
|---|---|---|---|---|---|
| Load | Random forest | 174.26 | 231.27 | 4.72 | 0.0474 |
| Load | MLP | 281.00 | 343.36 | 7.78 | 0.0764 |
| Load | Day-ahead (published) | 101.14 | 101.85 | 2.72 | 0.0275 |
| Wind | Hist. gradient boosting | 778.84 | 923.37 | 92.40 | 0.6790 |
| Wind | MLP | 838.40 | 957.93 | 96.13 | 0.7309 |
| Wind | Day-ahead (published) | 331.30 | 491.21 | 50.92 | 0.2888 |
| PV | Random forest | 36.12 | 82.08 | 117.73 | 0.1082 |
| PV | MLP | 221.64 | 249.27 | 135.47 | 0.6637 |
| PV | H24 persistence | 39.09 | 100.69 | 7.86 | 0.1171 |

**Benchmark Gate Outcomes**: Only the PV random forest satisfies its benchmark gate (36.12 vs. 39.09 MW persistence, -7.6%). The load candidate is +72.3% worse than the published day-ahead forecast and the wind candidate is +135.1% worse. These negative outcomes are reported as measured; no configuration was re-tuned against the test partition after unsealing.

**Residual-Correction Research (Stage 10)**: In a separately authorized forecast-correction experiment, ridge and histogram-gradient-boosting correctors were trained on leakage-safe residual features (day-ahead value at the target hour, cyclic calendar features, lagged residuals at 1/24/168 h). The best candidate reduced load MAE to 1.54 on held-out validation under a five-fold chronological scheme with zero detected leakage - an approximately 98.5% reduction relative to the day-ahead reference MAE of 101.14. Because this result depends on the day-ahead series as an input feature, it defines a forecast-correction experiment, not a standalone forecaster.

**Governance Evaluation (Stages 12 and 14)**: All seven packaged candidates were DENIED by the deterministic governance engine. Recurring reason codes include MODEL_SPEC_FINGERPRINT_MISMATCH, FEATURE_SPEC_FINGERPRINT_MISMATCH, PROTOCOL_MISMATCH, and EVIDENCE_INVALID; earlier audit probes also surfaced BENCHMARK_GATE_FAILED, STATISTICAL_EVIDENCE_FAILED, LINEAGE_INCOMPLETE, REPRODUCIBILITY_INCOMPLETE, UNRESOLVED_DEVIATION, and INVALID_STATE_TRANSITION. The strong residual-correction result was therefore prevented from entering the lifecycle as a promoted model: superior metrics alone do not confer promotion eligibility.

**Governance and Agentic Behavior**: All agent operations were advisory and bounded; no lifecycle action was executed by an agent. Every decision and blocked recommendation is recorded with SHA-256 fingerprints in the append-only audit ledger.

Detailed prediction timestamps and errors are available in artifacts/final_evaluation/final_predictions.csv. Aggregated metrics are available in artifacts/research_tables/final_forecasting_results.csv and artifacts/research_tables/final_model_comparison.csv."""

FILES["discussion.md"] = """The guardrailed agentic MLOps framework demonstrates that automation and governance can coexist in safety-critical ML forecasting systems. By bounding agentic actions within deterministic governance constraints, the system enables adaptive behaviors (governed retraining, rollback) only when separately evaluated safety conditions are met. This addresses a key limitation of fully autonomous agentic systems, which may inadvertently compromise system integrity.

**Strengths**:
- Cryptographic model provenance (SHA-256 model, feature, and decision fingerprints) ensures end-to-end traceability of the forecasting pipeline.
- The append-only JSONL evidence ledger provides reproducible audit trails suitable for regulatory review in energy markets.
- Bounded, deterministic agents reduce operational overhead while making unsafe actions structurally impossible rather than merely discouraged.
- The governance engine's ordered gates make promotion decisions inspectable: every denial carries a machine-readable reason code.

**Weaknesses**:
- The internal models lose to the published day-ahead forecasts on two of three targets (load +72.3%, wind +135.1% on MAE). Internal ML candidates do not yet add value over the operational reference for load and wind.
- Residual correction against the day-ahead series is powerful (load MAE 1.54) but defines a correction experiment dependent on that external input; its evidence was denied by governance, so it remains research-grade.
- The governance policy is versioned code (frozen Phase 13 policy); a declarative policy language would ease evolution, at the cost of the current simplicity and auditability.
- Evaluation is offline on a single dataset year; no live deployment, streaming telemetry, or production dispatch decision is involved.

**Implications**:
For grid operators and platform teams, the system provides a governance-first foundation for deploying ML-based forecasting: forecasts are not only scored but gated, and every lifecycle claim is verifiable against fingerprints and an append-only ledger. The honest negative benchmark results are themselves informative: they quantify how strong published day-ahead forecasts are, and they demonstrate that the platform reports failures rather than hiding them. The open research package enables reproducibility and collaboration in the energy MLOps community, advancing trustworthy ML practice for critical infrastructure."""

FILES["limitations.md"] = """The following limitations apply to the research presented:

1. **Single Dataset**: Evaluation was conducted on the RTS-GMLC dataset; generalization to real-world utility data remains untested. An external validation on German OPSD data showed the frozen models transfer poorly (all three significantly worse than simple persistence), underscoring this limitation.
2. **Limited Temporal Coverage**: The dataset spans one year (2020); multi-year seasonal extremes and rare events (e.g., storms) are not represented.
3. **Negative Benchmark Results on Two of Three Targets**: The load and wind candidates are substantially worse than the published day-ahead forecasts (+72.3% and +135.1% MAE respectively). The platform reports this honestly rather than tuning against the test partition; improving internal load/wind forecasters remains future work.
4. **Simulated Drift**: Drift monitoring was exercised by historical replay; long-term live drift adaptation is unvalidated. Monitoring is observational by design and never triggers lifecycle actions directly.
5. **No Production Grid Deployment**: The system has not been deployed in an operational smart grid; all results are from offline evaluation. There is no live telemetry, streaming, or real-time inference path.
6. **No Human Operator Study**: The agent-governance interaction was not evaluated with human operators; usability and trust effects are unknown.
7. **Bounded Agent Scope**: Agent capabilities are deterministic and advisory only (five recommendation types); open-ended agentic behaviors are excluded by design, and no LLM backend is integrated.
8. **External Benchmark Dependency**: Benchmark comparisons rely on the published RTS day-ahead series and persistence references, treated as external baselines rather than reproducible internal models.
9. **Governance Denials Not Yet Closed**: All seven packaged candidates were denied for fingerprint, lineage, protocol, and evidence deficiencies; a full ALLOW path with canary execution and verified rollback remains to be demonstrated end-to-end.
10. **Policy Language Expressiveness**: The frozen governance policy is versioned code; adapting to evolving regulatory requirements requires a new governed policy version rather than runtime configuration.

These limitations delineate the scope of the claimed contributions and identify avenues for future work."""

FILES["conclusion.md"] = """This work introduces a guardrailed agentic MLOps framework for self-adaptive energy forecasting in renewable-integrated smart grids. By coupling deterministic governance with a bounded, deterministic agent layer, the system achieves governed automation across the forecasting lifecycle - from checksummed data provisioning to candidate evaluation - without compromising integrity or safety.

Key contributions include:
- A leakage-safe evaluation protocol over the RTS-GMLC dataset: checksummed manifests, census sampling of 8,784 matched hourly observations per target, strictly chronological partitions, and a sealed 1,464-hour final-test window behind a protocol freeze.
- A bounded agent layer in which five advisory recommendation types are permitted and seven lifecycle action types are structurally blocked and audited, with memory restricted to structured summaries and evidence references.
- A deterministic governance engine (13-state lifecycle, 12 ordered gates, 16 reason codes, SHA-256 decision fingerprints) that denied all seven packaged candidates - including one whose residual-correction research result reduced load MAE to 1.54 - because formal evidence deficiencies outweigh superior offline metrics.
- An honest empirical account: the PV candidate beat its persistence benchmark (-7.6%) while the load and wind candidates lost to the published day-ahead forecasts (+72.3% and +135.1% MAE), and these outcomes are reported without post-hoc tuning.

The results support a governance-first conclusion: strong research metrics do not confer promotion eligibility, and bounded agent authority - advisory analysis under a capability firewall - is a practical architecture for research-grade MLOps in critical energy infrastructure.

Future work will focus on closing the ALLOW path (canary execution and verified rollback), improving internal load and wind forecasters honestly, external-dataset validation, and extending renewable-utilization analytics (load-matching and surplus-energy characterization) under the same advisory-only constraints."""

FILES["reproducibility.md"] = """**Environment**:
- Operating System: Windows (development and execution environment)
- Python: see requirements.txt for pinned dependencies (scikit-learn, pyarrow, mlflow, fastapi, uvicorn, etc.)
- Execution: final evaluation entry point at the repository root (run_final_evaluation.py); phase pipelines under scripts/ with recorded commands in each phase completion report.

**Dataset**:
- Source: RTS-GMLC (Reliability Test System - Grid Modernization Lab Consortium), National Renewable Energy Laboratory. Acquired by ZIP download on 2026-08-13; archive checksum recorded in data/manifests/rts_gmlc_manifest.yaml.
- Processing: six source time-series files (day-ahead/real-time x load/wind/PV) ingested with per-file SHA-256 checksums recorded before and after processing (source_unchanged: true in data/manifests/processed_dataset_manifest.yaml, dataset_version rts_gmlc_processed_v1).
- Coverage: 8,784 matched hourly observations per target for calendar year 2020; zero missing values; PV nighttime zeros (46.4%) retained as observed behavior.
- Final-test partition: November 1 to December 31, 2020 (1,464 hours), sealed by artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml.

**Model Fingerprints**:
- Frozen finalists from Phase 11 (load: random forest, wind: histogram gradient boosting, PV: random forest; B_lags_only feature set), registered with lineage and evaluated once on the sealed partition in Phase 19.

**Feature Fingerprints**:
- B_lags_only: lagged values of the target variable (lags 1, 24, 168 and related blocks); deterministic given the dataset; digests recorded in the lineage report.

**Experiment Protocols**:
1. Data loading from checksummed artifacts (never regenerated).
2. Model loading from the registry (frozen finalists).
3. Inference-only prediction on the sealed final-test partition.
4. Metric computation (MAE, RMSE, sMAPE, nMAE, nRMSE) aligned by timestamp.
5. Artifacts: artifacts/final_evaluation/final_predictions.csv; artifacts/research_tables/final_forecasting_results.csv and final_model_comparison.csv.
6. Lineage reporting in reports/phase_19_final_lineage_report.md.
7. Final-test access record: confirms no training, HPO, feature selection, model selection, or retraining occurred after the protocol freeze.

**Random Seeds**:
- Fixed seed 42 where stochastic (documented in the Phase 19 protocol freeze as seed_hard_coded_in_implementation); frozen models are deterministic at inference.

**Integrity Verification**:
- Post-execution checks confirm models, features, and governance policies are unchanged ("Lineage: PASS", "Governance: UNCHANGED"), and the append-only audit ledger records the evaluation events.

**Notes on Reproducibility**:
- All inputs are checksummed repository artifacts; no synthetic substitution occurs. Research extensions (Stages 07-14 and the live research console) similarly operate on checksummed or user-registered (manifest-documented) datasets only, with chronological splits and no lifecycle mutation."""

for name, content in FILES.items():
    path = os.path.join(D, name)
    io.open(path, "w", encoding="utf-8", newline="\n").write(content + "\n")
    print("rewrote", name)
print("done")
