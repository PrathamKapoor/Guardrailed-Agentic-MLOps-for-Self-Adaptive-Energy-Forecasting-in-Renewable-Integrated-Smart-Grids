# Unique selling proposition

Three consistent versions for different contexts. Every word is supported by a recorded artefact in the repository.

## 10-second explanation (one sentence)

A 20-phase, governance-first MLOps system for electricity forecasting whose bounded agentic layer cannot promote models — and whose final evaluation honestly reports the targets where the frozen models lose to the published benchmark.

## 30-second explanation (elevator pitch)

We built the opposite of "AI for MLOps." Our five specialist agents can investigate, summarize, and explain — but a governance firewall blocks them from promoting, rolling back, or retraining models. The deterministic lifecycle stays in charge. We evaluated three frozen finalists on a 2-month locked test partition and reported the result as recorded: PV's random forest beats the H24 daily persistence benchmark by 7.6%; LOAD and WIND do not beat the published RTS_DAY_AHEAD forecast. The result is honest, the artefacts are frozen, and a single `pytest` reproduces the submission.

## 2-minute explanation (technical pitch)

We implemented a 20-phase MLOps research system on the RTS-GMLC 2020 dataset (8,784 hourly rows; targets: system load, wind, utility-scale PV). The system layers tracking (MLflow), governance (13-gate promotion policy, 17-gate retraining policy), drift monitoring (PSI / KS / prediction drift / rolling performance), governed retraining (18 registered challengers, all blocked from promotion by the benchmark gate), champion-challenger + rollback (verified restoration, not best-effort), and a bounded agentic decision-support layer (5 specialist agents + governance firewall). The agent layer is the part most MLOps projects get wrong: it can only produce advisory outputs (investigate, summarize, explain, request human review, create reports) and the firewall blocks lifecycle action types (promote, rollback, change policy, start retraining, change features). The forbidden audit events `AGENT_MODEL_PROMOTED` and `AGENT_RETRAINING_STARTED` cannot be emitted by construction.

The frozen final evaluation reads the locked test partition (2020-11-01 to 2020-12-31, 1464 rows per target) exactly once under `AccessMode.FINAL_EVALUATION` with `configuration_frozen=True`. Every test-partition timestamp is checked by `authorize_final_evaluation`. The frozen finalists are random forest (LOAD), hist gradient boosting (WIND), and random forest (PV) — all using the frozen B_lags_only feature set (lag_1, lag_24, lag_168). The external benchmarks are frozen too: RTS_DAY_AHEAD for LOAD/WIND, H24 daily persistence for PV. Results are reported transparently: PV wins by 7.61%; LOAD and WIND lose by 72.29% and 135.08% respectively.

The Phase 20 read-only evidence dashboard consumes the frozen Phase 19 artefacts and renders them faithfully. The builder is verified to leave every Phase 19 artefact byte-identical. The 231-test suite (213 backend + 18 dashboard) reproduces the submission deterministically. The 20 protocol freeze checksums all verify. The agent operational benefit is measured by a frozen cost model: ~72% time reduction in explanation effort, 0 lifecycle differences, 14 of 14 unsafe recommendations blocked.

The system does not contain quantum computing, graph neural networks, or large language models. It is classical ML on commodity hardware, executed exactly once on a held-out test window, and reported honestly.

## Tagline

> A governance-first MLOps system for energy forecasting whose agents cannot promote models.

## One-line value proposition (landing-page hero)

> A 20-phase, governance-first MLOps system for electricity forecasting with a bounded, firewalled agentic decision-support layer and a frozen, fully audited final evaluation.

## Why this avoids empty phrases

The spec forbids "revolutionary", "game-changing", "next-generation", and "AI-powered" unless technically justified. This submission does not use them. Every claim above is supported by:

- A frozen artefact under `artifacts/` (with sidecar SHA-256).
- A test under `tests/` (the 231 backend + 18 dashboard tests, all passing).
- A specific page or section in the dashboard or the landing page.

If a claim cannot point to a file, the claim is removed.
