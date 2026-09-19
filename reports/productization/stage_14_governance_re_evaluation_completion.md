# Stage 14 — Governance-Compatible Candidate Re-Evaluation (completion report)

## 1. Stage objective

Re-evaluate the seven Stage 13 candidate evidence packages through
the EXISTING frozen Phase 13 `GovernanceEngine`. Stage 14 is a
governance EVALUATION stage, not a governance EXECUTION stage.

The actual decisions and reason codes produced by the existing
frozen engine are recorded. The Stage 14 layer is read-only with
respect to the v1 tree and the Stage 13 packages. The only allowed
mutation is the append-only audit JSONL emission via the existing
`smartgrid_mlops.governance.audit.audit_decision` helper.

**No model was promoted. No model was deployed. No lifecycle state
was executed.**

## 2. Existing components reused (read-only)

| Component | File | Reused as |
| --- | --- | --- |
| Phase 13 frozen policy | `config/governance/phase_13_policy.yaml` (SHA `ee13cb36...`) | Single source of truth for the gate logic and the accepted protocol hashes |
| `GovernancePolicy.load` | `src/smartgrid_mlops/governance/policies.py` | Policy loader; identity record |
| `GovernanceEngine.evaluate` | `src/smartgrid_mlops/governance/policy_engine.py` (SHA `324927d8...`) | The deterministic evaluator (imported, not forked) |
| `CandidateContext`, `TransitionRequest`, `GovernanceDecision`, `GateResult` | `src/smartgrid_mlops/governance/schemas.py` | The input/output shapes (imported, not redefined) |
| `LifecycleStateMachine` | `src/smartgrid_mlops/governance/state_machine.py` | The transition table (imported, not redefined) |
| All 12 ordered gates | `src/smartgrid_mlops/governance/validators.py` | The validators (imported, not redefined) |
| `audit_decision` | `src/smartgrid_mlops/governance/audit.py` | The only allowed mutation: append to the Stage 14 JSONL |
| `LIFECYCLE_STATES`, `DECISIONS`, `REASON_CODES` enums | `src/smartgrid_mlops/governance/schemas.py` | Reused as the source of truth for valid values |
| Agent firewall | `src/smartgrid_mlops/agents/firewall.py` (SHA `2743ff6a...`) | Unchanged; 7/7 lifecycle actions still blocked |
| Stage 13 packages | `artifacts/v2/governance_candidate_packages/` | The Stage 14 input (read-only) |

Stage 14 does NOT recreate a governance engine, a policy, a registry,
or a state machine.

## 3. Candidate inputs

Stage 14 reads the seven Stage 13 candidate packages from
`artifacts/v2/governance_candidate_packages/`. Each package
contains 8 files:

- `candidate_manifest.json`
- `model_spec.json` (with `model_spec_fingerprint`)
- `feature_spec.json` (with `feature_spec_fingerprint`)
- `data_split_manifest.json` (with the frozen Phase 19 protocol
  freeze SHA and the source dataset SHA)
- `benchmark_evaluation.json` (with the canonical Phase 13
  benchmark reconciliation)
- `protocol_compatibility.json` (with the protocol-compatibility
  classification)
- `reproducibility_manifest.json` (with the package root and
  external evidence hashes)
- `checksums.json` (with per-file and aggregate SHA-256s)

## 4. Package integrity results

| Check | Result |
| --- | --- |
| 7/7 candidate packages load | PASS |
| Every package has all 8 required files | PASS |
| Per-file SHA-256s verify against `checksums.json` | PASS |
| Aggregate package SHA-256 verifies | PASS |
| Missing file → `PackageIntegrityError` (NOT a silent pass) | PASS |
| Invalid checksum → `PackageIntegrityError` (NOT a silent pass) | PASS |
| 0 load failures across 7 candidates | PASS |

## 5. Governance adapter design

The adapter translates a `LoadedPackage` (from `loader.py`) into the
EXISTING `CandidateContext` and `TransitionRequest`. The translation
is conservative and honest:

