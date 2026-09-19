import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";
import { installFetchMock } from "./apiMocks";
import { PRIMARY_SCENARIO, SAFETY_SCENARIO } from "../demo/demoData";

beforeEach(() => {
  // Stub out the API-health polling so timers from one test don't bleed into
  // another. The shared afterEach (in src/test/setup.ts) calls vi.unstubAllGlobals
  // and vi.clearAllMocks() to restore state.
  vi.stubGlobal("setInterval", () => 0 as unknown as ReturnType<typeof setInterval>);
  vi.stubGlobal("clearInterval", () => undefined);
});

describe("Demo Mode — primary scenario", () => {
  it("renders all 7 primary steps in sequence with next/previous/restart", async () => {
    const h = installFetchMock();
    try {
      // The Demo component defaults to the "primary" scenario when no query is set.
      render(<MemoryRouter initialEntries={["/demo"]}><App /></MemoryRouter>);
      // Step indicator dot: aria-label "Step 1: 1. System overview"
      await waitFor(() => screen.getByRole("button", { name: /Step 1.*System overview/i }));
      expect(PRIMARY_SCENARIO.steps.length).toBe(7);
      fireEvent.click(screen.getByRole("button", { name: /Next/ }));
      await waitFor(() => screen.getByRole("button", { name: /Step 2.*Frozen forecasts/i }));
      fireEvent.click(screen.getByRole("button", { name: /Previous/ }));
      await waitFor(() => screen.getByRole("button", { name: /Step 1.*System overview/i }));
      fireEvent.click(screen.getByRole("button", { name: /Restart/ }));
      await waitFor(() => screen.getByRole("button", { name: /Step 1.*System overview/i }));
    } finally { h.restore(); }
  });
});

describe("Demo Mode — safety scenario", () => {
  it("renders the safety scenario and the FINAL INTERPRETATION block", async () => {
    const h = installFetchMock();
    try {
      render(<MemoryRouter initialEntries={["/demo"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByRole("button", { name: /Step 1.*System overview/i }));
      fireEvent.click(screen.getByRole("tab", { name: /safety/i }));
      await waitFor(() => screen.getByRole("button", { name: /Step 1.*Context/i }));
      expect(SAFETY_SCENARIO.steps.length).toBe(5);
      await waitFor(() => screen.getByText(/Final result interpretation/));
      expect(screen.getByText(/Better than benchmark/)).toBeInTheDocument();
      expect(screen.getAllByText(/Worse than benchmark/).length).toBeGreaterThanOrEqual(2);
    } finally { h.restore(); }
  });
});

describe("Demo Mode — safety guarantees", () => {
  it("renders the non-goals block listing what the demo does NOT do", async () => {
    const h = installFetchMock();
    try {
      render(<MemoryRouter initialEntries={["/demo"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByRole("button", { name: /Step 1.*System overview/i }));
      // The non-goal sentences are split across inline elements
      // (e.g. "does <strong>not</strong> retrain"). The page renders them
      // inside a <ul>; assert the visible text content contains each
      // fragment at least once.
      expect(screen.getByText(/What the demo does NOT do/)).toBeInTheDocument();
      const allText = document.body.textContent ?? "";
      expect(allText).toMatch(/does\s+not\s+retrain/);
      expect(allText).toMatch(/does\s+not\s+claim cryptographic/);
      expect(allText).toMatch(/does\s+not\s+add a fake real-time/);
      // Quantum / QML / GNN must not appear as advertised capabilities.
      // The non-goals card explicitly excludes them, so the only place
      // they appear is in the "not a fake LLM, or any quantum / QML / GNN
      // component" sentence. We assert the demo does not contain any
      // claim of these as live features.
      const demoRoot = document.querySelector(".demo-page");
      const demoText = (demoRoot?.textContent ?? "").toLowerCase();
      expect(demoText).not.toMatch(/quantum computing|qml algorithm|gnn-based model/);
    } finally { h.restore(); }
  });

  it("does not render any Promote/Deploy/Rollback/Retrain buttons", async () => {
    const h = installFetchMock();
    try {
      render(<MemoryRouter initialEntries={["/demo"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByRole("button", { name: /Step 1.*System overview/i }));
      fireEvent.click(screen.getByRole("tab", { name: /safety/i }));
      await waitFor(() => screen.getByRole("button", { name: /Step 1.*Context/i }));
      fireEvent.click(screen.getByRole("button", { name: /Next/ }));
      await waitFor(() => screen.getByRole("button", { name: /Step 2.*Frontend safety gate/i }));
      for (const verb of ["PROMOTE", "DEPLOY", "ROLLBACK", "RETRAIN",
                         "CHANGE_POLICY", "MODIFY_MODEL", "MODIFY_FEATURES"]) {
        const matches = screen.queryAllByText(verb);
        for (const m of matches) {
          expect(m.closest("button")).toBeNull();
        }
      }
    } finally { h.restore(); }
  });
});

describe("Demo Mode — presentation mode", () => {
  it("toggles the presentation class on the demo page root (sidebar hidden via CSS)", async () => {
    const h = installFetchMock();
    try {
      render(<MemoryRouter initialEntries={["/demo"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByRole("button", { name: /Step 1.*System overview/i }));
      const demoRoot = document.querySelector(".demo-page");
      expect(demoRoot).not.toBeNull();
      expect(demoRoot!.className).not.toContain("demo-page--presentation");
      fireEvent.click(screen.getByRole("button", { name: /Enter presentation mode/i }));
      expect(demoRoot!.className).toContain("demo-page--presentation");
      // Navigation still works in presentation mode.
      fireEvent.click(screen.getByRole("button", { name: /Next/ }));
      await waitFor(() => screen.getByRole("button", { name: /Step 2.*Frozen forecasts/i }));
      fireEvent.click(screen.getByRole("button", { name: /Exit presentation mode/i }));
      expect(demoRoot!.className).not.toContain("demo-page--presentation");
    } finally { h.restore(); }
  });
});

describe("Demo Mode — governance firewall visual (no fake execution)", () => {
  it("renders the DENY decision with the actual reason code from the API response", async () => {
    const h = installFetchMock();
    try {
      render(<MemoryRouter initialEntries={["/demo"]}><App /></MemoryRouter>);
      await waitFor(() => screen.getByRole("button", { name: /Step 1.*System overview/i }));
      for (let i = 0; i < 4; i++) fireEvent.click(screen.getByRole("button", { name: /Next/ }));
      await waitFor(() => screen.getByText(/Governance decision/));
      expect(screen.getByText(/BENCHMARK_GATE_FAILED/)).toBeInTheDocument();
      expect(screen.getByText(/SMARTGRID_DETERMINISTIC_GOVERNANCE/)).toBeInTheDocument();
    } finally { h.restore(); }
  });
});
