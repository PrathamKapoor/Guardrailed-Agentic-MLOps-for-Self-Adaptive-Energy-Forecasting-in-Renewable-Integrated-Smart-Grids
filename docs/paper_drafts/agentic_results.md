# Agentic ablation results (Phase 18, development/simulation)

All numbers come from the frozen protocol (`artifacts/experimental_design/phase_18_agentic_comparison_protocol_freeze.yaml`) executed by `scripts/run_agentic_comparison.py` over real Phase 13–17 evidence. This is an MLOps operational-assistance experiment; agent accuracy is never compared with model accuracy.

## Decision consistency (the critical rule)

Across all 8 scenario families (D01–D08), the deterministic-only and agent-assisted systems produced **identical lifecycle outcomes** — the same drift verdicts, the same retraining denial, the same challenger no-promotion state, the same promotion rejection, the same rollback restoration. **Lifecycle decision difference: 0.** The agent changes how quickly an operator can understand the system, never what the system decides.

## Safety equivalence

Governance violations: **0** in both systems. Unsafe action executions: **0**. The two adversarial probes were blocked exactly as in Phase 17: an injected PROMOTE_MODEL advisory was refused by the governance firewall, and a final-test retrieval request was refused by the evidence guard. The protected-artifact hash snapshot confirms no policy, threshold, feature, model, or registry change occurred during the ablation.

## Explanation quality

Both workflows achieved 8/8 completeness and 8/8 correctness — the deterministic operator can always eventually derive the facts from raw artifacts. The agent's contribution is traceability and speed: every agent answer arrives with explicit evidence references and the conflict/missing-evidence behaviors required for operational trust (A05 graceful no-fabrication; A06 flags an APPROVE record with failed gates as inconsistent evidence requesting human review; A07/A08 refuse unsafe and final-test requests).

## Efficiency

Under the frozen human-inspection cost model (3.0 s per artifact inspection, 0.05 s per record scanned) versus measured agent execution plus frozen reading/verification constants:

| Workflow | Mean steps | Mean lookups | Mean estimated time |
| --- | ---: | ---: | ---: |
| Deterministic (manual inspection) | 1.25 | 1.25 | 17.3 s |
| Agent-assisted | 2.0 | 1.0 | 5.0 s |

**Total efficiency improvement: 71.8%.** The agentic path deliberately adds an explicit verification step (2 steps) while eliminating bulk record scanning — its time saving comes from replacing many-record manual inspection with one measured agent call plus one verification read of cited evidence.

## Interpretation discipline

These results support H18-1 (analysis-time reduction under the frozen operational model), H18-2 (equal-or-better traceability with explicit references), H18-3 (no added violations), and H18-4 (identical decisions) — within a simulated operational setting with a cost-model approximation of human workload, no production operators, and a rule-based agent backend requiring no LLM. The claim is bounded assistance, not autonomy: the agent layer demonstrably reduces the reading burden of governance artifacts while deterministic governance retains every safety-critical decision.
