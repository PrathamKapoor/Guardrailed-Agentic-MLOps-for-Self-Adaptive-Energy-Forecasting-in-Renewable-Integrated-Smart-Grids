/** Centralized typed fetch-mock utility for the Stage 3 / Stage 4 frontend.
 *
 *  Design goals:
 *    1. EXACT path matching. No substring matching, no insertion-order
 *       dependence. Each API route has a unique normalized key.
 *    2. Query strings are stripped before matching (the API client builds
 *       URLs like `/api/governance/decisions?limit=20`, the mock key is
 *       `/api/governance/decisions`).
 *    3. Each test gets a fresh, independent mock. No global mutable state.
 *    4. Schemas are honest. Every default response satisfies the Pydantic
 *       schema mirrored in src/api/types.ts.
 *
 *  The previous implementation (a) relied on substring/endsWith matching
 *  with insertion-order precedence and (b) confused `responses` with
 *  `overrideByEndpoint`, so the default response was silently dropped when
 *  no per-endpoint override was set: `JSON.stringify(undefined)` returns
 *  the value `undefined`, not the string `"undefined"`, and the API
 *  client's `JSON.parse(text)` threw on every request. The whole suite
 *  then crashed inside React rendering.
 */
import { vi } from "vitest";
import type {
  AgentExplanationResponse, AgentTypes,
  AuditChainVerification, AuditEvent,
  ForecastInfo, ForecastMetric, ForecastSample,
  GovernanceDecisionRecord,
  HealthStatus, ModelRecord,
  MonitoringEvent, PolicyInfo,
} from "../api/types";

export interface FetchMockHandle {
  /** Install the fetch mock into globalThis. Idempotent. */
  install(): void;
  /** Per-endpoint response setter. Replaces the default for that endpoint. */
  set: <T>(endpoint: string, body: T | (() => T)) => void;
  /** Restore the original fetch. Idempotent. */
  restore(): void;
}

const defaultForecasts: ForecastInfo[] = [
  { target: "load", model: "random_forest", framework: "sklearn", feature_set: "B_lags_only",
    feature_count: 3, horizon: 24, n_samples: 1464, final_test_mae: 174.26,
    final_test_benchmark_mae: 101.14, final_test_relative_difference_pct: 72.29,
    final_test_status: "VERIFIED_LOCKED_TEST", strongest_benchmark: "RTS_DAY_AHEAD",
    development_mae: 285.10 },
  { target: "pv", model: "random_forest", framework: "sklearn", feature_set: "B_lags_only",
    feature_count: 3, horizon: 24, n_samples: 1464, final_test_mae: 36.12,
    final_test_benchmark_mae: 39.09, final_test_relative_difference_pct: -7.61,
    final_test_status: "VERIFIED_LOCKED_TEST", strongest_benchmark: "H24_DAILY_PERSISTENCE",
    development_mae: 44.18 },
  { target: "wind", model: "hist_gradient_boosting", framework: "sklearn", feature_set: "B_lags_only",
    feature_count: 3, horizon: 24, n_samples: 1464, final_test_mae: 778.84,
    final_test_benchmark_mae: 331.30, final_test_relative_difference_pct: 135.08,
    final_test_status: "VERIFIED_LOCKED_TEST", strongest_benchmark: "RTS_DAY_AHEAD",
    development_mae: 528.41 },
];

const defaultModels: ModelRecord[] = [
  { registry_id: "MLOPS-REF-LOAD-H24-V1", target: "load", horizon: 24, research_role: "REFERENCE",
    registry_state: "REGISTERED_REFERENCE", lifecycle_state: "REGISTERED_REFERENCE",
    model_family: "random_forest", framework: "sklearn", implementation_id: "RANDOM_FOREST",
    model_spec_fingerprint: "mspec-load", feature_set_id: "B_lags_only",
    feature_spec_fingerprint: "fspec", dataset_fingerprint: "dspec",
    protocol_hash: "phash", development_primary_metric: "MAE", development_mae: 285.10,
    strongest_benchmark: "RTS_DAY_AHEAD", benchmark_mae: 101.14,
    development_benchmark_gate: "BENCHMARK_GATE_FAIL", evidence_status: "VALID",
    selection_evidence: "Phase 11", created_from_phase: 11,
    final_test_performance_status: "VERIFIED_LOCKED_TEST" },
];

