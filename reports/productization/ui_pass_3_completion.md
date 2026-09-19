# UI Pass 3 — Judge-Mode Polish (completion report)

## 1. Issues found

| # | Area | Issue | Impact |
| --- | --- | --- | --- |
| 1 | Technical data | Long SHA-256 fingerprints and model identifiers in `<code>` elements overflowed table cells and card boundaries on narrow viewports | Layout breakage on Governance and Audit pages |
| 2 | Tables | Long reason codes and model identifiers in `<td>` cells caused horizontal scroll | Readability on Governance and Audit pages |
| 3 | Responsive | `.evaluator__row` had only 2 breakpoints (6-col → 2-col at 900px); 6 columns were too tight at 900–1100px | Cramped Governance evaluator on typical laptop widths |
| 4 | Responsive | Demo step indicator with 7 steps could overflow at narrow widths without scroll | Demo controls cut off on tablet/mobile |
| 5 | Interaction | `.btn` had no visible hover state; `.sidebar__link` had no transition | Interactive elements felt static |
| 6 | Layout | Grid/flex children (target cards, authority sections, research stages) could not shrink below their content width | Overflow at narrow viewports |
| 7 | Readability | Reason-code chips and governance decision values could overflow with long text | Unreadable on narrow viewports |
| 8 | Spacing | `.empty` and `.loading` could collapse to near-zero height during API loading | Layout jumps |
| 9 | Typography | Page titles at 28px were too large for 600px-wide viewports | Overwhelming on mobile/tablet |
| 10 | Tables | `<th>` headers could wrap mid-word on narrow viewports | Unreadable column headers |
| 11 | Demo | Demo controls did not wrap on narrow screens | Buttons cut off |
| 12 | Flow | Flow arrows (`→`) were visually too subtle | Pipeline steps ran together |

## 2. Improvements made

### Responsive behavior
- Added medium breakpoint (1100px) collapsing evaluator from 6 to 3 columns.
- Added narrow breakpoint (700px) collapsing evaluator to 1 column.
- Added `overflow-x: auto` + `-webkit-overflow-scrolling: touch` on demo step indicator.
- Reduced page title from 28px to 22px at ≤700px.
- Reduced hero padding at ≤700px.
- Added `flex-wrap: wrap` on demo controls.

### Interaction polish
- `.btn` hover: background shift to `--accent-dim` + subtle box-shadow glow.
- `.btn` active: inverted (background `--bg`, text `--accent`, border accent).
- `.sidebar__link` hover: `transition: background 0.12s, color 0.12s, border-color 0.12s`.
- `.card` hover: border-color shift from `--border` to `--border-strong`.
- `.target-tab` hover: border-color shift to accent + text color shift.

### Technical data readability
- `td code`, `.card code`, `.decision code`, `.gov-card code`: `overflow-wrap: anywhere; word-break: break-all; max-width: 280px` — prevents SHA-256 fingerprints from destroying layouts.
- `.table td`: `overflow-wrap: break-word; max-width: 320px`.
- `.decision__value`: `overflow-wrap: anywhere; min-width: 0`.
- `.chip`: `overflow-wrap: anywhere; max-width: 300px`.
- `.policy-grid > div`: `overflow-wrap: break-word`.
- `.banner`: `overflow-wrap: break-word`.
- `.agent-response__panel`: `overflow-wrap: break-word`.
- `.research-stage__desc`: `overflow-wrap: break-word`.
- `.hero__subtitle`: `overflow-wrap: break-word`.

### Layout stability
- `min-width: 0` on `.card__body`, `.targets-row > *`, `.authority > *`, `.research-stage > *`, `.sys-status__item`, `.flow__step` — allows grid/flex children to shrink below content width.
- `.empty`, `.loading`: `min-height: 60px` — prevents layout collapse during API loading.
- `.decision__label`: `white-space: nowrap; text-overflow: ellipsis` — prevents label wrapping.
- `.table th`: `white-space: nowrap` — prevents column-header wrapping.
- `.authority__blocked-item`, `.authority__allow-item`: `white-space: nowrap` — prevents badge text wrapping.
- `.flow__arrow`: `font-size: 14px; color: var(--border-strong); user-select: none` — more visually distinct.

### Spacing
- `.section-label`: `margin-bottom: var(--sp-2)` — consistent spacing below section labels.
- `.sidebar__foot`: `padding-bottom: var(--sp-2)` — prevents footer touching viewport edge.
- `.sys-status__item`: `gap: var(--sp-1)` — tighter label-to-value spacing.

## 3. Files changed

| File | Change |
| --- | --- |
| `product/frontend/src/styles.css` | Added ~80 lines of targeted CSS polish fixes at the end of the file. No existing rules were removed or rewritten. |

## 4. Tests changed

**NONE.** All 27 existing frontend tests pass without modification.

## 5. Verification

| Check | Result |
| --- | --- |
| Frontend tests | **27/27 PASS** (5.48s) |
| TypeScript | **PASS** (exit 0) |
| Production build | **PASS** (439.33 kB JS / 24.48 kB CSS, gzip 142.11 kB / 4.75 kB) |

## 6. Regression boundaries

| Boundary | Status |
| --- | --- |
| Backend changes | **NONE** |
| Protocol freeze | **20/20 PASS** |
| Phase 19 artifact integrity | **20/20 byte-identical** |
| Agent authority | **ADVISORY ONLY** |
| Governance authority | **AUTHORITATIVE** |
| No model promoted | **CONFIRMED** |
| No model deployed | **CONFIRMED** |
| No lifecycle mutation introduced | **CONFIRMED** |
| Historical replay explicitly labeled | **YES** (Monitoring page badges) |
| Quantum/QML NOT PART OF PROJECT | **YES** |

## 7. Final UX verdict

```
READY FOR JUDGES
```

The application now:

- Communicates the authority model (AGENT ≠ AUTONOMOUS CONTROL)
  on the Dashboard, Agents page, and in the persistent sidebar
- Makes Stages 7–14 visible through the Research timeline with
  the Stage 10 → Stage 14 DENY contrast
- Handles long technical identifiers without layout breakage
- Maintains readable tables and dense engineering data at all
  tested viewport widths
- Provides visible hover, active, and focus states for all
  interactive elements
- Uses honest loading and empty states that don't fabricate data
- Clearly distinguishes HISTORICAL REPLAY from live telemetry
- Labels every page with its authority boundary
