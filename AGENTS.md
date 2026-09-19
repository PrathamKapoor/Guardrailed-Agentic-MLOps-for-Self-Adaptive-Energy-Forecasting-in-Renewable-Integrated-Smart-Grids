# Repository Instructions

## Project mission

This repository develops a research implementation for MLOps-driven forecasting of electricity demand and renewable generation in smart grids. It investigates whether bounded Agentic AI can reduce manual lifecycle work while deterministic controls and human oversight retain authority over critical model decisions.

## Workspace boundary

Agents and Codex may modify files only inside `guardrailed-agentic-mlops-smart-grid/`. Do not alter parent-workspace projects or use their files as project inputs unless they are explicitly copied into this repository under an approved workflow.

## Dataset policy

Only use explicitly approved datasets. Never silently substitute a different dataset. Record the dataset source, license, retrieval date, version, schema, and approval in `data/manifests/` before it is used in an experiment.

## Data leakage policy

Future observations must never leak into past training periods. All splitting must respect time. Feature creation, normalization, imputation, and target transformations must be fit using training-period data only and then applied forward.

For RTS-GMLC, the actual CSV timestamp values override contradictory documentation examples. PV and rooftop-PV nighttime zero generation is valid observed behavior, not missingness by itself.

## Forecasting policy

Never use random train/test splitting for time-series forecasting. Use chronological holdout, rolling-origin, or walk-forward evaluation as appropriate, with all timestamps and forecast horizons documented.

RTS-GMLC DAY_AHEAD series are external forecast baselines, not default ML features. They may be used as model inputs only for an explicitly declared forecast-correction or residual-modelling experiment.

Feature scaling must occur inside a future training pipeline fitted only on training data; never globally scale canonical feature matrices.

The final test set must remain untouched during feature selection, model selection, architecture selection, hyperparameter optimization, early stopping, threshold tuning, and agent recommendations. Development decisions may use only training and validation data or pre-test rolling-origin folds. Final-test targets may be accessed only in an explicitly authorized final-evaluation mode after the candidate configuration is frozen.

## Reproducibility

For every experiment, record random seeds, dataset version, preprocessing version, feature version, model version, hyperparameters, library versions, and commit hash where available. Store these with the experiment artifact and phase report.

## Experimental integrity

Never fabricate experimental results, accuracy values, dataset characteristics or model improvements.

Research sources are inspiration only. Do not copy their methodology or prose, treat papers as datasets, copy results, or claim reproduction unless independently established by recorded experiments.

## Agent authority

No LLM or autonomous agent may bypass the deterministic model-governance policy engine.

Agent recommendations are advisory until they satisfy deterministic validation gates.

Agent capabilities are bounded by a governance firewall: only advisory recommendation types (investigate, summarize, explain, request human review, create report) may pass. Lifecycle action types (promote, rollback, change policy, start retraining, change features) are blocked and audited. Agents never store chain-of-thought, private reasoning traces, or prompts; agent memory holds structured summaries and evidence references only.

Drift detection is observational evidence and must not directly trigger model retraining, promotion, rollback, or lifecycle transition. Such actions require a separately governed policy decision.

Model retraining must never be invoked directly by a drift alert. Retraining requires a separately evaluated deterministic retraining policy (request schema, eligibility gates, ALLOW/DENY/DEFER decision, bounded job) whose frozen specification is recorded before official execution.

Retrained models enter the lifecycle as REGISTERED_CHALLENGER and must never replace a reference or champion automatically; promotion eligibility is decided only by the separately governed champion-challenger evaluation, never by retraining success.

Retraining must preserve the frozen model family, hyperparameters, feature specification, scaling policy, and deterministic seed policy. Hyperparameter optimization, feature selection, and model-family search during retraining are forbidden unless a separately approved experiment authorizes them.

Final-test data may never be used to trigger, train, evaluate, or select retraining. No historical integrity-audit exception authorizes retraining access to final-test data.

Champion promotion must never follow from superior model metrics alone. Every promotion requires a separately evaluated deterministic promotion policy (registration, lineage, fingerprint, protocol, metadata, evaluation, performance, benchmark, statistical, and approval gates) plus a passing canary stage; a model that only looks better must be rejected.

Rollback is mandatory infrastructure: the previous model must remain preserved and recoverable (artifact, fingerprint, lineage, loadability) before any promotion takes effect, and restoration must be verified before a rollback completes. A rollback whose verification fails must be blocked and audited.

Production-style champion replacement requires explicit approval unless the system is running in an explicitly configured simulation/demo environment.

## Model governance

Being the best internally trained model does not make a model promotion-eligible. Promotion eligibility must be evaluated independently against predefined benchmark, validity, provenance, and governance gates.

Every governed model change follows:

`Candidate → Validation → Challenger → Champion comparison → Policy gate → Human approval / simulation approval → Canary → Promotion`

Rollback is mandatory: a previous champion must remain recoverable, together with its model artifact, metadata, validation evidence, and deployment configuration.

## Testing

No phase is complete without tests. Tests must be run and their exact commands and outcomes recorded in that phase's completion report.

## Phase workflow

Future Codex sessions must:

1. Read `AGENTS.md`.
2. Read previous phase reports in `reports/`.
3. Inspect the existing implementation.
4. Extend rather than rewrite working components.
5. Run relevant tests.
6. Write a completion report before declaring a phase complete.
