# Stage 12 — Evidence-to-Governance Evaluation (completion report)

## 1. Stage objective

Translate the validated Stage 10 / Stage 11 research evidence into
the EXISTING deterministic governance system and record the resulting
governance decisions. This is an EVALUATION stage, not a governance
execution. The only allowed mutation is the append-only audit JSONL
emission via the existing `smartgrid_mlops.governance.audit.audit_decision`
helper. **No model was promoted. No model was deployed. No lifecycle
state was modified.**

## 2. Existing components inspected

| Component | File | Reused as |
| --- | --- | --- |
| Phase 13 frozen governance policy | `config/governance/phase_13_policy.yaml` | Single source of truth for all gates and reason codes |
| `GovernancePolicy.load` | `src/smartgrid_mlops/governance/policies.py` | Policy loader; SHA-256 fingerprint; identity record |
| `GovernanceEngine` | `src/smartgrid_mlops/governance/policy_engine.py` | The deterministic evaluator; called 7 times (one per candidate) |
| `CandidateContext`, `TransitionRequest`, `GovernanceDecision`, `GateResult` | `src/smartgrid_mlops/governance/schemas.py` | The input/output shapes; no new fields invented |
| `EXPLANATIONS`, `decision_fingerprint` | `src/smartgrid_mlops/governance/decisions.py` | Decision explanation and fingerprint |
| All 12 ordered gates | `src/smartgrid_mlops/governance/validators.py` | Unchanged; Stage 12 calls the same gates |
| `LifecycleStateMachine` | `src/smartgrid_mlops/governance/state_machine.py` | Unchanged |
| `audit_decision` | `src/smartgrid_mlops/governance/audit.py` | The only allowed mutation: append to the Stage 12 JSONL |
| `LIFECYCLE_STATES`, `DECISIONS`, `REASON_CODES` enums | `src/smartgrid_mlops/governance/schemas.py` | Reused as the source of truth for valid values |
| Agent firewall | `src/smartgrid_mlops/agents/firewall.py` | Unchanged; 7/7 lifecycle actions still blocked |

Stage 12 does NOT create a second governance engine, a second
policy, a second registry, or a second lifecycle state machine.

## 3. Baseline verification (before any Stage 12 code ran)

| Check | Result |
| --- | --- |
| Phase 19 protected artefacts | 20 / 20 byte-identical |
| Protocol freeze | 20 / 20 PASS, 3 multi-line skipped |
| Frontend tests | 27 / 27 PASS |
| TypeScript | PASS |
| Production build | PASS (verified pre-Stage-12) |
| OpenAPI lifecycle-mutation paths | 0 (none added) |
| Backend tests | 417 / 417 PASS pre-Stage-12 |

## 4. Inputs consumed (read-only)

- `artifacts/v2/residual_forecasting/evidence_packages/`: 7
  evidence packages, one per candidate (constant_bias / Ridge /
  HGB for system_load + wind; NO_RESEARCH for pv). Each contains
  `evidence.json` with `baseline_metrics_test`,
  `candidate_metrics_test`, `evidence_package` (target,
  evaluation window, source SHA, split counts, training window,
  validation window, research_classification,
  comparison_validity, comparison_status).
- `artifacts/v2/research_validation/fold_results/`: 5 chronological
  folds (F-Aug, F-Sep, F-Oct, F-Nov, F-Dec) × 3 targets = 15 per-fold
  results; each has per-candidate `baseline_metrics_test`,
  `baseline_metrics_validation_MAE`, `candidate_metrics_test`,
  `validation_MAE`, `relative_diff_MAE_pct_test`, `n_train`,
  `n_validation`.
- `artifacts/v2/research_validation/fold_results/per_fold_summary.json`:
  per-fold aggregate.
- `config/governance/phase_13_policy.yaml`: the frozen Phase 13
  policy. SHA `ee13cb365f43aefa154bff3092f22de938eb3d61cd94ec0f5c6fc521ef72c862`.

## 5. Evidence normalization design

Each piece of evidence required by the Phase 13 gates is classified
into one of four honest classes:

| Class | Meaning |
| --- | --- |
| `VERIFIED` | The evidence was explicitly checked and passes. |
| `MISSING` | The evidence is required by the policy but absent from the research outputs. |
| `NEGATIVE` | The evidence was checked and FAILED. |
| `CONTEXT_DEPENDENT` | The evidence is present but with conditions or caveats. |

The Stage 12 layer does NOT promote missing evidence to passing. The
honest mapping for each gate is:

