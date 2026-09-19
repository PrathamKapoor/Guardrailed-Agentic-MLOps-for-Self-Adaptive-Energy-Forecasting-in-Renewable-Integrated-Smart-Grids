# Phase 15 deviation report — P15-DEV-001 (Phase 12 LOAD model-spec fingerprint metadata defect)

## Discovery

While implementing Phase 15 governed retraining, reconstructing the frozen LOAD
reference specification for the MODEL_FINGERPRINT_GATE produced

`model-spec-v1:sha256:90b81da25f399af0b8461dc49598f1d937b84d9b79a6e2a61366d8ce17413d94`

while the Phase 12 research registry records

`model-spec-v1:sha256:60adb40d4904062690a9fdcec46a0b2e6e4e93a63a9383cc53f52bdb6e896122`

## Root cause

`scripts/build_phase12_mlops_foundation.py` builds a per-family hyperparameter map with

```python
classical = {x["model"]: x for x in phase10["classical_models"].values()}
```

LOAD and PV both use family `random_forest`, so the dict comprehension keeps only the
LAST entry (PV). The LOAD registry fingerprint was therefore computed from the PV
hyperparameters (bootstrap=false, max_depth=8, max_features=sqrt, n_estimators=209)
instead of the frozen LOAD hyperparameters (bootstrap=true, max_depth=null,
max_features=1.0, n_estimators=191, min_samples_split=2).

Verification: recomputing the LOAD fingerprint with the PV hyperparameters reproduces
the stored registry value exactly. WIND and PV registry fingerprints are unaffected.

## Scientific impact

- Phase 10 actually trained and evaluated the LOAD reference with the CORRECT
  per-target hyperparameters (development MAE 285.1046), so no forecasting result,
  selection outcome, benchmark comparison, or lifecycle decision is affected.
- The defect is confined to Phase 12/13 metadata identity fields: the registry and
  reproducibility-manifest fingerprint text for LOAD describes a specification that
  was never trained. All Phase 13 governance gates compared candidates against the
  same (incorrectly derived) stored value, so gate behavior and the 18/18 scenario
  outcomes are internally consistent and unchanged.
- The Phase 12/13 frozen artifacts are NOT modified by Phase 15 (prior freezes must
  remain unchanged). A future phase may choose to repair the registry metadata
  through an explicit deviation-controlled rebuild.

## Phase 15 handling

1. The defect is documented here (no silent edit of prior frozen evidence).
2. Phase 15 retrains challengers from the CORRECT per-target frozen specification in
   `artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml`
   (LOAD: n_estimators=191; this is the specification that produced the recorded
   development evidence).
3. The Phase 15 MODEL_FINGERPRINT_GATE compares the retraining source identity
   against a fingerprint recomputed from the correct per-target specification, so
   reference and challenger share one consistent specification identity.
4. WIND and PV fingerprints are identical to the registry values.
5. This deviation is recorded in the Phase 15 completion report, the evidence
   registry, and threats to validity.

## Classification

METADATA DEFECT — recorded as P15-DEV-001; prior frozen evidence unchanged; no
final-test access involved; discovered before any official Phase 15 retraining run.
