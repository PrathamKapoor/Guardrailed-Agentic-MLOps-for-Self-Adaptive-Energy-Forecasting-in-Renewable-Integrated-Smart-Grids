/** Demo Mode data (Stage 4). Read-only and deterministic.
 *
 *  This file does NOT fabricate research results. Every number / fact comes
 *  from the existing Phase 11 / Phase 13 / Phase 19 artefacts. The demo
 *  module is a presentation layer that sequences the real evidence; it does
 *  not invent new agent actions or governance decisions.
 *
 *  Source-of-truth: the Stage 2 FastAPI service. This module is a snapshot
 *  of what the API would return for the same target + decision ids, taken
 *  once at build time. Reset is a no-op (state is the snapshot, not mutable).
 *
 *  The build pipeline (src/test/syncDemoData.test.ts) verifies the snapshot
 *  matches the live API; if the artefacts change, the snapshot is regenerated.
 */

// ----- Primary scenario: PV forecasting + benchmark comparison + governance firewall -----

export interface DemoStep {
  id: string;
  title: string;
  kind: "system" | "forecast" | "monitoring" | "agent" | "governance" | "audit" | "safety";
  body: string;
  // Optional references into the real API data; the renderer displays these.
  api_refs?: { kind: "forecast" | "governance" | "monitoring" | "agent" | "audit"; target?: string };
  highlight?: string; // inline value to call out (e.g. "−7.61%")
}

export const PRIMARY_SCENARIO: { id: string; title: string; steps: DemoStep[] } = {
  id: "primary-pv-wins-load-wind-lose",
  title: "Forecasting → drift detection → agent analysis → governance → audit",
  steps: [
    {
      id: "step-1-overview",
      kind: "system",
      title: "1. System overview",
      body: "Three frozen finalists monitor the RTS-GMLC 2020 smart-grid dataset at horizon 24 hours. The dashboard and the agent layer are downstream of the deterministic governance engine; agents do not control the lifecycle.",
      highlight: "OFFLINE EVALUATION · 3 frozen finalists",
    },
    {
      id: "step-2-forecasts",
      kind: "forecast",
      title: "2. Frozen forecasts (final test, 2020-11-01 → 2020-12-31)",
      body: "On the locked final-test partition (1464 hourly rows per target) the frozen models report the following MAE against the published external benchmarks.",
      api_refs: { kind: "forecast" },
    },
    {
      id: "step-3-monitoring",
      kind: "monitoring",
      title: "3. Monitoring detects model health and prediction distribution",
      body: "The monitoring layer emits performance, prediction-distribution, and model-health events derived from the frozen final-test evidence. Severity indicators are based on the recorded final-test status (VERIFIED_LOCKED_TEST for all three frozen finalists; 0 live alerts because this is offline evaluation).",
      api_refs: { kind: "monitoring" },
    },
    {
      id: "step-4-agent",
      kind: "agent",
      title: "4. Bounded agent investigates",
      body: "The bounded agent (drift analysis, performance, security, governance, redteam) reads the monitoring evidence through the existing Orchestrator and produces an advisory recommendation. The recommendation is one of INVESTIGATE / SUMMARIZE / EXPLAIN / REQUEST_HUMAN_REVIEW / CREATE_REPORT. Lifecycle action types are blocked by the existing governance firewall at the audit-module level.",
      api_refs: { kind: "agent" },
    },
    {
      id: "step-5-governance",
      kind: "governance",
      title: "5. Deterministic governance evaluates the recommendation",
      body: "The frozen Phase 13 policy (13-state machine, 12 deterministic gates) evaluates the candidate. The PV candidate is benchmark-eligible (frozen random forest beats H24 daily persistence by 7.61%); the LOAD and WIND candidates are not.",
      api_refs: { kind: "governance" },
    },
    {
      id: "step-6-decision",
      kind: "governance",
      title: "6. Decision",
      body: "Governance produces a deterministic decision with a SHA-256 decision_content_fingerprint. PV is approved for canary; LOAD and WIND would be denied because their frozen reference models do not beat the published benchmarks on the 2-month final test.",
      highlight: "decision_content_fingerprint: sha256:deterministic",
    },
    {
      id: "step-7-audit",
      kind: "audit",
      title: "7. Audit trail",
      body: "The decision is appended to the existing evidence-ledger JSONL. The /api/audit/verify endpoint reports the JSONL well-formedness — the existing implementation does not have a cryptographic hash chain, and the UI is honest about that.",
      api_refs: { kind: "audit" },
      highlight: "Audit structure: VALID JSONL",
    },
  ],
};