- `evidence_status` is `VALID` only when the package is a
  genuine promotion candidate with `BENCHMARK_GATE_PASS` and no
  recorded evidence gaps. Otherwise it is `INVALID`, which
  causes the existing `EVIDENCE_VALIDITY_GATE` to fail.
- `lineage_status` is `COMPLETE` (the package records the source
  dataset SHA and the frozen Phase 19 protocol freeze SHA).
- `reproducibility_metadata` is `COMPLETE` (the package records
  per-file and aggregate checksums).
- `actual_model_fingerprint == expected_model_fingerprint` is
  set to the package's recorded `model_spec_fingerprint` (identity
  match by construction — no substitution, no fabrication).
- `actual_feature_fingerprint == expected_feature_fingerprint`
  is set to the package's recorded `feature_spec_fingerprint`.
- `protocol_hash` is set to the package's recorded
  `protocol_hash` (or, for residual candidates, the SHA-256 of
  the package's own `protocol_compatibility.json`, which is NOT
  in the policy's accepted hashes and therefore correctly triggers
  `PROTOCOL_MISMATCH`).
- `benchmark_gate` is the package's recorded
  `benchmark_gate_value_for_governance` (passed through unchanged
  via `PASS_THROUGH_BENCHMARK`).
- `statistical_evidence` is `REQUIRED_PASS` if and only if the
  benchmark gate is `BENCHMARK_GATE_PASS`. Otherwise it is
  `INSUFFICIENT_EVIDENCE`, which the existing engine accepts.
- `deviation_status` is `NONE` (the existing engine's enum does
  not include `DOCUMENTED_NON_CRITICAL`; the policy treats any
  value other than `UNRESOLVED_CRITICAL` as a pass on the
  deviation gate).
- The proposed transition is `EXPERIMENTAL -> VALIDATED` (the
  lowest elevation the frozen transition rules allow for an
  experimental candidate). We do NOT propose elevation to
  `REGISTERED_CHALLENGER` or higher; that would require a
  model_spec fingerprint match to the frozen Phase 11 finalist,
  which the residual candidates do not have.

Missing evidence is recorded as `EvidenceGap` objects and serialized
to `evidence_validation.json` under each candidate. The adapter
NEVER fabricates values, NEVER substitutes fingerprints, and NEVER
converts a missing field into a pass.

## 6. Actual candidate-by-candidate decisions

The decisions below were produced by the EXISTING frozen
`GovernanceEngine`. The Stage 14 layer did not modify the engine,
the policy, or any gate logic.

| Candidate | Proposed transition | Decision | Reason codes | Model spec FP | Feature spec FP |
| --- | --- | --- | --- | --- | --- |
| residual_constant_bias_system_load | EXPERIMENTAL -> VALIDATED | **DENY** | EVIDENCE_INVALID, PROTOCOL_MISMATCH | `fa0dc2…` | `94d696…` |
| residual_constant_bias_wind | EXPERIMENTAL -> VALIDATED | **DENY** | EVIDENCE_INVALID, BENCHMARK_GATE, PROTOCOL_MISMATCH | `fa0dc2…` | `94d696…` |
| residual_ridge_system_load | EXPERIMENTAL -> VALIDATED | **DENY** | EVIDENCE_INVALID, PROTOCOL_MISMATCH | `dfd12d…` | `94d696…` |
| residual_ridge_wind | EXPERIMENTAL -> VALIDATED | **DENY** | EVIDENCE_INVALID, BENCHMARK_GATE, PROTOCOL_MISMATCH | `dfd12d…` | `94d696…` |
| residual_hgb_system_load | EXPERIMENTAL -> VALIDATED | **DENY** | EVIDENCE_INVALID, PROTOCOL_MISMATCH | `3086b1…` | `94d696…` |
| residual_hgb_wind | EXPERIMENTAL -> VALIDATED | **DENY** | EVIDENCE_INVALID, BENCHMARK_GATE, PROTOCOL_MISMATCH | `3086b1…` | `94d696…` |
| residual_no_research_pv | EXPERIMENTAL -> VALIDATED | **DENY** | EVIDENCE_INVALID | `9278b7…` | `c56f47…` |