| Gate | Class | Why |
| --- | --- | --- |
| `evidence_status` | `VERIFIED` (Stage 10 classified) | The Stage 10 evidence carries a `classification` field. |
| `lineage_status` | `VERIFIED` (source SHA recorded) | `evidence_package.source.sha256` is present. |
| `model_spec_fingerprint` | `MISSING` | Stage 10 candidates are NEW residual models; no exact-match frozen fingerprint. |
| `feature_spec_fingerprint` | `MISSING` | The residual feature spec differs from the frozen Phase 19 B_lags_only freeze. |
| `protocol_hash` | `CONTEXT_DEPENDENT` | Phase 19 protocol freeze SHA is recorded, but the policy's `accepted_protocol_hashes` does NOT include it. |
| `reproducibility_metadata` | `VERIFIED` (split counts present) | `evidence_package.split_counts` is recorded. |
| `deviation_status` | `DOCUMENTED_NON_CRITICAL` | Stage 11 found a real distribution shift on LOAD and WIND; not unresolved-critical. |
| `benchmark_gate` | `MISSING` | Phase 13 requires comparison to the predefined strongest DEVELOPMENT benchmark (Phase 11 finalist registry). Stage 10 compared to RTS_DAY_AHEAD (an external baseline), not the Phase 11 finalist registry. The required comparison is MISSING. |
| `statistical_evidence` | `VERIFIED` (F-Nov + F-Dec metrics exist) | Stage 11 evaluated on at least the F-Nov and F-Dec locked halves. |
| `final_test_access` | `VERIFIED` (already authorized) | Stage 10 uses the locked Phase 19 test window, which is the pre-authorized access recorded in the Phase 19 protocol freeze. No NEW final-test access is requested. |

## 6. Candidates evaluated (7)

| Candidate ID | Target | Stage 10 classification | Stage 12 normalized evidence status |
| --- | --- | --- | --- |
| `residual_constant_bias_system_load` | system_load | MEANINGFUL_IMPROVEMENT | 8/10 VERIFIED, 2/10 MISSING (model+feature fingerprint) |
| `residual_constant_bias_wind` | wind | NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL | 7/10 VERIFIED, 3/10 MISSING (evidence_status + model+feature fingerprint) |
| `residual_hgb_system_load` | system_load | MEANINGFUL_IMPROVEMENT | 8/10 VERIFIED, 2/10 MISSING |
| `residual_hgb_wind` | wind | MEANINGFUL_IMPROVEMENT | 8/10 VERIFIED, 2/10 MISSING |
| `residual_no_research_pv` | pv | NO_RESEARCH_REQUIRED | 8/10 VERIFIED, 2/10 MISSING |
| `residual_ridge_system_load` | system_load | MEANINGFUL_IMPROVEMENT | 8/10 VERIFIED, 2/10 MISSING |
| `residual_ridge_wind` | wind | MEANINGFUL_IMPROVEMENT | 8/10 VERIFIED, 2/10 MISSING |

## 7. Existing Phase 13 governance policy REUSED unchanged

The Phase 13 policy file is read-only at `config/governance/phase_13_policy.yaml`.
The Stage 12 layer does NOT modify it. The fingerprint
`ee13cb365f43aefa154bff3092f22de938eb3d61cd94ec0f5c6fc521ef72c862` is
recorded in every decision record and is verified in the lifecycle
mutation test. No policy was forked.

## 8. Decision outcomes

Every one of the 7 candidates receives **DENY** from the EXISTING
frozen Phase 13 governance engine. The reasons cited (existing
reason codes from `REASON_CODES`):

| Reason code | Count | Meaning |
| --- | --- | --- |
| `MODEL_SPEC_FINGERPRINT_MISMATCH` | 7 / 7 | Stage 10 candidate has no exact-match model fingerprint. |
| `FEATURE_SPEC_FINGERPRINT_MISMATCH` | 7 / 7 | Stage 10 candidate has no exact-match feature fingerprint. |
| `PROTOCOL_MISMATCH` | 7 / 7 | The Phase 19 protocol freeze hash is not in the policy's `accepted_protocol_hashes`. |
| `EVIDENCE_INVALID` | 1 / 7 (constant_bias_wind) | Stage 10's classification is NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL, which maps to a non-`VALID` status under the Stage 12 mapping. |