const defaultEvents: MonitoringEvent[] = [
  { event_id: "e1", timestamp: "2026-01-01T00:00:00Z", event_type: "performance_evaluation",
    target: "load", model: "random_forest", extra: { final_test_status: "VERIFIED_LOCKED_TEST" } },
];

const defaultPolicy: PolicyInfo = {
  policy_id: "SMARTGRID_DETERMINISTIC_GOVERNANCE", policy_version: "13.0.0",
  policy_checksum: "ee13cb0", governance_policy_fingerprint: "gov-fp",
  lifecycle_states: ["EXPERIMENTAL", "REGISTERED_REFERENCE", "ACTIVE"],
  reason_codes: ["BENCHMARK_GATE_FAILED", "STAGE_1_2_SAFETY_INTEGRATION_FAILED"],
  source_path: "config/governance/phase_13_policy.yaml",
};

const defaultDecision: GovernanceDecisionRecord = {
  decision_id: "d1", subject_id: "MLOPS-REF-LOAD-H24-V1",
  requested_transition: "PROMOTION_ELIGIBLE -> APPROVAL_PENDING",
  decision: "DENY", current_state: "PROMOTION_ELIGIBLE", proposed_state: "APPROVAL_PENDING",
  policy_id: "SMARTGRID_DETERMINISTIC_GOVERNANCE", policy_version: "13.0.0",
  policy_checksum: "ee13cb0", reason_codes: ["BENCHMARK_GATE_FAILED"],
  explanation: "DENY: Candidate fails the benchmark gate.",
  decision_content_fingerprint: "governance-decision-v1:sha256:abc",
  timestamp: "2026-01-01T00:00:00Z", gate_results: [], actor_type: "AGENT", simulation: true,
};

const defaultDecisions: GovernanceDecisionRecord[] = [defaultDecision];

const defaultAgentTypes: AgentTypes = {
  query_types: ["EXPLAIN_DRIFT"],
  allowed_recommendation_types: ["INVESTIGATE", "SUMMARIZE", "EXPLAIN",
                                    "REQUEST_HUMAN_REVIEW", "CREATE_REPORT"],
  notes: "Lifecycle action types are NOT exposed.",
};

const defaultAgentExplain: AgentExplanationResponse = {
  agent_id: "DRIFT_ANALYSIS_AGENT", agent_version: "1.0.0", query_id: "q1",
  input_evidence_refs: [], reasoning_summary: "The candidate model beats H24 daily persistence but lags the RTS day-ahead forecast. This is the expected outcome documented in the Phase 11 development set.",
  recommendation: "EXPLAIN", confidence: 0.8, limitations: "Bounded agent.",
  requires_human_review: false, timestamp: "2026-01-01T00:00:00Z",
  firewall_decision: "allowed", firewall_reason_code: "ALLOW_ADVISORY",
};

const defaultAuditEvents: AuditEvent[] = [
  { seq: 1, timestamp: "2026-01-01T00:00:00Z", type: "AGENT_QUERY_RECEIVED",
    record: { subject_id: "MLOPS-REF-LOAD-H24-V1" } },
];

const defaultAuditVerify: AuditChainVerification = {
  chain_ok: true, message: "OK", head: "n_events=1234",
};

const defaultHealth: HealthStatus = {
  status: "ok", api: "UP", research_pipeline: "READY", productization: "READY",
  artifacts: {}, notes: ["This is an offline evaluation system."],
};

const defaultForecastMetric: ForecastMetric = {
  target: "load", model: "random_forest", features: "B_lags_only",
  mae: 174.257, rmse: 231.271, smape: 4.717, nmae: 0.0474, nrmse: 0.0628,
};

// Per-target metric fixtures. Numbers mirror the values rendered on the
// real Forecasts page (load/pv/wind) so the target-switching test can find
// the expected formatted value.
const defaultLoadMetric: ForecastMetric = { ...defaultForecastMetric, mae: 174.257 };
const defaultPvMetric: ForecastMetric = {
  ...defaultForecastMetric, target: "pv", mae: 36.12, smape: 8.42, nmae: 0.0621, nrmse: 0.0891,
};
const defaultWindMetric: ForecastMetric = {
  ...defaultForecastMetric, target: "wind", mae: 778.84, smape: 18.31, nmae: 0.1821, nrmse: 0.2311,
};

const defaultForecastSample: ForecastSample = {
  timestamp: "2020-11-01T00:00:00Z", target: "load", model: "random_forest",
  prediction: 3000, actual: 3001, absolute_error: 1,
};

