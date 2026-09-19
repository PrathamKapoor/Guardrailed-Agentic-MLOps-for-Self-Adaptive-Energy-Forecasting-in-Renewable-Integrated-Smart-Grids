/** Agent safety + lifecycle gate. The frontend never exposes mutation UI
 *  for the 7 lifecycle action types. This module is the single source of
 *  truth for what the UI must NOT pretend to execute.
 *
 *  The Stage 1 / Stage 2 guarantee is preserved at the UI layer by:
 *    (a) refusing to render mutation buttons for lifecycle types
 *    (b) surfacing the firewall decision when an agent response is blocked
 *    (c) labeling blocked agent recommendations explicitly
 */

export const LIFECYCLE_ACTION_TYPES = [
  "PROMOTE",
  "DEPLOY",
  "ROLLBACK",
  "RETRAIN",
  "CHANGE_POLICY",
  "MODIFY_MODEL",
  "MODIFY_FEATURES",
] as const;

export type LifecycleActionType = typeof LIFECYCLE_ACTION_TYPES[number];

/** Returns true if the user-supplied free-form text resembles a lifecycle
 *  mutation request. Used to short-circuit the agent explainer with the
 *  visible "AGENT ACTION BLOCKED" notice.
 */
export function isLifecycleCommand(text: string): LifecycleActionType | null {
  const lc = text.toLowerCase();
  for (const t of LIFECYCLE_ACTION_TYPES) {
    if (lc.includes(t.toLowerCase())) {
      return t;
    }
  }
  // synonym detection (only for the action types the firewall blocks)
  if (/\bdeploy\b.*\bmodel\b/.test(lc)) return "DEPLOY";
  if (/\b(rollback|revert|restore)\b.*\b(model|version)\b/.test(lc)) return "ROLLBACK";
  return null;
}

/** The default life-cycle intent the agent recommend endpoint accepts. The
 *  spec mandates that bounded-agent requests are advisory only and that the
 *  firewall blocks lifecycle action types. This helper formats the visible
 *  advisory notice.
 */
export function advisoryBlockedNotice(requested: LifecycleActionType): {
  title: string;
  body: string;
  recommendation: string;
} {
  return {
    title: "ACTION BLOCKED",
    body: `The bounded agent layer cannot perform "${requested}". Agents are advisory only.`,
    recommendation: "Lifecycle operations must pass through deterministic governance.",
  };
}
