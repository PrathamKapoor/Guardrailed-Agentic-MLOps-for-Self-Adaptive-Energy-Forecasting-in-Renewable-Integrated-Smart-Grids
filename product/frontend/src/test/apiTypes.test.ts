import { describe, it, expect } from "vitest";
import type { Recommendation } from "../api/types";
import { TARGETS, type Target } from "../api/types";

describe("api.types (Stage 1 contract mirror)", () => {
  it("exposes the three frozen targets in a stable order", () => {
    expect(TARGETS).toEqual(["load", "wind", "pv"] as readonly Target[]);
  });

  it("the recommendation union is the 5 advisory types only (no lifecycle types)", () => {
    const allowed: Recommendation[] = ["INVESTIGATE", "SUMMARIZE", "EXPLAIN",
                                         "REQUEST_HUMAN_REVIEW", "CREATE_REPORT"];
    expect(allowed.length).toBe(5);
    // None of the 7 lifecycle action types are in the allowed set
    for (const t of ["PROMOTE", "DEPLOY", "ROLLBACK", "RETRAIN",
                     "CHANGE_POLICY", "MODIFY_MODEL", "MODIFY_FEATURES"]) {
      expect(allowed).not.toContain(t as Recommendation);
    }
  });
});
