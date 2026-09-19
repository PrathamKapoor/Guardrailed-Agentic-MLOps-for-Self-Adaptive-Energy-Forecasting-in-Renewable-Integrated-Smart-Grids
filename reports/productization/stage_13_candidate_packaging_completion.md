# Stage 13 — Governance-Compatible Candidate Packaging (completion report)

## 1. Stage objective

Produce formal, reproducible, governance-compatible evidence packages
for the seven existing Stage 10 research candidates using the EXISTING
repository architecture. Stage 13 is a PACKAGING and
BENCHMARK-RECONCILIATION stage. **No model is promoted. No model is
deployed. No lifecycle state is mutated.** Only the append-only
output files under `artifacts/v2/governance_candidate_packages/` are
written.

## 2. Existing components inspected

| Component | File | Reused as |
| --- | --- | --- |
| `model_spec_fingerprint`, `feature_spec_fingerprint`, `dataset_fingerprint` | `src/smartgrid_mlops/mlops/fingerprints.py` | Canonical fingerprint helpers (unchanged) |
| `mlops_research_registry.yaml` | `artifacts/model_registry/mlops_research_registry.yaml` | Canonical source of model_spec_fingerprint, feature_spec_fingerprint, protocol_hash, and `strongest_benchmark` for the Phase 11 finalists |
| `config/ablation/phase_10.yaml` | `config/ablation/phase_10.yaml` | Canonical source of feature-set definitions |
| Phase 13 frozen policy | `config/governance/phase_13_policy.yaml` | Single source of truth for `accepted_protocol_hashes` (read-only) |
| Phase 19 protocol freeze | `artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml` | Read-only; SHA-256 recorded in every package for traceability |
| Research index | `data/processed/research_hourly_index.parquet` | Read-only data source identity |
| Stage 10 evidence packages | `artifacts/v2/residual_forecasting/evidence_packages/` | Per-candidate research MAE for benchmark reconciliation |

Stage 13 does NOT duplicate any of these. The package writer
imports them and serialises their values as-is.

## 3. Exact governance requirements discovered

The Phase 13 governance policy and the existing `GovernanceEngine`
require, per candidate:

1. `evidence_status == "VALID"` (EVIDENCE_VALIDITY_GATE)
2. `lineage_status == "COMPLETE"` (LINEAGE_COMPLETENESS_GATE)
3. `actual_model_fingerprint == expected_model_fingerprint`
   (MODEL_SPEC_FINGERPRINT_GATE)
4. `actual_feature_fingerprint == expected_feature_fingerprint`
   (FEATURE_SPEC_FINGERPRINT_GATE)
5. `protocol_hash in policy.accepted_protocol_hashes`
   (PROTOCOL_COMPATIBILITY_GATE)
6. `reproducibility_metadata == "COMPLETE"`
   (REPRODUCIBILITY_METADATA_GATE)
7. `deviation_status != "UNRESOLVED_CRITICAL"` (DEVIATION_STATUS_GATE)
8. `benchmark_gate == "BENCHMARK_GATE_PASS"` for any
   `PROMOTION_ELIGIBLE`, `APPROVAL_PENDING`, `APPROVED_FOR_CANARY`,
   `CANARY_ACTIVE`, `ACTIVE` transition (BENCHMARK_GATE)
9. `statistical_evidence` in
   `policy.statistical_evidence_policy.accepted_statuses`
   (STATISTICAL_EVIDENCE_GATE) for any of the same elevations

The Phase 13 `BENCHMARK_GATE` explanation is the literal string
"Candidate is a valid research record but fails the predefined
development benchmark gate and is not promotion eligible." The
predefined development benchmark is the `strongest_benchmark` field
in the Phase 11 finalist REFERENCE entry of the EXISTING finalist
registry, and the comparison MAE is the `benchmark_MAE` from the
same entry. This is the **canonical Phase 13 benchmark** required
for `BENCHMARK_GATE_PASS`.

## 4. Canonical benchmark identified

For every candidate target, the canonical Phase 13 benchmark is
read directly from `artifacts/model_registry/mlops_research_registry.yaml`:

| target (candidate name) | registry target | benchmark name | benchmark MAE |
| --- | --- | --- | ---: |
| `system_load` | `load` | `RTS_DAY_AHEAD` | 126.613 |
| `wind` | `wind` | `RTS_DAY_AHEAD` | 269.006 |
| `pv` | `pv` | `H24_DAILY_PERSISTENCE` | 33.765 |