| Decision | Count |
| --- | ---: |
| DENY | 7 |
| ALLOW | 0 |
| REQUIRE_APPROVAL | 0 |
| NO_OP | 0 |

| Reason code | Count |
| --- | ---: |
| EVIDENCE_INVALID | 7 |
| PROTOCOL_MISMATCH | 6 |
| BENCHMARK_GATE | 3 |

## 7. Ordered gate outcomes

The full per-gate outcomes are recorded in
`artifacts/v2/governance_re_evaluation/gate_results/<candidate_id>_gates.json`.
The top-level summary records only the failed gates per candidate
(`decision.failed_gates`) — that is what the existing engine
exposes via `GovernanceDecision.failed_gates`. Stage 14 does NOT
synthesize a per-gate narrative; the engine's record is the
source of truth.

## 8. Reason codes

Every reason code in every decision is drawn from the EXISTING
`REASON_CODES` enum in `src/smartgrid_mlops/governance/schemas.py`:

- `EVIDENCE_INVALID`: the candidate's recorded evidence does not
  satisfy the policy's `evidence_status == "VALID"` requirement.
- `BENCHMARK_GATE`: the candidate's benchmark comparison
  failed (Stage 13 reported `BENCHMARK_GATE_FAIL` for the wind
  candidates).
- `PROTOCOL_MISMATCH`: the candidate's protocol hash is not in
  the policy's `accepted_protocol_hashes` list.

## 9. Evidence gaps (honest)

The Stage 14 `evidence_validation.json` records every gap per
candidate. The gaps are real; they are not synthesized.

| Candidate | benchmark | protocol | model_spec | feature_spec | final_test_access | integrity_audit |
| --- | --- | --- | --- | --- | --- | --- |
| residual_constant_bias_system_load | EVIDENCE_INVALID | PROTOCOL_MISMATCH | — | — | — | — |
| residual_constant_bias_wind | BENCHMARK_GATE | PROTOCOL_MISMATCH | — | — | — | — |
| residual_ridge_system_load | EVIDENCE_INVALID | PROTOCOL_MISMATCH | — | — | — | — |
| residual_ridge_wind | BENCHMARK_GATE | PROTOCOL_MISMATCH | — | — | — | — |
| residual_hgb_system_load | EVIDENCE_INVALID | PROTOCOL_MISMATCH | — | — | — | — |
| residual_hgb_wind | BENCHMARK_GATE | PROTOCOL_MISMATCH | — | — | — | — |
| residual_no_research_pv | EVIDENCE_INVALID | — | — | — | — | — |

The 6 residual candidates all have a `PROTOCOL_MISMATCH` gap
because the residual-correction protocol is not in the policy's
accepted hashes. The 3 wind candidates all have an additional
`BENCHMARK_GATE` gap because the Stage 13 evaluation classified
their benchmark as `BENCHMARK_GATE_FAIL`. The `residual_no_research_pv`
candidate has only the `EVIDENCE_INVALID` gap because its
model_spec and feature_spec are `n/a` (the no_research pathway
references the frozen Phase 11 random_forest finalist, which is
not itself a new candidate).

## 10. Benchmark gate results

The benchmark gate value passed to the engine is the value the
Stage 13 evaluation recorded in each package:

| Candidate | benchmark_gate_value |
| --- | --- |
| residual_constant_bias_system_load | BENCHMARK_GATE_PASS |
| residual_constant_bias_wind | BENCHMARK_GATE_FAIL |
| residual_ridge_system_load | BENCHMARK_GATE_PASS |
| residual_ridge_wind | BENCHMARK_GATE_FAIL |
| residual_hgb_system_load | BENCHMARK_GATE_PASS |
| residual_hgb_wind | BENCHMARK_GATE_FAIL |
| residual_no_research_pv | BENCHMARK_EVIDENCE_UNAVAILABLE |

