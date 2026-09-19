# Controlled ablation: deterministic MLOps vs bounded agentic MLOps

## Motivation

Phases 13–17 established a deterministic governance stack and a bounded agent layer beside it. Phase 18 asks whether the agent layer provides measurable operational benefit while preserving identical governance safety. The experiment is explicitly an MLOps operational-assistance ablation — never a comparison of agent accuracy against model accuracy, and never a test of "AI making better model decisions".

## Comparison design

System A (DETERMINISTIC_ONLY) runs the recorded lifecycle — monitoring → governance → retraining decision → challenger evaluation → promotion decision — with an operator manually interpreting raw metrics, logs, registry information, and audit events. System B (BOUNDED_AGENTIC_MLOPS) executes the same tasks with agent explanation/retrieval between monitoring and human decision support, in front of the same deterministic governance. Both systems consume identical recorded Phase 13–17 evidence; the critical rule is that lifecycle outcomes must be identical.

## Workflows

The deterministic baseline (`agentic_evaluation/deterministic_workflow.py`) models manual inspection: one step per artifact opened, one lookup per artifact, records scanned counted per task, time estimated with a frozen human-inspection cost model. The agentic workflow (`agentic_workflow.py`) issues one bounded orchestrator query per task, then the operator reads the summary and performs one verification inspection of the cited evidence; agent execution time is measured and reading/verification use the frozen cost model. Neither workflow trains, promotes, rolls back, or modifies anything — a protected-artifact snapshot before and after enforces no model changes.

## Tasks and quality checks

Eight frozen task families (D01 drift investigation, D02 retraining decision explanation, D03 challenger comparison, D04 promotion rejection explanation, D05 rollback investigation, D06 audit preparation, D07 model lineage investigation, D08 incident summary generation) are built from real repository evidence. Eight agent quality checks (A01–A04 correct explanations from real evidence; A05 missing-evidence handling; A06 conflicting-evidence handling — an APPROVE record with failed gates must be flagged inconsistent with human review; A07 unsafe-request refusal; A08 final-test-request refusal) verify the agent layer reused from Phase 17.

## Metrics

Efficiency: completion steps, evidence lookups, estimated time. Quality: completeness, correctness, evidence references, missing-information handling. Safety: governance violations, unsafe recommendations, policy bypass attempts. Consistency: identical lifecycle, promotion, and rollback decisions per scenario.

## Safety boundaries

Success criteria frozen in the protocol: lifecycle decision difference 0, governance bypass 0, unsafe action execution 0. The agent remains firewalled to advisory types; the forbidden agent audit events remain impossible; no final-test path exists. Protected artifacts (Phase 13/15/16 policies, monitoring config, all registries) are hash-snapshotted before and after the run.

## Results summary

8/8 scenarios: identical lifecycle outcomes (difference 0); deterministic and agentic completeness/correctness 8/8 each; agent quality checks 8/8; 0 governance violations; unsafe probes blocked (A07 advisory promotion, A08 final-test retrieval). Estimated operational time fell from a mean 17.3 s (manual-inspection model) to 5.0 s (agent-assisted) — a 71.8% improvement under the frozen cost model. Steps are 2 for the agentic workflow versus 1–2 artifact inspections for deterministic tasks (agent path adds an explicit verification step while removing record scanning); the time saving comes from replacing bulk record scanning with one measured agent call plus one verification read.

## Limitations

Operational tasks are simulated and human workload is approximated by a frozen cost model; no production operators were evaluated; agent quality depends on evidence availability; the rule-based backend requires no LLM and results demonstrate bounded assistance, not autonomy; timing mixes measured agent execution with estimated human constants and should be read as an operational model, not a user study.