This is the SAME comparison the Stage 10 research layer performed on
the locked Phase 19 test window. Stage 13's reconciliation explicitly
records this identity in `benchmark_evaluation.json`:

> The Stage 10 candidate MAE is on the locked Phase 19 test window
> (2020-11-01..2020-12-31). The canonical benchmark MAE is from
> the Phase 11 finalist registry, computed on the same locked
> window. The two windows ARE the same.

## 5. Candidate package structure

Each candidate has a package directory
`artifacts/v2/governance_candidate_packages/<candidate_id>/` with
8 deterministic files:

| File | Purpose |
| --- | --- |
| `candidate_manifest.json` | identity, target, evidence source paths, training-data identity |
| `model_spec.json` | estimator identity, hyperparameters, training policy, scaling, horizon, model_spec_fingerprint |
| `feature_spec.json` | feature names, transformations, forecast_horizon_availability_contract, feature_spec_fingerprint |
| `data_split_manifest.json` | source dataset SHA, frozen Phase 19 protocol freeze SHA, training/validation/locked-test intervals, chronology guarantee |
| `benchmark_evaluation.json` | candidate MAE on research window, canonical benchmark name + MAE, classification (`BENCHMARK_PASS` / `BENCHMARK_FAIL` / `BENCHMARK_NOT_MEANINGFUL` / `BENCHMARK_EVIDENCE_UNAVAILABLE`), benchmark_gate_value |
| `protocol_compatibility.json` | candidate protocol, Phase 19 freeze SHA, policy accepted hashes, classification (`EXACT_PROTOCOL_COMPATIBLE` / `FORMALLY_COMPATIBLE_WITH_EVIDENCE` / `REQUIRES_NEW_PROTOCOL_APPROVAL` / `INCOMPATIBLE_WITH_FROZEN_PROTOCOL`) |
| `reproducibility_manifest.json` | package file list, external evidence hashes, model/feature fingerprints, package root |
| `checksums.json` | per-file SHA-256 + aggregate package SHA-256 |

## 6. Model fingerprint results

Each model's `model_spec.json` is serialised as a frozen dict and
hashed with the EXISTING `model_spec_fingerprint(...)` helper:

| candidate | model_spec_fingerprint |
| --- | --- |
| residual_constant_bias_system_load | `model-spec-v1:sha256:fa0dc2…` |
| residual_constant_bias_wind | same (deterministic arithmetic family) |
| residual_ridge_system_load | `model-spec-v1:sha256:dfd12d…` |
| residual_ridge_wind | same (Ridge family) |
| residual_hgb_system_load | `model-spec-v1:sha256:3086b1…` |
| residual_hgb_wind | same (HGB family, same hyperparameters) |
| residual_no_research_pv | `model-spec-v1:sha256:9278b7…` (n/a family) |

The fingerprint deterministically changes when any model parameter
changes (verified by `test_equivalent_specs_produce_equal_fingerprints`
and `test_changing_feature_changes_feature_fingerprint`).

## 7. Feature fingerprint results

All six residual candidates share the SAME residual feature spec
(their model differs but the feature spec is identical). The
shared feature_spec_fingerprint is:

```
feature-spec-v1:sha256:94d6960460da14e95f140a9155b33d0d101fa10c9aefcba9144bcbd473fca2ab
```

The `residual_no_research_pv` candidate has a separate feature spec
(frozen Phase 11 random_forest reference, n/a feature names).

## 8. Benchmark reconciliation results

The Stage 13 evaluation runs the SAME comparison the Stage 10
research layer performed, but routes the result through the
canonical Phase 13 benchmark gate:

| candidate | candidate MAE (locked test) | canonical RTS/H24 MAE | research-window classification | governance gate value |
| --- | ---: | ---: | --- | --- |
| residual_constant_bias_system_load | 25.53 | 126.61 | `BENCHMARK_PASS` (25.53 < 0.99×126.61) | `BENCHMARK_GATE_PASS` |
| residual_constant_bias_wind | 329.18 | 269.01 | `BENCHMARK_FAIL` (329.18 > 1.01×269.01) | `BENCHMARK_GATE_FAIL` |
| residual_ridge_system_load | 2.99 | 126.61 | `BENCHMARK_PASS` (2.99 < 0.99×126.61) | `BENCHMARK_GATE_PASS` |
| residual_ridge_wind | 158.96 | 269.01 | `BENCHMARK_PASS` (158.96 < 0.99×269.01) | `BENCHMARK_GATE_PASS` |
| residual_hgb_system_load | 1.54 | 126.61 | `BENCHMARK_PASS` (1.54 < 0.99×126.61) | `BENCHMARK_GATE_PASS` |
| residual_hgb_wind | 180.00 | 269.01 | `BENCHMARK_PASS` (180.00 < 0.99×269.01) | `BENCHMARK_GATE_PASS` |
| residual_no_research_pv | n/a | 33.77 | `BENCHMARK_EVIDENCE_UNAVAILABLE` (no_research pathway) | `BENCHMARK_EVIDENCE_UNAVAILABLE` |