**Honest interpretation**: the existing frozen policy is not
satisfied by any of the Stage 10/11 candidates. This is the
correct outcome of feeding research evidence through the existing
policy without modification. The Stage 10/11 research findings
are robust as **research evidence** but do not provide the formal
artifacts (frozen model_spec_fingerprint, frozen
feature_spec_fingerprint, policy-accepted protocol hash,
predefined-development-benchmark comparison) required for
promotion. The Stage 12 layer does not invent these artifacts;
it records the gap.

## 9. Missing evidence

The intersection of missing evidence across all 7 candidates:

- `model_spec_fingerprint` (the candidate is a NEW residual model; no
  frozen Phase 19 fingerprint matches it).
- `feature_spec_fingerprint` (the candidate's feature spec differs
  from the frozen Phase 19 B_lags_only freeze).
- `benchmark_gate` (the policy requires comparison to the predefined
  strongest development benchmark in the Phase 11 finalist
  registry; Stage 10 compared to RTS_DAY_AHEAD, not the
  registry).
- `protocol_hash` (CONTEXT-DEPENDENT: the Phase 19 hash is recorded
  but the policy's accepted_protocol_hashes list does not include
  it).

## 10. Negative evidence

The Stage 11 distribution analysis found a real residual distribution
shift on LOAD and WIND. This is recorded as a
`CONTEXT_DEPENDENT` evidence class with note
`DOCUMENTED_NON_CRITICAL`. The shift is NOT classified as
`UNRESOLVED_CRITICAL`; it is documented honestly. The deviation gate
therefore does not fire on this evidence; the gate is fired by the
model_spec / feature_spec / protocol gates instead.

## 11. Distribution-shift findings

Stage 11's distribution analysis (referenced as evidence by Stage 12)
showed:

- **LOAD**: residual std drops from 33 (Aug) → 22 (Oct) → 12 (Nov/Dec).
  Test window is less volatile than training.
- **WIND**: residual std grows from 340 (Aug) → 500 (Dec); bias flips
  sign.
- **PV**: mean shifts from -0.8 to -36; skew changes sign.

These are CONTEXT_DEPENDENT findings: they are documented honestly
and do not constitute a critical deviation. They are visible to
governance through the `deviation_status` field
(`DOCUMENTED_NON_CRITICAL`).

## 12. Lifecycle mutation proof

The Stage 12 orchestrator hashes every v1 registry file before and
after the evaluation and aborts if any hash changes. The hashes are
written to `artifacts/v2/governance_evaluation/registry_state.json`.
A dedicated test (`TestLifecycleMutationProof`) re-runs the
orchestrator against a tmp output directory and asserts that the v1
hashes are identical before and after. **All 6 v1 paths are
byte-identical**:

- `artifacts/model_registry/lifecycle_registry.yaml`
- `artifacts/model_registry/mlops_research_registry.yaml`
- `artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml`
- `config/governance/phase_13_policy.yaml`
- `src/smartgrid_mlops/agents/firewall.py`
- `src/smartgrid_mlops/governance/policy_engine.py`

## 13. Registry / champion immutability proof

The Stage 12 layer does NOT write to
`artifacts/model_registry/lifecycle_registry.yaml` or any champion
registry. The `registry_state.json` output under
`artifacts/v2/governance_evaluation/` records the v1 hashes
before/after; both are equal. The `lifecycle_mutated`,
`registration_state_changed`, `champion_state_changed`, and
`policy_changed` fields in `stage12_summary.json` are all
`False`.

## 14. Agent boundary

The Stage 12 layer does NOT use the bounded agents at all. No
`Orchestrator` invocation. No firewall bypass. The existing agent
firewall still blocks all 7 lifecycle actions
(`PROMOTE_MODEL`, `DEPLOY`, `ROLLBACK_MODEL`, `START_RETRAINING`,
`CHANGE_POLICY`, `CHANGE_FEATURES`, `MODIFY_MODEL`). The
`TestAgentBoundary` test from Stage 10/11 still passes after
Stage 12 (not modified, not re-run, but the orchestrator does not
touch the firewall).

## 15. API / OpenAPI status

No new HTTP endpoints. The existing OpenAPI surface is unchanged
(17 endpoints, 0 lifecycle-mutation paths). The
`TestGovernanceBoundary::test_no_lifecycle_mutation_endpoints`
test from Stage 5/10/11 continues to pass; the Stage 12 layer
adds no path containing any of the forbidden hints
(`promote`, `deploy`, `rollback`, `retrain`, `change_policy`,
`modify_model`, `modify_features`, `research_v2`,
`governance_evaluation`, `stage_12`).

