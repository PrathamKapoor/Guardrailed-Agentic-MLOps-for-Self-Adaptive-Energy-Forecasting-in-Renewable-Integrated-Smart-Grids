# Deterministic governance policy gates

| Gate | Purpose | Required for | Failure action | Reason code | Evidence dependency |
| --- | --- | --- | --- | --- | --- |
| EVIDENCE_VALIDITY_GATE | Reject invalid/audit-only evidence | Official lifecycle elevation | DENY | EVIDENCE_INVALID | Research registry / evidence status |
| LINEAGE_COMPLETENESS_GATE | Require dataset-to-registry trace | Lifecycle elevation | DENY | LINEAGE_INCOMPLETE | Phase 12 lineage index |
| MODEL_SPEC_FINGERPRINT_GATE | Bind exact model specification | Registry/promotion | DENY | MODEL_SPEC_FINGERPRINT_MISMATCH | Frozen model fingerprint |
| FEATURE_SPEC_FINGERPRINT_GATE | Bind exact feature identity | Registry/promotion | DENY | FEATURE_SPEC_FINGERPRINT_MISMATCH | Frozen feature fingerprint |
| PROTOCOL_COMPATIBILITY_GATE | Allow recognized freezes only | Lifecycle elevation | DENY | PROTOCOL_MISMATCH | Accepted protocol hashes |
| REPRODUCIBILITY_METADATA_GATE | Require complete metadata | Lifecycle elevation | DENY | REPRODUCIBILITY_INCOMPLETE | Reproducibility manifest |
| DEVIATION_STATUS_GATE | Block unresolved critical deviations | Lifecycle elevation | DENY | UNRESOLVED_DEVIATION | Deviation records |
| BENCHMARK_GATE | Require strict development superiority | Promotion and beyond | DENY | BENCHMARK_GATE_FAILED | Phase 11 paired evidence |
| STATISTICAL_EVIDENCE_GATE | Reject demonstrated degradation/insufficiency | Promotion and beyond | DENY | STATISTICAL_EVIDENCE_FAILED | Statistical status |
| APPROVAL_GATE | Prevent automatic production-style elevation | Canary eligibility | REQUIRE_APPROVAL / DENY | APPROVAL_REQUIRED / APPROVAL_REJECTED | Explicit approval record |
| STATE_TRANSITION_GATE | Enforce lifecycle graph | Every transition | DENY | INVALID_STATE_TRANSITION | Policy transition rules |
| FINAL_TEST_POLICY_GATE | Preserve Phase 13 isolation | Every transition | DENY | FINAL_TEST_POLICY_VIOLATION | Final-test access request |
| POLICY_VERSION_GATE | Bind decision to immutable policy | Every transition | DENY | POLICY_VERSION_MISMATCH | Policy ID/version/checksum |
