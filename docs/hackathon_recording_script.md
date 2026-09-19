# 90–120 second video / demo recording script

**Target length:** 90–120 seconds. **Target viewer:** a judge who has not read the repository. **Goal:** communicate the project without requiring the viewer to understand the repository.

## Pre-recording checklist

- [ ] `hackathon/index.html` is the first thing visible.
- [ ] Browser zoom at 100% (so the result card on the right renders correctly).
- [ ] Browser DevTools closed.
- [ ] Notifications and OS alerts muted.
- [ ] Microphone tested.

## Recording script

| Scene | Duration | Screen | Action | Spoken line (or on-screen caption) | Transition |
| --- | --- | --- | --- | --- | --- |
| 1 | 0–5 s | Hero | Static on landing page. | "Guardrailed Agentic MLOps for Smart-Grid Forecasting." | Hard cut. |
| 2 | 5–15 s | Hero (zoom in to result card) | Cursor hovers over the PV row. | "The PV model beats the H24 daily persistence benchmark by 7.6%. The LOAD and WIND models don't. We present the negative result." | Slow pan down. |
| 3 | 15–25 s | Problem section | Scroll down to "The problem." | "Most MLOps projects give the agent real authority. We asked the opposite: can a bounded agent reduce explanation burden without controlling the lifecycle?" | Continue scrolling. |
| 4 | 25–35 s | Solution section | Scroll to "The solution." | "20 phases, ending in a frozen, fully audited evaluation on a 2-month locked test partition." | Continue scrolling. |
| 5 | 35–50 s | Architecture section | Scroll to the architecture SVG. Cursor highlights the firewall row. | "Five agents sit beside the lifecycle. They can investigate, summarize, explain, request review, and create reports. They cannot promote, rollback, retrain, change features, or change policies. Deny-by-default." | Pan to the ALLOW/BLOCK row. |
| 6 | 50–70 s | Demo → Dashboard | Click "Open the dashboard." On the dashboard, click the PV tab. Scroll to Benchmark comparison. | "The dashboard is the primary demo. Click PV: it beats its benchmark. LOAD and WIND do not. Every number here is reproducible from the frozen artefacts." | Stay on the benchmark table for 3 seconds. |
| 7 | 70–85 s | What makes this different (scroll back) | Scroll back to "What makes this different." | "Differentiation: governance firewall, honest mixed-outcome evaluation, frozen protocol cascade, deterministic evidence pipeline. 20 phases of frozen artefacts." | Slow zoom out. |
| 8 | 85–100 s | Final panel | Scroll to the limitations section. | "Limits: one year, one dataset, classical ML only, external benchmark is strong. We report them." | Hard cut. |
| 9 | 100–115 s | Architecture SVG (zoom out) | Pull back to show the full diagram. | "20-phase governance-first MLOps. The 5 agent layer is firewalled. The 2-month final evaluation is read-only." | Hard cut. |
| 10 | 115–120 s | Title card | Static. | "Thank you. Repository: [link]. Demo: `dashboard/index.html`. 231 tests, 20 frozen protocols, 0 promotion, 0 retraining on test data." | End. |

## Recording tooling notes

- **Browser tab:** one tab. `hackathon/index.html` first, then `../dashboard/index.html` in a new tab if you want to keep both visible.
- **Cursor movement:** slow and deliberate; avoid clicking rapidly.
- **Typography on the result card:** at 1080p the green/red dots are 10px — verify they are visible on your recording resolution.
- **Audio:** record voice-over in a single take. If you make a mistake, do a hard cut at the next scene boundary, not a re-take of the whole segment.
- **No music, no transitions, no background graphics.** Restrained research aesthetic.

## Captions

- Add captions: the result numbers and the firewall names are the most important.
- Auto-generated captions will misread "MLOps" and "P10-load-random_forest-B_lags_only". Either post-process or pre-script them.

## Accessibility for the video

- Use a high-contrast recording theme (the dashboard's dark theme is fine).
- Add captions in `.srt` or `.vtt` (not the auto-generated on-platform ones).
- Avoid fast zoom-ins or quick cuts.
