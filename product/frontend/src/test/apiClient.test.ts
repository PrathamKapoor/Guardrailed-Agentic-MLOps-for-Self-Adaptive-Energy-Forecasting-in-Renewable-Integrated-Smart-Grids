import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { APIClient, APIRequestError } from "../api/client";

function okResponse(body: unknown): Response {
  return { ok: true, status: 200, statusText: "OK",
           text: async () => JSON.stringify(body) } as Response;
}
function notFound(body: unknown): Response {
  return { ok: false, status: 404, statusText: "Not Found",
           text: async () => JSON.stringify(body) } as Response;
}

describe("APIClient", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  beforeEach(() => { fetchMock = vi.fn(); globalThis.fetch = fetchMock as any; });
  afterEach(() => { vi.restoreAllMocks(); });

  it("issues GET requests at the expected path", async () => {
    fetchMock.mockResolvedValueOnce(okResponse({ ok: true }));
    const c = new APIClient("/api");
    await c.health();
    // /health is served at the backend root, outside the "/api" base prefix.
    expect(fetchMock).toHaveBeenCalledWith("/health", { method: "GET" });
  });

  it("serialises POST bodies as JSON", async () => {
    fetchMock.mockResolvedValueOnce(okResponse({ ok: true }));
    const c = new APIClient("/api");
    await c.evaluateGovernance({ subject_id: "x", current_state: "y", proposed_state: "z" });
    expect(fetchMock).toHaveBeenCalledWith("/api/governance/decisions",
      expect.objectContaining({ method: "POST",
                                 headers: expect.objectContaining({ "Content-Type": "application/json" }) }));
  });

  it("wraps non-2xx into APIRequestError with status, detail, path", async () => {
    fetchMock.mockResolvedValueOnce(notFound(
      { error: { type: "http", status: 404, detail: "not found", path: "/api/x" } }
    ));
    const c = new APIClient("/api");
    try { await c.getForecast("load"); throw new Error("expected throw"); } catch (e) {
      const err = e as APIRequestError;
      expect(err).toBeInstanceOf(APIRequestError);
      expect(err.status).toBe(404);
      expect(err.path).toBe("/forecasts/load");
      expect(err.detail).toBe("not found");
    }
    // The fetch URL itself is the resolved path with baseURL
    expect(fetchMock.mock.calls[0][0]).toBe("/api/forecasts/load");
  });

  it("uses a relative baseURL by default", async () => {
    fetchMock.mockResolvedValueOnce(okResponse({ ok: true }));
    const c = new APIClient();
    await c.getForecast("load");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/forecasts/load");
  });
});