// ----- Safety scenario: agent recommends a lifecycle action, governance blocks it -----

export const SAFETY_SCENARIO: { id: string; title: string; steps: DemoStep[] } = {
  id: "safety-lifecycle-blocked",
  title: "Safety boundary — agent recommends a lifecycle action, governance blocks it",
  steps: [
    {
      id: "safety-1-context",
      kind: "system",
      title: "1. Context",
      body: "A human operator types a lifecycle action in the Agent assistant. The frontend safety gate intercepts lifecycle action types before the request reaches the agent layer.",
      highlight: "PROMOTE / DEPLOY / ROLLBACK / RETRAIN / CHANGE_POLICY / MODIFY_MODEL / MODIFY_FEATURES",
    },
    {
      id: "safety-2-frontend-gate",
      kind: "safety",
      title: "2. Frontend safety gate",
      body: "The frontend matches the input against the 7 lifecycle action types and renders the ACTION BLOCKED notice. No mutation is sent.",
      highlight: "ACTION BLOCKED · Agents are advisory only",
    },
    {
      id: "safety-3-no-bypass",
      kind: "governance",
      title: "3. Even if the gate were bypassed, governance would still block",
      body: "The deterministic governance engine independently evaluates any candidate transition. The frozen Phase 13 policy's benchmark gate + statistical evidence gate + fingerprint checks would block unsafe transitions. The decision fingerprint is SHA-256 over the canonical content, so identical inputs produce identical decisions.",
    },
    {
      id: "safety-4-no-fabrication",
      kind: "safety",
      title: "4. No fake execution",
      body: "The UI never implies that the agent executed the lifecycle action. The bounded agent is advisory only. The deterministic governance engine is the only path that can move lifecycle state, and it requires the candidate to pass all frozen gates.",
      highlight: "AGENT RECOMMENDATION ≠ GOVERNANCE DECISION",
    },
    {
      id: "safety-5-audit-trail",
      kind: "audit",
      title: "5. Audit trail",
      body: "The attempt to execute a lifecycle action is recorded as an AGENT_QUERY_RECEIVED event in the existing evidence-ledger JSONL. The audit page exposes this event list.",
      api_refs: { kind: "audit" },
    },
  ],
};

// ----- Final result interpretation: the honest mixed outcome (matches Phase 19) -----

export const FINAL_INTERPRETATION = {
  pv: {
    verdict: "Better than benchmark",
    relative_difference_pct: -7.61,
    text: "The frozen random forest for PV beats the H24 daily persistence benchmark on MAE.",
  },
  load: {
    verdict: "Worse than benchmark",
    relative_difference_pct: 72.29,
    text: "The frozen random forest for LOAD is dominated by the published RTS_DAY_AHEAD forecast on this 2-month window. We report this honestly.",
  },
  wind: {
    verdict: "Worse than benchmark",
    relative_difference_pct: 135.08,
    text: "The frozen hist gradient boosting for WIND is dominated by RTS_DAY_AHEAD. The system does not claim universal superiority.",
  },
} as const;

// Helper: lifecycle action types (also exported via api/agentSafety.ts).
// Listed here for the demo renderer to colour the step indicator.
export const LIFECYCLE_ACTION_TYPES = [
  "PROMOTE", "DEPLOY", "ROLLBACK", "RETRAIN",
  "CHANGE_POLICY", "MODIFY_MODEL", "MODIFY_FEATURES",
] as const;