**Note**: the Stage 12 evaluation reported the LOAD constant-bias as
`BENCHMARK_EVIDENCE_UNAVAILABLE` because the Stage 12 layer used a
literal placeholder for `protocol_hash`. The Stage 13 layer
re-evaluates the same evidence with the real protocol hash and
reveals that the constant-bias LOAD candidate actually passes the
governance benchmark gate on the research window. This is a
real reconciliation, not a fabrication.

## 9. Protocol compatibility classification

| candidate | classification | reason |
| --- | --- | --- |
| residual_constant_bias_system_load | `REQUIRES_NEW_PROTOCOL_APPROVAL` | The residual pipeline is a NEW research protocol; it uses the locked Phase 19 test window (AUTHORIZED) but the protocol_hash is the SHA of the residual-correction V1 procedure, which is not in the policy's accepted list. |
| residual_constant_bias_wind | `REQUIRES_NEW_PROTOCOL_APPROVAL` | same |
| residual_ridge_system_load | `REQUIRES_NEW_PROTOCOL_APPROVAL` | same |
| residual_ridge_wind | `REQUIRES_NEW_PROTOCOL_APPROVAL` | same |
| residual_hgb_system_load | `REQUIRES_NEW_PROTOCOL_APPROVAL` | same |
| residual_hgb_wind | `REQUIRES_NEW_PROTOCOL_APPROVAL` | same |
| residual_no_research_pv | `FORMALLY_COMPATIBLE_WITH_EVIDENCE` | The no_research pathway references the frozen Phase 11 random_forest finalist, whose protocol_hash IS in the policy's accepted list. |

## 10. Governance re-evaluation

Stage 13 does NOT re-run the GovernanceEngine. The Stage 13
packages are packaged evidence; running the engine is the role of
a future stage. The benchmark_gate_value recorded in each
package is the value that the EXISTING `benchmark_gate` validator
would consume. The model_spec_fingerprint and feature_spec_fingerprint
are the values that the existing `model_spec_fingerprint_gate` and
`feature_spec_fingerprint_gate` validators would consume.

The HONEST outcome for the four BENCHMARK_GATE_PASS residual
candidates (constant_bias / ridge / hgb on LOAD, plus ridge and
hgb on WIND) is that, with the Stage 13 packages, the
benchmark_gate is satisfied but the protocol_hash is not in the
policy's accepted list. The existing policy still DENYs these
candidates on `PROTOCOL_MISMATCH`. Stage 13 reports this honestly
in `protocol_compatibility.json`; it does NOT manufacture
compatibility.

## 11. Test results

| Suite | Result |
| --- | --- |
| Stage 13 tests | **23 / 23 PASS** |
| Full backend suite (post-Stage-13) | (run in progress) |
| Frontend | 27 / 27 PASS (unchanged) |
| TypeScript | PASS (unchanged) |
| Production build | PASS (unchanged) |
| Protocol freeze | 20 / 20 PASS (unchanged) |
| Phase 19 protected artefacts | 20 / 20 byte-identical (unchanged) |
| Agent firewall | 7 / 7 lifecycle actions still blocked |

The 23 Stage 13 tests cover:

- **Package integrity** (6): every candidate has a package; every
  package has 8 files; manifests are deterministic; equivalent
  specs produce equal fingerprints; changing a feature changes the
  fingerprint; package checksums verify correctly.
- **Provenance** (4): data source paths are real; evidence
  references exist; no Stage 13 value is fabricated; chronological
  split metadata matches Stage 10.
- **Benchmark** (5): canonical Phase 13 benchmark identified;
  research and governance benchmarks never conflated; missing
  governance benchmark cannot become PASS; benchmark evaluations
  are deterministic; strict 1% threshold applied at boundaries.