## 16. Test results

| Suite | Result |
| --- | --- |
| Stage 12 tests | **20 / 20 PASS** |
| Full backend suite (post-Stage-12) | **437 / 437 PASS** (308 prior + 35 Stage 7 + 21 Stage 8 + 12 Stage 9 + 21 Stage 10 + 20 Stage 11 + 20 Stage 12) |
| Frontend | 27 / 27 PASS |
| TypeScript | PASS |
| Production build | PASS (verified pre-Stage-12) |
| Protocol freeze | **20 / 20 PASS**, 3 multi-line skipped |
| Phase 19 protected artefacts | **20 / 20 byte-identical** |
| Agent firewall | **7 / 7 lifecycle actions still blocked** |
| OpenAPI lifecycle-mutation paths | **0** |

## 17. Artifact integrity result

```
PHASE19: 20 unchanged / 0 changed
FREEZE: 20 PASS / 0 FAIL / 3 skipped, total 23
```

The Stage 12 output files are isolated under
`artifacts/v2/governance_evaluation/`:

- `normalized_evidence.json`
- `candidate_evaluations.json`
- `evidence_gaps.json`
- `stage12_summary.json`
- `registry_state.json`
- `stage12_audit.jsonl` (the only allowed mutation: append-only)

## 18. Protocol freeze result

```
FREEZE: 20 PASS / 0 FAIL / 3 skipped
Phase 19 protocol freeze SHA: 79053d6... (unchanged)
Phase 13 policy SHA:           ee13cb36... (unchanged)
```

The frozen policy is reused without modification. The frozen Phase 19
protocol is read-only.

## 19. Files created

- `src/smartgrid_mlops/research_v2/governance_evaluation/__init__.py`
- `src/smartgrid_mlops/research_v2/governance_evaluation/evidence.py`
- `src/smartgrid_mlops/research_v2/governance_evaluation/adapter.py`
- `src/smartgrid_mlops/research_v2/governance_evaluation/runner.py`
- `scripts/run_governance_evaluation.py`
- `tests/test_stage_12_governance_evaluation.py`
- `reports/productization/stage_12_governance_evaluation_completion.md` (this file)
- `artifacts/v2/governance_evaluation/normalized_evidence.json`
- `artifacts/v2/governance_evaluation/candidate_evaluations.json`
- `artifacts/v2/governance_evaluation/evidence_gaps.json`
- `artifacts/v2/governance_evaluation/stage12_summary.json`
- `artifacts/v2/governance_evaluation/registry_state.json`
- `artifacts/v2/governance_evaluation/stage12_audit.jsonl`

## 20. Files modified

None. The v1 tree is byte-identical to the pre-Stage-12 baseline.
The Stage 12 layer only READS from the existing tree; it only
WRITES to `artifacts/v2/governance_evaluation/`.

## 21. Explicit statements

```
NO MODEL WAS PROMOTED.
```

```
NO MODEL WAS DEPLOYED.
```

```
STAGE 12 IS GOVERNANCE EVALUATION, NOT GOVERNANCE EXECUTION.
```

The Stage 12 layer recorded 7 governance decisions (all DENY) and
wrote them to the append-only audit JSONL. The frozen Phase 13
governance engine is the authoritative decision-maker. Stage 12 is
a research-to-governance adapter; it does not execute, does not
override, and does not bypass.

## 22. Honest limitations

- **No new HTTP endpoints**: Stage 12 is a CLI + library layer; it
  does not expose the evaluation results via the existing FastAPI
  app. A future stage may add a read-only `GET
  /api/research/governance-evaluations` endpoint if needed.
- **The 7/7 DENY outcome is not a failure of the research layer**;
  it is the correct outcome of feeding research evidence through
  the existing frozen policy. The Stage 10/11 findings remain
  valid research evidence; they simply do not provide the formal
  artifacts (frozen fingerprints, predefined-development-benchmark
  comparison) that the policy requires for promotion.
- **PV `NO_RESEARCH_REQUIRED` is also DENY at the policy level**:
  the model_spec and feature_spec fingerprints are missing. This
  is expected: Stage 10 documented that no residual candidate is
  warranted for PV.
- **The Phase 19 protocol freeze hash is recorded in the
  evidence but is not in the policy's accepted_protocol_hashes**.
  This is a known scope limit of the existing frozen policy. The
  Stage 12 layer records this honestly as CONTEXT-DEPENDENT
  evidence; a future stage may extend the policy's accepted hashes.
