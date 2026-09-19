# 90-second hackathon demo script

**Target audience:** a technical judge seeing the project for the first time. **Goal:** the judge should understand WHAT we built, WHY it matters, and see the actual result — within 90 seconds.

| Time | What the presenter does | What the judge sees |
| --- | --- | --- |
| 0–15 s | Open `hackathon/index.html` in the browser. The hero card on the right already shows the result table (PV −7.61% / LOAD +72.29% / WIND +135.08%). | "Final result on locked test partition" with the three rows visible. |
| 15–30 s | Scroll to "The problem". Read the first paragraph aloud. Then scroll to "What makes this different" and skim the first bullet: "Most MLOps projects treat 'AI for MLOps' as autonomous promotion/retraining. We built the inverse." | A two-paragraph explanation that a judge can follow without quantum / classical-ML background. |
| 30–55 s | Click "Open the dashboard" in the Demo section. The dashboard loads. On the executive overview, point at the "AUTHORIZED FOR INFERENCE ONLY" pill and the F11/F12 walk-forward fold badges. Click the **PV** target tab. | The frozen result card flips to PV. The headline finding for PV says "outperforms" with a green dot. |
| 55–70 s | Scroll to "Benchmark comparison". Read the row for PV aloud: 36.12 vs 39.09, −7.61%, **Better**. Then the row for LOAD: 174.26 vs 101.14, +72.29%, **Worse**. Don't hide it. | The mixed outcome is explicit and tabulated. |
| 70–85 s | Scroll to "What makes this different". Click the third bullet: "Honest mixed-outcome final evaluation." Then point at the firewall diagram above: ALLOW list (green) vs BLOCK list (red). | The agent firewall is rendered visually; the unique claim is concrete, not a slogan. |
| 85–90 s | Closing line: "PV beats its benchmark by 7.6%. LOAD and WIND don't. We present both. The dashboard and the research are reproducible from a single `pytest`." | The presenter does not hide negative results. The reproducibility claim is verifiable. |

## What to NOT do in the 90 seconds

- Do not open the actual code editor.
- Do not open the architecture SVG.
- Do not open the charts page (it is a deeper drill-down, not a headline).
- Do not say "AI for energy forecasting" or any quantum / GNN phrase — the project does not contain those.
- Do not claim "the model beats RTS_DAY_AHEAD overall" — it doesn't. It only beats H24 daily persistence for PV.

## Failure modes to anticipate

- "Did you try XGBoost?" → "The frozen model registry is locked at Phase 11; we used random forest and hist gradient boosting per the final ablation. Adding XGBoost would re-open frozen evaluation. We chose not to."
- "Why are LOAD and WIND worse?" → "The published RTS_DAY_AHEAD forecast is a strong operating artefact for short horizons. Our models beat it on the 2-month PV comparison, not on the year-long LOAD/WIND comparison. The system reports this honestly."
- "What about the agent layer — does it change anything?" → "It does not change lifecycle outcomes. Phase 18 measured 0 lifecycle differences and 14/14 unsafe recommendations blocked. It reduces explanation effort by ~72% under a frozen cost model."