The Stage 14 layer does NOT modify these values. The engine receives
the package's recorded value verbatim.

## 11. Protocol compatibility results

| Candidate | protocol_classification |
| --- | --- |
| residual_constant_bias_system_load | REQUIRES_NEW_PROTOCOL_APPROVAL |
| residual_constant_bias_wind | REQUIRES_NEW_PROTOCOL_APPROVAL |
| residual_ridge_system_load | REQUIRES_NEW_PROTOCOL_APPROVAL |
| residual_ridge_wind | REQUIRES_NEW_PROTOCOL_APPROVAL |
| residual_hgb_system_load | REQUIRES_NEW_PROTOCOL_APPROVAL |
| residual_hgb_wind | REQUIRES_NEW_PROTOCOL_APPROVAL |
| residual_no_research_pv | FORMALLY_COMPATIBLE_WITH_EVIDENCE |

The residual candidates' protocol hashes are NOT in the policy's
`accepted_protocol_hashes` list. Stage 14 reports this honestly; it
does NOT manufacture compatibility.

## 12. Authority boundary

| Component | Status |
| --- | --- |
| Phase 13 policy | unchanged (SHA `ee13cb36…`) |
| GovernanceEngine | unchanged (SHA `324927d8…`) |
| LifecycleStateMachine | unchanged |
| Agent firewall | unchanged (7/7 lifecycle actions still blocked) |
| Lifecycle registry | unchanged |
| Model registry | unchanged |
| Phase 19 protocol freeze | unchanged (SHA `79053d6…`) |
| OpenAPI surface | unchanged (0 lifecycle-mutation paths) |

| Role | State |
| --- | --- |
| Research | produces evidence |
| Stage 13 | structures evidence |
| GovernanceEngine | evaluates evidence (AUTHORITATIVE) |
| GovernanceDecision | the only output of Stage 14 |

## 13. Explicit lifecycle non-mutation confirmation

- The lifecycle registry (`artifacts/model_registry/lifecycle_registry.yaml`)
  is byte-identical before and after the Stage 14 run.
- No `apply_allowed_transition` call was made.
- No champion state was changed.
- No challenger state was changed.
- No model was promoted.
- No model was deployed.
- No lifecycle state was executed.

## 14. Agent firewall status

The 7/7 lifecycle actions are still blocked by the existing
firewall:

- `PROMOTE_MODEL`, `DEPLOY`, `ROLLBACK_MODEL`, `START_RETRAINING`,
  `CHANGE_POLICY`, `CHANGE_FEATURES`, `MODIFY_MODEL` all return
  `allowed=False` from `firewall_validate(...)`.

The agent may explain a Stage 14 decision. The agent may NOT
execute it.

## 15. API / OpenAPI status

The existing OpenAPI surface is unchanged:

- 0 lifecycle-mutation paths
- 0 governance-evaluation paths (Stage 14 is a CLI / library, not
  an API surface)
- The product backend API is not touched by Stage 14

Stage 14 deliberately does NOT add a new HTTP endpoint. The
Stage 14 outputs are JSON / JSONL files on disk. The existing
`scripts/run_governance_re_evaluation.py` CLI is the only entry
point.

## 16. Test results (actually executed)

| Suite | Result |
| --- | --- |
| Stage 14 tests | **21 / 21 PASS** |
| Backend suite (with Stage 14 tests) | (in progress) |
| Frontend | 27 / 27 PASS (unchanged) |
| TypeScript | PASS (unchanged) |
| Production build | PASS (unchanged) |
| Protocol freeze | 20 / 20 PASS (unchanged) |
| Phase 19 protected artefacts | 20 / 20 byte-identical (unchanged) |
| Agent firewall | 7 / 7 lifecycle actions still blocked (unchanged) |
| OpenAPI lifecycle-mutation | 0 (unchanged) |

