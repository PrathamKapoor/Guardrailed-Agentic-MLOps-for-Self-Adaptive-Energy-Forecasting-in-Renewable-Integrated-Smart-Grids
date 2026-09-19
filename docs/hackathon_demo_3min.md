# 3-minute hackathon demo script

**Goal:** the judge understands the project end-to-end (problem, architecture, demo, results, evidence, differentiation, conclusion) without improvisation. Walk through the elements below; every link and every number has been verified against the repository.

## 0:00–0:30 — Problem (30 sec)

Open `hackathon/index.html`. Stand on the **hero** section. Read the lede and the first bullet of the hero list. The judge sees the result table on the right immediately — there is no setup curtain.

Say:

> "We built a 20-phase MLOps research system for electricity forecasting. Most 'AI for MLOps' projects give the agent real authority over promotion, retraining, and rollback. We built the inverse: a bounded, firewalled decision-support layer that reduces explanation effort but cannot control the lifecycle. The result card on the right already shows the honest outcome — the PV model beats its benchmark by 7.6%; LOAD and WIND do not. We will get back to that."

## 0:30–1:00 — Architecture (30 sec)

Scroll to **Architecture**. Point at the architecture SVG: data → preprocessing → features → tracking → governance → drift monitoring → finalist registry → governed retraining → champion-challenger + rollback → bounded agent layer → final evaluation. Mention the firewall row: ALLOW (green) and BLOCK (red). Don't explain every box — point at the firewall.

Say:

> "The five agents in the layer on the right can investigate, summarize, explain, request human review, and create reports. They cannot promote, rollback, retrain, change features, or change policies. The firewall is deny-by-default and every blocked attempt is audited."

## 1:00–1:30 — Quantum / advanced component (skipped)

The repository does not contain a quantum or graph-neural component. The hackathon layer is honest about this. The 20-phase system is classical ML (random forest, hist gradient boosting, MLP) on RTS-GMLC 2020. Do not invent a quantum or GNN story — judges who read the code will discover it immediately.

If the judge asks about more advanced modelling:

> "The frozen system is classical ML on a single year of a single dataset. We chose rigour over technique variety. The HPO explored gradient boosting, random forest, and MLP; the Phase 10 ablation selected the simplest configuration that met the within-0.5% tie-break criterion. The governance layer is what we wanted to demonstrate."

## 1:30–2:15 — Interactive demo (45 sec)

Click **Open the dashboard** in the Demo section. On the dashboard:

1. Point at the status pills (EVALUATION: COMPLETE, Folds: F11, F12, Final-test access: Inference only, Configuration frozen: PASS).
2. Click the **PV** target tab. The card switches to PV. The headline finding says "outperforms" with a green dot.
3. Scroll to **Benchmark comparison**. Read the three rows. The PV row is the only "Better" row. The LOAD and WIND rows are clearly "Worse" with a red dot.
4. Click the small "Open the chart" button in the Demo section on the landing page (or visit `dashboard/charts.html`). The actual-vs-predicted chart shows PV's random forest tracking the actual values. You don't need to interact with the date filter — just point at the chart.

## 2:15–2:45 — Evidence (30 sec)

Scroll back to the landing page's **Research evidence** section. Mention the chain:

1. Model identity — `artifacts/model_registry/forecasting_reference_registry.yaml` + `lifecycle_registry.yaml`
2. Frozen protocol — `artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml` (SHA-256 `79053d6f…`)
3. Final evaluation — `artifacts/experiments/final_evaluation/phase_19/official/`
4. Read-only dashboard — `dashboard/index.html` (this is the primary demo)
5. Full research documentation — `docs/research_methodology/` (20 documents), `docs/paper_drafts/` (12 documents)

Say:

> "Every claim on this page is reproducible from those five artefacts. The 20-phase protocol cascade means the final evaluation was the only access to the locked test partition. The dashboard builder is verified to leave the Phase 19 artefacts byte-identical."

## 2:45–3:00 — Differentiation + closing (15 sec)

Scroll to **What makes this different** on the landing page. Don't read the bullets — point at the firewall diagram you already explained. End with:

> "Differentiation: a governance firewall that keeps agents from controlling the lifecycle, an honest mixed-outcome final evaluation, a frozen protocol cascade, and a read-only evidence interface. The 20 phases of frozen artefacts are the submission. Thank you."

## What to NOT do in the 3 minutes

- Do not open the actual code. (If asked, point at `AGENTS.md`, the phase completion reports, and the `src/smartgrid_mlops/` tree.)
- Do not claim quantum / GNN / advanced techniques. (The repository doesn't contain them.)
- Do not minimize the LOAD/WIND negative result. (It is part of the honest story.)
- Do not promise future work as a current capability. (Phase 19 is the only authorized final evaluation; Phase 20 is the only UI.)
- Do not claim "real-time" or "production deployment." (There is none — the system is offline evaluation only.)

## How to handle each likely judge question

- **"Why classical ML only?"** → "The system is a research artefact demonstrating governance, not a model zoo. The frozen pipeline selects the simplest model that meets the within-0.5% tie-break criterion; Phase 10 ablations showed larger feature sets did not improve the finalists."
- **"Did the agents ever do anything dangerous?"** → "No. Phase 18 measured 0 lifecycle differences and 14 of 14 unsafe recommendations blocked. The firewall rejects forbidden events at the audit module level, not just at runtime."
- **"Why is the frozen evaluation on November–December 2020 only?"** → "Folds F01–F06 cover January–October 2020. November–December is the only data the system has never seen. We locked it as the final test before any model work and authorized access exactly once under `AccessMode.FINAL_EVALUATION`."
- **"Can I run it?"** → "Yes. `python -m venv .venv && .venv/Scripts/python.exe -m pip install -e ".[dev]" && .venv/Scripts/python.exe -m pytest` runs 231 backend + 18 dashboard tests. The dashboard is a static page — `start dashboard/index.html` opens it. Full instructions are in the Quick Start section of the landing page."
- **"Where is the 'research' here?"** → "20 phase completion reports under `reports/`, 20 frozen protocol artefacts under `artifacts/experimental_design/`, 12 paper drafts under `docs/paper_drafts/`, the frozen final evaluation evidence under `artifacts/experiments/final_evaluation/phase_19/`, and the MLflow lineage."
