/** Centralized typed API client. Every HTTP call in the app goes through here.
 *  No raw fetch() is used in components; this enforces a single place to
 *  update the API contract and prevents bypass of the typed wrapper.
 *
 *  The client never reads files directly and never mutates the backend; it
 *  consumes the Stage 2 FastAPI service exclusively.
 */
import type {
  AgentExplanationRequest,
  AgentExplanationResponse,
  AgentTypes,
  APIError,
  AuditChainVerification,
  AuditEvent,
  ForecastInfo,
  ForecastMetric,
  ForecastSample,
  GovernanceDecisionRecord,
  GovernanceEvaluateRequest,
  HealthStatus,
  ModelRecord,
  MonitoringEvent,
  PolicyInfo,
  Target,
  ResearchDataset,
  ResearchRunRequest,
  ResearchRunResult,
} from "./types";

export class APIClient {
  constructor(private readonly baseURL: string = "/api") {}

  private async get<T>(path: string): Promise<T> {
    const res = await fetch(this._url(path), { method: "GET" });
    return this._handle<T>(res, path);
  }

  /** GET against the backend root, bypassing the "/api" base prefix.
   *  Used for /health, which the backend serves outside /api. */
  private async rootGet<T>(path: string): Promise<T> {
    const res = await fetch(path, { method: "GET" });
    return this._handle<T>(res, path);
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(this._url(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return this._handle<T>(res, path);
  }

  private _url(path: string): string {
    if (path.startsWith("http")) return path;
    const base = this.baseURL.replace(/\/$/, "");
    const tail = path.startsWith("/") ? path : `/${path}`;
    return base ? `${base}${tail}` : tail;
  }

  private async _handle<T>(res: Response, path: string): Promise<T> {
    const text = await res.text();
    if (!res.ok) {
      let err: APIError | null = null;
      try { err = text ? JSON.parse(text) as APIError : null; } catch { /* not JSON */ }
      const detail = err?.error?.detail ?? text ?? res.statusText;
      throw new APIRequestError(res.status, detail, path, err);
    }
    if (!text) return {} as T;
    return JSON.parse(text) as T;
  }

  // ---- Health ----------------------------------------------------------------
  health(): Promise<HealthStatus> { return this.rootGet<HealthStatus>("/health"); }

  // ---- Forecasts -------------------------------------------------------------
  listForecasts(): Promise<ForecastInfo[]> { return this.get<ForecastInfo[]>("/forecasts"); }

  getForecast(target: Target): Promise<ForecastInfo> {
    return this.get<ForecastInfo>(`/forecasts/${encodeURIComponent(target)}`);
  }

  getForecastMetrics(target: Target): Promise<ForecastMetric> {
    return this.get<ForecastMetric>(`/forecasts/${encodeURIComponent(target)}/metrics`);
  }

  getForecastPredictions(target: Target, limit = 1464): Promise<ForecastSample[]> {
    return this.get<ForecastSample[]>(`/forecasts/${encodeURIComponent(target)}/predictions?limit=${limit}`);
  }

  // ---- Models ----------------------------------------------------------------
  listModels(): Promise<ModelRecord[]> { return this.get<ModelRecord[]>("/models"); }

  getModel(modelId: string): Promise<ModelRecord> {
    return this.get<ModelRecord>(`/models/${encodeURIComponent(modelId)}`);
  }

  // ---- Monitoring -------------------------------------------------------------
  listMonitoringEvents(opts: { eventType?: string; target?: string } = {}): Promise<MonitoringEvent[]> {
    const qs = new URLSearchParams();
    if (opts.eventType) qs.set("event_type", opts.eventType);
    if (opts.target) qs.set("target", opts.target);
    const q = qs.toString();
    return this.get<MonitoringEvent[]>(`/monitoring/events${q ? `?${q}` : ""}`);
  }

  getMonitoringEvent(eventId: string): Promise<MonitoringEvent> {
    return this.get<MonitoringEvent>(`/monitoring/events/${encodeURIComponent(eventId)}`);
  }

  listDrift(): Promise<MonitoringEvent[]> { return this.get<MonitoringEvent[]>("/monitoring/drift"); }

  // ---- Governance -------------------------------------------------------------
  getPolicy(): Promise<PolicyInfo> { return this.get<PolicyInfo>("/governance/policy"); }

  evaluateGovernance(req: GovernanceEvaluateRequest): Promise<GovernanceDecisionRecord> {
    return this.post<GovernanceDecisionRecord>("/governance/decisions", req);
  }

  listDecisions(limit = 100): Promise<Array<Record<string, unknown>>> {
    return this.get<Array<Record<string, unknown>>>(`/governance/decisions?limit=${limit}`);
  }

  // ---- Agents -----------------------------------------------------------------
  getAgentTypes(): Promise<AgentTypes> { return this.get<AgentTypes>("/agents/types"); }

  explain(req: AgentExplanationRequest): Promise<AgentExplanationResponse> {
    return this.post<AgentExplanationResponse>("/agents/explain", req);
  }

  // ---- Audit -----------------------------------------------------------------
  listAuditEvents(opts: { eventType?: string; subject?: string; limit?: number } = {}): Promise<AuditEvent[]> {
    const qs = new URLSearchParams();
    if (opts.eventType) qs.set("event_type", opts.eventType);
    if (opts.subject) qs.set("subject", opts.subject);
    if (opts.limit) qs.set("limit", String(opts.limit));
    const q = qs.toString();
    return this.get<AuditEvent[]>(`/audit/events${q ? `?${q}` : ""}`);
  }

  verifyAudit(): Promise<AuditChainVerification> {
    return this.get<AuditChainVerification>("/audit/verify");
  }

  // ---- Research console (user datasets + local forecasting runs) -------------
  listResearchDatasets(): Promise<ResearchDataset[]> {
    return this.get<ResearchDataset[]>("/research/datasets");
  }

  uploadResearchDataset(file: File): Promise<ResearchDataset> {
    // Multipart upload; the browser sets the Content-Type boundary.
    const form = new FormData();
    form.append("file", file);
    return fetch(this._url("/research/datasets"), { method: "POST", body: form })
      .then((res) => this._handle<ResearchDataset>(res, "/research/datasets"));
  }

  runResearch(req: ResearchRunRequest): Promise<ResearchRunResult> {
    return this.post<ResearchRunResult>("/research/runs", req);
  }

  listResearchRuns(): Promise<ResearchRunResult[]> {
    return this.get<ResearchRunResult[]>("/research/runs");
  }
}

export class APIRequestError extends Error {
  constructor(public status: number, public detail: string, public path: string,
              public errorBody: APIError | null) {
    super(`API ${status} on ${path}: ${detail}`);
    this.name = "APIRequestError";
  }
}

/** Resolve the API base URL.
 *
 *  - In `npm run dev` (Vite dev server), leave the base URL as the
 *    relative path "/api"; `vite.config.ts` proxies `/api` and `/health`
 *    to the backend at http://127.0.0.1:8000.
 *  - In a production build (`npm run build` or `npm run preview`), the
 *    `VITE_API_BASE_URL` environment variable is inlined at build time.
 *    If unset, the build falls back to the relative path "/api", which
 *    works when the built static files are served from the same origin
 *    as the backend (e.g. behind a single reverse proxy).
 *  - A test environment (Vitest jsdom) uses the relative path; the test
 *    suite stubs globalThis.fetch and never makes a real network call.
 */
function resolveBaseURL(): string {
  // import.meta.env is replaced statically by Vite; the conditional is
  // tree-shaken when VITE_API_BASE_URL is empty, so the production bundle
  // contains the configured value (or "/api") and nothing else.
  const fromEnv = (import.meta as any).env?.VITE_API_BASE_URL;
  if (typeof fromEnv === "string" && fromEnv.trim().length > 0) return fromEnv.trim();
  return "/api";
}

export const api = new APIClient(resolveBaseURL());