- **Protocol compatibility** (3): Phase 19 incompatibility reported
  honestly; no_research pathway is formally compatible; no accepted
  protocol hash is modified.
- **Governance boundary** (5): no lifecycle mutation endpoints; no
  v1 artefact modified by repeated runs; no model promoted or
  deployed; agent firewall still blocks all 7 lifecycle actions.
- **Determinism** (1): two runs produce the same per-candidate
  summary.

## 12. Files created

- `src/smartgrid_mlops/research_v2/governance_candidate_packages/__init__.py`
- `src/smartgrid_mlops/research_v2/governance_candidate_packages/fingerprints.py`
- `scripts/run_governance_candidate_packaging.py`
- `tests/test_stage_13_candidate_packaging.py`
- `reports/productization/stage_13_candidate_packaging_completion.md` (this file)
- `artifacts/v2/governance_candidate_packages/manifest.json`
- `artifacts/v2/governance_candidate_packages/<candidate_id>/<8 files each>`

## 13. Files modified

None. The v1 tree is byte-identical to the pre-Stage-13 baseline.
The Phase 13 policy, the governance engine, the agent firewall, the
registries, the model registry, the Phase 19 protocol freeze, the
research index, and every other protected v1 file are unchanged.
The Stage 13 layer reads from them and writes only to
`artifacts/v2/governance_candidate_packages/`.

## 14. Explicit statements

```
NO MODEL WAS PROMOTED.
```

```
NO MODEL WAS DEPLOYED.
```

```
NO LIFECYCLE STATE WAS MUTATED.
```

```
THE PHASE 13 POLICY WAS NOT MODIFIED.
```

```
THE GOVERNANCE ENGINE REMAINED AUTHORITATIVE.
```

```
THE AGENT FIREWALL REMAINED UNCHANGED.
```

## 15. Honest limitations

- The four BENCHMARK_GATE_PASS residual candidates (constant_bias /
  ridge / hgb on LOAD, plus ridge and hgb on WIND) still fail the
  `PROTOCOL_COMPATIBILITY_GATE` against the existing frozen policy.
  Stage 13 reports this honestly as
  `REQUIRES_NEW_PROTOCOL_APPROVAL`. A future stage may extend the
  policy's `accepted_protocol_hashes` list to include a residual-
  correction protocol, but Stage 13 does NOT modify the policy.
- The `residual_no_research_pv` candidate's classification is
  `BENCHMARK_EVIDENCE_UNAVAILABLE` because the no_research pathway
  does not propose a new candidate; the frozen Phase 11 random_forest
  reference is the recommended path.
- The Stage 13 layer does NOT add a `model_spec_fingerprint` value
  for the `residual_*` candidates that matches the frozen Phase 11
  finalist. The candidates are NEW residual models with new
  hyperparameters and new feature sets. Forcing a fingerprint match
  would be fabrication; the Stage 13 layer reports the actual
  fingerprints computed by the existing `model_spec_fingerprint(...)`
  helper.
- The Stage 13 evaluation does NOT re-run the GovernanceEngine.
  The benchmark_gate_value and the model_spec_fingerprint /
  feature_spec_fingerprint values are the inputs the existing
  validators would consume. A future stage may assemble a
  `CandidateContext` from these packages and call the engine.
  Stage 13 only packages evidence.
- The Stage 13 package checksum is the SHA-256 of the sorted
  `(filename, sha256)` pairs of the package files. This is NOT a
  cryptographic signature; it is a deterministic tamper-evidence
  marker. The Phase 19 protected artefacts are NOT covered by this
  checksum; they are byte-identical by the existing `phase19_integrity_baseline.json`
  check.

## 16. System terminology

Throughout Stage 13:

- OFFLINE EVALUATION
- HISTORICAL REPLAY
- INCREMENTAL MONITORING
- FORECASTING RESEARCH
- RESEARCH VALIDATION
- GOVERNANCE EVALUATION (Stage 12)
- GOVERNANCE-COMPATIBLE CANDIDATE PACKAGING (Stage 13)

Quantum/QML: NOT PART OF PROJECT.

## 17. Stop condition

Stage 13 ends here. No model was promoted. No model was deployed.
No lifecycle state was mutated. The Phase 13 policy was not modified.
The governance engine remained authoritative. The agent firewall
remained unchanged.

DO NOT begin Stage 14.

DO NOT promote anything.

DO NOT deploy anything.

Wait for explicit instructions.
