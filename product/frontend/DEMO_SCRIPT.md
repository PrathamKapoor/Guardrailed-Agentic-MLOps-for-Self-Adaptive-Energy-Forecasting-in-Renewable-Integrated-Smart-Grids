# Demo script (3–5 minute walkthrough)

The demo is a deterministic, read-only walkthrough of the existing
evidence. Every number comes from the Stage 2 FastAPI service, which
itself sources the frozen Phase 11/13/19 artefacts. **No model is
retrained, no result is fabricated, and no lifecycle action is executed
from the demo.** The only side effects are visual: the URL query string
records the current step so the demo is linkable.

## Pre-flight (before the demo starts)

- The Stage 2 API must be running on `http://127.0.0.1:8000` (see
  `reports/productization/api_stage_2_completion.md` for `uvicorn`).
- Open `http://127.0.0.1:5173/demo` in a browser. (Run `npm run dev`
  in `product/frontend/` if not already running.)

## 0:00 – 0:30 — Introduce the problem

> "We are building the operations console for a 20-phase MLOps
> research project on smart-grid forecasting. The repository is
> organised as: a deterministic MLOps backend that already runs
> experiments end-to-end, a small FastAPI service over the existing
> productization layer, and now this React dashboard. The point is
> to make the existing research system legible and reproducible."

Click around the sidebar briefly to show the 8 links (Dashboard,
Forecasts, Models, Monitoring, Governance, Agents, Audit, **Demo**). Point
at the **OFFLINE EVALUATION** pill in the sidebar and the
**Quantum/QML: NOT PART OF PROJECT** footer line.

## 0:30 – 1:15 — Show the forecasting model and its result

Click **Forecasts** in the sidebar. Note the metric row for each
target. The story is honest:

- **PV: 36.12** vs H24 daily persistence **39.09** → the frozen model
  wins by **7.61%**.
- **LOAD: 174.26** vs RTS_DAY_AHEAD **101.14** → the frozen model
  loses by **72.29%**.
- **WIND: 778.84** vs RTS_DAY_AHEAD **331.30** → the frozen model
  loses by **135.08%**.

> "The system does not claim universal superiority. The PV model wins
> on MAE; LOAD and WIND do not beat the published operating
> benchmark. This honest mixed-outcome is the result we present."

## 1:15 – 2:00 — Show the monitoring layer

Click **Monitoring**. The 12 events derived from the frozen final-test
evidence are listed. Every event has its event_type, target, model, and
the recorded final_test_status. Point at the **severity indicator** on
each row.

> "The monitoring layer is offline: it is a one-shot read of the
> frozen artefacts. There is no live telemetry, no streaming, and
> no real-time inference in this build."

## 2:00 – 2:40 — Show the agent layer and the firewall

Click **Agents**. Type a recommended action: "**Promote this model**".
The UI shows the **ACTION BLOCKED** notice. The bounded agent layer
does not pretend to execute the command.

Now type a real question: "**Why was this model rejected?**" The
bounded agent returns an advisory explanation with the firewall
decision (allowed) and the recommendation (EXPLAIN).

> "The firewall blocks lifecycle action types regardless of how the
> request is structured. The agent's recommendation is advisory only.
> The deterministic governance engine is the only path that can
> move lifecycle state, and it requires the candidate to pass all
> frozen gates."

## 2:40 – 3:20 — Show the deterministic governance

Click **Governance**. The frozen Phase 13 policy is shown with its
fingerprint. The decision log lists 18 real Phase 13 governance
decisions. Use the "Try a decision" form to submit a request:

- subject_id = `MLOPS-REF-LOAD-H24-V1`
- from = `PROMOTION_ELIGIBLE`
- to = `APPROVAL_PENDING`
- benchmark_gate = `BENCHMARK_GATE_FAIL`

The deterministic engine returns **DENY** with reason code
**BENCHMARK_GATE_FAILED** and a SHA-256 decision fingerprint.

> "The decision is deterministic: identical inputs produce identical
> fingerprints. The benchmark gate is the reason LOAD's frozen model
> does not pass — its dev MAE is 285, the published benchmark is
> lower. The system does not pretend this is OK; it says DENY."

## 3:20 – 4:00 — Show the blocked unsafe action

Now switch to the **Demo** tab. Pick the **Safety boundary** scenario.
Step through 1 → 5:

- **1. Context**: the 7 lifecycle action types are listed.
- **2. Frontend safety gate**: the UI short-circuits lifecycle commands
  with the **ACTION BLOCKED** notice.
- **3. Even if the gate were bypassed, governance would still block**:
  the deterministic engine independently evaluates any candidate.
- **4. No fake execution**: the UI never implies the agent executed
  the lifecycle action.
- **5. Audit trail**: the attempt is recorded as an
  AGENT_QUERY_RECEIVED event in the existing evidence-ledger JSONL.

> "The visual distinction is: AGENT RECOMMENDATION ≠ GOVERNANCE
> DECISION. The agent's job is to recommend; the governance's job
> is to authorize. The firewall enforces this boundary at three
> layers: the frontend safety gate, the bounded agent layer, and
> the deterministic governance engine."

## 4:00 – 4:30 — Show the audit trail

Click **Audit**. The 18 governance decisions are listed (from the
existing JSONL). The verify endpoint reports
**Audit structure: VALID JSONL** — the existing implementation
validates JSONL well-formedness. We **do not** claim cryptographic
verification; the system does not have a hash chain in the current
implementation.

> "Every meaningful event in the system is appended to this JSONL.
> The audit page is a real view into the existing ledger, not a
> fabricated visualization."

## 4:30 – 5:00 — Show the Final result interpretation

Scroll to the bottom of the Demo page. The Final result interpretation
block is the same honest mixed-outcome you saw on the Forecasts page:

- **PV**: Better than benchmark (−7.61%)
- **LOAD**: Worse than benchmark (+72.29%)
- **WIND**: Worse than benchmark (+135.08%)

> "This is the research contribution: a governance-first MLOps
> system where agentic AI is bounded by a deterministic firewall, and
> where the final result is reported honestly — including the
> targets where the model loses. Thank you."

## After the demo

If the judge asks follow-up questions, point at:

- `dashboard/index.html` for the read-only research evidence surface
  (Phase 20).
- `docs/research_methodology/final_evaluation.md` for the locked
  test protocol and the honest mixed-outcome justification.
- `reports/phase_19_completion.md` for the frozen final evaluation
  results.
- `reports/productization/api_stage_2_completion.md` for the
  API contract.
- `docs/productization/api_contract.md` for the 17 endpoints.

## Non-goals (do not claim these in the demo)

- "Real-time" / "live" / "streaming" — the system is offline.
- "Quantum" / "QML" / "GNN" — the project does not contain them.
- "LLM-powered agent" — the bounded agent is local-rule-based. The
  LLM backend interface is a contract only.
- "Production deployment" — there is no production deployment.
- "Autonomous agent" — the agent cannot perform lifecycle actions.
