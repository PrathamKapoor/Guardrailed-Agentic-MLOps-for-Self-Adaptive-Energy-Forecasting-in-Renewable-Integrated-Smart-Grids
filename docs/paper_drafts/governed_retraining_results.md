# Governed retraining results (Phase 15, development/simulation)

All numbers below come from the frozen Phase 15 protocol (`artifacts/experimental_design/phase_15_retraining_protocol_freeze.yaml`) executed by `scripts/run_governed_retraining.py`. Evidence is controlled development/simulation retraining on synthetic adaptation scenarios; no production, live-grid, or final-test claim is made.

## Request-policy correctness

The frozen 15-case request-policy suite returned 15/15 correct decisions (100%): 4 expected ALLOW, 7 expected DENY, 4 expected DEFER, with 0 false allows, 0 false denies, and 0 false defers. Five unsafe retraining attempts (critical data-quality failure, invalid lineage, model fingerprint tampering, final-test access request, invalid monitoring evidence) were all blocked — an Unsafe Retraining Prevention Rate of 100%. Six unnecessary retraining attempts (clean stream, WATCH-only feature drift, insufficient persistence, unavailable labels, insufficient new data, cooldown) were all prevented. The duplicate-request case deterministically returned the original decision with a DUPLICATE_REQUEST marker instead of launching a second job, and re-executing the full official suite created zero duplicate jobs or challengers.

## Allowed retraining jobs

All 18 planned adaptation scenarios (2 families × 3 severities × 3 targets) were ALLOWed by condition D of the frozen performance-signal rule and independently raised PERFORMANCE_DRIFT evidence from the perturbed streams. 18 jobs started, 18 completed, 0 failed. Mean runtime was 0.82 s (median 0.56 s). Jobs consumed 6,066 new post-drift rows in total (337 per scenario ≥ the 336 minimum) over 94,626 total expanding-window training rows. Each job reused the frozen specification exactly: no HPO, no feature selection, no family change, seed 42.

## Target-specific adaptation

| Target | Scenarios | Mean reference post-drift MAE | Mean challenger post-drift MAE | Mean adaptation gain | Improved | Degraded |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LOAD | 6 | 411.09 | 345.58 | +11.38% | 5 | 1 |
| WIND | 6 | 419.00 | 403.78 | +2.48% | 3 | 3 |
| PV | 6 | 201.99 | 65.84 | +60.05% | 6 | 0 |

PV benefited most (up to +87.97% in the abrupt HIGH case) because persistent target-level shifts move the lag-feature relationship strongly and the zero-clipped process stays learnable. LOAD improved clearly for MEDIUM/HIGH shifts (up to +30.51%) but was near zero at LOW severity. WIND was essentially flat: three cases improved slightly and three degraded (worst −4.99% at abrupt LOW), consistent with the high-noise wind process where a 336-hour sample cannot reliably identify the shifted relationship.

## Positive and negative adaptation

Improved: 14/18 cases. Degraded: 4/18 (A15-01-LOW-wind −4.99%, A15-01-MEDIUM-wind −1.08%, A15-02-HIGH-wind −1.02%, A15-02-LOW-load −0.47%). Negative results are retained, not retried: the frozen policy forbids rerunning until a favorable challenger appears, and the no-arbitrary-success-threshold rule means raw relative changes are reported.

## Severity effects

Mean adaptation gain rose with synthetic severity — LOW +13.32%, MEDIUM +20.34%, HIGH +40.25% — as expected when the shift is large relative to process noise. Monotonicity was not forced and did not hold case-by-case (e.g., WIND HIGH gradual was slightly negative), which is reported as observed.

## Clean-stability trade-offs

On the unperturbed counterfactual stream, adaptation cost was small but usually negative: mean clean stability change was slightly negative for most scenarios (e.g., −16.55% for abrupt-HIGH LOAD) while a few low-severity gradual cases were positive (up to +5.91% PV). Adapting to a large synthetic shift trades some clean-stream fidelity for large post-drift gains, quantified per case in `reports/tables/retraining_clean_stability.md`.

## Challenger registration and absence of automatic promotion

All 18 challengers passed admission checks and were registered as REGISTERED_CHALLENGER with promotion_eligible=false in an additive registry; the Phase 12/13 registries and all prior freezes are byte-identical to before Phase 15. Automatic promotions: 0. Reference replacements: 0. Governance bypasses: 0. No ACTIVE, CHAMPION, or canary state exists anywhere in the repository, and MODEL_PROMOTED is absent from the audit log by construction.

## Benchmark context

The frozen references still fail the strongest development benchmarks (RTS DAY_AHEAD for LOAD/WIND; H24 daily persistence for PV). A challenger beating its reference does not imply beating those benchmarks, and under synthetically modified targets the external benchmark values are not coherent forecasts, so no benchmark-based adaptation claim is made. Production-style benchmark eligibility remains unresolved until valid evidence exists.

## Provenance note

P15-DEV-001 documents that the Phase 12 registry stored LOAD's model-spec fingerprint computed from PV hyperparameters (a family-keyed dict collision). Phase 15 retrains from the correct per-target frozen specification and records the defect without modifying prior frozen evidence.
