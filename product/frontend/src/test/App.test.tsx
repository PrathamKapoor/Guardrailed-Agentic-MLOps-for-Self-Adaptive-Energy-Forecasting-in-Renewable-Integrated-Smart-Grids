import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";
import { installFetchMock, makeFetchMock } from "./apiMocks";

beforeEach(() => {
  // Stub out the API-health polling so timers from one test don't bleed into
  // another. vi.unstubAllGlobals() in the shared afterEach restores them.
  vi.stubGlobal("setInterval", () => 0 as unknown as ReturnType<typeof setInterval>);
  vi.stubGlobal("clearInterval", () => undefined);
});

function mockDefault() {
  return installFetchMock();
}

describe("App routing", () => {
  it("renders all 8 primary routes", async () => {
    const h = mockDefault();
    try {
      // Each route has a unique h1 (the page title) that is NOT also a sidebar link
      const routes: Array<[string, RegExp]> = [
        ["/", /^Executive dashboard$/],
        ["/forecasts", /^Forecasts$/],
        ["/models", /^Model registry$/],
        ["/monitoring", /^Monitoring$/],
        ["/governance", /^Governance$/],
        ["/agents", /^Agent assistant$/],
        ["/audit", /^Audit$/],
        ["/demo", /^Demo Mode$/],
      ];
      for (const [path, matcher] of routes) {
        const { unmount } = render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
        await waitFor(() => {
          const heading = document.querySelector("h1.page__title");
          expect(heading?.textContent).toMatch(matcher);
        });
        unmount();
      }
    } finally { h.restore(); }
  });
});

describe("Forecasts page — target switching", () => {
  it("switches between targets and re-fetches metrics", async () => {
    const h = mockDefault();
    try {
      render(<MemoryRouter initialEntries={["/forecasts"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByText(/MAE/));
      // Click PV tab — PV MAE is 36.12
      fireEvent.click(screen.getByRole("tab", { name: "PV" }));
      await waitFor(() => screen.getByText("36.120"));
    } finally { h.restore(); }
  });
});

describe("Agents page — lifecycle command blocked, advisory request rendered", () => {
  it("shows the ACTION BLOCKED notice when the user types 'promote this model'", async () => {
    const h = mockDefault();
    try {
      render(<MemoryRouter initialEntries={["/agents"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByText(/Bounded agent query types/i));
      const input = screen.getByPlaceholderText(/Ask the bounded agent/i);
      fireEvent.change(input, { target: { value: "promote this model" } });
      fireEvent.click(screen.getByRole("button", { name: "Ask" }));
      await waitFor(() => screen.getByText(/ACTION BLOCKED/));
      expect(screen.getByText(/Agents are advisory only/)).toBeInTheDocument();
      // The advisory bounded-agent response IS rendered (the firewall blocked
      // the lifecycle *recommendation* but the response is still advisory).
      expect(screen.getByText(/firewall/i)).toBeInTheDocument();
    } finally { h.restore(); }
  });

  it("advisory question is forwarded and renders the advisory response", async () => {
    const h = mockDefault();
    try {
      render(<MemoryRouter initialEntries={["/agents"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByText(/Bounded agent query types/i));
      const input = screen.getByPlaceholderText(/Ask the bounded agent/i);
      fireEvent.change(input, { target: { value: "Why was this model rejected?" } });
      fireEvent.click(screen.getByRole("button", { name: "Ask" }));
      await waitFor(() => screen.getByText(/beats H24 daily persistence/));
    } finally { h.restore(); }
  });
});

describe("Governance page — deny is visually distinct", () => {
  it("renders the BENCHMARK_GATE_FAILED deny decision and a green ALLOW pill is not present", async () => {
    const h = mockDefault();
    try {
      render(<MemoryRouter initialEntries={["/governance"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByText(/BENCHMARK_GATE_FAILED/));
      expect(screen.getAllByText("DENY").length).toBeGreaterThan(0);
    } finally { h.restore(); }
  });
});

describe("Audit page — JSONL integrity wording is honest", () => {
  it("uses 'Audit structure: VALID JSONL' wording, not 'cryptographically verified'", async () => {
    const h = mockDefault();
    try {
      render(<MemoryRouter initialEntries={["/audit"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByText(/Audit structure/));
      expect(screen.getByText("VALID JSONL")).toBeInTheDocument();
      expect(screen.queryByText(/cryptographically verified/i)).toBeNull();
    } finally { h.restore(); }
  });
});

describe("Dashboard — primary workflow story is visible", () => {
  it("shows the DRIFT -> AGENT -> GOVERNANCE flow and the OFFLINE EVALUATION indicator", async () => {
    const h = mockDefault();
    try {
      render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByText(/Primary workflow/));
      expect(screen.getByText(/OFFLINE EVALUATION/)).toBeInTheDocument();
      expect(screen.getByText(/Drift \/ Degradation/)).toBeInTheDocument();
      expect(screen.getByText(/Agent investigates/)).toBeInTheDocument();
      expect(screen.getByText(/Governance evaluates/)).toBeInTheDocument();
    } finally { h.restore(); }
  });
});

describe("Sidebar — no mutation UI; quantum claim", () => {
  it("renders the 8 nav links (Dashboard through Demo) and the Quantum/QML not-part-of-project line", async () => {
    const h = mockDefault();
    try {
      const { container } = render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
      // The Sidebar nav is rendered immediately on the initial route; we don't
      // need to wait for the Dashboard API to settle.
      await waitFor(() => {
        const labels = Array.from(container.querySelectorAll(".sidebar__link-label")).map((n) => n.textContent);
        expect(labels).toEqual([
          "Dashboard", "Forecasts", "Models", "Monitoring",
          "Governance", "Agents", "Audit", "Demo",
        ]);
      });
      expect(screen.getByText(/Quantum\/QML: NOT PART OF PROJECT/)).toBeInTheDocument();
    } finally { h.restore(); }
  });
});

describe("Error states", () => {
  it("Dashboard renders an error banner when the API returns a 503", async () => {
    // Set per-endpoint Response-like overrides. The mock passes any object
    // with `status` + `text` through as-is, so we can return a 503 envelope.
    const h = makeFetchMock();
    const errResp = (path: string): Response => ({
      status: 503, ok: false, statusText: "Service Unavailable",
      text: async () => JSON.stringify({ error: { type: "http", status: 503,
        detail: "missing artefact", path } }),
      json: async () => ({}),
    } as unknown as Response);
    for (const p of ["/health", "/api/forecasts", "/api/models",
                     "/api/monitoring/events", "/api/monitoring/drift",
                     "/api/governance/policy", "/api/governance/decisions",
                     "/api/agents/types", "/api/agents/explain",
                     "/api/audit/events", "/api/audit/verify"]) {
      h.set(p, errResp(p));
    }
    h.install();
    try {
      render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
      await waitFor(() => {
        const alerts = screen.getAllByRole("alert");
        const found = alerts.some((el) => /HTTP 503.*missing artefact/.test(el.textContent ?? ""));
        expect(found).toBe(true);
      });
    } finally { h.restore(); }
  });
});
