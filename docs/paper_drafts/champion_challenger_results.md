# Champion-challenger results (Phase 16, development/simulation)

All numbers come from the frozen Phase 16 protocol (`artifacts/experimental_design/phase_16_champion_challenger_protocol_freeze.yaml`) executed by `scripts/run_champion_challenger_simulation.py`. Everything is deterministic simulation; no deployment, production promotion, or final-test access occurred.

## Governance decisions

24 governed promotion decisions were evaluated: the 18 real registered Phase 15 challengers plus the six frozen scenarios CC01–CC06. Outcomes: 3 APPROVE (fixture scenarios), 21 REJECT, 0 DEFER. Scenario governance accuracy: **6/6 = 100%** (CC01 PROMOTED, CC02 REJECT, CC03 REJECT, CC04 REJECT, CC05 ROLLBACK_COMPLETED, CC06 ROLLBACK_BLOCKED).

## Unsafe promotions prevented despite superior appearance

14 of the 18 real challengers have strictly better MAE than their reference on their synthetic adaptation scenarios (relative improvements from +0.29% to +87.97%). **All 14 were rejected** — the four negative-gain challengers on the performance gate (`CHALLENGER_NOT_BETTER`), the fourteen superior ones on the benchmark gate (`BENCHMARK_REQUIREMENT_NOT_SATISFIED`), because synthetic-scenario superiority over a reference is not external development benchmark evidence (Phase 15 MD-045). Unsafe promotion attempts: 14; blocked: 14; **Unsafe Promotion Prevention Rate: 100%**. This is the central governance result: the framework prevents the intuitively tempting "promote the better-MAE model" action exactly as designed, mirroring the Phase 13 finding that internally best models are not automatically promotion-eligible.

## Frozen scenario evidence

- CC01 (better challenger, valid governance): APPROVE → canary passed (−5.0% regression) → PROMOTED (simulation). The only path to promotion runs through all 13 gates plus approval plus canary.
- CC02 (better challenger, invalid lineage): REJECT, `LINEAGE_INCOMPLETE` — superior MAE did not override provenance.
- CC03 (better challenger, benchmark failure): REJECT, `BENCHMARK_REQUIREMENT_NOT_SATISFIED`.
- CC04 (worse challenger): REJECT, `CHALLENGER_NOT_BETTER`.
- CC05 (promotion followed by degradation): the promoted fixture regressed +4.2% post-promotion; rollback was requested, restoration verified against the preserved reference artifact (artifact exists, fingerprint matches, lineage node present, model loads, outputs finite), and the previous reference was restored — ROLLBACK_COMPLETED.
- CC06 (rollback integrity failure): the preserved-record fingerprint was corrupted; verification failed on `fingerprint_matches` and the rollback was BLOCKED and audited rather than silently "restoring" an unverified model.

## Safety metrics

Automatic promotions: **0** — every MODEL_PROMOTED audit event is preceded by a PROMOTION_APPROVED event for the same subject (verified programmatically). Reference replacements outside simulation: 0. Rollback attempts: 2; successful: 1; blocked: 1. The Phase 13 lifecycle registry and Phase 15 challenger registry are byte-identical before and after Phase 16 (test-enforced); all promotion states live in the additive, simulation-scoped Phase 16 champion registry.

## Provenance and audit

Three real reference model artifacts were preserved (frozen specifications refit on pre-onset windows, identical to the Phase 15 REFERENCE_INFERENCE reconstruction) so rollback verification exercises actual model loading. The audit log gained Phase-16 events covering every evaluation, request, decision, canary, promotion, and rollback. Twenty-four native MLflow runs record reference_id, challenger_id, promotion decision, and the promotion policy fingerprint (`promotion-policy-v1:sha256:fe79bb...`).

## Scope discipline

Champion-Challenger: IMPLEMENTED. Promotion Policy: FROZEN (16.0.0, checksum `7b9cf08be7122b22302c8709a3a8cba16b2b0c827a498ccfdec88d8de1d56035`). This is governance-simulation evidence: the APPROVE path is exercised only by controlled fixtures, canary is a frozen guardrail rather than live traffic, and no production claim is made.
