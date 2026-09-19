/** TypeScript types mirroring the Stage 2 FastAPI Pydantic schemas. The frontend
 *  must not invent fields; if an API contract change is needed, update both
 *  the backend schema and this file in the same commit.
 */

// ---- Forecasts -------------------------------------------------------------

export type Target = "load" | "wind" | "pv";
export const TARGETS: readonly Target[] = ["load", "wind", "pv"] as const;

export interface ForecastInfo {
  target: Target;
  model: string;
  framework: string;
  feature_set: string;
  feature_count: number;
  horizon: number;
  n_samples: number;
  final_test_mae: number;
  final_test_benchmark_mae: number;
  final_test_relative_difference_pct: number;
  final_test_status: string;
  strongest_benchmark: string;
  development_mae: number;
}

export interface ForecastMetric {
  target: Target;
  model: string;
  features: string;
  mae: number;
  rmse: number;
  smape: number;
  nmae: number;
  nrmse: number;
}

export interface ForecastSample {
  timestamp: string;
  target: Target;
  model: string;
  prediction: number;
  actual: number;
  absolute_error: number;
}

// ---- Models ----------------------------------------------------------------

export interface ModelRecord {
  registry_id: string;
  target: Target;
  horizon: number;
  research_role: string;
  registry_state: string;
  lifecycle_state: string;
  model_family: string;
  framework: string;
  implementation_id: string;
  model_spec_fingerprint: string;
  feature_set_id: string;
  feature_spec_fingerprint: string;
  dataset_fingerprint: string;
  protocol_hash: string;
  development_primary_metric: string;
  development_mae: number;
  strongest_benchmark: string;
  benchmark_mae: number;
  development_benchmark_gate: string;
  evidence_status: string;
  selection_evidence: string;
  created_from_phase: number;
  final_test_performance_status: string;
}

// ---- Monitoring -------------------------------------------------------------

export interface MonitoringEvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  target: string;
  model: string;
  extra: Record<string, unknown>;
}

// ---- Governance ------------------------------------------------------------

export interface PolicyInfo {
  policy_id: string;
  policy_version: string;
  policy_checksum: string;
  governance_policy_fingerprint: string;
  lifecycle_states: string[];
  reason_codes: string[];
  source_path: string;
}

export interface GovernanceDecisionRecord {
  decision_id: string;
  subject_id: string;
  requested_transition: string;
  decision: "ALLOW" | "DENY" | "REQUIRE_APPROVAL" | "NO_OP";
  current_state: string;
  proposed_state: string;
  policy_id: string;
  policy_version: string;
  policy_checksum: string;
  reason_codes: string[];
  explanation: string;
  decision_content_fingerprint: string;
  timestamp: string;
  gate_results: Array<Record<string, unknown>>;
  actor_type: string;
  simulation: boolean;
}

export interface GovernanceEvaluateRequest {
  subject_id: string;
  current_state: string;
  proposed_state: string;
  actor_type?: string;
  simulation?: boolean;
  claimed_policy_id?: string | null;
  claimed_policy_version?: string | null;
  claimed_policy_checksum?: string | null;
  evidence_status?: string;
  benchmark_gate?: string;
  approval_state?: string;
}

// ---- Agents -----------------------------------------------------------------

export type FirewallDecision = "allowed" | "blocked";
export type Recommendation =
  | "INVESTIGATE"
  | "SUMMARIZE"
  | "EXPLAIN"
  | "REQUEST_HUMAN_REVIEW"
  | "CREATE_REPORT";

export interface AgentTypes {
  query_types: string[];
  allowed_recommendation_types: Recommendation[];
  notes: string;
}

export interface AgentExplanationRequest {
  query: string;
  context: Record<string, unknown>;
}

export interface AgentExplanationResponse {
  agent_id: string;
  agent_version: string;
  query_id: string;
  input_evidence_refs: string[];
  reasoning_summary: string;
  recommendation: Recommendation;
  confidence: number;
  limitations: string;
  requires_human_review: boolean;
  timestamp: string;
  firewall_decision: FirewallDecision;
  firewall_reason_code: string;
}

// ---- Audit -----------------------------------------------------------------

export interface AuditEvent {
  seq: number | null;
  timestamp: string;
  type: string;
  record: Record<string, unknown>;
}

export interface AuditChainVerification {
  chain_ok: boolean;
  message: string;
  head: string;
}

// ---- Health -----------------------------------------------------------------

export interface HealthStatus {
  status: string;
  api: string;
  research_pipeline: string;
  productization: string;
  artifacts: Record<string, { exists: boolean; size: number; sha256?: string | null }>;
  notes: string[];
}

// ---- Error envelope (typed HTTP errors from main.py) ---------------------

export interface APIError {
  error: {
    type: "http" | "internal";
    status: number;
    detail: string;
    path: string;
  };
}

// ---- Research console (local, user-provided datasets; advisory only) ------
export interface ResearchDataset {
  dataset_id: string;
  name: string;
  source: string;
  license: string;
  uploaded_at: string;
  rows: number;
  columns: string[];
  timestamp_column: string;
  numeric_columns: string[];
  start: string;
  end: string;
  sha256: string;
}

export interface ResearchRunRequest {
  dataset_id: string;
  target: string;
  model: "ridge" | "hist_gradient_boosting" | "seasonal_naive";
  test_fraction: number;
}

export interface ResearchRunMetrics {
  mae: number;
  rmse: number;
  benchmark_mae: number;
  benchmark: string;
  improvement_pct: number;
  n_train: number;
  n_test: number;
}

export interface ResearchRenewableInsight {
  available: boolean;
  renewable_share: number | null;
  load_matching_ratio: number | null;
  surplus_hours: number | null;
  correlation_load_renewable: number | null;
  note: string;
}

export interface ResearchAdvisoryItem {
  recommendation_type: "EXPLAIN" | "INVESTIGATE" | "CREATE_REPORT";
  text: string;
}

export interface ResearchRunResult {
  run_id: string;
  dataset_id: string;
  target: string;
  model: string;
  created_at: string;
  split: string;
  metrics: ResearchRunMetrics;
  renewable: ResearchRenewableInsight;
  advisory: ResearchAdvisoryItem[];
  series: Array<{ timestamp: string; actual: number; prediction: number }>;
}
