# Deterministic model lifecycle governance

## Research Objective

Phase 13 designs and validates a deterministic lifecycle engine using evidence, lineage, fingerprints, frozen protocols, reproducibility, deviations, benchmark evidence, statistical evidence, approval, state-transition, and final-test policies before autonomous recommendations exist. RQ-GOV-1 through RQ-GOV-5 ask whether invalid transitions are prevented, research validity is distinguished from promotion eligibility, repeated inputs reproduce decisions, every decision is traceable, and immutable specifications resist conflicting recommendations.

Before implementation, H-GOV-1 predicted invalid or incomplete candidates would be blocked; H-GOV-2 predicted benchmark-inferior models would not become promotion eligible; H-GOV-3 predicted identical scientific decisions; H-GOV-4 predicted gate-level attribution. Support is assessed only after the frozen simulation.

## Governance Architecture

MLflow evidence and Phase 12 registry/lineage records feed a deterministic policy engine. The engine alone evaluates lifecycle transitions and emits structured decisions plus audit events. Future recommendations may enter this engine but cannot bypass it.

## Lifecycle States and Transition Rules

Research role, registry state, lifecycle state, benchmark gate, and approval state remain independent. The policy declares legal transitions. `INVALIDATED` and `ARCHIVED` are terminal. Baselines are non-lifecycle comparators. Current references remain `REGISTERED_REFERENCE`.

## Evidence Gate

Only official `VALID` evidence passes. P9-DEV-001 audit evidence remains invalid despite deviation resolution.

## Lineage Gate

Lifecycle elevation requires a complete raw-dataset-to-registry trace.

## Fingerprint Gate

Actual model and feature fingerprints must exactly match frozen expectations.

## Protocol Gate

Only hashes enumerated in the frozen policy are recognized; new hashes are never adopted automatically.

## Deviation Gate

Unresolved critical deviations block elevation. A resolved deviation does not rehabilitate invalid artifacts. P9-DEV-002 passes because scientific logical identity is preserved while both binary hashes remain recorded.

## Benchmark and Statistical Gates

Promotion requires strict development MAE superiority at the frozen 0% margin and statistical evidence that does not show material degradation. The threshold was not tuned. Development evidence does not substitute for final/external validation.

## Approval Gate

Promotion eligibility never means active. Explicit approval is required before canary eligibility. `SIMULATION_POLICY` approval is distinctly labelled and is never human approval.

## Decision Semantics and Auditability

Decisions are `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, or `NO_OP`, with policy identity, all gate results, failures, reason codes, evidence paths, deterministic explanation, and a stable content fingerprint excluding IDs/timestamps.

## Scenario-Based Validation and Safety Metrics

Eighteen scenarios were frozen before execution. Unsafe Transition Prevention Rate is correctly blocked unsafe attempts divided by all unsafe attempts. False allowance and false denial are reported independently.

## Final-Test Isolation

The engine rejects final-test performance/data requests and activation of the historical P9-DEV-002 audit mode. Phase 13 reads are zero.

## Limitations

Metadata scenarios cannot emulate all operational failures, approval uses a simulation fixture rather than organizational IAM, and no deployment/canary system is evaluated.
