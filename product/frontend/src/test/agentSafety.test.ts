import { describe, it, expect } from "vitest";
import { LIFECYCLE_ACTION_TYPES, isLifecycleCommand, advisoryBlockedNotice } from "../api/agentSafety";

describe("agentSafety.isLifecycleCommand", () => {
  it("returns null for advisory questions", () => {
    expect(isLifecycleCommand("Why was this model rejected?")).toBeNull();
    expect(isLifecycleCommand("What is the MAE on PV?")).toBeNull();
    expect(isLifecycleCommand("Explain the drift event.")).toBeNull();
  });

  it("detects each lifecycle action type", () => {
    expect(isLifecycleCommand("Please PROMOTE this model.")).toBe("PROMOTE");
    expect(isLifecycleCommand("Deploy the new version.")).toBe("DEPLOY");
    expect(isLifecycleCommand("Trigger a ROLLBACK now.")).toBe("ROLLBACK");
    expect(isLifecycleCommand("Run a RETRAIN cycle.")).toBe("RETRAIN");
    expect(isLifecycleCommand("CHANGE_POLICY please.")).toBe("CHANGE_POLICY");
    expect(isLifecycleCommand("MODIFY_MODEL weights")).toBe("MODIFY_MODEL");
    expect(isLifecycleCommand("MODIFY_FEATURES list")).toBe("MODIFY_FEATURES");
  });

  it("detects synonym phrasing", () => {
    expect(isLifecycleCommand("deploy the model")).toBe("DEPLOY");
    expect(isLifecycleCommand("rollback the previous model")).toBe("ROLLBACK");
    expect(isLifecycleCommand("revert the current model")).toBe("ROLLBACK");
  });

  it("is case-insensitive", () => {
    expect(isLifecycleCommand("promote this model")).toBe("PROMOTE");
    expect(isLifecycleCommand("RetraiN now")).toBe("RETRAIN");
  });

  it("contains exactly the 7 lifecycle action types the firewall blocks", () => {
    expect(LIFECYCLE_ACTION_TYPES.length).toBe(7);
    expect(new Set(LIFECYCLE_ACTION_TYPES)).toEqual(new Set([
      "PROMOTE", "DEPLOY", "ROLLBACK", "RETRAIN",
      "CHANGE_POLICY", "MODIFY_MODEL", "MODIFY_FEATURES",
    ]));
  });
});

describe("agentSafety.advisoryBlockedNotice", () => {
  it("returns the visible advisory notice for any lifecycle action", () => {
    const n = advisoryBlockedNotice("PROMOTE");
    expect(n.title).toBe("ACTION BLOCKED");
    expect(n.body).toMatch(/PROMOTE/);
    expect(n.recommendation).toMatch(/deterministic governance/);
  });
});