const defaultPredictions: ForecastSample[] = [defaultForecastSample];

/** Default mock response per endpoint (normalized path, no query string). */
export const DEFAULTS: Record<string, unknown> = {
  "/health": defaultHealth,
  "/api/forecasts": defaultForecasts,
  "/api/forecasts/load/metrics": defaultLoadMetric,
  "/api/forecasts/pv/metrics": defaultPvMetric,
  "/api/forecasts/wind/metrics": defaultWindMetric,
  "/api/forecasts/load/predictions": defaultPredictions,
  "/api/models": defaultModels,
  "/api/monitoring/events": defaultEvents,
  "/api/monitoring/drift": defaultEvents,
  "/api/governance/policy": defaultPolicy,
  "/api/governance/decisions": defaultDecisions,
  "/api/agents/types": defaultAgentTypes,
  "/api/agents/explain": defaultAgentExplain,
  "/api/audit/events": defaultAuditEvents,
  "/api/audit/verify": defaultAuditVerify,
};

/** Strip the query string and return only the pathname. */
function pathname(url: string): string {
  const q = url.indexOf("?");
  return q === -1 ? url : url.slice(0, q);
}

/** Build a fresh, independent fetch-mock handle. The handle is bound to the
 *  current `responses` snapshot. Setting per-endpoint overrides does not
 *  mutate the imported DEFAULTS object; the test owns the snapshot. */
export function makeFetchMock(overrides: Record<string, unknown> = {}): FetchMockHandle {
  // The router keys are `<METHOD> <path>` (e.g. `GET /api/governance/decisions`,
  // `POST /api/governance/decisions`). Method matters because the same path
  // is used for both the GET list and the POST evaluate request.
  const responses: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(DEFAULTS)) responses[`GET ${k}`] = v;
  for (const [k, v] of Object.entries(overrides)) responses[`GET ${k}`] = v;
  // Some endpoints are also reachable as POST. The defaults below set the
  // POST response to the same data the GET would return. Tests can override.
  const POST_DEFAULTS: Record<string, unknown> = {
    "POST /api/governance/decisions": defaultDecision,
    "POST /api/agents/explain": defaultAgentExplain,
  };
  for (const [k, v] of Object.entries(POST_DEFAULTS)) {
    if (!(k in responses)) responses[k] = v;
  }
  const overrideByEndpoint: Map<string, (() => unknown) | unknown> = new Map();
  let installed = false;

  const set = <T,>(endpoint: string, body: T | (() => T)) => {
    // Accept either "PATH", "METHOD PATH", or "method PATH". Normalize.
    const parts = endpoint.split(/\s+/);
    if (parts.length === 1) overrideByEndpoint.set(`GET ${pathname(parts[0]!)}`, body);
    else overrideByEndpoint.set(`${parts[0]!.toUpperCase()} ${pathname(parts[1]!)}`, body);
  };

  const install = () => {
    if (installed) return;
    installed = true;
    const mockFn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = (init?.method ?? "GET").toUpperCase();
      const path = pathname(url);
      const key = `${method} ${path}`;
      const lookup = (v: unknown): Response => {
        // An override that is already a Response-like object wins as-is.
        if (v && typeof v === "object" && "status" in v && "text" in v) {
          return v as Response;
        }
        return toResponse(v);
      };
      if (overrideByEndpoint.has(key)) {
        const v = overrideByEndpoint.get(key);
        const body = typeof v === "function" ? (v as () => unknown)() : v;
        return lookup(body);
      }
      if (Object.prototype.hasOwnProperty.call(responses, key)) {
        return lookup(responses[key]);
      }
      return toResponse(
        { error: { type: "http", status: 404, detail: `not mocked: ${key}`, path } },
        404,
      );
    });
    vi.stubGlobal("fetch", mockFn as unknown as typeof fetch);
  };

  const restore = () => {
    if (!installed) return;
    installed = false;
    vi.unstubAllGlobals();
  };

  return { install, set, restore };
}

/** Convenience: build + install + auto-restore in vitest. */
export function installFetchMock(overrides: Record<string, unknown> = {}): FetchMockHandle {
  const h = makeFetchMock(overrides);
  h.install();
  return h;
}

function toResponse(body: unknown, status = 200): Response {
  const ok = status >= 200 && status < 300;
  const text = JSON.stringify(body);
  return {
    status, ok, statusText: ok ? "OK" : "Error",
    text: async () => text,
    json: async () => body,
  } as Response;
}
