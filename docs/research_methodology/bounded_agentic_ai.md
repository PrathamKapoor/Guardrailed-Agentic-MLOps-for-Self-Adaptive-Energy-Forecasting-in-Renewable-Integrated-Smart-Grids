# Bounded agentic AI decision support with governance firewall

## Motivation

The deterministic lifecycle (tracking → governance → monitoring → governed retraining → champion-challenger promotion/rollback) is complete but explanation-heavy: operators must inspect gate tables, decision logs, and registries to understand why the system acted (or refused to act). Phase 17 asks whether bounded Agentic AI can reduce that operational complexity while preserving every deterministic governance guarantee. The contribution is explicitly NOT autonomous AI management of ML systems: AI provides reasoning, explanation, and assistance while deterministic governance retains authority over safety-critical decisions.

## Architecture

`HUMAN OPERATOR → AGENTIC AI LAYER (recommendations / analysis) → DETERMINISTIC GOVERNANCE (ALLOW / DENY / APPROVE) → MLOPS LIFECYCLE ACTIONS`. The agent layer never replaces the deterministic lifecycle; it sits beside it. Implementation: `src/smartgrid_mlops/agents/` — base backend abstraction, schemas, planner, five specialist agents, bounded memory, orchestrator, governance firewall, validation, and audit.

## Agent roles

- **Drift analysis agent** — explains Phase 14/15 drift evidence: affected target, detectors triggered, severity semantics, rule-mapped possible causes, and an INVESTIGATE recommendation. Cannot change thresholds or approve retraining.
- **Retraining explanation agent** — explains Phase 15 decisions from recorded gate outputs ("Retraining was denied because: DATA_QUALITY_BLOCK ..."); data-quality denials request human review. Cannot rerun retraining.
- **Governance explanation agent** — explains Phase 13/16 promotion decisions (passed/failed gates, metrics, evidence references, why improved MAE alone was insufficient) and rollback records (trigger, verification checks, outcome). Cannot override governance.
- **Report generation agent** — deterministic experiment summaries, incident reports, model comparison reports, and audit explanations with measured generation time.
- **Evidence retrieval agent** — registered-source retrieval (drift events, decisions, registries, lineage, audits) with graceful missing-evidence handling; future and final-test data are unreachable.

## Input and output contracts

Agents receive structured evidence objects only (DriftEvent, RetrainingRequest/Decision, PromotionDecision, RollbackRecord, MLflow/registry metadata) — never raw filesystem access. Every output carries agent_id, agent_version, timestamp, input_evidence_refs, reasoning_summary, recommendation, confidence, limitations, and requires_human_review. Confidence is advisory only and is never a governance signal.

## Governance firewall

Every agent recommendation passes `agents/firewall.py`. Allowed advisory types: INVESTIGATE, SUMMARIZE, EXPLAIN, REQUEST_HUMAN_REVIEW, CREATE_REPORT. Blocked action types: PROMOTE_MODEL, ROLLBACK_MODEL, CHANGE_POLICY, START_RETRAINING, CHANGE_FEATURES — plus anything unknown (deny-by-default). Blocked attempts are audited as AGENT_RECOMMENDATION_BLOCKED. The forbidden events AGENT_MODEL_PROMOTED and AGENT_RETRAINING_STARTED cannot be emitted by construction (the audit module rejects them).

## Model backend and LLM safety boundary

The default backend is LOCAL_RULE_BASED: fully deterministic, offline, no external API — the system runs without any LLM. An optional LLM_BACKEND_INTERFACE documents the contract for future research: its output is UNTRUSTED ADVISORY TEXT that cannot execute commands, modify files, call training or deployment, or alter policies, and any recommendation derived from it must pass the firewall (scenarios A06/A07 exercise exactly this injection path).

## Human-in-the-loop design

Outputs that flag data-quality denials or blocked retrievals set requires_human_review=True, which emits HUMAN_REVIEW_REQUESTED. Humans remain the operators; agents reduce reading effort, not authority.

## Safety guarantees

No autonomous lifecycle control: promotion, rollback, retraining execution, feature changes, threshold changes, benchmark gates, and lifecycle transitions are all outside agent capabilities — structurally, not just by policy text. Memory stores only structured summaries, evidence references, and outputs; chain-of-thought, private reasoning traces, and prompts are never stored (field-filtered persistence, test-enforced). No final-test access exists in any agent code path.

## Evaluation evidence

The frozen A01–A08 suite (real repository evidence + injected adversarial advisories): 8/8 correct with complete contracts and evidence references; 3/3 unsafe recommendation attempts blocked (promotion, policy change, final-test retrieval); 0 governance bypasses; deterministic outputs on repeat; graceful missing-evidence handling; report generation 0.034 s and evidence retrieval 0.0025 s.

## Limitations

Explanations are rule-based template mappings over recorded evidence — they restate governance outcomes and cannot discover causes outside the recorded detector semantics. Scenario A06/A07 inject untrusted advisories synthetically; no real LLM output was evaluated. Efficiency numbers measure local rule-based generation on this device, not human time savings (H-AI-1's effort reduction is argued from artifact structure, not user studies). Confidence values are heuristic constants. The evaluation uses no final-test or future data.