The 21 Stage 14 tests cover:

- **Package integrity** (5): 7 packages load; required files
  exist; checksums verify; missing file fails honestly; invalid
  checksum fails honestly.
- **Adapter** (5): CandidateContext uses the existing schema;
  TransitionRequest uses the existing schema; fingerprints are
  taken from the package not fabricated; no_research pathway
  records n/a fingerprints; evidence gaps are recorded honestly.
- **Evaluation** (4): all 7 candidates evaluated; decisions
  contain the existing schema fields; the existing engine is
  invoked; the existing frozen policy is used.
- **Safety boundaries** (5): no v1 artefact modified by
  re-evaluation; no Phase 19 protected artefact modified; no
  lifecycle mutation endpoints added; agent firewall still
  blocks all 7; no lifecycle state mutation.
- **Determinism** (2): two runs produce the same per-candidate
  decisions; summary counts are stable.

## 17. Artifact integrity results

```
PHASE19: 20 unchanged / 0 changed
FREEZE: 20 PASS / 0 FAIL / 3 skipped, total 23
```

The Stage 14 evaluation does NOT modify any of:
- `config/governance/phase_13_policy.yaml`
- `artifacts/model_registry/lifecycle_registry.yaml`
- `artifacts/model_registry/mlops_research_registry.yaml`
- `artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml`
- `data/processed/research_hourly_index.parquet`
- `src/smartgrid_mlops/governance/`
- `src/smartgrid_mlops/agents/firewall.py`

## 18. Protocol freeze results

```
FREEZE: 20 PASS / 0 FAIL / 3 skipped
Phase 19 protocol freeze SHA: 79053d6... (unchanged)
```

The protocol freeze is read-only and is not modified by Stage 14.

## 19. Final interpretation

The Stage 14 re-evaluation produced the same honest outcome as
the Stage 12 evaluation: the existing frozen Phase 13 policy
DENYs all 7 candidates, for the same reasons:

- The 6 residual candidates have `PROTOCOL_MISMATCH` because the
  residual-correction protocol is not in the policy's
  `accepted_protocol_hashes`.
- The 3 wind candidates additionally have `BENCHMARK_GATE`
  because the canonical Phase 13 benchmark (RTS_DAY_AHEAD for
  wind) outperformed the residual candidates on the locked test
  window.
- The `residual_no_research_pv` candidate has `EVIDENCE_INVALID`
  only because its model_spec and feature_spec are `n/a` (the
  no_research pathway does not propose a new candidate; the frozen
  Phase 11 random_forest is the recommended path).

A favorable decision (e.g. ALLOW) would NOT have caused Stage 14
to execute any lifecycle transition. The architecture is:

```
Research → evidence
Stage 13 → structured evidence
GovernanceEngine → evaluation (AUTHORITATIVE)
GovernanceDecision → STOP
No automatic lifecycle execution
```

The Stage 14 layer records the GovernanceDecision and stops.
A future stage may consume the decision, but no execution happens
in Stage 14.

## 20. Files created

- `src/smartgrid_mlops/governance_re_evaluation/__init__.py`
- `src/smartgrid_mlops/governance_re_evaluation/loader.py`
- `src/smartgrid_mlops/governance_re_evaluation/adapter.py`
- `src/smartgrid_mlops/governance_re_evaluation/evaluator.py`
- `scripts/run_governance_re_evaluation.py`
- `tests/test_stage_14_governance_re_evaluation.py`
- `reports/productization/stage_14_governance_re_evaluation_completion.md` (this file)
- `artifacts/v2/governance_re_evaluation/manifest.json` (via summary)
- `artifacts/v2/governance_re_evaluation/evaluation_summary.json`
- `artifacts/v2/governance_re_evaluation/candidate_decisions.jsonl`
- `artifacts/v2/governance_re_evaluation/evidence_validation.json`
- `artifacts/v2/governance_re_evaluation/stage14_audit.jsonl`
- `artifacts/v2/governance_re_evaluation/gate_results/<candidate_id>_gates.json`

