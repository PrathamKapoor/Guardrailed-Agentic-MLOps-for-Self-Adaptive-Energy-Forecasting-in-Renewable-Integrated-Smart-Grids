import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";

// Per-test isolation: restore any global stubs FIRST, then clear mock call
// records. The clear-order matters: vi.unstubAllGlobals() removes the
// stubbed fetch (so the next test's installFetchMock can stub a fresh
// instance), then vi.clearAllMocks() resets call history on any remaining
// spied/observed objects.
afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});
