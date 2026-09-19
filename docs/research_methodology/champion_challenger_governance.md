# Champion-challenger evaluation, governed promotion, and rollback

## Research Objective

Phase 16 designs and evaluates a deterministic champion-challenger governance framework capable of selecting, approving, rejecting, promoting, and rolling back forecasting models while preventing unsafe autonomous model replacement (RQ-CC-1..RQ-CC-4). Hypotheses H-CC-1..H-CC-4 predict reproducible challenger evaluation, prevention of unsafe promotions despite superior appearance, verified rollback restoration, and deterministic auditable transitions. Phase 15 answered "can the system safely create challengers"; Phase 16 answers "can the system safely decide whether a challenger should replace the reference".

## Architecture

`REGISTERED_REFERENCE → CHALLENGER EVALUATION → GOVERNANCE POLICY → APPROVE / REJECT / DEFER → CANARY SIMULATION → ACTIVE MODEL (PROMOTED, SIMULATION)` with the rollback path `ACTIVE MODEL → degradation detected → ROLLBACK REQUEST → verified restoration of the previous model`. Implementation: `src/smartgrid_mlops/champion_challenger/` (schemas, evaluation, comparison, policy, promotion, canary, rollback, registry, events, simulation, validation), reusing Phase 13 governance identities, the Phase 15 challenger registry, and Phase 12 MLflow lineage and audit infrastructure. Everything is deterministic; no agents or LLMs exist yet.

## Promotion Policy

`config/governance/phase_16_promotion_policy.yaml` (16.0.0) freezes thirteen ordered gates: policy version, final-test, registration, lineage, model fingerprint, feature fingerprint, protocol, metadata, evaluation, performance, benchmark, statistical evidence, and approval. Promotion requires all of: challenger registered, complete lineage, valid fingerprints, no protocol violations, completed evaluation, satisfied benchmark requirements, and governance approval. **Improved MAE alone is not sufficient**: the performance gate demands strict matched-timestamp MAE improvement, but the benchmark gate additionally requires external development benchmark evidence, which synthetic-scenario superiority cannot provide (Phase 15 MD-045). Missing approval DEFERs; rejected approval or any hard-gate failure REJECTs. Approval in simulation is the explicitly labelled `SIMULATION_POLICY` actor, never human approval.

## Challenger Evaluation

Every evaluation compares the frozen reference against one challenger on identical timestamps, target, feature representation, and protocol, with MAE primary and RMSE/sMAPE/nMAE/nRMSE secondary (minimum 336 matched rows). Evaluation is metadata-level and reproducible; no model is refitted and no final-test data is read.

## Canary Simulation

Canary is simulation only — no deployment exists. After a governed APPROVE, the challenger must pass a frozen zero-regression guardrail on the canary window; failure emits CANARY_FAILED and rolls the challenger back before activation, leaving the reference unchanged. Simulation lifecycle states map onto the frozen Phase 13 states (APPROVED_FOR_CANARY, CANARY_ACTIVE, ACTIVE); the Phase 13 lifecycle registry itself is never modified.

## Rollback

Before any promotion takes effect, the previous reference model is preserved as a real loadable artifact with its specification fingerprint and lineage node (the runner refits each frozen reference specification on its pre-onset window — identical to the Phase 15 REFERENCE_INFERENCE reconstruction — and saves it). Post-promotion monitoring triggers a rollback request when matched-window MAE regression versus the preserved previous model exceeds the frozen 0.0% threshold. Restoration verification requires: artifact exists, fingerprint matches, lineage node exists, model loads, and predictions are finite. A verified rollback completes and restores the previous model (simulation-scoped ACTIVE); a failed verification is BLOCKED and audited (ROLLBACK_BLOCKED).

## Registry Integration

Promotion outcomes are recorded in the additive, simulation-scoped `artifacts/model_registry/phase_16_champion_registry.yaml` (promotions, rollbacks, preserved models, restored-reference states). The authoritative Phase 13 lifecycle registry and the Phase 15 challenger registry remain byte-identical; tests verify this. No production, deployment, or serving claim is made.

## Auditability and MLflow

The append-oriented audit log gains CHALLENGER_EVALUATED, PROMOTION_REQUESTED, PROMOTION_APPROVED/REJECTED/DEFERRED, CANARY_STARTED, CANARY_FAILED, MODEL_PROMOTED, ROLLBACK_REQUESTED, ROLLBACK_COMPLETED, and ROLLBACK_BLOCKED. Every MODEL_PROMOTED event is preceded by a PROMOTION_APPROVED event for the same subject — promotions without governed approval are structurally impossible. Every evaluation and scenario decision is a native MLflow run (experiment `phase16/champion_challenger`) with reference/challenger IDs, promotion decision, and the promotion policy fingerprint.

## Final-Test Isolation

No Phase 16 code path reads final-test data; requests asking for it REJECT with FINAL_TEST_POLICY_VIOLATION. PHASE_16_NEW_FINAL_TEST_READS = 0; the historical P9-DEV-002 integrity exception remains historical only.

## Limitations

Promotion fixtures are metadata-only constructs with declared valid benchmark and approval evidence; no real challenger is promotable because synthetic-scenario superiority is not benchmark evidence. The canary stage replays frozen guardrails rather than live traffic; degradation signals are fixtures; approval is not integrated with organizational IAM; promotion states are simulation-scoped; and no deployment, serving latency, or operational cost is evaluated.