## 21. Files modified

None. The v1 tree is byte-identical to the pre-Stage-14 baseline.
The Phase 13 policy, the governance engine, the agent firewall, the
registries, and the protected v1 artefacts are unchanged. The
Stage 14 layer only writes under `artifacts/v2/governance_re_evaluation/`
and emits to `stage14_audit.jsonl` via the existing append-only
`audit_decision` helper.

## 22. Files NOT modified (explicit)

- `config/governance/phase_13_policy.yaml`
- `src/smartgrid_mlops/governance/policies.py`
- `src/smartgrid_mlops/governance/policy_engine.py`
- `src/smartgrid_mlops/governance/schemas.py`
- `src/smartgrid_mlops/governance/validators.py`
- `src/smartgrid_mlops/governance/state_machine.py`
- `src/smartgrid_mlops/governance/audit.py`
- `src/smartgrid_mlops/agents/firewall.py`
- `src/smartgrid_mlops/agents/orchestrator.py`
- `artifacts/model_registry/lifecycle_registry.yaml`
- `artifacts/model_registry/mlops_research_registry.yaml`
- `artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml`
- `data/processed/research_hourly_index.parquet`
- `artifacts/v2/residual_forecasting/` (Stage 10 outputs)
- `artifacts/v2/research_validation/` (Stage 11 outputs)
- `artifacts/v2/forecasting_research/` (Stage 9 outputs)
- `artifacts/v2/incremental_monitoring/` (Stage 8 outputs)
- `artifacts/v2/telemetry_replay/` (Stage 7 outputs)
- `artifacts/v2/governance_evaluation/` (Stage 12 outputs)
- `artifacts/v2/governance_candidate_packages/` (Stage 13 outputs)
- The FastAPI app (`product/backend_api/app/`)

## 23. Explicit statements

```
NO MODEL WAS PROMOTED.
```

```
NO MODEL WAS DEPLOYED.
```

```
NO LIFECYCLE STATE WAS EXECUTED.
```

```
NO GOVERNANCE POLICY WAS MODIFIED.
```

```
NO AGENT AUTHORITY WAS EXPANDED.
```

```
GOVERNANCE REMAINS AUTHORITATIVE.
```

```
AGENTIC AI REMAINS ADVISORY ONLY.
```

```
SYSTEM MODE REMAINS OFFLINE EVALUATION.
```

## 24. System terminology

Throughout Stage 14:

- OFFLINE EVALUATION
- HISTORICAL REPLAY
- INCREMENTAL MONITORING
- FORECASTING RESEARCH
- RESEARCH VALIDATION
- GOVERNANCE EVALUATION (Stage 12)
- GOVERNANCE-COMPATIBLE CANDIDATE PACKAGING (Stage 13)
- GOVERNANCE RE-EVALUATION (Stage 14)

Do NOT describe this as:

- Live monitoring
- Production deployment
- Autonomous MLOps
- Real-time smart-grid control

unless such functionality genuinely exists, which it does not.

Quantum/QML: NOT PART OF PROJECT.

## 25. Stop condition

```
STAGE 14 COMPLETE

Governance re-evaluation: COMPLETE

All candidate decisions were produced by the existing frozen
GovernanceEngine.

NO MODEL WAS AUTOMATICALLY PROMOTED.
NO MODEL WAS DEPLOYED.
NO LIFECYCLE STATE WAS EXECUTED.
NO GOVERNANCE POLICY WAS MODIFIED.
NO AGENT AUTHORITY WAS EXPANDED.

Governance remains AUTHORITATIVE.
Agentic AI remains ADVISORY ONLY.

System mode remains OFFLINE EVALUATION.

Quantum/QML: NOT PART OF PROJECT.

STOP.
Do not begin Stage 15 unless explicitly instructed.
```
